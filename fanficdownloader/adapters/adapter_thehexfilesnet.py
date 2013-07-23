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

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return TheHexFilesNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class TheHexFilesNetAdapter(BaseSiteAdapter):

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
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','thf')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y.%m.%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'thehexfiles.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.thehexfiles.net','thehexfiles.net']

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+"(www\.)?"+re.escape(self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

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
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',stripHTML(a))
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
		
        try:
            # in case link points somewhere other than the first chapter
            a = soup.findAll('option')[1]['value']
            self.story.setMetadata('storyId',a.split('=',)[1])
            url = 'http://'+self.host+'/'+a
            soup = bs.BeautifulSoup(self._fetchUrl(url))
        except:
            pass
		
        for info in asoup.findAll('table', {'cellspacing' : '4'}):
            a = info.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
            if a != None:
                self.story.setMetadata('title',stripHTML(a))
                break
		

        # Find the chapters:
        chapters=soup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+&i=1$'))
        if len(chapters) == 0:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

				
        cats = info.findAll('a',href=re.compile('categories.php'))
        for cat in cats:
            self.story.addToList('category',cat.string)
			
        words = info.find(text=re.compile('Words:')).split('|')[1].split(': ')[1]
        self.story.setMetadata('numWords', words)
		
        comp = info.find('span', {'class' : 'completed'}).string.split(': ')[1]
        if 'Yes' in comp:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')
						
        summary = info.find('td', {'class' : 'summary'})
        summary.name='div' # change td to div so it doesn't mess up the display when using table titlepage.
        self.setDescription(url,summary)
		
        rating=stripHTML(info.find('td', {'align' : 'left'})).split('(')[1].split(')')[0]
        self.story.setMetadata('rating', rating)

        labels = info.findAll('td', {'width' : '10%'})
        values = info.findAll('td', {'width' : '40%'})
        for i in range(0,len(labels)):
            value = stripHTML(values[i])
            label = stripHTML(labels[i])

            if 'Genres' in label:
                genres = value.split(', ')
                for genre in genres:
                    if genre != 'none':
                        self.story.addToList('genre',genre)
						

            if 'Warnings' in label:
                warnings = value.split(', ')
                for warning in warnings:
                    if warning != 'none':
                        self.story.addToList('warnings',warning)

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr','img')) # otherwise soup eats the br/hr tags.

        if None == soup:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        # Ugh.  chapter html doesn't haven't anything useful around it to demarcate.
        for a in soup.findAll('table'):
            a.extract()        

        for a in soup.findAll('head'):
            a.extract()

        html = soup.find('html')
        html.name='div'
            
        return self.utf8FromSoup(url,soup)
