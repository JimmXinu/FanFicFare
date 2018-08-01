# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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
# Adapted by GComyn - December 10, 2016
####################################################################################################
from __future__ import absolute_import
''' This adapter will download the stories from the www.fireflyfans.net forum  pages '''
import logging
import re
import sys
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)


####################################################################################################
def getClass():
    return FireFlyFansNetSiteAdapter


####################################################################################################
class FireFlyFansNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'fffans')
        self.is_adult = False

        # get storyId from url--url validation guarantees query is only
        # sid=1234
        self.story.setMetadata('storyId', self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() +
                     '/bluesun.aspx?bid=' + self.story.getMetadata('storyId'))

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"

    ################################################################################################
    @staticmethod
    def getSiteDomain():
        return 'www.fireflyfans.net'

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://" + cls.getSiteDomain() + "/bluesun.aspx?bid=1234"

    ################################################################################################
    def getSiteURLPattern(self):
        return re.escape("http://" + self.getSiteDomain() + "/bluesun.aspx?bid=") + r"\d+$"

    ################################################################################################
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: " + url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if 'Something bad happened, but hell if I know what it is.' in data:
            raise exceptions.StoryDoesNotExist(
                '{0} says: GORAMIT!!! SOMETHING WENT WRONG! Something bad happened, but hell if I know what it is.'.format(self.url))

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Title
        a = soup.find('span', {'id': 'MainContent_txtItemName'})
        self.story.setMetadata('title', stripHTML(a))

        # Find authorid and URL from... author url.

        a = soup.find('a', href=re.compile(r"profileshow.aspx\?u="))
        self.story.setMetadata('authorId', a['href'].split('=')[1])
        self.story.setMetadata('authorUrl', 'http://' +
                               self.host + '/' + a['href'])
        self.story.setMetadata('author', a.string)

        # This site has all "chapters" on one page. Also, there is no easy systematic
        # way to determine if there are other chapters to the same story, so you have
        # to download them one at a time yourself. I'm also setting the status to
        # complete
        self.add_chapter(self.story.getMetadata('title'), self.url)
        self.story.setMetadata('numChapters', 1)
        self.story.setMetadata('status', 'Completed')

        ## some stories do not have a summary listed, so I'm setting it here.
        summary = soup.find('span', {'id': 'MainContent_txtItemDescription'})
        summary = stripHTML(summary)
        if not summary:
            self.setDescription(url, '>>>>>>>>>> No Summary Given <<<<<<<<<<')
        else:
            self.setDescription(url, summary)

        # There is not alot of Metadata with this site, so we get what we can.
        pubdate = soup.find('span', {'id': 'MainContent_txtItemInfo'})
        pubdate = stripHTML(pubdate)
        pubdate = pubdate[pubdate.find(', ') + 1:]
        self.story.setMetadata('datePublished', makeDate(
            pubdate.strip(), self.dateformat))

        # The only Metadata that I can find is the Category (usually Fiction) and the series
        # which is usualy FireFly on this site, but I'm going to get them
        # anyway.a
        category = soup.find('span', {'id': 'MainContent_txtItemDetails'})
        category = stripHTML(unicode(category).replace(u"\xa0", u' '))
        metad = category.split('    ')
        for meta in metad:
            if ":" in meta:
                label = meta.split(':')[0].strip()
                value = meta.split(':')[1].strip()
                if label == 'CATEGORY':
                    self.story.setMetadata('category', value)
                elif label == 'SERIES':
                    # There is no easy way to determine which number the current 'story' is
                    # in the total story, so I'm just going to set the series
                    # name here
                    self.story.setMetadata('series', value)
                else:
                    # This catches the elements I am not interested
                    # in, such as Times Read and Rating (which is a
                    # Number, not a determination on the content)
                    zzzzzzz = 0

        # The genre is contained in a tag that has 'BLUE SUN ROOM FAN FICTION - ' as part of
        # the text, so we get it, then remove that text
        genre = soup.find('span', {'id': 'MainContent_txtBlueSunHeader'})
        genre = stripHTML(genre).replace('BLUE SUN ROOM FAN FICTION - ', '')
        self.story.setMetadata('genre', genre.title())

        # since the 'story' is one page, I am going to save the soup here, so we can use iter
        # to get the story text in the getChapterText function, instead of having to retrieve
        # it again.
        self.html = soup

    ################################################################################################
    def getChapterText(self, url):

        logger.debug('Using the html retrieved previously from: %s' % url)

        soup = self.html

        span = soup.find('div', {'class': 'fanfic'})

        if not span:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, span)
