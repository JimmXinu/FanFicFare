#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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

import os
import sys
import zlib
import logging
import traceback
import StringIO

from google.appengine.runtime import DeadlineExceededError

from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from fanficdownloader.downloader import *
from fanficdownloader.ffnet import *
from fanficdownloader.output import *
from fanficdownloader import twilighted
from fanficdownloader import adastrafanfic

from google.appengine.ext import db

from fanficdownloader.zipdir import *

from ffstorage import *

class LoginRequired(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			self.redirect('/')
		else:
			logging.debug(users.create_login_url('/'))
			url = users.create_login_url(self.request.uri)
			template_values = {'login_url' : url}
			path = os.path.join(os.path.dirname(__file__), 'index-nonlogin.html')
			self.response.out.write(template.render(path, template_values))

class MainHandler(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			error = self.request.get('error')
			template_values = {'nickname' : user.nickname(), 'authorized': True}
			url = self.request.get('url')
			template_values['url'] = url
			
			if error != None and len(error) > 1:
				if error == 'login_required':
					template_values['error_message'] = 'This story (or one of the chapters) requires you to be logged in.'
				elif error == 'bad_url':
					template_values['error_message'] = 'Unsupported URL: ' + url
				elif error == 'custom':
					template_values['error_message'] = 'Error happened: ' + self.request.get('errtext')
			
			filename = self.request.get('file')
			if len(filename) > 1:
				template_values['yourfile'] = '''<div id='yourfile'><a href='/file?id=%s'>"%s" by %s</a></div>''' % (filename, self.request.get('name'), self.request.get('author'))
			
			self.response.headers['Content-Type'] = 'text/html'
			path = os.path.join(os.path.dirname(__file__), 'index.html')

			self.response.out.write(template.render(path, template_values))
		else:
#			self.redirect(users.create_login_url(self.request.uri))
#			self.redirect('/login')
			logging.debug(users.create_login_url('/'))
			url = users.create_login_url(self.request.uri)
			template_values = {'login_url' : url, 'authorized': False}
			path = os.path.join(os.path.dirname(__file__), 'index.html')
			self.response.out.write(template.render(path, template_values))


class FileServer(webapp.RequestHandler):
	def get(self):
#		user  = users.get_current_user()
		fileId = self.request.get('id')
		
		if fileId == None or len(fileId) < 3:
			self.redirect('/')
		
		key = db.Key(fileId)
		fanfic = db.get(key)

		# check for completed & failure.
		
		name = fanfic.name.encode('utf-8')
		
		name = makeAcceptableFilename(name)
		
		logging.info("Serving file: %s" % name)

		if fanfic.format == 'epub':
			self.response.headers['Content-Type'] = 'application/epub+zip'
			self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.epub'
		elif fanfic.format == 'html':
			self.response.headers['Content-Type'] = 'text/html'
			self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.html.zip'
		elif fanfic.format == 'text':
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.headers['Content-disposition'] = 'attachment; filename=' +name + '.txt.zip'
		elif fanfic.format == 'mobi':
			self.response.headers['Content-Type'] = 'application/x-mobipocket-ebook'
			self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.mobi'

		data = DownloadData.all().filter("download =", fanfic).order("index")
		# epub, txt and html are all already compressed.
		# Each chunk is compress individually to avoid having
		# to hold the whole in memory just for the
		# compress/uncompress
		if fanfic.format == 'mobi':
			def dc(data):
				try:
					return zlib.decompress(data)
				# if error, assume it's a chunk from before we started compessing.
				except zlib.error:
					return data
		else:
			def dc(data):
				return data
				
		for datum in data:
			self.response.out.write(dc(datum.blob))

class FileStatusServer(webapp.RequestHandler):
	def get(self):
		logging.info("Status id: %s" % id)
		user = users.get_current_user()
		if not user:
			self.redirect('/login')
		
		fileId = self.request.get('id')
		
		if fileId == None or len(fileId) < 3:
			self.redirect('/')
		
		key = db.Key(fileId)
		fic = db.get(key)

		logging.info("Status url: %s" % fic.url)
		
		template_values = dict(fic = fic, nickname = user.nickname())
		path = os.path.join(os.path.dirname(__file__), 'status.html')
		self.response.out.write(template.render(path, template_values))
		
class RecentFilesServer(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if not user:
			self.redirect('/login')
		
		q = DownloadMeta.all()
		q.filter('user =', user).order('-date')
		fics = q.fetch(100)
		
		template_values = dict(fics = fics, nickname = user.nickname())
		path = os.path.join(os.path.dirname(__file__), 'recent.html')
		self.response.out.write(template.render(path, template_values))
		
class RecentAllFilesServer(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user.nickname() != 'sigizmund':
			return
			
		fics = db.GqlQuery("Select * From DownloadedFanfic")
		template_values = dict(fics = fics, nickname = user.nickname())
		path = os.path.join(os.path.dirname(__file__), 'recent.html')
		self.response.out.write(template.render(path, template_values))	

class FanfictionDownloader(webapp.RequestHandler):
	def get(self):
		self.post()

	def post(self):
		logging.getLogger().setLevel(logging.DEBUG)
		
		user = users.get_current_user()
		if not user:
			self.redirect(users.create_login_url('/'))
			return
		
		format = self.request.get('format')
		url = self.request.get('url')
		login = self.request.get('login')
		password = self.request.get('password')
		
		logging.info("Queuing Download: " + url)

		# use existing record if available.
		q = DownloadMeta.all().filter('user =', user).filter('url =',url).filter('format =',format).fetch(1)
		if( q is None or len(q) < 1 ):
			download = DownloadMeta()
		else:
			download = q[0]
			download.completed=False
			download.failure=None
			for c in download.data_chunks:
				c.delete()
				
		download.user = user
		download.url = url
		download.format = format
		download.put()

		
		taskqueue.add(url='/fdowntask',
			      queue_name="download",
			      params={'format':format,
				      'url':url,
				      'login':login,
				      'password':password,
				      'user':user.email()})
		
		logging.info("enqueued download key: " + str(download.key()))
		self.redirect('/status?id='+str(download.key()))

		return


class FanfictionDownloaderTask(webapp.RequestHandler):
	def _printableVersion(self, text):
		text = removeEntities(text)
		try:
			d = text.decode('utf-8')
		except:
			d = text
		return d
	

	def post(self):
		logging.getLogger().setLevel(logging.DEBUG)
		
		format = self.request.get('format')
		url = self.request.get('url')
		login = self.request.get('login')
		password = self.request.get('password')
		# User object can't pass, just email address
		user = users.User(self.request.get('user'))
		
		logging.info("Downloading: " + url + " for user: "+user.nickname())
		
		adapter = None
		writerClass = None

		# use existing record if available.
		q = DownloadMeta.all().filter('user =', user).filter('url =',url).filter('format =',format).fetch(1)
		if( q is None or len(q) < 1 ):
			download = DownloadMeta()
		else:
			download = q[0]
			download.completed=False
			for c in download.data_chunks:
				c.delete()
				
		download.user = user
		download.url = url
		download.format = format
		download.put()
		logging.info('Creating adapter...')
		
		try:
			if url.find('fictionalley') != -1:
				adapter = fictionalley.FictionAlley(url)
			elif url.find('ficwad') != -1:
				adapter = ficwad.FicWad(url)
			elif url.find('fanfiction.net') != -1:
				adapter = ffnet.FFNet(url)
			elif url.find('fictionpress.com') != -1:
				adapter = fpcom.FPCom(url)
			elif url.find('harrypotterfanfiction.com') != -1:
				adapter = hpfiction.HPFiction(url)
			elif url.find('twilighted.net') != -1:
				adapter = twilighted.Twilighted(url)
			elif url.find('adastrafanfic.com') != -1:
				adapter = adastrafanfic.Adastrafanfic(url)
			elif url.find('whofic.com') != -1:
				adapter = whofic.Whofic(url)
			elif url.find('potionsandsnitches.net') != -1:
				adapter = potionsNsnitches.PotionsNSnitches(url)
			elif url.find('mediaminer.org') != -1:
				adapter = mediaminer.MediaMiner(url)
			else:
				logging.debug("Bad URL detected")
				download.failure = url +" is not a valid story URL."
				download.put()
				return
		except Exception, e:
			logging.exception(e)
			download.failure = "Adapter was not created: " + str(e)
			download.put()
			return
		
		logging.info('Created an adaper: %s' % adapter)
		
		if len(login) > 1:
			adapter.setLogin(login)
			adapter.setPassword(password)

		if format == 'epub':
			writerClass = output.EPubFanficWriter
		elif format == 'html':
			writerClass = output.HTMLWriter
		elif format == 'mobi':
			writerClass = output.MobiWriter
		else:
			writerClass = output.TextWriter
		
		loader = FanficLoader(adapter,
				      writerClass,
				      quiet = True,
				      inmemory=True,
				      compress=False)
		try:
			data = loader.download()
			
			if format == 'html' or format == 'text':
				# data is uncompressed hence huge
				ext = '.html'
				if format == 'text':
					ext = '.txt'
				logging.debug(data)
				files = {makeAcceptableFilename(str(adapter.getOutputName())) + ext : StringIO.StringIO(data.decode('utf-8')) }
				d = inMemoryZip(files)
				data = d.getvalue()
			
		
		except LoginRequiredException, e:
			logging.exception(e)
			download.failure = 'Login problem detected'
			download.put()
			return
		except Exception, e:
			logging.exception(e)
			download.failure = 'Some exception happened in downloader: ' + str(e) 
			download.put()
			return
			
		if data == None:
			if loader.badLogin:
				logging.debug("Bad login detected")
				download.failure = 'Login failed'
				download.put()
				return
			download.failure = 'No data returned by adaptor'
			download.put()
		else:
			download.name = self._printableVersion(adapter.getOutputName())
			download.title = self._printableVersion(adapter.getStoryName())
			download.author = self._printableVersion(adapter.getAuthorName())
			download.put()
			index=0

			# epub, txt and html are all already compressed.
			# Each chunk is compressed individually to avoid having
			# to hold the whole in memory just for the
			# compress/uncompress.
			if format == 'mobi':
				def c(data):
					return zlib.compress(data)
			else:
				def c(data):
					return data
				
			while( len(data) > 0 ):
				DownloadData(download=download,
					     index=index,
					     blob=c(data[:1000000])).put()
				index += 1
				data = data[1000000:]
			download.completed=True
			download.put()
			
			logging.info("Download finished OK")
		return
				
def toPercentDecimal(match): 
	"Return the %decimal number for the character for url escaping"
	s = match.group(1)
	return "%%%02x" % ord(s)

def urlEscape(data):
	"Escape text, including unicode, for use in URLs"
	p = re.compile(r'([^\w])')
	return p.sub(toPercentDecimal, data.encode("utf-8"))

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
					('/fdowntask', FanfictionDownloaderTask),
					('/fdown', FanfictionDownloader),
					('/file', FileServer),
					('/status', FileStatusServer),
					('/recent', RecentFilesServer),
					('/r2d2', RecentAllFilesServer),
					('/login', LoginRequired)],
                                       debug=False)
  util.run_wsgi_app(application)


if __name__ == '__main__':
	logging.getLogger().setLevel(logging.DEBUG)
	main()
