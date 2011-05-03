# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import os.path
import urllib as u
import logging
import pprint as pp
import unittest
import urllib2 as u2
import urlparse as up
import BeautifulSoup as bs
import htmlentitydefs as hdefs
import time
import datetime

from adapter import *
import twipassword

class Twiwrite(FanfictionSiteAdapter):
    def __init__(self, url):
        self.url = url
        parsedUrl = up.urlparse(url)
        self.host = parsedUrl.netloc
        self.path = parsedUrl.path
        self.opener = u2.build_opener(u2.HTTPCookieProcessor())
        self.password=twipassword.twiwritepassword
        self.login='BobsClue'
        self.storyDescription = 'Fanfiction Story'
        self.authorId = '0'
        self.authorURL = ''
        self.storyId = '0'
        self.storyPublished = datetime.date(1970, 01, 31)
        self.storyCreated = datetime.datetime.now()
        self.storyUpdated = datetime.date(1970, 01, 31)
        self.languageId = 'en-UK'
        self.language = 'English'
        self.subjects = []
        self.subjects.append ('fanfiction')
        self.subjects.append ('Twiwrite')
        self.publisher = self.host
        self.numChapters = 0
        self.numWords = 0
        self.genre = ''
        self.category = 'Fanfiction'
        self.storyStatus = 'Unknown'
        self.storyRating = 'Unknown'
        self.storyUserRating = '0'
        self.storyCharacters = []
        self.storySeries = ''
        self.outputName = ''
        self.outputStorySep = '-twrt_'
        
        self.chapurl = False
        ss=self.url.split('?')
        logging.debug('ss=%s' % ss)
        if ss is not None and len(ss) > 1:
            sss = ss[1].replace('&amp;','&').split('&')
            logging.debug('sss=%s' % sss)
            if sss is not None and len(sss) > 0:
                ssss = sss[0].split('=')
                logging.debug('ssss=%s' % ssss)
                if ssss is not None and len(ssss) > 1 and ssss[0] == 'sid':
                    self.storyId = ssss[1]
                if len(sss) > 1:
                    ssss = sss[1].split('=')
                    logging.debug('ssss=%s' % ssss)
                    if ssss is not None and len(ssss) > 1 and ssss[0] == 'chapter':
                        self.chapurl = True

        self.url = 'http://' + self.host + self.path + '?sid=' + self.storyId
        logging.debug('self.url=%s' % self.url)
        
        logging.debug("Created Twiwrite: url=%s" % (self.url))

    def _getLoginScript(self):
        return '/user.php?action=login'

    def reqLoginData(self, data):
        if data.find('Registered Users Only') != -1 or data.find('There is no such account on our website') != -1:
          return True
        else:
          return False

    def requiresLogin(self, url = None):
        return False

    def performLogin(self, url = None):
        data = {}
    
        data['penname'] = self.login
        data['password'] = self.password
        data['cookiecheck'] = '1'
        data['submit'] = 'Submit'
    
        urlvals = u.urlencode(data)
        loginUrl = 'http://' + self.host + self._getLoginScript()
        logging.debug("Will now login to URL %s" % loginUrl)
    
        req = self.opener.open(loginUrl, urlvals)
    
        d = req.read().decode('utf-8')
    
        if self.reqLoginData(d) :
          return False
        else:
          return True

    def extractIndividualUrls(self):
        url = self.url + '&chapter=1&ageconsent=ok&warning=1'

        data = ''
        try:
            data = self.opener.open(url).read()
        except Exception, e:
            data = ''
            logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
        if data is None:
            raise StoryDoesNotExist("Problem reading story URL " + url + "!")
        
        if self.reqLoginData(data):
            self.performLogin()

            data = ''
            try:
                data = self.opener.open(url).read()
            except Exception, e:
                data = ''
                logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
            if data is None:
                raise StoryDoesNotExist("Problem reading story URL " + url + "!")
        
            if self.reqLoginData(data):
                raise FailedToDownload("Error downloading Story: %s!  Login Failed!" % url)    
        
        soup = None
        try:
            soup = bs.BeautifulStoneSoup(data)
        except:
            raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % url)

        #<div id="pagetitle"><a href="viewstory.php?sid=280">Twilight for Dummies</a> by <a href="viewuser.php?uid=61">The Chick Norris</a> </div>

        div = soup.find('div',{'id':'pagetitle'})
        titlea = div.find('a', href=re.compile(r"viewstory.php"))
        self.storyName = titlea.string
        
        authora = div.find('a', href=re.compile(r"viewuser.php"))
        self.authorName = authora.string
        self.authorId= authora['href'].split('=')[1]
        self.authorURL = 'http://'+self.host+'/'+authora['href']

        logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
        logging.debug('self.authorId=%s, self.authorName=%s' % (self.authorId, self.authorName))

        select = soup.find('select', { 'name' : 'chapter' } )
    	 
        result = []
        if select is None:
    	   # no chapters found, try url by itself.
    	   result.append((self.url,self.storyName))
        else:
    	   allOptions = select.findAll('option')
    	   for o in allOptions:
    	     url = self.url + "&chapter=%s&ageconsent=ok&warning=1" % o['value']
    	     title = o.string
    	     result.append((url,title))
    
        url = self.url + "&index=1&ageconsent=ok&warning=1"
        data = self.opener.open(url).read()
        lines = data.split('\n')
        soup = bs.BeautifulStoneSoup(data)
        
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Rated' in label:
                self.storyRating = value.strip()

            if 'Chapters' in label:
                self.numChapters = value.strip()

            if 'Word count' in label:
                self.numWords = value.strip()

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                catstext = [cat.string for cat in cats]
                self.category = ', '.join(catstext)
                for cat in catstext:
                    self.addSubject(cat.string)

            if 'Genre' in label:
                genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                genrestext = [genre.string for genre in genres]
                self.genre = ', '.join(genrestext)
                for genre in genrestext:
                    self.addSubject(genre.string)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.storyStatus = 'Completed'
                else:
                    self.storyStatus = 'In-Progress'

            if 'Published' in label:
                self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value.strip(), "%B %d, %Y")))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                value = value[0:-1]
                self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value.strip(), "%B %d, %Y")))

        # the only things in <p> tags in <div class='content'> are the parts of the summary.
        divcontent = soup.find('div',{'class':'content'})
        
        # metadesc = soup.find('meta',{'name':'description'})
        # contentsoup = bs.BeautifulStoneSoup(metadesc['content'])
        ps = divcontent.findAll('p')
        pstext=[]
        for p in ps:
            if p.string:
                s = p.string.replace('&nbsp;',' ').strip()
                if s:
                    pstext.append(p.string)
                
        self.storyDescription = '  '.join(pstext)
        print "self.storyDescription: %s"%self.storyDescription
        
        return result

    def getText(self, url):
        if url.find('http://') == -1:
          url = 'http://' + self.host + '/' + url
    
        logging.debug('Getting data from: %s' % url)
    
        data = ''
        try:
            data = self.opener.open(url).read()
        except Exception, e:
            data = ''
            logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
        if data is None:
            raise FailedToDownload("Error downloading Chapter: %s!  Problem getting page!" % url)
                
        soup = None
        try:
            soup = bs.BeautifulStoneSoup(data, convertEntities=bs.BeautifulStoneSoup.HTML_ENTITIES)
        except:
            logging.info("Failed to decode: <%s>" % data)
            raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
        
        div = soup.find('div', {'id' : 'story'})
    
        if None == div:
            raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return div.__str__('utf8')


class Twiwrite_UnitTests(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)
    pass
  
  def testLoginWorks(self):
    url = 'http://www.twiwrite.net/viewstory.php?sid=117'
    self.assertTrue(Twiwrite(url).performLogin())
  
  def testGetUrlsWorks(self):
    url = 'http://www.twiwrite.net/viewstory.php?sid=117'
    self.assertEquals(36, len(Twiwrite(url).extractIndividualUrls()))

if __name__ == '__main__':
  unittest.main()
