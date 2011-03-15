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

class Adastrafanfic(FanfictionSiteAdapter):
    def __init__(self, url):
        self.url = url
        parsedUrl = up.urlparse(url)
        self.host = parsedUrl.netloc
        self.path = parsedUrl.path
        self.opener = u2.build_opener(u2.HTTPCookieProcessor())
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
        self.subjects.append ('Ad Astra')
        self.publisher = self.host
        self.numChapters = 0
        self.numWords = 0
        self.genre = ''
        self.category = 'Fanfiction'
        self.storyStatus = 'In-Progress'
        self.storyRating = 'PG'
        self.storyUserRating = '0'
        self.storyCharacters = []
        self.storySeries = ''
        self.outputName = ''
        self.outputStorySep = '-aaff_'
        
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
        
        logging.debug("Created Adastrafanfic: url=%s" % (self.url))

    def requiresLogin(self, url = None):
        return False

    def extractIndividualUrls(self):
        # warning=5 bypasses 'are you old enough' checks.
        url = self.url + '&warning=5&chapter=1'

        data = ''
        try:
            data = self.opener.open(url).read()
        except Exception, e:
            data = ''
            logging.error("Caught an exception reading URL " + url + ".  Exception " + unicode(e) + ".")
        if data is None:
            raise StoryDoesNotExist("Problem reading story URL " + url + "!")
        
        soup = None
        try:
            soup = bs.BeautifulStoneSoup(data)
        except:
            raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % url)    

        title = soup.find('title').string
        logging.debug('Title: %s' % title)
        self.storyName = title.split(' by ')[0].strip()
        self.authorName = title.split(' by ')[1].strip()

        logging.debug('self.storyId=%s, self.storyName=%s' % (self.storyId, self.storyName))
        logging.debug('self.authorId=%s, self.authorName=%s' % (self.authorId, self.authorName))
                
        select = soup.find('select', { 'name' : 'chapter' } )
    	 
        result = []
        if select is None:
    	   # no chapters found, try url by itself.
    	   result.append((url,self.storyName))
        else:
    	   allOptions = select.findAll('option')
    	   for o in allOptions:
             # warning=5 bypasses 'are you old enough' checks.
    	     url = self.url + "&warning=5&chapter=%s" % o['value']
             # ad astra can have tags, like <i> in chapter titles.
    	     title = "%s" % o
             title = re.sub('<[^>]+>','',title)
    	     result.append((url,title))

        # warning=5 bypasses 'are you old enough' checks.
        url = self.url + "&warning=5&index=1"
        data = self.opener.open(url).read()

        soup = bs.BeautifulStoneSoup(data, selfClosingTags=('br','hr'))
        # find authorId.
        titlediv = soup.find('div', {'id' : 'pagetitle'})
        for a in titlediv.findAll('a'):
            if a['href'].startswith('viewuser.php'):
                self.authorId = a['href'].split('=')[1]
                self.authorURL = 'http://'+self.host+'/'+a['href']

        # find other metadata
        contentdiv = soup.find('div', {'class' : 'content'})
        
        # adastra meta data is not well structured.  There's an
        # identifiable span class="label" around the *labels*, but
        # nothing around the content for each label.  And there's 
        # <a href> around lots of the meta data values.

        # characters are given 'ln, fn'.  Need to parse out
        # separately.  Of course, I only realized *after* doing this
        # that output.py isn't actually doing anything with the
        # characters... <sigh>
        for a in contentdiv.findAll('a'):
            if a['href'].startswith('browse.php?type=characters'):
                name=a.text
                if a.text.find(', ') > -1:
                    names=a.text.split(', ')
                    names.reverse()
                    name=' '.join(names)
                self.addCharacter(name)
        
        contentdivstring = contentdiv.__str__('utf8')
        labeledlines = contentdivstring.strip().split('<span class="label">') # eats the <span class="label"> tags.
        metadata = dict()
        for labeledline in labeledlines:
            labeledline = re.sub(r'<[^>]+>','',labeledline)
            (label,sep,value)=labeledline.strip().partition(':') # a bit like split, but splits on first separator.
            metadata[label.strip()]=value.strip()
            #print label+"->"+value

        self.storyDescription = metadata['Summary']
        self.genre = metadata['Genre']
        for genre in self.genre.split(", "):
            self.addSubject(genre)
        self.category = metadata['Categories']
        for category in self.category.split(", "):
            self.addSubject(category)
        if metadata['Completed'] == "No":
            self.storyStatus = 'In-Progress'
        else:
            self.storyStatus = 'Completed'
            
        self.storyRating = metadata['Rated']
        self.storySeries = metadata['Series']
        self.numChapters = metadata['Chapters']
        self.numWords = metadata['Word count']
        self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(metadata['Published'], "%m/%d/%Y")))
        self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(metadata['Updated'], "%m/%d/%Y")))
        
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
            # I really wish I knew why adastra needs the selfClosingTags to make <br /> work, but ficwad doesn't.
            soup = bs.BeautifulStoneSoup(data, convertEntities=bs.BeautifulStoneSoup.HTML_ENTITIES, selfClosingTags=('br','hr'))
        except:
            logging.info("Failed to decode: <%s>" % data)
            raise FailedToDownload("Error downloading Chapter: %s!  Problem decoding page!" % url)
        
        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return div.__str__('utf8')


class Adastrafanfic_UnitTests(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)
    pass
  
  def testGetUrlsWorks(self):
    url = 'http://www.adastrafanfic.com/viewstory.php?sid=426'
    self.assertEquals(32, len(Adastrafanfic(url).extractIndividualUrls()))

if __name__ == '__main__':
  unittest.main()
