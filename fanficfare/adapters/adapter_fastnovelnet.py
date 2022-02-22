# -*- coding: utf-8 -*-
# Copyright 2018 FanFicFare team
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
####################################################################################################
### Adapted by Rikkit on November 7. 2017
###=================================================================================================
### Tested with Calibre
####################################################################################################

from __future__ import absolute_import
import logging
import re
# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter, makeDate

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)

def getClass():
    ''' Initializing the class '''
    return FastNovelNetAdapter

class FastNovelNetAdapter(BaseSiteAdapter):
    ''' Adapter for FASTNOVEL.net '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'fstnvl')

        self.dateformat = '%d/%m/%Y'

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/%s/' % (self.getSiteDomain(), story_id))


    @staticmethod
    def getSiteDomain():
        return 'fastnovel.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://fastnovel.net/a-story-name-id"

    def getSiteURLPattern(self):
        # https://fastnovel.net/ultimate-scheming-system-158/
        return r"https?://fastnovel\.net/(?P<id>[^/]+)"

    ## Normalized chapter URLs by changing old titlenum part to be
    ## same as storyId.
    def normalize_chapterurl(self,url):
        # https://fastnovel.net/cultivation-chat-group8-29/chapter-25206.html
        return re.sub(r"\.net/.*(?P<keep>/chapter-\d+.html)",
                      r".net/"+self.story.getMetadata('storyId')+r"\g<keep>",url)

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        (data,rurl) = self.get_request_redirected(self.url)
        if rurl != self.url:
            match = re.match(self.getSiteURLPattern(), rurl)
            if not match:
                ## shouldn't happen, but in case it does...
                raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

            story_id = match.group('id')
            self.story.setMetadata('storyId', story_id)
            self._setURL('https://%s/%s/' % (self.getSiteDomain(), story_id))
            logger.debug("set to redirected url:%s"%self.url)

        soup = self.make_soup(data)

        self.story.setMetadata('title', soup.find('h1').string)

        for li in soup.select('.meta-data li'):
            label = li.select_one('label')
            if not label:
                continue

            if label.string == "Author:":
                for a in li.select('a'):
                    self.story.setMetadata('authorId', a["href"].split('/')[2])
                    self.story.setMetadata('authorUrl','https://'+self.host+a["href"])
                    self.story.setMetadata('author', a["title"])

            if label.string == "Genre:":
                for a in li.select('a'):
                    self.story.addToList('genre',a["title"])

            if label.string == "Status:":
                if li.select_one('strong').string.strip() == "Completed":
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if label.string == "Last updated:":
                dateUpd = label.next_sibling.strip()
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(dateUpd), self.dateformat))

        coverurl = soup.select_one('div.book-cover')["data-original"]
        if coverurl != "https://fastnovel.net/images/novel/default.jpg":
            self.setCoverImage(self.url, coverurl)

        tags = soup.select_one('.tags')
        if tags:
            for a in tags.select("li.tag-item a"):
                self.story.addToList('tags', a["title"])
            # extract tags, because it inside description
            tags.extract()

        # remove title from description
        soup.select_one('.film-content h3').extract()
        desc = soup.select_one('.film-content').extract()
        self.setDescription(self.url, desc)

        for book in soup.select("#list-chapters .book"):
            volume = book.select_one('.title a').string
            for a in book.select(".list-chapters a.chapter"):
                title = volume + " " + stripHTML(a)
                self.add_chapter(title, 'https://' + self.host + a["href"])

    def getChapterText(self, url):
        data = self.get_request(url)
        soup = self.make_soup(data)

        story = soup.select_one('#chapter-body')
        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, story)
