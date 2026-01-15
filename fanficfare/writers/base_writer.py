# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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

import os.path
import datetime
import string
from zipfile import ZipFile, ZIP_DEFLATED
import logging

# py2 vs py3 transition
from ..six import ensure_text
from ..six import ensure_binary
from io import BytesIO

from ..requestable import Requestable
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

class BaseStoryWriter(Requestable):

    @staticmethod
    def getFormatName():
        return 'base'

    @staticmethod
    def getFormatExt():
        return '.bse'

    def __init__(self, configuration, adapter):
        Requestable.__init__(self, configuration)

        self.adapter = adapter
        self.story = adapter.getStoryMetadataOnly() # only cache the metadata initially.

        self.story.setMetadata('formatname',self.getFormatName())
        self.story.setMetadata('formatext',self.getFormatExt())

    def getMetadata(self,key, removeallentities=False):
        return stripHTML(self.story.getMetadata(key, removeallentities))

    def getOutputFileName(self):
        if self.getConfig('zip_output'):
            return self.getZipFileName()
        else:
            return self.getBaseFileName()

    def getBaseFileName(self):
        return self.story.formatFileName(self.getConfig('output_filename'),self.getConfig('allow_unsafe_filename'))

    def getZipFileName(self):
        return self.story.formatFileName(self.getConfig('zip_filename'),self.getConfig('allow_unsafe_filename'))

    def _write(self, out, text):
        out.write(ensure_binary(text))

    def includeToCPage(self):
        return (self.getConfig("include_tocpage")=='always' or (self.story.getChapterCount() > 1 and self.getConfig("include_tocpage"))) and not self.metaonly

    def writeTitlePage(self, out, START, ENTRY, END, WIDE_ENTRY=None, NO_TITLE_ENTRY=None):
        """
        Write the title page, but only include entries that there's
        metadata for.  START, ENTRY and END are expected to already by
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use label and value.
        """
        if self.getConfig("include_titlepage"):

            if self.hasConfig("titlepage_start"):
                START = string.Template(self.getConfig("titlepage_start"))

            if self.hasConfig("titlepage_entry"):
                ENTRY = string.Template(self.getConfig("titlepage_entry"))

            if self.hasConfig("titlepage_end"):
                END = string.Template(self.getConfig("titlepage_end"))

            if self.hasConfig("titlepage_wide_entry"):
                WIDE_ENTRY = string.Template(self.getConfig("titlepage_wide_entry"))

            if self.hasConfig("titlepage_no_title_entry"):
                NO_TITLE_ENTRY = string.Template(self.getConfig("titlepage_no_title_entry"))

            self._write(out,START.substitute(self.story.getAllMetadata()))

            ## should only be include when titlepage_use_table:true
            if WIDE_ENTRY==None:
                WIDE_ENTRY=ENTRY

            titleEntriesList = self.getConfigList("titlepage_entries") + self.getConfigList("extra_titlepage_entries")
            wideTitleEntriesList = self.getConfigList("wide_titlepage_entries")

            for entry in titleEntriesList:
                # logger.debug("entry:%s"%entry)
                show_empty = False
                if entry.endswith('.SHOW_EMPTY'):
                    entry = entry[:-len('.SHOW_EMPTY')]
                    show_empty = True
                # logger.debug("entry:%s"%entry)
                # logger.debug("show_empty:%s"%show_empty)
                if self.isValidMetaEntry(entry):
                    if self.story.getMetadata(entry) or show_empty:
                        if entry in wideTitleEntriesList:
                            TEMPLATE=WIDE_ENTRY
                        else:
                            TEMPLATE=ENTRY

                        label=self.get_label(entry)

                        # If the label for the title entry is empty, use the
                        # 'no title' option if there is one.
                        if label == "" and NO_TITLE_ENTRY:
                           TEMPLATE= NO_TITLE_ENTRY

                        self._write(out,TEMPLATE.substitute({'label':label,
                                                             'id':entry,
                                                             'value':self.story.getMetadata(entry)}))
                else:
                    self._write(out, entry)

            self._write(out,END.substitute(self.story.getAllMetadata()))

    def writeTOCPage(self, out, START, ENTRY, END):
        """
        Write the Table of Contents page.  START, ENTRY and END are expected to already by
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use index and chapter.
        """
        # Only do TOC if there's more than one chapter and it's configured.
        if self.includeToCPage():
            if self.hasConfig("tocpage_start"):
                START = string.Template(self.getConfig("tocpage_start"))

            if self.hasConfig("tocpage_entry"):
                ENTRY = string.Template(self.getConfig("tocpage_entry"))

            if self.hasConfig("tocpage_end"):
                END = string.Template(self.getConfig("tocpage_end"))

            self._write(out,START.substitute(self.story.getAllMetadata()))

            for index, chap in enumerate(self.story.getChapters(fortoc=True)):
                if chap['html']:
                    self._write(out,ENTRY.substitute(chap))

            self._write(out,END.substitute(self.story.getAllMetadata()))

    # if no outstream is given, write to file.
    def writeStory(self,
                   outstream=None,
                   metaonly=False,
                   outfilename=None,
                   forceOverwrite=False,
                   notification=lambda x,y:x):

        self.metaonly = metaonly
        if outfilename == None:
            outfilename=self.getOutputFileName()

        self.outfilename = outfilename

        temp_css = ''
        # if the story has author-defined(AO3 workskin) CSS that we
        # want to include, include in FFF's CSS.
        if self.story.extra_css:
            temp_css = self.story.extra_css

        # output_css setting last so it can override
        if self.getConfig("output_css"):
            temp_css += self.getConfig("output_css")

        if self.getConfig('include_images'):
            temp_css = self.adapter.include_css_urls(self.story.getMetadata('storyUrl'), temp_css)

        # minor cheat, tucking css into metadata.
        self.story.setMetadata("output_css",
                               temp_css,
                               condremoveentities=False)

        if not outstream:
            close=True
            logger.info("Save directly to file: %s" % outfilename)
            if self.getConfig('make_directories'):
                path=""
                outputdirs = os.path.dirname(ensure_text(outfilename)).split('/')
                for dir in outputdirs:
                    path+=dir+"/"
                    if not os.path.exists(path):
                        os.mkdir(path) ## os.makedirs() doesn't work in 2.5.2?

            ## Check for output file date vs updated date here
            if not (self.getConfig('always_overwrite') or forceOverwrite):
                if os.path.exists(outfilename):
                    ## date() truncs off time, which files have, but sites don't report.
                    lastupdated=self.story.getMetadataRaw('dateUpdated').date()
                    fileupdated=datetime.datetime.fromtimestamp(os.stat(outfilename)[8]).date()
                    if fileupdated > lastupdated:
                        logger.warning("File(%s) Updated(%s) more recently than Story(%s) - Skipping" % (outfilename,fileupdated,lastupdated))
                        return
            if not metaonly:
                # get full story now, just before writing.  Fetch
                # before opening file.
                self.story = self.adapter.getStory(notification)
            outstream = open(outfilename,"wb")
        else:
            close=False
            logger.debug("Save to stream")

        if not metaonly:
            # get full story now, just before writing.  Okay if double
            # called with above, it will only fetch once.
            self.story = self.adapter.getStory(notification)
        if self.getConfig('zip_output'):
            out = BytesIO()
            self.zipout = ZipFile(outstream, 'w', compression=ZIP_DEFLATED)
            self.writeStoryImpl(out)
            self.zipout.writestr(self.getBaseFileName(),out.getvalue())
            # declares all the files created by Windows.  otherwise, when
            # it runs in appengine, windows unzips the files as 000 perms.
            for zf in self.zipout.filelist:
                zf.create_system = 0
            self.zipout.close()
            out.close()
        else:
            self.writeStoryImpl(outstream)

        if close:
            outstream.close()

    def writeFile(self, filename, data):
        logger.debug("writeFile:%s"%filename)

        if self.getConfig('zip_output'):
            outputdirs = os.path.dirname(self.getBaseFileName())
            if outputdirs:
                filename=outputdirs+'/'+filename
            self.zipout.writestr(filename,data)
        else:
            outputdirs = os.path.dirname(self.outfilename)
            if outputdirs:
                filename=outputdirs+'/'+filename

            dir = os.path.dirname(filename)
            if not os.path.exists(dir):
                os.mkdir(dir) ## os.makedirs() doesn't work in 2.5.2?

            outstream = open(filename,"wb")
            outstream.write(data)
            outstream.close()

    def writeStoryImpl(self, out):
        "Must be overriden by sub classes."
