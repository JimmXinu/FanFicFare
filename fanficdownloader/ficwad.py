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
		self.outputName = ''
		self.outputStorySep = '-fw_'

	def getPasswordLine(self):
		return 'opaopapassword'

	def getLoginScript(self):
		return 'opaopaloginscript'

	def getLoginPasswordOthers(self):
		login = dict(login = 'name', password = 'pass')
		other = dict(submit = 'Log In', remember='yes')
		return (login, other)

	def extractIndividualUrls(self):
		oldurl = ''
		cururl = self.url
		data = ''
		try:
			data = u2.urlopen(self.url).read()
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + self.url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise StoryDoesNotExist("Problem reading story URL " + self.url + "!")

		soup = None
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % self.url)
		
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

		logging.debug('self.storyName=%s, self.storyId=%s' % (self.storyName, self.storyId))
		
		author = soup.find('span', {'class' : 'author'})
		self.authorName = unicode(author.a.string)
		(u0, u1,self.authorId) = author.a['href'].split('/')
		self.authorURL = 'http://' + self.host + author.a['href']
		logging.debug('self.authorName=%s self.authorId=%s' % (self.authorName, self.authorId))
		
		description = soup.find('blockquote', {'class' : 'summary'})
		if description is not None:
			self.storyDescription = unicode(description.p.string)
		logging.debug('self.storyDescription=%s' % self.storyDescription.replace('\n',' ').replace('\r',''))
		
		meta = soup.find('p', {'class' : 'meta'})
		if meta is not None:
			logging.debug('meta.s pre=%s' % meta.__str__('utf8'))
			s = re.sub('<[^>]+>','',unicode(meta)).replace('\n',' ').replace('\t','').split(' - ')
			#logging.debug('meta.s post=%s' % s)
			for ss in s:
				s1 = ss.replace('&nbsp;','').split(':')
				#logging.debug('ss=%s' % ss)
				if len(s1) > 1:
					skey = s1[0].strip()
					#logging.debug('Checking = %s' % skey)
					if skey == 'Category':
						# ficwad doesn't allow multiple categories.
						self.category = unicode(s1[1])
						logging.debug('self.category=%s' % self.category)
						self.addSubject(self.category)
						logging.debug('self.subjects=%s' % self.subjects)
					elif skey == 'Rating':
						self.storyRating = s1[1]
						logging.debug('self.storyRating=%s' % self.storyRating)
					elif skey == 'Genres':
						self.genre = s1[1]
						logging.debug('self.genre=%s' % self.genre)
						s2 = s1[1].split(', ')
						for ss2 in s2:
							self.addSubject(ss2)
						logging.debug('self.subjects=%s' % self.subjects)
					elif skey == 'Characters':
						s2 = s1[1].split(', ')
						for ss2 in s2:
							self.addCharacter(ss2)
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
					if ss == 'Complete' :
						self.storyStatus = 'Completed'
					elif ss.endswith('words'):
						self.numWords=ss.replace('words','').replace('&nbsp;','')
						logging.debug('self.numWords=%s' % self.numWords)
					
		logging.debug('Story "%s" by %s' % (self.storyName, self.authorName))
		
		result = []
		ii = 1

		if oldurl is not None and len(oldurl) > 0:
			logging.debug('Switching back to %s' % oldurl)
			cururl = oldurl
			data = u2.urlopen(oldurl).read()
			soup = bs.BeautifulStoneSoup(data)
			
		storylist = soup.find('ul', {'id' : 'storylist'})
		if storylist is not None:
			allBlocked = storylist.findAll('li', {'class' : 'blocked'})
			if allBlocked is not None:
				#logging.debug('allBlocked=%s' % allBlocked)
				raise FailedToDownload("Are you sure %s is a chapter URL(not the chapter list)?"%cururl)
				raise LoginRequiredException(cururl)

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
				self.numChapters = '1'
				logging.debug('self.numChapters=%s' % self.numChapters)
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
		
		return result
	
	def getText(self, url):
		if url.find('http://') == -1:
			url = 'http://' + self.host + '/' + url
		
		data = ''
		try:
			data = u2.urlopen(url).read()
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)
		
		try:
			soup = bs.BeautifulStoneSoup(data)
		except:
			logging.info("Failed to decode: <%s>" % data)
			raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
		
		div = soup.find('div', {'id' : 'storytext'})
		if None == div:
			raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

		return div.__str__('utf8')
	
		
if __name__ == '__main__':
	url = 'http://www.ficwad.com/story/14536'
	data = u2.urlopen(url).read()
	host = up.urlparse(url).netloc
	fw = FicWad(url)
	urls = fw.extractIndividualUrls()
	pp.pprint(urls)
	print(fw.getText(data))
