# -*- coding: utf-8 -*-

import os
import re
import sys
import cgi
import uuid
import unicodedata
import codecs
import shutil
import string
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

import mobi
import zipdir
import html_constants
from constants import *


import html2text
import datetime


class FanficWriter:
	def __init__(self):
		pass
		
	def writeChapter(self, index, title, text):
		pass
	
	def finalise(self):
		pass

	@staticmethod
	def getFormatName():
		return 'base'
	
	@staticmethod	
	def getFormatExt():
		return '.bse'
	
class TextWriter(FanficWriter):
	htmlWriter = None
	
	@staticmethod
	def getFormatName():
		return 'text'
	
	@staticmethod	
	def getFormatExt():
		return '.txt'
	
	def __init__(self, base, adapter, inmemory=False, compress=False):
		self.inmemory = inmemory
		self.htmlWriter = HTMLWriter(base, adapter, True, False)
	
	def writeChapter(self, index, title, text):
		self.htmlWriter.writeChapter(index, title, text)
	
	def finalise(self):
		self.htmlWriter.finalise()
		self.name=self.htmlWriter.name
		self.fileName = self.htmlWriter.fileName.replace(".html",".txt")
		if self.inmemory:
			self.output = StringIO.StringIO()
		else:
			self.output = open(self.fileName, 'w')
		
		self.output.write(html2text.html2text(self.htmlWriter.output.getvalue().decode('utf-8')).encode('utf-8'))
		
		if not self.inmemory:
			self.output.close()
		

