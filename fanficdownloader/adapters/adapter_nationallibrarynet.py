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
    return NationalLibraryNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class NationalLibraryNetAdapter(BaseSiteAdapter):

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
        
        # get storyId from url--url validation guarantees query is only storyid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?storyid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ntlb')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m-%d-%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        return 'national-library.net'
        
    @classmethod
    def getAcceptDomains(cls):
        return ['www.national-library.net','national-library.net']

    def getSiteExampleURLs(self):
        return "ONLY the stories archived on or after June 17, 2006 and that are hosted on the website: http://"+self.getSiteDomain()+"/viewstory.php?storyid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+"(www\.)?"+re.escape(self.getSiteDomain()+"/viewstory.php?storyid=")+r"\d+$"


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
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"authorresults.php\?author=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for p in soup.findAll('p'):
            chapters = p.findAll('a', href=re.compile(r'viewstory.php\?storyid='+self.story.getMetadata('storyId')+"&chapnum=\d+$"))
            if len(chapters) > 0:
                for chapter in chapters:
                    # just in case there's tags, like <i> in chapter titles.
                    self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))
                break

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        self.story.setMetadata('status', 'Completed')

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('b')
        for x in range(2,len(labels)):
            value = labels[x].nextSibling
            label = labels[x].string
            
            if 'Summary' in label:
                self.setDescription(url,value)
                #self.story.setMetadata('description',stripHTML(svalue))

            if 'Rating' in label:
                self.story.setMetadata('rating', stripHTML(value.nextSibling))

            if 'Word Count' in label:
                self.story.setMetadata('numWords', value.string)

            if 'Category' in label:
                for cat in value.string.split(', '):
                    self.story.addToList('category',cat)
            if 'Crossover Shows' in label:
                for cat in value.string.split(', '):
                    if "No Show" not in cat:
                        self.story.addToList('category',cat)

            if 'Character' in label:
                for char in value.string.split(', '):
                    self.story.addToList('characters',char)
                    
            if 'Pairing' in label:
                for char in value.string.split(', '):
                    self.story.addToList('ships',char)
                    
            if 'Warnings' in label:
                for warning in value.string.split(', '):
                    self.story.addToList('warnings',warning)

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Series' in label:
                self.setSeries(stripHTML(value.nextSibling), value.nextSibling.nextSibling.string[2:])
                self.story.setMetadata('seriesUrl','http://'+self.host+'/'+value.nextSibling['href'])
                
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        story=asoup.find('a', href=re.compile(r'viewstory.php\?storyid='+self.story.getMetadata('storyId')))
            
        a=story.findNext(text=re.compile('Genre')).parent.nextSibling.string.split(', ')
        for genre in a:
            self.story.setMetadata('genre', genre)
        
        a=story.findNext(text=re.compile('Archived'))
        self.story.setMetadata('datePublished', makeDate(stripHTML(a.parent.nextSibling), self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(stripHTML(a.parent.nextSibling), self.dateformat))
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div')
        
        # bit messy since higly inconsistent
        for p in soup.findAll('p', {'align' : 'center'}):
            p.extract()
        p = soup.findAll('p')
        for x in range(0,3):
            p[x].extract()
        if "Chapters: " in stripHTML(p[3]):
            p[3].extract()
        for x in range(len(p)-2,len(p)-1):
            p[x].extract()

        for p in soup.findAll('h1'):
            p.extract()
        for p in soup.findAll('h3'):
            p.extract()
        for p in soup.findAll('a'):
            p.extract()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
