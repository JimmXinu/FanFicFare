# -*- coding: utf-8 -*-

import datetime
import logging

import fanficdownloader.BeautifulSoup as bs
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup

class TestSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tst1')
        self.crazystring = u" crazy tests:[bare amp(&) quote(&#39;) amp(&amp;) gt(&gt;) lt(&lt;) ATnT(AT&T) pound(&pound;)]"
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        self.username=''
        self.is_adult=False

    @staticmethod
    def getSiteDomain():
        return 'test1.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"?sid=1234"

    def getSiteURLPattern(self):
        return BaseSiteAdapter.getSiteURLPattern(self)+'\?sid=\d+$'

    def extractChapterUrlsAndMetadata(self):

        if self.story.getMetadata('storyId') == '665' and not (self.is_adult or self.getConfig("is_adult")):
            logging.warn("self.is_adult:%s"%self.is_adult)
            raise exceptions.AdultCheckRequired(self.url)

        if self.story.getMetadata('storyId') == '666':
            raise exceptions.StoryDoesNotExist(self.url)

        if self.getConfig("username"):
            self.username = self.getConfig("username")
        
        if self.story.getMetadata('storyId') == '668' and self.username != "Me" :
            raise exceptions.FailedToLogin(self.url,self.username)
        
        self.story.setMetadata(u'title',"Test Story Title "+self.crazystring)
        self.story.setMetadata('storyUrl',self.url)
        self.story.setMetadata('description',u'Description '+self.crazystring+u''' Done

Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
''')
        self.story.setMetadata('datePublished',datetime.date(1972, 01, 31))
        self.story.setMetadata('dateCreated',datetime.datetime.now())
        if self.story.getMetadata('storyId') == '669':
            self.story.setMetadata('dateUpdated',datetime.datetime.now())
        else:
            self.story.setMetadata('dateUpdated',datetime.date(1975, 01, 31))
        self.story.setMetadata('numChapters','5')
        self.story.setMetadata('numWords','123456')
        self.story.setMetadata('status','In-Completed')
        self.story.setMetadata('rating','Tweenie')
        
        self.story.setMetadata('author','Test Author aa')
        self.story.setMetadata('authorId','98765')
        self.story.setMetadata('authorUrl','http://author/url')

        self.story.addToList('warnings','Swearing')
        self.story.addToList('warnings','Violence')

        self.story.addToList('category','Harry Potter')
        self.story.addToList('category','Furbie')
        self.story.addToList('category','Crossover')
        
        self.story.addToList('genre','Fantasy')
        self.story.addToList('genre','SF')
        self.story.addToList('genre','Noir')
        
        self.chapterUrls = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
                            ('Chapter 1, Xenos on Cinnabar',self.url+"&chapter=2"),
                            ('Chapter 2, Sinmay on Kintikin',self.url+"&chapter=3"),
                            ('Chapter 3, Over Cinnabar',self.url+"&chapter=4"),
                            ('Epilogue',self.url+"&chapter=5")]
                            

    def getChapterText(self, url):
        if self.story.getMetadata('storyId') == '667':
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)

        if "chapter=1" in url :
            text=u'''
<div>
<h3>Prologue</h3>
<p>This is a fake adapter for testing purposes.  Different storyId's will give different errors:</p>
<p>http://test1.com?sid=665 - raises AdultCheckRequired</p>
<p>http://test1.com?sid=666 - raises StoryDoesNotExist</p>
<p>http://test1.com?sid=667 - raises FailedToDownload on chapter 1</p>
<p>http://test1.com?sid=668 - raises FailedToLogin unless username='Me'</p>
<p>http://test1.com?sid=669 - Succeeds with Updated Date=now</p>
<p>And other storyId will succeed with the same output.</p>
</div>
'''
        else:
            text=u'''
<div>
<h3>Chapter</h3>
<p><center>Centered text</center></p>
<p>Lorem '''+self.crazystring+''' <i>italics</i>, <b>bold</b>, <u>underline</u> consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
br breaks<br><br>
br breaks<br><br>
<hr>
horizontal rules
<hr>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
'''
        soup = bs.BeautifulStoneSoup(text,selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        return utf8FromSoup(soup)

def getClass():
    return TestSiteAdapter

