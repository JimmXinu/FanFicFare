# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2018 FanFicFare team
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

# Software: eFiction
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
    return ThePetulantPoetessComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ThePetulantPoetessComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId') +'&i=1')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','tpp')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y/%m/%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.thepetulantpoetess.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'You must be a member to read this story.' in data \
                or "The Ministry of Magic does not have a record of that password. " in data:
            return True
        else:
            return False

    def performLogin(self, url):
        params = {}

        if self.password:
            params['penname'] = self.username
            params['password'] = self.password
        else:
            params['penname'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['cookiecheck'] = '1'
        params['submit'] = 'Submit'

        loginUrl = 'http://' + self.getSiteDomain() + '/user.php?action=login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['penname']))

        d = self._fetchUrl(loginUrl, params)

        if "My Account Page" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['penname']))
            raise exceptions.FailedToLogin(url,params['penname'])
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

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        chapters=soup.find('select', {'name' : 'sid'})
        if chapters == None:
            self.add_chapter(self.story.getMetadata('title'),url)
        else:
            for chapter in chapters.findAll('option', value=re.compile(r"viewstory.php\?sid=\d+&i=1")):
                # just in case there's tags, like <i> in chapter titles.
                self.add_chapter(chapter,'http://'+self.host+'/'+chapter['value'])


        # make sure that the story id is from the first chapter
        self.story.setMetadata('storyId',self.get_chapter(0,'url').split('=')[1].split('&')[0])

        #locate the story on author's page
        index = 1
        found = 0
        while found == 0:
            asoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')+"&page="+unicode(index)))

            for info in asoup.findAll('td', {'class' : 'highlightcolor1'}):
                a = info.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
                if a != None:
                    self.story.setMetadata('title',stripHTML(a))
                    found = 1
                    break
            index=index+1

        # extract metadata
        b=info.find('b')
        b.find('a').extract()
        self.story.setMetadata('rating', b.text.split('[')[1].split(']')[0])

        info = info.findNext('td', {'colspan' : '2'})
        for label in info.findAll('b'):
            value = label.nextSibling

            if "Category" in label.text:
                for cat in info.findAll('a'):
                    self.story.addToList('category',cat.string)

            if "Characters" in label.text:
                for char in value.split(', '):
                    self.story.addToList('characters',char)

            if "Genres" in label.text:
                for genre in value.split(', '):
                    if "General" not in genre:
                        self.story.addToList('genre',genre)

            if "Warnings" in label.text:
                for warning in value.split(', '):
                    if "none" not in warning.lower():
                        self.story.addToList('warnings',warning)


        info = info.findNext('td', {'class' : 'tblborder'})
        info.find('b').extract()
        self.setDescription(url,info)

        info = info.findNext('td', {'class' : 'highlightcolor2'})
        for label in info.findAll('b'):
            value = label.nextSibling

            if "Completed" in label.text:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label.text:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))

            if 'Updated' in label.text:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

            if 'Word Count' in label.text:
                self.story.setMetadata('numWords', value)


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.findAll('table')[2].findAll('td')[1]
        for a in div.findAll('div'):
            a.extract()
        div.name='div'

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
