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
import re
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return NCISFictionComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class NCISFictionComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["iso-8859-1",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL("http://"+self.getSiteDomain()\
                         +"/chapters.php?stid="+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ncisfn')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d/%m/%Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.ncisfiction.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/story.php?stid=01234 http://"+self.getSiteDomain()+"/chapters.php?stid=1234"

    def getSiteURLPattern(self):
        return "http://"+self.getSiteDomain()+r'/(chapters|story)?.php\?stid=\d+'
       

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logging.debug("URL: "+url)

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
        soup = bs.BeautifulStoneSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title and author
        a = soup.find('div', {'class' : 'main_title'})
        
        aut = a.find('a')
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+aut['href'])
        self.story.setMetadata('author',aut.string)
        
        aut.extract()
        self.story.setMetadata('title',stripHTML(a)[:len(stripHTML(a))-2])

        # Find the chapters:
        i=0
        chapters=soup.findAll('table', {'class' : 'story_table'})
        for chapter in chapters:
            ch=chapter.find('a')
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(ch),'http://'+self.host+'/'+ch['href']))
            if i == 0:
                self.story.setMetadata('datePublished', makeDate(stripHTML(chapter.find('td')).split('Added: ')[1], self.dateformat))
            if i == len(chapters)-1:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(chapter.find('td')).split('Added: ')[1], self.dateformat))
            i=i+1

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        info = soup.find('table', {'class' : 'story_info'})
        
        # no convenient way to calculate word count as it is logged differently for stories with and without series
        
        labels = info.findAll('tr')
        for tr in labels:
            value = tr.find('td')
            label = tr.find('th').string

            if 'Summary' in label:
                self.setDescription(url,value)

            if 'Rating' in label:
                self.story.setMetadata('rating', value.string)

            if 'Category' in label:
                cats = value.findAll('a')
                for cat in cats:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                chars = value.findAll('a')
                for char in chars:
                    self.story.addToList('characters',char.string)

            if 'Pairing' in label:
                ships = value.findAll('a')
                for ship in ships:
                    self.story.addToList('ships',ship.string)

            if 'Genre' in label:
                genres = value.findAll('a')
                for genre in genres:
                    self.story.addToList('genre',genre.string)

            if 'Warnings' in label:
                warnings = value.findAll('a')
                for warning in warnings:
                    self.story.addToList('warnings',warning.string)

            if 'Status' in label:
                if 'not completed' in value.text:
                    self.story.setMetadata('status', 'In-Progress')
                else:
                    self.story.setMetadata('status', 'Completed')
                    
        try:
            # Find Series name from series URL.
            a = soup.find('div',{'class' : 'sub_header'})
            series_name = a.find('a').string
            i = a.text.split('#')[1]
            self.setSeries(series_name, i)
            
        except:
            # I find it hard to care if the series parsing fails
            pass
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'class' : 'story_text'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
