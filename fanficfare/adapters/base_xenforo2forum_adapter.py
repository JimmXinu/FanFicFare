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

    def parse_title(self,souptag):
        h1 = souptag.find('h1',{'class':'p-title-value'})
        logger.debug(h1)
        ## SV has started putting 'Crossover', 'Sci-Fi' etc spans in the title h1.
        for tag in h1.find_all('span',{'class':'label'}):
            ## stick them into genre.
            self.story.addToList('genre',stripHTML(tag))
            logger.debug(stripHTML(tag))
            tag.extract()
        self.story.setMetadata('title',stripHTML(h1))
        logger.debug(stripHTML(h1))

    def parse_author(self,souptag):
        a = souptag.find('section',{'class':'message-user'}).find('a',{'class':'username'})
        logger.debug(a)
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
        return self.get_first_post(topsoup).find('article',{'class':'message-body'}).find('div',{'class':'bbWrapper'})

    def extract_threadmarks(self,souptag):
        threadmarks=[]
        # try threadmarks if no '#' in url
        navdiv = souptag.find('div',{'class':'buttonGroup'})
        if not navdiv:
            return threadmarks
        # was class=threadmarksTrigger.  thread cats are currently
        # only OverlayTrigger <a>s in threadmarkMenus, but I wouldn't
        # be surprised if that changed.  Don't want to do use just
        # href=re because there's more than one copy on the page; plus
        # could be included in a post.  Would be easier if <noscript>s
        # weren't being stripped, but that's a different issue.
        threadmarksas = navdiv.find_all('a',{'class':'menuTrigger','href':re.compile('threadmarks.*(threadmark_category=)?')})
        ## Loop on threadmark categories.
        tmcat_num=None

        threadmarkgroups = dict() # for ordering threadmarks
        for threadmarksa in threadmarksas:
            logger.debug("threadmarksa:%s"%threadmarksa)
            if 'threadmark_category=' in threadmarksa['href']:
                tmcat_num = threadmarksa['href'].split('threadmark_category=')[1]
            else:
                tmcat_num = '1'
            # get from earlier <a> now.
            tmcat_name = stripHTML(threadmarksa)
            if tmcat_name in self.getConfigList('skip_threadmarks_categories'):
                continue

            if tmcat_name == 'Apocrypha' and self.getConfig('apocrypha_to_omake'):
                tmcat_name = 'Omake'

            if 'http' not in threadmarksa['href']:
                href = self.getURLPrefix()+'/'+threadmarksa['href']
            else:
                href = threadmarksa['href']
            threadmarkgroups[tmcat_name]=self.fetch_threadmarks(href,
                                                                  tmcat_name,
                                                                  tmcat_num)
            logger.debug(threadmarkgroups[tmcat_name])
        ## Order of threadmark groups in new SV is changed and
        ## possibly unpredictable.  Normalize.  Keep as configurable?
        ## What about categories not in the list?
        default_order = ['Threadmarks',
                         'Sidestory',
                         'Apocrypha',
                         'Omake',
                         'Media',
                         'Informational',
                         'Staff Post']
        # default order also *after* config'ed
        # threadmark_category_order so if they are not also in
        # skip_threadmarks_categories they appear in the expected
        # order.
        for cat_name in self.getConfigList('threadmark_category_order',default_order)+default_order:
            if cat_name in threadmarkgroups:
                threadmarks.extend(threadmarkgroups[cat_name])
                del threadmarkgroups[cat_name]
        # more categories left?  new or at least unknown
        if threadmarkgroups:
            cats = threadmarkgroups.keys()
            # alphabetize for lack of a better idea to insure consist ordering
            cats.sort()
            for cat_name in cats:
                threadmarks.extend(threadmarkgroups[cat_name])
        return threadmarks

    def fetch_threadmarks(self,url,tmcat_name,tmcat_num, passed_tmcat_index=0):
        logger.debug("fetch_threadmarks(%s,tmcat_num=%s,passed_tmcat_index:%s,url=%s)"%(tmcat_name,tmcat_num, passed_tmcat_index, url))
        threadmarks=[]
        soupmarks = self.make_soup(self._fetchUrl(url))
        tm_list = soupmarks.find('div',{'class':'structItemContainer'})
        if not tm_list: # load-range don't have threadmarkList.
            tm_list = soupmarks
        # logger.debug(tm_list)
        markas = []
        tmcat_index=passed_tmcat_index
        after = False
        for tm_item in tm_list.find_all('div',{'class':'structItem--threadmark'}):
            atag = tm_item.find('a',{'data-tp-primary':'on'})
            if not atag:
                fetcher = tm_item.find('div',{'data-xf-click':'threadmark-fetcher'})
                logger.debug(fetcher)
                range_url = fetcher['data-fetchurl']
                threadmarks.extend(self.fetch_threadmarks(range_url,
                                                          tmcat_name,
                                                          tmcat_num,
                                                          tmcat_index))
                tmcat_index = len(threadmarks)
                after=True
            else:
                if after:
                    logger.debug("AFTER "*10)
                    after=False
                url,name = atag['href'],stripHTML(atag)
                date = self.make_date(tm_item)
                worddd = tm_item.find('dd')
                if worddd:
                    kwords = stripHTML(worddd)
                else:
                    kwords = ""

                # if atag.parent.has_attr('data-words'):
                #     words = int(atag.parent['data-words'])
                #     if "(" in atag.next_sibling:
                #         kwords = atag.next_sibling.strip()
                #     logger.debug("%s"%kwords)
                # else:
                #     words = ""
                #     kwords = ""
                if 'http' not in url:
                    url = self.getURLPrefix()+"/"+url
                logger.debug("%s. %s"%(tmcat_index,name))
                threadmarks.append({"tmcat_name":tmcat_name,
                                    "tmcat_num":tmcat_num,
                                    "tmcat_index":tmcat_index,
                                    "title":name,
                                    "url":url,
                                    "date":date,
                                    "words":"",
                                    "kwords":kwords})
                tmcat_index += 1
        return threadmarks

    def make_date(self,parenttag): # forums use a BS thing where dates
                                   # can appear different if recent.
        datestr=None
        try:
            datetag = parenttag.find('time')
            return datetime.fromtimestamp(float(datetag['data-time']))
            # if datetag:
            #     datestr = datetag['title']
            # else:
            #     datetag = parenttag.find('abbr',{'class':'DateTime'})
            #     if datetag:
            #         datestr="%s at %s"%(datetag['data-datestring'],datetag['data-timestring'])
            # # Apr 24, 2015 at 4:39 AM
            # # May 1, 2015 at 5:47 AM
            # datestr = re.sub(r' (\d[^\d])',r' 0\1',datestr) # add leading 0 for single digit day & hours.
            # return makeDate(datestr, self.dateformat)
        except:
            logger.debug('No date found in %s'%parenttag,exc_info=True)
            return None

