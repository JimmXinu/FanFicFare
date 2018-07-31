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

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

class MCStoriesComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev','mcstories')

        # Normalize story URL to the chapter index page (.../index.html)
        url = re.sub("/([a-zA-Z0-9_-]+.html)?$", "/index.html", url)

        # Extract story ID from base URL, http://mcstories.com/STORY_ID/index.html
        storyId = self.parsedUrl.path.split('/',)[1]
        self.story.setMetadata('storyId', storyId)

        ## set url
        self._setURL(url)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = '%d %B %Y'

    @staticmethod
    def getSiteDomain():
        return 'mcstories.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['mcstories.com',
                'www.mcstories.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://mcstories.com/StoryTitle https://mcstories.com/StoryTitle/index.html https://mcstories.com/StoryTitle/StoryTitle1.html"

    def getSiteURLPattern(self):
        return r"https?://(www\.)?mcstories\.com/([a-zA-Z0-9_-]+)/"

    def extractChapterUrlsAndMetadata(self):
        """
        Chapters are located at /StoryName/StoryName.html (for single-chapter
        stories), or /StoryName/StoryName#.html for multiple chapters (# is a
        non-padded incrementing number, like StoryName1, StoryName2.html, ...,
        StoryName10.html)

        The story metadata page is at /StoryName/index.html , including a list
        of chapters.
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

        # Extract metadata
        title = soup1.find('h3', class_='title')
        self.story.setMetadata('title', title.text)

        # Author
        author = soup1.find('h3', class_='byline').a
        authorurl = urlparse.urljoin(self.url, author['href'])
        self.story.setMetadata('author', author.text)
        self.story.setMetadata('authorUrl', authorurl)
        authorid = os.path.splitext(os.path.basename(authorurl))[0]
        self.story.setMetadata('authorId', authorid)

        # Description
        synopsis = soup1.find('section', class_='synopsis')
        description = "\n\n".join([p.text for p in synopsis.find_all('p')])
        self.story.setMetadata('description', description)

        # Tags
        codesDiv = soup1.find('div', class_="storyCodes")
        for a in codesDiv.find_all('a'):
            self.story.addToList('eroticatags', a.text)

        # Publish and update dates
        publishdate = None
        updatedate = None
        datelines = soup1.find_all('h3', class_='dateline')
        for dateline in datelines:
            if dateline.text.startswith('Added '):
                publishdate = makeDate(dateline.text, "Added " + self.dateformat)
            elif dateline.text.startswith('Updated '):
                updatedate = makeDate(dateline.text, "Updated " + self.dateformat)

        if publishdate is not None: self.story.setMetadata('datePublished', publishdate)
        if updatedate is not None: self.story.setMetadata('dateUpdated', updatedate)

        # Get chapter URLs
        chapterTable = soup1.find('table', class_='index')

        if chapterTable is not None:
            # Multi-chapter story
            chapterRows = chapterTable.find_all('tr')

            for row in chapterRows:
                chapterCell = row.td
                if chapterCell is not None:
                    link = chapterCell.a
                    chapterTitle = link.text
                    chapterUrl = urlparse.urljoin(self.url, link['href'])
                    self.add_chapter(chapterTitle, chapterUrl)
        else:
            # Single chapter
            chapterDiv = soup1.find('div', class_='chapter')
            chapterTitle = chapterDiv.a.text
            chapterUrl = urlparse.urljoin(self.url, chapterDiv.a['href'])
            self.add_chapter(chapterTitle, chapterUrl)


        logger.debug("Story: <%s>", self.story)

        return

    def getChapterText(self, url):
        """
        Clean up a mcstories chapter page.

        All content is in article#mcstories, with chapter headers in h3
        """
        logger.debug('Getting chapter text from <%s>' % url)
        data1 = self._fetchUrl(url)
        soup1 = self.make_soup(data1)

        #strip comments from soup
        [comment.extract() for comment in soup1.find_all(text=lambda text:isinstance(text, Comment))]

        # get story text
        story1 = soup1.find('article', id='mcstories')

        # Remove duplicate name and author headers
        [h3.extract() for h3 in story1.find_all('h3',class_=re.compile(r'(title|chapter|byline)'))]

        storytext = self.utf8FromSoup(url, story1)

        return storytext


def getClass():
    return MCStoriesComSiteAdapter
