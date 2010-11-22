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
import logging
import traceback
import StringIO

from google.appengine.runtime import DeadlineExceededError

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from fanficdownloader.downloader import *
from fanficdownloader.ffnet import *
from fanficdownloader.output import *
from fanficdownloader import twilighted

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
		
		self.response.out.write(fanfic.blob)

class RecentFilesServer(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if not user:
			self.redirect('/login')
		
#		fics = db.GqlQuery("Select * From DownloadedFanfic WHERE user = :1 and cleared = :2", user)
		q = DownloadedFanfic.all()
		q.filter('user =', user)
		q.filter('cleared =', False)
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
	def _printableVersion(self, text):
		text = removeEntities(text)
		try:
			d = text.decode('utf-8')
		except:
			d = text
		return d
	

	def post(self):
		logging.getLogger().setLevel(logging.DEBUG)
		
		user = users.get_current_user()
		if not user:
			self.redirect(users.create_login_url('/'))
		
		format = self.request.get('format')
		url = self.request.get('url')
		login = self.request.get('login')
		password = self.request.get('password')
		
		logging.info("Downloading: " + url)
		
		adapter = None
		writerClass = None

		download = OneDownload()
		download.user = user
		download.url = url
		download.login = login
		download.password = password
		download.format = format
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
			elif url.find('potionsandsnitches.net') != -1:
				adapter = potionsNsnitches.PotionsNSnitches(url)
			elif url.find('mediaminer.org') != -1:
				adapter = mediaminer.MediaMiner(url)
			else:
				logging.debug("Bad URL detected")
				self.redirect('/?error=bad_url&url=' + urlEscape(url) )
				return
		except Exception, e:
			logging.exception(e)
			download.failure = "Adapter was not created: " + str(e)
			download.put()
			
			self.redirect('/?error=custom&url=' + urlEscape(url) + '&errtext=' + urlEscape(str(traceback.format_exc())) )
			return
		
		logging.info('Created an adaper: %s' % adapter)
		
		if len(login) > 1:
			adapter.setLogin(login)
			adapter.setPassword(password)

		if format == 'epub':
			writerClass = output.EPubFanficWriter
		elif format == 'html':
			writerClass = output.HTMLWriter
		else:
			writerClass = output.TextWriter
		
		loader = FanficLoader(adapter, writerClass, quiet = True, inmemory=True, compress=False)
		try:
			data = loader.download()
			
			if format == 'html' or format == 'text':
				# data is uncompressed hence huge
				ext = '.html'
				if format == 'text':
					ext = '.txt'
				files = {makeAcceptableFilename(str(adapter.getStoryName())) + ext : StringIO.StringIO(data.decode('utf-8')) }
				d = inMemoryZip(files)
				data = d.getvalue()
			
		
		except LoginRequiredException, e:
			logging.exception(e)
			download.failure = 'Login problem detected'
			download.put()
			
			self.redirect('/?error=login_required&url=' + urlEscape(url))
			return
		except:
			e = sys.exc_info()[0]
			
			logging.exception(e)
			download.failure = 'Some exception happened in downloader: ' + str(e)
			download.put()
			
			self.redirect('/?error=custom&url=' + urlEscape(url) + '&errtext=' + urlEscape(str(traceback.format_exc())) )
			return
			
		if data == None:
			if loader.badLogin:
				logging.debug("Bad login detected")
				
				download.failure = 'Login problem detected'
				download.put()
				
				self.redirect('/?error=login_required&url=' + urlEscape(url))
		else:
			fic = DownloadedFanfic()
			fic.user = user
			fic.url = url
			fic.format = format
			fic.name = self._printableVersion(adapter.getStoryName())
			fic.author = self._printableVersion(adapter.getAuthorName())
			fic.blob = data
			
			try:
				fic.put()
				
				key = fic.key()
				
				download.put()
				self.redirect('/?file='+str(key)+'&name=' + urlEscape(fic.name) + '&author=' + urlEscape(fic.author))
				
				logging.info("Download finished OK")
			except Exception, e:
				logging.exception(e)
				# it was too large, won't save it
				name = str(makeAcceptableFilename(adapter.getStoryName()))
				if format == 'epub':
					self.response.headers['Content-Type'] = 'application/epub+zip'
					self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.epub'
				elif format == 'html':
					self.response.headers['Content-Type'] = 'application/zip'
					self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.html.zip'
				elif format == 'text':
					self.response.headers['Content-Type'] = 'application/zip'
					self.response.headers['Content-disposition'] = 'attachment; filename=' + name + '.txt.zip'
				
				self.response.out.write(data)
				
def toPercentDecimal(match): 
	"Return the %decimal number for the character for url escaping"
	s = match.group(1)
	return "%%%02x" % ord(s)

def urlEscape(data):
	"Escape text, including unicode, for use in URLs"
	p = re.compile(r'([^\w])')
	return p.sub(toPercentDecimal, data.encode("utf-8"))

def main():
  application = webapp.WSGIApplication([('/', MainHandler), ('/fdown', FanfictionDownloader), ('/file', FileServer), ('/recent', RecentFilesServer), ('/r2d2', RecentAllFilesServer), ('/login', LoginRequired)],
                                       debug=False)
  util.run_wsgi_app(application)


if __name__ == '__main__':
	logging.getLogger().setLevel(logging.DEBUG)
	main()
