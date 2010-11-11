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


import ffnet
import fpcom
import ficwad
import output
import adapter
import fictionalley
import hpfiction
import twilighted
import potionsNsnitches

import time

class FanficLoader:
	'''A controller class which handles the interaction between various specific downloaders and writers'''
	booksDirectory = "books"
	
	def __init__(self, adapter, writerClass, quiet = False, inmemory = False, compress=True):
		self.adapter = adapter
		self.writerClass = writerClass
		self.quiet = quiet
		self.inmemory = inmemory
		self.compress = compress
		self.badLogin = False
		self.overWrite = True
	
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

		s = self.booksDirectory + "/" + self.adapter.getOutputName() + "." + format
		if not self.overWrite and os.path.isfile(s):
			print >> sys.stderr, "File " + s + " already exists!  Skipping!"
			exit(10)

		self.writer = self.writerClass(self.booksDirectory, self.adapter, inmemory=self.inmemory, compress=self.compress)
		
		i = 1
		for u,n in urls:
			if not self.quiet:
				print('Downloading chapter %d/%d' % (i, len(urls)))
			text = self.adapter.getText(u)
			self.writer.writeChapter(i, n, text)
			i = i+1
			# time.sleep(2)
			
		self.writer.finalise()
		
		if self.inmemory:
			self.name = self.writer.name
			return self.writer.output.getvalue()
	

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	(url, format) = sys.argv[1:]
	# (url) = sys.argv[1]
	# format = 'epub'
	
	if type(url) is unicode:
		print('URL is unicode')
		url = url.encode('latin1')
	
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
	elif url.find('potionsandsnitches.net') != -1:
		adapter = potionsNsnitches.PotionsNSnitches(url)
	else:
		print >> sys.stderr, "Oi! I can haz not appropriate adapter for URL %s!" % url
		sys.exit(1)

	if format == 'epub':
		writerClass = output.EPubFanficWriter
	elif format == 'html':
		writerClass = output.HTMLWriter
	
	if adapter.requiresLogin(url):
		print("Meow, URL %s requires you to haz been logged in! Please can I haz this datas?" % url)
		sys.stdout.write("Can I haz ur login? ")
		login = sys.stdin.readline().strip()
		password = getpass.getpass(prompt='Can I haz ur password? ')
		print("Login: `%s`, Password: `%s`" % (login, password))
		
		adapter.setLogin(login)
		adapter.setPassword(password)
		
	
	loader = FanficLoader(adapter, writerClass)
	loader.download()
	
