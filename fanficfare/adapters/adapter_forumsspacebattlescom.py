#  -*- coding: utf-8 -*-

# Copyright 2015 FanFicFare team
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

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return ForumsSpacebattlesComAdapter

logger = logging.getLogger(__name__)

class ForumsSpacebattlesComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
							   
							   
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            
            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/threads/'+self.story.getMetadata('storyId')+'/')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fsb')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        #self.dateformat = "%Y-%b-%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'forums.spacebattles.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/threads/some-story-name.123456/"

    def getSiteURLPattern(self):
        # http://archiveofourown.org/collections/Smallville_Slash_Archive/works/159770
        # Discard leading zeros from story ID numbers--AO3 doesn't use them in it's own chapter URLs.
        return r"http://"+re.escape(self.getSiteDomain())+r"/threads/(.+\.)?(?P<id>\d+)/"
        
    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.info("url: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        a = soup.find('h3',{'class':'userText'}).find('a')
        self.story.addToList('authorId',a['href'].split('/')[1])
        self.story.addToList('authorUrl','http://'+self.getSiteDomain()+'/'+a['href'])
        self.story.addToList('author',a.text)

        self.story.addToList('genre','ForumFic')

        h1 = soup.find('div',{'class':'titleBar'}).h1
        self.story.setMetadata('title',stripHTML(h1))

        # Now go hunting for the 'chapter list'.
        firstpost = soup.find('blockquote') # assume first posting contains TOC urls.

        # try threadmarks first, require at least 2.
        threadmarksa = soup.find('a',{'class':'threadmarksTrigger'})
        if threadmarksa:
            soupmarks = self.make_soup(self._fetchUrl('http://'+self.getSiteDomain()+'/'+threadmarksa['href']))
            markas = soupmarks.find('ol',{'class':'overlayScroll'}).find_all('a')
            if len(markas) > 1:
                for (url,name) in [ (x['href'],stripHTML(x)) for x in markas ]:
                    self.chapterUrls.append((name,'http://'+self.getSiteDomain()+'/'+url))

        # otherwise, use first post links--include first post since that's 
        if not self.chapterUrls:
            logger.debug("len(firstpost):%s"%len(unicode(firstpost)))
            self.chapterUrls.append(("First Post",self.url))
            for (url,name) in [ (x['href'],stripHTML(x)) for x in firstpost.find_all('a') ]:
                if not url.startswith('http'):
                    url = 'http://'+self.getSiteDomain()+'/'+url
    
                if url.startswith('http://'+self.getSiteDomain()) and ('/posts/' in url or '/threads/' in url):
                    self.chapterUrls.append((name,url))
                    
        self.story.setMetadata('numChapters',len(self.chapterUrls))

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        (data,opened) = self._fetchUrlOpened(url)
        url = opened.geturl()
        logger.debug("chapter URL redirected to: %s"%url)

        soup = self.make_soup(data)

        if '#' in url:
            anchorid = url.split('#')[1]
            soup = soup.find('li',id=anchorid)
        bq = soup.find('blockquote')

        bq.name='div'

        return self.utf8FromSoup(url,bq)
