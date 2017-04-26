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

# Adapted by GComyn on April 24, 2017


import logging
import re
import sys
import urllib2
from datetime import datetime, timedelta

from base_adapter import BaseSiteAdapter,  makeDate
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

UNIX_EPOCHE = datetime.fromtimestamp(0)
logger = logging.getLogger(__name__)


def getClass():
    return InkBunnyNetSiteAdapter

class InkBunnyNetSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = 'NoneGiven'  # if left empty, site doesn't return any message at all.
        self.password = ''
        self.is_adult = False

        # get storyId from url
        # https://inkbunny.net/submissionview.php?id=1342100
        self.story.setMetadata('storyId', self.parsedUrl.query.split('=')[1])

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'ibnet')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y %H:%M"

        # This is a 1 story/page site, so I'm initializing the soup variable here for the getChapterText Function
        self.soup = None

    @staticmethod  # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'inkbunny.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://' + cls.getSiteDomain() + '/submissionview.php?id=1234567'

    def getSiteURLPattern(self):
        return r'https://' + re.escape(self.getSiteDomain()) + r'/submissionview.php\?id=([0-9]+)'

    def performLogin(self,url,soup):
        params = {
            'token':soup.find("input",{"name":"token"})['value'],
            }

        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/login_process.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['username']))
        d = self._postUrl(loginUrl,params,usecache=False)

        if "Logout" not in d:
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
            return False
        else:
            return True

    # Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        url = self.url

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        if 'ERROR: Invalid submission_id or no submission_id requested.' in data:
            raise exceptions.StoryDoesNotExist('{0} says: "ERROR: Invalid submission_id or no submission_id requested." for url "{1}"'.format(self.getSiteDomain(), self.url))

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        ## To view content, we need to login
        if 'Submission blocked' in data:
            if self.performLogin(url,soup): # performLogin raises
                                       # FailedToLogin if it fails.
                soup = self.make_soup(self._fetchUrl(url,usecache=False))

        # removing all of the scripts
        for tag in soup.findAll('script'):
            tag.extract()

        # Now go hunting for all the meta data and the chapter list.

        # Title
        title = soup.find_all('h1')[1]
        self.story.setMetadata('title', stripHTML(title))

        # Get Author
        author = soup.find_all('table')[3].a
        self.story.setMetadata('author', stripHTML(author))
        self.story.setMetadata('authorId', stripHTML(author))
        self.story.setMetadata('authorUrl', 'https://'+self.getSiteDomain()+'/'+author['href'])

        # This is the block that holds the metadata
        bookdetails = soup.find('div', {'class': 'elephant elephant_bottom elephant_white'}).find('div', {'class':'content'})
        
        ## Getting the summary
        synopsis = bookdetails.span

        if not self.getConfig('keep_summary_html'):
            synopsis = stripHTML(synopsis)

        self.setDescription(url, stripHTML(synopsis))

        #Getting Keywords/Genres
        keywords = bookdetails.find('div', {'id':'kw_scroll'}).find_next_siblings('div')[0].find_all('a')
        for kword in keywords:
            self.story.addToList('genre', stripHTML(kword))

        # Getting the Category
        for div in bookdetails.find_all('div'):
            if 'Details' == stripHTML(div).strip():
                self.story.setMetadata('category', div.find_next_siblings('div')[0].span.next_sibling.strip())
            elif 'Rating:' == stripHTML(div).strip()[:7]:
                rating = div.span.next_sibling.strip()
                self.story.setMetadata('rating', rating)
                break

        ## Getting the update date
        updated = stripHTML(bookdetails.find('span', {'id':'submittime_exact'}))
        updated = updated[:updated.index(':')+3].strip()
        self.story.setMetadata('dateUpdated', makeDate(updated, self.dateformat))
        
        # This is a 1 story/page site, so we set the chapterUrls up with the story url and title
        self.chapterUrls.append((self.story.getMetadata('title'), url))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        if get_cover:
            cover_img = soup.find('img', {'id':'magicbox'})
            if cover_img:
                self.setCoverImage(url, cover_img['src'])

        ## Save for use below
        self.soup = soup

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Using the chapter text retrieved from: %s' % url)

        story = self.soup.find('div', {'id': 'storysectionbar'})
        if story is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, story) 
