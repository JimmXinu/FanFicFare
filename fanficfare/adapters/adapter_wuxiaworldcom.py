# -*- coding: utf-8 -*-
# Copyright 2016 Fanficdownloader team
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
####################################################################################################
### Adapted by GComyn on December 14. 2016
###=================================================================================================
### Tested with the CLI and it works for all of the stories I tested
### Tested with Calibre, but coulnd't get past an encoding error...
###=================================================================================================
### I have started to use lines of # on the line just before a function so they are easier to find.
####################################################################################################
'''
This will scrape the chapter text and metadata from stories on the site www.wuxiaworld.com
'''
import logging
import re
import urllib2
import urlparse

from base_adapter import BaseSiteAdapter, makeDate

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)

def getClass():
    ''' Initializing the class '''
    return WuxiaWorldComSiteAdapter

class WuxiaWorldComSiteAdapter(BaseSiteAdapter):
    ''' Adapter for Wuxiaworld.com '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'wux')

        self.dateformat = "%Y-%m-%dT%H:%M:%S+00:00"

        self.is_adult = False
        self.username = None
        self.password = None

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(), url)
        if m:
            self.story.setMetadata('storyId', m.group('id'))

            # normalized story URL.
            self._setURL("http://"+self.getSiteDomain()
                         +"/"+self.story.getMetadata('storyId')+"/")
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.wuxiaworld.com/astoryname-index/"

    def getSiteURLPattern(self):
        # http://www.wuxiaworld.com/emperor-index/
        return r"http(s)?://www\.wuxiaworld\.com/(?P<id>[^/]+)(/)?"

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter. From that we will get almost all the
        # metadata and chapter list

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)

        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(url))
            else:
                raise e

        soup = self.make_soup(data)

        ## I'm going to remove all of the scripts at the beginning...
        for tag in soup.find_all('script'):
            tag.extract()

        ## getting Author
        author_name = soup.find('span', {'itemprop':'author'}).find('meta')['content']
        author_url = soup.find('meta', {'property':'article:author'})['content']
        self.story.setMetadata('authorId', author_name.lower())
        self.story.setMetadata('authorUrl', author_url)
        self.story.setMetadata('author', author_name)

        ## get title, remove ' – Index' if present.
        title = stripHTML(soup.find('header', {'class':'entry-header'})).replace(u' – Index','')
        self.story.setMetadata('title', title)

        datePub = soup.find('meta', {'itemprop':'datePublished'})['content']
        dateUpd = soup.find('meta', {'itemprop':'dateModified'})['content']
        self.story.setMetadata('datePublished', makeDate(datePub, self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(dateUpd, self.dateformat))

        ## getting the chapters
        ### Unfortunately, for the active stories, the chapter list is not systematically updated...
        ### The 'author' has to enter the chapters on this page, so if they are not up to date we
        ### don't get them...
        ### Also, I'm going to remove the chapters from here after I have them so they won't be
        ## in the summary, which is where I'm going to put the rest of the text.

        cdata = soup.find('div', {'itemprop':'articleBody'})
        #logger.debug('############################ - cdata\n%s\n###########################', cdata)
        chapters = cdata.find_all('a', href=re.compile(
            r'^(((https?://)?'+self.getSiteDomain()+')?/'+self.story.getMetadata(
                'storyId')+r'/)?(#)?([a-zA-Z0-9_ -]+)(/)?$'))
        ## some have different chapter links... going to do it again
        if len(chapters) == 0:
            chapters = cdata.find_all('a', href=re.compile(
                r'https?://'+self.getSiteDomain()+'/master-index/'+r'([#a-zA-Z0-9_ -]+)(/)?'))

        for chap in chapters:
            if stripHTML(chap).strip() != '':
                href = urlparse.urljoin(self.url, chap['href'])
                self.chapterUrls.append((stripHTML(chap), href))
            chap.extract()

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        ## removing the 'folded' chapter lists..
        for tag in cdata.find_all('div', {'class':'sp-wrap'}) + cdata.find_all('span', {'class':'collapseomatic'}) + cdata.find_all('div', {'class':'collapseomatic_content'}):
            tag.extract()
        self.setDescription(url, cdata)

    def getChapterText(self, url):
        #logger.debug('Getting chapter text from: %s', url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)
        story = soup.find('div', {'itemprop':'articleBody'})
        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)
        #removing the Previous and next chapter links
        for tag in story.find_all('a',text=re.compile(r'(Previous|Next) Chapter')):
            tag.extract()

        return self.utf8FromSoup(url, story)
