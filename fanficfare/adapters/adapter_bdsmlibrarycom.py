# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2015 FanFicFare team
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
###########################################################################
### written by GComyn - 10/06/2016
### updated by GComyn = 10/24/2016
###########################################################################
'''
This works, but some of the stories have abysmal formatting, so it would 
probably need to be edited for reading.

I've seen one story that downloaded at 25M, but after editing is only 201K
after the formatting was corrected.

Right now it is written to download each chapter seperatly, but I may change 
that to get the whole story. It will still have formatting problems, but should
be able to get the longer stories this way.

Also, the site is notrious for lagging, so some of the longer stories will 
probably not be downloadable, since this program doesn't wait long enough 
for the site to catch up.

'''

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib
import urllib2
import sys
import urlparse

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return BDSMLibraryComSiteAdapter

class BDSMLibraryComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252",
                       "iso-8859-1"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
							
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only storyid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        self._setURL('http://{0}/stories/story.php?storyid={1}'.format(self.getSiteDomain(), self.story.getMetadata('storyId')))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','bdsmlib')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.bdsmlibrary.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/stories/story.php?storyid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/stories/story.php?storyid=")+r"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        try:
            data = self._fetchUrl(self.url)
            soup = self.make_soup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
            
        if 'The story does not exist' in data:
            raise exceptions.StoryDoesNotExist(self.url)

        # Extract metadata
        title=soup.title.text.replace('BDSM Library - Story: ','')
        self.story.setMetadata('title', title)

        # Author
        author = soup.find('a', href=re.compile(r"/stories/author.php\?authorid=\d+"))
        i = 0
        while author == None:
            time.sleep(1)
            logger.warning('A problem retrieving the author information. Trying Again')
            try:
                data = self._fetchUrl(self.url)
                soup = self.make_soup(data)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(self.url)
                else:
                    raise e
            author = soup.find('a', href=re.compile(r"/stories/author.php\?authorid=\d+"))
            print author
            i += 1
            if i == 20:
                logger.info('Too Many cycles... exiting')
                sys.exit()


        authorurl = urlparse.urljoin(self.url, author['href'])
        self.story.setMetadata('author', author.text)
        self.story.setMetadata('authorUrl', authorurl)
        authorid = author['href'].split('=')[1]
        self.story.setMetadata('authorId', authorid)

        # Find the chapters:
        # The update date is with the chapter links... so we will update it here as well
        for a in soup.findAll('a'):
            if '/stories/chapter.php?storyid='+self.story.getMetadata('storyId')+"&chapterid=" in a['href']:
                value = a.findNext('td').findNext('td').string.replace('(added on','').replace(')','').strip()
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                self.chapterUrls.append((stripHTML(a),'http://'+self.getSiteDomain()+a['href']))

        # I can't seem to get the re.compile to work for this. so I'm commenting it out
        #for chapter in soup.findAll('a', href=re.compile(r'/stories/chapter.php?storyid='+self.story.getMetadata('storyId')+"&chapterid=\d+$")):
        #    # just in case there's tags, like <i> in chapter titles.
        #    self.chapterUrls.append((stripHTML(chapter),'http://'+self.getSiteDomain()+chapter['href']+addurl))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        # Get the MetaData
        # Erotia Tags
        tags = soup.findAll('a',href=re.compile(r'/stories/search.php\?selectedcode'))
        for tag in tags:
            self.story.addToList('eroticatags',tag.text)
            
        # Published Date
        tds = soup.findAll('td')
        for td in tds:
            if len(td.text)>0:
                if 'Added on:' in td.text and '<table' not in unicode(td):
                    value = td.text.replace('Added on:','').strip()
                    self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                elif 'Synopsis:' in td.text and '<table' not in unicode(td):
                    value = td.text.replace('\n','').replace('Synopsis:','').strip()
                    self.setDescription(self.url,stripHTML(value))
                elif 'Size:' in td.text and '<table' not in unicode(td):
                    value = td.text.replace('\n','').replace('Size:','').strip()
                    self.story.setMetadata('size',stripHTML(value))
                elif 'Comments:' in td.text and '<table' not in unicode(td):
                    value = td.text.replace('\n','').replace('Comments:','').strip()
                    self.story.setMetadata('comments',stripHTML(value))

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        #Since each chapter is on 1 page, we don't need to do anything special, just get the content of the page.
        logger.debug('Getting chapter text from: %s' % url)
        logger.info('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))
        chaptertag = soup.find('div',{'class' : 'storyblock'})

        # Some of the stories have the chapters in <pre> sections, so have to check for that
        if chaptertag == None:
            chaptertag = soup.find('pre')
        
        try:
            # BDSM Library basically wraps it's own html around the document,
            # so we will be removing the script, title and meta content from the 
            # storyblock
            scripts = chaptertag.findAll('style')
            if scripts != None:
                for script in scripts:
                    script.extract()
                    
            titles = chaptertag.findAll('title')
            if titles !=None:
                for title in titles:
                    title.extract()
            
            metas = chaptertag.findAll('meta')
            if metas !=None:
                for meta in metas:
                    meta.extract()
        except:
            pass

        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: {0}!  Missing required element!".format(url))
        
        return self.utf8FromSoup(url,chaptertag)
                    