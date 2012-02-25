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

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return SiyeCoUkAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SiyeCoUkAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8",]# 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        # self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        # self.password = ""
        # self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/siye/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','siye') # XXX

        # If all stories from the site fall into the same category,
        # the site itself isn't likely to label them as such, so we
        # do.
        self.story.addToList("category","Harry Potter") # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y.%m.%d" # XXX
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.siye.co.uk' # XXX

    @classmethod
    def getAcceptDomains(cls):
        return ['www.siye.co.uk','siye.co.uk']

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/siye/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+r"(www\.)?siye\.co\.uk/(siye/)?"+re.escape("viewstory.php?sid=")+r"\d+$"

    # ## Login seems to be reasonably standard across eFiction sites.
    # def needToLoginCheck(self, data):
    #     if 'Registered Users Only' in data \
    #             or 'There is no such account on our website' in data \
    #             or "That password doesn't match the one in our database" in data:
    #         return True
    #     else:
    #         return False
        
    # def performLogin(self, url):
    #     params = {}

    #     if self.password:
    #         params['penname'] = self.username
    #         params['password'] = self.password
    #     else:
    #         params['penname'] = self.getConfig("username")
    #         params['password'] = self.getConfig("password")
    #     params['cookiecheck'] = '1'
    #     params['submit'] = 'Submit'
    
    #     loginUrl = 'http://' + self.getSiteDomain() + '/user.php?action=login'
    #     logging.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
    #                                                           params['penname']))
    
    #     d = self._fetchUrl(loginUrl, params)
    
    #     if "Member Account" not in d : #Member Account
    #         logging.info("Failed to login to URL %s as %s" % (loginUrl,
    #                                                           params['penname']))
    #         raise exceptions.FailedToLogin(url,params['penname'])
    #         return False
    #     else:
    #         return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # if self.is_adult or self.getConfig("is_adult"):
        #     # Weirdly, different sites use different warning numbers.
        #     # If the title search below fails, there's a good chance
        #     # you need a different number.  print data at that point
        #     # and see what the 'click here to continue' url says.
        #     addurl = "&ageconsent=ok&warning=4" # XXX
        # else:
        #     addurl=""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        # Except it doesn't this time. :-/
        url = self.url #+'&index=1'+addurl
        logging.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # if self.needToLoginCheck(data):
        #     # need to log in for this one.
        #     self.performLogin(url)
        #     data = self._fetchUrl(url)

        # # The actual text that is used to announce you need to be an
        # # adult varies from site to site.  Again, print data before
        # # the title search to troubleshoot.
        # if "Age Consent Required" in data: # XXX 
        #     raise exceptions.AdultCheckRequired(self.url)
            
        # if "Access denied. This story has not been validated by the adminstrators of this site." in data:
        #     raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/siye/'+a['href'])
        self.story.setMetadata('author',a.string)

        # need(or easier) to pull other metadata from the author's list page.
        authsoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))

        ## Title
        titlea = authsoup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',titlea.string)
        
        # Find the chapters (from soup, not authsoup):
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/siye/'+chapter['href']))

        if self.chapterUrls:
            self.story.setMetadata('numChapters',len(self.chapterUrls))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
            self.story.setMetadata('numChapters',1)

        # The stuff we can get from the chapter list/one-shot page are
        # in the first table with 95% width.
        metatable = soup.find('table',{'width':'95%'})

        # Categories
        cat_as = metatable.findAll('a', href=re.compile(r'categories.php'))
        for cat_a in cat_as:
            self.story.addToList('category',stripHTML(cat_a))

        moremetaparts = stripHTML(metatable).split('\n')
        for part in moremetaparts:
            part = part.strip()
            if part.startswith("Characters:"):
                part = part[part.find(':')+1:]
                for item in part.split(','):
                    if item.strip() == "Harry/Ginny":
                        self.story.addToList('characters',"Harry")
                        self.story.addToList('characters',"Ginny")
                    elif item.strip() not in ("None","All"):
                        self.story.addToList('characters',item)

            if part.startswith("Genres:"):
                part = part[part.find(':')+1:]
                for item in part.split(','):
                    if item.strip() != "None":
                        self.story.addToList('genre',item)

            if part.startswith("Warnings:"):
                part = part[part.find(':')+1:]
                for item in part.split(','):
                    if item.strip() != "None":
                        self.story.addToList('warnings',item)

            if part.startswith("Rating:"):
                part = part[part.find(':')+1:]
                self.story.setMetadata('rating',part)

            if part.startswith("Summary:"):
                part = part[part.find(':')+1:]
                self.setDescription(url,part)
                #self.story.setMetadata('description',part)
                
        # want to get the next tr of the table.
        #print("%s"%titlea.parent.parent.findNextSibling('tr'))
            
        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.
        moremeta = stripHTML(titlea.parent.parent.parent.find('div',{'class':'desc'}))
        for part in moremeta.replace(' - ','\n').split('\n'):
            #print("part:%s"%part)
            try:
                (name,value) = part.split(': ')
            except:
                # not going to worry about fancier processing for the bits
                # that don't match.
                continue
            name=name.strip()
            value=value.strip()
            if name == 'Published':
                self.story.setMetadata('datePublished', makeDate(value, self.dateformat))
            if name == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.dateformat))
            if name == 'Completed':
                if value == 'Yes':
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')
            if name == 'Words':
                self.story.setMetadata('numWords', value)

        try:
            # Find Series name from series URL.
            a = titlea.findPrevious('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
            storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
            i=1
            for a in storyas:
                if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                    self.setSeries(series_name, i)
                    break
                i+=1
            
        except:
            # I find it hard to care if the series parsing fails
            pass        

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        # soup = bs.BeautifulSoup(self._fetchUrl(url))
        # BeautifulSoup objects to <p> inside <span>, which
        # technically isn't allowed.
        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.

        # not the most unique thing in the world, but it appears to be
        # the best we can do here.
        story = soup.find('span', {'style' : 'font-size: 100%;'})
        
        if None == story:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,story)
