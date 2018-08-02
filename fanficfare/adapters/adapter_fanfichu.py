# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2018 FanFicFare team
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
import re
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six import ensure_text
from ..six.moves.urllib import parse as urlparse
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate
from .. import exceptions


_SOURCE_CODE_ENCODING = 'utf-8'


def getClass():
    return FanficHuAdapter


def _get_query_data(url):
    components = urlparse.urlparse(url)
    query_data = urlparse.parse_qs(components.query)
    return dict((key, data[0]) for key, data in query_data.items())


class FanficHuAdapter(BaseSiteAdapter):
    SITE_ABBREVIATION = 'ffh'
    SITE_DOMAIN = 'fanfic.hu'
    SITE_LANGUAGE = 'Hungarian'

    BASE_URL = 'https://' + SITE_DOMAIN + '/merengo/'
    VIEW_STORY_URL_TEMPLATE = BASE_URL + 'viewstory.php?sid=%s'

    DATE_FORMAT = '%m/%d/%Y'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        query_data = urlparse.parse_qs(self.parsedUrl.query)
        story_id = query_data['sid'][0]

        self.story.setMetadata('storyId', story_id)
        self._setURL(self.VIEW_STORY_URL_TEMPLATE % story_id)
        self.story.setMetadata('siteabbrev', self.SITE_ABBREVIATION)
        self.story.setMetadata('language', self.SITE_LANGUAGE)

    def _customized_fetch_url(self, url, exception=None, parameters=None):
        if exception:
            try:
                data = self._fetchUrl(url, parameters)
            except HTTPError:
                raise exception(self.url)
        # Just let self._fetchUrl throw the exception, don't catch and
        # customize it.
        else:
            data = self._fetchUrl(url, parameters)

        return self.make_soup(data)

    @staticmethod
    def getSiteDomain():
        return FanficHuAdapter.SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return cls.VIEW_STORY_URL_TEMPLATE % 1234

    def getSiteURLPattern(self):
        return re.escape(self.VIEW_STORY_URL_TEMPLATE[:-2]).replace('https','https?') + r'\d+$'

    def extractChapterUrlsAndMetadata(self):
        soup = self._customized_fetch_url(self.url + '&i=1')

        if ensure_text(soup.title.string).strip(u' :') == u'írta':
            raise exceptions.StoryDoesNotExist(self.url)

        chapter_options = soup.find('form', action='viewstory.php').select('option')
        # Remove redundant "Fejezetek" option
        chapter_options.pop(0)

        # If there is still more than one entry remove chapter overview entry
        if len(chapter_options) > 1:
            chapter_options.pop(0)

        for option in chapter_options:
            url = urlparse.urljoin(self.url, option['value'])
            self.add_chapter(option.string, url)

        author_url = urlparse.urljoin(self.BASE_URL, soup.find('a', href=lambda href: href and href.startswith('viewuser.php?uid='))['href'])
        soup = self._customized_fetch_url(author_url)

        story_id = self.story.getMetadata('storyId')
        for table in soup('table', {'class': 'mainnav'}):
            title_anchor = table.find('span', {'class': 'storytitle'}).a
            href = title_anchor['href']
            if href.startswith('javascript:'):
                href = href.rsplit(' ', 1)[1].strip("'")
            query_data = _get_query_data(href)

            if query_data['sid'] == story_id:
                break
        else:
            # This should never happen, the story must be found on the author's
            # page.
            raise exceptions.FailedToDownload(self.url)

        self.story.setMetadata('title', title_anchor.string)

        rows = table('tr')

        anchors = rows[0].div('a')
        author_anchor = anchors[1]
        query_data = _get_query_data(author_anchor['href'])
        self.story.setMetadata('author', author_anchor.string)
        self.story.setMetadata('authorId', query_data['uid'])
        self.story.setMetadata('authorUrl', urlparse.urljoin(self.BASE_URL, author_anchor['href']))
        self.story.setMetadata('reviews', anchors[3].string)

        if self.getConfig('keep_summary_html'):
            self.story.setMetadata('description', self.utf8FromSoup(author_url, rows[1].td))
        else:
            self.story.setMetadata('description', ''.join(rows[1].td(text=True)))

        for row in rows[3:]:
            index = 0
            cells = row('td')

            while index < len(cells):
                cell = cells[index]
                key = ensure_text(cell.b.string).strip(u':')
                try:
                    value = ensure_text(cells[index+1].string)
                except:
                    value = None

                if key == u'Kategória':
                    for anchor in cells[index+1]('a'):
                        self.story.addToList('category', anchor.string)

                elif key == u'Szereplõk':
                    if cells[index+1].string:
                        for name in cells[index+1].string.split(', '):
                            self.story.addToList('character', name)

                elif key == u'Korhatár':
                    if value != 'nem korhatáros':
                        self.story.setMetadata('rating', value)

                elif key == u'Figyelmeztetések':
                    for b_tag in cells[index+1]('b'):
                        self.story.addToList('warnings', b_tag.string)

                elif key == u'Jellemzõk':
                    for genre in cells[index+1].string.split(', '):
                        self.story.addToList('genre', genre)

                elif key == u'Fejezetek':
                    self.story.setMetadata('numChapters', int(value))

                elif key == u'Megjelenés':
                    self.story.setMetadata('datePublished', makeDate(value, self.DATE_FORMAT))

                elif key == u'Frissítés':
                    self.story.setMetadata('dateUpdated', makeDate(value, self.DATE_FORMAT))

                elif key == u'Szavak':
                    self.story.setMetadata('numWords', value)

                elif key == u'Befejezett':
                    self.story.setMetadata('status', 'Completed' if value == 'Nem' else 'In-Progress')

                index += 2

        if self.story.getMetadata('rating') == '18':
            if not (self.is_adult or self.getConfig('is_adult')):
                raise exceptions.AdultCheckRequired(self.url)

    def getChapterText(self, url):
        soup = self._customized_fetch_url(url)
        story_cell = soup.find('form', action='viewstory.php').parent.parent

        for div in story_cell('div'):
            div.extract()

        return self.utf8FromSoup(url, story_cell)
