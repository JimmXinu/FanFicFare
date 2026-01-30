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
### Adapted by GComyn on December 14, 2016
###=================================================================================================
### I ran this through a linter, and formatted it as per the suggestions, hence some of the lines
### are "chopped"
###=================================================================================================
### I have started to use lines of # on the line just before a function so they are easier to find.
####################################################################################################
from __future__ import absolute_import
'''
This will scrape the chapter text and metadata from stories on the site trekfanfiction.net
'''
import logging
import re
# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

##############################################################################
def getClass():
    return TrekFanFictionNetSiteAdapter

##############################################################################
class TrekFanFictionNetSiteAdapter(BaseSiteAdapter):

    ##########################################################################
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.is_adult=False

        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() +
             '/' + m.group('author') + '/' + self.story.getMetadata('storyId') +'/')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','trekffnet')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"

    ##########################################################################
    @staticmethod
    def getSiteDomain():
        return 'trekfanfiction.net'

    ##########################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/author/a-story-name/"

    ##########################################################################
    def getSiteURLPattern(self):
        return re.escape('https://{}'.format(
            self.getSiteDomain()))+r'/((?P<category>[^/]+)/)?(?P<author>[^/]+)/(?P<id>[^/]+)/?$'

    def get_request(self,url):
        try:
            return super(getClass(), self).get_request(url)
        except exceptions.HTTPErrorFFF as e:
            ## this site has a unique issue where it will serve pages
            ## with a 500 code while still serving the page. Browser
            ## silently accept this behavior, so users can't
            ## understand why FFF would choke.  This used to be down
            ## in the network code.
            if e.status_code == 500:
                return self.decode_data(e.data)
            else:
                raise

    ##########################################################################
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        if "Apologies, but we were unable to find what you were looking for." in data:
            raise exceptions.StoryDoesNotExist(
                '{} says: Apologies, but we were unable to find what you were looking for.'.format(
                    self.url))

        soup = self.make_soup(data)

        ## Title
        a = soup.find('h1', {'class':'entry-title'})
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r'https://'+self.getSiteDomain()+'/author/'))
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl',a['href'])
        self.story.setMetadata('author',a.string.strip())

        # This site has each story on one page, so there are no chapters to get. Will use original
        ## url since we can't get the chapter without this, I'm leaving it in.
        self.add_chapter(self.story.getMetadata('title'), url)

        # getting the rest of the metadata... there isn't much here, and the summary can only be
        # gotten on the author's page... so we'll get it to get the information from
        adata = self.get_request(self.story.getMetadata('authorUrl'))
        asoup = self.make_soup(adata)

        containers = asoup.find_all('div', {'class':'cat-container'})
        for container in containers:
            if container.find('a', href=url):
                break

        ## Getting the tags
        tags = container.find_all('a', {'rel':'tag'})
        for tag in tags:
            if 'category' not in tag['rel']:
                self.story.addToList('tags',tag.string)

        ## Getting the Categories
        tags = container.find_all('a', {'rel':'category tag'})
        for tag in tags:
            self.story.addToList('category', tag.string)

        ## Getting the summary
        summary = container.find('div', {'class':'excerpt'})
        self.setDescription(url, stripHTML(summary))

        ## Getting the Published Date.
        ### This is the only date for this site, since they only have one story per page...
        ### so I' going to put the date in the update metadata as well.
        datePub = container.find('div', {'class':'meta'}).get_text()[:8]
        self.story.setMetadata('datePublished', makeDate(datePub, self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(datePub, self.dateformat))

        ## Since this site doesn't "update" the stories, I'm goig to set the status
        ## to Complete
        self.story.setMetadata('status', "Completed")

        ## Getting the number of words
        ## I'm going to but using the entry-content that will be the same
        ## as what is used to get the chapter later
        ### XXX - This is a *character* count, not word count--JM
        # words = len(soup.find('div', {'class' : 'entry-content'}).get_text())
        # self.story.setMetadata('numWords', words)

        ## That is all of the metadata for this site, and since we are using the
        ## same page for the whole story, I'm going to save th soup to be used
        ## in the getChapterText function
        self.html = soup

    ##########################################################################
    def getChapterText(self, url):

        logger.debug('Using the html retrieved previously from: %s' % url)

        soup = self.html

        story = soup.find('div', {'class' : 'entry-content'})

        if None == story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        ## Sep2019 - I found at least one story that this removed all
        ## the content, but I have not idea which is more common.  No
        ## updates on the site in over a year, so I'm not going to
        ## worry about it too hard. --JM
        ## this site has mulitple divs within the content section, so I'm going to remove them.
        for tag in story.find_all('div'):
            tag.extract()

        return self.utf8FromSoup(url,story)
