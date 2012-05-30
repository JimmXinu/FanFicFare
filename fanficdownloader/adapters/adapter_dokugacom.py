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

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return DokugaComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class DokugaComAdapter(BaseSiteAdapter): # XXX

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
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[3])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        self.story.setMetadata('section',self.parsedUrl.path.split('/',)[1])
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/'+self.parsedUrl.path.split('/',)[1]+'/story/'+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','dkg')

        # If all stories from the site fall into the same category,
        # the site itself isn't likely to label them as such, so we
        # do.
        self.story.addToList("category","InuYasha")

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        if 'fanfiction' in self.story.getMetadata('section'):
            self.dateformat = "%d %b %Y"
        else:
            self.dateformat = "%m-%d-%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.dokuga.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/fanfiction/story/1234/1 http://"+self.getSiteDomain()+"/spark/story/1234/1"

    def getSiteURLPattern(self):
        return r"http://"+self.getSiteDomain()+"/(fanfiction|spark)?/story/\d+/?\d+?$"


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
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title and author
        a = soup.find('div', {'align' : 'center'}).find('h3')
        
        # Find authorid and URL from... author url.
        aut = a.find('a')
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        alink='http://'+self.host+aut['href']
        self.story.setMetadata('authorUrl','http://'+self.host+aut['href'])
        self.story.setMetadata('author',aut.string)
        aut.extract()
        
        a = a.string[:(len(a.string)-4)]
        self.story.setMetadata('title',a)

        # Find the chapters:
        chapters = soup.find('select').findAll('option')
        if len(chapters)==1:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/'+self.story.getMetadata('section')+'/story/'+self.story.getMetadata('storyId')+'/1'))
        else:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles. /fanfiction/story/7406/1
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+self.story.getMetadata('section')+'/story/'+self.story.getMetadata('storyId')+'/'+chapter['value']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        asoup = bs.BeautifulSoup(self._fetchUrl(alink))
        
        if 'fanfiction' in self.story.getMetadata('section'):
            asoup=asoup.find('div', {'id' : 'cb_tabid_52'}).find('div')
        
            #grab the rest of the metadata from the author's page
            for div in asoup.findAll('div'):
                nav=div.find('a', href=re.compile(r'/fanfiction/story/'+self.story.getMetadata('storyId')+"/1$"))
                if nav != None:
                    break
            div=div.nextSibling
            self.setDescription(url,div)
        
            div=div.nextSibling
            self.story.setMetadata('rating', div.text.split('Rating: ')[1].split('&')[0])
        
            iscomp=div.text.split('Status: ')[1].split('&')[0]
            if 'Complete' in iscomp:
                self.story.setMetadata('status', 'Completed')
            else:
                self.story.setMetadata('status', 'In-Progress')
            
            self.story.addToList('category', div.text.split('Category: ')[1].split('&')[0])
            self.story.addToList('category', 'Fanfiction')
        
            self.story.setMetadata('datePublished', makeDate(stripHTML(div.text.split('Created: ')[1].split('&')[0]), self.dateformat))
        
            self.story.setMetadata('dateUpdated', makeDate(stripHTML(div.text.split('Updated: ')[1]), self.dateformat))
            
            div=div.nextSibling.nextSibling
            self.story.setMetadata('numWords', div.text.split('Words: ')[1].split('&')[0])
        
            for genre in div.text.split('Genre: ')[1].split('&')[0].split(', '):
                self.story.addToList('genre',genre)
        
        else:
            asoup=asoup.find('div', {'id' : 'maincol'}).find('div', {'class' : 'padding'})
            for div in asoup.findAll('div'):
                nav=div.find('a', href=re.compile(r'/spark/story/'+self.story.getMetadata('storyId')+"/1$"))
                if nav != None:
                    break
                    
            div=div.nextSibling.nextSibling
            self.setDescription(url,div)
            self.story.addToList('category', 'Spark')
            
            div=div.nextSibling.nextSibling
            self.story.setMetadata('rating', div.text.split('Rating: ')[1].split(' - ')[0])
            
            iscomp=div.text.split('Status: ')[1].split(' - ')[0]
            if 'Complete' in iscomp:
                self.story.setMetadata('status', 'Completed')
            else:
                self.story.setMetadata('status', 'In-Progress')
            
            for genre in div.text.split('Genre: ')[1].split(' - ')[0].split('/'):
                self.story.addToList('genre',genre)
                
            div=div.nextSibling.nextSibling
            
            date=div.text.split('Updated: ')[1].split('      -')[0]
            self.story.setMetadata('dateUpdated', makeDate(date, self.dateformat))
        
            # does not have published date anywhere
            self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
            
            self.story.setMetadata('numWords', div.text.split('Words ')[1])
            
        


            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'chtext'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
