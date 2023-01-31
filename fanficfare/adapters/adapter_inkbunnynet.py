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

# Adapted by GComyn on April 24, 2017
# Updated by GComyn on June 11, 2018

from __future__ import absolute_import
import logging
import re

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter,  makeDate
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

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
        # https://inkbunny.net/submissionview.php?id=1342100 --- old style story url
        # https://inkbunny.net/s/1234567 --  new style story url
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            # normalized story URL. gets rid of chapter if there, left with chapter index URL
            nurl = "https://"+self.getSiteDomain()+"/s/"+self.story.getMetadata('storyId')
            self._setURL(nurl)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

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
        return 'https://' + cls.getSiteDomain() + '/s/1234567'

    def getSiteURLPattern(self):
        # https://inkbunny.net/s/1234567
        # or old form:
        # https://inkbunny.net/submissionview.php?id=1234567
        return r'https://' + re.escape(self.getSiteDomain()) + r'/(submissionview.php\?id=|s/)(?P<id>\d+)'

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
        d = self.post_request(loginUrl,params,usecache=False)

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

        data = self.get_request(url)

        if 'ERROR: Invalid submission_id or no submission_id requested.' in data:
            raise exceptions.StoryDoesNotExist('{0} says: "ERROR: Invalid submission_id or no submission_id requested." for url "{1}"'.format(self.getSiteDomain(), self.url))

        soup = self.make_soup(data)

        ## To view content, we need to login
        if 'Submission blocked' in data:
            if self.performLogin(url,soup): # performLogin raises
                                       # FailedToLogin if it fails.
                soup = self.make_soup(self.get_request(url,usecache=False))

        # removing all of the scripts
        for tag in soup.findAll('script'):
            tag.extract()


        # Title
        title = soup.find_all('h1')[1]
        self.story.setMetadata('title', stripHTML(title))

        # Get Author
        authortag = soup.find('table',{'class':'pooltable'}).find('a',href=re.compile(r'/gallery/'))
        author = authortag['href'].split('/')[-1] # no separate ID
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'https://{}/{}'.format(self.getSiteDomain(),author))

        # This is the block that holds the metadata
        bookdetails = soup.find('div', {'class': 'elephant elephant_bottom elephant_white'}).find('div', {'class':'content'})

        ## Getting the summary
        synopsis = bookdetails.span

        if not self.getConfig('keep_summary_html'):
            synopsis = stripHTML(synopsis)

        self.setDescription(url, synopsis)

        #Getting Keywords/Genres
        keywords = bookdetails.find('div', {'id':'kw_scroll'}).find_next_siblings('div')[0].div.div.find_all('a')
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

        ## Getting the Published/Update date
        updated = stripHTML(bookdetails.find('span', {'id':'submittime_exact'}))
        updated = updated[:updated.index(':')+3].strip()
        self.story.setMetadata('dateUpdated', makeDate(updated, self.dateformat))
        self.story.setMetadata('datePublished', makeDate(updated, self.dateformat))

        # This is a 1 story/page site, so we set the chapter up with the story url and title
        self.add_chapter(self.story.getMetadata('title'), url)


        if get_cover:
            cover_img = soup.find('img', {'id':'magicbox'})
            if cover_img:
                # image content is treated like a normal image submission
                self.setCoverImage(url, cover_img['src'])
            else:
                # image content is present, but secondary to text file
                cover_div = soup.find('div', {'class': 'content magicboxParent'})
                cover_img = cover_div.find('img', {'class':'shadowedimage'}) if cover_div else None
                if cover_img:
                    self.setCoverImage(url, cover_img['src'])

        ## Save for use below
        self.soup = soup

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Using the chapter text retrieved from: %s' % url)

        story = self.soup.find('div', {'id': 'storysectionbar'})
        if story is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s No text block found -- non-story URL?" % url)

        return self.utf8FromSoup(url, story)
