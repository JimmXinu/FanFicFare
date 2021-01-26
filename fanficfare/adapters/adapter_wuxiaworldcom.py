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

from __future__ import absolute_import
import json
import logging
import re
# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter, makeDate
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldComSiteAdapter


class WuxiaWorldComSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wux')
        self._dateformat = '%Y-%m-%d'

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/novel/%s' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/novel/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://%s/novel/(?P<id>[^/]+)(/)?' % re.escape(self.getSiteDomain())

    def use_pagecache(self):
        return True

    def _parse_linked_data(self, soup):
        # See https://json-ld.org
        tag = soup.find('script', type='application/ld+json')
        if not tag:
            return {}
        return json.loads(tag.string)

    def _parse_date(self, text):
        # Strip time from date--site doesn't seem to have it anymore.
        text = re.sub(r'T.*$', '', text)
        return makeDate(text, self._dateformat)

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)

        soup = self.make_soup(data)
        ld = self._parse_linked_data(soup)
        # logger.debug(ld)
        author_name = ld['author']['name']
        self.story.setMetadata('author', author_name)
        self.story.setMetadata('authorId', author_name.lower())
        self.story.setMetadata('title', ld['name'])
        self.story.setMetadata('datePublished', self._parse_date(ld['datePublished']))
        ## site doesn't have authorUrl links.

        tags = [stripHTML(a) for a in soup.select('.media-body .tags a')]
        for tag in tags:
            if 'Completed' == tag:
                self.story.setMetadata('status', 'Completed')
                tags.remove('Completed')
            elif 'Ongoing' == tag:
                self.story.setMetadata('status', 'In-Progress')
                tags.remove('Ongoing')
        self.story.setMetadata('tags', tags)

        cover_url = ld['image']
        if not cover_url:
            img = soup.select_one('.media-novel-index .media-left img')
            if img:
                cover_url = img['src']
        if cover_url:
            self.setCoverImage(self.url, cover_url)

        for a in soup.select('#accordion .chapter-item > a'):
            title = stripHTML(a)
            url = urlparse.urljoin(self.url, a['href'])
            self.add_chapter(title, url)


        last_chapter_data = self.get_request(self.get_chapter(-1,'url'))
        last_chapter_soup = self.make_soup(last_chapter_data)
        last_chapter_ld = self._parse_linked_data(last_chapter_soup)
        self.story.setMetadata('dateUpdated', self._parse_date(last_chapter_ld['datePublished']))

        description = stripHTML(soup.select_one('.section-content .p-15 > .fr-view'))
        self.setDescription(self.url, description)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        soup = self.make_soup(data)
        content = soup.select_one('.panel-default .fr-view')

        # Remove next- and previous-chapter links
        for a in content.select('.chapter-nav'):
            a.decompose()

        return self.utf8FromSoup(url, content)
