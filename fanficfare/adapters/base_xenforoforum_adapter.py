#  -*- coding: utf-8 -*-

# Copyright 2016 FanFicFare team
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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

logger = logging.getLogger(__name__)

class BaseXenForoForumAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        # save for reader processing.
        self.reader = False

        #logger.info("init url: "+url)
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.


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
                self._setURL(self.getURLPrefix() + '/'+m.group('tp')+'/'+self.story.getMetadata('storyId')+'/')
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
        return r"https?://"+re.escape(self.getSiteDomain())+r"/(?P<tp>threads|posts)/(.+\.)?(?P<id>\d+)/?[^#]*?(#post-(?P<anchorpost>\d+))?$"

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
            # brute force way to deal with SB's http->https change when hardcoded http urls.
            url = url.replace('http://'+self.getSiteDomain(),self.getURLPrefix())

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
        return (is_chapter_url,url)


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
        params['register'] = '0'
        params['cookie_check'] = '1'
        params['_xfToken'] = ''
        params['redirect'] = 'https://' + self.getSiteDomain() + '/'

        ## https://forum.questionablequesting.com/login/login
        loginUrl = 'https://' + self.getSiteDomain() + '/login/login'
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
        ## after lazy load images, there are noscript blocks also
        ## containing <img> tags.  The problem comes in when they hit
        ## book readers such as Kindle and Nook and then you see the
        ## same images twice.
        for noscript in soup.find_all('noscript'):
            noscript.extract()
        return soup

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        useurl = self.url
        logger.info("url: "+useurl)

        try:
            (data,opened) = self._fetchUrlOpened(useurl)
            useurl = opened.geturl()
            logger.info("use useurl: "+useurl)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            elif e.code == 403:
                self.performLogin()
                (data,opened) = self._fetchUrlOpened(useurl)
                useurl = opened.geturl()
                logger.info("use useurl: "+useurl)
            else:
                raise

        # use BeautifulSoup HTML parser to make everything easier to find.
        topsoup = souptag = self.make_soup(data)

        h1 = souptag.find('div',{'class':'titleBar'}).h1
        ## SV has started putting 'Crossover' spans in the title h1.
        for tag in h1.find_all('span',{'class':'prefix'}):
            tag.extract()
        self.story.setMetadata('title',stripHTML(h1))

        first_post_title = self.getConfig('first_post_title','First Post')

        threadmark_chaps = False
        if '#' in useurl:
            anchorid = useurl.split('#')[1]
            souptag = souptag.find('li',id=anchorid)
        else:
            # try threadmarks if no '#' in , require at least 2.
            threadmarksa = souptag.find('a',{'class':'threadmarksTrigger'})
            if threadmarksa:
                soupmarks = self.make_soup(self._fetchUrl(self.getURLPrefix()+'/'+threadmarksa['href']))
                markas = []
                ol = soupmarks.find('ol',{'class':'overlayScroll'})
                if ol:
                    markas = ol.find_all('a')
                else:
                    ## SV changed their threadmarks.  Not isolated to
                    ## SV only incase SB or QQ make the same change.
                    markas = soupmarks.find('div',{'class':'threadmarks'}).find_all('a',{'class':'PreviewTooltip'})
                if len(markas) >= int(self.getConfig('minimum_threadmarks',2)):
                    threadmark_chaps = True
                    # remember if reader link found.
                    self.reader = topsoup.find('a',href=re.compile(r'\.'+self.story.getMetadata('storyId')+r"/reader$")) is not None

                    if self.getConfig('always_include_first_post'):
                        self.chapterUrls.append((first_post_title,useurl))

                    for (atag,url,name) in [ (x,x['href'],stripHTML(x)) for x in markas ]:
                        date = self.make_date(atag.find_next_sibling('div',{'class':'extra'}))
                        if not self.story.getMetadataRaw('datePublished') or date < self.story.getMetadataRaw('datePublished'):
                            self.story.setMetadata('datePublished', date)
                        if not self.story.getMetadataRaw('dateUpdated') or date > self.story.getMetadataRaw('dateUpdated'):
                            self.story.setMetadata('dateUpdated', date)

                        self.chapterUrls.append((name,self.getURLPrefix()+'/'+url))

            souptag = souptag.find('li',{'class':'message'}) # limit first post for date stuff below. ('#' posts above)

        self.handle_spoilers(topsoup,souptag)

        if threadmark_chaps or self.getConfig('always_use_forumtags'):
            ## only use tags if threadmarks for chapters or always_use_forumtags is on.
            for tag in topsoup.findAll('a',{'class':'tag'}) + topsoup.findAll('span',{'class':'prefix'}):
                tstr = stripHTML(tag)
                if self.getConfig('capitalize_forumtags'):
                    tstr = tstr.title()
                self.story.addToList('forumtags',tstr)

        # author moved down here to take from post URLs.
        a = souptag.find('h3',{'class':'userText'}).find('a')
        self.story.addToList('authorId',a['href'].split('/')[1])
        self.story.addToList('authorUrl',self.getURLPrefix()+'/'+a['href'])
        self.story.addToList('author',a.text)

        # Now go hunting for the 'chapter list'.
        bq = souptag.find('blockquote') # assume first posting contains TOC urls.

        bq.name='div'

        for iframe in bq.find_all('iframe'):
            iframe.extract() # calibre book reader & editor don't like iframes to youtube.

        for qdiv in bq.find_all('div',{'class':'quoteExpand'}):
            qdiv.extract() # Remove <div class="quoteExpand">click to expand</div>

        self.setDescription(useurl,bq)

        # otherwise, use first post links--include first post since
        # that's often also the first chapter.

        if not self.chapterUrls:
            self.chapterUrls.append((first_post_title,useurl))
            for (url,name) in [ (x['href'],stripHTML(x)) for x in bq.find_all('a') ]:
                (is_chapter_url,url) = self._is_normalize_chapterurl(url)
                if is_chapter_url and name != u"\u2191": # skip quote links as indicated by up arrow character.
                    self.chapterUrls.append((name,url))
                    if url == useurl and first_post_title == self.chapterUrls[0][0] \
                            and not self.getConfig('always_include_first_post',False):
                        # remove "First Post" if included in list.
                        del self.chapterUrls[0]

            # Didn't use threadmarks, so take created/updated dates
            # from the 'first' posting created and updated.
            date = self.make_date(souptag.find('a',{'class':'datePermalink'}))
            if date:
                self.story.setMetadata('datePublished', date)
                self.story.setMetadata('dateUpdated', date) # updated overwritten below if found.

            date = self.make_date(souptag.find('div',{'class':'editDate'}))
            if date:
                self.story.setMetadata('dateUpdated', date)

        self.story.setMetadata('numChapters',len(self.chapterUrls))

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
            logger.debug('No date found in %s'%parenttag,exc_info=True)
            return None

    # grab the text for an individual chapter.
    def getChapterTextNum(self, url, index):
        logger.debug('Getting chapter text from: %s index: %s' % (url,index))

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
            posts_per_page = self.getConfig("reader_posts_per_page",10)

            # always_include_first_post with threadmarks added an
            # extra first chapter, we should be past it.
            if self.getConfig('always_include_first_post'):
                index = index - 1
            reader_page_num = int((index+posts_per_page)/posts_per_page)
            reader_url=self.getURLPrefix()+'/threads/'+self.story.getMetadata('storyId')+'/reader?page='+unicode(reader_page_num)
            logger.debug("Reader URL to: %s"%reader_url)
            data = self._fetchUrl(reader_url)
            topsoup = souptag = self.make_soup(data)

            # assumed normalized to /posts/1234/
            anchorid = "post-"+url.split('/')[-2]
            logger.debug("anchorid: %s"%anchorid)
            souptag = topsoup.find('li',id=anchorid)
        else:
            logger.debug("DON'T USE READER MODE")
            (data,opened) = self._fetchUrlOpened(url)
            url = opened.geturl()
            if '#' in origurl and '#' not in url:
                url = url + origurl[origurl.index('#'):]
            logger.debug("chapter URL redirected to: %s"%url)

            topsoup = souptag = self.make_soup(data)

            if '#' in url:
                anchorid = url.split('#')[1]
                souptag = topsoup.find('li',id=anchorid)

        self.handle_spoilers(topsoup,souptag)

        bq = souptag.find('blockquote')

        bq.name='div'

        for iframe in bq.find_all('iframe'):
            iframe.extract() # calibre book reader & editor don't like iframes to youtube.

        for qdiv in bq.find_all('div',{'class':'quoteExpand'}):
            qdiv.extract() # Remove <div class="quoteExpand">click to expand</div>

        ## img alt="[​IMG]" class="bbCodeImage LbImage lazyload
        ## include lazy load images.
        for img in bq.find_all('img',{'class':'lazyload'}):
            img['src'] = img['data-src']

        # XenForo uses <base href="https://forums.spacebattles.com/" />
        return self.utf8FromSoup(self.getURLPrefix()+'/',bq)

    def handle_spoilers(self,topsoup,tag):
        '''
        Modifies tag given as required to do spoiler changes.
        '''
        if self.getConfig('remove_spoilers'):
            for div in tag.find_all('div',class_='bbCodeSpoilerContainer'):
                div.extract()
        elif self.getConfig('legend_spoilers'):
            for div in tag.find_all('div',class_='bbCodeSpoilerContainer'):
                div.name='fieldset'
                legend = topsoup.new_tag('legend')
                legend.string = stripHTML(div.button.span)
                div.insert(0,legend)
                div.button.extract()

