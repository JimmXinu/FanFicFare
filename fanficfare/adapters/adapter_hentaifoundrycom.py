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

class HentaiFoundryComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','hf')
        self.is_adult=False

        match = re.compile(self.getSiteURLPattern()).match(self.url)
        storyId = match.group('storyId')
        self.story.setMetadata('storyId', storyId)
        authorId = match.group('authorId')
        self.story.setMetadata('authorId', authorId)
        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() +
                     '/stories/user/' + '/'.join([authorId,storyId,match.group('storyURLTitle')]))

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"

    @staticmethod
    def getSiteDomain():
        return 'www.hentai-foundry.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.hentai-foundry.com/stories/user/Author/12345/Story-Title"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://")+r"(www\.)?"+re.escape("hentai-foundry.com/stories/user/")+r"(?P<authorId>[^/]+)/(?P<storyId>\d+)/(?P<storyURLTitle>[^/]+)" # ignore any chapter

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):
        url = self.url
        logger.debug("URL: "+url)

        ## You need to have your is_adult set to true to get this story
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)
        else:
            url = url+"?enterAgree=1"

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        soup = self.make_soup(data)

        ## Title
        h1 = soup.find('h1', class_='titleSemantic')
        self.story.setMetadata('title',stripHTML(h1))

        storyInfo = h1.find_next('td', class_='storyInfo')
        storyDescript = h1.find_next('td', class_='storyDescript')
        
        # Find authorid and URL from... author url.
        a = soup.find('span',string='Author').find_next('a')
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',stripHTML(a))

        meta_labels = {'Submitted':'datePublished',
                       'Updated':'dateUpdated',
                       'Status':'status',
                       'Words:':'numWords',
                       'Size:':'size',
                       'Comments:':'comments',
                       'Views:':'views',
                       'Faves...:':'favs',
                       'Rating:':'vote_rating',
                       }
        for label in storyInfo.find_all('span',class_='label'):
            l = meta_labels.get(stripHTML(label),None)
            if l:
                val = label.next_sibling#.strip()
                indent = label.find_next('span',class_='indent')
                if l.startswith('date'):
                    val = makeDate(stripHTML(indent),self.dateformat)
                elif l == 'status':
                    if 'Complete' in indent:
                        val = 'Completed'
                    else:
                        val = 'In-Progress'
                self.story.setMetadata(l,val)
                # logger.debug("%s => '%s'"%(l,val))
        
        # process and remove non-desc stuff from storyDescript
        storyDescript.find('div', class_='storyRead').extract()
        storyDescript.find('div', class_='storyVote').extract()
        warnings = storyDescript.find('div', class_='ratings_box')
        for warn in warnings.find_all('span',class_='rating'):
            self.story.addToList('warnings',warn['title'])
        warnings.extract()

        cats = storyDescript.find('div', class_='storyCategoryRating')
        for cat in cats.find_all('a'):
            self.story.addToList('category',stripHTML(cat))
        cats.extract()

        storyDescript.name='div' # change td to div.
        self.setDescription(self.url,storyDescript)

        ## process chapters
        chapter_labels = {'Submitted:':'date',
                          'Updated:':'update',
                          'Word count:':'words',
                          'Size:':'size',
                          'Comments:':'comments',
                          'views:':'views',
                       }
        updateDate = self.story.getMetadataRaw('dateUpdated')
        boxbody = h1.find_next('div',class_='boxbody')
        for a in boxbody.find_all('a'):
            # <small>
	    # <b>Submitted:</b> July 31, 2018
            # <b>Updated:</b> July 31, 2018<br />
            # <b>Word count:</b> 4181
            # <b>Size:</b> 23k
            # <b>Comments:</b> 0
            # <b>views:</b> 3927
	    # </small>
            meta = a.find_next('small')
            chap_meta = {}
            for label in meta.find_all('b'):
                l = chapter_labels.get(label.string,None)
                if l:
                    val = label.next_sibling.replace('•','').strip() # remove bullets.
                    if l.endswith('date'):
                        d = makeDate(val,self.dateformat)
                        if d > updateDate:
                            updateDate = d
                        val = d.strftime(self.getConfig("datechapter_format",self.getConfig("datePublished_format","%Y-%m-%d")))
                    chap_meta[l] = val
            self.add_chapter(stripHTML(a),'https://'+self.host+a['href'],chap_meta)
        ## site can screw up updated date, take from newest chapter date if greater.
        if updateDate != self.story.getMetadataRaw('dateUpdated'):
            self.story.setMetadata('dateUpdated',updateDate)


    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        soup = self.make_soup(data)
        div = soup.select_one("section#viewChapter div.boxbody")
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return HentaiFoundryComSiteAdapter
