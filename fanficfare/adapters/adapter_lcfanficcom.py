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
    return LCFanFicComSiteAdapter


####################################################################################################
class LCFanFicComSiteAdapter(BaseSiteAdapter):
    ''' This is a site with 1 story per page, so no multiple chapter stories
        The date is listed (on the newer stories) as a month and a year, so I'll be adding that
         to the summary, instead of trying to transform it to a date. '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult = False

        # get storyId from url
        # http://lcfanfic.com/stories/2017/html/blooming.html
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/')[4].replace('.html', ''))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','lcffcom')

        # This is a 1 story/page site, so we will initialize the variable to keep the soup
        self.html = ''
        self.endindex = []

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        ## The dates listed are month year... and not all stories have it, so will leave it off.
        #self.dateformat = "%Y-%b-%d"

####################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'lcfanfic.com'

####################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return ("http://"+cls.getSiteDomain()+"/stories/2017/html/a-story-name "
                + "http://"+cls.getSiteDomain()+"/stories/_earliest/html/a-story-name")

####################################################################################################
    def getSiteURLPattern(self):
        return r"http://"+re.escape(self.getSiteDomain())+r"/stories/([0-9]+|_earliest)/html/*(?P<id>[^/]+)"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

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
        summaryblock = soup.find('div', {'class':'lcfheader'})
        if '<p align=center>***</p>' not in data:
            self.endindex.append(data.index('<p align="center">***</p>'))
            self.endindex.append(2)
        else:
            self.endindex.append(data.index('<p align=center>***</p>'))
            self.endindex.append(0)

        if not summaryblock:
            datasum = data[:self.endindex[0]]
            summaryblock = self.make_soup(datasum)
            summaryblock.head.decompose()
        else:
            summaryblock = self.make_soup(summaryblock.renderContents())

        ## Getting the Title
        title = stripHTML(summaryblock.h2)
        self.story.setMetadata('title', title)
        summaryblock.h2.decompose()

        ## Getting the author
        author = summaryblock.p
        authorUrl = author.find('a')
        ## Some stories do not have an author page, so I'm using the story Url
        if not authorUrl:
            authorUrl = url
        else:
            authorUrl = authorUrl['href']
        author = stripHTML(author)[3:] # discard leading 'By '
        author = re.sub(r' <[^>]+>','',author) # discard email in <>
        author = re.sub(r' \([^\)]+\)','',author) # discard email in ()
        authorId = author

        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', authorId)
        self.story.setMetadata('authorUrl', authorUrl)
        summaryblock.p.decompose()

        # Not all stories have a rating... so I have to check for it.
        rated = stripHTML(summaryblock.p)
        if 'Rated' in rated:
            self.story.setMetadata('rating', rated.replace('Rated', '').replace(':', '').strip())
            summaryblock.p.decompose()

        synopsis = unicode(summaryblock.body).strip()
        if not self.getConfig('keep_summary_html'):
            synopsis = stripHTML(synopsis)

        self.setDescription(url, synopsis)

        ## There are no published or updated dates listed on this site. I am arbitrarily setting
        ## these dates to the packaged date for now. If anyone else has an idea of how to get
        ## the original dates, please let me know [GComyn]
        ### I'd like to use the original date of the file, if this is an update, but I'm not proficient
        ### enough with programming to get it at this time. [GComyn]
        self.story.setMetadata('datePublished', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))
        self.story.setMetadata('dateUpdated', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))

        ## This is a 1 story/page site, so we'll keep the soup fo the getChapterText function
        ## the chapterUrl nd numChapters need to be set as well
        self.html = data
        self.add_chapter(self.story.getMetadata('title'),url)


    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Using data that we got from: %s' % url)

        data = self.html
        story = data[self.endindex[0]+23+self.endindex[1]:]
        story = self.make_soup(story).body

        if story == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        for script in story.find_all('script'):
            script.decompose()

        return self.utf8FromSoup(url,story)
