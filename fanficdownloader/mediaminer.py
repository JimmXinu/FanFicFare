# -*- coding: utf-8 -*-

import os
import re
import sys
import cgi
import uuid
import shutil
import os.path
import logging
import unittest
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs
import time
import datetime

from constants import *
from adapter import *

try:
	import login_password
except:
	# tough luck
	pass

class MediaMiner(FanfictionSiteAdapter):
	def __init__(self, url):		
		self.url = url
		parsedUrl = up.urlparse(url)
		self.host = parsedUrl.netloc
		self.path = parsedUrl.path
		
		self.storyName = ''
		self.authorName = ''
		self.storyDescription = ''
		self.storyCharacters = []
		self.storySeries = ''
		self.authorId = '0'
		self.authorURL = self.path
		self.storyId = '0'
		self.storyPublished = datetime.date(1970, 01, 31)
		self.storyCreated = datetime.datetime.now()
		self.storyUpdated = datetime.date(1970, 01, 31)
		self.languageId = 'en-UK'
		self.language = 'English'
		self.subjects = []
		self.publisher = self.host
		self.numChapters = 0
		self.numWords = 0
		self.genre = ''
		self.category = ''
		self.storyStatus = 'In-Progress'
		self.storyRating = 'K'
		self.storyUserRating = '0'
		self.outputName = ''
		self.outputStorySep = '-mm_'
				
		logging.debug('self.url=%s' % self.url)
		
		if self.url.find('view_st.php') != -1:
			ss = self.url.split('view_st.php')
			logging.debug('ss=%s' % ss)
			if ss is not None and len(ss) > 1:
				self.storyId = ss[1].replace('/','').strip()
		elif self.url.find('view_ch.php?') != -1:
			ss = self.url.split('=')
			logging.debug('ss=%s' % ss)
			if ss is not None and len(ss) > 1:
				self.storyId = ss[-1].replace('/','').strip()
				self.path = '/fanfic/view_st.php/' + self.storyId
				self.url = 'http://' + self.host + self.path
				logging.debug('self.url=%s' % self.url)
		elif self.url.find('view_ch.php/') != -1:
			ss = self.url.split('/')
			logging.debug('ss=%s' % ss)
			if ss is not None and len(ss) > 2:
				self.storyId = ss[-2].strip()
				self.path = '/fanfic/view_st.php/' + self.storyId
				self.url = 'http://' + self.host + self.path
				logging.debug('self.url=%s' % self.url)
		else:			
			raise InvalidStoryURL("Error URL \"%s\" is not a story." % self.url)
			
		logging.debug('self.storyId=%s' % self.storyId)
		
		logging.debug('self.path=%s' % self.path)
		
		if not self.appEngine:
			self.opener = u2.build_opener(u2.HTTPCookieProcessor())
		else:
			self.opener = None
	
		logging.debug("Created MediaMiner: url=%s" % (self.url))
	
	def _getLoginScript(self):
		return self.path

	def extractIndividualUrls(self):
		data = None
		try:
			data = self.fetchUrl(self.url)
		except Exception, e:
			data = None
			logging.error("Caught an exception reading URL " + self.url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise StoryDoesNotExist("Problem reading story URL " + self.url + "!")
		
		#data.replace('<br />',' ').replace('<br>',' ').replace('</br>',' ')
		soup = None
		try:
			soup = bs.BeautifulSoup(data)
		except:
			logging.error("Failed to decode: <%s>" % data)
			raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % self.url)

		#logging.debug('soap=%s' % soup)
		urls = []
		
		td_ffh = soup.find('td', {'class' : 'ffh'})
		#logging.debug('td_ffh=%s' % td_ffh)
		if td_ffh is not None:
			#logging.debug('td_ffh.text=%s' % td_ffh.find(text=True))
			self.storyName = unicode(td_ffh.find(text=True)).strip()
			logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
			fft = td_ffh.find('font', {'class' : 'smtxt'})
			#logging.debug('fft=%s' % fft)
			if fft is not None:
				ffts = fft.string.split(' ')
				if ffts is not None:
					if len(ffts) > 1:
						self.storyRating = ffts[1]
						logging.debug('self.storyRating=%s' % self.storyRating)
		self.genre = ''
		td_smtxt = soup.findAll('td')
		if td_smtxt is None:
			#logging.debug('td_smtxt is NONE!')
			pass
		else:
			ll = len(td_smtxt)
			#logging.debug('td_smtxt=%s, len=%s' % (td_smtxt, ll))
			for ii in range(ll):
				td = td_smtxt[ii]
				if 'class' in td._getAttrMap() and td['class'] != 'smtxt':
					#logging.debug('td has class attribute but is not smtxt')
					continue
				ss = unicode(td).replace('\n','').replace('\r','').replace('&nbsp;', ' ')
				#logging.debug('ss=%s' % ss)
				if len(ss) > 1 and (ss.find('Genre(s):') != -1 or ss.find('Type:') != -1):
					#logging.debug('ss=%s' % ss)
					ssbs = td.findAll('b')
					#logging.debug('ssbs=%s' % ssbs)
					bb = 0
					while bb < len(ssbs):
						nvs = bs.NavigableString('')
						sst=''
						ssb = ssbs[bb]
						ssbt = unicode(ssb.text).strip()
						#logging.debug('ssb=%s' % ssb)
						#logging.debug('ssbt=%s' % ssbt)
						ssbn = ssb.nextSibling
						while ssbn is not None:
							#logging.debug('ssbn=%s' % ssbn)
							#logging.debug('ssbn.class=%s' % ssbn.__class__)
							if nvs.__class__ == ssbn.__class__:
								st = unicode(ssbn)
								if st.strip() != '|':
									sst = sst + st
							else:
								#logging.debug('ssbn.name=%s' % ssbn.name)
								if ssbn.name == 'b':
									break								
								ssbnts = ssbn.findAll(text=True)
								for ssbnt in ssbnts:
									sst = sst + ssbnt
							ssbn = ssbn.nextSibling
						sst = sst.replace('&nbsp;',' ').strip()
						#logging.debug('sst=%s' % sst)
						if bb == 0:
							ssbt = ssbt.replace(':','')
							self.addSubject(ssbt)
							self.addSubject(sst)
							logging.debug('self.subjects=%s' % self.subjects)
						else:
							if ssbt == 'Genre(s):':
								self.genre = sst
								logging.debug('self.genre=%s' % self.genre)
								sts = sst.split(' / ')
								for st in sts:
									self.addSubject(st.strip())
								logging.debug('self.subjects=%s' % self.subjects)
							elif ssbt == 'Type:':
								self.category = sst
								logging.debug('self.category=%s' % self.category)
								self.addSubject(sst)
								logging.debug('self.subjects=%s' % self.subjects)
							elif ssbt == 'Author:':
								pass
							elif ssbt == 'Visits:':
								pass
							elif ssbt == 'Size:':
								pass
							elif ssbt == 'Pages:':
								pass
							elif ssbt == 'Status:':
								if sst == "Completed":
									self.storyStatus = 'Completed'
								else:
									self.storyStatus = 'In-Progress'
							elif ssbt == 'Words:':
								self.numWords = sst.replace('|','').strip()
								logging.debug('self.numWords=%s' % self.numWords)
								pass
							elif ssbt == 'Summary:':
								self.storyDescription = sst.strip()
								#logging.debug('self.storyDescription=%s' % self.storyDescription.replace("\n"," ").replace('\r',''))
							elif ssbt == 'Latest Revision:' or ssbt == 'Uploaded On:':
								#logging.debug('sst=%s' % sst)
								ssts = sst.split(' ')
								if ssts is not None and len(ssts) > 3:
									sst = ssts[0] + ' ' + ssts[1] + ' ' + ssts[2]
								#logging.debug('sst=%s' % sst)
								self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(sst.strip(' '), "%B %d, %Y")))
								logging.debug('self.storyUpdated=%s' % self.storyUpdated)
							else:
								pass
						bb = bb+1
						
					smtxt_as = td_smtxt[ii].findAll('a')
					#logging.debug('smtxt_as=%s' % smtxt_as)
					for smtxt_a in smtxt_as:
						if 'href' in smtxt_a._getAttrMap() and smtxt_a['href'].find('/u/'):
							sta = smtxt_a['href']
							#logging.debug('sta=%s' % sta)
							stas = sta.split('/u/')
							#logging.debug('stas=%s' % stas)
							if stas is not None and len(stas) > 1:
								self.authorId = stas[1]
								self.authorURL = 'http://' + self.host + sta
								self.authorName = smtxt_a.string
								logging.debug('self.authorName=%s, self.authorId=%s' % (self.authorName, self.authorId))
				
		urlstory=''
		numchapters = 0
		td_tbbrdr = soup.find('td', {'class' : 'tbbrdr'})
		if td_tbbrdr is not None:
			#logging.debug('td_tbbrdr=%s' % td_tbbrdr )

			sl = td_tbbrdr.find('select', {'name':'cid'})
			if sl is not None:
				#logging.debug('sl=%s' % sl )
				opts = sl.findAll('option')
				for o in opts:
					#logging.debug('o=%s' % o)				
					if 'value' in o._getAttrMap():
						url = 'http://' + self.host + '/fanfic/view_ch.php/' + self.storyId  + '/' + o['value']
						logging.debug('URL=%s, Title=%s' % (url, o.string))
						if numchapters == 0:
							ss = o.string.split('[')
							if ss is not None and len(ss) > 1:
								ssd = ss[-1].replace(']','') 
								#logging.debug('ssd=%s' % ssd)
								self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(ssd.strip(' '), "%b %d, %Y")))
								logging.debug('self.storyPublished=%s' % self.storyPublished)
						urls.append((url, o.string))
						numchapters = numchapters + 1
		
		if numchapters == 0:
			numchapters = 1
			url = 'http://' + self.host + '/fanfic/view_st.php/' + self.storyId
			self.storyPublished = self.storyUpdated
			logging.debug('self.storyPublished=%s' % self.storyPublished)
			ssd = self.storyName + ' [' + self.storyPublished.strftime("%b %d, %Y") + ']'
			logging.debug('URL=%s, Title=%s' % (url, ssd))
			urls.append((url, ssd))
			
		self.numChapters = unicode(numchapters)
		logging.debug('self.numChapters=%s' % self.numChapters)
		#logging.debug('urls=%s' % urls)
		
		return urls
	
	def getText(self, url):
		# time.sleep( 2.0 )
		logging.debug('url=%s' % url)
		data = ''
		try:
			data = self.fetchUrl(url)
		except Exception, e:
			data = ''
			logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
		if data is None:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)
		
		soup = None
		try:
			soup = bs.BeautifulSoup(data)
		except:
			raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)

		# convert div's to p's.  mediaminer uses div with a
		# margin for paragraphs.
		divlist = soup.findAll('div', {'class' : None})
		for tag in divlist:
			tag.name='p';
		
		nvs = bs.NavigableString('')
		sst=''
		allAs = soup.findAll ('a', { 'name' : 'fic_c' })
		#logging.debug('allAs=%s' % allAs)
		for a in allAs:
			#logging.debug('a=%s' % a)
			foundfirst = False
			done = False
			nxta = a.nextSibling
			while nxta is not None and not done:
				#logging.debug('nxta=%s' % nxta)
				#logging.debug('nxta.class=%s' % nxta.__class__)
				st = unicode(nxta)
				if nvs.__class__ != nxta.__class__:
					#logging.debug('nxta.name=%s' % nxta.name)
					if nxta.name == 'table':
						st = ''
						if foundfirst:
							done = True
					if nxta.name == 'div' and 'class' in nxta._getAttrMap() and nxta['class'] == 'acl' and foundfirst:
						st = ''
						done = True
				
					if nxta.name == 'br':
						if not foundfirst:
							st = ''
					else:
						foundfirst = True
				else:
					foundfirst = True
					
				sst = sst + st
				nxta = nxta.nextSibling

		if sst is None:	
			raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
		
		return sst
			
class FPC_UnitTests(unittest.TestCase):
	def setUp(self):
		logging.basicConfig(level=logging.DEBUG)
		pass
	
	def testFictionPress(self):
		url = 'http://www.fictionpress.com/s/2725180/1/Behind_This_Facade'
		f = FPCom(url)
		urls = f.extractIndividualUrls()
		
		self.assertEquals('Behind This Facade', f.getStoryName())
		self.assertEquals('IntoxicatingMelody', f.getAuthorName())
	
		text = f.getText(url)
		self.assertTrue(text.find('Kale Resgerald at your service" He answered, "So, can we go now? Or do you want to') != -1)

if __name__ == '__main__':
	unittest.main()
