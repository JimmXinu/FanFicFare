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
    return HennethAnnunNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class HennethAnnunNetAdapter(BaseSiteAdapter):

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
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/stories/chapter.cfm?stid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','htan')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.henneth-annun.net'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/stories/chapter.cfm?stid=1234"

    def getSiteURLPattern(self):
        return "http://"+self.getSiteDomain()+"/stories/chapter(_view)?.cfm\?stid="+r"\d+$"

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

            
        if "We're sorry. This story is not available." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: This story is not available.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('h2', {'id':'page_heading'})
        self.story.setMetadata('title',a.string)

        # Find the chapters: chapter_view.cfm?stid=6663&amp;spordinal=1" 
        for chapter in soup.findAll('a', href=re.compile(r'chapter_view.cfm\?stid='+self.story.getMetadata('storyId')+"&spordinal=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/stories/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        self.story.setMetadata('numWords', soup.find('tr', {'class':'foot'}).findAll('td')[1].text)

        self.setDescription(url,soup.find('div', {'id':'summary'}))

        # <span class="label">Rated:</span> NC-17<br /> etc
        info = soup.find('div', {'id':'storyinformation'})
        labels=info.findAll('b')
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string
                
            if 'Completion' in label:
                if 'Complete' in value.string:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Rating' in label:
                self.story.setMetadata('rating', value.string)

            if 'Era:' in label:
                self.story.addToList('category',value.string)

            if 'Genre' in label:
                self.story.addToList('genre',value.string)
                
        labels=info.findAll('strong')
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string
            
            if 'Author' in label:
                value=value.nextSibling
                self.story.setMetadata('authorId',value['href'].split('=')[1])
                self.story.setMetadata('authorUrl','http://'+self.host+'/'+value['href'])
                self.story.setMetadata('author',value.string)
                
            if 'Post' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated:' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
        for char in soup.findAll('a', href=re.compile(r"/resources/bios_view.cfm\?scid=\d+")):
            self.story.addToList('characters',stripHTML(char))
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'class' : 'block chapter'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
