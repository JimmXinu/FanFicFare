# -*- coding: utf-8 -*-
# Copyright 2018 FanFicFare team
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
### Adapted by Rikkit on November 9. 2017
###=================================================================================================
### Tested with Calibre
####################################################################################################

from __future__ import absolute_import
import logging
import re
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

from bs4 import Comment
from ..htmlcleanup import removeEntities, stripHTML, fix_excess_space
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)
HTML_TAGS = (
    'a', 'abbr', 'acronym', 'address', 'applet', 'area', 'article', 'aside', 'audio', 'b', 'base', 'basefont', 'bdi',
    'bdo', 'big', 'blockquote', 'body', 'br', 'button', 'canvas', 'caption', 'center', 'cite', 'code', 'col',
    'colgroup', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'dir', 'div', 'dl', 'dt', 'em', 'embed',
    'fieldset', 'figcaption', 'figure', 'font', 'footer', 'form', 'frame', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5',
    'h6', 'head', 'header', 'hr', 'html', 'i', 'iframe', 'img', 'input', 'ins', 'kbd', 'label', 'legend', 'li', 'link',
    'main', 'map', 'mark', 'menu', 'menuitem', 'meta', 'meter', 'nav', 'noframes', 'noscript', 'object', 'ol',
    'optgroup', 'option', 'output', 'p', 'param', 'picture', 'pre', 'progress', 'q', 'rp', 'rt', 'ruby', 's', 'samp',
    'script', 'section', 'select', 'small', 'source', 'span', 'strike', 'strong', 'style', 'sub', 'summary', 'sup',
    'svg', 'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th', 'thead', 'time', 'title', 'tr', 'track', 'tt',
    'u', 'ul', 'var', 'video', 'wbr')


def getClass():
    ''' Initializing the class '''
    return LightNovelGateSiteAdapter

class LightNovelGateSiteAdapter(BaseSiteAdapter):
    ''' Adapter for LightNovelGate.com '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'lng')

        self.dateformat = "%Y-%m-%dT%H:%M:%S+00:00"

        self.is_adult = False
        self.username = None
        self.password = None

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(), url)
        if m:
            self.story.setMetadata('storyId', m.group('id'))

            # normalized story URL.
            self._setURL("https://"+self.getSiteDomain()
                         +"/novel/"+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'novelonlinefull.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['lightnovelgate.com',cls.getSiteDomain()]

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return ['lightnovelgate.com',cls.getSiteDomain()]

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://novelonlinefull.com/novel/astoryname"

    def getSiteURLPattern(self):
        # http://novelonlinefull.com/novel/stellar_transformation
        return r"https?://(novelonlinefull|lightnovelgate)\.com/novel/(?P<id>[^/]+)"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter. From that we will get almost all the
        # metadata and chapter list

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        soup = self.make_soup(data)

        ## I'm going to remove all of the scripts at the beginning...
        for tag in soup.find_all('script'):
            tag.extract()

        ## getting Author
        try:
            author_link = soup.find('span', string='Author(s): ').find_next_sibling("a")
            author_name = author_link.string
            author_url = author_link['href']
            self.story.setMetadata('authorId', author_name.lower())
            self.story.setMetadata('authorUrl', author_url)
            self.story.setMetadata('author', author_name)
        except:
            self.story.setMetadata('authorId', 'unknown')
            self.story.setMetadata('author', 'Unknown')

        ## get title
        title = soup.find_all('span', {'itemprop':'title'})[1].string
        self.story.setMetadata('title', title)

        updatedSpan = soup.find('span', string='LAST UPDATED : ')
        dateUpd = updatedSpan.parent
        updatedSpan.extract() # discard label
        # example: 08-NOV-2017 18:21
        self.story.setMetadata('dateUpdated', makeDate(stripHTML(dateUpd), '%d-%b-%Y %H:%M'))

        ## getting status
        status = soup.find('span', string='STATUS : ').find_next_sibling("a").string
        if status == 'completed':
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        ## getting genres
        genres = soup.find('span', string='GENRES: ').find_next_siblings("a")
        genre_list = []
        for agenre in genres:
            genre_list.append(agenre.string)
        self.story.extendList('genre',genre_list)

        ## getting cover
        img = soup.find('img', class_='wp-post-image')
        if img:
            self.setCoverImage(url,img['src'])

        ## getting chapters
        cdata = soup.select('.chapter-list .row')
        cdata.reverse()
        cdates = []

        for row in cdata:
            # <span>May-08-18</span>
            dt = row.find_all('span')[-1].string
            cdates.append(makeDate(dt, '%b-%d-%y'))
            clink = row.find('a')
            self.add_chapter(clink.string, clink['href'])

        cdates.sort()
        # dateUpdated in upper part show only date of last chapter, but if 
        # chapter in middle will be updated - it will be ignored. So we select
        # dates manually
        self.story.setMetadata('dateUpdated', cdates[-1])
        self.story.setMetadata('datePublished', cdates[0])

        ## getting description
        cdata = soup.select_one('#noidungm')
        cdata.find('h2').extract()
        self.setDescription(url, cdata)

    def getChapterText(self, url):
        data = self.get_request(url)

        if self.getConfig('fix_excess_space', True):
            data = fix_excess_space(data)

        soup = self.make_soup(data)

        story = soup.find('div', {'id':'vung_doc'})
        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        # Some comments we will get is invalid. Remove them all.
        [comment.extract() for comment in story.find_all(text=lambda text:isinstance(text, Comment))]

        # We don't need links. They have a bad css and they are not working most of times.
        [a.extract() for a in story.find_all('a')]

        # Some tags have non-standard tag name.
        for tag in story.findAll(recursive=True):
            if tag.name not in HTML_TAGS:
                tag.name = 'span'

        return self.utf8FromSoup(url, story)
