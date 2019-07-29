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
        return super(BaseXenForo2ForumAdapter, cls).getConfigSections() + ['base_xenforo2forum']

    def performLogin(self):
        params = {}

        if self.password:
            params['login'] = self.username
            params['password'] = self.password
        else:
            params['login'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        if not params['login']:
            raise exceptions.FailedToLogin(self.url,"No username given.  Set in personal.ini or enter when prompted.")

        ## need a login token.
        data = self._fetchUrl(self.getURLPrefix() + '/login',usecache=False)
        # logger.debug(data)
        # <input type="hidden" name="_xfToken" value="1556822458,710e5bf6fc87c67ea04ab56a910ac3ff" />
        find_token='<input type="hidden" name="_xfToken" value="'
        xftoken = data[data.index(find_token)+len(find_token):]
        xftoken = xftoken[:xftoken.index('"')]
        params['remember'] = '1'
        params['_xfToken'] = xftoken
        params['_xfRedirect'] = self.getURLPrefix() + '/'

        ## https://forum.questionablequesting.com/login/login
        loginUrl = self.getURLPrefix() + '/login/login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                             params['login']))

        d = self._postUrl(loginUrl, params)# , headers={ 'referer':self.getURLPrefix() + '/login',
                                           #            'origin':self.getURLPrefix() })

        if "Log In" in d:
            # logger.debug(d)
            logger.info("Failed to login to URL %s as %s" % (self.url,
                                                             params['login']))
            raise exceptions.FailedToLogin(self.url,params['login'])
            return False
        else:
            return True

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

    def set_threadmarks_metadata(self,useurl,topsoup):
        header = topsoup.find('div',{'class':'threadmarkListingHeader'})
        if header:
            # logger.debug(header)
            desc = self.get_post_body(header)
            if desc:
                self.story.setMetadata("threadmarks_description",desc)
                if self.getConfig('use_threadmarks_description'):
                    self.setDescription(useurl,desc)
            # logger.debug(desc)
            title = header.find('h1',{'class':'threadmarkListingHeader-name'})
            if title:
                self.story.setMetadata("threadmarks_title",stripHTML(title))
            statusdt = header.find('dt',text="Index progress")
            if statusdt:
                statusdd = statusdt.find_next_sibling('dd')
                if statusdd:
                    threadmarks_status = stripHTML(statusdd)
                    self.story.setMetadata("threadmarks_status",threadmarks_status)
                    if self.getConfig('use_threadmarks_status'):
                        if 'Complete' in threadmarks_status:
                            self.story.setMetadata('status','Completed')
                        elif 'Incomplete' in threadmarks_status:
                            self.story.setMetadata('status','In-Progress')
                        else:
                            self.story.setMetadata('status',threadmarks_status)
            if self.getConfig('use_threadmarks_cover'):
                cover = header.find('span',{'class':'threadmarkListingHeader-icon'})
                # logger.debug(cover)
                if cover:
                    img = cover.find('img')
                    if img:
                        src = img['src']
                        if img.has_attr('srcset'):
                            src = img['srcset']
                        self.setCoverImage(useurl,src)
        return

    def get_forumtags(self,topsoup):
        return topsoup.find('div',{'class':'p-description'}).findAll('a',{'class':'tagItem'})

    def parse_author(self,souptag):
        a = souptag.find('section',{'class':'message-user'}).find('a',{'class':'username'})
        # logger.debug(a)
        self.story.addToList('authorId',a['href'].split('/')[-2])
        authorUrl = a['href'] # self.getURLPrefix()+'/'+a['href']
        self.story.addToList('authorUrl',authorUrl)
        self.story.addToList('author',a.text)

    def cache_posts(self,topsoup):
        for post in topsoup.find_all('article',{'class':'message--post'}):
            # logger.debug("Caching %s"%post['data-content'])
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
        return souptag.find('div',{'class':'block-outer-main--threadmarks'})

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
        retval = soupmarks.find('div',{'class':'structItemContainer'})
        if retval:
            ## SV, the first XF2 site, has an issue where the '...'
            ## fetcher link is placed outside the structItemContainer
            ## after the first one.  This finds it and sticks back in
            ## where we expect it.
            missing_fetcher = retval.find_next_sibling('div',{'class':'structItem--threadmark'})
            # logger.debug(missing_fetcher)
            if missing_fetcher:
                logger.debug("Fetcher URL outside structItemContainer, moving inside.")
                retval.append(missing_fetcher)
        return retval

    def get_threadmarks_from_list(self,tm_list):
        return tm_list.find_all('div',{'class':'structItem--threadmark'})

    def get_atag_from_threadmark(self,tm_item):
        return tm_item.find('a',{'data-tp-primary':'on'})

    def get_threadmark_range_url(self,tm_item,tmcat_num):
        fetcher = tm_item.find('div',{'data-xf-click':'threadmark-fetcher'})
        # logger.debug(fetcher)
        return self.getURLPrefix() + fetcher['data-fetchurl']

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
            # logger.warn('No date found in %s'%parenttag,exc_info=True)
            return None

    def make_reader_url(self,tmcat_num,reader_page_num):
        # https://xf2test.sufficientvelocity.com/threads/mauling-snarks-worm.41471/reader/page-4?threadmark_category=4
        return self.story.getMetadata('storyUrl')+'reader/page-'+unicode(reader_page_num)+'?threadmark_category='+tmcat_num

    def get_quote_expand_tag(self,soup):
        return soup.find_all('div',{'class':re.compile(r'bbCodeBlock-(expand|shrink)Link')})

    def get_spoiler_tags(self,topsoup):
        return topsoup.find_all('div',class_='bbCodeSpoiler')

    def convert_quotes(self,soup):
        ## make XF2 quote divs blockquotes so the spacing is the same
        ## as XF1.
        for tag in soup.find_all('div', class_="bbCodeBlock-expandContent"):
            tag.name='blockquote'
