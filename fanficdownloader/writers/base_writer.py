# -*- coding: utf-8 -*-

import re
import os.path
import string
import StringIO
import zipfile
from zipfile import ZipFile, ZIP_DEFLATED

from story import Story
from configurable import Configurable
from htmlcleanup import removeEntities, removeAllEntities, stripHTML

from adapters.base_adapter import *

class BaseStoryWriter(Configurable):

    @staticmethod
    def getFormatName():
        return 'base'

    @staticmethod
    def getFormatExt():
        return '.bse'

    def __init__(self, config, story):
        Configurable.__init__(self, config)
        self.addConfigSection(self.getFormatName())
        self.story = story
        self.titleLabels = {
            'category':'Category',
            'genre':'Genre',
            'status':'Status',
            'datePublished':'Published',
            'dateUpdated':'Updated',
            'dateCreated':'Packaged',
            'rating':'Rating',
            'warnings':'Warnings',
            'numChapters':'Chapters',
            'numWords':'Words',
            'site':'Publisher',
            'storyId':'Story ID',
            'authorId':'Author ID',
            'extratags':'Extra Tags',
            'title':'Title',
            'storyUrl':'Story URL',
            'description':'Summary',
            'author':'Author',
            'authorUrl':'Author URL',
            'formatname':'File Format',
            'formatext':'File Extension',
            }
        self.story.setMetadata('formatname',self.getFormatName())
        self.story.setMetadata('formatext',self.getFormatExt())

    def getOutputFileName(self):
        return self.getFileName(self.getConfig('output_filename'))

    def getZipFileName(self):
        return self.getFileName(self.getConfig('zip_filename'),extension=".zip")

    def getFileName(self,template,extension="${formatext}"):
        values = self.story.metadata
        fallback=False
        # fall back default:
        if not template:
            template="${title}-${siteabbrev}_${storyId}${formatext}"
            fallback=True

        # Add extension if not already included.
        if extension not in template:
            template+=extension

        if fallback or self.getConfig('safe_filename'):
            values={}
            pattern = re.compile(r"[^a-zA-Z0-9_\. \[\]\(\)&'-]+")
            for k in self.story.metadata.keys():
                values[k]=re.sub(pattern,'_', removeAllEntities(self.story.getMetadata(k)))

        return string.Template(template).substitute(values).encode('utf8')

    def _write(self, out, text):
        out.write(text.encode('utf8'))

    def writeTitlePage(self, out, START, ENTRY, END, WIDE_ENTRY=None):
        """
        Write the title page, but only include entries that there's
        metadata for.  START, ENTRY and END are expected to already by
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use label and value.
        """
        if self.getConfig("include_titlepage"):
            self._write(out,START.substitute(self.story.metadata))

            if WIDE_ENTRY==None:
                WIDE_ENTRY=ENTRY

            titleEntriesList = self.getConfigList("titlepage_entries")
            wideTitleEntriesList = self.getConfigList("wide_titlepage_entries")

            for entry in titleEntriesList:
                if entry in self.titleLabels:
                    if self.story.getMetadata(entry):
                        if entry in wideTitleEntriesList:
                            TEMPLATE=WIDE_ENTRY
                        else:
                            TEMPLATE=ENTRY
                        self._write(out,TEMPLATE.substitute({'label':self.titleLabels[entry],
                                                             'value':self.story.getMetadata(entry)}))

            self._write(out,END.substitute(self.story.metadata))

    def writeTOCPage(self, out, START, ENTRY, END):
        """
        Write the Table of Contents page.  START, ENTRY and END are expected to already by
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use index and chapter.
        """
        # Only do TOC if there's more than one chapter and it's configured.
        if len(self.story.getChapters()) > 1 and self.getConfig("include_tocpage"):
            self._write(out,START.substitute(self.story.metadata))

            for index, (title,html) in enumerate(self.story.getChapters()):
                self._write(out,ENTRY.substitute({'chapter':title, 'index':"%04d"%(index+1)}))

            self._write(out,END.substitute(self.story.metadata))

    # if no outstream is given, write to file.
    def writeStory(self,outstream=None):
        self.addConfigSection(self.story.getMetadata('site'))
        self.addConfigSection(self.story.getMetadata('site')+":"+self.getFormatName())
        for tag in self.getConfigList("extratags"):
            self.story.addToList("extratags",tag)

        zipfilename=self.getZipFileName()
        filename=self.getOutputFileName()

        if self.getConfig('zip_output'):
            outfilename=zipfilename
        else:
            outfilename=filename

        if not outstream:
            if self.getConfig('make_directories'):
                path=""
                dirs = os.path.dirname(outfilename).split('/')
                for dir in dirs:
                    path+=dir+"/"
                    if not os.path.exists(path):
                        os.mkdir(path) ## os.makedirs() doesn't work in 2.5.2?
            outstream = open(outfilename,"wb")

        if self.getConfig('zip_output'):
            out = StringIO.StringIO()
            self.writeStoryImpl(out)
            zipout = ZipFile(outstream, 'w', compression=ZIP_DEFLATED)
            zipout.writestr(filename,out.getvalue())
            zipout.close()
            out.close()
        else:
            self.writeStoryImpl(outstream)

        outstream.close()

    def writeStoryImpl(self, out):
        "Must be overriden by sub classes."
        pass

