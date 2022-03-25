#  -*- coding: utf-8 -*-

# Copyright 2020 FanFicFare team
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
import re
# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldCoSiteAdapter


class WuxiaWorldCoSiteAdapter(BaseSiteAdapter):
    DATE_FORMAT = '%Y-%m-%d %H:%M'

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
        return 'm.wuxiaworld.co'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.wuxiaworld.co','m.wuxiaworld.co']

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/story-name' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(www|m)\.wuxiaworld\.co/(?P<id>[^/]+)(/)?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)

        soup = self.make_soup(data)

        self.setCoverImage(self.url, soup.select_one('.book-img > img')['src'])

        book_info = soup.select_one('.book-info')
        author = book_info.select_one('.author > .name').get_text()
        self.story.setMetadata('title', book_info.select_one('.book-name').get_text())
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        ## site doesn't have authorUrl links.

        ## getting status
        status = stripHTML(soup.select_one('div.book-state > span.txt'))
        if status == 'Completed':
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        chapter_info = soup.select_one('.chapter-wrapper')
        date = makeDate(chapter_info.select_one('.update-time').get_text(), self.DATE_FORMAT)
        if date:
            self.story.setMetadata('dateUpdated', date)

        intro = soup.select_one('.synopsis > .content')
        if intro.strong:
            intro.strong.decompose()
        self.setDescription(self.url, intro)

        ## skip grayed out "In preparation" chapters -- couldn't make
        ## the :not() work in the same select.
        chapters = [ ch for ch in chapter_info.select('.chapter-item')
                     if not (ch.has_attr('style') and 'color:Gray;' not in ch('style')) ]
        if self.getConfig("dedup_order_chapter_list",False):
            # Sort and deduplicate chapters (some stories in incorrect order and/or duplicates)
            chapters_data = []
            numbers_regex = re.compile(r'[^0-9\.]') # Everything except decimal and numbers
            for ch in chapters:
                chapter_title = ch.p.get_text()
                chapter_url = ch['href']
                if chapter_title.startswith('Chapter'):
                    target_number = chapter_title.split()[1]
                else:
                    target_number = chapter_title.split()[0]
                try:
                    number = float(re.sub(numbers_regex, '', target_number))
                except:
                    continue # Cannot parse chapter number
                chapters_data.append((number, chapter_title, chapter_url))

            chapters_data.sort(key=lambda ch: ch[0])

            for index, chapter in enumerate(chapters_data):
                if index > 0:
                    # No previous duplicate chapter names or same chapter numbers
                    if chapter[1] == chapters_data[index-1][1] or chapter[0] == chapters_data[index-1][0]:
                        continue
                title = chapter[1]
                url = urlparse.urljoin(self.url, chapter[2])
                self.add_chapter(title, url)
        else:
            ## normal operation
            for ch in chapters:
                self.add_chapter(ch.p.get_text(), urlparse.urljoin(self.url, ch['href']))

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.select_one('.chapter-entity')

        return self.utf8FromSoup(url, content)
