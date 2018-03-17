# -*- coding: utf-8 -*-
# Copyright 2016 Fanficdownloader team
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

# Adapted by GComyn on December 14. 2016

import json
import logging
import re
import urllib2
import urlparse

from base_adapter import BaseSiteAdapter, makeDate
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldComSiteAdapter


class WuxiaWorldComSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wux')
        self._dateformat = '%Y-%m-%dT%H:%M:%S+00:00'

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('http://%s/novel/%s' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'http://%s/novel/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'http(s)?://%s/novel/(?P<id>[^/]+)(/)?' % re.escape(self.getSiteDomain())

    def use_pagecache(self):
        return True

    def _parse_linked_data(self, soup):
        # See https://json-ld.org
        tag = soup.find('script', type='application/ld+json')
        if not tag:
            return {}
        return json.loads(tag.string)

    def _parse_date(self, text):
        # Strip microseconds from date
        text = re.sub(r'\.\d+\+', '+', text)
        return makeDate(text, self._dateformat)

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)
        try:
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError, exception:
            if exception.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(self.url))
            raise exception

        soup = self.make_soup(data)
        ld = self._parse_linked_data(soup)
        author_name = ld['author']['name']
        self.story.setMetadata('author', author_name)
        self.story.setMetadata('authorId', author_name.lower())
        self.story.setMetadata('title', ld['headline'])
        self.story.setMetadata('datePublished', self._parse_date(ld['datePublished']))
        self.story.setMetadata('tags', [stripHTML(a) for a in soup.select('.media-body .tags a')])
        self.setCoverImage(self.url, ld['image'])

        for a in soup.select('#accordion .chapter-item > a'):
            title = stripHTML(a)
            url = urlparse.urljoin(self.url, a['href'])
            self.chapterUrls.append((title, url))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        last_chapter_data = self._fetchUrl(self.chapterUrls[-1][1])
        last_chapter_soup = self.make_soup(last_chapter_data)
        last_chapter_ld = self._parse_linked_data(last_chapter_soup)
        self.story.setMetadata('dateUpdated', self._parse_date(last_chapter_ld['datePublished']))

        description = stripHTML(soup.select_one('.section-content .p-15 > .fr-view'))
        self.setDescription(self.url, description)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self._fetchUrl(url)
        soup = self.make_soup(data)
        content = soup.select_one('.section-content .fr-view')

        # Remove next- and previous-chapter links
        for a in content.select('.chapter-nav'):
            a.decompose()

        return self.utf8FromSoup(url, content)
