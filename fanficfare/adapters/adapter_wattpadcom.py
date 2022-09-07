# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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

# py2 vs py3 transition
from ..six import text_type as unicode

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
        self.chapter_photoUrl = {}

        # categoryDefs do not change all that often, if at all.  Could be put in a constant, leaving it as a class var for now
        # note: classvar may be useless because of del adapter
        if WattpadComAdapter.CATEGORY_DEFs is None:
            try:
                WattpadComAdapter.CATEGORY_DEFs = json.loads(self.get_request(WattpadComAdapter.API_GETCATEGORIES))
            except:
                logger.warning('API_GETCATEGORIES failed.')
                WattpadComAdapter.CATEGORY_DEFs = []

    @staticmethod
    def getSiteDomain():
        return 'www.wattpad.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://www.wattpad.com/story/9999999-story-title https://www.wattpad.com/story/9999999 https://www.wattpad.com/9999999-chapter-is-ok-too'

    @classmethod
    def stripURLParameters(cls,url):
        # usually return re.sub(r"&.*$","",url)
        # changed to allow email notice URLs.
        return url

    @classmethod
    def getSiteURLPattern(cls):
        # changed to allow email notice URLs.
        return r'.*https(://|%3A%2F%2F)www\.wattpad\.com(/|%2F)(story/)?(?P<storyId>\d+).*'

    @classmethod
    def getSiteAbbrev(cls):
        return 'wattpad'

    @classmethod
    def getDateFormat(cls):
        return "%Y-%m-%dT%H:%M:%SZ"

    def getStoryId(self, url):
        storyIdInUrl = re.match(r'https://www\.wattpad\.com/story/(?P<storyId>\d+).*', url)
        if storyIdInUrl is not None:
            return storyIdInUrl.group("storyId")
        else:
            ## %2F to allow for escaped URL embedded in a redirect URL
            ## %in email.
            ## https://www.wattpad.com/et?c=euc&t=uploaded_story&l=https%3A%2F%2Fwww.wattpad.com%2F997616013-nuestro-destino-ron-weasley-y-tu-cap-11&emid=uploaded_story.295918124.1608687259%2C544769.4a691b8fc2a4607e1c770aa4ebd48cc3aaf39bd599a738d3747d41fdfa37fcda
            chapterIdInUrl = re.match(r'.*https(://|%3A%2F%2F)www\.wattpad\.com(/|%2F)(?P<chapterId>\d+).*', url)
            chapterInfo = json.loads(self.get_request(WattpadComAdapter.API_CHAPTERINFO % chapterIdInUrl.group('chapterId')))
            groupid = chapterInfo.get('groupId', None)
            if groupid is None:
                raise exceptions.StoryDoesNotExist(url)
            else:
                return groupid

    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        try:
            storyInfo = json.loads(self.get_request(WattpadComAdapter.API_STORYINFO % self.storyId))
            # logger.debug('storyInfo: %s' % json.dumps(storyInfo, sort_keys=True,
            #                                           indent=2, separators=(',', ':')))
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

        for part in storyInfo['parts']:
            self.add_chapter(part['title'], part['url'])
            self.chapter_photoUrl[part['url']] = part['photoUrl']
        self.setCoverImage(storyInfo['url'], storyInfo['cover'].replace('-256-','-512-'))
        self.story.setMetadata('language', storyInfo['language']['name'])

        # CATEGORIES
        try:
            storyCategories = [WattpadComAdapter.CATEGORY_DEFs.get(unicode(c)) for c in storyInfo['categories'] if
                               unicode(c) in WattpadComAdapter.CATEGORY_DEFs]

            self.story.setMetadata('category', storyCategories[0])
            self.story.setMetadata('tags', storyInfo['tags'])
        except:
            pass

        return self.extractChapterUrlsAndMetadata()

    def getChapterText(self, url):
        logger.debug('%s' % url)
        chapterID = re.search(r'https://www.wattpad.com/(?P<chapterID>\d+).*', url).group('chapterID')
        data = self.get_request(WattpadComAdapter.API_STORYTEXT % chapterID)
        # logger.debug(self.chapter_photoUrl[url])
        imgdata = ''
        if self.chapter_photoUrl[url] and self.getConfig('include_chapter_banner_images',True):
            imgdata = '''
<img class="photoUrl banner-image" src="%s">
''' % self.chapter_photoUrl[url]
        # logger.debug(imgdata + data)
        return self.utf8FromSoup(url,self.make_soup(imgdata + data))

# adapter self-dicovery is not implemented in fanficfare (it existed for the previous project)
def getClass():
    return WattpadComAdapter
