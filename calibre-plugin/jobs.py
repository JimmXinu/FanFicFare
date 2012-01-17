#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__copyright__ = '2011, Grant Drake <grant.drake@gmail.com>'
__docformat__ = 'restructuredtext en'

import time, os, traceback

from ConfigParser import SafeConfigParser
from StringIO import StringIO
#from itertools import izip
#from threading import Event

#from calibre.gui2.convert.single import sort_formats_by_preference
from calibre.utils.ipc.server import Server
from calibre.utils.ipc.job import ParallelJob
from calibre.utils.logging import Log

from calibre_plugins.fanfictiondownloader_plugin.dialogs import (NotGoingToDownload,
    OVERWRITE, OVERWRITEALWAYS, UPDATE, UPDATEALWAYS, ADDNEW, SKIP, CALIBREONLY)
from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, writers, exceptions
from calibre_plugins.fanfictiondownloader_plugin.epubmerge import doMerge

# ------------------------------------------------------------------------------
#
#              Functions to perform downloads using worker jobs
#
# ------------------------------------------------------------------------------

def do_download_worker(book_list, options,
                       cpus, notification=lambda x,y:x):
    '''
    Master job, to launch child jobs to extract ISBN for a set of books
    This is run as a worker job in the background to keep the UI more
    responsive and get around the memory leak issues as it will launch
    a child job for each book as a worker process
    '''
    server = Server(pool_size=cpus)

    print(options['version'])
    total = 0
    # Queue all the jobs
    print("Adding jobs for URLs:")
    for book in book_list:
        if book['good']:
            print("%s"%book['url'])
            total += 1
            args = ['calibre_plugins.fanfictiondownloader_plugin.jobs',
                    'do_download_for_worker',
                    (book,options)]
            job = ParallelJob('arbitrary',
                              "url:(%s) id:(%s)"%(book['url'],book['calibre_id']),
                              done=None,
                              args=args)
            job._book = book
            # job._book_id = book_id
            # job._title = title
            # job._modified_date = modified_date
            # job._existing_isbn = existing_isbn
            server.add_job(job)
    
    # This server is an arbitrary_n job, so there is a notifier available.
    # Set the % complete to a small number to avoid the 'unavailable' indicator
    notification(0.01, 'Downloading FanFiction Stories')

    # dequeue the job results as they arrive, saving the results
    count = 0
    while True:
        job = server.changed_jobs_queue.get()
        # A job can 'change' when it is not finished, for example if it
        # produces a notification. Ignore these.
        job.update()
        if not job.is_finished:
            continue
        # A job really finished. Get the information.
        output_book = job.result
        #print("output_book:%s"%output_book)
        book_list.remove(job._book)
        book_list.append(job.result)
        book_id = job._book['calibre_id']
        #title = job._title
        count = count + 1
        notification(float(count)/total, 'Downloaded Story')
        # Add this job's output to the current log
        print('Logfile for book ID %s (%s)'%(book_id, job._book['title']))
        print(job.details)

        if count >= total:
            # All done!
            break

    server.close()
    
    # return the book list as the job result
    return book_list

def do_download_for_worker(book,options):
    '''
    Child job, to extract isbn from formats for this specific book,
    when run as a worker job
    '''
    try:
        book['comment'] = 'Download started...'

        ffdlconfig = SafeConfigParser()
        ffdlconfig.readfp(StringIO(get_resources("plugin-defaults.ini")))
        ffdlconfig.readfp(StringIO(options['personal.ini']))
        
        adapter = adapters.getAdapter(ffdlconfig,book['url'])
        adapter.is_adult = book['is_adult'] 
        adapter.username = book['username'] 
        adapter.password = book['password']
        
        story = adapter.getStoryMetadataOnly()
        writer = writers.getWriter(options['fileform'],adapter.config,adapter)

        outfile = book['outfile']

        ## No need to download at all.  Shouldn't ever get down here.
        if options['collision'] in (CALIBREONLY):
            print("Skipping CALIBREONLY 'update' down inside worker--this shouldn't be happening...")
            book['comment'] = 'Metadata collected.'
            
        ## checks were done earlier, it's new or not dup or newer--just write it.
        elif options['collision'] in (ADDNEW, SKIP, OVERWRITE, OVERWRITEALWAYS) or \
                ('epub_for_update' not in book and options['collision'] in (UPDATE, UPDATEALWAYS)):
            print("write to %s"%outfile)
            writer.writeStory(outfilename=outfile, forceOverwrite=True)
            book['comment'] = 'Download %s completed, %s chapters.'%(options['fileform'],story.getMetadata("numChapters"))
            
        ## checks were done earlier, just update it.
        elif 'epub_for_update' in book and options['collision'] in (UPDATE, UPDATEALWAYS):
            
            urlchaptercount = int(story.getMetadata('numChapters'))
            ## First, get existing epub with titlepage and tocpage stripped.
            updateio = StringIO()
            (epuburl,chaptercount) = doMerge(updateio,
                                             [book['epub_for_update']],
                                             titlenavpoints=False,
                                             striptitletoc=True,
                                             forceunique=False)
            print("Do update - epub(%d) vs url(%d)" % (chaptercount, urlchaptercount))
            print("write to %s"%outfile)

            ## Get updated title page/metadata by itself in an epub.
            ## Even if the title page isn't included, this carries the metadata.
            titleio = StringIO()
            writer.writeStory(outstream=titleio,metaonly=True)

            newchaptersio = None
            if urlchaptercount > chaptercount :
                ## Go get the new chapters
                newchaptersio = StringIO()
                adapter.setChaptersRange(chaptercount+1,urlchaptercount)

                adapter.config.set("overrides",'include_tocpage','false')
                adapter.config.set("overrides",'include_titlepage','false')
                writer.writeStory(outstream=newchaptersio)

            ## Merge the three epubs together.
            doMerge(outfile,
                    [titleio,updateio,newchaptersio],
                    fromfirst=True,
                    titlenavpoints=False,
                    striptitletoc=False,
                    forceunique=False)
            
            book['comment'] = 'Update %s completed, added %s chapters for %s total.'%\
                (options['fileform'],(urlchaptercount-chaptercount),urlchaptercount)
        
    except NotGoingToDownload as d:
        book['good']=False
        book['comment']=unicode(d)
        book['icon'] = d.icon

    except Exception as e:
        book['good']=False
        book['comment']=unicode(e)
        book['icon']='dialog_error.png'
        print("Exception: %s:%s"%(book,unicode(e)))
        traceback.print_exc()

    #time.sleep(10)
    return book
