# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import os.path
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs
import logging
import time
import datetime

from adapter import *

class FicWad(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		self.host = up.urlparse(url).netloc
	
	def requiresLogin(self, url = None):
		return False
	
	def performLogin(self, url = None):
		pass
		
	def setLogin(self, login):
		self.login = login
	
	def setPassword(self, password):
		self.password = password
	
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
		self.storyDescription = 'Fanfiction Story'
		self.authorId = '0'
		self.storyId = '0'
		self.storyPublished = datetime.date(1970, 01, 31)
		self.storyCreated = datetime.datetime.now()
		self.storyUpdated = datetime.date(1970, 01, 31)
		self.languageId = 'en-UK'
		self.language = 'English'
		self.subjects = []
		self.subjects.append ('fanfiction')
		self.publisher = self.host
		self.numChapters = 0
		self.numWords = 0
		self.genre = 'FanFiction'
		self.category = 'Category'
		self.storyStatus = 'In-Progress'
		self.storyRating = 'PG'
		self.storyUserRating = '0'
		self.storyCharacters = []
		self.storySeries = ''
		oldurl = ''
		
		data = u2.urlopen(self.url).read()
		soup = bs.BeautifulStoneSoup(data)
		
		story = soup.find('div', {'id' : 'story'})
		crumbtrail = story.find('h3') # the only h3 ficwad uses.
		allAhrefs = crumbtrail.findAll('a')
		# last of crumbtrail
		storyinfo = allAhrefs[-1]
		(u0, u1, storyid) = storyinfo['href'].split('/')
		if u1 == "story":
			# This page does not have the correct information on it..  Need to get the Story Title Page
			logging.debug('URL %s is a chapter URL.  Getting Title Page http://%s/%s/%s.' % (self.url, self.host, u1, storyid))
			oldurl = self.url
			self.url = 'http://' + self.host + '/' + u1 + '/' + storyid
			data = u2.urlopen(self.url).read()
			soup = bs.BeautifulStoneSoup(data)
			
			story = soup.find('div', {'id' : 'story'})
			crumbtrail = story.find('h3') # the only h3 ficwad uses.
			allAhrefs = crumbtrail.findAll('a')
		
		# save chapter name from header in case of one-shot.
		storyinfo = story.find('h4').find('a')
		(u0, u1, self.storyId) = storyinfo['href'].split('/')
		self.storyName = storyinfo.string.strip()
		self.outputName = self.storyName.replace(" ", "_") + '-fw_' + self.storyId

		logging.debug('self.storyName=%s, self.storyId=%s, self.outputName=%s' % (self.storyName, self.storyId, self.outputName))
		
		author = soup.find('span', {'class' : 'author'})
		self.authorName = str(author.a.string)
		(u0, u1,self.authorId) = author.a['href'].split('/')
		self.authorURL = 'http://' + self.host + author.a['href']
		logging.debug('self.authorName=%s self.authorId=%s' % (self.authorName, self.authorId))
		
		description = soup.find('blockquote', {'class' : 'summary'})
		if description is not None:
			self.storyDescription = str(description.p.string)
		logging.debug('self.storyDescription=%s' % self.storyDescription)
		
		meta = soup.find('p', {'class' : 'meta'})
		if meta is not None:
			s = str(meta).replace('\n',' ').replace('\t','').split(' - ')
			logging.debug('meta.s=%s' % s)
			for ss in s:
				s1 = ss.replace('&nbsp;','').split(':')
				#logging.debug('meta.s.s1=%s' % s1)
				if len(s1) > 1:
					s2 = re.split ('<[^>]+>', s1[0])
					#logging.debug('meta.s.s1.s2=%s' % s2)
					if len(s2) > 1:
						s1[0] = s2[1]
					skey = s1[0].strip()
					#logging.debug('Checking = %s' % skey)
					if skey == 'Category':
						soup1 = bs.BeautifulStoneSoup(s1[1])
						allAs = soup1.findAll('a')
						for a in allAs:
							if self.category == 'Category':
								self.category = str(a.string)
								logging.debug('self.category=%s' % self.category)
							self._addSubject(self.category)
						logging.debug('self.subjects=%s' % self.subjects)
					elif skey == 'Rating':
						self.storyRating = s1[1]
						logging.debug('self.storyRating=%s' % self.storyRating)
					elif skey == 'Genres':
						self.genre = s1[1]
						logging.debug('self.genre=%s' % self.genre)
						s2 = s1[1].split(', ')
						for ss2 in s2:
							self._addSubject(ss2)
						logging.debug('self.subjects=%s' % self.subjects)
					elif skey == 'Characters':
						s2 = s1[1].split(', ')
						for ss2 in s2:
							self._addCharacter(ss2)
						logging.debug('self.storyCharacters=%s' % self.storyCharacters)
					elif skey == 'Chapters':
						self.numChapters = s1[1]
						logging.debug('self.numChapters=%s' % self.numChapters)
					elif skey == 'Warnings':
						logging.debug('Warnings=%s' % s1[1])
					elif skey == 'Published':
						self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s1[1].strip(' '), "%Y/%m/%d")))
						logging.debug('self.storyPublished=%s' % self.storyPublished)
					elif skey == 'Updated':
						self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s1[1].strip(' '), "%Y/%m/%d")))
						logging.debug('self.storyUpdated=%s' % self.storyUpdated)
				else:
					s3 = re.split ('<[^>]+>', s1[0])
					#logging.debug('meta.s.s1.s3=%s' % s3)
					if len(s3) > 1:
						s1[0] = s3[0]
					s4 = s1[0].split('w')
					#logging.debug('meta.s.s1.s4=%s' % s4)
					if len(s4) > 1 and s4[1] == 'ords':
						self.numWords = s4[0]
						logging.debug('self.numWords=%s' % self.numWords)
					
		
		print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		result = []
		ii = 1

		if oldurl is not None and len(oldurl) > 0:
			data = u2.urlopen(oldurl).read()
			soup = bs.BeautifulStoneSoup(data)
			
		storylist = soup.find('ul', {'id' : 'storylist'})
		if storylist is not None:
			allH4s = storylist.findAll('h4')
			#logging.debug('allH4s=%s' % allH4s)
	
			if allH4s is not None:
				for h4 in allH4s:
					chapterinfo = h4.find('a')
					#logging.debug('Chapter1=%s' % chapterinfo)
					url = 'http://' + self.host + chapterinfo['href']
					title = chapterinfo.string.strip()
					#logging.debug('Chapter=%s, %s' % (url, title))
					# ficwad includes 'Story Index' in the dropdown of chapters, 
					# but it's not a real chapter.
					if title != "Story Index":
						logging.debug('Chapter[%s]=%s, %s' % (ii, url, title))
						result.append((url,title))
						ii = ii+1
					else:
						logging.debug('Skipping Story Index.  URL %s' % url)
				
		if ii == 1:
			select = soup.find('select', { 'name' : 'goto' } )

			if select is None:
				result.append((self.url,self.storyName))
				logging.debug('Chapter[%s]=%s %s' % (ii, self.url, self.storyName))
			else:
				allOptions = select.findAll('option')
				for o in allOptions:
					url = 'http://' + self.host + o['value']
					title = o.string
					# ficwad includes 'Story Index' in the dropdown of chapters, 
					# but it's not a real chapter.
					if title != "Story Index":
						logging.debug('Chapter[%s]=%s, %s' % (ii, url, title))
						result.append((url,title))
						ii = ii+1
					else:
						logging.debug('Skipping Story Index.  URL %s' % url)
			
		self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
		logging.debug('self.uuid=%s' % self.uuid)
		
		return result
	
	def getStoryName(self):
		return self.storyName

	def getOutputName(self):
		return self.outputName
		
	def getAuthorName(self):
		return self.authorName
	
	def getText(self, url):
		if url.find('http://') == -1:
			url = 'http://' + self.host + '/' + url
		
		data = u2.urlopen(url).read()
		
		soup = bs.BeautifulStoneSoup(data)
		div = soup.find('div', {'id' : 'storytext'})
		if None == div:
			logging.error("Error downloading Chapter: %s" % url)
			exit(20)
			return '<html/>'
		return div.__str__('utf8')
	
	def getStoryURL(self):
		logging.debug('self.url=%s' % self.url)
		return self.url

	def getAuthorURL(self):
		logging.debug('self.authorURL=%s' % self.authorURL)
		return self.authorURL

	def getUUID(self):
		logging.debug('self.uuid=%s' % self.uuid)
		return self.uuid

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

	def getPrintableUrl(self, url):
		return url
	
	def getPasswordLine(self):
		return 'opaopapassword'

	def getLoginScript(self):
		return 'opaopaloginscript'

	def getLoginPasswordOthers(self):
		login = dict(login = 'name', password = 'pass')
		other = dict(submit = 'Log In', remember='yes')
		return (login, other)

	def getStoryCharacters(self):
		logging.debug('self.storyCharacters=%s' % self.storyCharacters)
		return self.storyCharacters
	
	def getStorySeries(self):
		logging.debug('self.storySeries=%s' % self.storySeries)
		return self.storySeries
		

		
if __name__ == '__main__':
	url = 'http://www.ficwad.com/story/14536'
	data = u2.urlopen(url).read()
	host = up.urlparse(url).netloc
	fw = FicWad(url)
	urls = fw.extractIndividualUrls()
	pp.pprint(urls)
	print(fw.getText(data))
