# -*- coding: utf-8 -*-
# Copyright 2017 Fanficdownloader team
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
### Adapted by Rikkit on November 9. 2017
###=================================================================================================
### Tested with Calibre
####################################################################################################

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
    return LightNovelGateSiteAdapter

class LightNovelGateSiteAdapter(BaseSiteAdapter):
    ''' Adapter for LightNovelGate.com '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'lng')

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
                         +"/novel/"+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'lightnovelgate.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://lightnovelgate.com/novel/astoryname"

    def getSiteURLPattern(self):
        # http://lightnovelgate.com/novel/stellar_transformation
        return r"http://lightnovelgate\.com/novel/(?P<id>[^/]+)"

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
        try:
            author_link = soup.find('span', string='Author(s): ').find_next_sibling("a")
            author_name = author_link.string
            author_url = author_link['href']
            self.story.setMetadata('authorId', author_name.lower())
            self.story.setMetadata('authorUrl', author_url)
            self.story.setMetadata('author', author_name)
        except:
            self.story.setMetadata('authorId', 'unknown')
            self.story.setMetadata('author', 'Unknown')

        ## get title
        title = soup.find_all('span', {'itemprop':'title'})[1].string
        self.story.setMetadata('title', title)

        # datePub = soup.find('meta', {'itemprop':'datePublished'})['content']
        dateUpd = soup.find('em', class_='updated').string
        # self.story.setMetadata('datePublished', makeDate(datePub, self.dateformat))
        # example: 08-NOV-2017 11:21
        self.story.setMetadata('dateUpdated', makeDate(dateUpd, '%d-%b-%Y %H:%M'))

        ## getting status
        status = soup.find('span', string='STATUS : ').find_next_sibling("a").string
        if status == 'completed':
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        ## getting genres
        genres = soup.find('span', string='GENRES: ').find_next_siblings("a")
        genre_list = []
        for agenre in genres:
            genre_list.append(agenre.string)
        self.story.extendList('genre',genre_list)

        ## getting cover
        img = soup.find('img', class_='wp-post-image')
        if img:
            self.setCoverImage(url,img['src'])

        ## getting chapters
        cdata = soup.select('.chapter-list .row')
        cdata.reverse()

        for row in cdata:
            clink = row.find('a')
            self.chapterUrls.append((clink.string, clink['href']))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        ## getting description
        cdata = soup.select_one('#noidungm')
        cdata.find('h2').extract()
        self.setDescription(url, cdata)

    def getChapterText(self, url):
        data = self._fetchUrl(url)
        soup = self.make_soup(data)
        story = soup.find('div', {'id':'vung_doc'})
        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, story)
