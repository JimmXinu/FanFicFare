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

from adapter import *
import twipassword

class Twilighted(FanfictionSiteAdapter):
  def __init__(self, url):
    self.url = url
    parsedUrl = up.urlparse(url)
    self.host = parsedUrl.netloc
    self.path = parsedUrl.path
    self.opener = u2.build_opener(u2.HTTPCookieProcessor())
    self.password=twipassword.password
    self.login='sigizmund'
    logging.debug("Created Twilighted: url=%s" % (self.url))


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

  def extractIndividualUrls(self):
    data = self.opener.open(self.url).read()
    
    if self.reqLoginData(data):
      self.performLogin()
      data = self.opener.open(self.url).read()
      if self.reqLoginData(data):
        return None
    
    soup = bs.BeautifulStoneSoup(data)

    title = soup.find('title').string
    self.storyName = title.split(' by ')[0].strip()
    self.authorName = title.split(' by ')[1].strip()

    select = soup.find('select', { 'name' : 'chapter' } )
	 
    result = []
    if select is None:
	   # no chapters found, try url by itself.
	   result.append((self.url,self.storyName))
    else:
	   allOptions = select.findAll('option')
	   for o in allOptions:
	     url = self.url + "&chapter=%s" % o['value']
	     title = o.string
	     result.append((url,title))

    return result

  def getStoryName(self):
    return self.storyName

  def getAuthorName(self):
    return self.authorName

  def getText(self, url):
    if url.find('http://') == -1:
      url = 'http://' + self.host + '/' + url

    logging.debug('Getting data from: %s' % url)

    data = self.opener.open(url).read()
    
    soup = bs.BeautifulStoneSoup(data, convertEntities=bs.BeautifulStoneSoup.HTML_ENTITIES)

    div = soup.find('div', {'id' : 'story'})

    if None == div:
      return '<html/>'

    return div.__str__('utf8')

  def _getLoginScript(self):
    return '/user.php?action=login'

  def reqLoginData(self, data):
    if data.find('Registered Users Only. Please click OK to login or register.') != -1 or data.find('There is no such account on our website') != -1:
      return True
    else:
      return False


class Twilighted_UnitTests(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.DEBUG)
    pass
  
  def testLoginWorks(self):
    url = 'http://www.twilighted.net/viewstory.php?sid=10004'
    self.assertTrue(Twilighted(url).performLogin())
  
  def testGetUrlsWorks(self):
    url = 'http://www.twilighted.net/viewstory.php?sid=10004'
    self.assertEquals(32, len(Twilighted(url).extractIndividualUrls()))

if __name__ == '__main__':
  unittest.main()
