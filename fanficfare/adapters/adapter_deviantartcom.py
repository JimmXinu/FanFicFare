#  -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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
import re
from datetime import datetime
# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return DeviantArtComSiteAdapter


class DeviantArtComSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'deviantart')

        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        author = match.group('author')
        self.story.setMetadata('storyId', story_id)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'https://www.deviantart.com/' + author)
        self._setURL(url)

    @staticmethod
    def getSiteDomain():
        return 'www.deviantart.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.deviantart.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/<author>/art/<work-name>' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://www\.deviantart\.com/(?P<author>[^/]+)/art/(?P<id>[^/]+)/?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)

        soup = self.make_soup(data)

        title = soup.select_one('h1').get_text()
        self.story.setMetadata('title', title)

        ## dA has no concept of status
        # self.story.setMetadata('status', 'Completed')

        pubdate = soup.select_one('time')['datetime']
        self.story.setMetadata('datePublished', datetime.strptime(pubdate, '%Y-%m-%dT%H:%M:%S.%f%z'))

        # do description here if appropriate

        self.add_chapter(title, self.url)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.select_one('.legacy-journal')

        return self.utf8FromSoup(url, content)
