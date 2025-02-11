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
from bs4.element import Comment

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions

logger = logging.getLogger(__name__)

def getClass():
    return WWWAnEroticStoryComAdapter

class WWWAnEroticStoryComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        # 1252 is a superset of iso-8859-1. Most sites that claim to be iso-8859-1 (and some that
        # claim to be utf8) are really windows-1252.
        self.decode = ["utf8", "Windows-1252", "iso-8859-1"] 

        self.story.setMetadata('siteabbrev','aescom')

        # Extract story ID from base URL, https://www.aneroticstory.com/story/565-daddy-explores-jessica
        storyId = self.parsedUrl.path.split('/')[2]
        self.story.setMetadata('storyId', storyId)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

        ## set url
        self._setURL(url)

        ## This is a 1 page/1 story site, so I'll be setting the html here
        self.html = ""

    @staticmethod
    def getSiteDomain():
        return 'www.aneroticstory.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.aneroticstory.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.aneroticstory.com/story/StoryTitle/"

    def getSiteURLPattern(self):
        return r"https?://(www\.)?aneroticstory\.com/story/([a-zA-Z0-9_\-%;=:\s]+)"

    def extractChapterUrlsAndMetadata(self):
        """
        Chapters are located at /story/StoryName/  (for single-chapter stories)

        This site doesn't have much in the way of metadata, except on the 
        Genre . so we will get what we can.
        
        Also, as this is an Adult site, the is_adult check is mandatory.
        """

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        data1 = self.get_request(self.url)
        soup1 = self.make_soup(data1)
        #strip comments and scripts from soup
        [comment.extract() for comment in soup1.find_all(string=lambda text:isinstance(text, Comment))]
        [script.extract() for script in soup1.find_all('script')]

        url = self.url

        # Extract metadata
        # Title
        title = soup1.select_one('h1.tit').text.title()
        self.story.setMetadata('title', title)

        # Author
        author = soup1.select_one('a[rel="author"]')
        authorurl = 'https://' + self.getSiteDomain() + author['href']
        self.story.setMetadata('author', author.text)
        self.story.setMetadata('authorUrl', authorurl)
        authorid = authorurl.split('/')[-2]
        self.story.setMetadata('authorId', authorid)

        # Description
        ### There is no summary for this site, s I will be taking the first 350 characters
        ### from the text of the story.
        description = soup1.find('div',{'class':'tes'}).get_text(strip=True)
        description = description.encode('utf-8','ignore').strip()[0:350].decode('utf-8','ignore')+'...'
        self.setDescription(url,'Excerpt from beginning of story: '+description+'...')
        
        ### This is a 1 page/ 1 story site, so the only chapterurl is the current story
        self.add_chapter('1', self.url)

        # Setting the status to complete
        self.story.setMetadata('status', 'Completed')

        ## Getting the date Posted and setting the Published and Updated metadata
        datePosted = soup1.select('div.infos strong')[1].text.strip()
        self.story.setMetadata('datePublished', makeDate(datePosted, self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(datePosted, self.dateformat))
        
        ## Getting the Genre
        genre = soup1.select_one('div.story a[href^="/genres/"]').text.strip().title()
        self.story.setMetadata('genre', genre)

        logger.debug("Story: <%s>", self.story)

        ## setting the html up for the getChapterText function
        self.html = soup1

        return

    def getChapterText(self, url):
        logger.debug('Using the HTML retrieved from <%s>' % url)

        soup1 = self.html

        # get story text
        story1 = soup1.find('div', {'class':'tes'})

        if not story1:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, story1)
