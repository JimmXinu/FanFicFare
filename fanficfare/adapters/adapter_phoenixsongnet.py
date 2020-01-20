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

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return PhoenixSongNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class PhoenixSongNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[3])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/fanfiction/story/' +self.story.getMetadata('storyId')+'/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','phs')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.phoenixsong.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/fanfiction/story/1234/"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/fanfiction/story/")+r"\d+/?$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Please login to continue.' in data:
            return True
        else:
            return False

    def performLogin(self, url):
        params = {}

        if self.password:
            params['txtusername'] = self.username
            params['txtpassword'] = self.password
        else:
            params['txtusername'] = self.getConfig("username")
            params['txtpassword'] = self.getConfig("password")
        #params['remember'] = '1'
        params['login'] = 'Login'

        loginUrl = 'https://' + self.getSiteDomain() + '/users/processlogin.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['txtusername']))
        d = self._fetchUrl(loginUrl, params)

        if 'Please login to continue.' in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['txtusername']))
            raise exceptions.FailedToLogin(url,params['txtusername'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        try:
            if self.getConfig('force_login'):
                self.performLogin(url)
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        b = soup.find('div', {'id' : 'nav25'})
        a = b.find('a', href=re.compile(r'fanfiction/story/'+self.story.getMetadata('storyId')+"/$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.  /fanfiction/stories.php?psid=125
        a = b.find('a', href=re.compile(r"/fanfiction/stories.php\?psid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        chapters = soup.find('select')
        if chapters == None:
            self.add_chapter(self.story.getMetadata('title'),url)
            for b in soup.findAll('b'):
                if b.text == "Updated":
                    date = b.nextSibling.string.split(': ')[1].split(',')
                    self.story.setMetadata('datePublished', makeDate(date[0]+date[1], self.dateformat))
                    self.story.setMetadata('dateUpdated', makeDate(date[0]+date[1], self.dateformat))
        else:
            i = 0
            chapters = chapters.findAll('option')
            for chapter in chapters:
                self.add_chapter(chapter,'https://'+self.host+chapter['value'])
                if i == 0:
                    self.story.setMetadata('storyId',chapter['value'].split('/')[3])
                    head = self.make_soup(self._fetchUrl('https://'+self.host+chapter['value'])).findAll('b')
                    for b in head:
                        if b.text == "Updated":
                            date = b.nextSibling.string.split(': ')[1].split(',')
                            self.story.setMetadata('datePublished', makeDate(date[0]+date[1], self.dateformat))

                if  i == (len(chapters)-1):
                    head = self.make_soup(self._fetchUrl('https://'+self.host+chapter['value'])).findAll('b')
                    for b in head:
                        if b.text == "Updated":
                            date = b.nextSibling.string.split(': ')[1].split(',')
                            self.story.setMetadata('dateUpdated', makeDate(date[0]+date[1], self.dateformat))
                i = i+1



        asoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))

        info = asoup.find('a', href=re.compile(r'fanfiction/story/'+self.story.getMetadata('storyId')+"/$"))
        while info != None:
            info = info.findNext('div')
            b = info.find('b')
            val = b.nextSibling

            if 'Rating' in b.string:
                self.story.setMetadata('rating', val.string.split(': ')[1])

            if 'Words' in b.string:
                self.story.setMetadata('numWords', val.string.split(': ')[1])

            if 'Setting' in b.string:
                self.story.addToList('category', val.string.split(': ')[1])

            if 'Status' in b.string:
                if 'Completed' in val:
                    val = 'Completed'
                else:
                    val = 'In-Progress'
                self.story.setMetadata('status', val)

            if 'Summary' in b.string:
                b.extract()
                info.find('br').extract()
                self.setDescription(url,info)
                break


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        chapter=self.make_soup('<div class="story"></div>')
        for p in soup.findAll(['p','blockquote']):
            if "This is for problems with the formatting or the layout of the chapter." in stripHTML(p):
                break
            chapter.append(p)

        for a in chapter.findAll('div'):
            a.extract()
        for a in chapter.findAll('table'):
            a.extract()
        for a in chapter.findAll('script'):
            a.extract()
        for a in chapter.findAll('form'):
            a.extract()
        for a in chapter.findAll('textarea'):
            a.extract()


        if None == chapter:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)
