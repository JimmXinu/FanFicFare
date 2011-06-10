# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import logging
import string
from textwrap import wrap

from base_writer import *

from fanficdownloader.html2text import html2text, BODY_WIDTH

## In BaseStoryWriter, we define _write to encode <unicode> objects
## back into <string> for true output.  But txt needs to write the
## title page and TOC to a buffer first to wordwrap.  And StringIO
## gets pissy about unicode bytes in its buflist.  This decodes the
## unicode containing <string> object passed in back to a <unicode>
## object so they join up properly.  Could override _write to not
## encode and do out.write(whatever.encode('utf8') instead.  Honestly
## not sure which is uglier.
class KludgeStringIO():
    def __init__(self, buf = ''):
        self.buflist=[]
    def write(self,s):
        try:
            s=s.decode('utf-8')
        except:
            pass
        self.buflist.append(s)
    def getvalue(self):
        return u''.join(self.buflist)
    def close(self):
        pass

class TextWriter(BaseStoryWriter):

    @staticmethod
    def getFormatName():
        return 'txt'

    @staticmethod
    def getFormatExt():
        return '.txt'

    def __init__(self, config, story):
        
        BaseStoryWriter.__init__(self, config, story)
        
        self.TEXT_FILE_START = string.Template(u'''


${title}

by ${author}


''')

        self.TEXT_TITLE_PAGE_START = string.Template(u'''
''')

        self.TEXT_TITLE_ENTRY = string.Template(u'''${label}: ${value}
''')

        self.TEXT_TITLE_PAGE_END = string.Template(u'''


''')

        self.TEXT_TOC_PAGE_START = string.Template(u'''

TABLE OF CONTENTS

''')

        self.TEXT_TOC_ENTRY = string.Template(u'''
${chapter}
''')
                          
        self.TEXT_TOC_PAGE_END = string.Template(u'''
''')

        self.TEXT_CHAPTER_START = string.Template(u'''

\t${chapter}

''')

        self.TEXT_FILE_END = string.Template(u'''

End file.
''')

    def writeStoryImpl(self, out):

        wrapout = KludgeStringIO()
        
        wrapout.write(self.TEXT_FILE_START.substitute(self.story.metadata))

        self.writeTitlePage(wrapout,
                            self.TEXT_TITLE_PAGE_START,
                            self.TEXT_TITLE_ENTRY,
                            self.TEXT_TITLE_PAGE_END)
        towrap = wrapout.getvalue()
        
        self.writeTOCPage(wrapout,
                          self.TEXT_TOC_PAGE_START,
                          self.TEXT_TOC_ENTRY,
                          self.TEXT_TOC_PAGE_END)

        towrap = wrapout.getvalue()
        wrapout.close()
        towrap = removeAllEntities(towrap)
        
        self._write(out,self.lineends(self.wraplines(towrap)))

        for index, (title,html) in enumerate(self.story.getChapters()):
            if html:
                logging.debug('Writing chapter text for: %s' % title)
                self._write(out,self.lineends(self.wraplines(removeAllEntities(self.TEXT_CHAPTER_START.substitute({'chapter':title, 'index':index+1})))))
                self._write(out,self.lineends(html2text(html)))

        self._write(out,self.lineends(self.wraplines(self.TEXT_FILE_END.substitute(self.story.metadata))))

    def wraplines(self, text):
        result=''
        for para in text.split("\n"):
            first=True
            for line in wrap(para, BODY_WIDTH):
                if first:
                    first=False
                else:
                    result += u"\n"
                result += line
            result += u"\n"
        return result 

    ## The appengine will return unix line endings.
    def lineends(self, txt):
        txt = txt.replace('\r','')
        if self.getConfig("windows_eol"):
            txt = txt.replace('\n',u'\r\n')
        return txt
                       
