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
import io
import logging
import re
import zipfile

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
        self.story.setMetadata('language','Français')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        fandom_name = match.group('fandom')

        self._setURL('https://%s/fanfictions/%s/%s/chapters.html' % (self.getSiteDomain(), fandom_name, story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.fanfictions.fr'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/fanfictions/fandom/fanfiction-id/chapters.html' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(?:www\.)?fanfictions\.fr/fanfictions/(?P<fandom>[^/]+)/(?P<id>[^/]+)(/chapters.html)?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)
        soup = self.make_soup(data)

        # detect if the fanfiction is 'suspended' (chapters unavailable)
        alert_div = soup.find('div', id='alertInactiveFic')
        if alert_div:
            raise exceptions.FailedToDownload("Failed to download the fanfiction, most likely because it is suspended.")

        title_element = soup.find('h1', itemprop='name')
        self.story.setMetadata('title', stripHTML(title_element))

        author_div = soup.find('div', itemprop='author')
        author_name = stripHTML(author_div.a)
        author_id = author_div.a['href'].split('/')[-1].replace('.html', '')

        self.story.setMetadata('author', author_name)
        self.story.setMetadata('authorId', author_id)

        published_date_element = soup.find('span', class_='date-distance')
        published_date_text = published_date_element['data-date']
        published_date = makeDate(published_date_text, '%Y-%m-%d %H:%M:%S')
        if published_date:
            self.story.setMetadata('datePublished', published_date)

        status_element = soup.find('p', title="Statut de la fanfiction").find('span', class_='badge')
        french_status = stripHTML(status_element)
        status_translation = {
            "En cours": "In-Progress",
            "Terminée": "Completed",
            "One-shot": "Completed",
        }
        self.story.setMetadata('status', status_translation.get(french_status, french_status))

        genre_elements = soup.find('div', title="Format et genres").find_all('span', class_="highlightable")
        self.story.extendList('genre', [ stripHTML(genre) for genre in genre_elements[1:] ])

        category_elements = soup.find_all('li', class_="breadcrumb-item")
        self.story.extendList('category', [ stripHTML(category) for category in category_elements[-2].find_all('a') ])

        first_description = soup.find('p', itemprop='abstract')
        self.setDescription(self.url, first_description)

        chapter_cards = soup.find_all(class_=['card', 'chapter'])

        for chapter_card in chapter_cards:
            chapter_title_tag = chapter_card.find('h2')
            if chapter_title_tag:
                chapter_title = stripHTML(chapter_title_tag)
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

        response, redirection_url = self.get_request_redirected(url)

        if "telecharger_pdf.html" in redirection_url:
            with zipfile.ZipFile(io.BytesIO(response.encode('latin1'))) as z:
                # Assuming there's only one text file inside the zip
                file_list = z.namelist()
                if len(file_list) != 1:
                    raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Zip file should contain exactly one text file!" % url)
                text_filename = file_list[0]
                with z.open(text_filename) as text_file:
                    # Decode the text file with windows-1252 encoding
                    text = text_file.read().decode('windows-1252')
                    return text.replace("\r\n", "<br>\r\n")
        else:
            soup = self.make_soup(response)

            div_content = soup.find('div', id='readarea')
            if div_content is None:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

            return self.utf8FromSoup(url, div_content)
