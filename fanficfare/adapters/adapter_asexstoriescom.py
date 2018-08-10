# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2018 FanFicFare team
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

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
import os

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions
import sys

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return ASexStoriesComAdapter

class ASexStoriesComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev','asscom')

        # Extract story ID from base URL, http://www.asexstories.com/Halloween-party-with-the-phantom/
        storyId = self.parsedUrl.path.split('/',)[1]
        self.story.setMetadata('storyId', storyId)

        ## set url
        self._setURL(url)

    @staticmethod
    def getSiteDomain():
        return 'www.asexstories.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.asexstories.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.asexstories.com/StoryTitle/"

    def getSiteURLPattern(self):
        return r"https?://(www\.)?asexstories\.com/([a-zA-Z0-9_-]+)/"

    def extractChapterUrlsAndMetadata(self):
        """
        Chapters are located at /StoryName/  (for single-chapter
        stories), or //StoryName/index#.html for multiple chapters (# is a
        non-padded incrementing number, like StoryName1, StoryName2.html, ...,
        StoryName10.html)

        This site doesn't have much in the way of metadata, except on the 
        Category and Tags index pages. so we will get what we can.
        
        Also, as this is an Adult site, the is_adult check is mandatory.
        """

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        try:
            data1 = self._fetchUrl(self.url)
            soup1 = self.make_soup(data1)
            #strip comments from soup
            [comment.extract() for comment in soup1.find_all(text=lambda text:isinstance(text, Comment))]
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if 'Page Not Found.' in data1:
            raise exceptions.StoryDoesNotExist(self.url)

        url = self.url

        # Extract metadata
        # Title
        title = soup1.find('div',{'class':'story-top-block'}).find('h1')
        self.story.setMetadata('title', title.string)

        # Author
        author = soup1.find('div',{'class':'story-info'}).findAll('div',{'class':'story-info-bl'})[1].find('a')
        authorurl = author['href']
        self.story.setMetadata('author', author.string)
        self.story.setMetadata('authorUrl', authorurl)
        authorid = os.path.splitext(os.path.basename(authorurl))[0]
        self.story.setMetadata('authorId', authorid)

        # Description
        ### The only way to get the Description (summary) is to 
        ### parse through the Category and/or Tags index pages.
        ### To get a summary, I've taken the first 150 characters
        ### from the story.
        description = soup1.find('div',{'class':'story-block'}).get_text(strip=True)
        description = description.encode('utf-8','ignore').strip()[0:150].decode('utf-8','ignore')
        self.setDescription(url,'Excerpt from beginning of story: '+description+'...')
        
        ### The first 'chapter' is not listed in the links, so we have to
        ### add it before the rest of the pages, if any
        self.add_chapter('1', self.url)

        chapterTable = soup1.find('div',{'class':'pages'}).findAll('a')

        if chapterTable is not None:
            # Multi-chapter story
            
            for page in chapterTable:
                chapterTitle = page.string
                chapterUrl = urlparse.urljoin(self.url, page['href'])
                if chapterUrl.startswith(self.url): # there are other URLs in the pages block now.
                    self.add_chapter(chapterTitle, chapterUrl)


        rated = soup1.find('div',{'class':'story-info'}).findAll('div',{'class':'story-info-bl5'})[0].find('img')['title'].replace('- Rate','').strip()
        self.story.setMetadata('rating',rated)
        
        self.story.setMetadata('dateUpdated', makeDate('01/01/2001', '%m/%d/%Y'))
        
        logger.debug("Story: <%s>", self.story)

        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)
        #logger.info('Getting chapter text from <%s>' % url)

        data1 = self._fetchUrl(url)
        soup1 = self.make_soup(data1)

        # get story text
        story1 = soup1.find('div', {'class':'story-block'})
        
        ### This site has links embeded in the text that lead 
        ### to either a video site, or to a tags index page
        ### the default is to remove them, but you can set the 
        ### strip_text_links to false to keep them in the text
        if self.getConfig('strip_text_links'):
            for anchor in story1('a', {'target': '_blank'}):
                anchor.replaceWith(anchor.string)
            ## remove ad links in the story text and their following <br>
            for anchor in story1('a', {'rel': 'nofollow'}):
                br = anchor.find_next_sibling('br')
                if br:
                    br.extract()
                anchor.extract()

        return self.utf8FromSoup(url, story1)
