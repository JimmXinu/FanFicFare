#  -*- coding: utf-8 -*-

# Copyright 2019 FanFicFare team
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
import re
# py2 vs py3 transition
from ..six import text_type as unicode, ensure_text
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldCoSiteAdapter


class WuxiaWorldCoSiteAdapter(BaseSiteAdapter):
    NEW_DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
    OLD_DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wuxco')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/%s/' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.wuxiaworld.co'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.wuxiaworld.co','m.wuxiaworld.co']

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(www|m)\.wuxiaworld\.co/(?P<id>[^/]+)(/)?'

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)
        try:
            data = self._fetchUrl(self.url)
        except HTTPError as exception:
            if exception.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(self.url))
            raise exception

        soup = self.make_soup(data)
        info = soup.select_one('#info')
        self.story.setMetadata('title', stripHTML(info.h1))
        self.setCoverImage(self.url, soup.select_one('#fmimg > img')['src'])

        info_paragraphs = info('p')
        # Unicode strings because '：' isn't ':', but \xef\xbc\x9a
        author = stripHTML(info_paragraphs[0]).replace(u'Author：', '', 1)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        datestr = stripHTML(info_paragraphs[2]).replace(u'UpdateTime：', '', 1)
        date = None
        try:
            ## Some older stories use a different date format.
            date = makeDate(datestr, self.NEW_DATE_FORMAT)
        except ValueError:
            date = makeDate(datestr, self.OLD_DATE_FORMAT)
        if date:
            self.story.setMetadata('dateUpdated', date)

        intro = soup.select_one('#intro')
        # Strip <strong>Description</strong>
        if intro.strong:
            intro.strong.decompose()
        self.setDescription(self.url, intro)

        dl = soup.select_one('#list > dl')
        for el in dl.contents:
            if el.name == u'dt':
                match = re.match(ensure_text(r'^《.+》\s+(.+)$'), stripHTML(el), re.UNICODE)
                volume = ''
                if match and match.group(1) != 'Text':
                    volume = match.group(1) + ' '
            elif el.name == u'dd':
                a = el.a
                if a['style'] != 'color:Gray;':
                    # skip grayed out "In preparation" chapters
                    url = urlparse.urljoin(self.url, a['href'])
                    title = volume + stripHTML(a)
                    self.add_chapter(title, url)
            # else:
            #     logger.debug('Unexpected tag in #list > dl: %s', el.name)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self._fetchUrl(url)
        soup = self.make_soup(data)

        content = soup.select_one('#content')

        # Script empty script tag at the end of the content
        for script in content('script'):
            script.decompose()

        return self.utf8FromSoup(url, content)
