# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class TwistingTheHellmouthSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tth')
        self.dateformat = "%d %b %y"
        self.is_adult=False
        self.username = None
        self.password = None
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            
            # normalized story URL.
            self._setURL("http://"+self.getSiteDomain()\
                         +"/Story-"+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'www.tthfanfic.org'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://www.tthfanfic.org/Story-1234 http://www.tthfanfic.org/Story-1234/Author+Story+Title.htm http://www.tthfanfic.org/T-99999999/Story-1234-1/Author+Story+Title.htm http://www.tthfanfic.org/story.php?no=12345"

    # http://www.tthfanfic.org/T-999999999999/Story-12345-1/Author+Story+Title.htm
    # http://www.tthfanfic.org/Story-12345
    # http://www.tthfanfic.org/Story-12345/Author+Story+Title.htm
    # http://www.tthfanfic.org/story.php?no=12345
    def getSiteURLPattern(self):
        return r"http://www.tthfanfic.org(/(T-\d+/)?Story-|/story.php\?no=)(?P<id>\d+)(-\d+)?(/.*)?$"

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
        
        loginUrl = 'http://' + self.getSiteDomain() + '/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['urealname']))

        ## need to pull empty login page first to get ctkn and
        ## password name, which are BUSs
# <form method='post' action='/login.php' accept-charset="utf-8">
# <input type='hidden' name='ctkn' value='4bdf761f5bea06bf4477072afcbd0f8d721d1a4f989c09945a9e87afb7a66de1'/>
# <input type='text' id='urealname' name='urealname' value=''/>
# <input type='password' id='password' name='6bb3fcd148d148629223690bf19733b8'/>
# <input type='submit' value='Login' name='loginsubmit'/>
        soup = bs.BeautifulSoup(self._fetchUrl(loginUrl))
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
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e
            
        descurl = url
            
        if "<h2>Story Not Found</h2>" in data:
            raise exceptions.StoryDoesNotExist(url)
        
        if self.is_adult or self.getConfig("is_adult"):
            form = soup.find('form', {'id':'sitemaxratingform'})
            params={'ctkn':form.find('input', {'name':'ctkn'})['value'],
                    'sitemaxrating':'5'}
            logger.info("Attempting to get rating cookie for %s" % url)
            data = self._postUrl("http://"+self.getSiteDomain()+'/setmaxrating.php',params)
            # refetch story page.
            data = self._fetchUrl(url)
            soup = bs.BeautifulSoup(data)

        if "NOTE: This story is rated FR21 which is above your chosen filter level." in data:
            raise exceptions.AdultCheckRequired(self.url)

        # http://www.tthfanfic.org/AuthorStories-3449/Greywizard.htm
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/AuthorStories-\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[1].split('-')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',stripHTML(a))
        authorurl = 'http://'+self.host+a['href']

        try:
            # going to pull part of the meta data from *primary* author list page.
            logger.debug("**AUTHOR** URL: "+authorurl)
            authordata = self._fetchUrl(authorurl)
            descurl=authorurl
            authorsoup = bs.BeautifulSoup(authordata)
            # author can have several pages, scan until we find it.
            while( not authorsoup.find('a', href=re.compile(r"^/Story-"+self.story.getMetadata('storyId'))) ):
                nextarrow = authorsoup.find('a', {'class':'arrowf'})
                if not nextarrow:
                    ## if rating is set lower than story, it won't be
                    ## visible on author lists unless.  The *story* is
                    ## visible via the url, just not the entry on
                    ## author list.
                    raise exceptions.AdultCheckRequired(self.url)
                nextpage = 'http://'+self.host+nextarrow['href']
                logger.debug("**AUTHOR** nextpage URL: "+nextpage)
                authordata = self._fetchUrl(nextpage)
                descurl=nextpage
                authorsoup = bs.BeautifulSoup(authordata)
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
                infourl = 'http://'+self.host+ainfo['href']
                logger.debug("**StoryInfo** URL: "+infourl)
                infodata = self._fetchUrl(infourl)
                infosoup = bs.BeautifulSoup(infodata)

                # for a in infosoup.findAll('a',href=re.compile(r"^/Author-\d+")):
                #     self.story.addToList('authorId',a['href'].split('/')[1].split('-')[1])
                #     self.story.addToList('authorUrl','http://'+self.host+a['href'].replace("/Author-","/AuthorStories-"))
                #     self.story.addToList('author',stripHTML(a))

                # second verticaltable is the chapter list.
                table = infosoup.findAll('table',{'class':'verticaltable'})[1]
                for a in table.findAll('a',href=re.compile(r"^/Story-"+self.story.getMetadata('storyId'))):
                    autha = a.findNext('a',href=re.compile(r"^/Author-\d+"))
                    self.story.addToList('authorId',autha['href'].split('/')[1].split('-')[1])
                    self.story.addToList('authorUrl','http://'+self.host+autha['href'].replace("/Author-","/AuthorStories-"))
                    self.story.addToList('author',stripHTML(autha))
                    # include leading number to match 1. ... 2. ...
                    self.chapterUrls.append(("%d. %s by %s"%(len(self.chapterUrls)+1,
                                                             stripHTML(a),
                                                             stripHTML(autha)),'http://'+self.host+a['href']))
                                            
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
                    url = "http://"+self.host+o['value']
                    # just in case there's tags, like <i> in chapter titles.
                    self.chapterUrls.append((stripHTML(o),url))
    
        self.story.setMetadata('numChapters',len(self.chapterUrls))

        verticaltable = soup.find('table', {'class':'verticaltable'})

        BtVS = True
        BtVSNonX = False
        for cat in verticaltable.findAll('a', href=re.compile(r"^/Category-")):
            if cat.string not in ['General', 'Non-BtVS/AtS Stories', 'Non-BTVS/AtS Stories', 'BtVS/AtS Non-Crossover', 'Non-BtVS Crossovers']:
                self.story.addToList('category',cat.string)
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
        m = re.match('This story is No\. (?P<num>\d+) in the series &quot;(?P<series>.+)&quot;\.',
                     pseries.text)
        if m:
            self.setSeries(m.group('series'),m.group('num'))
            self.story.setMetadata('seriesUrl',"http://"+self.host+pseries.find('a')['href'])

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'storyinnerbody'})
        
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # strip out included chapter title, if present, to avoid doubling up.
        try:
            div.find('h3').extract()
        except:
            pass
        return self.utf8FromSoup(url,div)

def getClass():
    return TwistingTheHellmouthSiteAdapter

