# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2017 FanFicFare team
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

from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
from urllib import unquote_plus

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from base_adapter import BaseSiteAdapter,  makeDate

ffnetgenres=["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy", "Friendship", "General",
             "Horror", "Humor", "Hurt-Comfort", "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi",
             "Spiritual", "Supernatural", "Suspense", "Tragedy", "Western"]

class FanFictionNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','ffnet')

        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # normalized story URL.
        self._setURL("https://"+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId')+"/1/")

        # ffnet update emails have the latest chapter URL.
        # Frequently, when they arrive, not all the servers have the
        # latest chapter yet and going back to chapter 1 to pull the
        # chapter list doesn't get the latest.  So save and use the
        # original URL given to pull chapter list & metadata.
        # Not used by plugin because URL gets normalized first for
        # eliminating duplicate story urls.
        self.origurl = url
        if "https://m." in self.origurl:
            ## accept m(mobile)url, but use www.
            self.origurl = self.origurl.replace("https://m.","https://www.")

    @staticmethod
    def getSiteDomain():
        return 'www.fanfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fanfiction.net','m.fanfiction.net']

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.fanfiction.net/s/1234/1/ https://www.fanfiction.net/s/1234/12/ http://www.fanfiction.net/s/1234/1/Story_Title http://m.fanfiction.net/s/1234/1/"

    def getSiteURLPattern(self):
        return r"https?://(www|m)?\.fanfiction\.net/s/\d+(/\d+)?(/|/[^/]+)?/?$"

    def _fetchUrl(self,url,parameters=None,extrasleep=1.0,usecache=True):
        ## ffnet(and, I assume, fpcom) tends to fail more if hit too
        ## fast.  This is in additional to what ever the
        ## slow_down_sleep_time setting is.
        return BaseSiteAdapter._fetchUrl(self,url,
                                         parameters=parameters,
                                         extrasleep=extrasleep,
                                         usecache=usecache)

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.origurl
        logger.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            #logger.debug("\n===================\n%s\n===================\n"%data)
            soup = self.make_soup(data)
        except urllib2.HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        if "Unable to locate story" in data:
            raise exceptions.StoryDoesNotExist(url)

        # some times "Chapter not found...", sometimes "Chapter text
        # not found..." or "Story does not have any chapters"
        if "Please check to see you are not using an outdated url." in data:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  'Chapter not found. Please check to see you are not using an outdated url.'" % url)

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
                tryurl = "https://%s/s/%s/%d/"%(self.getSiteDomain(),
                                                self.story.getMetadata('storyId'),
                                                chapcount+1)
                logger.debug('=Trying newer chapter: %s' % tryurl)
                newdata = self._fetchUrl(tryurl)
                if "not found. Please check to see you are not using an outdated url." not in newdata \
                        and "This request takes too long to process, it is timed out by the server." not in newdata:
                    logger.debug('=======Found newer chapter: %s' % tryurl)
                    soup = self.make_soup(newdata)
            except urllib2.HTTPError as e:
                if e.code == 503:
                    raise e
            except Exception as e:
                logger.warn("Caught an exception reading URL: %s Exception %s."%(unicode(url),unicode(e)))
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

        categories = soup.find('div',{'id':'pre_story_links'}).findAll('a',{'class':'xcontrast_txt'})
        #print("xcontrast_txt a:%s"%categories)
        if len(categories) > 1:
            # Strangely, the ones with *two* links are the
            # non-crossover categories.  Each is in a category itself
            # of Book, Movie, etc.
            self.story.addToList('category',stripHTML(categories[1]))
        elif 'Crossover' in categories[0]['href']:
            caturl = "https://%s%s"%(self.getSiteDomain(),categories[0]['href'])
            catsoup = self.make_soup(self._fetchUrl(caturl))
            found = False
            for a in catsoup.findAll('a',href=re.compile(r"^/crossovers/.+?/\d+/")):
                self.story.addToList('category',stripHTML(a))
                found = True
            if not found:
                # Fall back.  I ran across a story with a Crossver
                # category link to a broken page once.
                # http://www.fanfiction.net/s/2622060/1/
                # Naruto + Harry Potter Crossover
                logger.info("Fall back category collection")
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

        metalist = metatext.split(" - ")
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
                img = soup.select('img.lazy.cimage')
                cover_url=img[0]['data-original']
            except:
                img = soup.select('img.cimage')
                if img:
                    cover_url=img[0]['src']
            logger.debug("cover_url:%s"%cover_url)

            authimg_url = ""
            if cover_url and self.getConfig('skip_author_cover'):
                authsoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))
                try:
                    img = authsoup.select('img.lazy.cimage')
                    authimg_url=img[0]['data-original']
                except:
                    img = authsoup.select('img.cimage')
                    if img:
                        authimg_url=img[0]['src']

                logger.debug("authimg_url:%s"%authimg_url)

                ## ffnet uses different sizes on auth & story pages, but same id.
                ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/150/
                ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/180/
                try:
                    cover_id = cover_url.split('/')[4]
                except:
                    cover_id = None
                try:
                    authimg_id = authimg_url.split('/')[4]
                except:
                    authimg_id = None

                ## don't use cover if it matches the auth image.
                if cover_id and authimg_id and cover_id == authimg_id:
                    cover_url = None

            if cover_url:
                self.setCoverImage(url,cover_url)


        # Find the chapter selector
        select = soup.find('select', { 'name' : 'chapter' } )

        if select is None:
    	   # no selector found, so it's a one-chapter story.
    	   self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = u'https://%s/s/%s/%s/' % ( self.getSiteDomain(),
                                                 self.story.getMetadata('storyId'),
                                                 o['value'])
                # just in case there's tags, like <i> in chapter titles.
                title = u"%s" % o
                title = re.sub(r'<[^>]+>','',title)
                self.chapterUrls.append((title,url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        ## ffnet(and, I assume, fpcom) tends to fail more if hit too
        ## fast.  This is in additional to what ever the
        ## slow_down_sleep_time setting is.
        data = self._fetchUrl(url,extrasleep=4.0)

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

