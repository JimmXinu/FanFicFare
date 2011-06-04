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

from google.appengine.ext.webapp import util
from google.appengine.ext import webapp
from google.appengine.api import users

from ffstorage import *

class Remover(webapp.RequestHandler):
    def get(self):
        logging.debug("Starting r3m0v3r")
        user = users.get_current_user()
        logging.debug("Working as user %s" % user)
        theDate = datetime.datetime.now() - datetime.timedelta(days=7) # days=7
        logging.debug("Will delete stuff older than %s" % theDate)
        
        fics = DownloadMeta.all()
        fics.filter("date <",theDate).order("date")
        
        num = 0
        while( True ) :
            results = fics.fetch(100)
            if not results:
                self.response.out.write('Finished<br>')
                break
            logging.debug([x.name for x in results])

            for d in results:
                d.delete()
                for c in d.data_chunks:
                    c.delete()
                num += 1
                logging.debug('Delete '+d.url)

        logging.info('Deleted instances: %d' % num)
        self.response.out.write('Deleted instances: %d<br>' % num)

class RemoveOrphanDataChunks(webapp.RequestHandler):
    def get(self):
        logging.debug("Starting RemoveOrphanDataChunks")
        user = users.get_current_user()
        logging.debug("Working as user %s" % user)
        
        chunks = DownloadData.all()

        deleted = 0
        num = 0
        step=2
        while( True ) :
            results = chunks.fetch(limit=step,offset=num-deleted)
            if not results:
                self.response.out.write('Finished<br>')
                break

            for d in results:
                ## This is the only way to test for orphans I could find.
                try:
                    meta = d.download
                except db.ReferencePropertyResolveError:
                    ## delete orphan chunk.
                    d.delete()
                    deleted += 1
                num += 1
        
        logging.info('Deleted %d orphan chunks from %d total.' % (deleted,num))
        self.response.out.write('Deleted %d orphan chunks from %d total.<br>' % (deleted,num))

def main():
    application = webapp.WSGIApplication([('/r3m0v3r', Remover),
                                          ('/r3m0v3rOrphans', RemoveOrphanDataChunks)],
                                         debug=False)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main()
