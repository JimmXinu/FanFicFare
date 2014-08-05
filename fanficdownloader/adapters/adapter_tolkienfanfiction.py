# -*- coding: utf-8 -*-

"""
FFDL Adapter for TolkienFanFiction.com.

Chapter URL: http://www.tolkienfanfiction.com/Story_Read_Chapter.php?CHid=1234
    Metadata
        Link to Story URL [Index]
        chapterTitle
        storyTitle
Story URL: http://www.tolkienfanfiction.com/Story_Read_Head.php?STid=1034
    Metadata
        Links to Chapter URLs
        storyTitle
        chapterTitle[s]
        author
        authorId
        authorUrl
        numChapters
        wordCount
        description/summary
        rating TODO
        genre TODO
        Characters
        Ages (specific) TODO
Search: http://www.tolkienfanfiction.com/Story_Chapter_Search.php?text=From+Wilderness+to+Cities+White&field=1&type=3&search=Search
    Strategy
        Search by exact phrase for styo
    Metadata
        dateUpdated
    Parameters
        field (field to search)
            1: title
            2: description
            3: chapter text
        type (any, all or exact phrase)
            1: any
            2: all
            3: exact phrase

"""
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
import urllib
import urllib2
import urlparse
import string

from .. import BeautifulSoup as bs
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

def _is_story_url(url):
    return "Story_Read_Head.php" in url

def _latinize(text):
    """
    See http://stackoverflow.com/a/19114706/201318
    """
    src = u"áâäÉéêëíóôöúû"
    tgt = u"aaaEeeeiooouu"
    src_ord = [ord(char) for char in src]
    translate_table = dict(zip(src_ord, tgt))
    return text.translate(translate_table)

def _fix_broken_markup(html):
    """Replaces invalid comment tags"""
    if html.startswith("<CENTER>"):
        logger.error("TolkienFanFiction.com couldn't handle this request: '%s'" % html)
    html = re.sub("<!-.+?->", "", html)
    return html


class TolkienFanfictionAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["ISO-8859-1", "Windows-1252"] 

        self.story.setMetadata('siteabbrev','tolkien')

        self.dateformat = '%B %d, %Y'

        self._normalizeURL(url)

    def _normalizeURL(self, url):
        if _is_story_url(url):
            self.story.setMetadata('storyId', re.compile(self.getSiteURLPattern()).match(url).group('storyId'))
            self._setURL('http://' + self.getSiteDomain() + '/Story_Read_Head.php?STid=' + self.story.getMetadata('storyId'))

    @staticmethod
    def getSiteDomain():
        return 'tolkienfanfiction.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['tolkienfanfiction.com', 'www.tolkienfanfiction.com']

    @classmethod
    def getSiteExampleURLs(self):
        return 'http://www.tolkienfanfiction.com/Story_Read_Head.php?STid=1034 http://www.tolkienfanfiction.com/Story_Read_Chapter.php?CHid=4945'

    def getSiteURLPattern(self):
        return r"http://(?:www.)?tolkienfanfiction.com/(?:Story_Read_Chapter\.php\?CH|Story_Read_Head\.php\?ST)id=(?P<storyId>[0-9]+)"

    def extractChapterUrlsAndMetadata(self):

        if not _is_story_url(self.url):
            # Get the link to the index page
            try:
                chapterHtml = _fix_broken_markup(self._fetchUrl(self.url))
                chapterSoup = bs.BeautifulSoup(chapterHtml)
                indexLink = chapterSoup.find("a", text="[Index]").parent
                self._normalizeURL('http://' + self.host + '/' + indexLink.get('href'))
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(self.url)
                else:
                    raise e
        logger.debug("Determined index page: <%s>" % self.url)

        try:
            indexHtml = _fix_broken_markup(self._fetchUrl(self.url))
            soup = bs.BeautifulSoup(indexHtml)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # chapterUrls
        for pfLink in soup.findAll("a", text='[PF] '):
            chapterLink = pfLink.parent.findNext("a")
            chapterTitle = chapterLink.string
            if self.getConfig('strip_chapter_numeral'):
                chapterTitle = re.sub("^\d+:", "", chapterTitle)
            chapterUrl = 'http://' + self.host + '/' + chapterLink['href']
            self.chapterUrls.append((chapterTitle, chapterUrl))
            numChapters = len(self.chapterUrls)
            self.story.setMetadata('numChapters', numChapters)
        logger.debug('Number of Chapters: %s' % numChapters)

        # title
        title = soup.find("table", "headertitle").find("tr").contents[1].string
        logger.debug("Title: '%s'" % title)
        self.story.setMetadata('title', title)

        # author
        authorLink = soup.find("a", {"href":lambda x: x.startswith("Author_Profile.php")})
        authorName = authorLink.find("b").string
        authorHref = authorLink['href']
        authorUrl = 'http:' + self.host + '/' + authorHref
        authorId = authorHref[authorHref.index('=')+1:]
        self.story.setMetadata('author', authorName)
        self.story.setMetadata('authorId', authorId)
        self.story.setMetadata('authorUrl', authorUrl)
        logger.debug("Author: %s [%s] @ <%s>" % (authorId, authorName, authorUrl))

        # numWords
        numWordsMatch = re.search("Word Count: (\d+)<BR>", indexHtml)
        if numWordsMatch:
            numWords = numWordsMatch.group(1)
            logger.debug('Number of words: %s' % numWords)
            self.story.setMetadata('numWords', numWords)

        # description
        description = soup.find("b", text="Description:").parent.nextSibling.nextSibling
        self.story.setDescription(description)
        logger.debug("Summary: '%s'" % description)

        # characters
        characters = soup.find("b", text="Characters").parent.nextSibling.nextSibling.nextSibling
        for character in characters.split(", "):
            self.story.addToList('characters', character)
        logger.debug("Characters: %s" % self.story.getMetadata('characters'))

        logger.debug('Title as `str`: ' + str(title))
        # For publication date we need to search
        try:
            queryString = urllib.urlencode((
                ('type', 3),
                ('field', 1),
                # need translate here for the weird accented letters
                ('text', _latinize(title)),
                ('search', 'Search'),
            ))
            searchUrl = 'http://%s/Story_Chapter_Search.php?%s' % (self.host, queryString)
            logger.debug("Search URL: <%s>" % searchUrl)
            searchHtml = _fix_broken_markup(self._fetchUrl(searchUrl))
            searchSoup = bs.BeautifulSoup(searchHtml)
            date = searchSoup.find(text="Updated:").nextSibling.string
            logger.debug("Last Updated: '%s'" % date)
            self.story.setMetadata('dateUpdated', makeDate(date, self.dateformat))
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

    def getChapterText(self, url):

        logger.debug('Downloading chapter <%s>' % url)

        time.sleep(0.5)
        htmldata = _fix_broken_markup(self._fetchUrl(url))
        soup = bs.BeautifulSoup(htmldata)

        #strip comments from soup
        [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # Strip redundant headings
        [font.parent.extract() for font in soup.findAll("font", {"size": "4"})]

        # get story text
        textDiv = soup.find("div", "text")
        return self.utf8FromSoup(url, textDiv)

def getClass():
    return TolkienFanfictionAdapter
