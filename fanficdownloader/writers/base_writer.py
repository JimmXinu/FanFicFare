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

import re
import os.path
import datetime
import string
import StringIO
import zipfile
from zipfile import ZipFile, ZIP_DEFLATED
import logging

from fanficdownloader.configurable import Configurable
from fanficdownloader.htmlcleanup import removeEntities, removeAllEntities, stripHTML

class BaseStoryWriter(Configurable):

    @staticmethod
    def getFormatName():
        return 'base'

    @staticmethod
    def getFormatExt():
        return '.bse'

    def __init__(self, config, adapter):
        Configurable.__init__(self, config)
        self.addConfigSection(adapter.getSiteDomain())
        self.addConfigSection(self.getFormatName())
        self.addConfigSection(adapter.getSiteDomain()+":"+self.getFormatName())
        self.addConfigSection("overrides")
        
        self.adapter = adapter
        self.story = adapter.getStoryMetadataOnly() # only cache the metadata initially.
        self.validEntries = [
            'category',
            'genre',
            'characters',
            'status',
            'datePublished',
            'dateUpdated',
            'dateCreated',
            'rating',
            'warnings',
            'numChapters',
            'numWords',
            'site',
            'storyId',
            'authorId',
            'extratags',
            'title',
            'storyUrl',
            'description',
            'author',
            'authorUrl',
            'formatname',
            'formatext',
            'siteabbrev',
            'version']

        # fall back labels.
        self.titleLabels = {
            'category':'Category',
            'genre':'Genre',
            'status':'Status',
            'characters':'Characters',
            'datePublished':'Published',
            'dateUpdated':'Updated',
            'dateCreated':'Packaged',
            'rating':'Rating',
            'warnings':'Warnings',
            'numChapters':'Chapters',
            'numWords':'Words',
            'site':'Site',
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
            'siteabbrev':'Site Abbrev',
            'version':'FFD Version'
            }
        self.story.setMetadata('formatname',self.getFormatName())
        self.story.setMetadata('formatext',self.getFormatExt())

    def getOutputFileName(self):
        if self.getConfig('zip_output'):
            return self.getZipFileName()
        else:
            return self.getBaseFileName()

    def getBaseFileName(self):
        return self.formatFileName(self.getConfig('output_filename'))
    
    def getZipFileName(self):
        return self.formatFileName(self.getConfig('zip_filename'))

    def formatFileName(self,template):
        values = self.story.metadata
        # fall back default:
        if not template:
            template="${title}-${siteabbrev}_${storyId}${formatext}"

        if not self.getConfig('allow_unsafe_filename'):
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
                if entry in self.validEntries:
                    if self.story.getMetadata(entry):
                        if entry in wideTitleEntriesList:
                            TEMPLATE=WIDE_ENTRY
                        else:
                            TEMPLATE=ENTRY
                        if self.getConfigList(entry):
                            label=self.getConfig(entry+"_label")
                        else:
                            label=self.titleLabels[entry]
                        self._write(out,TEMPLATE.substitute({'label':label,
                                                             'value':self.story.getMetadata(entry)}))

            self._write(out,END.substitute(self.story.metadata))

    def writeTOCPage(self, out, START, ENTRY, END):
        """
        Write the Table of Contents page.  START, ENTRY and END are expected to already by
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use index and chapter.
        """
        # Only do TOC if there's more than one chapter and it's configured.
        if len(self.story.getChapters()) > 1 and self.getConfig("include_tocpage") and not self.metaonly :
            self._write(out,START.substitute(self.story.metadata))

            for index, (title,html) in enumerate(self.story.getChapters()):
                if html:
                    self._write(out,ENTRY.substitute({'chapter':title, 'index':"%04d"%(index+1)}))

            self._write(out,END.substitute(self.story.metadata))

    # if no outstream is given, write to file.
    def writeStory(self,outstream=None,metaonly=False):
        for tag in self.getConfigList("extratags"):
            self.story.addToList("extratags",tag)

        self.metaonly = metaonly
        outfilename=self.getOutputFileName()

        if not outstream:
            close=True
            logging.debug("Save directly to file: %s" % outfilename)
            if self.getConfig('make_directories'):
                path=""
                dirs = os.path.dirname(outfilename).split('/')
                for dir in dirs:
                    path+=dir+"/"
                    if not os.path.exists(path):
                        os.mkdir(path) ## os.makedirs() doesn't work in 2.5.2?

            ## Check for output file date vs updated date here
            if not self.getConfig('always_overwrite'):
                if os.path.exists(outfilename):
                    ## date() truncs off time, which files have, but sites don't report.
                    lastupdated=self.story.getMetadataRaw('dateUpdated').date()
                    fileupdated=datetime.datetime.fromtimestamp(os.stat(outfilename)[8]).date()
                    if fileupdated > lastupdated:
                        print "File(%s) Updated(%s) more recently than Story(%s) - Skipping" % (outfilename,fileupdated,lastupdated)
                        return
            if not metaonly:        
                self.story = self.adapter.getStory() # get full story
                                                     # now, just
                                                     # before writing.
                                                     # Fetch before
                                                     # opening file.
            outstream = open(outfilename,"wb")
        else:
            close=False
            logging.debug("Save to stream")

        if not metaonly:
            self.story = self.adapter.getStory() # get full story now,
                                                 # just before
                                                 # writing.  Okay if
                                                 # double called with
                                                 # above, it will only
                                                 # fetch once.
        if self.getConfig('zip_output'):
            out = StringIO.StringIO()
            self.writeStoryImpl(out)
            zipout = ZipFile(outstream, 'w', compression=ZIP_DEFLATED)
            zipout.writestr(self.getBaseFileName(),out.getvalue())
            # declares all the files created by Windows.  otherwise, when
            # it runs in appengine, windows unzips the files as 000 perms.
            for zf in zipout.filelist:
                zf.create_system = 0
            zipout.close()
            out.close()
        else:
            self.writeStoryImpl(outstream)

        if close:
            outstream.close()

    def writeStoryImpl(self, out):
        "Must be overriden by sub classes."
        pass

