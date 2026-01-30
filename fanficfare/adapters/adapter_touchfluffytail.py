# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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
from datetime import datetime
import logging
import re
logger = logging.getLogger(__name__)

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter

def getClass():
    return TouchFluffyTailAdapter

logger = logging.getLogger(__name__)

class TouchFluffyTailAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev','tft')
        self.story.setMetadata('language','English')
        self.dateformat = "%d-%m-%Y %H:%M:%S"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'touchfluffytail.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/story/title-of-the-book/"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain())+"/story/"+r"(?!page/)\S+"+"/"

    def extractChapterUrlsAndMetadata(self,get_cover=True):
        url=self.url
        logger.debug("URL: "+url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        # This ID seems to be unique to every story
        body = soup.find('article', id=re.compile(r'^post-'))
        self.story.setMetadata('storyId', body.get("id")[5:])

        # Title
        title = soup.find('h1', {'class':'entry-title'})
        self.story.setMetadata('title',stripHTML(title))
        logger.debug("Title: (%s)"%self.story.getMetadata('title'))

        # Story tags
        tags = body.find('span', {'class':'tag-links'})
        for tag in tags.find_all('a'):
            self.story.addToList('genre', stripHTML(tag))
        #logger.debug("Genre: (%s)"%self.story.getMetadata('genre'))

        # Couldn't find better author id. Assuming that it is unique
        author = body.find('a',{'rel':'author'})
        self.story.setMetadata('author', author.text)
        self.story.setMetadata('authorId', author.text)
        self.story.setMetadata('authorUrl', author['href'])
        #logger.debug("Author: (%s)"%self.story.getMetadata('author'))
        logger.debug("AuthorId: (%s)"%self.story.getMetadata('authorId'))
        #logger.debug("AuthorUrl: (%s)"%self.story.getMetadata('authorUrl'))

        # Published time
        published_time = body.find('time', {'class':'published'})['datetime']
        published = datetime.fromisoformat(published_time)
        self.story.setMetadata('datePublished', published)
        logger.debug("Date Published: (%s)"%self.story.getMetadata('datePublished'))

        # Updated time
        updated_time = body.find('time', {'class':'updated'})['datetime']
        updated = datetime.fromisoformat(updated_time)
        self.story.setMetadata('dateUpdated', updated)
        logger.debug("Date Updated: (%s)"%self.story.getMetadata('dateUpdated'))

        # The site only host content around this topic but. Is this proper category?
        self.story.addToList('category', "The Monstergirl")

        self.story.setMetadata('status', 'Completed')
        self.add_chapter(self.story.getMetadata('title'),url)

        avrrate = body.find_all('footer', class_='entry-meta')[1].find('em').span.find_all('strong')
        averrating = avrrate[1].text
        votes = avrrate[0].text
        self.story.setMetadata('averrating', float(averrating))
        self.story.setMetadata('reviews', int(votes))
        logger.debug("Averrating: (%s)"%self.story.getMetadata('averrating'))
        logger.debug("Votes: (%s)"%self.story.getMetadata('reviews'))
        
        views = re.search(r'</div>(\d+) Views\s+</div>', str(body)).group(1)
        self.story.setMetadata('views', views)
        logger.debug('Views: (%s)'%self.story.getMetadata('views'))

        comments = body.find('span', {'class':'comments-count'})
        self.story.setMetadata('comments', int(stripHTML(comments)))
        logger.debug('Comments (%s)'%self.story.getMetadata('comments'))

        if get_cover:
            try:
                cover = soup.find('div', {'id':"wp-custom-header"}).img['src']
                self.setCoverImage(url,cover)
            except:
                pass
                #logger.debug("No cover found in: %s"%url)

        
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))

        # Getting the chapter
        chapter = soup.find('article', id=re.compile(r'^post-')).find('div', {'class':'entry-content'})

        # The chapter div has rating included in it, this should remove it.
        for element in chapter.find_all('div', class_='post-ratings'):
            element.decompose()
        for element in chapter.find_all('div', class_='post-ratings-loading'):
            element.decompose()
        # The views counter is outside of the ratings but still in the chapter with no tags to match.
        views_element = chapter.find(text=re.compile(r'\d+ Views'))
        if views_element:
            views_element.extract()

        if not chapter.contents:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)

        return self.utf8FromSoup(url,chapter)
