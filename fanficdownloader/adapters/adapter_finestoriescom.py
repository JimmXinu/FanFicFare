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
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FineStoriesComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FineStoriesComAdapter(BaseSiteAdapter):

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
        
        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2].split(':')[0])
        if 'storyInfo' in self.story.getMetadata('storyId'):
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/s/storyInfo.php?id='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fnst')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'finestories.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/s/10537 http://"+self.getSiteDomain()+"/s/10537:4010 http://"+self.getSiteDomain()+"/s/toryInfo.php?id=10537"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/s/")+r"(storyInfo.php\?id=)?\d+(:\d+)?(;\d+)?$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Free Registration' in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data:
            return True
        else:
            return False
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['theusername'] = self.username
            params['thepassword'] = self.password
        else:
            params['theusername'] = self.getConfig("username")
            params['thepassword'] = self.getConfig("password")
        params['rememberMe'] = '1'
        params['page'] = 'http://finestories.com/'
        params['submit'] = 'Login'
    
        loginUrl = 'http://' + self.getSiteDomain() + '/login.php'
        logging.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['theusername']))
    
        d = self._fetchUrl(loginUrl, params)
    
        if "My Account" not in d : #Member Account
            logging.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['theusername']))
            raise exceptions.FailedToLogin(url,params['theusername'])
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
            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',a.text)
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/a/\w+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.text)

        # Find the chapters:
        chapters = soup.findAll('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')+":\d+$"))
        if len(chapters) != 0:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/s/'+self.story.getMetadata('storyId')))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # surprisingly, the detailed page does not give enough details, so go to author's page
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        for lc2 in asoup.findAll('td', {'class' : 'lc2'}):
            if lc2.find('a')['href'] == '/s/'+self.story.getMetadata('storyId'):
                break
        
        self.story.addToList('category',lc2.find('div', {'class' : 'typediv'}).text)
        
        self.story.setMetadata('numWords', lc2.findNext('td', {'class' : 'num'}).text)
        
        lc4 = lc2.findNext('td', {'class' : 'lc4'})
        
        
        try:
            a = lc4.find('a', href=re.compile(r"/library/show_series.php\?id=\d+"))
            i = a.parent.text.split('(')[1].split(')')[0]
            self.setSeries(a.text, i)
        except:
            pass
        try:
            a = lc4.find('a', href=re.compile(r"/library/universe.php\?id=\d+"))
            self.story.addToList("category",a.text)
        except:
            pass
            
        for a in lc4.findAll('span', {'class' : 'help'}):
            a.extract()
            
        self.setDescription('http://'+self.host+'/s/'+self.story.getMetadata('storyId'),lc4.text.split('[More Info')[0])
            
        for b in lc4.findAll('b'):
            label = b.text
            value = b.nextSibling
            
            if 'For Age' in label:
                self.story.setMetadata('rating', value)
                
            if 'Tags' in label:
                for genre in value.split(', '):
                    self.story.addToList('genre',genre)
                    
            if 'Posted' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
            if 'Concluded' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
        status = lc4.find('span', {'class' : 'ab'})
        if  status != None:
            self.story.setMetadata('status', 'In-Progress')
            if "Last Activity" in status.text:
                self.story.setMetadata('dateUpdated', makeDate(status.text.split('Activity: ')[1].split(')')[0], self.dateformat))
        else:
            self.story.setMetadata('status', 'Completed')

            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'story'})
        
        # some big chapters are split over several pages
        pager = div.find('span', {'class' : 'pager'})
        if pager != None:
            urls=pager.findAll('a')
            urls=urls[:len(urls)-1]
            
            
            for ur in urls:
                soup = bs.BeautifulSoup(self._fetchUrl("http://"+self.getSiteDomain()+ur['href']),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
                div1 = soup.find('div', {'id' : 'story'})
                
                # appending next section
                last=div.findAll('p')
                next=div1.find('span', {'class' : 'conTag'}).nextSibling
            
                last[len(last)-1]=last[len(last)-1].append(next)
                div.append(div1)
            
            
            
        # removing all the left-over stuff    
        for a in div.findAll('span'):
            a.extract()
            
        for a in div.findAll('h1'):
            a.extract()
        for a in div.findAll('h2'):
            a.extract()
        for a in div.findAll('h3'):
            a.extract()
        for a in div.findAll('h4'):
            a.extract()
        for a in div.findAll('br'):
            a.extract()
        for a in div.findAll('div', {'class' : 'date'}):
            a.extract()
            
        a = div.find('form')
        if a != None:
            b = a.nextSibling
            while b != None:
                a.extract()
                a=b
                b=b.nextSibling
        

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
