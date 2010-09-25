# -*- coding: utf-8 -*-

import os
import re
import sys
import cgi
import uuid
import codecs
import shutil
import string
import base64
import os.path
import zipfile
import StringIO
import logging
import hashlib
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs

import zipdir
import html_constants
from constants import *

import html2text


class FanficWriter:
	def __init__(self):
		pass
		
	def writeChapter(self, title, text):
		pass
	
	def finalise(self):
		pass

class TextWriter(FanficWriter):
	htmlWriter = None
	
	def __init__(self, base, name, author, inmemory=False, compress=False):
		self.htmlWriter = HTMLWriter(base, name, author, True, False)
	
	def writeChapter(self, title, text):
		self.htmlWriter.writeChapter(title, text)
	
	def finalise(self):
		self.htmlWriter.finalise()
		self.output = StringIO.StringIO()
		self.output.write(html2text.html2text(self.htmlWriter.output.getvalue().decode('utf-8')).encode('utf-8'))
		self.name = self.htmlWriter.name
		

class HTMLWriter(FanficWriter):
	body = ''
	
	def __init__(self, base, name, author, inmemory=False, compress=False):
		self.basePath = base
		self.name = name.replace(" ", "_")
		self.storyTitle = name
		self.fileName = self.basePath + '/' + self.name + '.html'
		self.authorName = author
		
		self.inmemory = inmemory

		if not self.inmemory and os.path.exists(self.fileName):
			os.remove(self.fileName)
		
		if self.inmemory:
			self.output = StringIO.StringIO()
		else:
			self.output = open(self.fileName, 'w')
		
		self.xhtmlTemplate = string.Template(html_constants.XHTML_START)
		self.chapterStartTemplate = string.Template(html_constants.XHTML_CHAPTER_START)
	
	def _printableVersion(self, text):
		try:
			d = text.decode('utf-8')
			return d
		except:
			return text
	
	def writeChapter(self, title, text):
		title = self._printableVersion(title) #title.decode('utf-8')
		text = self._printableVersion(text) #text.decode('utf-8')
		self.body = self.body + '\n' + self.chapterStartTemplate.substitute({'chapter' : title})
		self.body = self.body + '\n' + text
	
	def finalise(self):
		html = self.xhtmlTemplate.substitute({'title' : self.storyTitle, 'author' : self.authorName, 'body' : self.body})
		soup = bs.BeautifulSoup(html)
		result = soup.prettify()
		
#		f = open(self.fileName, 'w')
#		f.write(result)
#		f.close()

		self.output.write(result)
		if not self.inmemory:
			self.output.close()

class EPubFanficWriter(FanficWriter):
	chapters = []
	
	files = {}
	
	def _writeFile(self, fileName, data):
		#logging.debug('_writeFile(`%s`, data)' % fileName)
		if fileName in self.files:
			try:
				d = data.decode('utf-8')
			except UnicodeEncodeError, e:
				d = data
			
			self.files[fileName].write(d)
		else:
			if self.inmemory:
				self.files[fileName] = StringIO.StringIO()
			else:
				self.files[fileName] = open(self.directory + '/' + fileName, 'w')
			
			self._writeFile(fileName, data)
		
		
	def _closeFiles(self):
		if not self.inmemory:
			for f in self.files:
				self.files[f].close()
	
	def __init__(self, base, name, author, inmemory=False, compress=True):
		self.basePath = base
		self.name = name.replace(" ", "_")
		self.storyTitle = name
		self.directory = self.basePath + '/' + self.name
		self.inmemory = inmemory
		self.authorName = author
		
		self.files = {}
		self.chapters = []
		
		if not self.inmemory:
			self.inmemory = True
			self.writeToFile = True
		else:
			self.writeToFile = False
		

		if not self.inmemory:
			if os.path.exists(self.directory):
				shutil.rmtree(self.directory)
		
			os.mkdir(self.directory)
		
			os.mkdir(self.directory + '/META-INF')
			os.mkdir(self.directory + '/OEBPS')
		
		self._writeFile('mimetype', MIMETYPE)
		self._writeFile('META-INF/container.xml', CONTAINER)
		self._writeFile('OEBPS/stylesheet.css', CSS)

	def _removeEntities(self, text):
		for e in entities:
			v = entities[e]
			text = text.replace(e, v)
		
		text = text.replace('&', '&amp;')
		
		return text
	
	def writeChapter(self, title, text):
		logging.debug("Writing chapter: %s" % title)
		try:
			fileName = base64.b64encode(title).replace('/', '_') + ".xhtml"
		except UnicodeEncodeError, e:
			fileName = base64.b64encode(title.encode('utf-8')).replace('/', '_') + ".xhtml"
