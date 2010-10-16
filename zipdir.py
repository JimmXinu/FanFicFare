import os
import zipfile
import logging

import StringIO

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
