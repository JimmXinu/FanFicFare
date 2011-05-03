# -*- coding: utf-8 -*-

import logging
import string

from writers.base_writer import *

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
<a name="TOCTOP"><h3>Table of Contents</h3>
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
            logging.debug('Writing chapter text for: %s' % title)
            self._write(out,self.HTML_CHAPTER_START.substitute({'chapter':title, 'index':"%04d"%(index+1)}))
            self._write(out,html)

        self._write(out,self.HTML_FILE_END.substitute(self.story.metadata))
