# -*- coding: utf-8 -*-

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
import datetime
from adapter import *


class FictionAlley(FanfictionSiteAdapter):
	def __init__(self, url):
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		logging.debug('self.host=%s' % self.host)
		logging.debug('self.path=%s' % self.path)

		cookieproc = u2.HTTPCookieProcessor()

		# FictionAlley wants a cookie to prove you're old enough to read R+ rated stuff.
		cookie = cl.Cookie(version=0, name='fauser', value='wizard',
                 port=None, port_specified=False,
                  domain='www.fictionalley.org', domain_specified=False, domain_initial_dot=False,
                 path='/authors', path_specified=True,
                 secure=False,
                 expires=time.time()+10000,
                 discard=False,
                 comment=None,
                 comment_url=None,
                 rest={'HttpOnly': None},
					  rfc2109=False)
		cookieproc.cookiejar.set_cookie(cookie)
		self.opener = u2.build_opener(cookieproc)

		ss = self.path.split('/')
		
		self.storyDescription = 'Fanfiction Story'
		self.authorId = ''
		self.authorURL = ''
		self.storyId = ''
		if len(ss) > 2 and ss[1] == 'authors':
			self.authorId = ss[2]
			self.authorURL = 'http://' + self.host + '/authors/' + self.authorId
			if len(ss) > 3:
				self.storyId = ss[3].replace ('.html','')
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
		self.genre = ''
		self.category = 'Harry Potter'
		self.storyStatus = 'Unknown' # fictionalley doesn't give us in-progress/completed anywhere.
		self.storyRating = 'K'
		self.storyUserRating = '0'
		self.storyCharacters = []
		self.storySeries = ''
		self.storyName = ''
		self.outputName = ''
		self.outputStorySep = '-fa_'	
		
	def getPasswordLine(self):
		return 'opaopapassword'

	def getLoginScript(self):
		return 'opaopaloginscript'

	def getLoginPasswordOthers(self):
		login = dict(login = 'name', password = 'pass')
		other = dict(submit = 'Log In', remember='yes')
		return (login, other)

	def _processChapterHeaders(self, div):
		brs = div.findAll ('br')
		for br in brs:
			keystr=''
			valstr=''
			if len(br.contents) > 2:
				keystr = br.contents[1]
				if keystr is not None:
					strs = re.split ("<[^>]+>", unicode(keystr))
					keystr=''
					for s in strs:
						keystr = keystr + s					
				valstr = br.contents[2].strip(' ')
			if keystr is not None:
				if keystr == 'Rating:':
					self.storyRating = valstr
					logging.debug('self.storyRating=%s' % self.storyRating)
				elif keystr == 'Genre:':
					self.genre = valstr
					logging.debug('self.genre=%s' % self.genre)
					s2 = valstr.split(', ')
					for ss2 in s2:
						self.addSubject(ss2)
					logging.debug('self.subjects=%s' % self.subjects)
				elif keystr == 'Main Character(s):':
					s2 = valstr.split(', ')
					for ss2 in s2:
						self.addCharacter(ss2)
					logging.debug('self.storyCharacters=%s' % self.storyCharacters)
				elif keystr == 'Summary:':
					self.storyDescription = valstr
					#logging.debug('self.storyDescription=%s' % self.storyDescription.replace("\n"," ").replace('\r',''))
	
		
	def extractIndividualUrls(self):
		data = ''
		try:
			data = self.opener.open(self.url).read()		
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + self.url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise StoryDoesNotExist("Problem reading story URL " + self.url + "!")
		
		# There is some usefull information in the headers of the first chapter page..
		data = data.replace('<!-- headerstart -->','<crazytagstringnobodywouldstumbleonaccidently id="storyheaders">').replace('<!-- headerend -->','</crazytagstringnobodywouldstumbleonaccidently>')
		soup = None
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % self.url)
				
		breadcrumbs = soup.find('div', {'class': 'breadcrumbs'})
		if breadcrumbs is not None:
			# Be aware that this means that the user has entered the {STORY}01.html 
			# We will not have valid Publised and Updated dates.  User should enter 
			# the {STORY}.html instead.  We should force that instead of this.
			#logging.debug('breadcrumbs=%s' % breadcrumbs )
			bcas = breadcrumbs.findAll('a')
			#logging.debug('bcas=%s' % bcas )
			if bcas is not None and len(bcas) > 1:
				bca = bcas[1]
				#logging.debug('bca=%s' % bca )
				if 'href' in bca._getAttrMap():
					#logging.debug('bca.href=%s' % bca['href'] )
					url = unicode(bca['href'])
					if url is not None and len(url) > 0:
						self.url = url
						logging.debug('self.url=%s' % self.url )
						ss = self.url.split('/')
						self.storyId = ss[-1].replace('.html','')
						self.storyName = bca.string
						logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))

						data = self.opener.open(self.url).read()		
						
						# There is some usefull information in the headers of the first chapter page..
						data = data.replace('<!-- headerstart -->','<crazytagstringnobodywouldstumbleonaccidently id="storyheaders">').replace('<!-- headerend -->','</crazytagstringnobodywouldstumbleonaccidently>')
						soup = bs.BeautifulStoneSoup(data)
		
		# If it is decided that we really do care about number of words..  It's only available on the author's page..
		#d0 = self.opener.open(self.authorURL).read()
		#soupA = bs.BeautifulStoneSoup(d0)
		#dls = soupA.findAll('dl')
		#logging.debug('dls=%s' % dls)
		
		# Get title from <title>, remove before '-'.
		if len(self.storyName) == 0:
			title = soup.find('title').string
			self.storyName = "-".join(title.split('-')[1:]).strip().replace(" (Story Text)","")
		
		links = soup.findAll('li')

		self.numChapters = 0;
		result = []
		if len(links) == 0:
			# Be aware that this means that the user has entered the {STORY}01.html 
			# We will not have valid Publised and Updated dates.  User should enter 
			# the {STORY}.html instead.  We should force that instead of this.
			breadcrumbs = soup.find('div', {'class': 'breadcrumbs'})
			self.authorName = breadcrumbs.a.string.replace("'s Fics","")
			result.append((self.url,self.storyName))
			#logging.debug('chapter[%s]=%s, %s' % (self.numChapters+1,self.url,self.storyName))
			self.numChapters = self.numChapters + 1;
			div = soup.find('crazytagstringnobodywouldstumbleonaccidently', {'id' : 'storyheaders'})
			if div is not None:
				self._processChapterHeaders(div)
		else:
			author = soup.find('h1', {'class' : 'title'})
			self.authorName = author.a.string
			
			summary = soup.find('div', {'class' : 'summary'})
			ss = summary.contents
			if len(ss) > 1:
				ss1 = ss[0].split(': ')
				if len(ss1) > 1 and ss1[0] == 'Rating':
					self.storyRating = ss1[1]
					logging.debug('self.storyRating=%s' % self.storyRating)
				self.storyDescription = unicode(ss[1]).replace("<br>","").replace("</br>","").replace('\n','')
				#logging.debug('self.storyDescription=%s' % self.storyDescription.replace("\n"," ").replace('\r',''))
			
			for li in links:
				a = li.find('a', {'class' : 'chapterlink'})
				s = li.contents
				if a is not None:
					url = a['href']
					title = a.string
					result.append((url,title))
					#logging.debug('chapter[%s]=%s, %s' % (self.numChapters+1,url,title))
					if self.numChapters == 0:
						# fictionalley uses full URLs in chapter list.
						d1 = self.opener.open(url).read()
						
						# find <!-- headerstart --> & <!-- headerend --> and
						# replaced with matching div pair for easier parsing.
						# Yes, it's an evil kludge, but what can ya do?  Using
						# something other than div prevents soup from pairing
						# our div with poor html inside the story text.
						d1 = d1.replace('<!-- headerstart -->','<crazytagstringnobodywouldstumbleonaccidently id="storyheaders">').replace('<!-- headerend -->','</crazytagstringnobodywouldstumbleonaccidently>')
						sop = bs.BeautifulStoneSoup(d1)
						
						div = sop.find('crazytagstringnobodywouldstumbleonaccidently', {'id' : 'storyheaders'})
						if div is not None:
							self._processChapterHeaders(div)
							
					self.numChapters = self.numChapters + 1
					if len(s) > 1:
						datestr=''
						ss2 = s[1].replace('\n','').replace('(','').split(' ')
						if len(ss2) > 2 and ss2[0] == 'Posted:':
							datestr = ss2[1] + ' ' + ss2[2]
							tmpdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestr.strip(' '), "%Y-%m-%d %H:%M:%S")))
							if self.numChapters == 1:
								self.storyPublished = tmpdate
							self.storyUpdated = tmpdate
						logging.debug('self.storyPublished=%s, self.storyUpdated=%s' % (self.storyPublished, self.storyUpdated))
				else:
					logging.debug('li chapterlink not found!  li=%s' % li)
					

		logging.debug('Story "%s" by %s' % (self.storyName, self.authorName))
		
		return result
	
	def getText(self, url):
		# fictionalley uses full URLs in chapter list.
		data = ''
		try:
			data = self.opener.open(url).read()
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)
		
		
		# find <!-- headerend --> & <!-- footerstart --> and
		# replaced with matching div pair for easier parsing.
		# Yes, it's an evil kludge, but what can ya do?  Using
		# something other than div prevents soup from pairing
		# our div with poor html inside the story text.
		data = data.replace('<!-- headerend -->','<crazytagstringnobodywouldstumbleonaccidently id="storytext">').replace('<!-- footerstart -->','</crazytagstringnobodywouldstumbleonaccidently>')
		
		soup = None
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			logging.info("Failed to decode: <%s>" % data)
			raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
		
		div = soup.find('crazytagstringnobodywouldstumbleonaccidently', {'id' : 'storytext'})
		if None == div:
			raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

		html = soup.findAll('html')
		if len(html) > 1:
			return html[1].__str__('utf8')
		else:
			return div.__str__('utf8').replace('crazytagstringnobodywouldstumbleonaccidently','div')
	
	
		
if __name__ == '__main__':
	url = 'http://www.fictionalley.org/authors/drt/DA.html'
	data = self.opener.open(url).read()
	host = up.urlparse(url).netloc
	fw = FictionAlley(url)
	urls = fw.extractIndividualUrls(data, host, url)
	pp.pprint(urls)
	print(fw.getText(data))
