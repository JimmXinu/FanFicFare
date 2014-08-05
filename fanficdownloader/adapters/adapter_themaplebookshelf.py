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

import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate


class TheMapleBookshelfComSiteAdapter(BaseSiteAdapter):
    """
    Use Printable version which is easier to parse and has everything in one
    page and cache between extractChapterUrlsAndMetadata and getChapterText
    """

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','maplebook')
        self.decode = ["Windows-1252", "utf8"]
        self.story.setMetadata('storyId', re.compile(self.getSiteURLPattern()).match(url).group('storyId'))
        self.dateformat = "%b %d, %Y"

    @staticmethod
    def getSiteDomain():
        return 'themaplebookshelf.com'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://www.themaplebookshelf.com/Literati/viewstory.php?sid=227 http://themaplebookshelf.com/Literati/viewstory.php?sid=227&chapter=2"

    def getSiteURLPattern(self):
        return r"http://themaplebookshelf.com/Literati/viewstory.php\?sid=(?P<storyId>\d+)"

    def extractChapterUrlsAndMetadata(self):
        logger.debug(self.url)
        self._setURL(self.url + "&action=printable")
        try:
            html = self._fetchUrl(self.url)
            soup = bs.BeautifulSoup(html)
            # #strip comments from soup
            # [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, bs.Comment))]
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        ## title + author
        pagetitleDiv = soup.find("div", {"id": "pagetitle"})
        self.story.setMetadata('title', pagetitleDiv.find("a").text)
        authorLink = pagetitleDiv.findAll("a")[1]
        self.story.setMetadata('author', authorLink.text)
        self.story.setMetadata('authorUrl', "http://" + self.getSiteDomain() + "/" + authorLink['href'])
        self.story.setMetadata('authorId', re.search("\d+", authorLink['href']).group(0))

        ## Description
        description = ""
        summaryEnd = soup.find("div", "content").find("span", "label").nextSibling
        while summaryEnd is not None:
            description += stripHTML(summaryEnd)
            summaryEnd = summaryEnd.nextSibling
            if type(summaryEnd) != bs.NavigableString and summaryEnd.name == 'br':
                break
        self.story.setMetadata('description', description)

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
                self.story.setMetadata('datePublished', makeDate(v, self.dateformat))
            elif k == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(v, self.dateformat))
            # TODO: Series, Warnings

        ## Chapter URLs (fragment identifiers in the document, so we don' need to fetch so much)
        for chapterNumB in soup.findAll("b", text=re.compile("^\d+\.$")):
            self.chapterUrls.append((
                chapterNumB.parent.parent.find("a").text,
                self.url + chapterNumB.parent.parent.find("a")["href"]
                ))

        ## fix all local image 'src' to absolute
        for img in soup.findAll("img", {"src": re.compile("^(?!http)")}):
            img['src'] = re.sub("viewstory.php\?.*", "", self.url) + img['src']

        self.html = soup

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)
        anchor = url.replace(self.url, "")
        anchor = anchor.replace("#", "")
        chapterDiv = self.html.find("a", {"name": anchor}).parent.findNext("div", "chapter")
        return self.utf8FromSoup(self.url, chapterDiv)

def getClass():
    return TheMapleBookshelfComSiteAdapter
