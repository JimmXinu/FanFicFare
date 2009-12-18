# -*- coding: utf-8 -*-

import os
import re
import sys
import cgi
import uuid
import shutil
import base64
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

class HPFiction(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		self.opener = u2.build_opener(u2.HTTPCookieProcessor())
	
		logging.debug("Created HPFiction: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def requiresLogin(self, url = None):
		return False

	def performLogin(self, url = None):
		return True
	
	def extractIndividualUrls(self):
		data = self.opener.open(self.url).read()
		soup = bs.BeautifulSoup(data)
		
		links = soup.findAll('a')
		
		for a in links:
			if a['href'].find('psid') != -1:
				self.storyName = a.string
			elif a['href'].find('viewuser.php') != -1:
				self.authorName = a.string
		
		select = soup.find('select', {'name' : 'chapterid'})
		urls = []
		for o in select.findAll('option'):
			if 'value' in o._getAttrMap():
				url = 'http://' + self.host + '/' + self.path + o['value']
				title = o.string
				urls.append((url,title))
		return urls

	def getStoryName(self):
		return self.storyName

	def getAuthorName(self):
		return self.authorName
	
	def getText(self, url):
		logging.debug('Downloading from URL: %s' % url)
		data = self.opener.open(self.url).read()
		soup = bs.BeautifulSoup(data)
		divtext = soup.find('div', {'id' : 'fluidtext'})
		return divtext.prettify()

class FF_UnitTests(unittest.TestCase):
	def setUp(self):
		logging.basicConfig(level=logging.DEBUG)
		pass

	def testChaptersAuthStory(self):
		f = HPFiction('http://www.harrypotterfanfiction.com/viewstory.php?chapterid=80123')
		urls = f.extractIndividualUrls()
		
		self.assertEquals(49, len(urls))
		self.assertEquals('Elisha', f.getAuthorName())
		self.assertEquals('A Secret Thought', f.getStoryName())
	
	def testGetText(self):
		url = 'http://www.harrypotterfanfiction.com/viewstory.php?chapterid=80123'
		f = HPFiction(url)
		#urls = f.extractIndividualUrls()
		text = f.getText(url)
		self.assertTrue(text.find('She pulled out of his arms and felt the subtle regret') != -1)

if __name__ == '__main__':
	unittest.main()

	