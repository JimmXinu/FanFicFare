#!/usr/bin/env python
# encoding: utf-8
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

"""
remover.py

Created by Roman on 2010-06-20.
Copyright 2011 Fanficdownloader team
"""

import datetime
import logging

#from google.appengine.ext.webapp import util
import webapp2
#from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import taskqueue
from google.appengine.api import memcache

from ffstorage import *

class Remover(webapp2.RequestHandler):
    def get(self):
        logging.debug("Starting r3m0v3r")
        user = users.get_current_user()
        logging.debug("Working as user %s" % user)
        theDate = datetime.datetime.now() - datetime.timedelta(days=3)
        logging.debug("Will delete stuff older than %s" % theDate)
        
        fics = DownloadMeta.all()
        fics.filter("date <",theDate).order("date")
        
        results = fics.fetch(100)
        logging.debug([x.name for x in results])

        num=0
        for d in results:
            d.delete()
            for c in d.data_chunks:
                c.delete()
            num += 1
            logging.debug('Delete '+d.url)

        logging.info('Deleted instances: %d' % num)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write('Deleted instances: %d<br>' % num)

class RemoveOrphanDataChunks(webapp2.RequestHandler):

    def get(self):
        logging.debug("Starting RemoveOrphanDataChunks")
        user = users.get_current_user()
        logging.debug("Working as user %s" % user)

        ## Can't search for all chunks in web req because it's too
        ## long.  Can't do it in a queue task, because it's still too
        ## long.  Can't try ordering by id or download because the ids
        ## are not increasing.  Instead, use a saved cursor to walk
        ## all the way through over time, then starting at the top
        ## again when finished.
        
        chunks = DownloadData.all()

        cursor = memcache.get('orphan_search_cursor')
        if cursor:
            chunks.with_cursor(cursor)

        deleted = 0
        num = 0
        step = 100
        results = chunks.fetch(step)
        for d in results:
            ## This is the only way to test for orphans I could find.
            try:
                meta = d.download
            except db.ReferencePropertyResolveError:
                ## delete orphan chunk.
                d.delete()
                deleted += 1
            num += 1
        if num < step:
            memcache.delete('orphan_search_cursor')
            logging.warn('Orphan search reached end, starting over next time.')
        else:
            memcache.set('orphan_search_cursor',chunks.cursor())
        
        logging.info('Deleted %d orphan chunks from %d total.' % (deleted,num))
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write('Deleted %d orphan chunks from %d total.' % (deleted,num))

logging.getLogger().setLevel(logging.DEBUG)
app = webapp2.WSGIApplication([('/r3m0v3r', Remover),
                               ('/r3m0v3rOrphans', RemoveOrphanDataChunks)],
                              debug=False)
