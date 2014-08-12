# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import urlparse
import time

from .. import BeautifulSoup as bs
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

def _translate_date_german_english(date):
    fullmon = {"Januar":"01",
               "Februar":"02",
               u"März":"03",
               "April":"04",
               "Mai":"05",
               "Juni":"06",
               "Juli":"07",
               "August":"08",
               "September":"09",
               "Oktober":"10",
               "November":"11",
               "Dezember":"12"}
    for (name,num) in fullmon.items():
        date = date.replace(name,num)
    return date

_REGEX_TRAILING_DIGIT = re.compile("(\d+)$")
_REGEX_DASH_TO_END = re.compile("-[^-]+$")
_REGEX_CHAPTER_TITLE = re.compile(ur"""
    \s*
    [\u2013-]?
    \s*
    ([\dIVX-]+)?
    \.?
    \s*
    [\[\(]?
    \s*
    (Teil|Kapitel|Tag)?
    \s*
    ([\dIVX-]+)?
    \s*
    [\]\)]?
    \s*
    $
""", re.VERBOSE)
_INITIAL_STEP = 5

class BdsmGeschichtenAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8", "Windows-1252"]

        self.story.setMetadata('siteabbrev','bdsmgesch')

        # Replace possible chapter numbering
        chapterMatch = _REGEX_TRAILING_DIGIT.search(url)
        if chapterMatch is None:
            self.maxChapter = 1
        else:
            self.maxChapter = int(chapterMatch.group(1))
        # url = re.sub(_REGEX_TRAILING_DIGIT, "1", url)

        # set storyId
        self.story.setMetadata('storyId', re.compile(self.getSiteURLPattern()).match(url).group('storyId'))

        # normalize URL
        self._setURL('http://%s/%s' % (self.getSiteDomain(), self.story.getMetadata('storyId')))

        self.dateformat = '%d. %m %Y - %H:%M'

    @staticmethod
    def getSiteDomain():
        return 'bdsm-geschichten.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.bdsm-geschichten.net', 'www.bdsm-geschichten.net']

    @classmethod
    def getSiteExampleURLs(self):
        return "http://www.bdsm-geschichten.net/title-of-story-1 http://bdsm-geschichten.net/title-of-story-1"

    def getSiteURLPattern(self):
        return r"http://(www\.)?bdsm-geschichten.net/(?P<storyId>[a-zA-Z0-9_-]+)"

    def extractChapterUrlsAndMetadata(self):

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        try:
            data1 = self._fetchUrl(self.url)
            soup = bs.BeautifulSoup(data1)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        #strip comments from soup
        [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # Cache the soups so we won't have to redownload in getChapterText later
        self.soupsCache = {}
        self.soupsCache[self.url] = soup

        # author
        authorDiv = soup.find("div", "author-pane-line author-name")
        authorId = authorDiv.string.strip()
        self.story.setMetadata('authorId', authorId)
        self.story.setMetadata('author', authorId)
        # TODO not really true need to be loggedin for this to work or fetch userid
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+authorId)

        # TODO better metadata
        date = soup.find("div", {"class": "submitted"}).string.strip()
        date = re.sub(" &#151;.*", "", date)
        date = _translate_date_german_english(date)
        self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
        title1 = soup.find("h1", {'class': 'title'}).string


        for tagLink in soup.find("ul", "taxonomy").findAll("a"):
            self.story.addToList('category', tagLink.string)

        ## Retrieve chapter soups
        if self.getConfig('find_chapters') == 'guess':
            self.chapterUrls = []
            self._find_chapters_by_guessing(title1)
        else:
            self._find_chapters_by_parsing(soup)

        firstChapterUrl = self.chapterUrls[0][1]
        if firstChapterUrl in self.soupsCache:
            firstChapterSoup = self.soupsCache[firstChapterUrl]
            h1 = firstChapterSoup.find("h1").text
        else:
            h1 = soup.find("h1").text

        h1 = re.sub(_REGEX_CHAPTER_TITLE, "", h1)
        self.story.setMetadata('title', h1)
        self.story.setMetadata('numChapters', len(self.chapterUrls))
        return

    def _find_chapters_by_parsing(self, soup):

        # store original soup
        origSoup = soup

        #
        # find first chapter
        #
        firstLink = None
        firstLinkDiv = soup.find("div", "field-field-erster-teil")
        if firstLinkDiv is not None:
            firstLink = "http://%s%s" % (self.getSiteDomain(), firstLinkDiv.findNext("a")['href'])
            logger.debug("Found first chapter right away <%s>" % firstLink)
            try:
                soup = bs.BeautifulSoup(self._fetchUrl(firstLink))
                self.soupsCache[firstLink] = soup
                self.chapterUrls.insert(0, (soup.find("h1").text, firstLink))
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(self.url)
                else:
                    raise exceptions.StoryDoesNotExist(firstLink)
        else:
            logger.debug("DIDN'T find first chapter right away")
            # parse previous Link until first
            while True:
                prevLink = None
                prevLinkDiv = soup.find("div", "field-field-vorheriger-teil")
                if prevLinkDiv is not None:
                    prevLink = prevLinkDiv.find("a")
                if prevLink is None:
                    prevLink = soup.find("a", text=re.compile("&lt;&lt;&lt;")) # <<<
                if prevLink is None:
                    logger.debug("Couldn't find prev part")
                    break
                else:
                    logger.debug("Previous Chapter <%s>" % prevLink)
                    if type(prevLink) != bs.Tag or prevLink.name != "a":
                        prevLink = prevLink.findParent("a")
                    if prevLink is None or '#' in prevLink['href']:
                        logger.debug("Couldn't find prev part (false positive) <%s>" % prevLink)
                        break
                    prevLink = prevLink['href']
                try:
                    soup = bs.BeautifulSoup(self._fetchUrl(prevLink))
                    self.soupsCache[prevLink] = soup
                    prevTtitle = soup.find("h1", {'class': 'title'}).string
                    self.chapterUrls.insert(0, (prevTtitle, prevLink))
                except urllib2.HTTPError, e:
                    if e.code == 404:
                        raise exceptions.StoryDoesNotExist(nextLink)
                    else:
                        raise e
                firstLink = prevLink

        # if first chapter couldn't be determined, assume the URL originally
        # passed is the first chapter
        if firstLink is None:
            logger.debug("Couldn't set first chapter")
            firstLink = self.url
            self.chapterUrls.insert(0, (soup.find("h1").text, firstLink))

        # set first URL
        logger.debug("Set first link: %s" % firstLink)
        self._setURL(firstLink)
        self.story.setMetadata('storyId', re.compile(self.getSiteURLPattern()).match(firstLink).group('storyId'))

        #
        # Parse next chapters
        #
        while True:
            nextLink = None
            nextLinkDiv = soup.find("div", "field-field-naechster-teil")
            if nextLinkDiv is not None:
                nextLink = nextLinkDiv.find("a")
            if nextLink is None:
                nextLink = soup.find("a", text=re.compile("&gt;&gt;&gt;"))
            if nextLink is None:
                nextLink = soup.find("a", text=re.compile("Fortsetzung"))

            if nextLink is None:
                logger.debug("Couldn't find next part")
                break
            else:
                if type(nextLink) != bs.Tag or nextLink.name != "a":
                    nextLink = nextLink.findParent("a")
                if nextLink is None or '#' in nextLink['href']:
                    logger.debug("Couldn't find next part (false positive) <%s>" % nextLink)
                    break
                nextLink = nextLink['href']

            if not nextLink.startswith('http:'):
                nextLink = 'http://' + self.getSiteDomain() + nextLink

            for loadedChapter in self.chapterUrls:
                if loadedChapter[0] == nextLink:
                    logger.debug("ERROR: Repeating chapter <%s> Try to fix it" % nextLink)
                    nextLinkMatch = _REGEX_TRAILING_DIGIT.match(nextLink)
                    if nextLinkMatch is not None:
                        curChap = nextLinkMatch.group(1)
                        nextLink = re.sub(_REGEX_TRAILING_DIGIT, str(int(curChap) + 1), nextLink)
                    else:
                        break
            try:
                data = self._fetchUrl(nextLink)
                soup = bs.BeautifulSoup(data)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(nextLink)
                else:
                    raise e
            title2 = soup.find("h1", {'class': 'title'}).string
            self.chapterUrls.append((title2, nextLink))
            logger.debug("Grabbing next chapter URL " + nextLink)
            self.soupsCache[nextLink] = soup
            # [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, bs.Comment))]
        logger.debug("Chapters: %s" % self.chapterUrls)


    def _find_chapters_by_guessing(self, title1):
        step = _INITIAL_STEP
        curMax = self.maxChapter + step
        lastHit = True
        while True:
            nextChapterUrl = re.sub(_REGEX_TRAILING_DIGIT, str(curMax), self.url) 
            if nextChapterUrl == self.url:
                logger.debug("Unable to guess next chapter because URL doesn't end in numbers")
                break;
            try:
                logger.debug("Trying chapter URL " + nextChapterUrl)
                data = self._fetchUrl(nextChapterUrl)
                hit = True
            except urllib2.HTTPError, e:
                if e.code == 404:
                    hit = False
                else:
                    raise e
            if hit:
                logger.debug("Found chapter URL " + nextChapterUrl)
                self.maxChapter = curMax
                self.soupsCache[nextChapterUrl] = bs.BeautifulSoup(data)
                if not lastHit:
                    break
                lastHit = curMax
                curMax += step
            else:
                lastHit = False
                curMax -= 1
            logger.debug(curMax)

        for i in xrange(1, self.maxChapter):
            nextChapterUrl = re.sub(_REGEX_TRAILING_DIGIT, str(i), self.url)
            nextChapterTitle = re.sub("1", str(i), title1)
            self.chapterUrls.append((nextChapterTitle, nextChapterUrl))

    def getChapterText(self, url):

        if url in self.soupsCache:
            logger.debug('Getting chapter <%s> from cache' % url)
            soup = self.soupsCache[url]
        else:
            logger.debug('Downloading chapter <%s>' % url)
            data1 = self._fetchUrl(url)
            soup = bs.BeautifulSoup(data1)
            #strip comments from soup
            [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # get story text
        storyDiv1 = bs.Tag(soup, "div")
        for para in soup.find("div", "full-node").find('div', 'content').findAll("p"):
            storyDiv1.append(para)
        storyDiv1.append('<br />')
        storytext = self.utf8FromSoup(url,storyDiv1)

        return storytext


def getClass():
    return BdsmGeschichtenAdapter
