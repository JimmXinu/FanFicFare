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
        self.outputName = ''
        self.outputStorySep = '-pns_'

        self.chapurl = False
        ss=self.url.split('?')
        if ss is not None and len(ss) > 1:
            sss = ss[1].replace('&amp;','&').split('&')
            if sss is not None and len(sss) > 0:
                ssss = sss[0].split('=')
                if ssss is not None and len(ssss) > 1 and ssss[0] == 'sid':
                    self.storyId = ssss[1]
                if len(sss) > 1:
                    ssss = sss[1].split('=')
                    if ssss is not None and len(ssss) > 1 and ssss[0] == 'chapter':
                        self.chapurl = True

        self.url = 'http://' + self.host + self.path + '?sid=' + self.storyId
        logging.debug('self.url=%s' % self.url)
        
        logging.debug("Created PotionsNSnitches: url=%s" % (self.url))


    def _getLoginScript(self):
        return '/user.php?action=login'

    def reqLoginData(self, data):
        if data.find('Registered Users Only. Please click OK to login or register.') != -1 or data.find('There is no such account on our website') != -1:
          return True
        else:
          return False

    def _fillCharacters(self, strlist, idx, maxlen):
        ii = idx
        while ii < maxlen:
            chara = strlist[ii].strip()
            if len(chara) > 0:
                if chara.find(':') != -1:
                    return (ii-1)
                elif chara.find(',') == -1:
                    self.addCharacter (chara)
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
                    self.addSubject (genre)
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
                    self.addSubject (cat)
                self.category = self.category + cat
            ii = ii + 1
        return (ii) 

    def extractIndividualUrls(self):
        url = self.url + '&chapter=1'
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

        logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
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
        #logging.debug('output: %s' % unicode(output))
        if output is not None and len(unicode(output)) > 1:
            s2 = re.split ('<[^>]+>', unicode(output))
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
            #logging.debug('td: %s' % unicode(td))
            ss = unicode(td).replace('\n','').replace('\r','').replace('&nbsp;', ' ')
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
            ss = unicode(tl).replace('\n','').replace('\r','').replace('&nbsp;', ' ')
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
        
        # need to do this, because for some reason the <br /> tag in the story causes problems
        data = data.replace('<br />', ' SOMETHING_BR ')

        soup = None
        try:
            soup = bs.BeautifulStoneSoup(data, convertEntities=bs.BeautifulStoneSoup.HTML_ENTITIES)
        except:
            logging.info("Failed to decode: <%s>" % data)
            raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
        
        div = soup.find('div', {'id' : 'story'})
    
        if None == div:
            raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # put the <br /> tags back in..
        text = div.__str__('utf8').replace(' SOMETHING_BR ','<br />')    
        return text


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
