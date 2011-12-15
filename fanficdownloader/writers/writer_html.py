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

from base_writer import *

class HTMLWriter(BaseStoryWriter):

    @staticmethod
    def getFormatName():
        return 'html'

    @staticmethod
    def getFormatExt():
        return '.html'

    def __init__(self, config, story):
        BaseStoryWriter.__init__(self, config, story)
        
        self.HTML_FILE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
<style type="text/css">
body { background-color: #${background_color}; }
.CI {
    text-align:center;
    margin-top:0px;
    margin-bottom:0px;
    padding:0px;
    }
.center   {text-align: center;}
.cover    {text-align: center;}
.full     {width: 100%; }
.quarter  {width: 25%; }
.smcap    {font-variant: small-caps;}
.u        {text-decoration: underline;}
.bold     {font-weight: bold;}
</style>
</head>
<body>
<h1><a href="${storyUrl}">${title}</a> by <a href="${authorUrl}">${author}</a></h1>
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
<a name="TOCTOP"><h2>Table of Contents</h2>
<p>
''')

        self.HTML_TOC_ENTRY = string.Template('''
<a href="#section${index}">${chapter}</a><br />
''')
                          
        self.HTML_TOC_PAGE_END = string.Template('''
</p>
''')

        self.HTML_CHAPTER_START = string.Template('''
<a name="section${index}"><h2>${chapter}</h2></a>
''')

        self.HTML_FILE_END = string.Template('''
</body>
</html>''')


    def writeStoryImpl(self, out):

        # minor cheat, tucking bg into metadata.
        if self.getConfig("background_color"):
            self.story.metadata["background_color"] = self.getConfig("background_color")
        self._write(out,self.HTML_FILE_START.substitute(self.story.metadata))

        self.writeTitlePage(out,
                            self.HTML_TITLE_PAGE_START,
                            self.HTML_TITLE_ENTRY,
                            self.HTML_TITLE_PAGE_END)

        self.writeTOCPage(out,
                          self.HTML_TOC_PAGE_START,
                          self.HTML_TOC_ENTRY,
                          self.HTML_TOC_PAGE_END)

        for index, (title,html) in enumerate(self.story.getChapters()):
            if html:
                logging.debug('Writing chapter text for: %s' % title)
                self._write(out,self.HTML_CHAPTER_START.substitute({'chapter':title, 'index':"%04d"%(index+1)}))
                self._write(out,html)

        self._write(out,self.HTML_FILE_END.substitute(self.story.metadata))
