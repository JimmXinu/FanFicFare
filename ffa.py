import os
import re
import sys
import cgi
import uuid
import shutil
import base64
import os.path
import urllib as u
import pprint as pp
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs

from constants import *

from ficwad import *

class FFA:
	storyName = None
	
	def __init__(self):
		self.grabUrl = re.compile('(\<option.+value=\")(.+?)\"\>(.+?)\<')
		self.grabAuthor = re.compile('.+pemail.+\'(\w+)')
	
	def getPasswordLine(self):
		return '<input type="password" name="pass"'
		
	def getLoginScript(self):
		return '/scripts/login.php'
		
	def getLoginPasswordOthers(self):
		login = dict(login = 'name', password = 'pass')
		other = dict(submit = 'Log In', remember='yes')
		return (login, other)
	
	def getPrintableUrl(self, url):
		return url + '?print=yes'
	
	def _findIndex(self, lines, what, start):
		for i in range(start, len(lines)):
			if lines[i].find(what) != -1:
				return i
		return -1
	
	def extractIndividualUrls(self, data, host, first, fetch = False):
		lines = data.split('\n')
		
		optionLines = filter(lambda x : x.find('<option value="') != -1, lines)
		
		authorLines = filter(lambda x : x.find('pemail') != -1, lines)
		for al in authorLines:
			m = self.grabAuthor.match(al)
			if m != None:
				self.authorName = m.group(1)
				break
				
		
		optionsLines = optionLines[:len(optionLines)/2]
		
		storyName = first.split("/")[1]
		
		result = []
		urls = []
		for line in optionLines:
			m = self.grabUrl.match(line)
			u = m.group(2)
			if u.find('" selected="selected') != -1:
				u = u.replace('" selected="selected', '')
			
			if u in urls:
				continue
			else:
				urls.append(u)
			
			result.append((self.getPrintableUrl(storyName + "/" + u), m.group(3)))
		
		self.soup = bs.BeautifulSoup(data)
		titles = self.soup.findAll(name = 'title', recursive=True)
		if len(titles) > 0:
			title = titles[0]
			print(title)
			(website, rest) = title.string.split('::')
			story_chapter = rest.split("-")
			
			story = story_chapter[0].strip()
			self.storyName = story
		
		return result
	
	def getStoryName(self):
		return self.storyName
	
	def getAuthorName(self):
		return self.authorName
	
	def getText(self, data, fetch = False):
		lines = data.split('\n')
		begin = self._findIndex(lines, '</select>', 0)+1
		if begin == 0:
			begiun = self._findIndex(lines, '<div><p>', 24)
		
		if begin == 0:
			print('BAD start')
			pp.pprint(lines)
			sys.abort()
		end = self._findIndex(lines, '<form action="index.php"><div class="topandbotline"', begin)
		print('<!-- ========= begin=%d, end=%d ============= -->' % (begin, end))
		return "\n".join(lines[begin:end])

class Downloader:
	login = None
	password = None
	url = None
	host = None
	first = None
	opener = None
	
	writer = None
	
	def __init__(self, url, login, password):
		self.login = login
		self.password = password
		self.url = url

		self.infoProvider = FicWad() #FFA()

		parse = up.urlparse(url)
		self.host = parse.scheme + '://' + parse.netloc
		self.first = parse.path;
		
		self.loginUrl = self.host + self.infoProvider.getLoginScript()
		
		self.opener = u2.build_opener(u2.HTTPCookieProcessor())
		
	
	def _loginRequired(self):
		print('is login required?')
		resp = self.opener.open(self.url)
		data = resp.read()
		if data.find(self.infoProvider.getPasswordLine()) != -1:
			print('yep')
			return True
		else:
			print('nada')
			return False
		
	def _login(self):
		(login, data) = self.infoProvider.getLoginPasswordOthers()

		data[login['login']] = self.login
		data[login['password']] = self.password
		
		urlvals = u.urlencode(data)
		req = self.opener.open(self.loginUrl, urlvals)
		
		if req.read().find(self.infoProvider.getPasswordLine()) != -1:
			return False
		else:
			return True
	
	def _getContent(self, url):
		print("<!-- Opening %s -->" % url)
		return self.opener.open(url).read()
	
	def download(self):
		first = self._getContent(self.host + self.first)
		urls = self.infoProvider.extractIndividualUrls(first, self.host, self.first)
		
		self.writer = EPubFanficWriter("books", self.infoProvider.getStoryName(), self.infoProvider.getAuthorName())
		
		for u,n in urls:
			text = self.infoProvider.getText(self._getContent(self.host+"/"+u))
			self.writer.writeChapter(n, text)
		
		self.writer.finalise()
		

if __name__ == '__main__':
	f = Downloader(sys.argv[1], 'sigizmund', '***************')
	if f._loginRequired():
		f._login()
	f.download()
	
	
	