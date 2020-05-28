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

from __future__ import absolute_import
import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions


# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FanFiktionDeAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FanFiktionDeAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/s/'+self.story.getMetadata('storyId') + '/1')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ffde')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d.%m.%Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.fanfiktion.de'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/s/46ccbef30000616306614050 https://"+cls.getSiteDomain()+"/s/46ccbef30000616306614050/1 https://"+cls.getSiteDomain()+"/s/46ccbef30000616306614050/1/story-name"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://"+self.getSiteDomain()+"/s/")+r"\w+(/\d+)?"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

        ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Diese Geschichte wurde als entwicklungsbeeintr' in data \
                or 'There is no such account on our website' in data \
                or "Noch kein registrierter Benutzer?" in data:
            return True
        else:
            return False

    def performLogin(self,url):
        params = {}

        if self.password:
            params['nickname'] = self.username
            params['passwd'] = self.password
        else:
            params['nickname'] = self.getConfig("username")
            params['passwd'] = self.getConfig("password")
        params['savelogindata'] = '1'
        params['a'] = 'l'
        params['submit'] = 'Login...'

        loginUrl = 'https://www.fanfiktion.de/'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['nickname']))
        soup = self.make_soup(self._postUrl(loginUrl,params))
        if not soup.find('a', title='Logout'):
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['nickname']))
            raise exceptions.FailedToLogin(url,params['nickname'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

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
            data = self._fetchUrl(url,usecache=False)

        if "Uhr ist diese Geschichte nur nach einer" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Auserhalb der Zeit von 23:00 Uhr bis 04:00 Uhr ist diese Geschichte nur nach einer erfolgreichen Altersverifikation zuganglich.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r'/s/'+self.story.getMetadata('storyId')+"/"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        head = soup.find('div', {'class' : 'story-left'})
        a = head.find('a')
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',stripHTML(a))

        # Find the chapters:
        for chapter in soup.find('select').findAll('option'):
            self.add_chapter(chapter,'https://'+self.host+'/s/'+self.story.getMetadata('storyId')+'/'+chapter['value'])

        ## title="Wörter" failed with max_zalgo:1
        self.story.setMetadata('numWords',stripHTML(soup.find("span",{'class':"fa-keyboard"}).parent).replace('.','')) # 1.234 = 1,234
        self.story.setMetadata('language','German')

        self.story.setMetadata('datePublished', makeDate(stripHTML(head.find('span',title='erstellt').parent), self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(stripHTML(head.find('span',title='aktualisiert').parent), self.dateformat))

        ## Genre now shares a line with rating.
        genres=stripHTML(head.find('span',class_='fa-angle-right').next_sibling)
        self.story.extendList('genre',genres[:genres.index(' / ')].split(', '))
        self.story.setMetadata('rating', genres[genres.index(' / ')+3:])

        # self.story.addToList('category',stripHTML(soup.find('span',id='ffcbox-story-topic-1')).split('/')[2].strip())
        for a in soup.find('span',id='ffcbox-story-topic-1').find_all('a',href=re.compile(r'/c/')):
            cat = stripHTML(a)
            if cat != 'Fanfiction':
                self.story.addToList('category',cat)

        for span in soup.find_all('span',class_='badge-character'):
            self.story.addToList('characters',stripHTML(span))

        try:
            self.story.setMetadata('native_status', head.find_all('span',{'class':'titled-icon'})[3]['title'])
        except e:
            logger.debug("Failed to find native status:%s"%e)

        if head.find('span',title='Fertiggestellt'):
            self.story.setMetadata('status', 'Completed')
        elif head.find('span',title='Pausiert'):
            self.story.setMetadata('status', 'Paused')
        elif head.find('span',title='Abgebrochen'):
            self.story.setMetadata('status', 'Cancelled')
        else:
            self.story.setMetadata('status', 'In-Progress')

        ## Get description from own URL:
        ## /?a=v&storyid=46ccbef30000616306614050&s=1
        descsoup = self.make_soup(self._fetchUrl("https://"+self.getSiteDomain()+"/?a=v&storyid="+self.story.getMetadata('storyId')+"&s=1"))
        self.setDescription(url,stripHTML(descsoup))

        # #find metadata on the author's page
        # asoup = self.make_soup(self._fetchUrl("https://"+self.getSiteDomain()+"?a=q&a1=v&t=nickdetailsstories&lbi=stories&ar=0&nick="+self.story.getMetadata('authorId')))
        # tr=asoup.findAll('tr')
        # for i in range(1,len(tr)):
        #     a = tr[i].find('a')
        #     if '/s/'+self.story.getMetadata('storyId')+'/1/' in a['href']:
        #         break

        # td = tr[i].findAll('td')
        # self.story.addToList('category',stripHTML(td[2]))
        # self.story.setMetadata('rating', stripHTML(td[5]))
        # self.story.setMetadata('numWords', stripHTML(td[6]))




    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)
        time.sleep(0.5) ## ffde has "floodlock" protection

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'storytext'})
        for a in div.findAll('script'):
            a.extract()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
