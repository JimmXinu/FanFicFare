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
import re
import urllib2
import time

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

class TwistingTheHellmouthSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tth')
        self.dateformat = "%d %b %y"
        self.is_adult=False
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
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

    def getSiteExampleURLs(self):
        return "http://www.tthfanfic.org/Story-5583 http://www.tthfanfic.org/Story-5583/Greywizard+Marked+By+Kane.htm ttp://www.tthfanfic.org/T-526321777890480578489880055880/Story-26448-15/batzulger+Willow+Rosenberg+and+the+Mind+Riders.htm"

    # http://www.tthfanfic.org/T-526321777848988007890480555880/Story-26448-15/batzulger+Willow+Rosenberg+and+the+Mind+Riders.htm
    # http://www.tthfanfic.org/Story-5583
    # http://www.tthfanfic.org/Story-5583/Greywizard+Marked+By+Kane.htm
    def getSiteURLPattern(self):
        return r"http://www.tthfanfic.org/(T-\d+/)?Story-(?P<id>\d+)(-\d+)?(/.*)?$"

    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url=self.url
        logging.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e
            
        if "<h2>Story Not Found</h2>" in data:
            raise exceptions.StoryDoesNotExist(url)
        
        if "NOTE: This story is rated FR21 which is above your chosen filter level." in data:
            if self.is_adult or self.getConfig("is_adult"):
                form = soup.find('form', {'id':'sitemaxratingform'})
                params={'ctkn':form.find('input', {'name':'ctkn'})['value'],
                        'sitemaxrating':'5'}
                logging.info("Attempting to get rating cookie for %s" % url)
                data = self._postUrl("http://"+self.getSiteDomain()+'/setmaxrating.php',params)
                # refetch story page.
                data = self._fetchUrl(url)
                soup = bs.BeautifulSoup(data)
            else:
                raise exceptions.AdultCheckRequired(self.url)

        # http://www.tthfanfic.org/AuthorStories-3449/Greywizard.htm
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/AuthorStories-\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[1].split('-')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',stripHTML(a))

        try:
            # going to pull part of the meta data from author list page.
            logging.debug("author URL: "+self.story.getMetadata('authorUrl'))
            authordata = self._fetchUrl(self.story.getMetadata('authorUrl'))
            authorsoup = bs.BeautifulSoup(authordata)
            # author can have several pages, scan until we find it.
            while( not authorsoup.find('a', href=re.compile(r"^/Story-"+self.story.getMetadata('storyId'))) ):
                nextpage = 'http://'+self.host+authorsoup.find('a', {'class':'arrowf'})['href']
                logging.debug("author nextpage URL: "+nextpage)
                authordata = self._fetchUrl(nextpage)
                authorsoup = bs.BeautifulSoup(authordata)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        storydiv = authorsoup.find('div', {'id':'st'+self.story.getMetadata('storyId'), 'class':re.compile(r"storylistitem")})
        self.story.setMetadata('description',stripHTML(storydiv.find('div',{'class':'storydesc'})))
        self.story.setMetadata('title',stripHTML(storydiv.find('a',{'class':'storylink'})))

        verticaltable = soup.find('table', {'class':'verticaltable'})

        BtVS = True
        for cat in verticaltable.findAll('a', href=re.compile(r"^/Category-")):
            if cat.string not in ['General', 'Non-BtVS/AtS Stories', 'BtVS/AtS Non-Crossover']:
                self.story.addToList('category',cat.string)
            else:
                if cat.string == 'Non-BtVS/AtS Stories':
                    BtVS = False
        if BtVS:
            self.story.addToList('category','Buffy: The Vampire Slayer')

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
        
        return


    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'storyinnerbody'})
        
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # strip out included chapter title, if present, to avoid doubling up.
        try:
            div.find('h3').extract()
        except:
            pass
        return utf8FromSoup(div)

def getClass():
    return TwistingTheHellmouthSiteAdapter

