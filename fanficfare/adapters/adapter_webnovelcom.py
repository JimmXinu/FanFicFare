#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2017 FanFicFare team
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
## Adapted by GComyn on April 16, 2017
####################################################################################################

import logging
import re
import sys  # ## used for debug purposes
import time
import urllib2
import datetime

from base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

####################################################################################################
def getClass():
    return WWWWebNovelComAdapter


####################################################################################################
class WWWWebNovelComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult = False

        # get storyId from url
        # https://www.webnovel.com/book/6831837102000205
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/')[2])

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','wncom')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        ## There are no dates listed on this site, so am commenting this out
        #self.dateformat = "%Y-%b-%d"

####################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.webnovel.com'

####################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/book/123456789012345"

####################################################################################################
    def getSiteURLPattern(self):
        return r"https://"+re.escape(self.getSiteDomain())+r"/book/*(?P<id>\d+)"

####################################################################################################
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        url = self.url

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        if "We might have some troubles to find out this page." in data:
            raise exceptions.StoryDoesNotExist('{0} says: "" for url "{1}"'.format(self.getSiteDomain(),self.url))

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # removing all of the scripts
        for tag in soup.findAll('script') + soup.find_all('svg'):
            tag.extract()

        # Now go hunting for all the meta data and the chapter list.

        ## This is the block that holds the metadata
        bookdetails = soup.find('div', {'class':'g_col_8'})

        ## Title
        a = bookdetails.find('h2', {'class':'lh1d2'})
        self.story.setMetadata('title',stripHTML(a))
		
        # Find authorid and URL from... author url.
        paras = bookdetails.find_all('p')
        for para in paras:
            parat = stripHTML(para)
            if parat[:7] == 'Author:':
                self.story.setMetadata('author', parat.replace('Author:', '').strip())
                self.story.setMetadata('authorId', parat.replace('Author:', '').strip())
                ## There is no authorUrl for this site, so I'm setting it to the story url
                ## otherwise it defaults to the file location
                self.story.setMetadata('authorUrl', url)
            elif parat[:11] == 'Translator:':
                self.story.setMetadata('translator', parat.replace('Translator:', '').strip())
            elif parat[:7] == 'Editor:':
                self.story.setMetadata('editor', parat.replace('Editor:', '').strip())

        category = stripHTML(paras[0].strong).strip()
        self.story.setMetadata('category', category)

        ## Getting the ChapterUrls
        chaps = soup.find('div', {'id':'contentsModal'}).find_all('a')
        for chap in chaps:
            ## capitalize to change leading 'chapter' to 'Chapter'.
            chap_title = stripHTML(chap).capitalize()
            chap_Url = 'https:'+chap['href']
            self.chapterUrls.append((chap_title, chap_Url))
        
        self.story.setMetadata('numChapters', len(self.chapterUrls))

        if get_cover:
            cover_meta = soup.find('div', {'class':'g_col_4'}).find('img')
            cover_url = 'https:'+cover_meta['src']
            self.setCoverImage(url, cover_url)

        synopsis = soup.find('div', {'class':'det-abt'}).find('p')

        self.setDescription(url, synopsis)

        ## There are no published or updated dates listed on this site. I am arbitrarily setting
        ## these dates to the packaged date for now. If anyone else has an idea of how to get
        ## the original dates, please let me know [GComyn]
        ### I'd like to use the original date of the file, if this is an update, but I'm not proficient
        ### enough with programming to get it at this time. [GComyn]
        self.story.setMetadata('datePublished', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))
        self.story.setMetadata('dateUpdated', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))

        ## We don't know the status of the story from the index page, so we can't update it.

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
		
        data = self._fetchUrl(url)
        html = self.make_soup(data)

        story = html.find('div', {'class':'cha-content'})
			
        if story == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        for tag in story.find_all('form'):
            tag.extract()

        return self.utf8FromSoup(url,story)
