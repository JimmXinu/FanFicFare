# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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
from io import BytesIO
import logging
import string

from .base_writer import BaseStoryWriter
from ..mobi import Converter
from ..exceptions import FailedToWriteOutput

logger = logging.getLogger(__name__)

class MobiWriter(BaseStoryWriter):

    @staticmethod
    def getFormatName():
        return 'mobi'

    @staticmethod
    def getFormatExt():
        return '.mobi'

    def __init__(self, config, story):
        BaseStoryWriter.__init__(self, config, story)

        self.MOBI_TITLE_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
</head>
<body>
<h3><a href="${storyUrl}">${title}</a> by ${authorHTML}</h3>
<div>
''')

        self.MOBI_TITLE_ENTRY = string.Template('''
<b>${label}:</b> ${value}<br />
''')

        self.MOBI_NO_TITLE_ENTRY = string.Template('''
${value}<br />
''')

        self.MOBI_TITLE_PAGE_END = string.Template('''
</div>

</body>
</html>
''')

        self.MOBI_TABLE_TITLE_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
</head>
<body>
<h3><a href="${storyUrl}">${title}</a> by ${authorHTML}</h3>
<table class="full">
''')

        self.MOBI_TABLE_TITLE_ENTRY = string.Template('''
<tr><td><b>${label}:</b></td><td>${value}</td></tr>
''')

        self.MOBI_TABLE_TITLE_WIDE_ENTRY = string.Template('''
<tr><td colspan="2"><b>${label}:</b> ${value}</td></tr>
''')

        self.MOBI_TABLE_NO_TITLE_WIDE_ENTRY = string.Template('''
<tr><td colspan="2">${value}</td></tr>
''')

        self.MOBI_TABLE_TITLE_PAGE_END = string.Template('''
</table>

</body>
</html>
''')

        self.MOBI_CHAPTER_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${chapter}</title>
</head>
<body>
<h3>${chapter}</h3>
''')

        self.MOBI_CHAPTER_END = string.Template('''
</body>
</html>
''')

    def writeStoryImpl(self, out):

        files = []

        # write title page.
        if self.getConfig("titlepage_use_table"):
            TITLE_PAGE_START  = self.MOBI_TABLE_TITLE_PAGE_START
            TITLE_ENTRY       = self.MOBI_TABLE_TITLE_ENTRY
            WIDE_TITLE_ENTRY  = self.MOBI_TABLE_TITLE_WIDE_ENTRY
            NO_TITLE_ENTRY    = self.MOBI_TABLE_NO_TITLE_ENTRY
            TITLE_PAGE_END    = self.MOBI_TABLE_TITLE_PAGE_END
        else:
            TITLE_PAGE_START  = self.MOBI_TITLE_PAGE_START
            TITLE_ENTRY       = self.MOBI_TITLE_ENTRY
            WIDE_TITLE_ENTRY  = self.MOBI_TITLE_ENTRY # same, only wide in tables.
            NO_TITLE_ENTRY    = self.MOBI_NO_TITLE_ENTRY
            TITLE_PAGE_END    = self.MOBI_TITLE_PAGE_END

        titlepageIO = BytesIO()
        self.writeTitlePage(out=titlepageIO,
                            START=TITLE_PAGE_START,
                            ENTRY=TITLE_ENTRY,
                            WIDE_ENTRY=WIDE_TITLE_ENTRY,
                            END=TITLE_PAGE_END,
                            NO_TITLE_ENTRY=NO_TITLE_ENTRY)
        if titlepageIO.getvalue(): # will be false if no title page.
            files.append(titlepageIO.getvalue())
        titlepageIO.close()

        ## MOBI always has a TOC injected by mobi.py because there's
        ## no meta-data TOC.
        # # write toc page.
        # tocpageIO = BytesIO()
        # self.writeTOCPage(tocpageIO,
        #                   self.MOBI_TOC_PAGE_START,
        #                   self.MOBI_TOC_ENTRY,
        #                   self.MOBI_TOC_PAGE_END)
        # if tocpageIO.getvalue(): # will be false if no toc page.
        #     files.append(tocpageIO.getvalue())
        # tocpageIO.close()

        if self.hasConfig('chapter_start'):
            CHAPTER_START = string.Template(self.getConfig("chapter_start"))
        else:
            CHAPTER_START = self.MOBI_CHAPTER_START

        if self.hasConfig('chapter_end'):
            CHAPTER_END = string.Template(self.getConfig("chapter_end"))
        else:
            CHAPTER_END = self.MOBI_CHAPTER_END

        for index, chap in enumerate(self.story.getChapters()):
            if chap['html']:
                logger.debug('Writing chapter text for: %s' % chap['title'])
                fullhtml = CHAPTER_START.substitute(chap) + chap['html'] + CHAPTER_END.substitute(chap)
                # ffnet(& maybe others) gives the whole chapter text
                # as one line.  This causes problems for nook(at
                # least) when the chapter size starts getting big
                # (200k+)
                fullhtml = fullhtml.replace('</p>','</p>\n').replace('<br />','<br />\n')
                files.append(fullhtml.encode('utf-8'))
                del fullhtml

        c = Converter(title=self.getMetadata('title'),
                      author=self.getMetadata('author'),
                      publisher=self.getMetadata('site'))
        mobidata = c.ConvertStrings(files)
        if len(mobidata) < 1:
            raise FailedToWriteOutput("Zero length mobi output")
        out.write(mobidata)

        del files
        del mobidata

## Utility method for creating new tags.
def newTag(dom,name,attrs=None,text=None):
    tag = dom.createElement(name)
    if( attrs is not None ):
        for attr in attrs.keys():
            tag.setAttribute(attr,attrs[attr])
    if( text is not None ):
        tag.appendChild(dom.createTextNode(text))
    return tag
