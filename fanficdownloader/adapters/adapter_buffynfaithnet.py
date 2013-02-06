# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import cookielib as cl

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate


# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return BuffyNFaithNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class BuffyNFaithNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        
        self.setHeader()
        
        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
            # normalized story URL. gets rid of chapter if there, left with ch 1 URL on this site
            nurl = "http://"+self.getSiteDomain()+"/fanfictions/index.php?act=vie&id="+self.story.getMetadata('storyId')
            self._setURL(nurl)
            #argh, this mangles the ampersands I need on metadata['storyUrl']
            #will set it this way
            self.story.setMetadata('storyUrl',nurl,condremoveentities=False)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','bnfnet')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'buffynfaith.net'

    @classmethod
    def stripURLParameters(cls,url):
        "Only needs to be overriden if URL contains more than one parameter"
        ## This adapter needs at least two parameters left on the URL, act and id
        return re.sub(r"(\?act=(vie|ovr)&id=\d+)&.*$",r"\1",url)
    
    def setHeader(self):
        "buffynfaith.net wants a Referer for images.  Used both above and below(after cookieproc added)"
        self.opener.addheaders = [('Referer', 'http://'+self.getSiteDomain()+'/')]
        
    def getSiteExampleURLs(self):
        return "http://buffynfaith.net/fanfictions/index.php?act=vie&id=963 http://buffynfaith.net/fanfictions/index.php?act=vie&id=949 http://buffynfaith.net/fanfictions/index.php?act=vie&id=949&ch=2"

    def getSiteURLPattern(self):
        #http://buffynfaith.net/fanfictions/index.php?act=vie&id=963
        #http://buffynfaith.net/fanfictions/index.php?act=vie&id=949
        #http://buffynfaith.net/fanfictions/index.php?act=vie&id=949&ch=2
        p = re.escape("http://"+self.getSiteDomain()+"/fanfictions/index.php?act=")+\
            r"(vie|ovr)&id=(?P<id>\d+)(&ch=(?P<ch>\d+))?$"
        return p

    def extractChapterUrlsAndMetadata(self):

        dateformat = "%d %B %Y"
        url = self.url
        logger.debug("URL: "+url)
        
        #set a cookie to get past adult check
        if self.is_adult or self.getConfig("is_adult"):
            cookieproc = urllib2.HTTPCookieProcessor()
            cookie = cl.Cookie(version=0, name='my_age', value='yes',
                               port=None, port_specified=False,
                               domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                               path='/', path_specified=True,
                               secure=False,
                               expires=time.time()+10000,
                               discard=False,
                               comment=None,
                               comment_url=None,
                               rest={'HttpOnly': None},
                               rfc2109=False)
            cookieproc.cookiejar.set_cookie(cookie)
            self.opener = urllib2.build_opener(cookieproc)        
            self.setHeader()

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        #print data

        if "ADULT CONTENT WARNING" in data: 
            raise exceptions.AdultCheckRequired(self.url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        # Now go hunting for all the meta data and the chapter list.
        
        #stuff in <head>: description
        svalue = soup.head.find('meta',attrs={'name':'description'})['content']
        #self.story.setMetadata('description',svalue)
        self.setDescription(url,svalue)
        
        #useful stuff in rest of doc, all contained in this:
        doc = soup.body.find('div', id='my_wrapper')
        
        #first the site category (more of a genre to me, meh) and title, in this element:
        mt = doc.find('div',attrs={'class':'maintitle'})
        self.story.addToList('genre',mt.findAll('a')[1].string)
        self.story.setMetadata('title',mt.findAll('a')[1].nextSibling[len('&nbsp;&raquo;&nbsp;'):])
        del mt

        #the actual category, for me, is 'Buffy: The Vampire Slayer'
        #self.story.addToList('category','Buffy: The Vampire Slayer')
        #No need to do it here, it is better to set it in in plugin-defaults.ini and defaults.ini
        
        #then a block that sits in a table cell like so:
        #(contains a lot of metadata)
        mblock = doc.find('td', align='left', width = '70%').contents
        while len(mblock) > 0:
            i = mblock.pop(0)
            if 'Author:' in i.string:
                #drop empty space
                mblock.pop(0)
                #get author link
                a = mblock.pop(0)
                authre = re.escape('./index.php?act=bio&id=')+'(?P<authid>\d+)'
                m = re.match(authre,a['href'])
                self.story.setMetadata('author',a.string)
                self.story.setMetadata('authorId',m.group('authid'))
                authurl = u'http://%s/fanfictions/index.php?act=bio&id=%s' % ( self.getSiteDomain(),
                                            self.story.getMetadata('authorId'))
                self.story.setMetadata('authorUrl',authurl,condremoveentities=False)
                #drop empty space
                mblock.pop(0)
            if 'Rating:' in i.string:
                self.story.setMetadata('rating',mblock.pop(0).strip())
            if 'Published:' in i.string:
                date = mblock.pop(0).strip()
                #get rid of 'st', 'nd', 'rd', 'th' after day number
                date = date[0:2]+date[4:]
                self.story.setMetadata('datePublished',makeDate(date, dateformat))
            if 'Last Updated:' in i.string:
                date = mblock.pop(0).strip()
                #get rid of 'st', 'nd', 'rd', 'th' after day number
                date = date[0:2]+date[4:]
                self.story.setMetadata('dateUpdated',makeDate(date, dateformat))
            if 'Genre:' in i.string:
                genres = mblock.pop(0).strip()
                genres = genres.split('/')
                for genre in genres: self.story.addToList('genre',genre)
            #end ifs
        #end while

        # Find the chapter selector 
        select = soup.find('select', { 'name' : 'ch' } )
         
        if select is None:
           # no selector found, so it's a one-chapter story.
           #self.chapterUrls.append((self.story.getMetadata('title'),url))
           self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = u'http://%s/fanfictions/index.php?act=vie&id=%s&ch=%s' % ( self.getSiteDomain(),
                                            self.story.getMetadata('storyId'),
                                            o['value'])
                title = u"%s" % o
                title = stripHTML(title)
                ts = title.split(' ',1)
                title = ts[0]+'. '+ts[1]
                self.chapterUrls.append((title,url))
        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        ## Go scrape the rest of the metadata from the author's page.
        data = self._fetchUrl(self.story.getMetadata('authorUrl'))
        soup = bs.BeautifulSoup(data)
        #find the story link and its parent div
        storya = soup.find('a',{'href':self.story.getMetadata('storyUrl')})
        storydiv = storya.parent
        #warnings come under a <spawn> tag. Never seen that before...
        #appears to just be a line of freeform text, not necessarily a list
        #optional
        spawn = storydiv.find('spawn',{'id':'warnings'})
        if spawn is not None:
            warns = spawn.nextSibling.strip()
            self.story.addToList('warnings',warns)
        #some meta in spans - this should get all, even the ones jammed in a table
        spans = storydiv.findAll('span')
        for s in spans:
            if s.string == 'Ship:':
                list = s.nextSibling.strip().split()
                self.story.extendList('ships',list)
            if s.string == 'Characters:':
                list = s.nextSibling.strip().split(',')
                self.story.extendList('characters',list)
            if s.string == 'Status:':
                st = s.nextSibling.strip()
                self.story.setMetadata('status',st)
            if s.string == 'Words:':
                st = s.nextSibling.strip()
                self.story.setMetadata('numWords',st)

        #reviews - is this worth having?
        #ffnet adapter gathers it, don't know if anything else does
        #or if it's ever going to be used!
        a = storydiv.find('a',{'id':'bold-blue'})
        if a:
            revs = a.nextSibling.strip()[1:-1]
            self.story.setMetadata('reviews',st)
        else:
            revs = '0'
            self.story.setMetadata('reviews',st)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'fanfiction'})
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        
        #remove all the unnecessary bookmark tags
        [s.extract() for s in div('div',{'class':"tiny_box2"})]
        
        #is there a review link?
        r = div.find('a',href=re.compile(re.escape("./index.php?act=irv")+".*$"))
        if r is not None:
        #remove the review link and its parent div
            r.parent.extract()
        
        #There might also be a link to the sequel on the last chapter
        #I'm inclined to keep it in, but the URL needs to be changed from relative to absolute
        #Shame there isn't proper series metadata available
        #(I couldn't find it anyway)
        s = div.find('a',href=re.compile(re.escape("./index.php?act=ovr")+".*$"))
        if s is not None:
            s['href'] = 'http://'+self.getSiteDomain()+'/fanfictions'+s['href'][1:]

        return self.utf8FromSoup(url,div)
