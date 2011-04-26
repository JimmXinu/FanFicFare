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
import time
import datetime

from constants import *
from adapter import *

try:
	import login_password
except:
	# tough luck
	pass

class FFNet(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		self.storyName = 'FF.Net story'
		self.authorName = 'FF.Net author'
		self.storyDescription = 'Fanfiction Story'
		self.storyCharacters = []
		self.storySeries = ''
		self.authorId = '0'
		self.authorURL = self.path
		self.storyId = '0'
		self.storyPublished = datetime.date(1970, 01, 31)
		self.storyCreated = datetime.datetime.now()
		self.storyUpdated = datetime.date(1970, 01, 31)
		self.languageId = 'en-UK'
		self.language = 'English'
		self.subjects = []
		self.subjects.append ('FanFiction')
		logging.debug('self.subjects=%s' % self.subjects)
		self.publisher = self.host
		self.numChapters = 0
		self.numWords = 0
		self.genre = 'FanFiction'
		self.category = 'FF.Net Category'
		self.storyStatus = 'In-Progress'
		self.storyRating = 'K'
		self.storyUserRating = '0'
		self.outputName = ''
		self.outputStorySep = '-ffnet_'
		
		logging.debug('self.path=%s' % self.path)

		if self.path.startswith('/'):
			self.path = self.path[1:]
		
		spl = self.path.split('/')
		logging.debug('spl=%s' % spl)
		if spl is not None:
			if len(spl) > 0 and spl[0] != 's':
				raise InvalidStoryURL("Error URL \"%s\" is not a story." % self.url)
			if len(spl) > 1:
				self.storyId = spl[1]
			if len(spl) > 2:
				chapter = spl[1]
			else:
				chapter = '1'
			if len(spl) == 5:
				self.path = "/".join(spl[1:-1])
		
		if self.path.endswith('/'):
			self.path = self.path[:-1]
		
		logging.debug('self.path=%s' % self.path)
		
		if self.host is not None and self.host == "m.fanfiction.net":
			self.host = "www.fanfiction.net"
			logging.debug('self.host=%s' % self.host)
			self.url = "http://" + self.host + "/" + self.path
			logging.debug('self.url=%s' % self.url)
			
		logging.debug('self.storyId=%s' % self.storyId)
		if not self.appEngine:
			self.opener = u2.build_opener(u2.HTTPCookieProcessor())
		else:
			self.opener = None
	
		logging.debug("Created FF.Net: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def _getVarValue(self, varstr):
		#logging.debug('_getVarValue varstr=%s' % varstr)
		vals = varstr.split('=')
		#logging.debug('vals=%s' % vals)
		retstr="".join(vals[+1:])
		#logging.debug('retstr=%s' % retstr)
		if retstr.startswith(' '):
			retstr = retstr[1:]
		if retstr.endswith(';'):
			retstr = retstr[:-1]
		return retstr
	
	def _splitCrossover(self, subject):
		if "Crossover" in subject:
			self.addSubject ("Crossover")
			logging.debug('Crossover=%s' % subject)
			if subject.find(' and ') != -1:
				words = subject.split(' ')
				logging.debug('words=%s' % words)
				subj = ''
				for s in words:
					if s in "and Crossover":
						if len(subj) > 0:
							self.addSubject(subj)
						subj = ''
					else:
						if len(subj) > 0:
							subj = subj + ' '
						subj = subj + s
				if len(subj) > 0:
					self.addSubject(subj)
			else:
				self.addSubject(subject)
		else:
			self.addSubject(subject)
		return True

	def _splitGenre(self, subject):
		if len(subject) > 0:
			words = subject.split('/')
			logging.debug('words=%s' % words)
			for subj in words:
			    if len(subj) > 0:
				self.addSubject(subj)
		return True

	def extractIndividualUrls(self):
		data = ''
		try:
			data = self.fetchUrl(self.url)
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + self.url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise StoryDoesNotExist("Problem reading story URL " + self.url + "!")
		
		d2 = re.sub('&\#[0-9]+;', ' ', data)
		soup = None
		try:
			soup = bs.BeautifulStoneSoup(d2)
		except:
			logging.error("Failed to decode: <%s>" % d2)
			raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % self.url)

		allA = soup.findAll('a')
		for a in allA:
			if 'href' in a._getAttrMap() and a['href'].find('/u/') != -1:
				self.authorName = a.string
				(u1, u2, self.authorId, u3) = a['href'].split('/')
				logging.debug('self.authorId=%s self.authorName=%s' % (self.authorId, self.authorName))

		urls = []
		lines = data.split('\n')
		for l in lines:
			if l.find("&#187;") != -1 and l.find('<b>') != -1:
				s2 = bs.BeautifulStoneSoup(l)
				self.storyName = unicode(s2.find('b').string)
				logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
			elif l.find("<a href='/u/") != -1:
				s2 = bs.BeautifulStoneSoup(l)
				self.authorName = unicode(s2.a.string)
				(u1, u2, self.authorId, u3) = s2.a['href'].split('/')
				logging.debug('self.authorId=%s, self.authorName=%s' % (self.authorId, self.authorName))
			elif l.find("Rated: <a href=") != -1:
				if "Complete" in l:
					self.storyStatus = 'Completed'
				else:
					self.storyStatus = 'In-Progress'
				
				s2 = bs.BeautifulStoneSoup(l)
				self.storyRating = unicode(s2.a.string).strip()
				logging.debug('self.storyRating=%s' % self.storyRating)
				logging.debug('s2.a=%s' % s2.a)
				s3 = l.split(' - ')
				logging.debug('s3=%s' % s3)
				if len(s3) > 0:
					if s3[1].find("Reviews: <a href=") != -1:
						continue
					self.language = s3[1].strip()
					logging.debug('self.language=%s' % self.language)
					if len(s3) > 1:
						if s3[2].find("Reviews: <a href=") != -1:
							continue
						self.genre = s3[2].strip()
						if "&" in self.genre:
							self.genre = ''
							continue
						logging.debug('self.genre=%s' % self.genre)
						self._splitGenre(self.genre)
						logging.debug('self.subjects=%s' % self.subjects)
			elif l.find("<SELECT title='chapter navigation'") != -1:
				if len(urls) > 0:
					continue
				try:
					u = l.decode('utf-8')
				except UnicodeEncodeError, e:
					u = l
				except:
					u = l.encode('ascii', 'xmlcharrefreplace')
				u = re.sub('&\#[0-9]+;', ' ', u)
				s2 = bs.BeautifulSoup(u)
				options = s2.findAll('option')
				for o in options:
					url = 'http://' + self.host + '/s/' + self.storyId + '/' + o['value']
					title = o.string
					logging.debug('URL = `%s`, Title = `%s`' % (url, title))
					urls.append((url,title))
			elif l.find("var chapters") != -1:
				self.numChapters = self._getVarValue (l)
				logging.debug('self.numChapters=%s' % self.numChapters)
			elif l.find("var words") != -1:
				self.numWords = self._getVarValue (l)
				logging.debug('self.numWords=%s' % self.numWords)
			elif l.find("var categoryid") != -1:
				categoryid = self._getVarValue (l)
				logging.debug('categoryid=%s' % categoryid)
			elif l.find("var cat_title") != -1:
				self.category = self._getVarValue (l).strip("'")
				logging.debug('self.category=%s' % self.category)
				self._splitCrossover(self.category)
				logging.debug('self.subjects=%s' % self.subjects)
			elif l.find("var summary") != -1:
				self.storyDescription = self._getVarValue (l).strip("'")
				if '&' in self.storyDescription:
					s = self.storyDescription.split('&')
					logging.debug('s=%s' % s)
					self.storyDescription = ''
					for ss in s:
						if len(self.storyDescription) > 0:
							if len(ss) > 4 and 'amp;' in ss[1:4]:
								self.storyDescription = self.storyDescription + '&' + ss
							else:
								self.storyDescription = self.storyDescription + '&amp;' + ss
						else:
							self.storyDescription = ss
				logging.debug('self.storyDescription=%s' % self.storyDescription.replace('\n',' ').replace('\r',''))
			elif l.find("var datep") != -1:
				dateps = self._getVarValue (l)
				self.storyPublished = datetime.datetime(*time.strptime ( dateps, "'%m-%d-%y'" )[0:5])
				logging.debug('self.storyPublished=%s' % self.storyPublished.strftime("%Y-%m-%dT%I:%M:%S"))
			elif l.find("var dateu") != -1:
				dateus = self._getVarValue (l)
				self.storyUpdated = datetime.datetime(*time.strptime ( dateus, "'%m-%d-%y'" )[0:5])
				logging.debug('self.storyUpdated=%s' % self.storyUpdated.strftime("%Y-%m-%dT%I:%M:%S"))

		if len(urls) <= 0:
			# no chapters found, try url by itself.
			urls.append((self.url,self.storyName))

		self.authorURL = 'http://' + self.host + '/u/' + self.authorId

		#logging.debug('urls=%s' % urls)
		return urls
	
	def getText(self, url):
		data = None

		# try up to three times, with longer sleeps first.
		for sleeptime in [0.5, 4, 9]:
			time.sleep(sleeptime)	
			try:
				logging.debug("Fetching URL: %s sleeptime: %f" % (url, sleeptime))
				data = self.fetchUrl(url)
				if data is not None:
					break
			except Exception, e:
				logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
				logging.error("Data downloaded: <%s>" % data)

		if data is None:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)

		lines = data.split('\n')

		textbuf = ''
		emit = False

		olddata = data
		try:
			data = data.decode('utf8')
		except:
			data = olddata
		
		soup = None
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			logging.debug(data)
			raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)

		div = soup.find('div', {'id' : 'storytext'})
		if None == div:
			if "Story Not Found" in data:
				logging.info("Story not Found at %s" % url)
				raise FailedToDownload("Story not Found at %s" % url)
			logging.debug(data)
			raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
			
		return div.__str__('utf8')
					
		
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
