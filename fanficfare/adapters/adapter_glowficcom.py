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

from .base_adapter import BaseSiteAdapter, makeDate
from fanficfare.htmlcleanup import stripHTML
from .. import exceptions as exceptions

logger = logging.getLogger(__name__)


def getClass():
    return GlowficComSiteAdapter


class GlowficComSiteAdapter(BaseSiteAdapter):
    NEW_DATE_FORMAT = '%Y/%m/%d %H:%M:%S'
    OLD_DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev', 'glowfic')

        # get storyId from url--url validation guarantees query correct
        match = re.match(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())

        story_id = match.group('id')
        self.story.setMetadata('storyId', story_id)
        self._setURL('https://%s/posts/%s' % (self.getSiteDomain(), story_id))

    @staticmethod
    def getSiteDomain():
        return 'www.glowfic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://%s/posts/id' % cls.getSiteDomain()

    def getSiteURLPattern(self):
        return r'https?://(?:www\.)?glowfic\.com/posts/(?P<id>\d+)(?:/)?'

    def extractChapterUrlsAndMetadata(self):
        logger.debug('URL: %s', self.url)

        data = self.get_request(self.url + "/stats")

        soup = self.make_soup(data)
        info = soup.select_one('.table-title')
        self.story.setMetadata('title', stripHTML(info.a))

        # self.setCoverImage(self.url, soup.select_one('.inform-product > img')['src'])

        # Unicode strings because '：' isn't ':', but \xef\xbc\x9a
        # author = stripHTML(info.h6).split(u' ')[0].replace(u'Auteur : ', '', 1)

        # author = stripHTML(info.h6).split('Babelcheck')[0].replace('Auteur : ', '').replace('\xc2\xa0', '')
        authors = soup.find('th', string="Authors").parent.td
        author = ','.join([stripHTML(x) for x in authors.find_all('a')])
        # # author = stripHTML(info.h6).split('\xa0')[0].replace(u'Auteur : ', '', 1)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        # ## site doesn't have authorUrl links.

        # last_updated = soup.find('th', string="Time Last Updated").parent.td
        # datestr = stripHTML(last_updated)
        # date = makeDate(datestr, '%Y/%m/%d')
        # if date:
        #     self.story.setMetadata('dateUpdated', date)

        # intro = stripHTML(info.select_one('.inform-inform-txt').span)
        # self.setDescription(self.url, intro)

        # for content in soup.findAll('div', {'id': 'content'}):
        #     for a in content.findAll('a'):
        self.add_chapter("Story", self.url + '?view=flat')


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        soup = self.make_soup(data)

        content = soup.new_tag('div')
        posts = soup.select('.post-content')
        for post in posts:
            info = post.parent.select_one('.post-info-box')
            author = stripHTML(info.select_one('.post-author'))
            character = info.select_one('.post-character')

            heading = soup.new_tag('h3')
            if character is not None:
                character = stripHTML(character)
                heading.string = "%s (%s)" % (character, author)
            else:
                heading.string = author

            content.append(heading)
            content.append(post)

        return self.utf8FromSoup(url,content)