#		title = cgi.esca#title.decode('utf-8')
#		sha = hashlib.sha224(title)
#		fileName = sha.hexdigest() + ".xhtml"
		#fileName = cgi.escape(title) + '.xhtml'
		filePath = self.directory + "/OEBPS/" + fileName
		
		fn = 'OEBPS/' + fileName
		
#		f = open(filePath, 'w')
		
		text = self._removeEntities(text)
		
		# BeautifulStoneSoup doesn't have any selfClosingTags by default.  
		# hr needs to be if it's going to work.
		self.soup = bs.BeautifulStoneSoup(text.decode('utf-8'), selfClosingTags=('hr'))

		allTags = self.soup.findAll(recursive=True)
		for t in allTags:
			for attr in t._getAttrMap().keys():
				if attr not in acceptable_attributes:
					del t[attr]

		allPs = self.soup.findAll(recursive=True)
		for p in allPs:
			if p.string != None and (len(p.string.strip()) == 0 or p.string.strip() == '&nbsp;' ) :
				p.extract()
				
		allBrs = self.soup.findAll(recursive=True, name = ["br", 'div'])
		for br in allBrs:
			if (br.string != None and len(br.string.strip()) != 0) or (br.contents != None):
				br.name = 'p'

#		cleanup(self.soup )
		
		text = self.soup.prettify()
		
		tt = self._removeEntities(title)
		
		self._writeFile(fn, XHTML_START % (tt, tt))
		self._writeFile(fn, text)
		self._writeFile(fn, XHTML_END)
#		print >> f, XHTML_START % (tt, tt)
#		f.write(text)
#		print >> f, XHTML_END
		
		self.chapters.append((title, fileName))
	
	def finalise(self):
		logging.debug("Finalising...")
		### writing table of contents -- ncx file
		
		tocFilePath = "OEBPS/toc.ncx"
#		toc = open(tocFilePath, 'w')
#		print >> toc, TOC_START % self.storyTitle
		self._writeFile(tocFilePath, TOC_START % self.storyTitle)
		### writing content -- opf file
		opfFilePath = "OEBPS/content.opf"
		
#		opf = open(opfFilePath, 'w')
		self._writeFile(opfFilePath, CONTENT_START % (uuid.uuid4().urn, self.storyTitle, self.authorName))
#		print >> opf, CONTENT_START % (uuid.uuid4().urn, self.storyTitle, self.authorName)

		ids = []
		
		i = 0
		for t,f in self.chapters:
			try:
				chapterId = base64.b64encode(t)
			except UnicodeEncodeError, e:
				chapterId = base64.b64encode(t.encode('utf-8'))
			
			self._writeFile(tocFilePath, TOC_ITEM % (chapterId, i, cgi.escape(t), f))
			self._writeFile(opfFilePath, CONTENT_ITEM % (chapterId, f))
			
			ids.append(chapterId)
			
			i = i + 1
			
#		logging.d('Toc and refs printed, proceesing to ref-ids....')
		
		self._writeFile(tocFilePath, TOC_END)
		self._writeFile(opfFilePath, CONTENT_END_MANIFEST)
		
		for chapterId in ids:
			self._writeFile(opfFilePath, CONTENT_ITEMREF % chapterId)
		
		self._writeFile(opfFilePath, CONTENT_END)
		
		self._closeFiles()
		
		filename = self.directory + '.epub'
		
		zipdata = zipdir.inMemoryZip(self.files)
		
		if self.writeToFile:
			f = open(filename, 'wb')
			f.write(zipdata.getvalue())
			f.close()
		else:
			self.output = zipdata
			
#		zipdir.toZip(filename, self.directory)
