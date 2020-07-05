#  -*- coding: utf-8 -*-

# Copyright 2019 FanFicFare team
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
from ..six import text_type as unicode, ensure_text
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return ChireadsComSiteAdapter


class ChireadsComSiteAdapter(BaseSiteAdapter):
    NEW_DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
    OLD_DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'chireads')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/category/translatedtales/%s/' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'chireads.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['chireads.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/category/translatedtales/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://chireads\.com/category/translatedtales/(?P<id>[^/]+)(/)?'

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
        info = soup.select_one('.inform-inform-data')
        self.story.setMetadata('title', stripHTML(info.h3).split(' | ')[0])

        self.setCoverImage(self.url, soup.select_one('.inform-product > img')['src'])

        # Unicode strings because '：' isn't ':', but \xef\xbc\x9a
        # author = stripHTML(info.h6).split(u' ')[0].replace(u'Auteur : ', '', 1)

        author = stripHTML(info.h6).split('Babelcheck')[0].replace('Auteur : ', '').replace('\xc2\xa0', '')
        # author = stripHTML(info.h6).split('\xa0')[0].replace(u'Auteur : ', '', 1)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)

        datestr = stripHTML(soup.select_one('.newestchapitre > div > a')['href'])[-11:-1]
        date = makeDate(datestr, '%Y/%m/%d')
        if date:
            self.story.setMetadata('dateUpdated', date)

        intro = stripHTML(info.select_one('.inform-inform-txt').span)
        self.setDescription(self.url, intro)

        for content in soup.findAll('div', {'id': 'content'}):
            for a in content.findAll('a'):
                self.add_chapter(a.get_text(), a['href'])


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        content = soup.select_one('#content')

        if None == content:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,content)
