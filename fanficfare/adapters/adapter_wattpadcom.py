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
    API_STORYINFO = 'https://www.wattpad.com/api/v3/stories/{0}'  # SAME URL WITH /stories?id=X is NIT the same
    API_STORYTEXT = 'https://www.wattpad.com/apiv2/storytext?id={0}'
    API_CHAPTERINFO = 'https://www.wattpad.com/apiv2/info?id={0}'
    CATEGORY_DEFs = None

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.storyId = str(self.getStoryId(url))
        self.story.setMetadata('storyId', self.storyId)
        self._setURL('https://www.wattpad.com/story/{0}'.format(self.storyId))

        # categoryDefs do not change all that often, if at all.  Could be put in a constant, leaving it as a class var for now
        # note: classvar may be useless because of del adapter
        if WattpadComAdapter.CATEGORY_DEFs is None:
            try:
                WattpadComAdapter.CATEGORY_DEFs = json.loads(self._fetchUrl(WattpadComAdapter.API_GETCATEGORIES))
            except:
                logger.debug('Something went wrong trying to fetch the category definitions (API_GETCATEGORIES)')

    @staticmethod
    def getSiteDomain():
        return 'www.wattpad.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.wattpad.com']

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
            logger.debug('storyId found in given url:{0}'.format(storyIdInUrl))
            return storyIdInUrl.group("storyId")
        else:
            chapterIdInUrl = re.match('https://www\.wattpad\.com/(?P<storyId>\d+).*', url)
            logger.debug('call API_CHAPTER_INFO for:{0}'.format(chapterIdInUrl))
            chapterInfo = json.loads(self._fetchUrl(WattpadComAdapter.API_CHAPTERINFO.format(chapterIdInUrl.group('storyId'))))
            groupid = chapterInfo.get('groupId', None)
            logger.debug('API_CHAPTER_INFO returned {0} for chapterId {1}'.format(groupid, chapterIdInUrl))
            if groupid is None:
                raise exceptions.StoryDoesNotExist(url)
            else:
                return groupid

    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        # API_STORYINFO
        logger.debug('Start of metadata extraction for storyId:' + self.storyId)
        try:
            storyInfo = json.loads(self._fetchUrl(WattpadComAdapter.API_STORYINFO.format(self.storyId)))
            logger.debug('API_STORYINFO returned:' + json.dumps(storyInfo, indent=1))
        except Exception, e:
            raise exceptions.InvalidStoryURL(self.url, self.getSiteDomain(), self.getSiteExampleURLs())

        if not self.getConfig('is_adult') and storyInfo['mature'] == True:
            logger.debug('config is_adult is false but storyInfo[mature] is true')
            raise exceptions.AdultCheckRequired(self.url)

        # title
        logger.debug('Found Title' + storyInfo['title'])
        self.story.setMetadata('title', storyInfo['title'])

        # author
        logger.debug('authorId (and author name)' + storyInfo['user']['name'])
        self.story.setMetadata('authorId', storyInfo['user']['name'])
        self.story.setMetadata('author', storyInfo['user']['name'])
        logger.debug('authorURL: ' + 'https://www.wattpad.com/user/{0}'.format(storyInfo['user']['name']))
        self.story.setMetadata('authorUrl', 'https://www.wattpad.com/user/{0}'.format(storyInfo['user']['name']))
        logger.debug('Story read count: {0}'.format(storyInfo['readCount']))
        self.story.setMetadata('reads', storyInfo['readCount'])

        # STATUS
        logger.debug('status: ' + str(storyInfo['completed']))
        self.story.setMetadata('status', 'In-Progress')
        if storyInfo['completed']:
            self.story.setMetadata('status', 'Completed')

        # DESCRIPTION
        logger.debug('description: ' + storyInfo['description'])
        self.setDescription(storyInfo['url'], storyInfo['description'])

        # DATES
        logger.debug('dateUpdated: ' + storyInfo['modifyDate'])
        self.story.setMetadata('dateUpdated', makeDate(storyInfo['modifyDate'].rstrip('Z'), "%Y-%m-%dT%H:%M:%S"))
        logger.debug('datePublished: ' + storyInfo['createDate'])
        self.story.setMetadata('datePublished', makeDate(storyInfo['createDate'].rstrip('Z'), "%Y-%m-%dT%H:%M:%S"))

        self.chapterUrls = [(part['title'], part['url']) for part in storyInfo['parts']]
        logger.debug('chapterUrls:' + str(storyInfo['parts']))
        self.story.setMetadata('numChapters', len(self.chapterUrls))

        logger.debug('Cover: {0}'.format(storyInfo['cover']))
        self.setCoverImage(storyInfo['url'], storyInfo['cover'])

        logger.debug('Language: ', storyInfo['language']['name'])
        self.story.setMetadata('language', storyInfo['language']['name'])

        # CATEGORIES
        # there should be only one category per book, but the data structure allows for more
        try:
            logger.debug('Category Keys: ' + str(storyInfo['categories']))
            storyCategories = [WattpadComAdapter.CATEGORY_DEFs.get(str(c)) for c in storyInfo['categories'] if
                               WattpadComAdapter.CATEGORY_DEFs.has_key(str(c))]
            logger.debug('Categories from Category Keys: {0}.'.format(str(storyCategories)))

            logger.debug('Tags: {0}.'.format(str(storyInfo['tags'])))
            tags = storyCategories + storyInfo['tags']
            logger.debug('Tags + Categories = ', str(tags))
            self.story.setMetadata('tags', tags)
        except:
            logger.debug('Conversion from category keys to tags failed.')
            pass

        return self.extractChapterUrlsAndMetadata()

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        chapterID = re.search(u'https://www.wattpad.com/(?P<chapterID>\d+).*', url).group('chapterID')
        return self._fetchUrl(WattpadComAdapter.API_STORYTEXT.format(chapterID))


# adapter self-dicovery is not implemented in fanficfare (it existed for the previous project)
def getClass():
    return WattpadComAdapter
