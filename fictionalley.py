import os
import re
import sys
import shutil
import logging
import os.path
import urllib as u
import pprint as pp
import urllib2 as u2
import cookielib as cl
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs
import time as time
from adapter import *


class FictionAlley(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		self.host = up.urlparse(url).netloc
		cookieproc = u2.HTTPCookieProcessor()

		# FictionAlley wants a cookie to prove you're old enough to read R+ rated stuff.
		cookie = cl.Cookie(version=0, name='fauser', value='wizard',
                 port=None, port_specified=False,
                  domain='www.fictionalley.org', domain_specified=False, domain_initial_dot=False,
                 path='/authors', path_specified=True,
                 secure=False,
                 expires=time.time()+100,
                 discard=False,
                 comment=None,
                 comment_url=None,
                 rest={'HttpOnly': None},
					  rfc2109=False)
		cookieproc.cookiejar.set_cookie(cookie)
		self.opener = u2.build_opener(cookieproc)
		
	def requiresLogin(self, url = None):
		return False
	
	def performLogin(self, url = None):
		pass
		
	def setLogin(self, login):
		self.login = login
	
	def setPassword(self, password):
		self.password = password
	
	def extractIndividualUrls(self):
		data = self.opener.open(self.url).read()		
		soup = bs.BeautifulStoneSoup(data)
				
		# Get title from <title>, remove before '-'.
		title = soup.find('title').string
		self.storyName = "-".join(title.split('-')[1:]).strip().replace(" (Story Text)","")
		
		links = soup.findAll('a', { 'class' : 'chapterlink' } )

		result = []
		if len(links) == 0:
			breadcrumbs = soup.find('div', {'class': 'breadcrumbs'})
			self.authorName = breadcrumbs.a.string.replace("'s Fics","")
			result.append((self.url,self.storyName))
		else:
			author = soup.find('h1', {'class' : 'title'})
			self.authorName = author.a.string
			
			for a in links:
				url = a['href']
				title = a.string
				result.append((url,title))
					
		#print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		return result
	
	def getStoryName(self):
		return self.storyName

	def getAuthorName(self):
		return self.authorName
	
	def getText(self, url):
		# fictionalley uses full URLs in chapter list.
		data = self.opener.open(url).read()
		
		# find <!-- headerend --> & <!-- footerstart --> and
		# replaced with matching div pair for easier parsing.
		# Yes, it's an evil kludge, but what can ya do?  Using
		# something other than div prevents soup from pairing
		# our div with poor html inside the story text.
		data = data.replace('<!-- headerend -->','<crazytagstringnobodywouldstumbleonaccidently id="storytext">').replace('<!-- footerstart -->','</crazytagstringnobodywouldstumbleonaccidently>')
		soup = bs.BeautifulStoneSoup(data)
		
		div = soup.find('crazytagstringnobodywouldstumbleonaccidently', {'id' : 'storytext'})
		if None == div:
			logging.error("Error downloading Chapter: %s" % url)
			exit(1)
			return '<html/>'
		return div.__str__('utf8').replace('crazytagstringnobodywouldstumbleonaccidently','div')
	
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
	data = self.opener.open(url).read()
	host = up.urlparse(url).netloc
	fw = FictionAlley(url)
	urls = fw.extractIndividualUrls(data, host, url)
	pp.pprint(urls)
	print(fw.getText(data))
