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
from ..six.moves.urllib.parse import urlparse

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from .base_adapter import BaseSiteAdapter

ffnetgenres=["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
             "Friendship", "General", "Horror", "Humor", "Hurt-Comfort",
             "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual",
             "Supernatural", "Suspense", "Tragedy", "Western"]

ffnetpluscategories=["+Anima", "Rosario + Vampire", "Blood+",
                     "+C: Sword and Cornett", "Norn9 - ノルン+ノネット",
                     "Haré+Guu/ジャングルはいつもハレのちグゥ", "Lost+Brain",
                     "Wicked + The Divine", "Alex + Ada", "RE: Alistair++",
                     "Tristan + Isolde"]

class FanFictionNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','ffnet')

        self.set_story_idurl(url)

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

    def set_story_idurl(self,url):
        parsedUrl = urlparse(url)
        pathparts = parsedUrl.path.split('/',)
        self.story.setMetadata('storyId',pathparts[2])
        self.urltitle='' if len(pathparts)<5 else pathparts[4]
        # normalized story URL.
        self._setURL("https://"+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId')+"/1/"+self.urltitle)

    ## here so getSiteURLPattern and get_section_url(class method) can
    ## both use it.  Note adapter_fictionpresscom has one too.
    @classmethod
    def _get_site_url_pattern(cls):
        return r"https?://(www|m)?\.fanfiction\.net/s/(?P<id>\d+)(/\d+)?(/(?P<title>[^/]+))?/?$"

    @classmethod
    def get_section_url(cls,url):
        ## minimal URL used for section names in INI and reject list
        ## for comparison
        # logger.debug("pre--url:%s"%url)
        m = re.match(cls._get_site_url_pattern(),url)
        if m:
            url = "https://"+cls.getSiteDomain()\
                +"/s/"+m.group('id')+"/1/"
        # logger.debug("post-url:%s"%url)
        return url

    def getSiteURLPattern(self):
        return self._get_site_url_pattern()

    ## not actually putting urltitle on multi-chapters below, but
    ## one-shots will have it, so this is still useful.  normalized
    ## chapter URLs do NOT contain the story title.
    def normalize_chapterurl(self,url):
        return re.sub(r"https?://(www|m)\.(?P<keep>fanfiction\.net/s/\d+/\d+/).*",
                      r"https://www.\g<keep>",url)

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.origurl
        logger.debug("URL: "+url)

        data = self.get_request(url)
        #logger.debug("\n===================\n%s\n===================\n"%data)
        soup = self.make_soup(data)

        if "Unable to locate story" in data or "Story Not Found" in data:
            raise exceptions.StoryDoesNotExist(url)

        # some times "Chapter not found...", sometimes "Chapter text
        # not found..." or "Story does not have any chapters"
        if "Please check to see you are not using an outdated url." in data:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  'Chapter not found. Please check to see you are not using an outdated url.'" % url)

        if "Category for this story has been disabled" in data:
            raise exceptions.FailedToDownload("FanFiction.Net has removed the category for this story and will no longer serve it.")

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
                newdata = self.get_request(tryurl)
                if "not found. Please check to see you are not using an outdated url." not in newdata \
                        and "This request takes too long to process, it is timed out by the server." not in newdata:
                    logger.debug('=======Found newer chapter: %s' % tryurl)
                    soup = self.make_soup(newdata)
            except Exception as e:
                logger.warning("Caught exception in check_next_chapter URL: %s Exception %s."%(unicode(tryurl),unicode(e)))

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
            ## turns out there's only a handful of ffnet category's
            ## with '+' in.  Keep a list and look for them
            ## specifically instead of looking up the crossover page.
            crossover_cat = stripHTML(categories[0]).replace(" Crossover","")
            for pluscat in ffnetpluscategories:
                if pluscat in crossover_cat:
                    self.story.addToList('category',pluscat)
                    crossover_cat = crossover_cat.replace(pluscat,'')
            for cat in crossover_cat.split(' + '):
                if cat:
                    self.story.addToList('category',cat)

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
            logger.debug("cover_url:%s"%cover_url)

            authimg_url = ""
            if cover_url and self.getConfig('skip_author_cover') and self.getConfig('include_images'):
                try:
                    authsoup = self.make_soup(self.get_request(self.story.getMetadata('authorUrl')))
                    try:
                        img = authsoup.select_one('img.lazy.cimage')
                        authimg_url=img['data-original']
                    except:
                        img = authsoup.select_one('img.cimage')
                        if img:
                            authimg_url=img['src']

                    logger.debug("authimg_url:%s"%authimg_url)

                    ## ffnet uses different sizes on auth & story pages, but same id.
                    ## Old URLs:
                    ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/150/
                    ## //ffcdn2012t-fictionpressllc.netdna-ssl.com/image/1936929/180/
                    ## After Dec 2020 ffnet changes:
                    ## /image/6472517/180/
                    ## /image/6472517/150/
                    try:
                        cover_id = cover_url.split('/')[-3]
                    except:
                        cover_id = None
                    try:
                        authimg_id = authimg_url.split('/')[-3]
                    except:
                        authimg_id = None

                    ## don't use cover if it matches the auth image.
                    if cover_id and authimg_id and cover_id == authimg_id:
                        logger.debug("skip_author_cover: cover_url matches authimg_url: don't use")
                        cover_url = None
                except Exception as e:
                    logger.warning("Caught exception in skip_author_cover: %s."%unicode(e))

            if cover_url:
                self.setCoverImage(url,cover_url)


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

        ## AND explicitly put title URL back on chapter URL for fetch
        ## *only*--normalized chapter URL does NOT have urltitle
        data = self.get_request(url+self.urltitle)

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

