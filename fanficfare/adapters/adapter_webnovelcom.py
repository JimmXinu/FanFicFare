#  -*- coding: utf-8 -*-

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

# Adapted by GComyn on April 16, 2017
from __future__ import absolute_import
try:
    # python3
    from html import escape
except ImportError:
    # python2
    from cgi import escape
import difflib
import json
import logging
import re
import time
# py2 vs py3 transition
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML
from ..dateutils import parse_relative_date_string

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

# TinyMCE-specific annotations, let's ignore these just like previously
TINY_MCE_TAGS = 'anno', 'annotations'

logger = logging.getLogger(__name__)
pseudo_html_regex_format = r'(<+(?!/?(%s)>).*?>+)'
real_html_regex = re.compile(r'</?(?:%s)(?:\s.*?)?\s*>' % '|'.join(HTML_TAGS), re.IGNORECASE)

def getClass():
    return WWWWebNovelComAdapter


def fix_pseudo_html(pseudo_html, whitelist_tags=()):
    tags = set(HTML_TAGS).union(whitelist_tags)
    pseudo_html_regex = re.compile(pseudo_html_regex_format % '|'.join(tags), re.IGNORECASE)
    return pseudo_html_regex.sub(lambda match: escape(match.group(1)), pseudo_html)


class WWWWebNovelComAdapter(BaseSiteAdapter):
    _GET_VIP_CONTENT_DELAY = 8

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        # get storyId from url
        # https://www.webnovel.com/book/6831837102000205

        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            # normalized story URL.
            title = m.group('title') or ""
            self._setURL('https://' + self.getSiteDomain() + '/book/' + title + self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())


        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'wncom')

        self._csrf_token = None

    @staticmethod  # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.webnovel.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return 'https://' + cls.getSiteDomain() + '/book/story-title_123456789012345 https://' + cls.getSiteDomain() + '/book/123456789012345'

    def getSiteURLPattern(self):
        # https://www.webnovel.com/book/game-of-thrones%3A-the-prideful-one._17509790806343405
        return r'https://' + re.escape(self.getSiteDomain()) + r'/book/(?P<title>.*_)?(?P<id>\d+)'

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    # Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        url = self.url

        data = self.get_request(url)

        if 'We might have some troubles to find out this page.' in data:
            raise exceptions.StoryDoesNotExist('{0} says: "" for url "{1}"'.format(self.getSiteDomain(), self.url))

        soup = self.make_soup(data)
        # removing all of the scripts
        for tag in soup.findAll('script') + soup.find_all('svg'):
            tag.extract()


        # This is the block that holds the metadata
        bookdetails = soup.find('div', {'class': '_8'})

        # Title
        title = bookdetails.find('h2')
        # done as a loop incase there isn't one, or more than one.
        for tag in title.find_all('small'):
            tag.extract()
        self.story.setMetadata('title', stripHTML(title))

        detail_txt = stripHTML(bookdetails.find('p', {'class': re.compile('detail')}))
        if "Completed" in detail_txt:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        meta_tag = bookdetails.find('address').p
        meta_txt = stripHTML(meta_tag)

        def parse_meta(mt,label,setmd):
            if label in mt:
                data = mt.split(label,1)[1].split('Translator:', 1)[0].split('Editor:', 1)[0].strip()
                if data:
                    # print("setting %s to %s"%(setmd, data))
                    self.story.setMetadata(setmd, data)

        parse_meta(meta_txt,'Author:','author')
        self.story.setMetadata('authorId', self.story.getMetadata('author'))
        # There is no authorUrl for this site, so I'm setting it to the story url
        # otherwise it defaults to the file location
        self.story.setMetadata('authorUrl', url)
        parse_meta(meta_txt,'Translator:','translator')
        parse_meta(meta_txt,'Editor:','editor')

        cats = bookdetails.find_all('a',href=re.compile(r'/category/list'))
        self.story.extendList('category',[stripHTML(cat) for cat in cats])

        poptags = soup.find('div',{'class':'m-tags'})
        if poptags:
            sitetags = poptags.find_all('a',href=re.compile(r'/tag/list'))
            self.story.extendList('sitetags',[sitetag.string.replace("# ","") for sitetag in sitetags])

        ## get _csrfToken cookie for chapter list fetch
        for cookie in self.get_configuration().get_cookiejar():
            if cookie.name == '_csrfToken':
                self._csrf_token = csrf_token = cookie.value
                break
        else:
            raise exceptions.FailedToDownload('csrf token could not be found')

        ## get chapters from a json API url.
        jsondata = json.loads(self.get_request(
            "https://" + self.getSiteDomain() + "/apiajax/chapter/GetChapterList?_csrfToken=" + csrf_token + "&bookId=" + self.story.getMetadata(
                'storyId')))
        # print json.dumps(jsondata, sort_keys=True,
        #                  indent=2, separators=(',', ':'))
        for volume in jsondata["data"]["volumeItems"]:
            for chap in volume["chapterItems"]:
                # Only allow free and VIP type 1 chapters
                if chap['isAuth'] not in [1]: # Ad wall indicator
                                              # seems to have changed
                                              # --JM
                    continue
                chap_title = 'Chapter ' + unicode(chap['index']) + ' - ' + chap['name']
                chap_Url = url.rstrip('/') + '/' + chap['id']
                self.add_chapter(chap_title, chap_Url)


        if get_cover:
            cover_meta = soup.find('div', {'class': '_4'}).find('img')
            cover_url = 'https:' + cover_meta['src']
            self.setCoverImage(url, cover_url)

        detabt = soup.find('div', {'class': 'det-abt'})
        synopsis = detabt.find('p')
        self.setDescription(url, synopsis)
        rating = detabt.find('span',{'class': 'vam'})
        if rating:
            self.story.setMetadata('rating',rating.string)

        last_updated_string = jsondata['data']['bookInfo']['newChapterTime']
        last_updated = parse_relative_date_string(last_updated_string)

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
        topdata = json.loads(self.get_request(content_url))
        # logger.debug(json.dumps(topdata, sort_keys=True,
        #                         indent=2, separators=(',', ':')))
        chapter_info = topdata['data']['chapterInfo']

        # Check if chapter is marked as VIP type 1 (requires an ad to be watched)
        if chapter_info['isVip'] == 1:
            content_token_url = 'https://%s/apiajax/chapter/GetChapterContentToken?_csrfToken=%s&bookId=%s&chapterId=%s' % (
                self.getSiteDomain(), self._csrf_token, self.story.getMetadata('storyId'), chapter_id)
            content_token = json.loads(self.get_request(content_token_url))['data']['token']

            content_by_token_url = 'https://%s/apiajax/chapter/GetChapterContentByToken?_csrfToken=%s&token=%s' % (
                self.getSiteDomain(), self._csrf_token, content_token)

            # This is actually required or the data/content field will be empty
            time.sleep(self._GET_VIP_CONTENT_DELAY)
            contents = json.loads(self.get_request(content_by_token_url))['data']['contents']
        else:
            contents = chapter_info['contents']

        # Content is HTML, so return it directly
        if chapter_info['isRichFormat']:
            content = "\n".join([ x['content'] for x in contents])
            if self.getConfig('fix_pseudo_html', False):
                # Attempt to fix pseudo HTML
                fixed_content = fix_pseudo_html(content, TINY_MCE_TAGS)
                if content != fixed_content:
                    diff = difflib.unified_diff(
                        real_html_regex.split(content),
                        real_html_regex.split(fixed_content),
                        n=0, lineterm='')
                    logger.info('fix_pseudo_html() modified content:\n%s', '\n'.join(diff))
                content = fixed_content
        else: # text format.
            content = "".join([ x['content'] for x in contents])
            # Content is raw text, so convert paired newlines into paragraphs like the website
            content = content.replace('\r', '')
            content = escape(content)
            content = re.sub(r'\n(.+?)\n', r'<p>\1</p>', content)
        content = re.sub(r'(<|&lt;)pirate(>|&gt;).+?(<|&lt;)/pirate(>|&gt;)', r'', content)
        return content
