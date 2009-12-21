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

	def getStoryName(self):
		pass

	def getAuthorName(self):
		pass

	def getPrintableUrl(self, url):
		pass