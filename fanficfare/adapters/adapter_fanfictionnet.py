# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import re

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError
from ..six.moves.urllib.parse import urlparse

from ..browsercache import BrowserCache, BrowserCacheException

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from .base_adapter import BaseSiteAdapter,  makeDate

ffnetgenres=["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy", "Friendship", "General",
             "Horror", "Humor", "Hurt-Comfort", "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi",
             "Spiritual", "Supernatural", "Suspense", "Tragedy", "Western"]

class FanFictionNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','ffnet')

        self.set_story_idurl(url)

        self.origurl = url
        if "https://m." in self.origurl:
            ## accept m(mobile)url, but use www.
            self.origurl = self.origurl.replace("https://m.","https://www.")

        self.browser_cache = None
    @staticmethod
    def getSiteDomain():
        return 'www.fanfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fanfiction.net','m.fanfiction.net']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.fanfiction.net/s/1234/1/ https://www.fanfiction.net/s/1234/12/ http://www.fanfiction.net/s/1234/1/Story_Title http://m.fanfiction.net/s/1234/1/"

    def set_story_idurl(self,url):
        parsedUrl = urlparse(url)
        pathparts = parsedUrl.path.split('/',)
        self.story.setMetadata('storyId',pathparts[2])
        self.urltitle='' if len(pathparts)<5 else pathparts[4]
        # normalized story URL.
        self._setURL("https://"+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId')+"/1/"+self.urltitle)

    def getSiteURLPattern(self):
        return r"https?://(www|m)?\.fanfiction\.net/s/\d+(/\d+)?(/|/[^/]+)?/?$"

    def _postUrl(self, url,
                 parameters={},
                 headers={},
                 extrasleep=None,
                 usecache=True):
        logger.debug("_postUrl")
        raise NotImplementedError

    def _fetchUrlRawOpened(self, url,
                           parameters=None,
                           extrasleep=None,
                           usecache=True,
                           referer=None):
        logger.debug("_fetchUrlRawOpened")
        raise NotImplementedError

    def _fetchUrlOpened(self, url,
                        parameters=None,
                        usecache=True,
                        extrasleep=None,
                        referer=None):
        logger.debug("_fetchUrlOpened")
        raise NotImplementedError

    def _fetchUrlRaw(self, url,
                     parameters=None,
                     extrasleep=None,
                     usecache=True,
                     referer=None):
        ## This should be the one called for images.
        logger.debug("_fetchUrlRaw")
        raise NotImplementedError
    
    def _fetchUrl(self,url,parameters=None,extrasleep=1.0,usecache=True):

        if self.browser_cache is None:
            logger.debug("Start making self.browser_cache")
            try:
                if not self.getConfig("chrome_cache_path"):
                    raise exceptions.FailedToDownload("FFnet Workaround: chrome_cache_path setting must be set.")
                self.browser_cache = BrowserCache(self.getConfig("chrome_cache_path"))
            except (IOError, OSError) as e:
                # Workaround for PermissionError being py3 only.
                from errno import EACCES, EPERM, ENOENT
                if e.errno==EPERM or e.errno==EACCES:
                    raise exceptions.FailedToDownload("Permission to Chrome Cache (%s) denied--Did you quit Chrome?" % self.getConfig("chrome_cache_path"))
                else:
                    raise
            logger.debug("Done making self.browser_cache")
        data = self.browser_cache.get_data(url)
        if data is None:
            ## XXX Do something to collect list of failed URLs?
            ## Turn on continue on fail?
            raise exceptions.FailedToDownload("URL not found in Chrome Cache: %s" % url)
        logger.debug("%s:len(%s)"%(url,len(data)))
        return self.configuration._decode(data)

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## not actually putting urltitle on multi-chapters below, but
    ## one-shots will have it, so this is still useful.  normalized
    ## chapter URLs do NOT contain the story title.
    def normalize_chapterurl(self,url):
        return re.sub(r"https?://(www|m)\.(?P<keep>fanfiction\.net/s/\d+/\d+/).*",
                      r"https://www.\g<keep>",url)

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        get_cover=False
        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.origurl
        logger.debug("URL: "+url)
        # raise exceptions.FailedToDownload("The site fanfiction.net is blocking downloads.  Site is disabled in this version of FanFicFare.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            # logger.debug("\n===================\n%s\n===================\n"%data)
            soup = self.make_soup(data)
            # logger.debug("\n===================\n%s\n===================\n"%soup)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        if "Unable to locate story" in data or "Story Not Found" in data:
            raise exceptions.StoryDoesNotExist(url)

        # some times "Chapter not found...", sometimes "Chapter text
        # not found..." or "Story does not have any chapters"
        if "Please check to see you are not using an outdated url." in data:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  'Chapter not found. Please check to see you are not using an outdated url.'" % url)

        # <link rel="canonical" href="//www.fanfiction.net/s/13551154/100/Haze-Gray">
        canonicalurl = soup.select_one('link[rel=canonical]')['href']
        self.set_story_idurl(canonicalurl)

        if self.getConfig('check_next_chapter'):
            try:
                ## ffnet used to have a tendency to send out update
                ## notices in email before all their servers were
                ## showing the update on the first chapter.  It
                ## generates another server request and doesn't seem
                ## to be needed lately, so now default it to off.
                try:
                    chapcount = len(soup.find('select', { 'name' : 'chapter' } ).findAll('option'))
                # get chapter part of url.
                except:
                    chapcount = 1
                tryurl = "https://%s/s/%s/%d/%s"%(self.getSiteDomain(),
                                                  self.story.getMetadata('storyId'),
                                                  chapcount+1,
                                                  self.urltitle)
                logger.debug('=Trying newer chapter: %s' % tryurl)
                newdata = self._fetchUrl(tryurl)
                if "not found. Please check to see you are not using an outdated url." not in newdata \
                        and "This request takes too long to process, it is timed out by the server." not in newdata:
                    logger.debug('=======Found newer chapter: %s' % tryurl)
                    soup = self.make_soup(newdata)
            except HTTPError as e:
                if e.code == 503:
                    raise e
            except Exception as e:
                logger.warning("Caught an exception reading URL: %s Exception %s."%(unicode(url),unicode(e)))
                pass

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        ## Pull some additional data from html.

        ## ffnet shows category two ways
        ## 1) class(Book, TV, Game,etc) >> category(Harry Potter, Sailor Moon, etc)
        ## 2) cat1_cat2_Crossover
        ## For 1, use the second link.
        ## For 2, fetch the crossover page and pull the two categories from there.
        pre_links = soup.find('div',{'id':'pre_story_links'})
        categories = pre_links.findAll('a',{'class':'xcontrast_txt'})
        #print("xcontrast_txt a:%s"%categories)
        if len(categories) > 1:
            # Strangely, the ones with *two* links are the
            # non-crossover categories.  Each is in a category itself
            # of Book, Movie, etc.
            self.story.addToList('category',stripHTML(categories[1]))
        elif 'Crossover' in categories[0]['href']:
            # caturl = "https://%s%s"%(self.getSiteDomain(),categories[0]['href'])
            # catsoup = self.make_soup(self._fetchUrl(caturl))
            # found = False
            # for a in catsoup.findAll('a',href=re.compile(r"^/crossovers/.+?/\d+/")):
            #     self.story.addToList('category',stripHTML(a))
            #     found = True
            # if not found:
            #     # Fall back.  I ran across a story with a Crossver
            #     # category link to a broken page once.
            #     # http://www.fanfiction.net/s/2622060/1/
            #     # Naruto + Harry Potter Crossover
            #     logger.info("Fall back category collection")
            for c in stripHTML(categories[0]).replace(" Crossover","").split(' + '):
                self.story.addToList('category',c)

        a = soup.find('a', href=re.compile(r'https?://www\.fictionratings\.com/'))
        rating = a.string
        if 'Fiction' in rating: # if rating has 'Fiction ', strip that out for consistency with past.
            rating = rating[8:]

        self.story.setMetadata('rating',rating)

        # after Rating, the same bit of text containing id:123456 contains
        # Complete--if completed.
        gui_table1i = soup.find('div',{'id':'content_wrapper_inner'})

        self.story.setMetadata('title', stripHTML(gui_table1i.find('b'))) # title appears to be only(or at least first) bold tag in gui_table1i

        summarydiv = gui_table1i.find('div',{'style':'margin-top:2px'})
        if summarydiv:
            self.setDescription(url,stripHTML(summarydiv))


        grayspan = gui_table1i.find('span', {'class':'xgray xcontrast_txt'})
        # for b in grayspan.findAll('button'):
        #     b.extract()
        metatext = stripHTML(grayspan).replace('Hurt/Comfort','Hurt-Comfort')
        #logger.debug("metatext:(%s)"%metatext)

        if 'Status: Complete' in metatext:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        ## Newer BS libraries are discarding whitespace after tags now. :-/
        metalist = re.split(" ?- ",metatext)
        #logger.debug("metalist:(%s)"%metalist)

        # Rated: Fiction K - English - Words: 158,078 - Published: 02-04-11
        # Rated: Fiction T - English - Adventure/Sci-Fi - Naruto U. - Chapters: 22 - Words: 114,414 - Reviews: 395 - Favs: 779 - Follows: 835 - Updated: 03-21-13 - Published: 04-28-12 - id: 8067258

        # rating is obtained above more robustly.
        if metalist[0].startswith('Rated:'):
            metalist=metalist[1:]

        # next is assumed to be language.
        self.story.setMetadata('language',metalist[0])
        metalist=metalist[1:]

        # next might be genre.
        genrelist = metalist[0].split('/') # Hurt/Comfort already changed above.
        goodgenres=True
        for g in genrelist:
            #logger.debug("g:(%s)"%g)
            if g.strip() not in ffnetgenres:
                #logger.info("g not in ffnetgenres")
                goodgenres=False
        if goodgenres:
            self.story.extendList('genre',genrelist)
            metalist=metalist[1:]

        # Updated: <span data-xutime='1368059198'>5/8</span> - Published: <span data-xutime='1278984264'>7/12/2010</span>
        # Published: <span data-xutime='1384358726'>8m ago</span>
        dates = soup.findAll('span',{'data-xutime':re.compile(r'^\d+$')})
        if len(dates) > 1 :
            # updated get set to the same as published upstream if not found.
            self.story.setMetadata('dateUpdated',datetime.fromtimestamp(float(dates[0]['data-xutime'])))
        self.story.setMetadata('datePublished',datetime.fromtimestamp(float(dates[-1]['data-xutime'])))

        # Meta key titles and the metadata they go into, if any.
        metakeys = {
            # These are already handled separately.
            'Chapters':False,
            'Status':False,
            'id':False,
            'Updated':False,
            'Published':False,
            'Reviews':'reviews',
            'Favs':'favs',
            'Follows':'follows',
            'Words':'numWords',
            }

        chars_ships_list=[]
        while len(metalist) > 0:
            m = metalist.pop(0)
            if ':' in m:
                key = m.split(':')[0].strip()
                if key in metakeys:
                    if metakeys[key]:
                        self.story.setMetadata(metakeys[key],m.split(':')[1].strip())
                    continue
            # no ':' or not found in metakeys
            chars_ships_list.append(m)

        # all because sometimes chars can have ' - ' in them.
        chars_ships_text = (' - ').join(chars_ships_list)
        # print("chars_ships_text:%s"%chars_ships_text)
        # with 'pairing' support, pairings are bracketed w/o comma after
        # [Caspian X, Lucy Pevensie] Edmund Pevensie, Peter Pevensie
        self.story.extendList('characters',chars_ships_text.replace('[','').replace(']',',').split(','))

        l = chars_ships_text
        while '[' in l:
            self.story.addToList('ships',l[l.index('[')+1:l.index(']')].replace(', ','/'))
            l = l[l.index(']')+1:]

        if get_cover:
            # Try the larger image first.
            cover_url = ""
            try:
                img = soup.select_one('img.lazy.cimage')
                cover_url=img['data-original']
            except:
                img = soup.select_one('img.cimage:not(.lazy)')
                if img:
                    cover_url=img['src']
            ## Nov 19, 2020, ffnet lazy cover images returning 0 byte
            ## files.
            # logger.debug("cover_url:%s"%cover_url)

            # authimg_url = ""
            # if cover_url and self.getConfig('include_images') and self.getConfig('skip_author_cover'):
            #     authsoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))
            #     try:
            #         img = authsoup.select_one('img.lazy.cimage')
            #         authimg_url=img['data-original']
            #     except:
            #         img = authsoup.select_one('img.cimage')
            #         if img:
            #             authimg_url=img['src']

            #     logger.debug("authimg_url:%s"%authimg_url)

            #     ## ffnet uses different sizes on auth & story pages, but same id.
            #     ## Old URLs:
            #     ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/150/
            #     ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/180/
            #     ## After Dec 2020 ffnet changes:
            #     ## /image/6472517/180/
            #     ## /image/6472517/150/
            #     try:
            #         cover_id = cover_url.split('/')[-3]
            #     except:
            #         cover_id = None
            #     try:
            #         authimg_id = authimg_url.split('/')[-3]
            #     except:
            #         authimg_id = None

            #     ## don't use cover if it matches the auth image.
            #     if cover_id and authimg_id and cover_id == authimg_id:
            #         logger.debug("skip_author_cover: cover_url matches authimg_url: don't use")
            #         cover_url = None

            # if cover_url:
            #     self.setCoverImage(url,cover_url)


        # Find the chapter selector
        select = soup.find('select', { 'name' : 'chapter' } )

        if select is None:
            # no selector found, so it's a one-chapter story.
            self.add_chapter(self.story.getMetadata('title'),url)
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = u'https://%s/s/%s/%s/' % ( self.getSiteDomain(),
                                                 self.story.getMetadata('storyId'),
                                                 o['value'])
                # just in case there's tags, like <i> in chapter titles.
                title = u"%s" % o
                title = re.sub(r'<[^>]+>','',title)
                self.add_chapter(title,url)


        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        ## ffnet(and, I assume, fpcom) tends to fail more if hit too
        ## fast.  This is in additional to what ever the
        ## slow_down_sleep_time setting is.

        ## AND explicitly put title URL back on chapter URL for fetch
        ## *only*--normalized chapter URL does NOT have urltitle
        data = self._fetchUrl(url+self.urltitle,
                              extrasleep=4.0)

        if "Please email this error message in full to <a href='mailto:support@fanfiction.com'>support@fanfiction.com</a>" in data:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  FanFiction.net Site Error!" % url)

        soup = self.make_soup(data)

        div = soup.find('div', {'id' : 'storytextp'})

        if None == div:
            logger.debug('div id=storytextp not found.  data:%s'%data)
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return FanFictionNetSiteAdapter

