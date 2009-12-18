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

class FFA(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		self.opener = u2.build_opener(u2.HTTPCookieProcessor())
	
		logging.debug("Created FFA: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def requiresLogin(self, url = None):
		resp = self.opener.open(self.url)
		data = resp.read()
		if data.find('<legend>Please login to continue</legend>') != -1:
			return True
		else:
			return False
 
	def performLogin(self, url = None):
		if url == None:
			url = self.url
		
		data = {}
		
		data['username'] = self.login
		data['password'] = self.password
		data['submit'] = 'Submit'
		
		urlvals = u.urlencode(data)
		loginUrl = 'http://' + self.host + self._getLoginScript()
		logging.debug("Will now login to URL %s" % loginUrl)
		
		req = self.opener.open(loginUrl, urlvals)
		
		if self.requiresLogin():
			return False
		else:
			return True
	
	def extractIndividualUrls(self):
		data = self.opener.open(self.url).read()
		soup = bs.BeautifulStoneSoup(data)

		self.author = soup.find('a', {'href' : '/contact/'}).string
		self.storyName = str(soup.find('h1', {'class' : 'textCenter'}).contents[0]).strip()
		
		logging.debug("Story `%s` by `%s`" % (self.storyName, self.author))
		
		selector = soup.find('select', {'class' : 'tinput'})
		options = selector.findAll('option')
		
		urls = []
		
		for o in options:
			title = o.string
			url = o['value']
			
			urls.append((url,title))
		
		return urls

	def getText(self, url):
		if url.find('http://') == -1:
			url = 'http://' + self.host + '/' + url
		
		logging.info('Downloading: %s' % url)
		data = self.opener.open(url).read()
		
		lines = data.split('\n')
		
		emit = False
		
		post = ''
		
		for l in lines:
			if l.find('</div></form>') != -1:
				logging.debug('emit = True')
				emit = True
				continue
			elif l.find('<form action="#">') != -1:
				logging.debug('emit = False')
				if emit:
					break
				else:
					emit = False
			
			if emit:
				post = post + l + '\n'
		
		return post

	def setLogin(self, login):
		self.login = login

	def setPassword(self, password):
		self.password = password
	
	def getStoryName(self):
		return self.storyName
		
	def getAuthorName(self):
		return self.author

	def getPrintableUrl(self, url):
		return url

class FFA_UnitTests(unittest.TestCase):
	def setUp(self):
		logging.basicConfig(level=logging.DEBUG)
		pass
	
	def testRequiresLoginNeg(self):
		f = FFA('http://jeconais.fanficauthors.net/Happily_Ever_After/Introduction/')
		self.assertFalse(f.requiresLogin())
	
	def testRequiresLogin(self):
		f = FFA('http://jeconais.fanficauthors.net/Rons_Harem/Rons_Harem/')
		self.assertTrue(f.requiresLogin())
	
	def testPerformLogin(self):
		f = FFA('http://jeconais.fanficauthors.net/Rons_Harem/Rons_Harem/')
		
		if login_password != None:
			f.setLogin(login_password.login)
			f.setPassword(login_password.password)
		
		self.assertTrue(f.performLogin(None))
		
	def testExtractURLsAuthorStoryName(self):
		f = FFA('http://draco664.fanficauthors.net/Apprentice_Potter/Prologue/')
		f.extractIndividualUrls()
		
		self.assertEquals('Draco664', f.getAuthorName())
		self.assertEquals('Apprentice Potter', f.getStoryName())
	
	def testExtractUrls(self):
		f = FFA('http://draco664.fanficauthors.net/Apprentice_Potter/Prologue/')
		urls = f.extractIndividualUrls()
		self.assertEquals(25, len(urls))
		
		self.assertEquals('Grievances', urls[2][1])
		self.assertEquals('/Apprentice_Potter/Prologue/', urls[0][0])
	
	def testGetText(self):
		f = FFA('http://jeconais.fanficauthors.net/Happily_Ever_After/Introduction/')
		data = f.getText('http://jeconais.fanficauthors.net/Happily_Ever_After/Introduction/')
		
		self.assertTrue(data.find('smiled slightly, and settled back in her rocking chair') != -1)
		
	def testGetTextLogin(self):
		url = 'http://viridian.fanficauthors.net/Out_of_the_Darkness_A_Jinchuurikis_Tale/A_Harrowing_Escape/'
		f = FFA(url)
		
		if login_password != None:
			f.setLogin(login_password.login)
			f.setPassword(login_password.password)
		
		if f.requiresLogin():
			f.performLogin()
		
		data = f.getText(url)
		seek = 'So Hokage-sama” I said, “this is how we came'
		self.assertTrue(data.find(seek) != -1)
		
if __name__ == '__main__':
	unittest.main()