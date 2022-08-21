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

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_xenforoforum_adapter import BaseXenForoForumAdapter

logger = logging.getLogger(__name__)

class BaseXenForo2ForumAdapter(BaseXenForoForumAdapter):

    def __init__(self, config, url):
        BaseXenForoForumAdapter.__init__(self, config, url)

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return super(BaseXenForo2ForumAdapter, cls).getConfigSections() + ['base_xenforo2forum']

    def performLogin(self,data):
        params = {}

        if data and "Log in" not in data:
            ## already logged in.
            logger.debug("Already Logged In")
            return

        if self.password:
            params['login'] = self.username
            params['password'] = self.password
        else:
            params['login'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        if not params['password']:
            raise exceptions.FailedToLogin(self.url,"No username given.  Set in personal.ini or enter when prompted.")

        ## need a login token.
        data = self.get_request(self.getURLPrefix() + 'login',usecache=False)
        # logger.debug(data)
        # <input type="hidden" name="_xfToken" value="1556822458,710e5bf6fc87c67ea04ab56a910ac3ff" />
        find_token='<input type="hidden" name="_xfToken" value="'
        xftoken = data[data.index(find_token)+len(find_token):]
        xftoken = xftoken[:xftoken.index('"')]
        params['remember'] = '1'
        params['_xfToken'] = xftoken
        params['_xfRedirect'] = self.getURLPrefix()

        ## https://forum.questionablequesting.com/login/login
        loginUrl = self.getURLPrefix() + 'login/login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                             params['login']))

        d = self.post_request(loginUrl, params)

        if "Log in" in d:
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
                title.a.decompose() # remove RSS link.
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
                        elif 'Incomplete' in threadmarks_status or 'Ongoing' in threadmarks_status:
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
        stats = topsoup.find('span',class_='block-formSectionHeader-aligner')
        if stats:
            m = re.search(r' (?P<words>[^ ]+) words\)',stripHTML(stats))
            if m:
                self.story.setMetadata('estimatedWords',m.group('words'))
        return

    def get_forumtags(self,topsoup):
        return topsoup.find('div',{'class':'p-description'}).findAll('a',{'class':'tagItem'})

    def parse_author(self,souptag):
        user = souptag.find('section',{'class':'message-user'})
        a = user.find('a',{'class':'username'})
        authorUrl = None
        if a:
            # logger.debug(a)
            self.story.addToList('authorId',a['href'].split('/')[-2])
            authorUrl = a['href']
            if not authorUrl.startswith('http'):
                authorUrl = self.getURLDomain()+authorUrl
            self.story.addToList('authorUrl',authorUrl)
            self.story.addToList('author',a.text)
        else:
            # No author link found--it's a rare case, but at least one
            # thread had a 'Guest' account author.
            self.story.setMetadata('author',stripHTML(user.find('span',{'class':'username'})))
            self.story.setMetadata('authorUrl',self.getURLPrefix())
            self.story.setMetadata('authorId','0')

        # logger.debug("author_avatar_cover:%s"%self.getConfig('author_avatar_cover'))
        if self.getConfig('author_avatar_cover') and authorUrl:
            authorcard = self.make_soup(self.get_request(authorUrl))
            # logger.debug(authorcard)
            covera = authorcard.find('span',{'class':'avatarWrapper'}).find('a')
            if covera:
                self.setCoverImage(self.url,covera['href'])

    def cache_posts(self,topsoup):
        for post in topsoup.find_all('article',{'class':'message--post'}):
            # logger.debug("Caching %s"%post['data-content'])
            self.post_cache[post['data-content']] = post

    def get_first_post(self,topsoup):
        # limit=3 is an arbitrary assumption.
        posts = topsoup.find_all('article',{'class':'message--post'},limit=3)
        if self.getConfig("skip_sticky_first_posts",True):
            # don't use sticky first post (assumed to be Staff Post)
            for p in posts:
                if 'sticky-container' not in p['class']:
                    return p
            logger.warning("First X posts all sticky? Using first-first post.")
        return posts[0]

    def get_first_post_body(self,topsoup):
        return self.get_post_body(self.get_first_post(topsoup))

    def get_post_body(self,souptag):
        body = souptag.find('article',{'class':'message-body'}).find('div',{'class':'bbWrapper'})
        if self.getConfig('include_dice_rolls',False):
            # logger.debug("body:%s"%body)
            for fieldset in body.find_next_siblings('fieldset',class_='dice_container'):
                logger.debug("fieldset:%s"%fieldset)
                # body.append(fieldset.extract())
                ## If include_dice_rolls:svg, keep the <svg>
                ## up to the user to include
                ## add_to_keep_html_attrs:,style,xmlns,height,width,d,x,y,transform,text-anchor,cx,cy,r
                if self.getConfig('include_dice_rolls') != 'svg':
                    for d in fieldset.find_all('svg'):
                        result = d.select_one('title').extract()
                        result.name='span'
                        d.replace_with(result)
        return body

    def get_post_created_date(self,souptag):
        return self.make_date(souptag.find('div', {'class':'message-attribution-main'}))

    def get_post_updated_date(self,souptag):
        return self.make_date(souptag.find('div',{'class':'message-lastEdit'}))

    def get_threadmarks_top(self,souptag):
        return souptag.find('div',{'class':'block-outer-recent-threadmarks'})

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
        # logger.debug('data-fetchurl:%s'%fetcher)
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
            # logger.warning('No date found in %s'%parenttag,exc_info=True)
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

    def get_last_page_url(self,topsoup):
        ## <ul class="pageNav-main">
        ul = topsoup.find('ul',{'class':'pageNav-main'})
        # logger.debug(ul)
        lastpage = ul.find_all('a',href=re.compile(r'page-'))[-1]
        # logger.debug(lastpage)
        # doing make_soup will also cache posts from that last page.
        return lastpage['href']

    def fetch_forums_breadcrumbs(self,topsoup):
        '''
        Fetch 'breadcrumb' list of forum links, return as list of <a>
        tags.
        '''
        return topsoup.find("ul",{'class':'p-breadcrumbs'}).find_all('a',{'itemprop':'item'})
