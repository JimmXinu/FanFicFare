#!/usr/bin/env python
# encoding: utf-8
"""
remover.py

Created by Roman on 2010-06-20.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
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
		theDate = datetime.date.today() - datetime.timedelta(days=3)
		logging.debug("Will delete stuff older than %s" % theDate)

		fics = DownloadMeta.all()
		fics.filter("date <",theDate).order("date")
		results = fics.fetch(100)
		logging.debug([x.name for x in results])

		num = 0
		for d in results:
			d.delete()
			for c in d.data_chunks:
				c.delete()
			num = num + 1
			logging.debug('Delete '+d.url)
		
		logging.info('Deleted instances: %d' % num)
		self.response.out.write('Deleted instances: %d' % num)
		

def main():
	application = webapp.WSGIApplication([('/r3m0v3r', Remover)],
                                               debug=False)
	util.run_wsgi_app(application)


if __name__ == '__main__':
	logging.getLogger().setLevel(logging.DEBUG)
	main()
