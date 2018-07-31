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
    return DokugaComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class DokugaComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[3])


        # www.dokuga.com has two 'sections', shown in URL as
        # 'fanfiction' and 'spark' that change how things should be
        # handled.
        # http://www.dokuga.com/fanfiction/story/7528/1
        # http://www.dokuga.com/spark/story/7299/1
        self.section=self.parsedUrl.path.split('/',)[1]

        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/'+self.parsedUrl.path.split('/',)[1]+'/story/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','dkg')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        if 'fanfiction' in self.section:
            self.dateformat = "%d %b %Y"
        else:
            self.dateformat = "%m-%d-%y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.dokuga.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/fanfiction/story/1234/1 http://"+cls.getSiteDomain()+"/spark/story/1234/1"

    def getSiteURLPattern(self):
        return r"http://"+self.getSiteDomain()+"/(fanfiction|spark)?/story/\d+/?\d+?$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'The author has disabled anonymous viewing for this story.' in data:
            return True
        else:
            return False

    def performLogin(self, url,soup):
        params = {}

        if self.password:
            params['username'] = self.username
            params['passwd'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['passwd'] = self.getConfig("password")
        params['Submit'] = 'Submit'

        # copy all hidden input tags to pick up appropriate tokens.
        for tag in soup.findAll('input',{'type':'hidden'}):
            params[tag['name']] = tag['value']

        loginUrl = 'http://' + self.getSiteDomain() + '/fanfiction'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['username']))

        d = self._postUrl(loginUrl, params)

        if "Your session has expired. Please log in again." in d:
            d = self._postUrl(loginUrl, params)

        if "Logout" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
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
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url,soup)
            data = self._fetchUrl(url)
            soup = self.make_soup(data)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title and author
        a = soup.find('div', {'align' : 'center'}).find('h3')

        # Find authorid and URL from... author url.
        aut = a.find('a')
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        alink='http://'+self.host+aut['href']
        self.story.setMetadata('authorUrl','http://'+self.host+aut['href'])
        self.story.setMetadata('author',aut.string)
        aut.extract()

        a = a.string[:(len(a.string)-4)]
        self.story.setMetadata('title',stripHTML(a))

        # Find the chapters:
        chapters = soup.find('select').findAll('option')
        if len(chapters)==1:
            self.add_chapter(self.story.getMetadata('title'),'http://'+self.host+'/'+self.section+'/story/'+self.story.getMetadata('storyId')+'/1')
        else:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles. /fanfiction/story/7406/1
                self.add_chapter(chapter,'http://'+self.host+'/'+self.section+'/story/'+self.story.getMetadata('storyId')+'/'+chapter['value'])


        asoup = self.make_soup(self._fetchUrl(alink))

        if 'fanfiction' in self.section:
            asoup=asoup.find('div', {'id' : 'cb_tabid_52'}).find('div')

            #grab the rest of the metadata from the author's page
            for div in asoup.findAll('div'):
                nav=div.find('a', href=re.compile(r'/fanfiction/story/'+self.story.getMetadata('storyId')+"/1$"))
                if nav != None:
                    break
            div=div.nextSibling
            self.setDescription(url,div)

            div=div.nextSibling

            a=div.string.split('Rating: ')
            if len(a) == 2: self.story.setMetadata('rating', a[1].split('-')[0])

            a=div.string.split('Status: ')
            if len(a)==2:
                iscomp=a[1].split('-')[0]
                if 'Complete' in iscomp:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            a=div.string.split('Category: ')
            if len(a) == 2: self.story.addToList('category', a[1].split('-')[0])

            a=div.string.split('Created: ')
            if len(a) == 2: self.story.setMetadata('datePublished', makeDate(stripHTML(a[1].split('-')[0]), self.dateformat))

            a=div.string.split('Updated: ')
            if len(a) == 2: self.story.setMetadata('dateUpdated', makeDate(stripHTML(a[1]), self.dateformat))

            div=div.nextSibling.nextSibling
            a=div.string.split('Words: ')
            if len(a) == 2: self.story.setMetadata('numWords', a[1].split('-')[0])

            a=div.string.split('Genre: ')
            if len(a) == 2:
                for genre in a[1].split('-')[0].split(', '):
                    self.story.addToList('genre',genre)

        else:
            asoup=asoup.find('div', {'id' : 'maincol'}).find('div', {'class' : 'padding'})
            for div in asoup.findAll('div'):
                nav=div.find('a', href=re.compile(r'/spark/story/'+self.story.getMetadata('storyId')+"/1$"))
                if nav != None:
                    break

            div=div.nextSibling.nextSibling
            self.setDescription(url,div)
            self.story.addToList('category', 'Spark')

            div=div.nextSibling.nextSibling
            a=div.string.split('Rating: ')
            if len(a) == 2: self.story.setMetadata('rating', a[1].split(' - ')[0])

            a=div.string.split('Status: ')
            if len(a)==2:
                iscomp=a[1].split(' - ')[0]
                if 'Complete' in iscomp:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            a=div.string.split('Genre: ')
            if len(a)==2:
                for genre in a[1].split(' - ')[0].split('/'):
                    self.story.addToList('genre',genre)

            div=div.nextSibling.nextSibling

            a=div.string.split('Updated: ')
            if len(a)==2:
                date=a[1].split('      -')[0]
                self.story.setMetadata('dateUpdated', makeDate(date, self.dateformat))

                # does not have published date anywhere
                self.story.setMetadata('datePublished', makeDate(date, self.dateformat))

            a=div.string.split('Words ')
            if len(a)==2: self.story.setMetadata('numWords', a[1])

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'chtext'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
