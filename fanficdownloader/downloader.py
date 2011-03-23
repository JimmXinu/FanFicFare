# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import os.path
import getpass
import logging
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs

import zipdir

import output
import adapter
from adapter import StoryArchivedAlready
from adapter import StoryDoesNotExist
from adapter import FailedToDownload
from adapter import InvalidStoryURL
from adapter import LoginRequiredException
import ffnet
import fpcom
import ficwad
import fictionalley
import hpfiction
import twilighted
import adastrafanfic
import whofic
import potionsNsnitches
import mediaminer

import time

class FanficLoader:
	'''A controller class which handles the interaction between various specific downloaders and writers'''
	booksDirectory = "books"
	standAlone = False
	
	def __init__(self, adapter, writerClass, quiet = False, inmemory = False, compress=True, overwrite=False):
		self.adapter = adapter
		self.writerClass = writerClass
		self.quiet = quiet
		self.inmemory = inmemory
		self.compress = compress
		self.badLogin = False
		self.overWrite = overwrite
			
	def getBooksDirectory(self):
		return self.booksDirectory

	def setBooksDirectory(self, bd):
		self.booksDirectory = bd
		return self.booksDirectory
	
	def getStandAlone(self):
		return self.standAlone

	def setStandAlone(self, sa):
		self.standAlone = sa
		return self.standAlone
	
	def getOverWrite(self):
		return self.overWrite

	def setOverWrite(self, sa):
		self.overWrite = sa
		return self.overWrite
	
	def getAdapter():
		return self.adapter
	
	def download(self):
		logging.debug("Trying to download the story")
		if self.adapter.requiresLogin():
			logging.debug("Story requires login")
			if not self.adapter.performLogin():
				logging.debug("Login/password problem")
				self.badLogin = True
				raise adapter.LoginRequiredException(self.adapter.url)
		
		urls = self.adapter.extractIndividualUrls()

		logging.debug("self.writerClass=%s" % self.writerClass)
		if self.standAlone and not self.inmemory:
			s = self.adapter.getOutputFileName(self.booksDirectory, self.writerClass.getFormatExt())
			logging.debug("Always overwrite? %s" % self.overWrite)
			if not self.overWrite:
				logging.debug("Checking if current archive of the story exists.  Filename=%s" % s)
				if not zipdir.checkNewer ( s, self.adapter.getStoryUpdated() ):
					raise StoryArchivedAlready("A Current archive file \"" + s + "\" already exists!  Skipping!")
		else:
			logging.debug("Do not check for existance of archive file.")

		self.writer = self.writerClass(self.booksDirectory, self.adapter, inmemory=self.inmemory, compress=self.compress)
		
		i = 1
		for u,n in urls:
			if not self.quiet:
				print('Downloading chapter %d/%d' % (i, len(urls)))
			text = self.adapter.getText(u)
			self.writer.writeChapter(i, n, text)
			i = i+1
			#time.sleep(2)
			
		self.writer.finalise()
		
		if self.inmemory:
			self.name = self.writer.name
			return self.writer.output.getvalue()
	

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG,format="%(levelname)s:%(filename)s(%(lineno)d):%(message)s")
	argvlen = len(sys.argv)
	url = None
	bookFormat = 'epub'
	if argvlen > 1:
		url = sys.argv[1]
	if argvlen > 2:
		bookFormat = sys.argv[2]
	
	if url is None: 
		print >> sys.stderr, "Usage: downloader.py URL Type"
		sys.exit(-1)
		
	if type(url) is unicode:
		print('URL is unicode')
		url = url.encode('latin1')
	url = url.strip()
	adapter = None
	writerClass = None
	
	if url.find('fanficauthors') != -1:
		print >> sys.stderr, "fanficauthors.net already provides ebooks"
		sys.exit(0)
	elif url.find('fictionalley') != -1:
		adapter = fictionalley.FictionAlley(url)
	elif url.find('ficwad') != -1:
		adapter = ficwad.FicWad(url)
	elif url.find('fanfiction.net') != -1:
		adapter = ffnet.FFNet(url)
	elif url.find('fictionpress.com') != -1:
		adapter = fpcom.FPCom(url)
	elif url.find('harrypotterfanfiction.com') != -1:
		adapter = hpfiction.HPFiction(url)
	elif url.find('twilighted.net') != -1:
		adapter = twilighted.Twilighted(url)
	elif url.find('adastrafanfic.com') != -1:
		adapter = adastrafanfic.Adastrafanfic(url)
	elif url.find('whofic.com') != -1:
		adapter = whofic.Whofic(url)
	elif url.find('potionsandsnitches.net') != -1:
		adapter = potionsNsnitches.PotionsNSnitches(url)
	elif url.find('mediaminer.org') != -1:
		adapter = mediaminer.MediaMiner(url)
	else:
		print >> sys.stderr, "Oi! I can haz not appropriate adapter for URL %s!" % url
		sys.exit(1)

	if bookFormat == 'epub':
		writerClass = output.EPubFanficWriter
	elif bookFormat == 'html':
		writerClass = output.HTMLWriter
	elif bookFormat == 'mobi':
		writerClass = output.MobiWriter
	elif bookFormat == 'text':
		writerClass = output.TextWriter
	
	if adapter.requiresLogin(url):
		print("Meow, URL %s requires you to haz been logged in! Please can I haz this datas?" % url)
		sys.stdout.write("Can I haz ur login? ")
		login = sys.stdin.readline().strip()
		password = getpass.getpass(prompt='Can I haz ur password? ')
		print("Login: `%s`, Password: `%s`" % (login, password))
		
		adapter.setLogin(login)
		adapter.setPassword(password)
		
	
	loader = FanficLoader(adapter, writerClass)
	loader.setStandAlone(True)
	if bookFormat != 'epub':
		loader.setOverWrite(True)
	

	try:
		loader.download()
	except FailedToDownload, ftd:
		print >> sys.stderr, str(ftd)
		sys.exit(2)		# Error Downloading
	except InvalidStoryURL, isu:
		print >> sys.stderr, str(isu)
		sys.exit(3)		# Unknown Error
	except StoryArchivedAlready, se:
		print >> sys.stderr, str(se)
		sys.exit(10)	# Skipped
	except StoryDoesNotExist, sdne:
		print >> sys.stderr, str(sdne)
		sys.exit(20) 	# Missing
	except LoginRequiredException, lre:
		print >> sys.stderr, str(lre)
		sys.exit(30) 	# Missing
	except Exception, e:
		print >> sys.stderr, str(e)
		sys.exit(99)		# Unknown Error
	
	sys.exit(0)
	
