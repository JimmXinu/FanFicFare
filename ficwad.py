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
	
	def extractIndividualUrls(self):
		data = u2.urlopen(self.url).read()
		soup = bs.BeautifulStoneSoup(data)
		
		story = soup.find('div', {'id' : 'story'})
		crumbtrail = story.find('h3') # the only h3 ficwad uses.
		allAhrefs = crumbtrail.findAll('a')
		# last of crumbtrail
		self.storyName = allAhrefs[-1].string.strip()
		# save chapter name from header in case of one-shot.
		chaptername = story.find('h4').find('a').string.strip()
		
		author = soup.find('span', {'class' : 'author'})
		self.authorName = str(author.a.string)
		
		select = soup.find('select', { 'name' : 'goto' } )
		
		result = []
		if select is None:
			# Single chapter storys don't have title in crumbtrail, just 'chapter' title in h4.
			self.storyName = chaptername
			# no chapters found, try url by itself.
			result.append((self.url,self.storyName))
		else:
			allOptions = select.findAll('option')
			for o in allOptions:
				url = o['value']
				title = o.string
				# ficwad includes 'Story Index' in the dropdown of chapters, 
				# but it's not a real chapter.
				if title != "Story Index":
					result.append((url,title))
			
		print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		return result
	
	def getStoryName(self):
		return self.storyName

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
			exit(1)
			return '<html/>'
		return div.__str__('utf8')
	
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

		
if __name__ == '__main__':
	url = 'http://www.ficwad.com/story/14536'
	data = u2.urlopen(url).read()
	host = up.urlparse(url).netloc
	fw = FicWad(url)
	urls = fw.extractIndividualUrls()
	pp.pprint(urls)
	print(fw.getText(data))