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
import datetime
import logging
import re
import urllib2
from .. import translit

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return FicBookNetAdapter


class FicBookNetAdapter(BaseSiteAdapter):

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
        self._setURL('http://' + self.getSiteDomain() + '/readfic/'+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fbn')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %m %Y" 
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.ficbook.net'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/readfic/12345"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/readfic/")+r"\d+"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        url=self.url
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

        # Now go hunting for all the meta data and the chapter list.
		
        table = soup.find('td',{'width':'50%'})
        
        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a))
        logging.debug("Title: (%s)"%self.story.getMetadata('title'))
        
        # Find authorid and URL from... author url.
        a = table.find('a')
        self.story.setMetadata('authorId',a.text) # Author's name is unique
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.text)
        logging.debug("Author: (%s)"%self.story.getMetadata('author'))

        # Find the chapters:
        chapters = soup.find('div', {'class' : 'part_list'})
        if chapters != None:
            chapters=chapters.findAll('a', href=re.compile(r'/readfic/'+self.story.getMetadata('storyId')+"/\d+#part_content$"))
            self.story.setMetadata('numChapters',len(chapters))
            for x in range(0,len(chapters)):
                chapter=chapters[x]
                churl='http://'+self.host+chapter['href']
                self.chapterUrls.append((stripHTML(chapter),churl))
                if x == 0:
                    pubdate = translit.translit(stripHTML(bs.BeautifulSoup(self._fetchUrl(churl)).find('div', {'class' : 'part_added'}).find('span')))
                if x == len(chapters)-1:
                    update = translit.translit(stripHTML(bs.BeautifulSoup(self._fetchUrl(churl)).find('div', {'class' : 'part_added'}).find('span')))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
            self.story.setMetadata('numChapters',1)
            pubdate=translit.translit(stripHTML(soup.find('div', {'class' : 'part_added'}).find('span')))
            update=pubdate

        logging.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))

        if not ',' in pubdate:
            pubdate=datetime.date.today().strftime(self.dateformat)
        if not ',' in update:
            update=datetime.date.today().strftime(self.dateformat)
        pubdate=pubdate.split(',')[0]
        update=update.split(',')[0]
		
        fullmon = {"yanvarya":"01", "января":"01",
           "fievralya":"02", "февраля":"02",
           "marta":"03", "марта":"03",
           "aprielya":"04", "апреля":"04",
           "maya":"05", "мая":"05",
           "iyunya":"06", "июня":"06",
           "iyulya":"07", "июля":"07",
           "avghusta":"08", "августа":"08",
           "sentyabrya":"09", "сентября":"09",
           "oktyabrya":"10", "октября":"10",
           "noyabrya":"11", "ноября":"11",
           "diekabrya":"12", "декабря":"12" }
        for (name,num) in fullmon.items():
            if name in pubdate:
                pubdate = pubdate.replace(name,num)
            if name in update:
                update = update.replace(name,num)

        self.story.setMetadata('dateUpdated', makeDate(update, self.dateformat))
        self.story.setMetadata('datePublished', makeDate(pubdate, self.dateformat))
        self.story.setMetadata('language','Russian')
		
        pr=soup.find('a', href=re.compile(r'/printfic/\w+'))
        pr='http://'+self.host+pr['href']
        pr = bs.BeautifulSoup(self._fetchUrl(pr))
        pr=pr.findAll('div', {'class' : 'part_text'})
        i=0
        for part in pr:
            i=i+len(stripHTML(part).split(' '))
        self.story.setMetadata('numWords', str(i))
		
        i=0
        fandoms = table.findAll('a', href=re.compile(r'/fanfiction/\w+'))
        for fandom in fandoms:
            self.story.addToList('category',fandom.string)
            i=i+1
        if i > 1:
            self.story.addToList('genre', 'Кроссовер')
		
        meta=table.findAll('a', href=re.compile(r'/ratings/'))
        i=0
        for m in meta:
            if i == 0:
                self.story.setMetadata('rating', m.find('b').text)
                i=1
            elif i == 1:
                if not "," in m.nextSibling:
                    i=2
                self.story.addToList('genre', m.find('b').text)
            elif i == 2:
                self.story.addToList('warnings', m.find('b').text)
		

        if table.find('span', {'style' : 'color: green'}):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In Progress')
		

        tags = table.findAll('b')
        for tag in tags:
            label = translit.translit(tag.text)
            if 'Piersonazhi:' in label or 'Персонажи:' in label:
                chars=tag.nextSibling.string.split(', ')
                for char in chars:
                    self.story.addToList('characters',char)
                break
				
        summary=soup.find('span', {'class' : 'urlize'})
        self.setDescription(url,summary.text)
        #self.story.setMetadata('description', summary.text)
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        chapter = soup.find('div', {'class' : 'public_beta'})
        if chapter == None:
            chapter = soup.find('div', {'class' : 'public_beta_disabled'})

        if None == chapter:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,chapter)
