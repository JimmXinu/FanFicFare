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

from __future__ import absolute_import, division, unicode_literals, print_function
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML, removeAllEntities
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class HarryPotterFanFictionComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','hp')
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only psid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d %H:%M%p"

        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/viewstory.php?psid='+self.story.getMetadata('storyId'))


    @staticmethod
    def getSiteDomain():
        return 'harrypotterfanfiction.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://harrypotterfanfiction.com/viewstory.php?psid=1234"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://")+r"(www\.)?"+re.escape("harrypotterfanfiction.com/viewstory.php?psid=")+r"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):

        url = self.url
        if self.is_adult or self.getConfig("is_adult"):
            url = url+'&showRestricted'
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "This story may contain chapters not appropriate for a general audience." in data and not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        ## Don't know if these still apply
        # if "Access denied. This story has not been validated by the adminstrators of this site." in data:
        #     raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        # elif "ERROR locating story meta for psid" in data:
        #     raise exceptions.StoryDoesNotExist(self.url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        ## Title
        h2 = soup.find('h2')
        h2.find('i').extract() # remove author
        self.story.setMetadata('title',stripHTML(h2))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string[3:]) # remove 'by '

        ## hpcom doesn't always give us total words--but it does give
        ## us words/chapter.  I'd rather add than fetch and parse
        ## another page.
        chapter_words=0
        for tr in soup.find('table',{'class':'table-chapters'}).find('tbody').findAll('tr'):
            tdstr = tr.findAll('td')[2].string
            chapter = tr.find('a')
            chpt=re.sub(r'^.*?(\?chapterid=\d+).*?',r'\1',chapter['href'])
            added = self.add_chapter(chapter,'https://'+self.host+'/viewstory.php'+chpt)
            if added and tdstr and tdstr.isdigit():
                chapter_words+=int(tdstr)
                ## used below if total words from site not found

        # fetch author page to get story description.
        authorsoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))

        for story in authorsoup.find_all('article',class_='story-summary'):
            storya = story.find('h3').find('a',href=re.compile(r"^/viewstory.php\?psid="+self.story.getMetadata('storyId')))
            if storya:
                storydiv = storya.find_parent('div')
                break

        # desc is escaped html in attr on iframe.
        iframe = storydiv.find('iframe')
        iframesrc = removeAllEntities(iframe['srcdoc'])
        # logger.debug(iframesrc)
        descsoup=self.make_soup(iframesrc)
        desc = descsoup.body
        desc.name='div'   # change body tag to div
        del desc['class'] # clear class='iframe'
        # logger.debug(desc.body)
        self.setDescription(url,desc)

        # <div class='entry'>
        # <div class='entry__key'>Rating</div>
        # <div class='entry__value'>Mature</div>
        # </div>

        meta_key_map = {
            'Rating':'rating',
            'Words':'numWords',
            'Characters':'characters',
            'Primary Relationship':'ships',
            'Secondary Relationship(s)':'ships',
            'Genre(s)':'genre',
            'Era':'era',
            'Advisory':'warnings',
            'Story Reviews':'reviews',
#            'Status':'', # Status is treated special
            'First Published':'datePublished',
            'Last Updated':'dateUpdated',
            }
        for key in soup.find_all('div',{'class':'entry__key'}):
            value = stripHTML(key.find_next('div',{'class':'entry__value'}))
            key = stripHTML(key)
            meta = meta_key_map.get(key,None)
            if meta:
                if meta.startswith('date'):
                    value = makeDate(value,self.dateformat)
                if meta in ('characters','genre','ships'):
                    self.story.extendList(meta,value.split(','))
                else:
                    self.story.setMetadata(meta,value)
            if key == 'Status':
                if value == 'WIP':
                    value = 'In-Progress'
                elif value == 'COMPLETED':
                    value = 'Completed'
                # 'Abandoned' and other possible values used as-is
                self.story.setMetadata('status',value)

        # older stories don't present total words, use sum from chapters.
        if not self.story.getMetadata('numWords'):
            self.story.setMetadata('numWords',chapter_words)

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)
        div = soup.find('div', {'class' : 'storytext-container'})
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return HarryPotterFanFictionComSiteAdapter
