# -*- coding: utf-8 -*-

class LoginRequiredException(Exception):
	def __init__(self, url):
		self.url = url
	
	def __str__(self):
		return repr(self.url + ' requires user to be logged in')

class FanfictionSiteAdapter:
	login = ''
	password = ''
	def __init__(self, url):
		pass
	
	def requiresLogin(self, url = None):
		pass
	
	def performLogin(self, url = None):
		pass
	
	def extractIndividualUrls(self):
		pass
		
	def getText(self, url):
		pass

	def setLogin(self, login):
		pass

	def setPassword(self, password):
		pass

	def getHost(self):
		pass
	
	def getStoryURL(self):
		pass

	def getUUID(self):
		pass

	def getOutputName(self):
		pass

	def getAuthorURL(self):
		pass

	def getAuthorId(self):
		pass

	def getAuthorName(self):
		pass

	def getStoryId(self):
		pass

	def getStoryName(self):
		pass

	def getStoryDescription(self):
		pass

	def getStoryCreated(self):
		pass

	def getStoryPublished(self):
		pass

	def getStoryUpdated(self):
		pass

	def getStorySeries(self):
		pass

	def getLanguage(self):
		pass

	def getLanguageId(self):
		pass

	def getSubjects(self):
		pass

	def getCharacters(self):
		pass

	def getPublisher(self):
		pass

	def getNumChapters(self):
		pass

	def getNumWords(self):
		pass

	def getCategory(self):
		pass

	def getGenre(self):
		pass

	def getStoryStatus(self):
		pass

	def getStoryRating(self):
		pass

	def getStoryUserRating(self):
		pass

	def getPrintableUrl(self, url):
		pass
