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
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs

import zipdir
import html_constants
from constants import *



class FanficWriter:
	def __init__(self):
		pass
		
	def writeChapter(self, title, text):
		pass
	
	def finalise(self):
		pass

class HTMLWriter(FanficWriter):
	body = ''
	
	def __init__(self, base, name, author, inmemory=False):
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
		
	def writeChapter(self, title, text):
		title = title.decode('utf-8')
		text = text.decode('utf-8')
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
	
	def __init__(self, base, name, author, inmemory=False):
		self.basePath = base
		self.name = name.replace(" ", "_")
		self.storyTitle = name
		self.directory = self.basePath + '/' + self.name
		
		self.authorName = author

		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)
		
		os.mkdir(self.directory)
		
		os.mkdir(self.directory + '/META-INF')
		os.mkdir(self.directory + '/OEBPS')
		
		print >> codecs.open(self.directory + '/mimetype', 'w', 'utf-8'), MIMETYPE
		print >> codecs.open(self.directory + '/META-INF/container.xml', 'w', 'utf-8'), CONTAINER
		print >> codecs.open(self.directory + '/OEBPS/stylesheet.css', 'w', 'utf-8'), CSS

	def _removeEntities(self, text):
		for e in entities:
			v = entities[e]
			text = text.replace(e, v)
		
		text = text.replace('&', '&amp;')
		
		return text
	
	def writeChapter(self, title, text):
		fileName = base64.b64encode(title).replace('/', '_') + ".xhtml"
		filePath = self.directory + "/OEBPS/" + fileName
		
		f = open(filePath, 'w')
		
		text = self._removeEntities(text)
		
		self.soup = bs.BeautifulStoneSoup(text)

		allTags = self.soup.findAll(recursive=True)
		for t in allTags:
			for attr in t._getAttrMap().keys():
				if attr not in acceptable_attributes:
					del t[attr]
	    
		allPs = self.soup.findAll(recursive=True)
		for p in allPs:
			if p.string != None and (len(p.string.strip()) == 0 or p.string.strip() == '&nbsp;' ) :
				p.extract()
				
		allBrs = self.soup.findAll(recursive=True, name = ["br", "hr"])
		for br in allBrs:
			if (br.string != None and len(br.string.strip()) != 0) or (br.contents != None):
				br.name = 'p'

#		cleanup(self.soup )
		
		text = self.soup.prettify()
		
		tt = self._removeEntities(title)
		
		print >> f, XHTML_START % (tt, tt)
		f.write(text)
		print >> f, XHTML_END
		
		self.chapters.append((title, fileName))
	
	def finalise(self):
		print("Finalising...")
		### writing table of contents -- ncx file
		
		tocFilePath = self.directory + "/OEBPS/toc.ncx"
		toc = open(tocFilePath, 'w')
		print >> toc, TOC_START % self.storyTitle

		print("Printing toc and refs")

		### writing content -- opf file
		opfFilePath = self.directory + "/OEBPS/content.opf"
		opf = open(opfFilePath, 'w')
		
		print >> opf, CONTENT_START % (uuid.uuid4().urn, self.storyTitle, self.authorName)

		ids = []
		
		i = 0
		for t,f in self.chapters:
			chapterId = base64.b64encode(t)
			print >> toc, TOC_ITEM % (chapterId, i, cgi.escape(t), f)
			
			print >> opf, CONTENT_ITEM % (chapterId, f)
			
			ids.append(chapterId)
			
			i = i + 1
			
		print('Toc and refs printed, proceesing to ref-ids....')
		
		print >> toc, TOC_END
		print >> opf, CONTENT_END_MANIFEST		
		
		for chapterId in ids:
			print >> opf, CONTENT_ITEMREF % chapterId
		
		print >> opf, CONTENT_END
		
		opf.close()
		toc.close()
		
		print('Finished')

		filename = self.directory + '.epub'
		zipdir.toZip(filename, self.directory)
