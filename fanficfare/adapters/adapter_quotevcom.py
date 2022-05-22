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

from __future__ import absolute_import
import re
import datetime
import logging
logger = logging.getLogger(__name__)

from .. import exceptions
# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib import parse as urlparse

from .base_adapter import BaseSiteAdapter
from ..htmlcleanup import stripHTML

SITE_DOMAIN = 'quotev.com'
STORY_URL_TEMPLATE = 'https://www.quotev.com/story/%s'


def getClass():
    return QuotevComAdapter

class QuotevComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        story_id = url.split('/')[4]
        self._setURL(STORY_URL_TEMPLATE % story_id)
        self.story.setMetadata('storyId', story_id)
        self.story.setMetadata('siteabbrev', SITE_DOMAIN)

    @staticmethod
    def getSiteDomain():
        return SITE_DOMAIN

    @classmethod
    def getSiteExampleURLs(cls):
        return STORY_URL_TEMPLATE % '1234'

    def getSiteURLPattern(self):
        pattern = re.escape(STORY_URL_TEMPLATE.rsplit('%', 1)[0]) + r'(.+?)($|&|/)'
        pattern = pattern.replace(r'https', r'https?')
        pattern = pattern.replace(r'www\.', r'(www\.)?')
        return pattern

    def extractChapterUrlsAndMetadata(self):
        data = self.get_request(self.url)

        soup = self.make_soup(data)

        element = soup.find('div', {'class': 'result'})
        if not element:
            raise exceptions.StoryDoesNotExist(self.url)

        title = element.find('h1')
        self.story.setMetadata('title', title.get_text())

        authdiv = soup.find('div', {'class':"quizAuthorList"})
        if authdiv:
            for a in authdiv.find_all('a'):
                self.story.addToList('author', a.get_text())
                self.story.addToList('authorId', a['href'].split('/')[-1])
                self.story.addToList('authorUrl', urlparse.urljoin(self.url, a['href']))
        if not self.story.getList('author'):
            self.story.addToList('author','Anonymous')
            self.story.addToList('authorUrl','https://www.quotev.com')
            self.story.addToList('authorId','0')

        self.setDescription(self.url, soup.find('div', id='qdesct'))
        imgmeta = soup.find('meta',{'property':"og:image" })
        if imgmeta:
            self.coverurl = self.setCoverImage(self.url, urlparse.urljoin(self.url, imgmeta['content']))[1]

        for a in soup.find_all('a', {'href': re.compile('/fiction(/c)?/')}):
            self.story.addToList('category', a.get_text())

        for a in soup.select('div#quizHeader div.quizBoxTags a'):
            self.story.addToList('searchtags', a.get_text())

        elements = soup.find_all('time') # , {'class': 'q_time'}
        self.story.setMetadata('datePublished', datetime.datetime.fromtimestamp(float(elements[0]['ts'])))
        if len(elements) > 1:
            self.story.setMetadata('dateUpdated', datetime.datetime.fromtimestamp(float(elements[1]['ts'])))

        metadiv = elements[0].parent.parent
        if u'· completed' in stripHTML(metadiv):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # pages,readers,reads
        metahtml = unicode(metadiv).replace(u'\n',' ')
        # logger.debug(metahtml)
        for entry in self.getConfigList('extra_valid_entries'):
            # if entry in metahtml:
            #     logger.debug("should find")
            # logger.debug(r".*?([0-9,]+) +%s.*?"%entry)
            m = re.match((r".*?([0-9,]+) +%s.*?"%entry),metahtml)
            if m:
                val = m.group(1)
                # logger.debug(val)
                self.story.setMetadata(entry, val.replace(',', '').replace('.', ''))

        favspans = soup.find('a',{'id':'fav_btn'}).find_all('span')
        if len(favspans) > 1:
            self.story.setMetadata('favorites', stripHTML(favspans[-1]).replace(',', ''))

        commentspans = soup.find('a',{'id':'comment_btn'}).find_all('span')
        #print("commentspans:%s"%commentspans)
        if len(commentspans) > 0:
            self.story.setMetadata('comments', stripHTML(commentspans[0]).replace(',', ''))

        for a in soup.find('div', id='rselect')('a'):
            if 'javascript' not in a['href']:
                self.add_chapter(a.get_text(), urlparse.urljoin(self.url, a['href']))


    def getChapterText(self, url):
        data = self.get_request(url)
        # logger.debug(data)
        soup = self.make_soup(data)

        rescontent = soup.find('div', id='rescontent')

        # attempt to find and include chapter specific images.
        img = soup.find('div',{'id':'quizHeader'}).find('img')
        # don't include if same as cover or if hr.png placeholder
        if img['src'] != self.coverurl and not img['src'].endswith('/hr.png'):
            rescontent.insert(0,img)

        # find and include JS hidden image.
        resultImage = soup.find('img',id='resultImage')
        if resultImage:
            onclick = resultImage['onclick']
            imgstr = onclick[onclick.index('<img'):onclick.index('>')+1].replace('\\','')
            # logger.debug(imgstr)
            imgsoup = self.make_soup(imgstr)
            # logger.debug(imgsoup)
            rescontent.insert(0,imgsoup.find('img').extract())

        for a in rescontent('a'):
            a.unwrap()

        return self.utf8FromSoup(url, rescontent)