class MobiWriter(FanficWriter):
	chapters = []
	files = {}

	@staticmethod
	def getFormatName():
		return 'mobi'

	@staticmethod	
	def getFormatExt():
		return '.mobi'

	def __init__(self, base, adapter, inmemory=False, compress=False):
		self.basePath = base
		self.storyTitle = removeEntities(adapter.getStoryName())
		self.name = makeAcceptableFilename(adapter.getOutputName())
		self.fileName = self.basePath + '/' + self.name + self.getFormatExt()
		self.authorName = removeEntities(adapter.getAuthorName())
		self.publisher = adapter.getPublisher()
		self.adapter = adapter
		self.mobi = mobi
		self.inmemory = inmemory

		self.files = {}
		self.chapters = []

		if not self.inmemory and os.path.exists(self.fileName):
			os.remove(self.fileName)

		if self.inmemory:
			self.output = StringIO.StringIO()
		else:
			self.output = open(self.fileName, 'wb')

		self.xhtmlTemplate = string.Template(html_constants.XHTML_START)
		self.chapterStartTemplate = string.Template(html_constants.XHTML_CHAPTER_START)

	def _printableVersion(self, text):
		try:
			d = text.decode('utf-8')
			return d
		except:
			return text

	def _writeFile(self, fileName, data):
		#logging.debug('_writeFile(`%s`, data)' % fileName)
		if fileName in self.files:
			try:
				d = data.decode('utf-8')
			except UnicodeEncodeError, e:
				d = data
			
			self.files[fileName].write(d)
		else:
			self.files[fileName] = StringIO.StringIO()			
			self._writeFile(fileName, data)

	def _getFilesStrings(self):
		strings = []
		if "title_page.xhtml" in self.files:
			strings.append(self.files["title_page.xhtml"].getvalue())
			del(self.files["title_page.xhtml"])

		keys = self.files.keys()
		keys.sort()

		# Assumed all other files are chapter0000.xhtml.
		for fn in keys:
			strings.append(self.files[fn].getvalue())
			
		return strings
		
	def writeChapter(self, index, title, text):
		title = removeEntities(title)
		logging.debug("Writing chapter: %s" % title)
		#title = self._printableVersion(title) #title.decode('utf-8')
		text = removeEntities(text)
                #text = self._printableVersion(text) #text.decode('utf-8')

		# BeautifulStoneSoup doesn't have any selfClosingTags by default.  
		# hr & br needs to be if they're going to work.
		# Some stories do use multiple br tags as their section breaks...
		self.soup = bs.BeautifulStoneSoup(text, selfClosingTags=('br','hr'))

		allTags = self.soup.findAll(recursive=True)
		for t in allTags:
			for attr in t._getAttrMap().keys():
				if attr not in acceptable_attributes:
					del t[attr]
			# these are not acceptable strict XHTML.  But we do already have 
			# CSS classes of the same names defined in constants.py
			if t.name in ('u'):
				t['class']=t.name
				t.name='span'
			if t.name in ('center'):
				t['class']=t.name
				t.name='div'
			# removes paired, but empty tags.
			if t.string != None and len(t.string.strip()) == 0 :
				t.extract()

		text = self.soup.__str__('utf8')
		
		# ffnet(& maybe others) gives the whole chapter text
		# as one line.  This causes problems for nook(at
		# least) when the chapter size starts getting big
		# (200k+) Using Soup's prettify() messes up italics
		# and such.  Done after soup extract so <p> and <br>
		# tags are normalized.  Doing it here seems less evil
		# than hacking BeautifulSoup, but it's debatable.
		text = text.replace('</p>','</p>\n').replace('<br />','<br />\n')
		
		filename="chapter%04d.xhtml" % index
		self._writeFile(filename, XHTML_START % (title, title))
		self._writeFile(filename, text)
		self._writeFile(filename, XHTML_END)
		
		#self.body = self.body + '\n' + self.chapterStartTemplate.substitute({'chapter' : title})
		#self.body = self.body + '\n' + text

	def finalise(self):
		logging.debug("Finalising...")

		published = self.adapter.getStoryPublished().strftime("%Y-%m-%d")
		createda = self.adapter.getStoryCreated().strftime("%Y-%m-%d %H:%M:%S")
		created = self.adapter.getStoryCreated().strftime("%Y-%m-%d")
		updated = self.adapter.getStoryUpdated().strftime("%Y-%m-%d")
		updateyy = self.adapter.getStoryUpdated().strftime("%Y")
		updatemm = self.adapter.getStoryUpdated().strftime("%m")
		updatedd = self.adapter.getStoryUpdated().strftime("%d")
		calibre = self.adapter.getStoryUpdated().strftime("%Y-%m-%dT%H:%M:%S")
		
		description = self.adapter.getStoryDescription()
		if hasattr(description, "text"):
			description = description.text
		prevalue=description
		try:
			description = unicode(description)
		except:
			description=prevalue
			
		if description is not None and len(description) > 0:
			description = description.replace ('\\\'', '\'').replace('\\\"', '\"')
			description =  removeEntities(description)
		else:
			description = ' '

		### writing content -- title page
		titleFilePath = "title_page.xhtml"
		self._writeFile(titleFilePath, TITLE_HEADER % (self.authorName, self.storyTitle, self.adapter.getStoryURL(), self.storyTitle, self.adapter.getAuthorURL(), self.authorName))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Category:', self.adapter.getCategory()))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Genre:', self.adapter.getGenre())) 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Status:', self.adapter.getStoryStatus()))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Published:', published))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Updated:', updated))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Packaged:', createda))
		tmpstr = self.adapter.getStoryRating() + " / " + self.adapter.getStoryUserRating()		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Rating Age/User:', tmpstr))
		tmpstr = unicode(self.adapter.getNumChapters()) + " / " + commaGroups(unicode(self.adapter.getNumWords()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Chapters/Words:', tmpstr))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Publisher:', self.adapter.getHost()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Story ID:', self.adapter.getStoryId()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Author ID:', self.adapter.getAuthorId()))

		self._writeFile(titleFilePath, TITLE_FOOTER % description )

		

		c = mobi.Converter(title=self.storyTitle,
				   author=self.authorName,
				   publisher=self.publisher)
		mobidata = c.ConvertStrings(self._getFilesStrings())

		self.output.write(mobidata)
		if not self.inmemory:
			self.output.close()
