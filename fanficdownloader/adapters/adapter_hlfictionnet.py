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
    return HLFictionNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class HLFictionNetAdapter(BaseSiteAdapter):

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
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','hlf')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'hlfiction.net'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

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
            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title and author
        a = soup.find('div', {'id' : 'pagetitle'})
        
        aut = a.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+aut['href'])
        self.story.setMetadata('author',aut.string)
        aut.extract()
        
        self.story.setMetadata('title',a.string[:(len(a.string)-3)])

        # Find the chapters:
        chapters=soup.find('select')
        if chapters != None:
            for chapter in chapters.findAll('option'):
                # just in case there's tags, like <i> in chapter titles. 
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/viewstory.php?sid='+self.story.getMetadata('storyId')+'&chapter='+chapter['value']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        for list in asoup.findAll('div', {'class' : re.compile('listbox\s+')}):
            a = list.find('a')
            if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in a['href']:
                break

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = list.findAll('span', {'class' : 'classification'})
        for labelspan in labels:
            label = labelspan.string
            value = labelspan.nextSibling

            if 'Summary' in label:
                ## Everything until the next span class='label'
                svalue = ""
                while not defaultGetattr(value,'class') == 'classification':
                    svalue += str(value)
                    value = value.nextSibling
                self.setDescription(url,svalue)
                #self.story.setMetadata('description',stripHTML(svalue))

            if 'Rated' in label:
                self.story.setMetadata('rating', value[:len(value)-2])

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'categories.php\?catid=\d+'))
                for cat in cats:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                for char in value.string.split(', '):
                    if not 'None' in char:
                        self.story.addToList('characters',char)

            if 'Genre' in label:
                for genre in value.string.split(', '):
                    if not 'None' in genre:
                        self.story.addToList('genre',genre)

            if 'Warnings' in label:
                for warning in value.string.split(', '):
                    if not 'None' in warning:
                        self.story.addToList('warnings',warning)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        try:
            # Find Series name from series URL.
            a = list.find('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
            # can't use ^viewstory...$ in case of higher rated stories with javascript href.
            storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+'))
            i=1
            for a in storyas:
                # skip 'report this' and 'TOC' links
                if 'contact.php' not in a['href'] and 'index' not in a['href']:
                    if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in a['href']:
                        self.setSeries(series_name, i)
                        break
                    i+=1
            
        except:
            # I find it hard to care if the series parsing fails
            pass
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
