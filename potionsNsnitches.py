# -*- coding: utf-8 -*-

# Copied from the twilighted.py because site is almost the same..
# of course, now that we're trying to scrape more detail about the
# story, there were differences in how headers are displayed

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

class PotionsNSnitches(FanfictionSiteAdapter):
    def __init__(self, url):
        self.url = url
        parsedUrl = up.urlparse(url)
        self.host = parsedUrl.netloc
        self.path = parsedUrl.path
        self.opener = u2.build_opener(u2.HTTPCookieProcessor())
        self.password = ''
        self.login='sigizmund'
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
        self.subjects.append ('Harry Potter')
        self.publisher = self.host
        self.numChapters = 0
        self.numWords = 0
        self.genre = 'FanFiction'
        self.category = 'Category'
        self.storyStatus = 'In-Progress'
        self.storyRating = 'PG'
        self.storyUserRating = '0'
        self.storyCharacters = []
        self.storySeries = ''
        
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

        self.url = 'http://' + self.host + '/' + self.path + '?sid=' + self.storyId
        logging.debug('self.url=%s' % self.url)
        
        self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
        logging.debug('self.uuid=%s' % self.uuid)
    
        logging.debug("Created PotionsNSnitches: url=%s" % (self.url))


    def requiresLogin(self, url = None):
        # potionsandsnitches.net doesn't require login.
        if self.host == 'potionsandsnitches.net':
          return False
        else:
          return True

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


    def setLogin(self, login):
        self.login = login

    def setPassword(self, password):
        self.password = password

    def _addSubject(self, subject):
        subj = subject.upper()
        for s in self.subjects:
            if s.upper() == subj:
                return False
        self.subjects.append(subject)
        return True

    def _addCharacter(self, character):
        chara = character.upper()
        for c in self.storyCharacters:
            if c.upper() == chara:
                return False
        self.storyCharacters.append(character)
        return True 
    
    def _fillCharacters(self, strlist, idx, maxlen):
        ii = idx
        while ii < maxlen:
            chara = strlist[ii].strip()
            if len(chara) > 0:
                if chara.find(':') != -1:
                    return (ii-1)
                elif chara.find(',') == -1:
                    self._addCharacter (chara)
            ii = ii + 1
        return (ii) 

    def _buildGenre(self, strlist, idx, maxlen):
        self.genre = ''
        ii = idx
        while ii < maxlen:
            genre = strlist[ii].strip()
            if len(genre) > 0:
                if genre.find(':') != -1:
                    return (ii-1)
                elif genre.find(',') != -1:
                    genre = ', '
                else:
                    self._addSubject (genre)
                self.genre = self.genre + genre
            ii = ii + 1
        return (ii) 

    def _buildCategory(self, strlist, idx, maxlen):
        self.category = ''
        ii = idx
        while ii < maxlen:
            cat = strlist[ii].strip()
            if len(cat) > 0:
                if cat.find(':') != -1:
                    return (ii-1)
                elif cat.find(',') != -1:
                    cat = ', '
                else:
                    self._addSubject (cat)
                self.category = self.category + cat
            ii = ii + 1
        return (ii) 

    def extractIndividualUrls(self):
        url = self.url + '&chapter=1'
        data = self.opener.open(url).read()
        
        if self.reqLoginData(data):
          self.performLogin()
          data = self.opener.open(url).read()
          if self.reqLoginData(data):
            return None
        
        soup = bs.BeautifulStoneSoup(data)

        self.storyName = ''
        self.authorName = ''
        self.storyId = '0'
        title = soup.find('title').string
        if title is not None and len(title) > 0:
            logging.debug('Title: %s' % title)
            ss = title.split(' by ')
            if ss is not None and len(ss) > 1:
                self.storyName = ss[0].strip()
                self.authorName = ss[1].strip()
                self.outputName = self.storyName.replace(" ", "_") + '-pNs_' + self.storyId

        logging.debug('self.storyId=%s, self.storyName=%s, self.outputName=%s' % (self.storyId, self.storyName, self.outputName))
        logging.debug('self.authorId=%s, self.authorName=%s' % (self.authorId, self.authorName))
                
        select = soup.find('select', { 'name' : 'chapter' } )
    	 
        result = []
        if select is None:
    	   # no chapters found, try url by itself.
           chaptitle = soup.find('div', { 'id' : 'chaptertitle' } )
           if chaptitle is not None and chaptitle.string is not None and len(chaptitle.string) > 0:
               result.append((url,chaptitle.string))
           else:
    	       result.append((url,self.storyName))
        else:
    	   allOptions = select.findAll('option')
    	   for o in allOptions:
    	     url = self.url + "&chapter=%s" % o['value']
    	     title = o.string
    	     result.append((url,title))
    
        url = self.url + "&index=1"
        data = self.opener.open(url).read()
        lines = data.split('\n')
        soup = bs.BeautifulStoneSoup(data)
        pgt = soup.find('div', {'id' : 'pagetitle'})
        #logging.debug('pagetitle: %s' % pgt)
        pgtAs = pgt.findAll('a')
        #logging.debug('pgtAs: %s' % pgtAs)
        for a in pgtAs:
            if a['href'].find('viewstory.php') != -1:
                (u1, self.storyId) = a['href'].split('=')
                self.storyName = a.string
                logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
            elif a['href'].find('viewuser.php') != -1:
                self.authorName = a.string
                self.authorURL = 'http://' + self.host + '/' + a['href']
                (u1, self.authorId) = a['href'].split('=')
                logging.debug('self.authorName=%s, self.authorId=%s' % (self.authorName, self.authorId))

        output = soup.find('div', {'id' : 'output'})
        #logging.debug('output: %s' % str(output))
        if output is not None and len(str(output)) > 1:
            s2 = re.split ('<[^>]+>', str(output))
            #logging.debug('s2=%s' % s2)
            ii = 0
            ll = len(s2)
            while ii < ll:
                if s2[ii] == 'Summary:' and ii+1 < ll:
                    self.storyDescription = s2[ii+1].strip()
                    logging.debug('self.storyDescription: %s' % self.storyDescription)
                    break;
                ii = ii+1
            
        cnt = soup.find('div', {'class' : 'content'})
        #logging.debug('content: %s' % cnt)
        cnttd = cnt.findAll('td')
        #logging.debug('cnttd: %s' % cnttd)
        for td in cnttd:
            #logging.debug('td: %s' % str(td))
            ss = str(td).replace('\n','').replace('\r','').replace('&nbsp;', ' ')
            if len(ss) > 1:
                s2 = re.split ('<[^>]+>', ss)
                #logging.debug('s2=%s' % s2)
                ii = 0
                ll = len(s2)
                while ii < ll-1:
                    if s2[ii] is not None and len(s2[ii]) > 0 and s2[ii].find(':') != -1:
                        skey = s2[ii].strip()
                        ii = ii+1
                        if skey == 'Rated:':
                            self.storyRating = s2[ii].strip()
                            logging.debug('self.storyRating=%s' % self.storyRating)
                            ii = ii + 1
                        elif skey == 'Chapters:':
                            self.numChapters = s2[ii].strip()
                            logging.debug('self.numChapters=%s' % self.numChapters)
                            ii = ii + 1
                        elif skey == 'Characters:':
                            ii = self._fillCharacters(s2, ii, ll)
                            logging.debug('self.storyCharacters=%s' % self.storyCharacters)
                            ii = ii + 1
                        elif skey == 'Genres:':
                            ii = self._buildGenre(s2, ii, ll)
                            logging.debug('self.genre=%s' % self.genre)
                            logging.debug('self.subjects=%s' % self.subjects)
                        elif skey == 'Categories:':
                            ii = self._buildCategory(s2, ii, ll)
                            logging.debug('self.category=%s' % self.category)
                            logging.debug('self.subjects=%s' % self.subjects)
                        elif skey == 'Completed:':
                            if s2[ii].strip(' ') == "No":
                                self.storyStatus = 'In-Progress'
                            else:
                                self.storyStatus = 'Completed'
                            ii = ii + 1
                        elif skey == 'Word count:':
                            self.numWords = s2[ii].strip()
                            if self.numWords is None or len(self.numWords) == 0:
                                self.numWords = '0'
                            logging.debug('self.numWords=%s' % self.numWords)
                            ii = ii + 1
                        elif skey == 'Takes Place:':
                            ii = ii + 1
                        elif skey == 'Awards:':
                            ii = ii + 1
                        elif skey == 'Series:':
                            ii = ii + 1
                        elif skey == 'Read:':
                            ii = ii + 1
                        elif skey == 'Warnings:':
                            ii = ii + 1
                    else:
                        ii = ii + 1
                                        
        tls = soup.findAll('div', {'style' : 'text-align: center;'})
        for tl in tls:
            #logging.debug('tl: %s' % tl)
            ss = str(tl).replace('\n','').replace('\r','').replace('&nbsp;', ' ')
            if ss.find('Published:') != -1:
                s2 = re.split ('<[^>]+>', ss)
                #logging.debug('s2: %s' % s2)
                ii = 0
                ll = len(s2)
                while ii < ll-1:
                    if s2[ii] is not None and len(s2[ii]) > 0 and s2[ii].find(':') != -1:
                        skey = s2[ii].strip()
                        #logging.debug('skey: %s' % skey)
                        ii = ii+1
                        if skey == 'Published:':
                            self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s2[ii].strip(' '), "%b %d %Y")))
                            logging.debug('self.storyPublished=%s' % self.storyPublished)
                            ii = ii + 1
                        elif skey == 'Updated:':
                            self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(s2[ii].strip(' '), "%b %d %Y")))
                            logging.debug('self.storyUpdated=%s' % self.storyUpdated)
                            ii = ii + 1
                    else:
                        ii = ii + 1
            
        if (self.storyName is None or len(self.storyName) == 0) and self.storyId == '0': 
            logging.error('self.storyName is empty!!  Exitting!')
            exit(1)
            
        self.outputName = self.storyName.replace(" ", "_") + '-pNs_' + self.storyId
        logging.debug('self.outputName=%s' % self.outputName)
        
        self.uuid = 'urn:uuid:' + self.host + '-u.' + self.authorId + '-s.' + self.storyId
        logging.debug('self.uuid=%s' % self.uuid)

        return result

    def getStoryName(self):
        return self.storyName

    def getOutputName(self):
        return self.outputName
		
    def getAuthorName(self):
        return self.authorName
    
    def getText(self, url):
        if url.find('http://') == -1:
          url = 'http://' + self.host + '/' + url
    
        logging.debug('Getting data from: %s' % url)
    
        data = self.opener.open(url).read()
        
        # need to do this, because for some reason the <br /> tag in the story causes problems
        data = data.replace('<br />', ' SOMETHING_BR ')
        soup = bs.BeautifulStoneSoup(data, convertEntities=bs.BeautifulStoneSoup.HTML_ENTITIES)
    
        div = soup.find('div', {'id' : 'story'})
    
        if None == div:
          return '<html/>'

        # put the <br /> tags back in..
        text = div.__str__('utf8').replace(' SOMETHING_BR ','<br />')    
        return text

    def _getLoginScript(self):
        return '/user.php?action=login'

    def reqLoginData(self, data):
        if data.find('Registered Users Only. Please click OK to login or register.') != -1 or data.find('There is no such account on our website') != -1:
          return True
        else:
          return False

    def getHost(self):
        logging.debug('self.host=%s' % self.host)
        return self.host

    def getStoryURL(self):
        logging.debug('self.url=%s' % self.url)
        return self.url

    def getAuthorURL(self):
        logging.debug('self.authorURL=%s' % self.authorURL)
        return self.authorURL

    def getUUID(self):
        logging.debug('self.uuid=%s' % self.uuid)
        return self.uuid
    
    def getStoryDescription(self):
        logging.debug('self.storyDescription=%s' % self.storyDescription)
        return self.storyDescription
    
    def getStoryPublished(self):
        logging.debug('self.storyPublished=%s' % self.storyPublished)
        return self.storyPublished
    
    def getStoryCreated(self):
        self.storyCreated = datetime.datetime.now()
        logging.debug('self.storyCreated=%s' % self.storyCreated)
        return self.storyCreated
    
    def getStoryUpdated(self):
        logging.debug('self.storyUpdated=%s' % self.storyUpdated)
        return self.storyUpdated
    
    def getLanguage(self):
        logging.debug('self.language=%s' % self.language)
        return self.language
    
    def getLanguageId(self):
        logging.debug('self.languageId=%s' % self.languageId)
        return self.languageId
    
    def getSubjects(self):
        logging.debug('self.subjects=%s' % self.authorName)
        return self.subjects
    
    def getPublisher(self):
        logging.debug('self.publisher=%s' % self.publisher)
        return self.publisher
    
    def getNumChapters(self):
        logging.debug('self.numChapters=%s' % self.numChapters)
        return self.numChapters
    
    def getNumWords(self):
        logging.debug('self.numWords=%s' % self.numWords)
        return self.numWords
    
    def getAuthorId(self):
        logging.debug('self.authorId=%s' % self.authorId)
        return self.authorId
    
    def getStoryId(self):
        logging.debug('self.storyId=%s' % self.storyId)
        return self.storyId
    
    def getCategory(self):
        logging.debug('self.category=%s' % self.category)
        return self.category
    
    def getGenre(self):
        logging.debug('self.genre=%s' % self.genre)
        return self.genre
    
    def getStoryStatus(self):
        logging.debug('self.storyStatus=%s' % self.storyStatus)
        return self.storyStatus
    
    def getStoryRating(self):
        logging.debug('self.storyRating=%s' % self.storyRating)
        return self.storyRating
    
    def getStoryUserRating(self):
        logging.debug('self.storyUserRating=%s' % self.storyUserRating)
        return self.storyUserRating
    
    def getStoryCharacters(self):
        logging.debug('self.storyCharacters=%s' % self.storyCharacters)
        return self.storyCharacters

    def getStorySeries(self):
        logging.debug('self.storySeries=%s' % self.storySeries)
        return self.storySeries

class PotionsNSnitches_UnitTests(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        pass
  
    def testLoginWorks(self):
        pass
  
    def testGetUrlsWorks(self):
        url = 'http://potionsandsnitches.net/fanfiction/viewstory.php?sid=2230'
        self.assertEquals(32, len(Twilighted(url).extractIndividualUrls()))

if __name__ == '__main__':
    unittest.main()
