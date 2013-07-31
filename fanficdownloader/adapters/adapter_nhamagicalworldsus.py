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
logger = logging.getLogger(__name__)
import re
import urllib2

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return NHAMagicalWorldsUsAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class NHAMagicalWorldsUsAdapter(BaseSiteAdapter):

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
        
		
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','nha')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = " %m/%d/%y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'nha.magical-worlds.us'

    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        url = self.url
        logger.debug("URL: "+url)

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
            
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
		
        try:
            # in case link points somewhere other than the first chapter
            a = soup.findAll('option')[1]['value']
            self.story.setMetadata('storyId',a.split('=',)[1])
            url = 'http://'+self.host+'/'+a
            soup = bs.BeautifulSoup(self._fetchUrl(url))
        except:
            pass
		
        for info in asoup.findAll('table', {'width' : '100%', 'bordercolor' : re.compile(r'#')}):
            a = info.find('a')
            if 'viewstory.php?sid='+self.story.getMetadata('storyId') == a['href'] or \
                    ('viewstory.php?sid='+self.story.getMetadata('storyId')+'&') in a['href']:
                self.story.setMetadata('title',a.string)
                break
		

        # Find the chapters:
        chapters=soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+'&chapter=\d+$'))
        if len(chapters) == 0:
            self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d):
            try:
                return d.name
            except:
                return ""
				
        cats = info.findAll('a',href=re.compile('categories.php'))
        for cat in cats:
            self.story.addToList('category',cat.string)
					
        a = info.find('a', href=re.compile(r'viewuser.php'))
        val = a.nextSibling
        svalue = ""
        while not defaultGetattr(val) == 'br':
            val = val.nextSibling
        val = val.nextSibling
        while not defaultGetattr(val) == 'br':
            svalue += unicode(val)
            val = val.nextSibling
        self.setDescription(url,svalue)
        
        #does not provide convenient way to get word count
        labels = info.findAll('i')
        for labelspan in labels:
            value = labelspan.nextSibling
            label = stripHTML(labelspan)

            if 'Rating' in label:
                self.story.setMetadata('rating', value.split(' -')[0])

            if 'Genres' in label:
                genres = value.string.split(', ')
                for genre in genres:
                    if 'None' not in genre:
                        self.story.addToList('genre',genre.split(' -')[0])
            
            if 'Characters' in label:
                chars = value.string.split(', ')
                for char in chars:
                    if 'None' not in char:
                        self.story.addToList('characters',char.split(' -')[0])

            if 'Warnings' in label:
                warnings = value.string.split(', ')
                for warning in warnings:
                    if 'None' not in warning:
                        self.story.addToList('warnings',warning.split(' -')[0])

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(value.split(' -')[0], self.dateformat))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(value.split(' -')[0], self.dateformat))

            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)
		
        data = self._fetchUrl(url)

        soup = bs.BeautifulSoup(data, selfClosingTags=('br','hr','span','center')) # some chapters seem to be hanging up on those tags, so it is safer to close them
        
        story = soup.find('div', {"id" : "story"})

        if None == story:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,story)
