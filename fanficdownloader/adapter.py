# -*- coding: utf-8 -*-

import logging
import datetime
from output import makeAcceptableFilename

try:
	from google.appengine.api.urlfetch import fetch as googlefetch
	appEngineGlob = True
except:
	appEngineGlob = False

class LoginRequiredException(Exception):
	def __init__(self, url):
		self.url = url
	
	def __str__(self):
		return repr(self.url + ' requires user to be logged in')
	
class StoryArchivedAlready(Exception):
	pass

class StoryDoesNotExist(Exception):
	pass

class FailedToDownload(Exception):
	pass

class InvalidStoryURL(Exception):
	pass

class FanfictionSiteAdapter:
	appEngine = appEngineGlob
	login = ''
	password = ''
	url = ''
	host = ''
	path = ''
	uuid = ''
	storyName = ''
	storyId = ''
	authorName = ''
	authorId = ''
	authorURL = ''
	outputStorySep = '-Ukn_'
	outputName = ''
	outputFileName = ''
	storyDescription = ''
	storyCharacters = []
	storySeries = ''
	storyPublished = datetime.date(1970, 01, 31)
	storyCreated = datetime.datetime.now()
	storyUpdated = datetime.date(1970, 01, 31)
	languageId = 'en-UK'
	language = 'English'
	subjects = []
	publisher = ''
	numChapters = '0'
	numWords = '0'
	genre = ''
	category = ''
	storyStatus = 'In-Progress'
	storyRating = ''
	storyUserRating = '0'
	def __init__(self, url):
		# basic plain url parsing...
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
			
	def hasAppEngine(self):
		return self.appEngine
	
	def fetchUrl(self, url):
		if not self.appEngine:
			return self.opener.open(url).read().decode('utf-8')
		else:
			return googlefetch(url,deadline=10).content
	
	def requiresLogin(self, url = None):
		return False
	
	def performLogin(self, url = None):
		return True
	
	def extractIndividualUrls(self):
		pass
		
	def getText(self, url):
		pass

	def setLogin(self, login):
		self.login = login

	def setPassword(self, password):
		self.password = password

	def getHost(self):
		logging.debug('self.host=%s' % self.host)
		return self.host
	
	def getUUID(self):
		self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
		logging.debug('self.uuid=%s' % self.uuid)
		return self.uuid

	def getOutputName(self):
		self.outputName = makeAcceptableFilename(self.storyName.replace(" ", "_") + self.outputStorySep + self.storyId)
		logging.debug('self.outputName=%s' % self.outputName)
		return self.outputName

	def getOutputFileName(self, booksDirectory, bookExt):
		self.getOutputName()	# make sure self.outputName is populated
		self.outputFileName = booksDirectory + "/" + self.outputName + bookExt
		logging.debug('self.outputFileName=%s' % self.outputFileName)
		return self.outputFileName

	def getAuthorURL(self):
		logging.debug('self.authorURL=%s' % self.authorURL)
		return self.authorURL

	def getAuthorId(self):
		logging.debug('self.authorId=%s' % self.authorId)
		return self.authorId

	def getAuthorName(self):
		logging.debug('self.authorName=%s' % self.authorName)
		return self.authorName

	def getStoryURL(self):
		logging.debug('self.url=%s' % self.url)
		return self.url

	def getStoryId(self):
		logging.debug('self.storyId=%s' % self.storyId)
		return self.storyId

	def getStoryName(self):
		logging.debug('self.storyName=%s' % self.storyName)
		return self.storyName

	def getStoryDescription(self):
		logging.debug('self.storyDescription=%s' % self.storyDescription)
		return self.storyDescription

	def getStoryCreated(self):
		self.storyCreated = datetime.datetime.now()
		logging.debug('self.storyCreated=%s' % self.storyCreated)
		return self.storyCreated

	def addCharacter(self, character):
		chara = character.upper()
		for c in self.storyCharacters:
			if c.upper() == chara:
				return False
		self.storyCharacters.append(character)
		return True

	def getStoryCharacters(self):
		logging.debug('self.storyCharacters=%s' % self.storyCharacters)
		return self.storyCharacters
	
	def getStoryPublished(self):
		logging.debug('self.storyPublished=%s' % self.storyPublished)
		return self.storyPublished

	def getStoryUpdated(self):
		logging.debug('self.storyUpdated=%s' % self.storyUpdated)
		return self.storyUpdated

	def getStorySeries(self):
		logging.debug('self.storySeries=%s' % self.storySeries)
		return self.storySeries

	def getLanguage(self):
		logging.debug('self.language=%s' % self.language)
		return self.language

	def getLanguageId(self):
		logging.debug('self.languageId=%s' % self.languageId)
		return self.languageId

	def addSubject(self, subject):
		subj = subject.upper()
		for s in self.subjects:
			if s.upper() == subj:
				return False
		self.subjects.append(subject)
		return True

	def getSubjects(self):
		logging.debug('self.subjects=%s' % self.subjects)
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
