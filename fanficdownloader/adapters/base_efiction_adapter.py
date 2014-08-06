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

# import time
# import urllib
import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

"""
This is a generic adapter for eFiction based archives (see
http://fanlore.org/wiki/List_of_eFiction_Archives for a list).

Most of them share common traits:
    * No HTTPS
    * 'www.' is optional
    * Default story template is 'viewstory.php' with arguments
        * 'sid' the storyId
        * 'chapter' for chapters (will be thrown away anyway by
           stripURLParameters in base_adapter
    Use Printable version which is easier to parse and has everything in one
    page and cache between extractChapterUrlsAndMetadata and getChapterText
"""


class BaseEfictionAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev',self.getSiteAbbrev())
        self.decode = ["Windows-1252", "utf8"]
        storyId = re.compile(self.getSiteURLPattern()).match(self.url).group('storyId')
        self.story.setMetadata('storyId', storyId)
        self._setURL(self.getStoryUrl(storyId))

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),'www.' + cls.getSiteDomain()]

    @classmethod
    def getSiteExampleURLs(self):
        return getStoryUrl('1234') + ' ' + getStoryUrl('1234') + '&chapter=2'

    def getDateFormat(self):
        return "%d %b %Y"

    def getPathToArchive(cls):
        return "/"

    def getViewStoryPhpName(cls):
        return "viewstory.php"

    def getViewUserPhpName(cls):
        return "viewuser.php"

    def getStoryUrl(self, storyId):
        return "http://%s%s/%s?sid=%s" % (
            self.getSiteDomain(),
            self.getPathToArchive(),
            self.getViewStoryPhpName(),
            storyId)

    def getUserUrl(self, userId):
        return "http://%s%s/%s?uid=%s" % (
            self.getSiteDomain(),
            self.getPathToArchive(),
            self.getViewUserPhpName(),
            userId)

    def getSiteURLPattern(self):
        return r"http://(www\.)?%s%s/%s\?sid=(?P<storyId>\d+)" % (self.getSiteDomain(), self.getPathToArchive(), self.getViewStoryPhpName())

    def _fetch_to_soup(self, url):
        """Replaces invalid comment tags and parses to BeautifulSoup"""
        try:
            html = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        html = re.sub("<!-.+?->", "", html)
        html = re.sub("<meta[^<>]+>(.*</meta>)?", "", html)
        return bs.BeautifulSoup(html)

    def confirmWarnings(self, relLink):
# TODO check whether user is_adult
        absLink = "http://%s%s/%s" % (self.getSiteDomain(), self.getPathToArchive(), relLink)
        logger.debug('Confirm warnings <%s>' % (absLink))
        self._fetchUrl(absLink)

    def extractChapterUrlsAndMetadata(self):
        printUrl = self.url + '&action=printable&chapter=all&textsize=0'
        soup = self._fetch_to_soup(printUrl)

        ## Handle warnings
        errorDiv = soup.find("div", "errortext")
        if errorDiv is not None:
            warningLink = errorDiv.find("a", {"href": re.compile(".*warning=.*")})
            if warningLink is not None:
                self.confirmWarnings(warningLink['href'])
                soup = self._fetch_to_soup(printUrl)
                errorDiv = soup.find("div", "errortext")
                if errorDiv is not None:
                    raise exceptions.FailedToDownload(errorDiv.text)
            else:
                raise exceptions.FailedToDownload(errorDiv.text)

        # title and author
        pagetitleDiv = soup.find("div", {"id": "pagetitle"})
        if pagetitleDiv.find('a') is None:
            logger.debug(html)
            logger.debug(soup)
            raise execeptions.FailedToDownload()
        self.story.setMetadata('title', pagetitleDiv.find("a").text)
        authorLink = pagetitleDiv.findAll("a")[1]
        self.story.setMetadata('author', authorLink.text)
        self.story.setMetadata('authorId', re.search("\d+", authorLink['href']).group(0))
        self.story.setMetadata('authorUrl', self.getUserUrl(self.story.getMetadata('authorId')))

        ## Description
        description = ""
        summaryEnd = soup.find("div", "content").find("span", "label").nextSibling
        while summaryEnd is not None:
            description += summaryEnd
            summaryEnd = summaryEnd.nextSibling
            if type(summaryEnd) != bs.NavigableString and summaryEnd.name == 'br':
                break
        self.setDescription(self.url, description)

        ## General Metadata
        for kSpan in soup.findAll("span", "label"):
            k = kSpan.text.strip().replace(':', '')
            vSpan = kSpan.nextSibling
            if k == 'Summary:' or not vSpan or not vSpan.string:
                continue
            v = vSpan.string.strip()
            if v == 'None':
                continue
            logger.debug("%s '%s'" %(k, v))
            if k == 'Genre':
                for genre in v.split(", "):
                    self.story.addToList('genre', genre)
            elif k == 'Chapters':
                self.story.setMetadata('numChapters', int(v))
            elif k == 'Word count':
                self.story.setMetadata('numWords', v)
            elif k == 'Published':
                self.story.setMetadata('datePublished', makeDate(v, self.getDateFormat()))
            elif k == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(v, self.getDateFormat()))
            # TODO: Series, Warnings

        ## fix all local image 'src' to absolute
        for img in soup.findAll("img", {"src": re.compile("^(?!http)")}):
            if img['src'].startswith('/'):
                img['src'] = img['src'][1:]
            img['src'] = "http://%s%s/%s" % (self.getSiteDomain(), self.getPathToArchive(), img['src'])

        ## Chapter URLs (fragment identifiers in the document, so we don' need to fetch so much)
        for chapterNumB in soup.findAll("b", text=re.compile("^\d+\.$")):
            self.chapterUrls.append((
                chapterNumB.parent.parent.find("a").text,
                self.url + chapterNumB.parent.parent.find("a")["href"]
                ))

        ## Store reference to soup for getChapterText
        self.html = soup

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)
        anchor = url.replace(self.url, "")
        anchor = anchor.replace("#", "")
        chapterDiv = self.html.find("a", {"name": anchor}).parent.findNext("div", "chapter")
        return self.utf8FromSoup(self.url, chapterDiv)

def getClass():
    return BaseEfictionAdapter
