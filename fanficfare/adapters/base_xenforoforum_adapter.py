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
logger = logging.getLogger(__name__)
import re
from xml.dom.minidom import parseString

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

logger = logging.getLogger(__name__)

class BaseXenForoForumAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        # save for reader processing.
        self.reader = False
        self.post_cache = {}
        self.threadmarks_for_reader = {}

        #logger.info("init url: "+url)
        BaseSiteAdapter.__init__(self, config, url)

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            #logger.debug("groupdict:%s"%m.groupdict())
            if m.group('anchorpost'):
                self.story.setMetadata('storyId',m.group('anchorpost'))
                self._setURL(self.getURLPrefix() + '/posts/'+m.group('anchorpost')+'/')
            else:
                self.story.setMetadata('storyId',m.group('id'))
                # normalized story URL.
                title = m.group('title') or ""
                self._setURL(self.getURLPrefix() + '/'+m.group('tp')+'/'+title+self.story.getMetadata('storyId')+'/')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fsb')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y at %I:%M %p"

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['base_xenforoforum',cls.getConfigSection()]

    @classmethod
    def getURLPrefix(cls):
        # The site domain.  Does have www here, if it uses it.
        return 'https://' + cls.getSiteDomain()

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.getURLPrefix()+"/threads/some-story-name.123456/ "+cls.getURLPrefix()+"/posts/123456/"

    def getSiteURLPattern(self):
        ## need to accept http and https still.
        return re.escape(self.getURLPrefix()).replace("https","https?")+r"/(?P<tp>threads|posts)/(?P<title>.+\.)?(?P<id>\d+)/?[^#]*?(#?post-(?P<anchorpost>\d+))?$"

    def _fetchUrlOpened(self, url,
                        parameters=None,
                        usecache=True,
                        extrasleep=2.0,
                        referer=None):
        ## We've been requested by the site(s) admin to rein in hits.
        ## This is in additional to what ever the slow_down_sleep_time
        ## setting is.
        return BaseSiteAdapter._fetchUrlOpened(self,url,
                                               parameters=parameters,
                                               usecache=usecache,
                                               extrasleep=extrasleep,
                                               referer=referer)

    ## For adapters, especially base_xenforoforum to override.  Make
    ## sure to return unchanged URL if it's NOT a chapter URL.  This
    ## is most helpful for xenforoforum because threadmarks use
    ## thread-name URLs--which can change if the thread name changes.
    def normalize_chapterurl(self,url):
        (is_chapter_url,normalized_url) = self._is_normalize_chapterurl(url)
        if is_chapter_url:
            return normalized_url
        else:
            return url

    ## returns (is_chapter_url,normalized_url)
    def _is_normalize_chapterurl(self,url):
        is_chapter_url = False

        ## moved from extract metadata to share with normalize_chapterurl.
        if not url.startswith('http'):
            url = self.getURLPrefix()+'/'+url

        if ( url.startswith(self.getURLPrefix()) or
             url.startswith('http://'+self.getSiteDomain()) or
             url.startswith('https://'+self.getSiteDomain()) ) and \
             ( '/posts/' in url or '/threads/' in url or 'showpost.php' in url or 'goto/post' in url):
            ## brute force way to deal with SB's http->https change
            ## when hardcoded http urls.  Now assumes all
            ## base_xenforoforum sites use https--true as of
            ## 2017-04-28
            url = url.replace('http://','https://')

            # http://forums.spacebattles.com/showpost.php?p=4755532&postcount=9
            url = re.sub(r'showpost\.php\?p=([0-9]+)(&postcount=[0-9]+)?',r'/posts/\1/',url)

            # http://forums.spacebattles.com/goto/post?id=15222406#post-15222406
            url = re.sub(r'/goto/post\?id=([0-9]+)(#post-[0-9]+)?',r'/posts/\1/',url)

            url = re.sub(r'(^[\'"]+|[\'"]+$)','',url) # strip leading or trailing '" from incorrect quoting.
            url = re.sub(r'like$','',url) # strip 'like' if incorrect 'like' link instead of proper post URL.

            #### moved from getChapterText()
            ## there's some history of stories with links to the wrong
            ## page.  This changes page#post URLs to perma-link URLs.
            ## Which will be redirected back to page#posts, but the
            ## *correct* ones.
            # https://forums.sufficientvelocity.com/posts/39915/
            if '#post-' in url:
                url = self.getURLPrefix()+'/posts/'+url.split('#post-')[1]+'/'

            ## Same as above except for for case where author mistakenly
            ## used the reply link instead of normal link to post.
            # "http://forums.spacebattles.com/threads/manager-worm-story-thread-iv.301602/reply?quote=15962513"
            # https://forums.spacebattles.com/posts/
            if 'reply?quote=' in url:
                url = self.getURLPrefix()+'/posts/'+url.split('reply?quote=')[1]+'/'

            ## normalize named thread urls, too.
            # http://forums.sufficientvelocity.com/threads/harry-potter-and-the-not-fatal-at-all-cultural-exchange-program.330/
            url = re.sub(r'/threads/.*\.([0-9]+)/',r'/threads/\1/',url)

            is_chapter_url = True

            ## One person once put a threadmarks URL directly in an
            ## index post and now we have to exclude it.
            if re.match(r".*/threads/[0-9]+/threadmarks",url):
                is_chapter_url = False

        return (is_chapter_url,url)

    def _section_url(self,url):
        ## domain is checked in configuration loop.  Can't check for
        ## storyId, because this is called before story url has been
        ## parsed.
        # logger.debug("pre--url:%s"%url)
        url = re.sub(r'/threads/.*\.(?P<id>[0-9]+)/',r'/threads/\g<id>/',url)
        # logger.debug("post-url:%s"%url)
        return url

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

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

        params['register'] = '0'
        params['cookie_check'] = '1'
        params['_xfToken'] = ''
        params['redirect'] = self.getURLPrefix() + '/'

        ## https://forum.questionablequesting.com/login/login
        loginUrl = self.getURLPrefix() + '/login/login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                             params['login']))

        d = self._fetchUrl(loginUrl, params)

        if "Log Out" not in d:
            logger.info("Failed to login to URL %s as %s" % (self.url,
                                                             params['login']))
            raise exceptions.FailedToLogin(self.url,params['login'])
            return False
        else:
            return True

    def make_soup(self,data):
        soup = super(BaseXenForoForumAdapter, self).make_soup(data)
        ## img class="lazyload"
        ## include lazy load images.
        for img in soup.find_all('img',{'class':'lazyload'}):
            img['src'] = img['data-src']

        ## after lazy load images, there are noscript blocks also
        ## containing <img> tags.  The problem comes in when they hit
        ## book readers such as Kindle and Nook and then you see the
        ## same images twice.
        for noscript in soup.find_all('noscript'):
            noscript.extract()

        for iframe in soup.find_all('iframe'):
            iframe.extract() # calibre book reader & editor don't like iframes to youtube.

        for qdiv in self.get_quote_expand_tag(soup):
            qdiv.extract() # Remove <div class="...">click to expand</div>

        self.convert_quotes(soup)

        self.handle_spoilers(soup)

        ## cache posts on page.
        self.cache_posts(soup)
        return soup

    def get_threadmarks_top(self,souptag):
        return souptag.find('div',{'class':'threadmarkMenus'})

    def get_threadmarks(self,navdiv):
        return navdiv.find_all('a',{'class':'OverlayTrigger','href':re.compile('threadmarks.*category_id=')})

    def get_threadmark_catnumname(self,threadmarksa):
        return (threadmarksa['href'].split('category_id=')[1],
                stripHTML(threadmarksa.find_previous('a',{'class':'threadmarksTrigger'})))

    def extract_threadmarks(self,souptag):
        threadmarks=[]
        # try threadmarks if no '#' in url
        navdiv = self.get_threadmarks_top(souptag)
        if not navdiv:
            return threadmarks
        threadmarksas = self.get_threadmarks(navdiv)

        threadmarkgroups = dict() # for ordering threadmarks
        ## Loop on threadmark categories.
        for threadmarksa in threadmarksas:
            (tmcat_num,tmcat_name) = self.get_threadmark_catnumname(threadmarksa)
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
            cats = list(threadmarkgroups.keys())
            # alphabetize for lack of a better idea to insure consist ordering
            cats.sort()
            for cat_name in cats:
                threadmarks.extend(threadmarkgroups[cat_name])
        return threadmarks

    def get_threadmarks_list(self,soupmarks):
        return soupmarks.find('div',{'class':'threadmarkList'})

    def get_threadmarks_from_list(self,tm_list):
        return tm_list.find_all('li',{'class':'threadmarkListItem'})

    def get_atag_from_threadmark(self,tm_item):
        return tm_item.find('a',{'class':'PreviewTooltip'})

    def get_threadmark_range_url(self,tm_item,tmcat_num):
        load_range = "threadmarks/load-range?min=%s&max=%s&category_id=%s"%(tm_item['data-range-min'],
                                                                            tm_item['data-range-max'],
                                                                            tmcat_num)
        return self.url+load_range

    def get_threadmark_date(self,tm_item):
        atag = self.get_atag_from_threadmark(tm_item)
        return self.make_date(atag.find_next_sibling('div',{'class':'extra'}))

    def get_threadmark_words(self,tm_item):
        words = kwords = ""
        atag = self.get_atag_from_threadmark(tm_item)
        if atag.parent.has_attr('data-words'):
            words = int(atag.parent['data-words'])
            if "(" in atag.next_sibling:
                kwords = atag.next_sibling.strip()
        return words,kwords

    def fetch_threadmarks(self,url,tmcat_name,tmcat_num, passed_tmcat_index=0, dedup=[]):
        threadmarks=[]
        if url in dedup:
            logger.debug("fetch_threadmarks(%s,tmcat_num=%s,passed_tmcat_index:%s,url=%s,dedup=%s)\nDuplicate threadmark URL, skipping"%(tmcat_name,tmcat_num, passed_tmcat_index, url, dedup))
            return threadmarks
        dedup = dedup + [url]
        soupmarks = self.make_soup(self._fetchUrl(url))
        tm_list = self.get_threadmarks_list(soupmarks)
        if not tm_list: # load-range don't match
            tm_list = soupmarks
        # logger.debug(tm_list)
        markas = []
        tmcat_index=passed_tmcat_index
        after = False
        for tm_item in self.get_threadmarks_from_list(tm_list):
            atag = self.get_atag_from_threadmark(tm_item)
            if not atag:
                threadmarks.extend(self.fetch_threadmarks(self.get_threadmark_range_url(tm_item,tmcat_num),
                                                          tmcat_name,
                                                          tmcat_num,
                                                          tmcat_index,
                                                          dedup))
                tmcat_index = len(threadmarks)
                after=True
            else:
                if after:
                    # logger.debug("AFTER "*10)
                    after=False
                url,name = atag['href'],stripHTML(atag)
                date = self.get_threadmark_date(tm_item)
                words,kwords = self.get_threadmark_words(tm_item)
                if 'http' not in url:
                    url = self.getURLPrefix()+"/"+url
                # logger.debug("%s. %s"%(tmcat_index,name))
                threadmarks.append({"tmcat_name":tmcat_name,
                                    "tmcat_num":tmcat_num,
                                    "tmcat_index":tmcat_index,
                                    "title":name,
                                    "url":url,
                                    "date":date,
                                    "words":words,
                                    "kwords":kwords})
                tmcat_index += 1
        return threadmarks

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        useurl = self.url
        logger.info("url: "+useurl)

        try:
            (data,opened) = self._fetchUrlOpened(useurl)
            useurl = opened.geturl()
            logger.info("use useurl: "+useurl)
        except HTTPError as e:
            # QQ gives 403, SV at least gives 404.  Which unfortunately
            if e.code == 403 or self.getConfig('always_login',False):
                self.performLogin()
                (data,opened) = self._fetchUrlOpened(useurl)
                useurl = opened.geturl()
                logger.info("use useurl: "+useurl)
            elif e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise
        if '#' not in useurl and '/posts/' not in useurl:
            self._setURL(useurl) ## for when threadmarked thread name changes.

        # use BeautifulSoup HTML parser to make everything easier to find.
        topsoup = souptag = self.make_soup(data)

        self.parse_title(topsoup)

        first_post_title = self.getConfig('first_post_title','First Post')

        use_threadmark_chaps = False
        if '#' in useurl:
            anchorid = useurl.split('#')[1]
            # souptag = souptag.find('li',id=anchorid)
            # cache is now loaded with posts from that reader
            # page.  looking for it in cache reuses code in
            # cache_posts that finds post tags.
            souptag = self.get_cache_post(anchorid)

        else:
            ## Also sets datePublished / dateUpdated to oldest / newest post datetimes.
            threadmarks = self.extract_threadmarks(souptag)

            if len(threadmarks) >= int(self.getConfig('minimum_threadmarks',2)):
                # remember if reader link found--only applicable if using threadmarks.
                self.reader = topsoup.find('a',href=re.compile(r'\.'+self.story.getMetadata('storyId')+r"/reader/?$")) is not None

                if self.getConfig('always_include_first_post'):
                    self.add_chapter(first_post_title,useurl)

                use_threadmark_chaps = True

                # spin threadmarks for date, to adjust tmcat_name/prepend.
                words = 0
                for tm in threadmarks:
                    # {"tmcat_name":tmcat_name,"tmcat_num":tmcat_num,"tmcat_index":tmcat_index,"title":title,"url":url,"date":date}
                    prepend=""
                    if 'tmcat_name' in tm:
                        tmcat_name = tm['tmcat_name']
                        if tmcat_name == 'Apocrypha' and self.getConfig('apocrypha_to_omake'):
                            tmcat_name = 'Omake'
                        if tmcat_name != "Threadmarks":
                            prepend = tmcat_name+" - "

                    if 'date' in tm:
                        date = tm['date']
                        if not self.story.getMetadataRaw('datePublished') or date < self.story.getMetadataRaw('datePublished'):
                            self.story.setMetadata('datePublished', date)
                        if not self.story.getMetadataRaw('dateUpdated') or date > self.story.getMetadataRaw('dateUpdated'):
                            self.story.setMetadata('dateUpdated', date)

                    if 'tmcat_num' in tm and 'tmcat_index' in tm:
                        self.threadmarks_for_reader[self.normalize_chapterurl(tm['url'])] = (tm['tmcat_num'],tm['tmcat_index'])

                    ## threadmark date, words available for chapter custom output
                    ## date formate from datethreadmark_format or dateCreated_format
                    ## then a basic default.
                    added = self.add_chapter(prepend+tm['title'],tm['url'],{'date':tm['date'].strftime(self.getConfig("datethreadmark_format",self.getConfig("dateCreated_format","%Y-%m-%d %H:%M:%S"))),
                                                                            'words':tm['words'],
                                                                            'kwords':tm['kwords']})
                    if added and tm.get('words',None):
                        words = words + tm['words']

                if words and self.getConfig('use_threadmark_wordcounts',True):
                    self.story.setMetadata('numWords',words)
            souptag = self.get_first_post(topsoup)

        if use_threadmark_chaps:
            self.set_threadmarks_metadata(useurl,topsoup)

        if use_threadmark_chaps or self.getConfig('always_use_forumtags'):
            ## only use tags if threadmarks for chapters or always_use_forumtags is on.
            for tag in self.get_forumtags(topsoup):
                tstr = stripHTML(tag)
                if self.getConfig('capitalize_forumtags'):
                    tstr = title(tstr)
                self.story.addToList('forumtags',tstr)

        # author moved down here to take from post URLs.
        self.parse_author(souptag)

        if self.getConfig('author_avatar_cover'):
            authorcard = self.make_soup(self._fetchUrl(authorUrl+"?card=1"))
            coverurl = '/'+authorcard.find('div',{'class':'avatarCropper'}).find('img')['src']
            self.setCoverImage(self.url,coverurl)
            ## https://forums.spacebattles.com/members/mp3-1415player.322925/?card=1
            ## <div class="avatarCropper">
            ##        <a class="avatar NoOverlay Av322925l" href="members/mp3-1415player.322925/">
            ##                <img src="data/avatars/l/322/322925.jpg?1471421076" alt="" style="left: 0px; top: -92px; " />
            ##        </a>
            ##
            ## </div>

        # Now get first post for description and chapter list if not
        # using threadmarks.
        index_post = self.get_post_body(souptag)

        if not self.story.getMetadata('description'):
            self.setDescription(useurl,index_post)

        # otherwise, use first post links--include first post since
        # that's often also the first chapter.

        if self.num_chapters() < 1 or self.getConfig('always_include_first_post_chapters',False):
            self.add_chapter(first_post_title,useurl)
            # logger.debug(index_post)
            for (url,name,tag) in [ (x['href'],stripHTML(x),x) for x in index_post.find_all('a',href=True) ]:
                (is_chapter_url,url) = self._is_normalize_chapterurl(url)
                # skip quote links as indicated by up arrow character or data-xf-click=attribution
                if is_chapter_url and name != u"\u2191" and tag.get("data-xf-click",None)!="attribution":
                    self.add_chapter(name,url)
                    if url == useurl and first_post_title == self.get_chapter(0,'url') \
                            and not self.getConfig('always_include_first_post',False):
                        # remove "First Post" if included in list.
                        self.del_chapter(0)

            # Didn't use threadmarks, so take created/updated dates
            # from the 'first' posting created and updated.
            date = self.get_post_created_date(souptag)
            if date:
                self.story.setMetadata('datePublished', date)
                self.story.setMetadata('dateUpdated', date) # updated overwritten below if found.

            date = self.get_post_updated_date(souptag)
            if date:
                self.story.setMetadata('dateUpdated', date)
            # logger.debug(self.story.getMetadata('datePublished'))
            # logger.debug(self.story.getMetadata('dateUpdated'))

    def parse_title(self,souptag):
        h1 = souptag.find('div',{'class':'titleBar'}).h1
        ## SV has started putting 'Crossover', 'Sci-Fi' etc spans in the title h1.
        for tag in h1.find_all('span',{'class':'prefix'}):
            ## stick them into genre.
            self.story.addToList('genre',stripHTML(tag))
            tag.extract()
        self.story.setMetadata('title',stripHTML(h1))

    def set_threadmarks_metadata(self,useurl,topsoup):
        # None in XF1.
        return

    def get_forumtags(self,topsoup):
        return topsoup.findAll('a',{'class':'tag'}) + topsoup.findAll('span',{'class':'prefix'})

    def parse_author(self,souptag):
        a = souptag.find('h3',{'class':'userText'}).find('a')
        self.story.addToList('authorId',a['href'].split('/')[1])
        authorUrl = self.getURLPrefix()+'/'+a['href']
        self.story.addToList('authorUrl',authorUrl)
        self.story.addToList('author',a.text)

    def get_first_post(self,topsoup):
        return topsoup.find('li',{'class':'message'}) # limit first post for date stuff below. ('#' posts above)

    def get_first_post_body(self,topsoup):
        bq = self.get_first_post(topsoup).find('blockquote',{'class':'messageText'})
        bq.name='div'
        return bq

    def get_post_body(self,souptag):
        bq = souptag.find('blockquote',{'class':'messageText'})
        if not bq:
            bq = souptag.find('div',{'class':'messageText'}) # cached gets if it was already used before
        bq.name='div'
        return bq

    def get_post_created_date(self,souptag):
        return self.make_date(souptag.find('a',{'class':'datePermalink'}))

    def get_post_updated_date(self,souptag):
        return self.make_date(souptag.find('div',{'class':'editDate'}))

    def make_date(self,parenttag): # forums use a BS thing where dates
                                   # can appear different if recent.
        datestr=None
        try:
            datetag = parenttag.find('span',{'class':'DateTime'})
            if datetag:
                datestr = datetag['title']
            else:
                datetag = parenttag.find('abbr',{'class':'DateTime'})
                if datetag:
                    datestr="%s at %s"%(datetag['data-datestring'],datetag['data-timestring'])
            # Apr 24, 2015 at 4:39 AM
            # May 1, 2015 at 5:47 AM
            datestr = re.sub(r' (\d[^\d])',r' 0\1',datestr) # add leading 0 for single digit day & hours.
            return makeDate(datestr, self.dateformat)
        except:
            logger.debug('No date found in %s, going on without'%parenttag,exc_info=True)
            return None

    def cache_posts(self,topsoup):
        for post in topsoup.find_all('li',id=re.compile('post-[0-9]+')):
            # logger.debug("Caching %s"%post['id'])
            self.post_cache[post['id']] = post

    def get_cache_post(self,postid):
        ## saved using original 'post-99999' id for key.
        postid=unicode(postid) # thank you, Py3.
        if '/posts/' in postid:
            ## allows chapter urls to be passed in directly.
            # assumed normalized to /posts/1234/
            postid = "post-"+postid.split('/')[-2]
        elif '#post-' in postid:
            postid = postid.split('#')[1]
        # logger.debug("get cache %s %s"%(postid,postid in self.post_cache))
        return self.post_cache.get(postid,None)

    # grab the text for an individual chapter.
    def getChapterTextNum(self, url, index):
        topsoup = None
        souptag = None
        logger.debug('Getting chapter text for: %s index: %s' % (url,index))

        origurl = url

        # reader mode shows only threadmarked posts in threadmark
        # order.  don't use reader mode for /threads/ urls, or
        # first post when always_include_first_post.
        if ( self.reader and
             self.getConfig("use_reader_mode",True) and
             '/threads/' not in url and
             (index > 0 or not self.getConfig('always_include_first_post')) ):
            logger.debug("USE READER MODE")
            # in case it changes:
            posts_per_page = int(self.getConfig("reader_posts_per_page",10))

            ## look forward a hardcoded 3 pages max in reader mode.
            for offset in range(0,3):
                souptag = self.get_cache_post(url)

                if not souptag and url in self.threadmarks_for_reader:
                    (tmcat_num,tmcat_index)=self.threadmarks_for_reader[url]
                    reader_page_num = int((tmcat_index+posts_per_page)/posts_per_page) + offset
                    logger.debug('Reader page offset:%s tmcat_num:%s tmcat_index:%s'%(offset,tmcat_num,tmcat_index))
                    reader_url=self.make_reader_url(tmcat_num,reader_page_num)
                    logger.debug("Fetch reader URL to: %s"%reader_url)
                    topsoup = self.make_soup(self._fetchUrl(reader_url))
                    # make_soup() loads cache with posts from that reader
                    # page.  looking for it in cache reuses code in
                    # cache_posts that finds post tags.
                    souptag = self.get_cache_post(url)
                else:
                    logger.debug("post found in cache")
                if souptag:
                    break

        if not souptag:
            logger.debug("DON'T USE READER MODE")

            souptag = self.get_cache_post(url)
            if not souptag:
                (data,opened) = self._fetchUrlOpened(url)
                url = unicode(opened.geturl())
                if '#' in origurl and '#' not in url:
                    url = url + origurl[origurl.index('#'):]
                    logger.debug("chapter URL redirected to: %s"%url)

                topsoup = self.make_soup(data)
                # make_soup() loads cache with posts from that reader
                # page.  looking for it in cache reuses code in
                # cache_posts that finds post tags.
                souptag = self.get_cache_post(url)
                if not souptag and '/threads/' in url: # first post uses /thread/ URL.
                    souptag = self.get_first_post(topsoup)

        # remove <div class="baseHtml noticeContent"> because it can
        # get confused for post content on first posts.
        for notice in souptag.find_all('div',{'class':'noticeContent'}):
            notice.extract()

        postbody = self.get_post_body(souptag)

        # XenForo uses <base href="https://forums.spacebattles.com/" />
        return self.utf8FromSoup(self.getURLPrefix()+'/',postbody)

    def make_reader_url(self,tmcat_num,reader_page_num):
        return self.getURLPrefix()+'/threads/'+self.story.getMetadata('storyId')+'/'+tmcat_num+'/reader?page='+unicode(reader_page_num)

    def get_quote_expand_tag(self,soup):
        return soup.find_all('div',{'class':'quoteExpand'})

    def get_spoiler_tags(self,topsoup):
        return topsoup.find_all('div',class_='bbCodeSpoilerContainer')

    def convert_quotes(self,soup):
        pass

    def handle_spoilers(self,topsoup):
        '''
        Modifies tag given as required to do spoiler changes.
        '''
        if self.getConfig('remove_spoilers'):
            for div in self.get_spoiler_tags(topsoup):
                div.extract()
        elif self.getConfig('legend_spoilers'):
            for div in self.get_spoiler_tags(topsoup):
                div.name='fieldset'
                # add copy of XF1 class name for convenience of
                # existing output_css when XF2.
                div['class'].append('bbCodeSpoilerContainer')
                legend = topsoup.new_tag('legend')
                legend.string = stripHTML(div.button.span)
                div.insert(0,legend)
                div.button.extract()

    def _do_utf8FromSoup(self,url,soup,fetch=None,allow_replace_br_with_p=True):
        if self.getConfig('replace_failed_smilies_with_alt_text'):
            for img in soup.find_all('img',src=re.compile(r'(^data:image|(failedtoload|clear.png)$)')):
                # logger.debug("replace_failed_smilies_with_alt_text img: %s"%img)
                clses = unicode(img['class']) # stringify list.
                if img.has_attr('alt') and ('mceSmilie' in clses or 'smilie--sprite' in clses):
                    ## Change the img to a span containing the alt
                    ## text, remove attrs.  This is a one-way change.
                    img.name='span'
                    img.string = img['alt'].replace('`','') # no idea why some have `
                    # not valid attrs on span.
                    del img['alt']
                    if img.has_attr('src'):
                        del img['src']
                    if img.has_attr('longdesc'):
                        del img['longdesc']
        return super(BaseXenForoForumAdapter, self)._do_utf8FromSoup(url,soup,fetch,allow_replace_br_with_p)

# from https://daviseford.com/blog/2017/04/27/python-string-to-title-including-punctuation.html
# fixes englisher contractions being title cased incorrectly.
def title(title):
    return re.sub(r"(?<=[a-z])[\']([A-Z])", lambda x: x.group().lower(), title.title())
