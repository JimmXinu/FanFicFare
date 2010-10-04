# -*- coding: utf-8 -*-

import os
import re
import sys
import cgi
import uuid
import shutil
import os.path
import logging
import unittest
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs

from constants import *
from adapter import *

try:
	import login_password
except:
	# tough luck
	pass

try:
	from google.appengine.api.urlfetch import fetch as googlefetch
	appEngine = True
except:
	appEngine = False

class FFNet(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		self.storyName = 'FF.Net story'
		self.authorName = 'FF.Net author'
		
		spl = self.path.split('/')
		if len(spl) == 5:
			self.path = "/".join(spl[1:-1])
		
		if self.path.startswith('/'):
			self.path = self.path[1:]
		
		if self.path.endswith('/'):
			self.path = self.path[:-1]
		
		(s, self.storyId, chapter) = self.path.split('/')
		
		logging.debug('self.storyId=%s, chapter=%s' % (self.storyId, chapter))
		
		if not appEngine:
			self.opener = u2.build_opener(u2.HTTPCookieProcessor())
		else:
			self.opener = None
	
		logging.debug("Created FF.Net: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def requiresLogin(self, url = None):
		return False

	def performLogin(self, url = None):
		return True
	
	def _fetchUrl(self, url):
		if not appEngine:
			return self.opener.open(url).read().decode('utf-8')
		else:
			return googlefetch(url).content
	
	def extractIndividualUrls(self):
		data = self._fetchUrl(self.url)
		d2 = re.sub('&\#[0-9]+;', ' ', data)
		soup = bs.BeautifulStoneSoup(d2)
		allA = soup.findAll('a')
		for a in allA:
			if 'href' in a._getAttrMap() and a['href'].find('/u/') != -1:
				self.authorName = a.string

		urls = []
		lines = data.split('\n')
		for l in lines:
			if l.find("&#187;") != -1 and l.find('<b>') != -1:
				s2 = bs.BeautifulStoneSoup(l)
				self.storyName = str(s2.find('b').string)
			elif l.find("<a href='/u/") != -1:
				s2 = bs.BeautifulStoneSoup(l)
				self.authorName = str(s2.a.string)
			elif l.find("<SELECT title='chapter navigation'") != -1:
				if len(urls) > 0:
					continue
				try:
					u = l.decode('utf-8')
				except UnicodeEncodeError, e:
					u = l
				u = re.sub('&\#[0-9]+;', ' ', u)
				s2 = bs.BeautifulSoup(u)
				options = s2.findAll('option')
				for o in options:
					url = 'http://' + self.host + '/s/' + self.storyId + '/' + o['value']
					title = o.string
					logging.debug('URL = `%s`, Title = `%s`' % (url, title))
					urls.append((url,title))
		if len(urls) == 0:
			# no chapters found, try url by itself.
			urls.append((self.url,self.storyName))
		return urls
	
	def getText(self, url):
		data = self._fetchUrl(url)
		lines = data.split('\n')
		
		textbuf = ''
		emit = False
		
		olddata = data
		try:
			data = data.decode('utf8')
		except:
			data = olddata
		
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			logging.info("Failed to decode: <%s>" % data)
			soup = None
		div = soup.find('div', {'id' : 'storytext'})
		if None == div:
			logging.error("Error downloading Chapter: %s" % url)
			exit(1)
			return '<html/>'
			
		return div.__str__('utf8')
		
	def setLogin(self, login):
		self.login = login

	def setPassword(self, password):
		self.password = password

	def getStoryName(self):
		return self.storyName

	def getAuthorName(self):
		return self.authorName

class FFA_UnitTests(unittest.TestCase):
	def setUp(self):
		logging.basicConfig(level=logging.DEBUG)
		pass
	
	def testChaptersAuthStory(self):
		f = FFNet('http://www.fanfiction.net/s/5257563/1')
		f.extractIndividualUrls()
		
		self.assertEquals('Beka0502', f.getAuthorName())
		self.assertEquals("Draco's Redemption", f.getStoryName())

	def testChaptersCountNames(self):
		f = FFNet('http://www.fanfiction.net/s/5257563/1')
		urls = f.extractIndividualUrls()
		
		self.assertEquals(10, len(urls))
	
	def testGetText(self):
		url = 'http://www.fanfiction.net/s/5257563/1'
		f = FFNet(url)
		text = f.getText(url)
		self.assertTrue(text.find('He was just about to look at some photos when he heard a crack') != -1)
	
	def testBrokenWands(self):
		url = 'http://www.fanfiction.net/s/1527263/30/Harry_Potter_and_Broken_Wands'
		f = FFNet(url)
		text = f.getText(url)
		
		urls = f.extractIndividualUrls()
	
	def testFictionPress(self):
		url = 'http://www.fictionpress.com/s/2725180/1/Behind_This_Facade'
		f = FFNet(url)
		urls = f.extractIndividualUrls()
		
		self.assertEquals('Behind This Facade', f.getStoryName())
		self.assertEquals('IntoxicatingMelody', f.getAuthorName())
	
		text = f.getText(url)
		self.assertTrue(text.find('Kale Resgerald at your service" He answered, "So, can we go now? Or do you want to') != -1)
if __name__ == '__main__':
	unittest.main()