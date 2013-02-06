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
    return DotMoonNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class DotMoonNetAdapter(BaseSiteAdapter):

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
        
        # normalized story URL. www.dotmoon.net/library_view.php?storyid=3
        self._setURL('http://' + self.getSiteDomain() + '/library_view.php?storyid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','dotm')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.dotmoon.net'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/library_view.php?storyid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/library_view.php?storyid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'You must be logged in to read adult-rated stories' in data \
                or 'Password incorrect' in data \
                or "That username does not exist" in data:
            return True
        else:
            return False
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['user'] = self.username
            params['passwrd'] = self.password
        else:
            params['user'] = self.getConfig("username")
            params['passwrd'] = self.getConfig("password")

        loginUrl = 'http://' + self.getSiteDomain() + '/board/index.php'
        
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['user']))
    
        d = self._fetchUrl(loginUrl+'?action=login2&user='+params['user']+'&passwrd='+params['passwrd'])
        d = self._fetchUrl(loginUrl)
    
        if "Show unread posts since last visit" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['user']))
            raise exceptions.FailedToLogin(url,params['user'])
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
            
        if "Invalid story ID" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Invalid story ID.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        body=soup.findAll('body')[1]
        body.find('table').extract()
        
        ## Title
        a = body.find('b')
        self.story.setMetadata('title',a.string)
        
        # Find authorid and URL from... author url. http://www.dotmoon.net/board/index.php?action=profile;u=1'
        a = body.find('a', href=re.compile(r"index.php\?action=profile;u=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters: 'library_storyview.php?chapterid=3
        chapters=body.findAll('a', href=re.compile(r"library_storyview.php\?chapterid=\d+$"))
        if len(chapters)==0:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: No php/html chapters found.")
        if len(chapters)==1:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/'+chapters[0]['href']))
        else:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # other tags

        labels = body.find('table', {'width':'390'}).findAll('td')
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string
            
            if label != None:
                if 'Fandom' in label:
                    self.story.addToList('category',value.string)
                
                if 'Setting' in label:
                    self.story.addToList('genre',value.string)
                
                if 'Genre' in label:
                    self.story.addToList('genre',value.string)
                
                if 'Style' in label:
                    self.story.addToList('genre',value.string)
                
                if 'Rating' in label:
                    self.story.addToList('rating',value.string)
                
                if 'Created' in label:
                    self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
                if 'Updated' in label:
                    self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
        
                if 'Status' in label:
                    if 'Completed' in value.string:
                        self.story.setMetadata('status', 'Completed')
                    else:
                        self.story.setMetadata('status', 'In-Progress')
                        
        table=body.findAll('table', {'width':'400'})[1].find('td')
        self.setDescription(url,stripHTML(table).split('Summary: ')[1])
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('blockquote')
        div.name='div'

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
