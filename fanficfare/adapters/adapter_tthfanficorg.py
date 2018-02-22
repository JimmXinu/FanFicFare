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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import time

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class TwistingTheHellmouthSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tth')
        self.dateformat = u"%d\u00a0%b\u00a0%y" # &nbsp; becomes \u00a0 with bs4/html5lib.
        self.is_adult=False
        self.username = None
        self.password = None
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL("https://"+self.getSiteDomain()\
                         +"/Story-"+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'www.tthfanfic.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.tthfanfic.org/Story-1234 https://www.tthfanfic.org/Story-1234/Author+Story+Title.htm https://www.tthfanfic.org/T-99999999/Story-1234-1/Author+Story+Title.htm https://www.tthfanfic.org/story.php?no=12345"

    # http://www.tthfanfic.org/T-999999999999/Story-12345-1/Author+Story+Title.htm
    # http://www.tthfanfic.org/Story-12345
    # http://www.tthfanfic.org/Story-12345/Author+Story+Title.htm
    # http://www.tthfanfic.org/story.php?no=12345
    def getSiteURLPattern(self):
        return r"https?://www.tthfanfic.org(/(T-\d+/)?Story-|/story.php\?no=)(?P<id>\d+)(-\d+)?(/.*)?$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    # tth won't send you future updates if you aren't 'caught up'
    # on the story.  Login isn't required for F21, but logging in will
    # mark stories you've downloaded as 'read' on tth.
    def performLogin(self):
        params = {}

        if self.password:
            params['urealname'] = self.username
            params['password'] = self.password
        else:
            params['urealname'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['loginsubmit'] = 'Login'

        if not params['password']:
            return

        loginUrl = 'https://' + self.getSiteDomain() + '/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['urealname']))

        ## need to pull empty login page first to get ctkn and
        ## password name, which are BUSs
# <form method='post' action='/login.php' accept-charset="utf-8">
# <input type='hidden' name='ctkn' value='4bdf761f5bea06bf4477072afcbd0f8d721d1a4f989c09945a9e87afb7a66de1'/>
# <input type='text' id='urealname' name='urealname' value=''/>
# <input type='password' id='password' name='6bb3fcd148d148629223690bf19733b8'/>
# <input type='submit' value='Login' name='loginsubmit'/>
        soup = self.make_soup(self._fetchUrl(loginUrl))
        ## FYI, this will fail if cookiejar is shared, but
        ## use_pagecache is false.
        params['ctkn']=soup.find('input', {'name':'ctkn'})['value']
        params[soup.find('input', {'id':'password'})['name']] = params['password']

        d = self._fetchUrl(loginUrl, params)

        if "Stories Published" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                             params['urealname']))
            raise exceptions.FailedToLogin(self.url,params['urealname'])
            return False
        else:
            return True

    def setSiteMaxRating(self,url,data=None,soup=None):
        if not data:
            data = self._fetchUrl(url)
            soup = self.make_soup(data)

        if self.is_adult or self.getConfig("is_adult"):
            form = soup.find('form', {'id':'sitemaxratingform'})
            # if is_adult and rating isn't already set to FR21, set it so.
            if not form.find('option',{'value':'5'}).get('selected'):
                params={'ctkn':form.find('input', {'name':'ctkn'})['value'],
                        'sitemaxrating':'5'}
                logger.info("Attempting to get rating cookie for %s" % url)
                data = self._postUrl("https://"+self.getSiteDomain()+'/setmaxrating.php',params)
                # refetch story page.
                ## XXX - needs cache invalidate?  Or at least check that it this needs doing...
                data = self._fetchUrl(url,usecache=False)
                soup = self.make_soup(data)
        return (data,soup)

    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url=self.url
        logger.debug("URL: "+url)

        # tth won't send you future updates if you aren't 'caught up'
        # on the story.  Login isn't required for F21, but logging in will
        # mark stories you've downloaded as 'read' on tth.
        self.performLogin()

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            #print("data:%s"%data)
            soup = self.make_soup(data)
        except urllib2.HTTPError, e:
            if e.code in (404,410):
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        descurl = url

        if "<h2>Story Not Found</h2>" in data:
            raise exceptions.StoryDoesNotExist(url)

        ## conditionally set sitemaxrating
        (data,soup) = self.setSiteMaxRating(url,data,soup)

        if "NOTE: This story is rated FR21 which is above your chosen filter level." in data:
            raise exceptions.AdultCheckRequired(self.url)

        # http://www.tthfanfic.org/AuthorStories-3449/Greywizard.htm
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/AuthorStories-\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[1].split('-')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',stripHTML(a))
        authorurl = 'https://'+self.host+a['href']

        try:
            # going to pull part of the meta data from *primary* author list page.
            logger.debug("**AUTHOR** URL: "+authorurl)
            authordata = self._fetchUrl(authorurl)
            descurl=authorurl
            authorsoup = self.make_soup(authordata)
            # author can have several pages, scan until we find it.
            # find('a', href=re.compile(r"^/Story-"+self.story.getMetadata('storyId')+'/')) ):
            #logger.info("authsoup:%s"%authorsoup)
            while( not authorsoup.find('div', {'id':'st'+self.story.getMetadata('storyId'), 'class':re.compile(r"storylistitem")}) ):
                nextarrow = authorsoup.find('a', {'class':'arrowf'})
                if not nextarrow:
                    ## if rating is set lower than story, it won't be
                    ## visible on author lists unless.  The *story* is
                    ## visible via the url, just not the entry on
                    ## author list.
                    logger.info("Story Not Found on Author List--Assuming needs Adult.")
                    raise exceptions.FailedToDownload("Story Not Found on Author List--Assume needs Adult?")
                    # raise exceptions.AdultCheckRequired(self.url)
                nextpage = 'https://'+self.host+nextarrow['href']
                logger.debug("**AUTHOR** nextpage URL: "+nextpage)
                authordata = self._fetchUrl(nextpage)
                #logger.info("authsoup:%s"%authorsoup)
                descurl=nextpage
                authorsoup = self.make_soup(authordata)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        storydiv = authorsoup.find('div', {'id':'st'+self.story.getMetadata('storyId'), 'class':re.compile(r"storylistitem")})
        self.setDescription(descurl,storydiv.find('div',{'class':'storydesc'}))
        #self.story.setMetadata('description',stripHTML(storydiv.find('div',{'class':'storydesc'})))
        self.story.setMetadata('title',stripHTML(storydiv.find('a',{'class':'storylink'})))

        ainfo = soup.find('a', href='/StoryInfo-%s-1'%self.story.getMetadata('storyId'))
        if ainfo != None: # indicates multiple authors/contributors.
            try:
                # going to pull part of the meta data from author list page.
                infourl = 'https://'+self.host+ainfo['href']
                logger.debug("**StoryInfo** URL: "+infourl)
                infodata = self._fetchUrl(infourl)
                infosoup = self.make_soup(infodata)

                # for a in infosoup.findAll('a',href=re.compile(r"^/Author-\d+")):
                #     self.story.addToList('authorId',a['href'].split('/')[1].split('-')[1])
                #     self.story.addToList('authorUrl','https://'+self.host+a['href'].replace("/Author-","/AuthorStories-"))
                #     self.story.addToList('author',stripHTML(a))

                # second verticaltable is the chapter list.
                table = infosoup.findAll('table',{'class':'verticaltable'})[1]
                for a in table.findAll('a',href=re.compile(r"^/Story-"+self.story.getMetadata('storyId'))):
                    autha = a.findNext('a',href=re.compile(r"^/Author-\d+"))
                    self.story.addToList('authorId',autha['href'].split('/')[1].split('-')[1])
                    self.story.addToList('authorUrl','https://'+self.host+autha['href'].replace("/Author-","/AuthorStories-"))
                    self.story.addToList('author',stripHTML(autha))
                    # include leading number to match 1. ... 2. ...
                    self.chapterUrls.append(("%d. %s by %s"%(len(self.chapterUrls)+1,
                                                             stripHTML(a),
                                                             stripHTML(autha)),'https://'+self.host+a['href']))

            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(url)
                else:
                    raise e
        else: # single author:
            # Find the chapter selector
            select = soup.find('select', { 'name' : 'chapnav' } )

            if select is None:
        	   # no selector found, so it's a one-chapter story.
        	   self.chapterUrls.append((self.story.getMetadata('title'),url))
            else:
                allOptions = select.findAll('option')
                for o in allOptions:
                    url = "https://"+self.host+o['value']
                    # just in case there's tags, like <i> in chapter titles.
                    self.chapterUrls.append((stripHTML(o),url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        verticaltable = soup.find('table', {'class':'verticaltable'})

        BtVS = True
        BtVSNonX = False
        char=None
        romance=False
        for cat in verticaltable.findAll('a', href=re.compile(r"^/Category-")):
            # assumes only one -Centered and one Pairing: cat can ever
            # be applied to one story.
            # Seen at least once: incorrect (empty) cat link, thus "and cat.string"
            if self.getConfig('centeredcat_to_characters') and cat.string and cat.string.endswith('-Centered'):
                char = cat.string[:-len('-Centered')]
                self.story.addToList('characters',char)
            elif self.getConfig('pairingcat_to_characters_ships') and cat.string and cat.string.startswith('Pairing: '):
                pair = cat.string[len('Pairing: '):]
                self.story.addToList('characters',pair)
                if char:
                    self.story.addToList('ships',char+'/'+pair)
            elif cat.string not in ['General', 'Non-BtVS/AtS Stories', 'Non-BTVS/AtS Stories', 'BtVS/AtS Non-Crossover', 'Non-BtVS Crossovers']:
                # assumed only ship category after Romance cat.
                if self.getConfig('romancecat_to_characters_ships') and romance:
                    self.story.addToList('ships',cat.string)
                    for c in cat.string.split('/'):
                        self.story.addToList('characters',c)
                else:
                    self.story.addToList('category',cat.string)
                    if cat.string == 'Romance':
                        romance=True
            else:
                if 'Non-BtVS' in cat.string or 'Non-BTVS' in cat.string:
                    BtVS = False
                if 'BtVS/AtS Non-Crossover' == cat.string:
                    BtVSNonX = True

        verticaltabletds = verticaltable.findAll('td')
        self.story.setMetadata('rating', verticaltabletds[2].string)
        self.story.setMetadata('numWords', verticaltabletds[4].string)

        # Complete--if completed.
        if 'Yes' in verticaltabletds[10].string:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        #print("date:%s"%verticaltabletds[8])
        self.story.setMetadata('datePublished',makeDate(stripHTML(verticaltabletds[8].string), self.dateformat))
        self.story.setMetadata('dateUpdated',makeDate(stripHTML(verticaltabletds[9].string), self.dateformat))

        for icon in storydiv.find('span',{'class':'storyicons'}).findAll('img'):
            if( icon['title'] not in ['Non-Crossover'] ) :
                self.story.addToList('genre',icon['title'])
            else:
                if not BtVSNonX:
                    BtVS = False # Don't add BtVS if Non-Crossover, unless it's a BtVS/AtS Non-Crossover

        #print("BtVS: %s BtVSNonX: %s"%(BtVS,BtVSNonX))
        if BtVS:
            self.story.addToList('category','Buffy: The Vampire Slayer')

        pseries = soup.find('p', {'style':'margin-top:0px'})
        #print("pseries:%s"%pseries.get_text())
        m = re.match('This story is No\. (?P<num>\d+) in the series "(?P<series>.+)"\.',
                     pseries.get_text())
        if m:
            self.setSeries(m.group('series'),m.group('num'))
            self.story.setMetadata('seriesUrl',"https://"+self.host+pseries.find('a')['href'])

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'storyinnerbody'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # strip out included chapter title, if present, to avoid doubling up.
        try:
            div.find('h3').extract()
        except:
            pass
        return self.utf8FromSoup(url,div)

    ## Normalize chapter URLs because a) site has changed from http to
    ## https and b) in case of title change.  That way updates to
    ## existing stories don't re-download all chapters.
    def normalize_chapterurl(self,url):
        url = re.sub(r"https?://("+self.getSiteDomain()+"/Story-\d+(-\d+)?)(/.*)?$",
                     r"https://\1",url)
        return url

def getClass():
    return TwistingTheHellmouthSiteAdapter

