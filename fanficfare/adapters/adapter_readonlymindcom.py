# -*- coding: utf-8 -*-
# Copyright 2022 FanFicFare team
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
###   Based on MCStoriesComSiteAdapter and reworked by Nothorse
###
####################################################################################################
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
logger = logging.getLogger(__name__)
import re

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

####################################################################################################
def getClass():
    return ReadOnlyMindComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ReadOnlyMindComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','rom')

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # Normalize story URL to the chapter index page (.../index.html)
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            # normalized story URL.
            self._setURL("https://"+self.getSiteDomain()+"/@"+m.group('aut')+"/"+m.group('id')+"/")
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])


        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"


    ################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        return 'readonlymind.com'

    ################################################################################################
    @classmethod
    def getAcceptDomains(cls):

        return ['readonlymind.com', 'www.readonlymind.com']

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(self):
        return "https://readonlymind.com/@AnAuthor/A_Story_Name/"

    ################################################################################################
    def getSiteURLPattern(self):
        return r'https?://readonlymind\.com/@(?P<aut>[a-zA-Z0-9_]+)/(?P<id>[a-zA-Z0-9_]+)'

    ################################################################################################
    def extractChapterUrlsAndMetadata(self):
        """
        Chapters are located at /@author/StoryName/#/

        The story metadata page is at /@author/StoryName/, including a list
        of chapters.
        """
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        data1 = self.get_request(self.url)
        logger.debug(self.url)

        soup1 = self.make_soup(data1)
        #strip comments from soup
        baseUrl = "https://" + self.getSiteDomain()
        if 'Page Not Found.' in data1:
            raise exceptions.StoryDoesNotExist(self.url)

        # Extract metadata
        header = soup1.find('header')
        title = header.find('h1')
        self.story.setMetadata('title', title.text)

        # Author
        author = soup1.find('meta', attrs={"name":"author"})
        authorurl = soup1.find('link', rel="author")
        self.story.setMetadata('author', author.attrs["content"])
        self.story.setMetadata('authorUrl', baseUrl + authorurl["href"])
        self.story.setMetadata('authorId', author.attrs["content"])

        # Description
        synopsis = soup1.find('meta', attrs={"name":"description"})
        self.story.setMetadata('description', synopsis.attrs["content"])

        # Tags
        # As these are the only tags should they go in categories?
        # Also check for series tags in config
        # Unfortunately there's no way to get a meaningful volume number
        series_tags = self.getConfig('series_tags').split(',')

        for a in soup1.find_all('a', class_="tag-link"):
            strippedTag = a.text.strip('#')
            if strippedTag in series_tags:
                self.setSeries(strippedTag.replace('_', ' '), 0)
                seriesUrl = baseUrl + a.attrs['href']
                self.story.setMetadata('seriesUrl', seriesUrl);
            else:
                self.story.addToList('eroticatags', strippedTag)


        # Publish and update dates
        publishdate = soup1.find('meta', attrs={"name":"created"})
        pDate = makeDate(publishdate.attrs['content'], self.dateformat)
        if publishdate is not None: self.story.setMetadata('datePublished', pDate)

        # Get chapter URLs
        chapterTable = soup1.find('section', id='chapter-list')
        #
        if chapterTable is not None:
            # Multi-chapter story
            chapterRows = chapterTable.find_all('section', class_='story-card-large')
            for row in chapterRows:
                titleDiv = row.find('div', class_='story-card-title')
                chapterCell = titleDiv.a
                if chapterCell is not None:
                    chapterTitle = chapterCell.text
                    chapterUrl = baseUrl + chapterCell['href']
                    self.add_chapter(chapterTitle, chapterUrl)
                dateUpdated = row.find('div', class_='story-card-publication-date')
                if dateUpdated is not None:
                    self.story.setMetadata('dateUpdated', makeDate(dateUpdated.text, self.dateformat))

        else:
            # Single chapter
            chapterTitle = self.story.getMetadata('title')
            chapterUrl = self.url
            self.add_chapter(chapterTitle, chapterUrl)


        logger.debug("Story: <%s>", self.story)

        return

    def getChapterText(self, url):
        """

        All content is in section#chapter-content
        """
        logger.debug('Getting chapter text from <%s>' % url)
        data1 = self.get_request(url)
        soup1 = self.make_soup(data1)

        #strip comments from soup
        # [comment.extract() for comment in soup1.find_all(text=lambda text:isinstance(text, Comment))]

        # get story text
        story1 = soup1.find('section', id='chapter-content')


        storytext = self.utf8FromSoup(url, story1)

        return storytext
