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
import urllib
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FanFiktionDeAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FanFiktionDeAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/s/'+self.story.getMetadata('storyId') + '/1')
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ffde')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d.%m.%Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.fanfiktion.de'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/s/46ccbef30000616306614050"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/s/")+r"\w+(/\d+)?$"
        
        ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Diese Geschichte wurde als entwicklungsbeeintr' in data \
                or 'There is no such account on our website' in data \
                or "Noch kein registrierter Benutzer?" in data:
            return True
        else:
            return False
        
    def performLogin(self,url):
        params = {}

        if self.password:
            params['nickname'] = self.username
            params['passwd'] = self.password
        else:
            params['nickname'] = self.getConfig("username")
            params['passwd'] = self.getConfig("password")
        params['savelogindata'] = '1'
        params['a'] = 'l'
        params['submit'] = 'Login...'

        loginUrl = 'https://ssl.fanfiktion.de/'
        logging.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['nickname']))
        d = self._postUrl(loginUrl,params)
    
        if "Login erfolgreich" not in d : #Member Account
            logging.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['nickname']))
            raise exceptions.FailedToLogin(url,params['nickname'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

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
            
        if "Uhr ist diese Geschichte nur nach einer" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Auserhalb der Zeit von 23:00 Uhr bis 04:00 Uhr ist diese Geschichte nur nach einer erfolgreichen Altersverifikation zuganglich.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',a.string)
        
        # Find authorid and URL from... author url.
        head = soup.find('div', {'style' : 'width:85%;float:left;'})
        a = head.find('a')
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.find('select').findAll('option'):
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/s/'+self.story.getMetadata('storyId')+'/'+chapter['value']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        self.story.setMetadata('language','German')

        #find metadata on the story page
        self.story.setMetadata('datePublished', makeDate(head.text.split('erstellt: ')[1].split('\n')[0], self.dateformat))
        
        self.story.setMetadata('dateUpdated', makeDate(head.text.split('letztes Update: ')[1].split('\n')[0], self.dateformat))
        
        for genre in head.text.split('&nbsp;&nbsp;&nbsp;')[3].split('/')[0].split(', '):
            self.story.addToList('genre',genre)
            
        if 'fertiggestellt' in head.text:
            self.story.setMetadata('status', 'Fertiggestellt')
        else:
            self.story.setMetadata('status', 'In Arbeit')

        #find metadata on the author's page
        asoup = bs.BeautifulSoup(self._fetchUrl("http://"+self.getSiteDomain()+"?a=q&a1=v&t=nickdetailsstories&lbi=stories&ar=0&nick="+self.story.getMetadata('authorId')))
        tr=asoup.findAll('tr')
        for i in range(1,len(tr)):
            a = tr[i].find('a')
            if a['href'] == '/s/'+self.story.getMetadata('storyId'):
                break
        self.setDescription(url,a['onmouseover'].split("', '")[1])
        
        td = tr[i].findAll('td')
        self.story.addToList('category',td[1].string)
        self.story.setMetadata('rating', td[4].string)
        self.story.setMetadata('numWords', td[5].string)
 
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)
        time.sleep(0.5) ## ffde has "floodlock" protection

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'storytext'})
        for a in div.findAll('script'):
            a.extract()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
