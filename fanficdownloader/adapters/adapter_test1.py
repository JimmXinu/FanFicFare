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
logger = logging.getLogger(__name__)

from .. import BeautifulSoup as bs
from .. import exceptions

from base_adapter import BaseSiteAdapter,  makeDate

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
            logger.warn("self.is_adult:%s"%self.is_adult)
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
        self.setDescription(self.url,u'Description '+self.crazystring+u''' Done
<p>
Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
''')
        self.story.setMetadata('datePublished',makeDate("1975-03-15","%Y-%m-%d"))
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

        # greater than 10, no language or series.
        if idnum < 10:
            langs = {
                0:"English",
                1:"Russian",
                2:"French",
                3:"German",
                }
            self.story.setMetadata('language',langs[idnum%len(langs)])
            self.setSeries('The Great Test',idnum)
        if idnum == 0:
            self.setSeries("A Nook Hyphen Test "+self.story.getMetadata('dateCreated'),idnum)
            
        self.story.setMetadata('rating','Tweenie')

        if self.story.getMetadata('storyId') == '673':
            self.story.addToList('author','Author From List')
            self.story.addToList('author','Author From List 2')
        
            self.story.addToList('authorId','98765')
            self.story.addToList('authorId','98765-2')
        
            self.story.addToList('authorUrl','http://author/url')
            self.story.addToList('authorUrl','http://author/url-2')
            self.story.addToList('category','Power Rangers')
            self.story.addToList('category','SG-1')
            self.story.addToList('genre','Porn')
            self.story.addToList('genre','Drama')
        else:
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
        self.story.addToList('genre','Comedy')
        self.story.addToList('genre','Sci-Fi')
        self.story.addToList('genre','Noir')
        
        self.story.addToList('characters','Bob Smith')
        self.story.addToList('characters','George Johnson')
        self.story.addToList('characters','Fred Smythe')
        
        self.story.addToList('listX','xVal1')
        self.story.addToList('listX','xVal2')
        self.story.addToList('listX','xVal3')
        self.story.addToList('listX','xVal4')
        
        self.story.addToList('listY','yVal1')
        self.story.addToList('listY','yVal2')
        self.story.addToList('listY','yVal3')
        self.story.addToList('listY','yVal4')
        
        self.story.addToList('listZ','zVal1')
        self.story.addToList('listZ','zVal2')
        self.story.addToList('listZ','zVal3')
        self.story.addToList('listZ','zVal4')
        
        self.story.setMetadata('metaA','98765')
        self.story.setMetadata('metaB','01245')
        self.story.setMetadata('metaC','The mighty metaC!')

        self.chapterUrls = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
                            ('Chapter 1, Xenos on Cinnabar',self.url+"&chapter=2"),
                            ('Chapter 2, Sinmay on Kintikin',self.url+"&chapter=3"),
                            ('Chapter 3, Over Cinnabar',self.url+"&chapter=4"),
                            ('Chapter 4',self.url+"&chapter=5"),
                            ('Chapter 5',self.url+"&chapter=6"),
                            ('Chapter 6',self.url+"&chapter=7"),
                            ('Chapter 7',self.url+"&chapter=8"),
                            ('Chapter 8',self.url+"&chapter=9"),
                            #('Chapter 9',self.url+"&chapter=0"),
                            #('Chapter 0',self.url+"&chapter=a"),
                            #('Chapter a',self.url+"&chapter=b"),
                            #('Chapter b',self.url+"&chapter=c"),
                            #('Chapter c',self.url+"&chapter=d"),
                            #('Chapter d',self.url+"&chapter=e"),
                            #('Chapter e',self.url+"&chapter=f"),
                            #('Chapter f',self.url+"&chapter=g"),
                            #('Chapter g',self.url+"&chapter=h"),
                            #('Chapter h',self.url+"&chapter=i"),
                            #('Chapter i',self.url+"&chapter=j"),
                            #('Chapter j',self.url+"&chapter=k"),
                            #('Chapter k',self.url+"&chapter=l"),
                            #('Chapter l',self.url+"&chapter=m"),
                            #('Chapter m',self.url+"&chapter=n"),
                            #('Chapter n',self.url+"&chapter=o"),
                            ]
        self.story.setMetadata('numChapters',len(self.chapterUrls))
                            

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        if self.story.getMetadata('storyId').startswith('670') or \
                self.story.getMetadata('storyId').startswith('672'):
            time.sleep(1.0)

        if "chapter=1" in url :
            text=u'''
<div>
<h3>Prologue</h3>
<p>This is a fake adapter for testing purposes.  Different sid's will give different errors:</p>
<p>http://test1.com?sid=664 - Crazy string title</p>
<p>http://test1.com?sid=665 - raises AdultCheckRequired</p>
<p>http://test1.com?sid=666 - raises StoryDoesNotExist</p>
<p>http://test1.com?sid=667 - raises FailedToDownload on chapters 2+</p>
<p>http://test1.com?sid=668 - raises FailedToLogin unless username='Me'</p>
<p>http://test1.com?sid=669 - Succeeds with Updated Date=now</p>
<p>http://test1.com?sid=670 - Succeeds, but sleeps 2sec on each chapter</p>




<p>http://test1.com?sid=671 - Succeeds, but sleeps 2sec metadata only</p>
<p>http://test1.com?sid=672 - Succeeds, quick meta, sleeps 2sec chapters only</p>
<p>http://test1.com?sid=673 - Succeeds, multiple authors, extra categories, genres</p>
<p>http://test1.com?sid=0 - Succeeds, generates some text specifically for testing hyphenation problems with Nook STR/STRwG</p>
<p>Odd sid's will be In-Progress, evens complete.  sid&lt;10 will be assigned one of four languages and included in a series.</p>
</div>
'''
        elif self.story.getMetadata('storyId') == '0':
            text=u'''
<h3>45. Pronglet Returns to Hogwarts: Chapter 7</h3>
<br />
    eyes… but I’m not convinced we should automatically<br />
<br /><br />
<b>Thanks to the latest to recommend me: Alastor</b><br />
<br /><br />
    “Sure, invite her along. Does she have children?”<br />
<br />
'''
        else:
            if self.story.getMetadata('storyId') == '667':
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)

            text=u'''
<div>
<h3>Chapter title from site</h3>
<p>Timestamp:'''+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'''</p>
<p>Lorem '''+self.crazystring+u''' <i>italics</i>, <b>bold</b>, <u>underline</u> consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
br breaks<br><br>
Puella Magi Madoka Magica/魔法少女まどか★マギカ
<!-- a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownLoaderPluginWithReadingList" title="Tilt-a-Whirl by Jim &amp; Sarah, on Flickr"><img src="http://i.imgur.com/bo8eD.png"></a --><br/>
br breaks<br><br>
Don't&#8212e;ver&#8212d;o&#8212;that&#8212a;gain, &#27861; &#xE9;
<hr>
horizontal rules
<hr size=1 noshade>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
'''
        soup = bs.BeautifulStoneSoup(text,selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        return self.utf8FromSoup(url,soup)

def getClass():
    return TestSiteAdapter

