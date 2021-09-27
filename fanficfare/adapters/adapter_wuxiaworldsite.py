# -*- coding: utf-8 -*-
# Copyright 2016 Fanficdownloader team
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

# Adapted by GComyn on December 14. 2016

from __future__ import absolute_import
import json
import logging
import re
# py2 vs py3 transition
from ..six.moves.urllib import parse as urlparse
from ..dateutils import parse_relative_date_string

from .base_adapter import BaseSiteAdapter, makeDate
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return WuxiaWorldSiteSiteAdapter


class WuxiaWorldSiteSiteAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'wuxsite')
        self._dateformat = '%Y-%m-%d'

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/novel/%s' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'wuxiaworld.site'

    @classmethod
    def getAcceptDomains(cls):
        return ['wuxiaworld.site',
                'wuxiaworldsite.com',
                ]

    @classmethod
    def getSiteExampleURLs(cls):
        return ' '.join([ 'https://%s/novel/story-name' % x for x in cls.getAcceptDomains() ])

    def getSiteURLPattern(self):
        return (r'https?://(%s)/novel/(?P<id>[^/]+)(/)?' %
                '|'.join([re.escape(x) for x in self.getAcceptDomains()]))

    def _parse_linked_data(self, soup):
        # See https://json-ld.org
        tag = soup.find('script', type='application/ld+json')
        if not tag:
            return {}
        return json.loads(tag.string)

    def _parse_date(self, text):
        # Strip time from date--site doesn't seem to have it anymore.
        text = re.sub(r'T.*$', '', text)
        return makeDate(text, self._dateformat)

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url)

        soup = self.make_soup(data)

        self.story.setMetadata('title', soup.find('meta', {'property': 'og:title'})['content'].split(' - ')[0])

        author = soup.select_one('.author-content > a')
        if author:
            author_name = author.get_text()
            self.story.setMetadata('authorUrl', author['href'])
        else:
            ## when no author link found, use whatever is there, usually 'Updating'
            author_name = stripHTML(soup.select_one('.author-content'))
            self.story.setMetadata('authorUrl','https://' + self.getSiteDomain() + '/')
        self.story.setMetadata('author', author_name)
        self.story.setMetadata('authorId', author_name.lower())


        ld = self._parse_linked_data(soup)
        webpage_graph = [g for g in ld['@graph'] if g['@type'] == 'WebPage']
        date_updated_webpage = None
        if len(webpage_graph) > 0:
            webpage = webpage_graph[0]

            str_date_published = webpage['datePublished']
            date_published = self._parse_date(str_date_published)
            self.story.setMetadata('datePublished', date_published)

            str_date_updated_webpage = webpage['dateModified']
            date_updated_webpage = self._parse_date(str_date_updated_webpage)

        manga_id = soup.find('input',class_='rating-post-id')['value']
        ## Chapter list moved to page Sept 2021
        # params = {'action':'manga_get_chapters',
        #           'manga':manga_id}
        # post_url = 'https://%s/wp-admin/admin-ajax.php' % self.getSiteDomain()
        # chapters_data = self.post_request(post_url, params)
        # chapters_soup = self.make_soup(chapters_data)
        # logger.debug(chapters_data)

        str_date_updated_last_chapter = soup.select_one('.chapter-release-date').i.get_text()
        if str_date_updated_last_chapter[-4:] == ' ago':
            date_updated_last_chapter = parse_relative_date_string(str_date_updated_last_chapter[:-4])
        else:
            date_updated_last_chapter = makeDate(str_date_updated_last_chapter, '%B %d, %Y')

        date_updated = date_updated_last_chapter if date_updated_webpage is None else max(date_updated_webpage, date_updated_last_chapter)
        self.story.setMetadata('dateUpdated', date_updated)

        tags = [stripHTML(a) for a in soup.select('.post-status .summary-content')]
        for tag in tags:
            if 'Completed' == tag:
                self.story.setMetadata('status', 'Completed')
            elif 'OnGoing' == tag:
                self.story.setMetadata('status', 'In-Progress')

        self.setCoverImage(self.url, soup.find('meta', {'property': "og:image"})['content'])

        description = ' '.join([stripHTML(a) for a in soup.select('.summary__content p')])
        self.setDescription(self.url, description)

        chapter_list = soup.select('.wp-manga-chapter > a')
        chapter_list.reverse()
        for a in chapter_list:
            title = stripHTML(a)
            url = urlparse.urljoin(self.url, a['href'])
            self.add_chapter(title, url)

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s', url)
        data = self.get_request(url)
        soup = self.make_soup(data)
        content = soup.select_one('.reading-content')

        return self.utf8FromSoup(url, content)
