# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

import datetime
import time
import logging

from .. import BeautifulSoup as bs
from .. import exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

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
        return BaseSiteAdapter.getSiteURLPattern(self)+r'/?\?sid=\d+$'

    def extractChapterUrlsAndMetadata(self):

        if self.story.getMetadata('storyId') == '665' and not (self.is_adult or self.getConfig("is_adult")):
            logging.warn("self.is_adult:%s"%self.is_adult)
            raise exceptions.AdultCheckRequired(self.url)

        if self.story.getMetadata('storyId') == '666':
            raise exceptions.StoryDoesNotExist(self.url)

        if self.story.getMetadata('storyId').startswith('670'):
            time.sleep(1.0)
            
        if self.story.getMetadata('storyId').startswith('671'):
            time.sleep(1.0)
            
        if self.getConfig("username"):
            self.username = self.getConfig("username")
        
        if self.story.getMetadata('storyId') == '668' and self.username != "Me" :
            raise exceptions.FailedToLogin(self.url,self.username)

        if self.story.getMetadata('storyId') == '664':
            self.story.setMetadata(u'title',"Test Story Title "+self.story.getMetadata('storyId')+self.crazystring)
            self.story.setMetadata('author','Test Author aa bare amp(&) quote(&#39;) amp(&amp;)')
        else:
            self.story.setMetadata(u'title',"Test Story Title "+self.story.getMetadata('storyId'))
            self.story.setMetadata('author','Test Author aa')
        self.story.setMetadata('storyUrl',self.url)
        self.story.setMetadata('description',u'Description '+self.crazystring+u''' Done

Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
''')
        self.story.setMetadata('datePublished',makeDate("1975-03-15","%Y-%m-%d"))
        self.story.setMetadata('dateCreated',datetime.datetime.now())
        if self.story.getMetadata('storyId') == '669':
            self.story.setMetadata('dateUpdated',datetime.datetime.now())
        else:
            self.story.setMetadata('dateUpdated',makeDate("1975-04-15","%Y-%m-%d"))
        self.story.setMetadata('numWords','123456')

        idnum = int(self.story.getMetadata('storyId'))
        if idnum % 2 == 1:
            self.story.setMetadata('status','In-Progress')
        else:
            self.story.setMetadata('status','Completed')

        langs = {
            0:"English",
            1:"Russian",
            2:"French",
            3:"German",
            }
        if idnum < 10:
            self.story.setMetadata('language',langs[idnum%len(langs)])
        # greater than 10, no language.
            
        self.setSeries('The Great Test',idnum)
        
        self.story.setMetadata('rating','Tweenie')
        
        self.story.setMetadata('authorId','98765')
        self.story.setMetadata('authorUrl','http://author/url')

        self.story.addToList('warnings','Swearing')
        self.story.addToList('warnings','Violence')

        self.story.addToList('category','Harry Potter')
        self.story.addToList('category','Furbie')
        self.story.addToList('category','Crossover')
        self.story.addToList('category',u'Puella Magi Madoka Magica/魔法少女まどか★マギカ')
        self.story.addToList('category',u'Magical Girl Lyrical Nanoha')
        self.story.addToList('genre','Fantasy')
        self.story.addToList('genre','SF')
        self.story.addToList('genre','Noir')
        
        self.chapterUrls = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
                            ('Chapter 1, Xenos on Cinnabar',self.url+"&chapter=2"),
                            ('Chapter 2, Sinmay on Kintikin',self.url+"&chapter=3"),
                            ('Chapter 3, Over Cinnabar',self.url+"&chapter=4"),
                            ('Chapter 4',self.url+"&chapter=5"),
                            ('Chapter 5',self.url+"&chapter=6"),
                            ('Chapter 6',self.url+"&chapter=6"),
                            ('Chapter 7',self.url+"&chapter=6"),
                            # ('Chapter 8',self.url+"&chapter=6"),
                            # ('Chapter 9',self.url+"&chapter=6"),
                            # ('Chapter 0',self.url+"&chapter=6"),
                            # ('Chapter a',self.url+"&chapter=6"),
                            # ('Chapter b',self.url+"&chapter=6"),
                            # ('Chapter c',self.url+"&chapter=6"),
                            # ('Chapter d',self.url+"&chapter=6"),
                            # ('Chapter e',self.url+"&chapter=6"),
                            # ('Chapter f',self.url+"&chapter=6"),
                            # ('Chapter g',self.url+"&chapter=6"),
                            # ('Chapter h',self.url+"&chapter=6"),
                            # ('Chapter i',self.url+"&chapter=6"),
                            # ('Chapter j',self.url+"&chapter=6"),
                            # ('Chapter k',self.url+"&chapter=6"),
                            # ('Chapter l',self.url+"&chapter=6"),
                            # ('Chapter m',self.url+"&chapter=6"),
                            # ('Chapter n',self.url+"&chapter=6"),
                            ]
        self.story.setMetadata('numChapters',len(self.chapterUrls))
                            

    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        if self.story.getMetadata('storyId') == '667':
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)

        if self.story.getMetadata('storyId').startswith('670') or \
                self.story.getMetadata('storyId').startswith('672'):
            time.sleep(1.0)

        if "chapter=1" in url :
            text=u'''
<div>
<h3>Prologue</h3>
<p>This is a fake adapter for testing purposes.  Different storyId's will give different errors:</p>
<p>http://test1.com?sid=664 - Crazy string title</p>
<p>http://test1.com?sid=665 - raises AdultCheckRequired</p>
<p>http://test1.com?sid=666 - raises StoryDoesNotExist</p>
<p>http://test1.com?sid=667 - raises FailedToDownload on chapter 1</p>
<p>http://test1.com?sid=668 - raises FailedToLogin unless username='Me'</p>
<p>http://test1.com?sid=669 - Succeeds with Updated Date=now</p>
<p>http://test1.com?sid=670 - Succeeds, but sleeps 2sec on each chapter</p>
<p>http://test1.com?sid=671 - Succeeds, but sleeps 2sec metadata only</p>
<p>http://test1.com?sid=672 - Succeeds, quick meta, sleeps 2sec chapters only</p>
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

