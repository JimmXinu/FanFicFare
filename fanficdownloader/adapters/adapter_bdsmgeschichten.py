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

class BdsmGeschichtenAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8", "Windows-1252"]

        self.story.setMetadata('siteabbrev','bdsmgesch')

        # Replace possible chapter numbering
        url = re.sub("-\d+$", "-1", url)

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
        return ["http://www.bdsm-geschichten.net/title-of-story-1", "http://bdsm-geschichten.net/title-of-story-1"]

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
        storyTitle = re.sub(" Teil .*$", "", title1)
        self.chapterUrls = [(title1, self.url)]
        self.story.setMetadata('title', storyTitle)

        for tagLink in soup.find("ul", "taxonomy").findAll("a"):
            self.story.addToList('category', tagLink.string)

        ## Retrieve chapter soups
        nextLinkDiv = soup.find("div", "field-field-naechster-teil")
        while nextLinkDiv is not None:
            nextLink = 'http://' + self.getSiteDomain() + nextLinkDiv.find("a")['href']
            try:
                logger.debug("Grabbing next chapter URL " + nextLink)
                data2 = self._fetchUrl(nextLink)
                soup2 = bs.BeautifulSoup(data2)
                self.soupsCache[nextLink] = soup2
                [comment.extract() for comment in soup2.findAll(text=lambda text:isinstance(text, bs.Comment))]
                nextLinkDiv = soup2.find("div", "field-field-naechster-teil")
                title2 = soup2.find("h1", {'class': 'title'}).string
                self.chapterUrls.append((title2, nextLink))
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(nextLink)
                else:
                    raise e

        self.story.setMetadata('numChapters', len(self.chapterUrls))
        return

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
