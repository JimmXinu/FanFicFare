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

class HPFiction(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		logging.debug('self.url=%s' % self.url)
		logging.debug('self.host=%s' % self.host)
		logging.debug('self.path=%s' % self.path)
	
		self.opener = u2.build_opener(u2.HTTPCookieProcessor())

		self.chapurl = False
		self.storyId = '0'
		
		sss = self.url.split('?')
		logging.debug('sss=%s' % sss)
		if sss is not None and len(sss) > 1:
			sc = sss[1].split('=')
			logging.debug('sc=%s' % sc)
			if sc is not None and len(sc) > 1:
				if sc[0] == 'chapterid':
					self.chapurl = True
				elif sc[0] == 'psid' or sc[0] == 'sid':
					self.storyId = sc[1]

		self.storyDescription = 'Fanfiction Story'
		self.authorId = '0'
		self.authorURL = ''
		self.storyPublished = datetime.date(1970, 01, 31)
		self.storyCreated = datetime.datetime.now()
		self.storyUpdated = datetime.date(1970, 01, 31)
		self.languageId = 'en-UK'
		self.language = 'English'
		self.subjects = []
		self.subjects.append ('fanfiction')
		self.subjects.append ('Harry Potter')
		self.publisher = self.host
		self.numChapters = 0
		self.numWords = 0
		self.genre = 'FanFiction'
		self.category = 'Category'
		self.storyStatus = 'In-Progress'
		self.storyRating = 'K'
		self.storyUserRating = '0'
		self.storyCharacters = []
		self.storySeries = ''
		self.outputName = ''
		self.outputStorySep = '-hp_'
		
		logging.debug("Created HPFiction: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path
	
	def extractIndividualUrls(self):
		data = ''
		try:
			data = self.opener.open(self.url).read()
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + self.url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise StoryDoesNotExist("Problem reading story URL " + self.url + "!")
		
		soup = None
		try:
			soup = bs.BeautifulSoup(data)
		except:
			raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % self.url)
				
		links = soup.findAll('a')
		def_chapurl = ''
		def_chaptitle = ''
		
		if self.chapurl:
			foundid = False
			for a in links:
				if a['href'].find('psid') != -1:
					sp = a['href'].split('?')
					if sp is not None and len(sp) > 1:
						for sp1 in sp:
							if sp1.find('psid') != -1:
								ps = sp1.split('=')
								if ps is not None and len(ps) > 1:
									self.storyId = ps[1].replace('\'','')
									foundid = True
					self.storyName = a.string
					logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
					break
			if foundid:
				self.url = "http://" + self.host + "/viewstory.php?psid=" + self.storyId
				logging.debug('Title Page URL=%s' % self.url)
				data1 = self.opener.open(self.url).read()
				hdrsoup = bs.BeautifulSoup(data1)
			else:
				hdrsoup = soup
		else:
			hdrsoup = soup
			
		for a in links:
			if not self.chapurl and a['href'].find('psid') != -1:
				sp = a['href'].split('?')
				if sp is not None and len(sp) > 1:
					for sp1 in sp:
						if sp1.find('psid') != -1:
							ps = sp1.split('=')
							if ps is not None and len(ps) > 1:
								self.storyId = ps[1].replace('\'','')
				self.storyName = a.string
				logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
			elif a['href'].find('viewuser.php') != -1:
				self.authorName = a.string
				self.authorURL = 'http://' + self.host + '/' + a['href']
				(u1, self.authorId) = a['href'].split('=')
				logging.debug('self.authorName=%s, self.authorId=%s' % (self.authorName, self.authorId))
			elif a['href'].find('chapterid=') != -1 and len(def_chapurl) == 0:
				def_chapurl = 'http://' + self.host + '/viewstory.php' + unicode(a['href'])
				def_chaptitle = a.string
				logging.debug('def_chapurl=%s, def_chaptitle=%s' % (def_chapurl, def_chaptitle))
		
		centers = hdrsoup.findAll('center')
		for center in centers:
			tds = center.findAll ('td')
			if tds is not None and len(tds) > 0:
				for td in tds:
					s = re.split ("<[^>]+>", unicode(td).replace('\n','').replace('&nbsp;',' '))
					ii = 0
					ll = len(s)
					sss = ''
					while ii < ll - 1:
						if s[ii] is not None and len(s[ii]) > 0:
							if s[ii] == 'Rating:':
								self.storyRating = s[ii+1]
								logging.debug('self.storyRating=%s' % self.storyRating)
								ii = ii + 2
							elif s[ii] == 'Chapters:':
								self.numChapters = s[ii+1]
								logging.debug('self.numChapters=%s' % self.numChapters)
								ii = ii + 2
							elif s[ii] == 'Characters:':
								s2 = s[ii+1].split(', ')
								for ss2 in s2:
									self.addCharacter(ss2)
								logging.debug('self.storyCharacters=%s' % self.storyCharacters)
								ii = ii + 2
							elif s[ii] == 'Genre(s):':
								self.genre = s[ii+1]
								logging.debug('self.genre=%s' % self.genre)
								s2 = s[ii+1].split(', ')
								for ss2 in s2:
									self.addSubject(ss2)
								logging.debug('self.subjects=%s' % self.subjects)
								ii = ii + 2
							elif s[ii] == 'Status:':
								if s[ii+1].strip(' ') == "Work In Progress":
									self.storyStatus = 'In-Progress'
								else:
									self.storyStatus = 'Completed'
								ii = ii + 2
							elif s[ii] == 'First Published:':
								self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s[ii+1].strip(' '), "%Y.%m.%d")))
								logging.debug('self.storyPublished=%s' % self.storyPublished)
								ii = ii + 2
							elif s[ii] == 'Last Updated:':
								self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s[ii+1].strip(' '), "%Y.%m.%d")))
								logging.debug('self.storyUpdated=%s' % self.storyUpdated)
								ii = ii + 2
							elif s[ii] == 'Last Published Chapter:':
								ii = ii + 2
							elif s[ii] == 'Pairings:':
								ii = ii + 2
							elif s[ii] == 'Warnings:':
								ii = ii + 2
							else:
								sss = sss + ' ' + s[ii]
								ii = ii + 1
						else:
							ii = ii + 1
					self.storyDescription = sss
					logging.debug('self.storyDescription=%s' % self.storyDescription.replace("\n"," ").replace('\r',''))
		
		urls = []

		select = soup.find('select', {'name' : 'chapterid'})
		if select is None:
			# no chapters found, try url by itself.
			if len(def_chapurl) > 0:
				urls.append((def_chapurl, def_chaptitle))
			else:
				urls.append((self.url,self.storyName))
		else:
			for o in select.findAll('option'):
				if 'value' in o._getAttrMap():
					url = 'http://' + self.host + self.path + o['value']
					title = o.string
					if title != "Story Index":
						urls.append((url,title))

		return urls

	def getText(self, url):
		logging.debug('Downloading from URL: %s' % url)
		data = ''
		try:
			data = self.opener.open(url).read()
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)
		
		soup = None
		try:
			soup = bs.BeautifulSoup(data)
		except:
			logging.info("Failed to decode: <%s>" % data)
			raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
		
		divtext = soup.find('div', {'id' : 'fluidtext'})
		if None == divtext:
			raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

		return divtext.__str__('utf8')


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

	
