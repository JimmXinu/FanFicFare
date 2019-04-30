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
from datetime import datetime
logger = logging.getLogger(__name__)
import re
from xml.dom.minidom import parseString

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import makeDate
from .base_xenforoforum_adapter import BaseXenForoForumAdapter

logger = logging.getLogger(__name__)

class BaseXenForo2ForumAdapter(BaseXenForoForumAdapter):

    def __init__(self, config, url):
        logger.info("init url: "+url)
        BaseXenForoForumAdapter.__init__(self, config, url)

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['base_xenforo2forum'] + BaseXenForoForumAdapter.getConfigSections()

    def parse_title(self,souptag):
        h1 = souptag.find('h1',{'class':'p-title-value'})
        # logger.debug(h1)
        ## SV has started putting 'Crossover', 'Sci-Fi' etc spans in the title h1.
        for tag in h1.find_all('span',{'class':'label'}):
            ## stick them into genre.
            self.story.addToList('genre',stripHTML(tag))
            # logger.debug(stripHTML(tag))
            tag.extract()
        self.story.setMetadata('title',stripHTML(h1))
        # logger.debug(stripHTML(h1))

    def parse_author(self,souptag):
        a = souptag.find('section',{'class':'message-user'}).find('a',{'class':'username'})
        # logger.debug(a)
        self.story.addToList('authorId',a['href'].split('/')[-2])
        authorUrl = a['href'] # self.getURLPrefix()+'/'+a['href']
        self.story.addToList('authorUrl',authorUrl)
        self.story.addToList('author',a.text)

    def cache_posts(self,topsoup):
        for post in topsoup.find_all('article',{'class':'message--post'}):
            logger.debug("Caching %s"%post['data-content'])
            self.post_cache[post['data-content']] = post

    def get_first_post(self,topsoup):
        return topsoup.find('article',{'class':'message--post'})

    def get_first_post_body(self,topsoup):
        return self.get_post_body(self.get_first_post(topsoup))

    def get_post_body(self,souptag):
        return souptag.find('article',{'class':'message-body'}).find('div',{'class':'bbWrapper'})

    def get_post_created_date(self,souptag):
        return self.make_date(souptag.find('div', {'class':'message-date'}))

    def get_post_updated_date(self,souptag):
        return self.make_date(souptag.find('div',{'class':'message-lastEdit'}))

    def get_threadmarks_top(self,souptag):
        return souptag.find('div',{'class':'buttonGroup'})

    def get_threadmarks(self,navdiv):
        return navdiv.find_all('a',{'class':'menuTrigger','href':re.compile('threadmarks.*(threadmark_category=)?')})

    def get_threadmark_catnumname(self,threadmarksa):
        if 'threadmark_category=' in threadmarksa['href']:
            tmcat_num = threadmarksa['href'].split('threadmark_category=')[1]
        else:
            tmcat_num = '1'
        tmcat_name = stripHTML(threadmarksa)
        return (tmcat_num,tmcat_name)

    def get_threadmarks_list(self,soupmarks):
        return soupmarks.find('div',{'class':'structItemContainer'})

    def get_threadmarks_from_list(self,tm_list):
        return tm_list.find_all('div',{'class':'structItem--threadmark'})

    def get_atag_from_threadmark(self,tm_item):
        return tm_item.find('a',{'data-tp-primary':'on'})

    def get_threadmark_range_url(self,tm_item,tmcat_num):
        fetcher = tm_item.find('div',{'data-xf-click':'threadmark-fetcher'})
        # logger.debug(fetcher)
        return fetcher['data-fetchurl']

    def get_threadmark_date(self,tm_item):
        return self.make_date(tm_item)

    ## XF2 doesn't appear to have words, just kwords.
    def get_threadmark_words(self,tm_item):
        words = kwords = ""
        worddd = tm_item.find('dd')
        if worddd:
            kwords = "("+stripHTML(worddd)+")" # to match XF1
        return words,kwords

    def make_date(self,parenttag):
        datestr=None
        try:
            datetag = parenttag.find('time')
            # not paying any attention to TZ issues.
            return datetime.fromtimestamp(float(datetag['data-time']))
        except:
            logger.warn('No date found in %s'%parenttag,exc_info=True)
            return None

    def make_reader_url(self,tmcat_num,reader_page_num):
        # https://xf2test.sufficientvelocity.com/threads/mauling-snarks-worm.41471/reader/page-4?threadmark_category=4
        return self.story.getMetadata('storyUrl')+'reader/page-'+unicode(reader_page_num)+'?threadmark_category='+tmcat_num

    def get_spoiler_tags(self,topsoup):
        return topsoup.find_all('div',class_='bbCodeSpoiler')
