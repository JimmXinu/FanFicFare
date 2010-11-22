# -*- coding: utf-8 -*-

from __future__ import with_statement

import sys
import os
import zlib
import zipfile
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from contextlib import closing
import logging

import BeautifulSoup as bs
import htmlentitydefs as hdefs
import time
import datetime
from datetime import timedelta

import StringIO

class InvalidEPub(Exception):
    pass

def checkNewer(filename, curdte):
	ret = True
	
	if not os.path.isfile(filename):
		logging.debug('File %s does not already exist.' % filename)
		return ret
	
	#logging.debug('filename=%s, curdte=%s' % (filename, curdte))
	lastdate = None
	with closing(ZipFile(open(filename, 'rb'))) as epub:
		titleFilePath = "OEBPS/title_page.xhtml"
		contentFilePath = "OEBPS/content.opf"
		
		namelist = set(epub.namelist())
		#logging.debug('namelist=%s' % namelist)
		if 'mimetype' not in namelist or \
		   'META-INF/container.xml' not in namelist:
			#raise InvalidEPub('%s: not a valid EPUB' % filename)
			logging.debug('File %s is not a valid EPub format file.' % filename)
			return ret
		
		if contentFilePath not in namelist:
			return ret	# file is not newer
		
		data = epub.read(contentFilePath)
		soup = bs.BeautifulStoneSoup(data)
		lstdte = soup.find ('dc:date', {'opf:event' : 'modification'})
		#logging.debug('lstdte=%s' % lstdte.string)
		if lstdte is None and titleFilePath in namelist:
			data = epub.read(titleFilePath)
			soup = bs.BeautifulStoneSoup(data)
			fld = ''
			allTDs = soup.findAll ('td')
			for td in allTDs:
				b = td.find ('b')
				if b is not None:
					fld = b.string
				if td.string is not None and fld == "Updated:":
					lastdate = td.string
					#logging.debug('title lastdate=%s' % lastdate)
		else:
			lastdate = lstdte.string.strip(' ')
			#logging.debug('contents lastdate=%s' % lastdate)
	
	if lastdate is not None:	
		currUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(curdte.strftime('%Y-%m-%d'), "%Y-%m-%d")))
		storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(lastdate, "%Y-%m-%d")))
		logging.debug('File %s last update date is %s, comparing to %s' % (filename, storyUpdated, currUpdated))
		if currUpdated <= storyUpdated :	
			ret = False
	
	logging.debug("Does %s need to be updated? %s" % (filename, ret))
	return ret


def toZip(filename, directory):
	zippedHelp = zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED)
	lst = os.listdir(directory)
	
	for entity in lst:
		if entity.startswith('.'):
			continue

		each = os.path.join(directory,entity)
		print(each)

		if os.path.isfile(each):
			print(each)
			# epub standard requires mimetype to be uncompressed and first file.
			if entity == 'mimetype':
				zippedHelp.write(each, arcname=entity, compress_type=zipfile.ZIP_STORED)
			else:
				zippedHelp.write(each, arcname=entity)
		else:
			addFolderToZip(zippedHelp,entity, each)
 	
	zippedHelp.close()

def addFolderToZip(zippedHelp,folder,fpath):
	#print('addFolderToZip(%s)' % folder)
	
	if folder == '.' or folder == '..':
		return
	
	folderFiles = os.listdir(fpath)
	for f in folderFiles:
		if os.path.isfile(fpath + '/' + f):
			#print('basename=%s' % os.path.basename(fpath + '/' + f))
			zippedHelp.write(fpath + '/' + f, folder + '/' + f, zipfile.ZIP_DEFLATED)
		elif os.path.isdir(f):
			addFolderToZip(zippedHelp,f)

def inMemoryZip(files):
	# files have a structure of {'path/to/file' => content} dictionary
	io = StringIO.StringIO()

	if 'mimetype' in files:
		# This fixes the uncompressed mimetype-first issue by opening
		# the in memory file as STORE, putting in the mimetype, then
		# closing and re-opening with DEFLATED.  while it is often
		# true that mimetype is the first file, we can't assume it,
		# because the dict object is defined as unordered.
		path='mimetype'
		memzip = zipfile.ZipFile(io, 'a', compression=zipfile.ZIP_STORED)
		memzip.debug = 3
		if type(files[path]) != type('str'):
			data = files[path].getvalue()
		else:
			data = files[path]
		
		logging.debug("Writing ZIP path %s" % path)
		try:
			memzip.writestr(path, data.encode('utf-8'))
		except UnicodeDecodeError, e:
			memzip.writestr(path.encode('utf-8'), data.encode('utf-8'))
		
		memzip.close()

		# remove it from the files dict.
		del(files['mimetype'])
	
	# open in 'a' append mode.
	memzip = zipfile.ZipFile(io, 'a', compression=zipfile.ZIP_DEFLATED)
	memzip.debug = 3
	
	for path in files:
		if type(files[path]) != type('str'):
			data = files[path].getvalue()
		else:
			data = files[path]
		
#		logging.debug(data)
		logging.debug("Writing ZIP path %s" % path)
		try:
			memzip.writestr(path, data.encode('utf-8'))
		except UnicodeDecodeError, e:
			memzip.writestr(path.encode('utf-8'), data.encode('utf-8'))

	# declares all the files created by Windows.  
	for zf in memzip.filelist:
		zf.create_system = 0
	
	memzip.close()
	
	return io

if __name__ == '__main__':
#	toZip('sample.epub', "books/A_Time_To_Reflect")
#	z = zipfile.ZipFile('sample.epub', 'r')
	files = {'test.txt' : 'test', 'data/abc.txt' : 'abc'}
	data = inMemoryZip(files)
	f = open('res.zip', 'w')
	f.write(data)
	f.close()
