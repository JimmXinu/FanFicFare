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

import datetime
import logging

#from google.appengine.ext.webapp import util
import webapp2
#from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.api import taskqueue
from google.appengine.api import memcache

from ffstorage import *

class Tally(webapp2.RequestHandler):
    def get(self):
        logging.debug("Starting Tally")
        user = users.get_current_user()
        logging.debug("Working as user %s" % user)
        
        fics = DownloadMeta.all()
        
        cursor = memcache.get('tally_search_cursor')
        if cursor:
            fics.with_cursor(cursor)

        self.response.out.write('"user","url","name","title","author","format","failure","completed","date","version"<br/>')
        num = 0
        step = 500
        results = fics.fetch(step)
        for d in results:
            self.response.out.write('"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s"<br/>' %
                                    (d.user,d.url,d.name,d.title,d.author,
                                     d.format,d.failure,d.completed,d.date,
                                     d.version))
            num += 1
        if num < step:
            memcache.delete('tally_search_cursor')
            logging.warn('Tally search reached end, starting over next time.')
        else:
            memcache.set('tally_search_cursor',fics.cursor())
        
        logging.info('Tallied %d fics.' % num)
        self.response.out.write('<br/>Tallied %d fics.<br/>' % num)

logging.getLogger().setLevel(logging.DEBUG)
app = webapp2.WSGIApplication([('/tally', Tally),
                               ],
                              debug=False)
