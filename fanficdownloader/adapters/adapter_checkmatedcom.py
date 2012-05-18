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
    return CheckmatedComAdapter


class CheckmatedComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        self._setURL('http://' + self.getSiteDomain() + '/story.php?story='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','chm')

        # If all stories from the site fall into the same category,
        # the site itself isn't likely to label them as such, so we
        # do.
        self.story.addToList("category","Harry Potter")

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.checkmated.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/story.php?story=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/story.php?story=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites. This story is in The Bedchamber
    def needToLoginCheck(self, data):
        if 'This story is in The Bedchamber' in data \
                or 'That username is not in our database' in data \
                or "That password is not correct, please try again" in data:
            return True
        else:
            return False
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['name'] = self.username
            params['pass'] = self.password
        else:
            params['name'] = self.getConfig("username")
            params['pass'] = self.getConfig("password")
        params['login'] = 'yes'
        params['submit'] = 'login'	
	
        loginUrl = 'http://' + self.getSiteDomain()+'/login.php'
        d = self._fetchUrl(loginUrl,params)
        e = self._fetchUrl(url)

        if "Welcome back," not in d : #Member Account
            logging.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['name']))
            raise exceptions.FailedToLogin(url,params['name'])
            return False
        elif "This story is in The Bedchamber" in e:
            logging.info("Your account does not have sufficient priviliges to read this story.")
            return False
        else:
            return True


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

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        # The actual text that is used to announce you need to be an
        # adult varies from site to site.  Again, print data before
        # the title search to troubleshoot.
            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.findAll('span', {'class' : 'storytitle'})
        self.story.setMetadata('title',a[0].string)
        
        # Find authorid and URL from... author url.
        a = a[1].find('a', href=re.compile(r"authors.php\?name\=\w+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)
			
        a = soup.find('select', {'name' : 'chapter'})
        if a == None:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            for chapter in a.findAll('option'):
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/story.php?story='+self.story.getMetadata('storyId')+'&chapter='+chapter['value']))
			
        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

				
        # website does not keep track of word count, and there is no convenient way to calculate it

        summary = soup.find('fieldset')
        summary.find('legend').extract()
        summary.name='div'
        self.setDescription(url,summary)

		
        # <span class="label">Rated:</span> NC-17<br /> etc
        table = soup.findAll('div', {'class' : 'text'})[1]
        for labels in table.findAll('tr'):
            value = labels.findAll('td')[1]
            label = labels.findAll('td')[0]

			
            if 'Rating' in stripHTML(label):
                self.story.setMetadata('rating', stripHTML(value))

            if 'Ship' in stripHTML(label):
                for char in value.string.split('/'):
                    if char != 'none':
                        self.story.addToList('characters',char)		

            if 'Status' in stripHTML(label):
                if value.find('img', {'src' : 'img/incomplete.gif'}) == None:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in stripHTML(label):
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in stripHTML(label):
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
			
        a = self._fetchUrl(self.story.getMetadata('authorUrl')+'&cat=stories')	
        for story in bs.BeautifulSoup(a).findAll('table', {'class' : 'storyinfo'}):
            a = story.find('a', href=re.compile(r"review.php\?s\="+self.story.getMetadata('storyId')+'&act=view'))
            if a != None:
                for labels in story.findAll('tr'):
                    value = labels.findAll('td')[1]
                    label = labels.findAll('td')[0]
                    if 'genre' in stripHTML(label):
                        for genre in value.findAll('img'):
                            self.story.addToList('genre',genre['title'])
        
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'resizeableText'})
        div.find('div', {'class' : 'storyTools'}).extract()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
