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
# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return PatreonComSiteAdapter

class PatreonComSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'patreon')

        self.is_adult = False

        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL(url)

    @staticmethod
    def getSiteDomain():
        return 'www.patreon.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.patreon.com']

    @classmethod
    def getProtocol(self):
        return 'https'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://www.patreon.com/posts/<post-id>' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://www\.patreon\.com/posts/(?P<id>[^/]+)/?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)
        soup = self.make_soup(data)

        title = soup.select_one('[data-tag="post-title"]').get_text()
        self.story.setMetadata('title', stripHTML(title))

        author = soup.select_one('[data-tag=metadata-wrapper] > div:first-child > div').get_text()
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'https://www.patreon.com/' + author)

        pubdate = soup.select_one('[data-tag="post-published-at"] span').get_text()
        self.story.setMetadata('datePublished', makeDate(pubdate, '%b %d, %Y at %I:%M %p'))

        story_tags = soup.select('[data-tag="post-tags"] a p')
        if story_tags is not None:
            for tag in story_tags:
                self.story.addToList('genre', tag.get_text())

        self.add_chapter(title, self.url)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.select_one('[data-tag="post-content"]')

        return self.utf8FromSoup(url, content)
