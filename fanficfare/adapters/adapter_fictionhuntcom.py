# -*- coding: utf-8 -*-

# Copyright 2016 FanFicFare team
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

import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from base_adapter import BaseSiteAdapter,  makeDate

class FictionHuntComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fichunt')

        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # normalized story URL.
        self._setURL("http://"+self.getSiteDomain()\
                         +"/read/"+self.story.getMetadata('storyId')+"/1")

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d-%m-%Y"

    @staticmethod
    def getSiteDomain():
        return 'fictionhunt.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://fictionhunt.com/read/1234/1"

    def getSiteURLPattern(self):
        return r"http://(www.)?fictionhunt.com/read/\d+(/\d+)?(/|/[^/]+)?/?$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.url
        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.meta)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        self.story.setMetadata('title',stripHTML(soup.find('div',{'class':'title'})).strip())

        self.setDescription(url,'<i>(Story descriptions not available on fictionhunt.com)</i>')

        # Find authorid and URL from... author url.
        # fictionhunt doesn't have author pages, use ffnet original author link.
        a = soup.find('a', href=re.compile(r"fanfiction.net/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl','https://www.fanfiction.net/u/'+self.story.getMetadata('authorId'))
        self.story.setMetadata('author',a.string)

        # Find original ffnet URL
        a = soup.find('a', href=re.compile(r"fanfiction.net/s/\d+"))
        self.story.setMetadata('origin',stripHTML(a))
        self.story.setMetadata('originUrl',a['href'])

        # Fleur D. & Harry P. & Hermione G. & Susan B. - Words: 42,848 - Rated: M - English - None - Chapters: 9 - Reviews: 248 - Updated: 21-09-2016 - Published: 16-05-2015 - by Elven Sorcerer (FFN)
        # None - Words: 13,087 - Rated: M - English - Romance & Supernatural - Chapters: 3 - Reviews: 5 - Updated: 21-09-2016 - Published: 20-09-2016
        # Harry P. & OC - Words: 10,910 - Rated: M - English - None - Chapters: 5 - Reviews: 6 - Updated: 21-09-2016 - Published: 11-09-2016
        # Dudley D. & Harry P. & Nagini & Vernon D. - Words: 4,328 - Rated: K+ - English - None - Chapters: 2 - Updated: 21-09-2016 - Published: 20-09-2016 -
        details = soup.find('div',{'class':'details'})

        detail_re = \
            r'(?P<characters>.+) - Words: (?P<numWords>[0-9,]+) - Rated: (?P<rating>[a-zA-Z\\+]+) - (?P<language>.+) - (?P<genre>.+)'+ \
            r' - Chapters: (?P<numChapters>[0-9,]+)( - Reviews: (?P<reviews>[0-9,]+))? - Updated: (?P<dateUpdated>[0-9-]+)'+ \
            r' - Published: (?P<datePublished>[0-9-]+)(?P<completed> - Complete)?'

        details_dict = re.match(detail_re,stripHTML(details)).groupdict()

        # lists
        for meta in ('characters','genre'):
            if details_dict[meta] != 'None':
                self.story.extendList(meta,details_dict[meta].split(' & '))

        # scalars
        for meta in ('numWords','numChapters','rating','language','reviews'):
            self.story.setMetadata(meta,details_dict[meta])

        # dates
        for meta in ('datePublished','dateUpdated'):
            self.story.setMetadata(meta, makeDate(details_dict[meta], self.dateformat))

        # status
        if details_dict['completed']:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # It's assumed that the number of chapters is correct.
        # There's no complete list of chapters, so the only
        # alternative is to get the num of chaps from the last
        # indiated chapter list instead.
        for i in range(1,1+int(self.story.getMetadata('numChapters'))):
            self.chapterUrls.append(("Chapter "+unicode(i),"http://"+self.getSiteDomain()\
                                         +"/read/"+self.story.getMetadata('storyId')+"/%s"%i))

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        data = self._fetchUrl(url)

        soup = self.make_soup(data)

        div = soup.find('div', {'class' : 'text'})

        return self.utf8FromSoup(url,div)

def getClass():
    return FictionHuntComSiteAdapter
