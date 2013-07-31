# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
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

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return NickAndGregNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class NickAndGregNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        
        
        # normalized story URL.
        # XXX Most sites don't have the /fanfic part.  Replace all to remove it usually.
        self._setURL('http://' + self.getSiteDomain() + '/desert_archive/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','nag')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y/%m/%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.nickandgreg.net'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/desert_archive/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/desert_archive/viewstory.php?sid=")+r"\d+$"
    

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+'&i=1'
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',a.string)
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/desert_archive/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        chapters = soup.find('select')
        for chapter in chapters.findAll('option'):
            if chapter.text != 'Story Index' and chapter.text != 'Chapters':
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/desert_archive/'+chapter['value']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        for div in asoup.findAll('td', {'class' : 'tblborder6'}):
            a = div.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
            if a != None:
                break
        
        self.setDescription(url,div.find('br').nextSibling)
        
        a=div.text.split('Rating:')
        if len(a) == 2: self.story.setMetadata('rating', a[1].split(' -')[0])
        
        a=div.text.split('Characters:')
        if len(a) == 2: 
        	for char in a[1].split(' -')[0].split(', '):
        	    self.story.addToList('characters',char)
        	    
        a=div.text.split('Genres:')
        if len(a) == 2: 
        	for genre in a[1].split(' -')[0].split(', '):
        	    self.story.addToList('genre',genre)
        	    
        a=div.text.split('Warnings:')
        if len(a) == 2: 
        	for warn in a[1].split(' -')[0].split(', '):
        	    if 'none' not in warn:
        	        self.story.addToList('warnings',warn)
        	    
        a=div.text.split('Completed:')
        if len(a) ==2:
            if 'Yes' in a[1]:
                self.story.setMetadata('status', 'Completed')
            else:
                self.story.setMetadata('status', 'In-Progress')
                
        a=div.text.split('Published:')
        if len(a) == 2: self.story.setMetadata('datePublished', makeDate(stripHTML(a[1].split(' -')[0]), self.dateformat))
        
        a=div.text.split('Updated:')
        if len(a) == 2: self.story.setMetadata('dateUpdated', makeDate(stripHTML(a[1].split(' -')[0]), self.dateformat))

            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('table', {'class' : 'tblborder6'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
