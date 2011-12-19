#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

import os, traceback, time

import ConfigParser

from calibre.ebooks import DRMError
from calibre.ptempfile import PersistentTemporaryFile
from calibre.ebooks.metadata import MetaInformation

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters,writers,exceptions

def do_story_downloads(adaptertuple_list, fileform, db,
                       abort=None, log=None, notifications=[]): # lambda x,y:x lambda makes small anonymous function.
    '''
    Master job, to launch child jobs to download this list of stories
    '''
    print("do_story_downloads")
    notifications.put((0.01, 'Start Downloading Stories'))
    count = 0
    total = len(adaptertuple_list)
    # Queue all the jobs
    for (url,adapter) in adaptertuple_list:
        do_story_download(adapter,fileform,db)
        count = count + 1
        notifications.put((float(count)/total, 'Downloading Stories'))
    # return the map as the job result
    # return book_pages_map, book_words_map
    return {},{}

def do_story_download(adapter,fileform,db):
    print("do_story_download")

#    ffdlconfig = ConfigParser.SafeConfigParser()
#    adapter = adapters.getAdapter(ffdlconfig,url)

    story = adapter.getStoryMetadataOnly()

    mi = MetaInformation(story.getMetadata("title"),
                         (story.getMetadata("author"),)) # author is a list.
    
    writer = writers.getWriter(fileform,adapter.config,adapter)
    tmp = PersistentTemporaryFile("."+fileform)
    print("tmp: "+tmp.name)
    
    writer.writeStory(tmp)
    
    print("post write tmp: "+tmp.name)
    
    mi.set_identifiers({'url':story.getMetadata("storyUrl")})
    mi.publisher = story.getMetadata("site")

    mi.tags = writer.getTags()
    mi.languages = ['en']
    mi.pubdate = story.getMetadataRaw('datePublished').strftime("%Y-%m-%d")
    mi.timestamp = story.getMetadataRaw('dateCreated').strftime("%Y-%m-%d")
    mi.comments = story.getMetadata("description")

    (notadded,addedcount)=db.add_books([tmp],[fileform],[mi], add_duplicates=True)
    # Otherwise list of books doesn't update right away.
    #self.gui.library_view.model().books_added(addedcount)

    del adapter
    del writer

