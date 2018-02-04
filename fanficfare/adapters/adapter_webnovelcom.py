#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2017 FanFicFare team
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

# Adapted by GComyn on April 16, 2017
import cgi
import json
import logging
import re
import time
import urllib2
from datetime import datetime, timedelta

from base_adapter import BaseSiteAdapter
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

UNIX_EPOCHE = datetime.fromtimestamp(0)
logger = logging.getLogger(__name__)


def getClass():
    return WWWWebNovelComAdapter


def _parse_relative_date_string(string_):
    # Keep this explicit instead of replacing parentheses in case we discover a format that is not so easily
    # translated as a keyword-argument to timedelta. In practice I have only observed hours, weeks and days
    unit_to_keyword = {
        'second(s)': 'seconds',
        'minute(s)': 'minutes',
        'hour(s)': 'hours',
        'day(s)': 'days',
        'week(s)': 'weeks',
        'seconds': 'seconds',
        'minutes': 'minutes',
        'hours': 'hours',
        'days': 'days',
        'weeks': 'weeks',
        'second': 'seconds',
        'minute': 'minutes',
        'hour': 'hours',
        'day': 'days',
        'week': 'weeks',
    }

    value, unit_string, rest = string_.split()
    unit = unit_to_keyword.get(unit_string)
    if not unit:
        # This is "just as wrong" as always returning the current date, but prevents unneeded updates each time
        logger.warn('Failed to parse relative date string: %r, falling back to unix epoche', string_)
        return UNIX_EPOCHE

    kwargs = {unit: int(value)}

    # "naive" dates without hours and seconds are created in writers.base_writer.writeStory(), so we don't have to strip
    # hours and minutes from the base date. Using datetime objects would result in a slightly different time (since we
    # calculate the last updated date based on the current time) during each update, since the seconds and hours change.
    today = datetime.utcnow()
    time_ago = timedelta(**kwargs)
    return today - time_ago


class WWWWebNovelComAdapter(BaseSiteAdapter):
    _GET_VIP_CONTENT_DELAY = 8

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        # get storyId from url
        # https://www.webnovel.com/book/6831837102000205
        self.story.setMetadata('storyId', self.parsedUrl.path.split('/')[2])

        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/book/' + self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'wncom')

        self._csrf_token = None

    @staticmethod  # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.webnovel.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://' + cls.getSiteDomain() + '/book/123456789012345'

    def getSiteURLPattern(self):
        return r'https://' + re.escape(self.getSiteDomain()) + r'/book/*(?P<id>\d+)'

    # Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        url = self.url

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        if 'We might have some troubles to find out this page.' in data:
            raise exceptions.StoryDoesNotExist('{0} says: "" for url "{1}"'.format(self.getSiteDomain(), self.url))

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # removing all of the scripts
        for tag in soup.findAll('script') + soup.find_all('svg'):
            tag.extract()

        # Now go hunting for all the meta data and the chapter list.

        # This is the block that holds the metadata
        bookdetails = soup.find('div', {'class': 'g_col_8'})

        # Title
        title = bookdetails.find('h2', {'class': 'lh1d2'})
        # done as a loop incase there isn't one, or more than one.
        for tag in title.find_all('small'):
            tag.extract()
        self.story.setMetadata('title', stripHTML(title))

        # TODO: This should be more robust...
        # Find authorid and URL from... author url.
        paras = bookdetails.find_all('p')
        for para in paras:
            parat = stripHTML(para)
            if parat[:7] == 'Author:':
                author = parat.split('Author:', 1)[1].split(u'|', 1)[0].strip()
                self.story.setMetadata('author', author)
                self.story.setMetadata('authorId', author)
                # There is no authorUrl for this site, so I'm setting it to the story url
                # otherwise it defaults to the file location
                self.story.setMetadata('authorUrl', url)
            elif parat[:11] == 'Translator:':
                self.story.setMetadata('translator', parat.replace('Translator:', '').strip())
            elif parat[:7] == 'Editor:':
                self.story.setMetadata('editor', parat.replace('Editor:', '').strip())
            elif '_tags' in para.get('class', []):
                category = stripHTML(para.strong).strip()
                self.story.setMetadata('category', category)

        ## get _csrfToken cookie for chapter list fetch
        for cookie in self.get_configuration().get_cookiejar():
            if cookie.name == '_csrfToken':
                self._csrf_token = csrf_token = cookie.value
                break
        else:
            raise exceptions.FailedToDownload('csrf token could not be found')

        ## get chapters from a json API url.
        jsondata = json.loads(self._fetchUrl(
            "https://" + self.getSiteDomain() + "/apiajax/chapter/GetChapterList?_csrfToken=" + csrf_token + "&bookId=" + self.story.getMetadata(
                'storyId')))
        for chap in jsondata["data"]["chapterItems"]:
            # Only allow free and VIP type 1 chapters
            if chap['isVip'] not in {0, 1}:
                continue

            chap_title = 'Chapter ' + unicode(chap['chapterIndex']) + ' - ' + chap['chapterName']
            chap_Url = url.rstrip('/') + '/' + chap['chapterId']
            self.chapterUrls.append((chap_title, chap_Url))

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        if get_cover:
            cover_meta = soup.find('div', {'class': 'g_col_4'}).find('img')
            cover_url = 'https:' + cover_meta['src']
            self.setCoverImage(url, cover_url)

        synopsis = soup.find('div', {'class': 'det-abt'}).find('p')
        self.setDescription(url, synopsis)

        last_updated_string = jsondata['data']['bookInfo']['newChapterTime']
        last_updated = _parse_relative_date_string(last_updated_string)

        # Published date is always unknown, so simply don't set it
        # self.story.setMetadata('datePublished', UNIX_EPOCHE)
        self.story.setMetadata('dateUpdated', last_updated)

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        book_id = self.story.getMetadata('storyId')
        chapter_id = url.split('/')[-1]
        content_url = 'https://%s/apiajax/chapter/GetContent?_csrfToken=%s&bookId=%s&chapterId=%s&_=%d' % (
            self.getSiteDomain(), self._csrf_token, book_id, chapter_id, time.time() * 1000)
        chapter_info = json.loads(self._fetchUrl(content_url))['data']['chapterInfo']

        # Check if chapter is marked as VIP type 1 (requires an ad to be watched)
        if chapter_info['isVip'] == 1:
            content_token_url = 'https://%s/apiajax/chapter/GetChapterContentToken?_csrfToken=%s&bookId=%s&chapterId=%s' % (
                self.getSiteDomain(), self._csrf_token, self.story.getMetadata('storyId'), chapter_id)
            content_token = json.loads(self._fetchUrl(content_token_url))['data']['token']

            content_by_token_url = 'https://%s/apiajax/chapter/GetChapterContentByToken?_csrfToken=%s&token=%s' % (
                self.getSiteDomain(), self._csrf_token, content_token)

            # This is actually required or the data/content field will be empty
            time.sleep(self._GET_VIP_CONTENT_DELAY)
            content = json.loads(self._fetchUrl(content_by_token_url))['data']['content']
        else:
            content = chapter_info['content']

        # Content is HTML, so return it directly
        if chapter_info['isRichFormat']:
            return content

        # Content is raw text, so convert paired newlines into paragraphs like the website
        content = content.replace('\r', '')
        content = cgi.escape(content)
        content = re.sub(r'\n(.+?)\n', r'<p>\1</p>', content)
        return content
