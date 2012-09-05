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
import cookielib as cl
from datetime import datetime
import json

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FimFictionNetSiteAdapter

class FimFictionNetSiteAdapter(BaseSiteAdapter):
    
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fimficnet')
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/',)[2])
        self._setURL("http://"+self.getSiteDomain()+"/story/"+self.story.getMetadata('storyId')+"/")
        self.is_adult = False
        
    @staticmethod
    def getSiteDomain():
        return 'www.fimfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        # mobile.fimifction.com isn't actually a valid domain, but we can still get the story id from URLs anyway
        return ['www.fimfiction.net','mobile.fimfiction.net', 'www.fimfiction.com', 'mobile.fimfiction.com']

    def getSiteExampleURLs(self):
        return "http://www.fimfiction.net/story/1234/story-title-here http://www.fimfiction.net/story/1234/ http://www.fimfiction.com/story/1234/1/ http://mobile.fimfiction.net/story/1234/1/story-title-here/chapter-title-here"

    def getSiteURLPattern(self):
        return r"http://(www|mobile)\.fimfiction\.(net|com)/story/\d+/?.*"
        
    def extractChapterUrlsAndMetadata(self):
        
        if self.is_adult or self.getConfig("is_adult"):
            cookieproc = urllib2.HTTPCookieProcessor()
            cookie = cl.Cookie(version=0, name='view_mature', value='true',
                               port=None, port_specified=False,
                               domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                               path='/story', path_specified=True,
                               secure=False,
                               expires=time.time()+10000,
                               discard=False,
                               comment=None,
                               comment_url=None,
                               rest={'HttpOnly': None},
                               rfc2109=False)
            cookieproc.cookiejar.set_cookie(cookie)
            self.opener = urllib2.build_opener(cookieproc)
        
        try:
            apiResponse = urllib2.urlopen("http://www.fimfiction.net/api/story.php?story=%s" % (self.story.getMetadata("storyId"))).read()
            apiData = json.loads(apiResponse)
            
            # Unfortunately, we still need to load the story index page to parse the characters
            data = self._fetchUrl(self.url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        
        if "Warning: mysql_fetch_array(): supplied argument is not a valid MySQL result resource" in data:
            raise exceptions.StoryDoesNotExist(self.url)

        if "/images/missing_story.png" in data:
            raise exceptions.StoryDoesNotExist(self.url)
        
        if "Invalid story id" in apiData.values():
            raise exceptions.StoryDoesNotExist(self.url)
        
        if "This story has been marked as having adult content." in data:
            raise exceptions.AdultCheckRequired(self.url)
        
        if self.password:
            params = {}
            params['password'] = self.password
            data = self._postUrl(self.url,params)

        if "Enter the password the author set for this story to view it." in data:
            if self.getConfig('fail_on_password'):
                raise exceptions.FailedToDownload("%s requires story password and fail_on_password is true."%self.url)
            else:
                raise exceptions.FailedToLogin(self.url,"Story requires individual password",passwdonly=True)
         
        storyMetadata = apiData["story"]    
            
        self.story.setMetadata("title", storyMetadata["title"])
        self.story.setMetadata("author", storyMetadata["author"]["name"])
        self.story.setMetadata("authorId", storyMetadata["author"]["id"])
        self.story.setMetadata("authorUrl", "http://%s/user/%s" % (self.getSiteDomain(), storyMetadata["author"]["name"]))
        
        chapters = [{"chapterTitle": chapter["title"], "chapterURL": chapter["link"]} for chapter in storyMetadata["chapters"]]
        for chapter in chapters:
            self.chapterUrls.append((chapter["chapterTitle"], chapter["chapterURL"]))
        self.story.setMetadata("numChapters", len(self.chapterUrls))
        
        # In the case of fimfiction.net, possible statuses are 'Completed', 'Incomplete', 'On Hiatus' and 'Cancelled'
        # For the sake of bringing it in line with the other adapters, 'Incomplete' and 'On Hiatus' become 'In-Progress'
        # and 'Complete' beomes 'Completed'. 'Cancelled' seems an important enough (not to mention more strictly true) 
        # status to leave unchanged.
        status = storyMetadata["status"].replace("Incomplete", "In-Progress").replace("On Hiatus", "In-Progress").replace("Complete", "Completed")
        self.story.setMetadata("status", status)
        self.story.setMetadata("rating", storyMetadata["content_rating_text"])
            
        for category in storyMetadata["categories"]:
            if storyMetadata["categories"][category]:
                self.story.addToList("genre", category) 

        self.story.setMetadata("numWords", str(storyMetadata["words"]))
        
        # fimfic is the first site with an explicit cover image.
        if self.getConfig('include_images') and "image" in storyMetadata.keys():
            coverurl = storyMetadata["image"]
            if coverurl.startswith('//static.fimfiction.net'): # fix for img urls missing 'http:'
                coverurl = "http:"+coverurl
            self.story.addImgUrl(self,self.url,coverurl,self._fetchUrlRaw,cover=True)
            
        self.setDescription(self.url, storyMetadata["description"])
        
        # Dates are in Unix time
        # Take the publish date from the first chapter posted
        rawDatePublished = storyMetadata["chapters"][0]["date_modified"]
        self.story.setMetadata("datePublished", datetime.fromtimestamp(rawDatePublished))
        rawDateUpdated = storyMetadata["date_modified"]
        self.story.setMetadata("dateUpdated", datetime.fromtimestamp(rawDateUpdated))
        
        soup = bs.BeautifulSoup(data).find("div", {"class":"story"})
        for character in [character_icon["title"] for character_icon in soup.findAll("a", {"class":"character_icon"})]:
            self.story.addToList("characters", character)
            
            
    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url),selfClosingTags=('br','hr')).find('div', {'id' : 'chapter_container'})
        if soup == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        return self.utf8FromSoup(url,soup)
        
