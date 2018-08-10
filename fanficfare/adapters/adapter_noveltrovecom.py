#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2018 FanFicFare team
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
## Adapted by GComyn on April 22, 2017
####################################################################################################

from __future__ import absolute_import
import logging
import json
import re
import sys  # ## used for debug purposes
import datetime

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

####################################################################################################
def getClass():
    return NovelTroveComSiteAdapter


####################################################################################################
class NovelTroveComSiteAdapter(BaseSiteAdapter):
    ''' This is a site with 1 story per page, so no multiple chapter stories
        The date is listed (on the newer stories) as a month and a year, so I'll be adding that
         to the summary, instead of trying to transform it to a date. '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult = False

        # get storyId from url
        # https://noveltrove.com/story/983/put-that-big-cock-in-me
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/')[2] + '_' + self.parsedUrl.path.split('/')[3])

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ntcom')

        # This is a 1 story/page site, so we will initialize the variable to keep the soup
        self.html = ''
        self.endindex = []

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b. '%y"

####################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'noveltrove.com'

####################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/story/12345/astoryname"

####################################################################################################
    def getSiteURLPattern(self):
        return r"https://"+re.escape(self.getSiteDomain())+r"/story/([0-9])+/*(?P<id>[^/]+)"

####################################################################################################
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        url = self.url

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data we can get
        metablock = soup.find('div', {'class': 'title-infos'})

        ## Getting Title
        title = stripHTML(metablock.find('h1'))
        self.story.setMetadata('title', title)

        ## Getting author
        author = metablock.find('a', {'class':'author'})
        self.story.setMetadata('authorId',author['href'].split('/')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+author['href'])
        self.story.setMetadata('author',author.string)

        ## Get the categories
        for tag in metablock.find_all('a', {'class':'story-category'}):
            self.story.addToList('category',stripHTML(tag))

        ## There is no summary for these stories, so I'm going to take the first
        ## 250 characters.
        synopsis = ''
        pcount = 0
        for para in soup.find('div', {'class':'body'}).find_all('p'):
            synopsis += para.get_text() + ' '
            pcount += 1
            if pcount > 10:
                break

        synopsis = synopsis.strip()[:250] + '...'

        self.setDescription(url, synopsis)

        ## Since this is a 1 story/page site, the published and updated dates are the same.
        dateposted = stripHTML(metablock.find('div', {'class':'date'}))
        self.story.setMetadata('datePublished', makeDate(dateposted, self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(dateposted, self.dateformat))

        ## This is a 1 story/page site, so we'll keep the soup for the getChapterText function
        ## the chapterUrl and numChapters need to be set as well
        self.html = soup
        self.add_chapter(self.story.getMetadata('title'), url)
        self.story.setMetadata('status', 'Completed')

        ## Getting the non-standard title page entries
        copyrt = soup.find('div', {'class':'copyright'}).get_text()
        self.story.setMetadata('copyright', copyrt)


    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Using data that we got from: %s' % url)

        soup = self.html
        story = soup.find('div', {'class':'body'})

        if story == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,story)