#		zipdir.toZip(filename, self.directory)
			


class HTMLWriter(FanficWriter):
	body = ''
	
	@staticmethod
	def getFormatName():
		return 'html'
	
	@staticmethod	
	def getFormatExt():
		return '.html'
	
	def __init__(self, base, adapter, inmemory=False, compress=False, mobi = False):
		self.basePath = base
		self.storyTitle = removeEntities(adapter.getStoryName())
		self.name = makeAcceptableFilename(adapter.getOutputName())
		self.fileName = self.basePath + '/' + self.name + self.getFormatExt()
		self.authorName = removeEntities(adapter.getAuthorName())
		self.adapter = adapter
		self.mobi = mobi
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
	
	def writeChapter(self, index, title, text):
		title = self._printableVersion(title) #title.decode('utf-8')
		text = self._printableVersion(text) #text.decode('utf-8')
		self.body = self.body + '\n' + self.chapterStartTemplate.substitute({'chapter' : title})
		self.body = self.body + '\n' + text
	
	def finalise(self):
		html = self.xhtmlTemplate.substitute({'title' : self.storyTitle, 'author' : self.authorName, 'body' : self.body})
		soup = bs.BeautifulSoup(html)
		result = soup.__str__('utf8')
		
#		f = open(self.fileName, 'w')
#		f.write(result)
#		f.close()

		self.output.write(result)
		if not self.inmemory:
			self.output.close()

class EPubFanficWriter(FanficWriter):
	chapters = []
	files = {}
	
	@staticmethod
	def getFormatName():
		return 'epub'
	
	@staticmethod	
	def getFormatExt():
		return '.epub'
	
	def __init__(self, base, adapter, inmemory=False, compress=True):
		self.basePath = base
		self.storyTitle = removeEntities(adapter.getStoryName())
		self.name = makeAcceptableFilename(adapter.getOutputName())
		self.directory = self.basePath + '/' + self.name
		self.authorName = removeEntities(adapter.getAuthorName())
		self.inmemory = inmemory
		self.adapter = adapter
		
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
				self.files[fileName] = open(self.directory + '/' + fileName, encoding='utf-8', mode='w')
			
			self._writeFile(fileName, data)
		
		
	def _closeFiles(self):
		if not self.inmemory:
			for f in self.files:
				self.files[f].close()
	
	def writeChapter(self, index, title, text):
		title = removeEntities(title)
		logging.debug("Writing chapter: %s" % title)
		fileName="chapter%04d.xhtml" % index

		filePath = self.directory + "/OEBPS/" + fileName
		
		fn = 'OEBPS/' + fileName
		
#		f = open(filePath, 'w')
		
		text = removeEntities(text)
		
		# BeautifulStoneSoup doesn't have any selfClosingTags by default.  
		# hr & br needs to be if they're going to work.
		# Some stories do use multiple br tags as their section breaks...
		self.soup = bs.BeautifulStoneSoup(text, selfClosingTags=('br','hr'))

		allTags = self.soup.findAll(recursive=True)
		for t in allTags:
			for attr in t._getAttrMap().keys():
				if attr not in acceptable_attributes:
					del t[attr]
			# these are not acceptable strict XHTML.  But we do already have 
			# CSS classes of the same names defined in constants.py
			if t.name in ('u'):
				t['class']=t.name
				t.name='span'
			if t.name in ('center'):
				t['class']=t.name
				t.name='div'
			# removes paired, but empty tags.
			if t.string != None and len(t.string.strip()) == 0 :
				t.extract()

		text = self.soup.__str__('utf8')
		
		# ffnet(& maybe others) gives the whole chapter text
		# as one line.  This causes problems for nook(at
		# least) when the chapter size starts getting big
		# (200k+) Using Soup's prettify() messes up italics
		# and such.  Done after soup extract so <p> and <br>
		# tags are normalized.  Doing it here seems less evil
		# than hacking BeautifulSoup, but it's debatable.
		text = text.replace('</p>','</p>\n').replace('<br />','<br />\n')
		
		self._writeFile(fn, XHTML_START % (title, title))
		self._writeFile(fn, text)
		self._writeFile(fn, XHTML_END)
