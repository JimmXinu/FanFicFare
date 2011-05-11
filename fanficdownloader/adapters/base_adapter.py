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

import re
import datetime
import time
import urllib
import urllib2 as u2
import urlparse as up

from fanficdownloader.story import Story
from fanficdownloader.configurable import Configurable
from fanficdownloader.htmlcleanup import removeEntities, removeAllEntities, stripHTML
from fanficdownloader.exceptions import InvalidStoryURL

class BaseSiteAdapter(Configurable):

    @classmethod
    def matchesSite(cls,site):
        return site in cls.getAcceptDomains()

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain()]

    def validateURL(self):
        return re.match(self.getSiteURLPattern(), self.url)

    def __init__(self, config, url):
        Configurable.__init__(self, config)
        self.addConfigSection(self.getSiteDomain())
        self.addConfigSection("overrides")
        
        self.opener = u2.build_opener(u2.HTTPCookieProcessor())
        self.storyDone = False
        self.metadataDone = False
        self.story = Story()
        self.story.setMetadata('site',self.getSiteDomain())
        self.story.setMetadata('dateCreated',datetime.datetime.now())
        self.chapterUrls = [] # tuples of (chapter title,chapter url)
        self.decode = "utf8"
        self._setURL(url)
        if not self.validateURL():
            raise InvalidStoryURL(url,
                                  self.getSiteDomain(),
                                  self.getSiteExampleURLs())        

    def _setURL(self,url):
        self.url = url
        self.parsedUrl = up.urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path        
        self.story.setMetadata('storyUrl',self.url)

    # Assumes application/x-www-form-urlencoded.  parameters, headers are dict()s
    def _postUrl(self, url, parameters={}, headers={}):
        if self.getConfig('slow_down_sleep_time'):
            time.sleep(float(self.getConfig('slow_down_sleep_time')))

        ## u2.Request assumes POST when data!=None.  Also assumes data
        ## is application/x-www-form-urlencoded.
        if 'Content-type' not in headers:
            headers['Content-type']='application/x-www-form-urlencoded'
        if 'Accept' not in headers:
            headers['Accept']="text/html,*/*"
        req = u2.Request(url,
                         data=urllib.urlencode(parameters),
                         headers=headers)
        return self.opener.open(req).read().decode(self.decode)

    # parameters is a dict()
    def _fetchUrl(self, url, parameters=None):
        if self.getConfig('slow_down_sleep_time'):
            time.sleep(float(self.getConfig('slow_down_sleep_time')))
        if parameters:
            return self.opener.open(url,urllib.urlencode(parameters))\
                .read().decode(self.decode)
        else:
            return self.opener.open(url).read().decode(self.decode)

    # Does the download the first time it's called.
    def getStory(self):
        if not self.storyDone:
            self.getStoryMetadataOnly()
            for (title,url) in self.chapterUrls:
                self.story.addChapter(removeEntities(title),
                                      removeEntities(self.getChapterText(url)))
            self.storyDone = True
        return self.story

    def getStoryMetadataOnly(self):
        if not self.metadataDone:
            self.extractChapterUrlsAndMetadata()
            self.metadataDone = True
        return self.story

    ###############################
    
    @staticmethod
    def getSiteDomain():
        "Needs to be overriden in each adapter class."
        return 'no such domain'
    
    ## URL pattern validation is done *after* picking an adaptor based
    ## on domain instead of *as* the adaptor selector so we can offer
    ## the user example(s) for that particular site.
    ## Override validateURL(self) instead if you need more control.
    def getSiteURLPattern(self):
        "Used to validate URL.  Should be override in each adapter class."
        return '^http://'+re.escape(self.getSiteDomain())
    
    def getSiteExampleURLs(self):
        """
        Needs to be overriden in each adapter class.  It's the adapter
        writer's responsibility to make sure the example(s) pass the
        URL validate.
        """
        return 'no such example'
    
    def extractChapterUrlsAndMetadata(self):
        "Needs to be overriden in each adapter class.  Populates self.story metadata and self.chapterUrls"
        pass

    def getChapterText(self, url):
        "Needs to be overriden in each adapter class."
        pass
        

# this gives us a unicode object, not just a string containing bytes.
# (I gave soup a unicode string, you'd think it could give it back...)
def utf8FromSoup(soup):
    return soup.__str__('utf8').decode('utf-8')
