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
	
		self.storyDescription = 'Fanfiction Story'
		self.authorId = '0'
		self.authorURL = ''
		(u1, self.storyId) = self.url.split('=')
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
		self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
		logging.debug('self.uuid=%s' % self.uuid)
		
		logging.debug("Created HPFiction: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def requiresLogin(self, url = None):
		return False

	def performLogin(self, url = None):
		return True
	
	def _addSubject(self, subject):
		subj = subject.upper()
		for s in self.subjects:
			if s.upper() == subj:
				return False
		self.subjects.append(subject)
		return True

	def _addCharacter(self, character):
		chara = character.upper()
		for c in self.storyCharacters:
			if c.upper() == chara:
				return False
		self.storyCharacters.append(character)
		return True

	def extractIndividualUrls(self):
		data = self.opener.open(self.url).read()
		soup = bs.BeautifulSoup(data)
		
		links = soup.findAll('a')
		def_chapurl = ''
		def_chaptitle = ''
		
		for a in links:
			if a['href'].find('psid') != -1:
				self.storyName = a.string
				logging.debug('self.storyName=%s' % self.storyName)
			elif a['href'].find('viewuser.php') != -1:
				self.authorName = a.string
				self.authorURL = 'http://' + self.host + '/' + a['href']
				(u1, self.authorId) = a['href'].split('=')
				logging.debug('self.authorName=%s, self.authorId=%s' % (self.authorName, self.authorId))
			elif a['href'].find('chapterid=') != -1 and len(def_chapurl) == 0:
				def_chapurl = 'http://' + self.host + '/viewstory.php' + str(a['href'])
				def_chaptitle = a.string
				logging.debug('def_chapurl=%s, def_chaptitle=%s' % (def_chapurl, def_chaptitle))
		
		centers = soup.findAll('center')
		for center in centers:
			tds = center.findAll ('td')
			if tds is not None and len(tds) > 0:
				for td in tds:
					s = re.split ("<[^>]+>", str(td).replace('\n','').replace('&nbsp;',' '))
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
									self._addCharacter(ss2)
								logging.debug('self.storyCharacters=%s' % self.storyCharacters)
								ii = ii + 2
							elif s[ii] == 'Genre(s):':
								self.genre = s[ii+1]
								logging.debug('self.genre=%s' % self.genre)
								s2 = s[ii+1].split(', ')
								for ss2 in s2:
									self._addSubject(ss2)
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
					logging.debug('self.storyDescription=%s' % self.storyDescription)
		
		urls = []
		self.outputName = self.storyName.replace(" ", "_") + '-hp_' + self.storyId

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

		self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
		logging.debug('self.uuid=%s' % self.uuid)
		
		return urls

	def getStoryName(self):
		return self.storyName

	def getOutputName(self):
		return self.outputName
		
	def getAuthorName(self):
		return self.authorName
	
	def getText(self, url):
		logging.debug('Downloading from URL: %s' % url)
		data = self.opener.open(url).read()
		soup = bs.BeautifulSoup(data)
		divtext = soup.find('div', {'id' : 'fluidtext'})
		if None == divtext:
			logging.error("Error downloading Chapter: %s" % url)
			exit(20)
		return divtext.__str__('utf8')

	def getAuthorId(self):
		logging.debug('self.authorId=%s' % self.authorId)
		return self.authorId

	def getStoryId(self):
		logging.debug('self.storyId=%s' % self.storyId)
		return self.storyId

	def getStoryDescription(self):
		logging.debug('self.storyDescription=%s' % self.storyDescription)
		return self.storyDescription

	def getStoryPublished(self):
		logging.debug('self.storyPublished=%s' % self.storyPublished)
		return self.storyPublished

	def getStoryCreated(self):
		self.storyCreated = datetime.datetime.now()
		logging.debug('self.storyCreated=%s' % self.storyCreated)
		return self.storyCreated

	def getStoryUpdated(self):
		logging.debug('self.storyUpdated=%s' % self.storyUpdated)
		return self.storyUpdated

	def getLanguage(self):
		logging.debug('self.language=%s' % self.language)
		return self.language

	def getLanguageId(self):
		logging.debug('self.languageId=%s' % self.languageId)
		return self.languageId

	def getSubjects(self):
		logging.debug('self.subjects=%s' % self.authorName)
		return self.subjects

	def getPublisher(self):
		logging.debug('self.publisher=%s' % self.publisher)
		return self.publisher

	def getNumChapters(self):
		logging.debug('self.numChapters=%s' % self.numChapters)
		return self.numChapters

	def getNumWords(self):
		logging.debug('self.numWords=%s' % self.numWords)
		return self.numWords

	def getStoryURL(self):
		logging.debug('self.url=%s' % self.url)
		return self.url

	def getAuthorURL(self):
		logging.debug('self.authorURL=%s' % self.authorURL)
		return self.authorURL

	def getUUID(self):
		logging.debug('self.uuid=%s' % self.uuid)
		return self.uuid

	def getCategory(self):
		logging.debug('self.category=%s' % self.category)
		return self.category

	def getGenre(self):
		logging.debug('self.genre=%s' % self.genre)
		return self.genre

	def getStoryStatus(self):
		logging.debug('self.storyStatus=%s' % self.storyStatus)
		return self.storyStatus

	def getStoryRating(self):
		logging.debug('self.storyRating=%s' % self.storyRating)
		return self.storyRating

	def getStoryUserRating(self):
		logging.debug('self.storyUserRating=%s' % self.storyUserRating)
		return self.storyUserRating

	def getStoryCharacters(self):
		logging.debug('self.storyCharacters=%s' % self.storyCharacters)
		return self.storyCharacters
	
	def getStorySeries(self):
		logging.debug('self.storySeries=%s' % self.storySeries)
		return self.storySeries
		


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

	
