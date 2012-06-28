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
    return StoriesOfArdaComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class StoriesOfArdaComAdapter(BaseSiteAdapter):

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
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/chapterlistview.asp?SID='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','soa')

        # If all stories from the site fall into the same category,
        # the site itself isn't likely to label them as such, so we
        # do.
        self.story.addToList("category","Lord of the Rings")

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.storiesofarda.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/chapterlistview.asp?SID=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/chapterlistview.asp?SID=")+r"\d+$"

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
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title and author
        a = soup.find('th', {'colspan' : '3'})
        
        aut = a.find('a')
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+aut['href'])
        self.story.setMetadata('author',aut.string)
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        a.find('em').extract()
        self.story.setMetadata('title',a.text)

        # Find the chapters: chapterview.asp?sid=7000&cid=30919
        chapters=soup.findAll('a', href=re.compile(r'chapterview.asp\?sid='+self.story.getMetadata('storyId')+"&cid=\d+$"))
        if len(chapters)==1:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/'+chapters[0]['href']))
        else:
            for chapter in chapters:
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        summary = soup.find('td', {'colspan' : '3'})
        self.setDescription(url,summary)
        
        # no convenient way to get word count

        for td in asoup.findAll('td', {'colspan' : '3'}):
            if td.find('a', href=re.compile('chapterlistview.asp\?SID='+self.story.getMetadata('storyId'))) != None:
                break     
        td=td.nextSibling.nextSibling
        self.story.setMetadata('dateUpdated', makeDate(stripHTML(td).split(': ')[1], self.dateformat))
        tr=td.parent.nextSibling.nextSibling.nextSibling.nextSibling
        td=tr.findAll('td')
        self.story.setMetadata('rating', td[0].string.split(': ')[1])
        self.story.setMetadata('status', td[2].string.split(': ')[1])
        self.story.setMetadata('datePublished', makeDate(stripHTML(td[4]).split(': ')[1], self.dateformat))
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('table', {'width' : '90%'}).find('td')
        div.name='div'

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
