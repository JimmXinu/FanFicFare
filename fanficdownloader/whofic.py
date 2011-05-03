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

class Whofic(FanfictionSiteAdapter):
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
        self.subjects.append ('Fanfiction')
        self.subjects.append ('Doctor Who')
        self.publisher = self.host
        self.numChapters = 0
        self.numWords = 0
        self.genre = ''
        self.category = ''
        self.storyStatus = 'In-Progress'
        self.storyRating = 'PG'
        self.storyUserRating = '0'
        self.storyCharacters = []
        self.storySeries = ''
        self.outputName = ''
        self.outputStorySep = '-whof_'
        
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
        
        logging.debug("Created Whofic: url=%s" % (self.url))

    def requiresLogin(self, url = None):
        return False

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
        
        soup = None
        try:
            soup = bs.BeautifulStoneSoup(data)
        except:
            raise FailedToDownload("Error downloading Story: %s!  Problem decoding page!" % url)    

        title = soup.find('title').string
        title = title.split('::')[1].strip()
        logging.debug('Title: %s' % title)
        self.storyName = title.split(' by ')[0].strip()
        self.authorName = title.split(' by ')[1].strip()

        for a in soup.findAll('a'):
            if a['href'].startswith('viewuser.php'):
                self.authorId = a['href'].split('=')[1]
                self.authorURL = 'http://'+self.host+'/'+a['href']

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
    	     url = self.url + "&chapter=%s" % o['value']
             # just in case there's tags, like <i> in chapter titles.
    	     title = "%s" % o
             title = re.sub('<[^>]+>','',title)
    	     result.append((url,title))

        ## Whofic.com puts none of the meta data in the chapters or
        ## even the story chapter index page.  Need to scrape the
        ## author page to find it.
        data = self.opener.open(self.authorURL).read()

        soup = bs.BeautifulStoneSoup(data, selfClosingTags=('br','hr'))
        # find this story in the list, parse it's metadata based on
        # lots of assumptions, since there's little tagging.
        for a in soup.findAll('a'):
            if a['href'].find('viewstory.php?sid='+self.storyId) != -1:
                metadata = a.findParent('td')
                metadatachunks = metadata.__str__('utf8').split('<br />')
                # process metadata for this story.
                self.storyDescription = metadatachunks[1].strip()

                # the stuff with ' - ' separators
                moremeta = metadatachunks[2]
                moremeta = re.sub('<[^>]+>','',moremeta) # strip tags.
                
                moremetaparts = moremeta.split(' - ')
                
                self.category = moremetaparts[0]
                for cat in self.category.split(', '):
                    self.addSubject(cat.strip())

                self.storyRating = moremetaparts[1]
                
                for warn in moremetaparts[2].split(', '):
                    self.addSubject(warn.strip())
                    
                self.genre = moremetaparts[3]

                # the stuff with ' - ' separators *and* names
                moremeta = metadatachunks[5]
                moremeta = re.sub('<[^>]+>','',moremeta) # strip tags.
                
                moremetaparts = moremeta.split(' - ')

                for part in moremetaparts:
                    (name,value) = part.split(': ')
                    name=name.strip()
                    value=value.strip()
                    if name == 'Published':
                        self.storyPublished = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value, '%Y.%m.%d')))
                    if name == 'Updated':
                        self.storyUpdated = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value, '%Y.%m.%d')))
                    if name == 'Completed' and value == 'Yes':
                        self.storyStatus = name
                    if name == 'Word Count':
                        self.numWords = value

                break                

        self.numChapters = len(result)
        
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

        # hardly a great identifier, I know, but whofic really doesn't
        # give us anything better to work with.
        span = soup.find('span', {'style' : 'font-size: 100%;'})

        if None == span:
            raise FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return span.__str__('utf8')


class Whofic_UnitTests(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)
    pass
  
  def testGetUrlsWorks(self):
    url = 'http://www.whofic.com/viewstory.php?sid=37139'
    self.assertEquals(6, len(Whofic(url).extractIndividualUrls()))

if __name__ == '__main__':
  unittest.main()
