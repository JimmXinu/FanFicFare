#  -*- coding: utf-8 -*-

# Copyright 2024 FanFicFare team
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

from bs4 import BeautifulSoup
# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return FanfictionsFrSiteAdapter


class FanfictionsFrSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'fanfictionsfr')
        self.story.setMetadata('langcode','fr')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        fandom_name = match.group('fandom')

        self._setURL('https://www.%s/fanfictions/%s/%s/chapters.html' % (self.getSiteDomain(), fandom_name, story_id))

    @staticmethod
    def getSiteDomain():
        return 'fanfictions.fr'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/fanfictions/fandom/fanfiction-id/chapters.html' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(?:www\.)?fanfictions\.fr/fanfictions/(?P<fandom>[^/]+)/(?P<id>[^/]+)(/chapters.html)?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)
        soup = self.make_soup(data)

        title_element = soup.find('h1', itemprop='name')
        self.story.setMetadata('title', title_element.text.strip())

        self.setCoverImage(self.url, None)

        author_div = soup.find('div', itemprop='author')
        author_name = author_div.a.text.strip()
        author_id = author_div.a['href'].split('/')[-1].replace('.html', '')

        self.story.setMetadata('author', author_name)
        self.story.setMetadata('authorId', author_id)


        first_description = soup.find('p', itemprop='abstract')
        fic_description = first_description.text.strip()
        self.setDescription(self.url, fic_description)

        chapter_cards = soup.find_all(class_=['card', 'chapter'])

        for chapter_card in chapter_cards:
            chapter_title_tag = chapter_card.find('h2')
            if chapter_title_tag:
                chapter_title = chapter_title_tag.text.strip()
                chapter_link = 'https://'+self.getSiteDomain()+chapter_title_tag.find('a')['href']

                # Clean up the chapter title by replacing multiple spaces and newline characters with a single space
                chapter_title = re.sub(r'\s+', ' ', chapter_title)

                self.add_chapter(chapter_title, chapter_link)

        last_chapter_div = chapter_cards[-1]
        updated_date_element = last_chapter_div.find('span', class_='date-distance')
        last_chapter_update_date = updated_date_element['data-date']
        date = makeDate(last_chapter_update_date, '%Y-%m-%d %H:%M:%S')
        if date:
            self.story.setMetadata('dateUpdated', date)


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = BeautifulSoup(data, 'html.parser')

        div_content = soup.find('div', id='readarea')
        if div_content is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, div_content)
