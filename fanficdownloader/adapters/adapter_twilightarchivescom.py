# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team
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
    return TwilightArchivesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class TwilightArchivesComAdapter(BaseSiteAdapter):

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
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        
        
        # normalized story URL. http://www.twilightarchives.com/read/9353
        self._setURL('http://' + self.getSiteDomain() + '/read/'+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','twa')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.twilightarchives.com'
       

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/read/1234"

    def getSiteURLPattern(self):
        return re.escape("http://" + self.getSiteDomain()+"/read/")+r"\d+(/d+)?$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
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
        a = soup.find('h1')
        self.story.setMetadata('title',a.string)
        
        # Find the chapters:
        chapters=soup.find('ol', {'class' : 'chapters'})
        if chapters != None:
            for chapter in chapters.findAll('a', href=re.compile(r'/read/'+self.story.getMetadata('storyId')+"/\d+$")):
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
                
# rated, genre, warnings, seires

        summary = soup.find('p', {'class' : 'images'})
        self.setDescription(url,summary)

        for c in soup.findAll('h2', {'class' : 'title'}):
            div = c.nextSibling.nextSibling
            
            if 'Information' in c.text:
                for dt in div.findAll('dt'):
                    dd=dt.nextSibling.nextSibling
                    
                    if 'Author' in dt.text:
                        a=dd.find('a')
                        self.story.setMetadata('authorId',a['href'].split('/')[2])
                        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
                        self.story.setMetadata('author',a.text)
                        
                    if 'Words' in dt.text:
                        self.story.setMetadata('numWords', dd.text)
                        
                    if 'Published' in dt.text:
                        self.story.setMetadata('datePublished', makeDate(stripHTML(dd.text), self.dateformat))
            
                    if 'Updated' in dt.text:
                        self.story.setMetadata('dateUpdated', makeDate(stripHTML(dd.text), self.dateformat))
                    
                    if 'Status' in dt.text:
                        if 'Complete' in dd.text:
                            self.story.setMetadata('status', 'Completed')
                        else:
                            self.story.setMetadata('status', 'In-Progress')

            if 'Categories' in c.text:
                for a in div.findAll('a'):
                    self.story.addToList('category',a.text)
                    
            if 'Characters' in c.text:
                for a in div.findAll('a'):
                    self.story.addToList('category',a.text)

            if 'Series' in c.text:
                a=div.find('a')
                series_name = a.text
                series_url = 'http://'+self.host+a['href']
                
                seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
                storyas = seriessoup.find('tbody').findAll('a', href=re.compile(r'^/read/\d+$'))
                i=1
                for a in storyas:
                    if a['href'] == ('/read/'+self.story.getMetadata('storyId')):
                        self.setSeries(series_name, i)
                        self.story.setMetadata('seriesUrl',series_url)
                        break
                    i+=1
                    
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        a=asoup.find('tbody').find('a', href=re.compile(r'^/read/'+self.story.getMetadata('storyId')))
        self.story.setMetadata('rating',a.parent.nextSibling.nextSibling.text)
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'class' : 'size images medium'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
