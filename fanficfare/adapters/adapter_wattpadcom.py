# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2017 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import absolute_import

import json
import logging
import re

from .base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions as exceptions
logger = logging.getLogger(__name__)

class WattpadComAdapter(BaseSiteAdapter):
    # All the API discovery work done by github user de3sw2aq1
    # Source: https://github.com/de3sw2aq1/wattpad-ebook-scraper/blob/master/scrape.py
    API_GETCATEGORIES = 'https://www.wattpad.com/apiv2/getcategories'
    API_STORYINFO = 'https://www.wattpad.com/api/v3/stories/%s'  # stories?id=X is NOT the same
    API_STORYTEXT = 'https://www.wattpad.com/apiv2/storytext?id=%s'
    API_CHAPTERINFO = 'https://www.wattpad.com/apiv2/info?id=%s'
    CATEGORY_DEFs = None

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.storyId = unicode(self.getStoryId(url))
        self.story.setMetadata('siteabbrev',self.getSiteAbbrev())
        self.story.setMetadata('storyId', self.storyId)
        self._setURL('https://www.wattpad.com/story/%s' % self.storyId)

        # categoryDefs do not change all that often, if at all.  Could be put in a constant, leaving it as a class var for now
        # note: classvar may be useless because of del adapter
        if WattpadComAdapter.CATEGORY_DEFs is None:
            try:
                WattpadComAdapter.CATEGORY_DEFs = json.loads(self._fetchUrl(WattpadComAdapter.API_GETCATEGORIES))
            except:
                logger.debug('API_GETCATEGORIES failed.')
                WattpadComAdapter.CATEGORY_DEFs = []

    @staticmethod
    def getSiteDomain():
        return 'www.wattpad.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://www.wattpad.com/story/9999999-story-title https://www.wattpad.com/story/9999999 https://www.wattpad.com/9999999-chapter-is-ok-too'

    @classmethod
    def getSiteURLPattern(cls):
        return 'https://www\.wattpad\.com/(story/)?(?P<storyId>\d+).*'

    @classmethod
    def getSiteAbbrev(cls):
        return 'wattpad'

    @classmethod
    def getDateFormat(cls):
        return "%Y-%m-%dT%H:%M:%SZ"

    def use_pagecache(self):
        return True

    def getStoryId(self, url):
        storyIdInUrl = re.match('https://www\.wattpad\.com/story/(?P<storyId>\d+).*', url)
        if storyIdInUrl is not None:
            return storyIdInUrl.group("storyId")
        else:
            chapterIdInUrl = re.match('https://www\.wattpad\.com/(?P<chapterId>\d+).*', url)
            chapterInfo = json.loads(self._fetchUrl(WattpadComAdapter.API_CHAPTERINFO % chapterIdInUrl.group('chapterId')))
            groupid = chapterInfo.get('groupId', None)
            if groupid is None:
                raise exceptions.StoryDoesNotExist(url)
            else:
                return groupid

    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        try:
            storyInfo = json.loads(self._fetchUrl(WattpadComAdapter.API_STORYINFO % self.storyId))
            logger.debug('storyInfo: %s' % json.dumps(storyInfo))
        except Exception:
            raise exceptions.InvalidStoryURL(self.url, self.getSiteDomain(), self.getSiteExampleURLs())

        if not (self.is_adult or self.getConfig("is_adult")) and storyInfo['mature'] == True:
            raise exceptions.AdultCheckRequired(self.url)

        # title
        self.story.setMetadata('title', storyInfo['title'])

        # author
        self.story.setMetadata('authorId', storyInfo['user']['name'])
        self.story.setMetadata('author', storyInfo['user']['name'])
        self.story.setMetadata('authorUrl', 'https://www.wattpad.com/user/%s' % storyInfo['user']['name'])
        self.story.setMetadata('reads', storyInfo['readCount'])

        # STATUS
        self.story.setMetadata('status', 'In-Progress')
        if storyInfo['completed']:
            self.story.setMetadata('status', 'Completed')

        # DESCRIPTION
        self.setDescription(storyInfo['url'], storyInfo['description'])

        # DATES
        self.story.setMetadata('dateUpdated', makeDate(storyInfo['modifyDate'].rstrip('Z'), "%Y-%m-%dT%H:%M:%S"))
        self.story.setMetadata('datePublished', makeDate(storyInfo['createDate'].rstrip('Z'), "%Y-%m-%dT%H:%M:%S"))

        self.chapterUrls = [(part['title'], part['url']) for part in storyInfo['parts']]
        self.story.setMetadata('numChapters', len(self.chapterUrls))
        self.setCoverImage(storyInfo['url'], storyInfo['cover'].replace('-256-','-512-'))
        self.story.setMetadata('language', storyInfo['language']['name'])

        # CATEGORIES
        try:
            storyCategories = [WattpadComAdapter.CATEGORY_DEFs.get(str(c)) for c in storyInfo['categories'] if
                               WattpadComAdapter.CATEGORY_DEFs.has_key(str(c))]

            self.story.setMetadata('category', storyCategories[0])
            self.story.setMetadata('tags', storyInfo['tags'])
        except:
            pass

        return self.extractChapterUrlsAndMetadata()

    def getChapterText(self, url):
        logger.debug('%s' % url)
        chapterID = re.search(u'https://www.wattpad.com/(?P<chapterID>\d+).*', url).group('chapterID')
        return self.utf8FromSoup(url,self.make_soup(self._fetchUrl(WattpadComAdapter.API_STORYTEXT % chapterID)))

# adapter self-dicovery is not implemented in fanficfare (it existed for the previous project)
def getClass():
    return WattpadComAdapter
