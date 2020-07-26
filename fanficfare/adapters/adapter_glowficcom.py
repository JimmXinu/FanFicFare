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

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class GlowficComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','gf')

        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        self.username = "NoneGiven"
        self.password = ""

    @staticmethod
    def getSiteDomain():
        return 'glowfic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://glowfic.com/posts/1234"

    def getSiteURLPattern(self):
        return r"https?:"+re.escape(r"//"+self.getSiteDomain())+r"/posts/\d+?$"

    def performLogin(self,url):
        params = {}

        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['username']))
        d = self._postUrl(loginUrl,params,usecache=False)

        if "Login attempt failed..." in d:
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
            return False
        else:
            return True

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.url
        logger.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url + '?view=flat')
            metadata = self._fetchUrl(url + '/stats')
            # non-existent/removed story urls get thrown to the front page.
            if "<title>Continuities | Glowfic Constellation</title>" in data:
                raise exceptions.StoryDoesNotExist(self.url)
            soup = self.make_soup(data)
            metasoup = self.make_soup(metadata)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # title - span with id post-title will be title.
        titlespan = soup.find('span',{'id':'post-title'})
        self.story.setMetadata('title', stripHTML(titlespan.get_text()))

        # description
        descriptiontd = metasoup.find('td',{'class':'post-subheader'})
        if descriptiontd is not None:
            self.setDescription(url,descriptiontd.get_text())
            #self.story.setMetadata('description', descriptiontd.get_text())

        metadata_tds = {}
        metatable = metasoup.find('table',{'id':'stats'})
        metabody = metatable.tbody
        for row in metabody.findAll('tr'):
            metadata_tds[row.th.string.lower().strip()] = row.td

        # status
        statusstr = metadata_tds['status'].get_text()
        if 'Complete' in statusstr:
            self.story.setMetadata('status', 'Completed')
        elif 'In Progress' in statusstr:
            self.story.setMetadata('status', 'In-Progress')
        else:
            self.story.setMetadata('status', statusstr.strip())
        del metadata_tds['status']

        # authors
        authors = metadata_tds['authors'].ul.findAll('a')
        for a in authors:
            self.story.addToList('author',a.string)
            self.story.addToList('authorId',a['href'].split('/')[-1])
            self.story.addToList('authorUrl','https://'+self.host+a['href'])
        del metadata_tds['authors']

        # warnings
        if 'content warnings' in metadata_tds.keys():
            warnings = metadata_tds['content warnings'].findAll('a')
            for a in warnings:
                self.story.addToList('warnings',a.string)
            del metadata_tds['content warnings']

        # characters
        if 'characters' in metadata_tds.keys():
            for a in metadata_tds['characters'].findAll('a',href=re.compile(r'/characters/')):
                self.story.addToList('characters',a.string)
            del metadata_tds['characters']

        # setting
        if 'setting' in metadata_tds.keys():
            for a in metadata_tds['setting'].findAll('a'):
                self.story.addToList('setting',a.string)
            del metadata_tds['setting']

        self.story.setMetadata('dateUpdated',makeDate(metadata_tds['time last updated'].string, '%b %d, %Y  %H:%M %p'))
        del metadata_tds['time last updated']

        self.story.setMetadata('datePublished',makeDate(metadata_tds['time begun'].string, '%b %d, %Y  %H:%M %p'))
        del metadata_tds['time begun']

        m = re.match(r'([0-9,]+).*?',metadata_tds['word count'].get_text().strip())
        self.story.setMetadata('numWords',m.group(1))
        del metadata_tds['word count']

        self.story.setMetadata('audience',metadata_tds['audience'].get_text().strip())
        del metadata_tds['audience']

        for k, v in metadata_tds.items():
            logger.debug('Unhandled metadata key: %s' % k)

        chapters = soup.findAll('div',{'class':'post-container'})
        self.__chapter_contents = []
        for chapterdiv in chapters:
            othermeta = {}
            infodiv = chapterdiv.find('div',{'class':'post-info-box'})
            footer = chapterdiv.find('div',{'class':'post-footer'}).get_text().strip()
            icondiv = infodiv.find('div',{'class':'post-icon'})
            othermeta['post-icon'] = icondiv.img['src'] if icondiv is not None else ''
            othermeta['footer'] = footer
            infos = infodiv.find('div',{'class':'post-info-text'}).findAll('div')
            chaptertitle = ', '.join([footer] + [d.get_text().strip() for d in infos])
            for d in infos:
                othermeta[' '.join(d['class'])] = d.get_text().strip()
            post_content = chapterdiv.find('div',{'class':'post-content'})
            #othermeta['post-content'] = post_content
            self.__chapter_contents.append(post_content)
            chapter_url = u'https://%s%s'%(self.getSiteDomain(),chapterdiv.find('div',{'class':'post-edit-box'}).find('a')['href'])
            self.add_chapter(chaptertitle, chapter_url, othermeta=othermeta)

        return

    def getChapterTextNum(self, url, index):
        logger.debug('Getting cached chapter text from: %s (index: %d)' % (url, index))
        soup = self.__chapter_contents[index]

        return self.utf8FromSoup(url,soup)

def getClass():
    return GlowficComSiteAdapter
