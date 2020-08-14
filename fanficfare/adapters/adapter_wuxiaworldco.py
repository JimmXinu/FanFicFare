#  -*- coding: utf-8 -*-

# Copyright 2020 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Ljicense is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from __future__ import absolute_import
import logging
import re
# py2 vs py3 transition
from ..six import text_type as unicode, ensure_text
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldCoSiteAdapter


class WuxiaWorldCoSiteAdapter(BaseSiteAdapter):
    DATE_FORMAT = '%Y-m-%d %H:%M'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wuxco')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/%s/' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.co'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.wuxiaworld.co','m.wuxiaworld.co']

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(www|m)\.wuxiaworld\.co/(?P<id>[^/]+)(/)?'

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)
        try:
            data = self._fetchUrl(self.url)
        except HTTPError as exception:
            if exception.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(self.url))
            raise exception

        soup = self.make_soup(data)

        self.setCoverImage(self.url, soup.select_one('.book-img > img')['src'])

        book_info = soup.select_one('.book-info')
        author = book_info.select_one('.author > .name').get_text()
        self.story.setMetadata('title', book_info.select_one('.book-name').get_text())
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)

        chapter_info = soup.select_one('.chapter-wrapper')
        date = makeDate(chapter_info.select_one('.update-time').get_text(), self.DATE_FORMAT)
        if date:
            self.story.setMetadata('dateUpdated', date)

        intro = stripHTML(soup.select_one('.synopsis').p)
        self.setDescription(self.url, intro)

        chapters = chapter_info.select('.chapter-item')
        
        # Sort and deduplicate chapters (some stories in incorrect order and/or duplicates)
        chapters_data = [(int(ch.p.get_text().split()[0]), ch.p.get_text(), ch['href']) for ch in chapters]
        chapters_data.sort(key=lambda ch: ch[0])
        
        current = 1 # Assume starts at chapter 1
        for chapter in chapters_data:
            if current == chapter[0]: # Only 1 chapter per chapter number allowed
                title = chapter[1]
                url = urlparse.urljoin(self.url, chapter[2])
                self.add_chapter(title, url)
                current+=1
            else:
                continue

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        content = soup.select_one('.chapter-entity')

        return self.utf8FromSoup(url, content)
