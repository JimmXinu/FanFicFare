# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2025 FanFicFare team
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

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from .base_adapter import BaseSiteAdapter, makeDate

def getClass():
    return PMDFanFictionComSiteAdapter

class PMDFanFictionComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/')[2])
        self._setURL('https://'+self.getSiteDomain()+'/story/'+self.story.getMetadata('storyId')+'/')
        self.is_adult=False
        self.dateformat = "%B %d, %Y"

    @staticmethod
    def getSiteDomain():
        return "www.pmdfanfiction.com"
    
    @classmethod
    def getAcceptDomain(cls):
        return ['www.pmdfanfiction.com']
    
    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://www.pmdfanfiction.com/story/story-title-here'

    @classmethod
    def getSiteAbbrev(cls):
        return 'pmdff'
    
    def getSiteURLPattern(self):
        return r"https?://(www\.)?pmdfanfiction\.(com)/story/.*"
    
    def extractChapterUrlsAndMetadata(self, get_cover=True):

        data = self.get_request(self.url)
        soup = self.make_soup(data)

        # Extract metadata
        storyContent = soup.find('article', {'class', 'story__article'})

        # Title
        title = storyContent.find('h1', {'class': 'story__identity-title'})
        self.story.setMetadata('title', stripHTML(title))

        # Author
        author = storyContent.find('a', {'class': 'author'})
        self.story.setMetadata('author', stripHTML(author))
        self.story.setMetadata('authorId', author['href'].rstrip('/').split('/')[-1])
        self.story.setMetadata('authorUrl', author['href'])

        # Chapters
        # Because PMDFF allows chapters to be grouped into sections, we need to grab all the chapter groups and 
        # then iterate through each chapter in each group to get the chapter URLs.
        for chapter_group in soup.find_all('ol', {'class': 'chapter-group__list'}):
            for chapter in chapter_group.find_all('a', {'class': 'chapter-group__list-item-link'}):
                self.add_chapter(chapter, chapter['href'])

        # Status
        # For PMDFF, possible statuses are Completed, Ongoing, Oneshot, Hiatus, and Canceled
        # To align with other adapters, 'Ongoing' becomes 'In-Progress', and 'Oneshot' becomes
        # 'Completed'. 'Hiatus' is passed through.
        status = storyContent.find('span', {'class': 'story__status'})
        if status is not None:
            status = stripHTML(status)
            status = status.replace('Ongoing', 'In-Progress').replace('Oneshot', 'Completed')
            self.story.setMetadata('status', status)

        #Rating
        rating = storyContent.find('span', {'class': 'story__rating'})
        if rating is not None:
            self.story.setMetadata('rating', stripHTML(rating))

        # Cover Image
        if get_cover:
            storyImage = soup.find('img', {'class': 'story__thumbnail-image'})
            if storyImage:
                coverurl = storyImage['data-src']
                self.setCoverImage(self.url, coverurl)

        # Description
        description = storyContent.find('section', {'class': 'story__summary'})
        if description is not None:
            description_str = u"%s"%description
            self.setDescription(self.url, description_str)

        # Chapter Dates
        storyData = storyContent.find('ol', {'class': 'chapter-group__list'})
        oldestChapter = None
        newestChapter = None
        self.newestChapterNum = None # Do this for comparing during updates
        # Iterate all chapters to find the oldest and newest ones
        if storyData is not None:
            for index, chapterDate in enumerate(storyData.find_all('time', {'class': 'chapter-group__list-item-date'})):
                chapterDate = stripHTML(chapterDate.find('span', {'class': 'list-view'}))
                chapterDate = makeDate(chapterDate, self.dateformat)
                if oldestChapter == None or chapterDate < oldestChapter:
                    oldestChapter = chapterDate
                if newestChapter == None or chapterDate > newestChapter:
                    newestChapter = chapterDate
                    self.newestChapterNum = index

        # Date Updated
        self.story.setMetadata('dateUpdated', newestChapter)

        # Date Published
        # Will use oldest chapter date if story doesn't have an official published date
        publish_date = storyContent.find('span', {'class': 'story__date'})
        if publish_date is not None:
            publish_date = stripHTML(publish_date)
        if publish_date is None:
            if oldestChapter is None:
                # This will only be true if the story has no chapters and hasn't been published
                self.story.setMetadata('datePublished', newestChapter)
            else:
                self.story.setMetadata('datePublished', oldestChapter)
        else:
            publish_date = makeDate(publish_date, self.dateformat)
            self.story.setMetadata('datePublished', publish_date)

        # Tags
        taxonomies = storyContent.find('div', {'class': 'story__taxonomies'})
        if taxonomies is not None:
            for taxonomy in taxonomies.find_all('a'):
                classes = taxonomy.get('class', [])
                if not classes:
                    continue
                value = stripHTML(taxonomy)
                if '_taxonomy-genre' in classes:
                    self.story.addToList('genre', value)
                elif '_taxonomy-character' in classes:
                    self.story.addToList('characters', value)
                elif '_taxonomy-content_warning' in classes:
                    self.story.addToList('warnings', value)
                elif '_taxonomy-post_tag' in classes:
                    self.story.addToList('content', value)
                elif '_taxonomy-fandom' in classes:
                    self.story.addToList('content', value)

        tags = storyContent.find('section', {'class': 'story__tags-and-warnings'})
        if tags is not None:
            for warning in tags.find_all('a', {'class': '_taxonomy-content_warning'}):
                self.story.addToList('warnings', stripHTML(warning))
            for tag in tags.find_all('a', {'class': '_taxonomy-post_tag '}):
                self.story.addToList('content', stripHTML(tag))
    
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)

        soup = self.make_soup(data).find('section', {'class': 'chapter__content'})
        
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, soup)