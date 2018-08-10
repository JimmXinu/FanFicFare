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
### Adapted by Rikkit on April 15. 2018
###=================================================================================================
### Tested with Calibre
####################################################################################################

from __future__ import absolute_import
import logging
import re
import json
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

from bs4 import Comment
from ..htmlcleanup import removeEntities, stripHTML, fix_excess_space
from .. import exceptions as exceptions
from ..dateutils import parse_relative_date_string

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
    return WWWNovelAllComAdapter

class WWWNovelAllComAdapter(BaseSiteAdapter):
    ''' Adapter for www.novelall.com '''
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev', 'novall')

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
                         + "/novel/"+self.story.getMetadata('storyId')
                         + ".html")
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'www.novelall.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.novelall.com/novel/a-story-name.html"

    def getSiteURLPattern(self):
        # https://www.novelall.com/novel/Castle-of-Black-Iron.html
        return r"https://www\.novelall\.com/novel/(?P<id>[^\.]+)\.html"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):
        if self.is_adult or self.getConfig("is_adult"):
            addurl = "?waring=1"
        else:
            addurl = ""

        url = self.url+addurl
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)

        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(url))
            else:
                raise e

        ## You need to have your is_adult set to true to get this story
        if "Please click here to continue the reading." in data:
            raise exceptions.AdultCheckRequired(self.url)

        soup = self.make_soup(data)

        story_ld = json.loads(soup.find('script', type='application/ld+json').string)
        title = story_ld["itemReviewed"]["name"]
        authors = story_ld["author"]["name"].split(',')
        self.story.setMetadata('title', title)
        for author in authors:
            self.story.addToList('author', author)
            self.story.addToList('authorId', author)
            # https://www.novelall.com/search/?author=Li%20Xianyu
            self.story.addToList("authorUrl", "https://%s/search/?author=%s" % (self.getSiteDomain(), author))
        self.story.setMetadata('stars',story_ld["reviewRating"]["ratingValue"])
        self.story.setMetadata('translator',story_ld["publisher"]["name"])

        ## getting votes
        mc = re.match(r"\((?P<votes>[\d,]+) votes\)", data)
        if mc:
            self.story.setMetadata('votes', mc.group('votes'))

        ## getting status
        status = soup.find('span', string='Status:').next_sibling.strip()
        if status == 'Completed':
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        ## getting release frequency
        rf = soup.find('span', string='Release Frequency:')
        if rf:
            self.story.setMetadata('releaseFrequency', rf.next_sibling.strip())

        ## getting released
        released = soup.find('span', string='Released:')
        if released:
            self.story.setMetadata('released', released.find_next_sibling('a').string.strip())

        ## getting follows
        follows = soup.find('num', {"id": "follow_num"})
        if follows:
            self.story.setMetadata('follows', follows.string)

        ## getting views
        mc = re.match(r"It has (?P<views>[\d,]+) views", data)
        if mc:
            self.story.setMetadata('views', mc.group('views'))

        ## getting alternative titles
        alt_titles = soup.find('span', string='Alternative(s):')
        if alt_titles:
            self.story.setMetadata('altTitles', alt_titles.next_sibling.string.split('; '))

        ## getting genres
        for a in soup.find('span', string='Genre(s):').find_next_siblings("a"):
            self.story.addToList('genre', a.string)

        ## getting tags
        tags = soup.find('span', string='Tag(s):')
        if tags:
            for a in tags.find_next_siblings("a"):
                self.story.addToList('sitetags', a.string)

        ## getting description
        self.setDescription(url, soup.select_one('#show').string.strip())

        ## getting cover
        img = soup.find('img', class_='detail-cover')
        if img:
            self.setCoverImage(url,img['src'])

        ## getting chapters
        cdata = soup.select('.detail-chlist li')
        cdata.reverse()
        cdates = []

        for li in cdata:
            # <span class="time">31 minutes ago</span>s
            # <span class="time">Jul 15, 2017</span>
            dt = li.select_one('.time').string
            if "ago" in dt:
                cdates.append(parse_relative_date_string(dt))
            else:
                cdates.append(makeDate(dt, '%b %d, %Y'))
            # <a href="https://www.novelall.com/chapter/Stellar-Transformation-Volume-18-Chapter-45-part2/616971/" title="Stellar Transformation Volume 18 Chapter 45 part2">
            a = li.find('a')
            ctitle = re.sub(r"^%s(.+)$" % re.escape(title), r"\1", a['title'], 0, re.UNICODE | re.IGNORECASE).strip()
            self.add_chapter(ctitle, a['href'])

        cdates.sort()
        self.story.setMetadata('datePublished', cdates[0])
        self.story.setMetadata('dateUpdated', cdates[-1])


    def getChapterText(self, url):
        data = self._fetchUrl(url)

        # remove unnecessary <br> created to add space between advert
        data = re.sub(r"<br><script", "<script", data)
        data = re.sub(r"script><br>", "script>", data)

        if self.getConfig('fix_excess_space', False):
            data = fix_excess_space(data)

        soup = self.make_soup(data)

        story = soup.find('div', {'class':'reading-box'})
        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        # Some comments we will get is invalid. Remove them all.
        for comment in story.find_all(text=lambda text:isinstance(text, Comment)):
            comment.extract()

        extract_tags = ('a', 'ins', 'script')
        for tagname in extract_tags:
            for tag in story.find_all(tagname):
                tag.extract()

        # Some tags have non-standard tag name.
        for tag in story.findAll(recursive=True):
            if tag.name not in HTML_TAGS:
                tag.name = 'span'

        return self.utf8FromSoup(url, story)
