import os
import zipfile

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

if __name__ == '__main__':
	toZip('sample.epub', "books/A_Time_To_Reflect")
	z = zipfile.ZipFile('sample.epub', 'r')