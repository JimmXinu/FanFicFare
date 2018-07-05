#  -*- coding: utf-8 -*-

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


import logging
import re
import urllib2
import urlparse

from base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldCoSiteAdapter


class WuxiaWorldCoSiteAdapter(BaseSiteAdapter):
    DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wuxco')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('http://%s/%s/' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.co'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'http://%s/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://%s/(?P<id>[^/]+)(/)?' % re.escape(self.getSiteDomain())

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)
        try:
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError, exception:
            if exception.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(self.url))
            raise exception

        soup = self.make_soup(data)
        info = soup.select_one('#info')
        self.story.setMetadata('title', stripHTML(info.h1))
        self.setCoverImage(self.url, soup.select_one('#fmimg > img')['src'])

        info_paragraphs = info('p')
        # Unicode strings because '：' isn't ':', but \xef\xbc\x9a
        author = stripHTML(info_paragraphs[0]).replace(u'Author：', '', 1)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata(
            'dateUpdated', makeDate(stripHTML(info_paragraphs[2]).replace(u'UpdateTime：', '', 1), self.DATE_FORMAT))

        intro = soup.select_one('#intro')
        # Strip <strong>Description</strong>
        intro.strong.decompose()
        self.setDescription(self.url, intro)

        for a in soup.select('#list a'):
            url = urlparse.urljoin(self.url, a['href'])
            title = stripHTML(a)
            self.chapterUrls.append((title, url))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        content = soup.select_one('#content')

        # Script empty script tag at the end of the content
        for script in content('script'):
            script.decompose()

        return self.utf8FromSoup(url, content)
