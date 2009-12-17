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

class FicWad:
	def __init__(self, url):
		self.url = url
		self.host = up.urlparse(url).netloc
	
	def requiresLogin(self, url):
		return False
	
	def performLogin(self, url):
		pass
		
	def setLogin(self, login):
		self.login = login
	
	def setPassword(self, password):
		self.password = password
	
	def extractIndividualUrls(self):
		data = u2.urlopen(self.url).read()
		soup = bs.BeautifulStoneSoup(data)
		
		title = soup.find('title').string
		self.storyName = title.split('::')[0].strip()
		
		author = soup.find('span', {'class' : 'author'})
		self.authorName = author.a.string
		
		print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		select = soup.find('select', { 'name' : 'goto' } )
		
		allOptions = select.findAll('option')
		result = []
		for o in allOptions:
			url = o['value']
#			if type(url) is unicode:
#				url = url.encode('utf-8')
			title = o.string
			result.append((url,title))
			
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
			return '<html/>'
		
		return div.prettify()
	
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
	fw = FicWad()
	urls = fw.extractIndividualUrls(data, host, url)
	pp.pprint(urls)
	print(fw.getText(data))