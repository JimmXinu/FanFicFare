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

class FictionAlley:
	def __init__(self):
		pass
	
	def extractIndividualUrls(self, data, host, contents):
		soup = bs.BeautifulStoneSoup(data)
		
		title = soup.find('title').string
		self.storyName = "-".join(title.split('-')[1:]).strip()
		
		authors = soup.findAll('a')
		
		print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		links = soup.findAll('a', { 'class' : 'chapterlink' } )

		result = []
		for a in links:
			url = a['href']
			title = a.string
			result.append((url,title))
			
		return result
	
	def getStoryName(self):
		return self.storyName

	def getAuthorName(self):
		return self.authorName
	

	def getText(self, data, fetch = False):
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
	url = 'http://www.fictionalley.org/authors/drt/DA.html'
	data = u2.urlopen(url).read()
	host = up.urlparse(url).netloc
	fw = FictionAlley()
	fw.authorName = 'DrT'
	urls = fw.extractIndividualUrls(data, host, url)
	pp.pprint(urls)
	print(fw.getText(data))