#		print >> f, XHTML_START % (title, title)
#		f.write(text)
#		print >> f, XHTML_END
		
		self.chapters.append((title, fileName))
	
	def finalise(self):
		logging.debug("Finalising...")
		### writing table of contents -- ncx file
		
		tocFilePath = "OEBPS/toc.ncx"
#		toc = open(tocFilePath, 'w')
#		print >> toc, TOC_START % self.storyTitle
		self._writeFile(tocFilePath, TOC_START % (self.adapter.getUUID(), self.storyTitle))

		published = self.adapter.getStoryPublished().strftime("%Y-%m-%d")
		createda = self.adapter.getStoryCreated().strftime("%Y-%m-%d %H:%M:%S")
		created = self.adapter.getStoryCreated().strftime("%Y-%m-%d")
		updated = self.adapter.getStoryUpdated().strftime("%Y-%m-%d")
		updateyy = self.adapter.getStoryUpdated().strftime("%Y")
		updatemm = self.adapter.getStoryUpdated().strftime("%m")
		updatedd = self.adapter.getStoryUpdated().strftime("%d")
		calibre = self.adapter.getStoryUpdated().strftime("%Y-%m-%dT%H:%M:%S")
		
		description = self.adapter.getStoryDescription()
		if hasattr(description, "text"):
			description = description.text
		prevalue=description
		try:
			description = unicode(description)
		except:
			description=prevalue
			
		if description is not None and len(description) > 0:
			description = description.replace ('\\\'', '\'').replace('\\\"', '\"')
			description =  removeEntities(description)
		else:
			description = ' '

		### writing content -- title page
		titleFilePath = "OEBPS/title_page.xhtml"
		self._writeFile(titleFilePath, TITLE_HEADER % (self.authorName, self.storyTitle, self.adapter.getStoryURL(), self.storyTitle, self.adapter.getAuthorURL(), self.authorName))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Category:', self.adapter.getCategory()))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Genre:', self.adapter.getGenre())) 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Status:', self.adapter.getStoryStatus()))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Published:', published))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Updated:', updated))		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Packaged:', createda))
		tmpstr = self.adapter.getStoryRating() + " / " + self.adapter.getStoryUserRating()		 
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Rating Age/User:', tmpstr))
		tmpstr = unicode(self.adapter.getNumChapters()) + " / " + commaGroups(unicode(self.adapter.getNumWords()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Chapters/Words:', tmpstr))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Publisher:', self.adapter.getHost()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Story ID:', self.adapter.getStoryId()))
		self._writeFile(titleFilePath, TITLE_ENTRY % ('Author ID:', self.adapter.getAuthorId()))

		self._writeFile(titleFilePath, TITLE_FOOTER % description )

		### writing content -- opf file
		opfFilePath = "OEBPS/content.opf"

#		opf = open(opfFilePath, 'w')
		self._writeFile(opfFilePath, CONTENT_START % (uuid.uuid4().urn, self.storyTitle, self.authorName, self.adapter.getLanguageId(), published, created, updated, calibre, description))

		if self.adapter.storyStatus != 'Unknown':
			self.adapter.addSubject(self.adapter.storyStatus)
		i = 0
		subjs = []
		subjs = self.adapter.getSubjects()
		for subj in subjs:
			self._writeFile(opfFilePath, CONTENT_SUBJECT % subj)
			i = i + 1
		if (i <= 0):
			self._writeFile(opfFilePath, CONTENT_SUBJECT % "FanFiction")
		
		subj = "Last Update Year/Month: " + updateyy + "/" + updatemm
		self._writeFile(opfFilePath, CONTENT_SUBJECT % subj)

		subj = "Last Update: " + updateyy + "/" + updatemm + "/" + updatedd
		self._writeFile(opfFilePath, CONTENT_SUBJECT % subj)

		self._writeFile(opfFilePath, CONTENT_END_METADATA % (self.adapter.getPublisher(), self.adapter.getUUID(), self.adapter.getStoryURL(), self.adapter.getStoryURL(), self.adapter.getStoryUserRating()))
#		print >> opf, CONTENT_START % (uuid.uuid4().urn, self.storyTitle, self.authorName)

		ids = []
		
		i = 0

		t = "Title Page"
		f = "title_page.xhtml"
		chapterId = "title_page"		
		self._writeFile(tocFilePath, TOC_ITEM % (chapterId, i, t, f))
		self._writeFile(opfFilePath, CONTENT_ITEM % (chapterId, f))
		
		ids.append(chapterId)
		
		i = i + 1
		
		for t,f in self.chapters:
			chapterId = "chapter%04d" % i
			
			self._writeFile(tocFilePath, TOC_ITEM % (chapterId, i, t, f))
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
		
		filename = self.directory + self.getFormatExt()
		
		zipdata = zipdir.inMemoryZip(self.files)
		
		if self.writeToFile:
			f = open(filename, 'wb')
			f.write(zipdata.getvalue())
			f.close()
		else:
			self.output = zipdata
			
#		zipdir.toZip(filename, self.directory)

def unirepl(match):
	"Return the unicode string for a decimal number"
	if match.group(1)=='x':
		radix=16
	else:
		radix=10
	value = int(match.group(2), radix )
	return unichr(value)

def replaceNumberEntities(data):
	p = re.compile(r'&#(x?)(\d+);')
	return p.sub(unirepl, data)

def replaceNotEntities(data):
	# not just \w or \S.  regexp from c:\Python25\lib\sgmllib.py
	# (or equiv), SGMLParser, entityref
	p = re.compile(r'&([a-zA-Z][-.a-zA-Z0-9]*);')
	return p.sub(r'&\1', data)

def removeEntities(text):
	# replace numeric versions of [&<>] with named versions.
	
	if text is None:
		return text
	try:
		t = text.decode('utf-8')
	except UnicodeEncodeError, e:
		try:
			t = text.encode ('ascii', 'xmlcharrefreplace') 
		except UnicodeEncodeError, e:
			t = text
	text = t 
	text = re.sub(r'&#0*38;','&amp;',text)
	text = re.sub(r'&#0*60;','&lt;',text)
	text = re.sub(r'&#0*62;','&gt;',text)
	
	# replace remaining &#000; entities with unicode value, such as &#039; -> '
	text = replaceNumberEntities(text)

	# replace several named entities with character, such as &mdash; -> -
	# see constants.py for the list.
	# reverse sort will put entities with ; before the same one without, when valid.
	for e in reversed(sorted(entities.keys())):
		v = entities[e]
		try:
			text = text.replace(e, v)
		except UnicodeDecodeError, ex:
			# for the pound symbol in constants.py
			text = text.replace(e, v.decode('utf-8'))

	# SGMLParser, and in turn, BeautifulStoneSoup doesn't parse
	# entities terribly well and inserts (;) after something that
	# it thinks might be an entity.  AT&T becomes AT&T; All of my
	# attempts to fix this by changing the input to
	# BeautifulStoneSoup break something else instead.  But at
	# this point, there should be *no* real entities left, so find
	# these not-entities and removing them here should be safe.
	text = replaceNotEntities(text)
	
	# &lt; &lt; and &amp; are the only html entities allowed in xhtml, put those back.
	text = text.replace('&', '&amp;').replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')
		
	return text
	
def makeAcceptableFilename(text):
	return re.sub('[^a-zA-Z0-9_-]+','',removeEntities(text).replace(" ", "_").replace(":","_"))	

def commaGroups(s):
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))
