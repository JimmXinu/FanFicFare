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
                 expires=time.time()+100,
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

	def _processChapterHeaders(self, div):
		brs = div.findAll ('br')
		for br in brs:
			keystr=''
			valstr=''
			if len(br.contents) > 2:
				keystr = br.contents[1]
				if keystr is not None:
					strs = re.split ("<[^>]+>", str(keystr))
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
						self._addSubject(ss2)
					logging.debug('self.subjects=%s' % self.subjects)
				elif keystr == 'Main Character(s):':
					s2 = valstr.split(', ')
					for ss2 in s2:
						self._addCharacter(ss2)
					logging.debug('self.storyCharacters=%s' % self.storyCharacters)
				elif keystr == 'Summary:':
					self.storyDescription = valstr
					logging.debug('self.storyDescription=%s' % self.storyDescription)
	
		
	def extractIndividualUrls(self):
		data = self.opener.open(self.url).read()		
		
		# There is some usefull information in the headers of the first chapter page..
		data = data.replace('<!-- headerstart -->','<crazytagstringnobodywouldstumbleonaccidently id="storyheaders">').replace('<!-- headerend -->','</crazytagstringnobodywouldstumbleonaccidently>')
		soup = bs.BeautifulStoneSoup(data)
				
		# Get title from <title>, remove before '-'.
		title = soup.find('title').string
		self.storyName = "-".join(title.split('-')[1:]).strip().replace(" (Story Text)","")
		self.outputName = self.storyName.replace(" ", "_") + '-fa_' + self.storyId
		
		links = soup.findAll('li')

		# If it is decided that we really do care about number of words..  It's only available on the author's page..
		#d0 = self.opener.open(self.authorURL).read()
		#soupA = bs.BeautifulStoneSoup(d0)
		#dls = soupA.findAll('dl')
		#logging.debug('dls=%s' % dls)
		
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
				self.storyDescription = str(ss[1]).replace("<br>","").replace("</br>","").replace('\n','')
				logging.debug('self.storyDescription=%s' % self.storyDescription)
			
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
					

		print('Story "%s" by %s' % (self.storyName, self.authorName))
		
		self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
		logging.debug('self.uuid=%s' % self.uuid)
		
		return result
	
	def getStoryName(self):
		return self.storyName

	def getAuthorName(self):
		return self.authorName
	
	def getOutputName(self):
		return self.outputName

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
			exit(20)
			return '<html/>'

		html = soup.findAll('html')
		if len(html) > 1:
			return html[1].__str__('utf8')
		else:
			return div.__str__('utf8').replace('crazytagstringnobodywouldstumbleonaccidently','div')
	
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
	url = 'http://www.fictionalley.org/authors/drt/DA.html'
	data = self.opener.open(url).read()
	host = up.urlparse(url).netloc
	fw = FictionAlley(url)
	urls = fw.extractIndividualUrls(data, host, url)
	pp.pprint(urls)
	print(fw.getText(data))
