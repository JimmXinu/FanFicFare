# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2019 FanFicFare team
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
import string

# py2 vs py3 transition
from ..six import text_type as unicode

import bs4

from .base_writer import *
class HTMLWriter(BaseStoryWriter):

    @staticmethod
    def getFormatName():
        return 'html'

    @staticmethod
    def getFormatExt():
        return '.html'

    def __init__(self, config, story):
        BaseStoryWriter.__init__(self, config, story)

        self.HTML_FILE_START = string.Template('''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>${title} by ${author}</title>
<style type="text/css">
${output_css}
</style>
</head>
<body>
<h1><a href="${storyUrl}">${title}</a> by ${authorHTML}</h1>
''')

        self.HTML_COVER = string.Template('''
<img src="${coverimg}" alt="cover" />
''')

        self.HTML_TITLE_PAGE_START = string.Template('''
<table class="full">
''')

        self.HTML_TITLE_ENTRY = string.Template('''
<tr><td><b>${label}:</b></td><td>${value}</td></tr>
''')

        self.HTML_TITLE_PAGE_END = string.Template('''
</table>
''')

        self.HTML_TOC_PAGE_START = string.Template('''
<a name="TOCTOP"><h2>Table of Contents</h2></a>
<p>
''')

        self.HTML_TOC_ENTRY = string.Template('''
<a href="#section${index04}">${chapter}</a><br />
''')

        self.HTML_TOC_PAGE_END = string.Template('''
</p>
''')

        self.HTML_CHAPTER_START = string.Template('''
<a name="section${index04}"><h2>${chapter}</h2></a>
''')

        self.HTML_CHAPTER_END = string.Template('')

        self.HTML_FILE_END = string.Template('''
</body>
</html>''')


    def writeStoryImpl(self, out):
        if self.hasConfig("cover_content"):
            COVER = string.Template(self.getConfig("cover_content"))
        else:
            COVER = self.HTML_COVER

        if self.hasConfig('file_start'):
            FILE_START = string.Template(self.getConfig("file_start"))
        else:
            FILE_START = self.HTML_FILE_START

        if self.hasConfig('file_end'):
            FILE_END = string.Template(self.getConfig("file_end"))
        else:
            FILE_END = self.HTML_FILE_END

        self._write(out,FILE_START.substitute(self.story.getAllMetadata()))

        if self.getConfig('include_images') and self.story.cover:
            self._write(out,COVER.substitute(dict(list(self.story.getAllMetadata().items())+list({'coverimg':self.story.cover}.items()))))

        self.writeTitlePage(out,
                            self.HTML_TITLE_PAGE_START,
                            self.HTML_TITLE_ENTRY,
                            self.HTML_TITLE_PAGE_END)

        self.writeTOCPage(out,
                          self.HTML_TOC_PAGE_START,
                          self.HTML_TOC_ENTRY,
                          self.HTML_TOC_PAGE_END)

        if self.hasConfig('chapter_start'):
            CHAPTER_START = string.Template(self.getConfig("chapter_start"))
        else:
            CHAPTER_START = self.HTML_CHAPTER_START

        if self.hasConfig('chapter_end'):
            CHAPTER_END = string.Template(self.getConfig("chapter_end"))
        else:
            CHAPTER_END = self.HTML_CHAPTER_END

        ## collect chapter urls and file names for internalize_text_links option.
        chapurlmap = {}
        for index, chap in enumerate(self.story.getChapters()):
            if chap['html']:
                ## HTML_CHAPTER_START needs to have matching <a>
                ## anchor to work.  Which it does by default.  This
                ## could also be made configurable if some user
                ## changed it.
                chapurlmap[chap['url']]="#section%s"%chap['index04'] # url -> index

        for index, chap in enumerate(self.story.getChapters()):
            if chap['html']:
                chap_data = chap['html']
                if self.getConfig('internalize_text_links'):
                    # html doesn't need data-orighref because it
                    # doesn't do updates.
                    soup = bs4.BeautifulSoup(chap['html'],'html5lib')
                    changed=False
                    for alink in soup.find_all('a'):
                        if alink.has_attr('href') and alink['href'] in chapurlmap:
                            alink['href']=chapurlmap[alink['href']]
                            changed=True
                    if changed:
                        chap_data = unicode(soup)
                        # Don't want html, head or body tags in
                        # chapter html--bs4 insists on adding them.
                        chap_data = re.sub(r"</?(html|head|body)[^>]*>\r?\n?","",chap_data)


                logging.debug('Writing chapter text for: %s' % chap['title'])
                self._write(out,CHAPTER_START.substitute(chap))
                self._write(out,chap_data)
                self._write(out,CHAPTER_END.substitute(chap))

        self._write(out,FILE_END.substitute(self.story.getAllMetadata()))

        if self.getConfig('include_images'):
            for imgmap in self.story.getImgUrls():
                self.writeFile(imgmap['newsrc'],imgmap['data'])

