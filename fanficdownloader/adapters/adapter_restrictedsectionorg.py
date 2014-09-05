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
import cookielib as cl
from datetime import datetime

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return RestrictedSectionOrgSiteAdapter

class RestrictedSectionOrgSiteAdapter(BaseSiteAdapter):
    
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
            
        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        
        # normalized story URL.
        # get story/file and storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            
            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/' + m.group('filestory') + '.php?' + m.group('filestory') + '=' + self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        
        self.story.setMetadata('siteabbrev','ressec')
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y" # 20 Nov 2005
        
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        return 'www.restrictedsection.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/story.php?story=1234 http://"+cls.getSiteDomain()+"/file.php?file=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r"/(?P<filestory>file|story).php\?(file|story)=(?P<id>\d+)$"
        
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        # one-shot stories use file url instead of story.  'Luckily',
        # we don't have to worry about one-shots becoming
        # multi-chapter because ressec is frozen.  Still need 'story'
        # url for metadata, however.
        try:
            if 'file' in url:
                data = self._postUrlUP(url)
                soup = bs.BeautifulSoup(data)
                storya = soup.find('a',href=re.compile(r"^story.php\?story=\d+"))
                url = 'http://'+self.host+'/'+storya['href'].split('&')[0]  # strip rs_session

                fileas = soup.find('a',href=re.compile(r"^file.php\?file=\d+"))
                if fileas:
                    for filea in fileas:
                        if 'Previous Chapter' in filea.string or 'Next Chapter' in filea.string:
                            raise exceptions.FailedToDownload(self.getSiteDomain() +" Cannot use chapter url with multi-chapter stories on this site.")
                    
            logger.debug("metadata URL: "+url)
            data = self._fetchUrl(url)
            # print data
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
        if "Story not found" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Story not found.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        # check user/pass on a chapter for multi-chapter
        if 'file' not in self.url:
            self._postUrlUP('http://'+self.host+'/'+soup.find('a', href=re.compile(r"^file.php\?file=\d+"))['href'])

        ## Title
        h2 = soup.find('h2')

        # Find authorid and URL from... author url.
        a = h2.find('a')
        ahref = a['href'].split('&')[0]  # strip rs_session
        
        self.story.setMetadata('authorId',ahref.split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+ahref)
        self.story.setMetadata('author',stripHTML(a))

        # title, remove byauthorname.
        auth=stripHTML(a)
        title=stripHTML(h2)
        self.story.setMetadata('title',title[:title.index(" by "+auth)])

        dates = soup.findAll('span', {'class':'date'})
        if dates: # only for multi-chapter
            self.story.setMetadata('datePublished', makeDate(stripHTML(dates[0]), self.dateformat))
            self.story.setMetadata('dateUpdated', makeDate(stripHTML(dates[-1]), self.dateformat))

        words = soup.findAll('span', {'class':'size'})
        wordcount=0
        for w in words:
            wordcount = wordcount + int(w.string[:-6].replace(',',''))

        self.story.setMetadata('numWords',"%s"%wordcount)

        self.story.setMetadata('rating', soup.find('a',href=re.compile(r"^rating.php\?rating=\d+")).string)
        
        # other tags

        labels = soup.find('table', {'class':'info'}).findAll('th')
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string
            
            if label != None:
                
                if 'Categories' in label:
                    for g in stripHTML(value).split('\n'):
                        self.story.addToList('genre',g)
                
                if 'Pairings' in label:
                    for g in stripHTML(value).split('\n'):
                        self.story.addToList('ships',g)
                
                if 'Summary' in label:
                    self.setDescription(url,stripHTML(value).replace("\n"," ").replace("\r",""))
                    value.extract() # remove summary incase it contains file URLs.

                if 'Updated' in label: # one-shots only.
                    print "value:%s"%value
                    value.find('sup').extract() # remove 'st', 'nd', 'th' ordinals
                    print "value:%s"%value
                    date = makeDate(stripHTML(value), '%d %B %Y') # full month name
                    self.story.setMetadata('datePublished', date)

                if 'Length' in label: # one-shots only.
                    self.story.setMetadata('numWords',value.string[:-6])
                    
        # one-shot.
        if 'file' in self.url:
            self.chapterUrls.append((self.story.getMetadata('title'),self.url))
        else: # multi-chapter
            # Find the chapters: 'library_storyview.php?chapterid=3
            chapters=soup.findAll('a', href=re.compile(r"^file.php\?file=\d+"))
            if len(chapters)==0:
                raise exceptions.FailedToDownload(self.getSiteDomain() +" says: No chapters found.")
            else:
                for chapter in chapters:
                    chhref = chapter['href'].split('&')[0] # strip rs_session
                    # just in case there's tags, like <i> in chapter titles.
                    self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chhref))

        self.story.setMetadata('numChapters',len(self.chapterUrls))



    def _postUrlUP(self, url):
        params = {}
        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['accept.x'] = 1
        params['accept.y'] = 1

        excpt=None
        for sleeptime in [0.5, 1.5, 4, 9]:
            time.sleep(sleeptime)	
            try:
                data = self._postUrl(url, params)
                if data == "Unable to connect to the database":
                    raise exceptions.FailedToDownload("Site reported 'Unable to connect to the database'")
                if "I certify that I am over the age of 18 and that accessing the following story will not violate the laws of my country or local ordinances." in data:
                    raise exceptions.FailedToLogin(url,params['username'])
                return data
            except exceptions.FailedToLogin, ftl:
                # no need to retry these.
                raise(ftl)
            except Exception, e:
                excpt=e
                logger.warn("Caught an exception reading URL: %s  Exception %s."%(unicode(url),unicode(e)))

        logger.error("Giving up on %s" %url)
        logger.exception(excpt)
        raise(excpt)
        
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._postUrlUP(url)
        #print("data:%s"%data)
        
        # some stories have html that confuses the parser.  For story
        # text we don't care about anything before '<table id="page"'
        # and seems to clear the issue.
        data = data[data.index('<table id="page"'):]
        
        soup = bs.BeautifulSoup(data)
        
        div = soup.find('td',{'id':'page_content'})
        div.name='div'

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        ## Remove stuff from page_content

        # Remove all tags before the first <hr> after class=info table (including hr)
        hr = div.find('table',{'class':'info'}).findNext('hr')
        for tag in hr.findAllPrevious():
            tag.extract()
        hr.extract()
        
        # Remove all tags after the last <hr> (including hr)
        hr = div.findAll('hr')[-1]
        for tag in hr.findAllNext():
            tag.extract()
        hr.extract()
        
        return self.utf8FromSoup(url,div)
