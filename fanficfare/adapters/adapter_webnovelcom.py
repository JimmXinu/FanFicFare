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

logger = logging.getLogger(__name__)

def getClass():
    return WWWWebNovelComAdapter

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
        return r'https://' + re.escape(self.getSiteDomain()) + r'/book/(?P<title>.*?_)?(?P<id>\d+)'

    # Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        url = self.story.getMetadata('storyUrl') #self.url
        logger.debug(url)

        data = self.get_request(url)
        # logger.debug("\n"+data)

        if 'We might have some troubles to find out this page.' in data:
            raise exceptions.StoryDoesNotExist('{0} says: "" for url "{1}"'.format(self.getSiteDomain(), self.url))

        soup = self.make_soup(data)
        # removing all of the scripts
        for tag in soup.findAll('script') + soup.find_all('svg'):
            tag.extract()


        # This is the block that holds the metadata
        bookdetails = soup.find('div', {'class': '_8'})

        # Title
        title = bookdetails.find('h1')
        # done as a loop incase there isn't one, or more than one.
        for tag in title.find_all('small'):
            tag.extract()
        self.story.setMetadata('title', stripHTML(title))

        detail_txt = stripHTML(bookdetails.find('h2', {'class': 'det-hd-detail'}))
        if "Completed" in detail_txt:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        meta_tag = soup.find('address')
        meta_txt = stripHTML(meta_tag)

        def parse_meta(mt,label,setmd):
            if label in mt:
                data = mt.split(label,1)[1].split('Translator:', 1)[0].split('Editor:', 1)[0].strip()
                if data:
                    # print("setting %s to %s"%(setmd, data))
                    self.story.setMetadata(setmd, data)

        # Author details. Name, id, url...
        autdet = bookdetails.find('a', {'class': re.compile('c_primary')})
        if autdet:
            self.story.setMetadata('author',stripHTML(autdet))
            self.story.setMetadata('authorId',re.search(r"/([0-9]+)", autdet.get("href")).group(1))
            self.story.setMetadata('authorUrl', "https://www.webnovel.com" + autdet.get("href"))
        else:
            parse_meta(meta_txt,'Author:','author')
            self.story.setMetadata('authorId', self.story.getMetadata('author'))
            # There is no authorUrl for this story, so I'm setting it to the story url
            # otherwise it defaults to the file location
            self.story.setMetadata('authorUrl', url)
        parse_meta(meta_txt,'Translator:','translator')
        parse_meta(meta_txt,'Editor:','editor')

        cattags = soup.find('div',{'class':'_mn'})
        if cattags:
            cats = cattags.find_all('a',href=re.compile(r'/category/'))
            self.story.extendList('category',[stripHTML(cat) for cat in cats])

        poptags = soup.find('div',{'class':'m-tags'})
        if poptags:
            sitetags = poptags.find_all('a',href=re.compile(r'/tags/'))
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
                "https://" + self.getSiteDomain() + "/go/pcm/chapter/get-chapter-list?_csrfToken=" + csrf_token + "&bookId=" + self.story.getMetadata(
                    'storyId') + "&pageIndex=0"))

        # logger.debug(json.dumps(jsondata, sort_keys=True,
        #                         indent=2, separators=(',', ':')))
        for volume in jsondata["data"]["volumeItems"]:
            for chap in volume["chapterItems"]:
                # Only allow free and VIP type 1 chapters
                if chap['isAuth'] not in [1]: # Ad wall indicator
                                              # seems to have changed
                                              # --JM
                    continue
                chap_title = 'Chapter ' + unicode(self.num_chapters()+1) + ' - ' + chap['chapterName']
                chap_Url = url.rstrip('/') + '/' + chap['chapterId']
                self.add_chapter(chap_title, chap_Url,
                                 {'volumeName':volume['volumeName'],
                                  'volumeId':volume['volumeId'],
                                  ## dates are months or years ago for
                                  ## so many chapters I judge this
                                  ## worthless.
                                  # 'publishTimeFormat':chap['publishTimeFormat'],
                                  # 'date':parse_relative_date_string(chap['publishTimeFormat']).strftime(self.getConfig("datethreadmark_format",
                                  #                                                                                      self.getConfig("dateCreated_format","%Y-%m-%d %H:%M:%S"))),
                                  })


        if get_cover:
            cover_elements = soup.find('div', {'class': '_4'}).find_all('img')
            image_sources = [ x['src'] for x in cover_elements ]
            largest_image_size = max([ re.search(r'\/([\d]{3})\/([\d]{3})\.([a-z]{3})', x).group(1) for x in image_sources ])
            for source in image_sources:
                if re.search(r'\/{0}\/{0}\.'.format(largest_image_size), source):
                    cover_url = 'https:' + source
            self.setCoverImage(url, cover_url)

        detabt = soup.find('div', {'class': 'det-abt'})
        synopsis = detabt.find('p')
        self.setDescription(url, synopsis)
        rating = detabt.find('span',{'class': 'vam'})
        if rating:
            self.story.setMetadata('rating',rating.string)

        last_updated_string = jsondata['data']['lastChapterItem']['publishTimeFormat']
        last_updated = parse_relative_date_string(last_updated_string)

        # Published date is always unknown, so simply don't set it
        # self.story.setMetadata('datePublished', UNIX_EPOCHE)
        self.story.setMetadata('dateUpdated', last_updated)

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_request(url)
        # soup = self.make_soup(data)

        save_chapter_soup = self.make_soup('<div class="story"></div>')
        save_chapter=save_chapter_soup.find('div')

        def append_tag(elem,tag,string=None,classes=None):
            '''bs4 requires tags be added separately.'''
            new_tag = save_chapter_soup.new_tag(tag)
            if string:
                new_tag.string=string
            if classes:
                new_tag['class']=[classes]
            elem.append(new_tag)
            return new_tag

        # Chapter text is now apparently json encoded in a <script> tag.
        # This seems to find it.
        start_marker="var chapInfo= "
        end_marker=";g_data.chapInfo=chapInfo"
        data = data[data.index(start_marker)+len(start_marker):]
        data = data[:data.index(end_marker)]

        # unescape a bunch of stuff that json lib chokes on.
        data = re.sub(r"\\([ /<>'&])",r"\1",data)
        # logger.debug("\n"+data)

        ch_json = json.loads(data)
        # logger.debug(json.dumps(ch_json, sort_keys=True,
        #                         indent=2, separators=(',', ':')))

        for paragraph in ch_json["chapterInfo"]["contents"]:
            p = paragraph["content"]
            # logger.debug(p)
            ## sometimes wrapped in <p>, sometimes not. Treat as html
            ## if starts with <p>
            if p.startswith('<p>'):
                p = self.make_soup(p)
                ## make_soup--html5lib/bs really--adds a full html tag
                ## set like:
                # "<html><head></head><body> ...  </body></html>"
                ## but utf8FromSoup will remove them all.  Noted here
                ## because it looks odd in debug.
                # logger.debug(p)
                save_chapter.append(p)
            else:
                append_tag(save_chapter,'p',p)

        # logger.debug(save_chapter)
        return self.utf8FromSoup(url,save_chapter)
