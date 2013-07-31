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
    return SimplyUndeniableComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SimplyUndeniableComAdapter(BaseSiteAdapter):

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
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','sud')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.simplyundeniable.com'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Please log in now' in data \
                or 'There is no such account on our website' in data \
                or "That password doesn't match the one in our database" in data:
            return True
        else:
            return False
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['penname'] = self.username
            params['password'] = self.password
        else:
            params['penname'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['cookiecheck'] = '1'
        params['submit'] = 'Submit'
    
        loginUrl = 'http://' + self.getSiteDomain() + '/user.php?action=login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['penname']))
    
        d = self._fetchUrl(loginUrl, params)
    
        if "My Account" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['penname']))
            raise exceptions.FailedToLogin(url,params['penname'])
            return False
        else:
            return True

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

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        if "Please log in now" in data:
                raise exceptions.FailedToDownload(self.getSiteDomain() +" says: You need to have access to the restricted section.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',a.text)
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        for info in asoup.findAll('table', {'cellpadding' : '5'}):
            a = info.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
            if a != None:
                self.story.setMetadata('title',a.string)
                break
                
        # Find the chapters:
        if "Disclaimer" in data:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+&i=1$')):
            # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.
        
        a = info.find('td', {'valign' : 'top'}).find('p')
        self.setDescription(url,a)
        
        a = info.find('td', {'class' : 'greysm'}).findAll('b')
        self.story.setMetadata('datePublished', makeDate(stripHTML(a[0].nextSibling), self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(stripHTML(a[1].nextSibling), self.dateformat))
        if 'Yes' in a[2].nextSibling:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')
        self.story.setMetadata('rating', a[3].nextSibling)
        self.story.setMetadata('numWords', a[4].nextSibling)
        
        
        warnings = info.find('td', {'width' : '45'}).nextSibling.nextSibling.text.split(', ')
        for warning in warnings:
            if 'none' not in warning:
                self.story.addToList('warnings',warning)
        chars = info.find('td', {'width' : '51'}).nextSibling.nextSibling.text.split(', ')
        for char in chars:
            if '&' in char:
                self.story.addToList('ships',char)
            else:
                self.story.addToList('characters',char)
        genres = info.find('td', {'width' : '36'}).nextSibling.nextSibling.text.split(', ')
        for genre in genres:
            self.story.addToList('genre',genre)
            
        cat = info.find('a', href=re.compile(r'categories.php'))
        self.story.addToList('category',cat.string)
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('span', {'class' : 'style'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
