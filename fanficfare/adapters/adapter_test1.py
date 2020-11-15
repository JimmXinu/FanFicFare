# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2019 FanFicFare team
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

from __future__ import absolute_import
import re
import datetime
import time
import logging
logger = logging.getLogger(__name__)

from .. import exceptions

# py2 vs py3 transition
from ..six import ensure_text

from .base_adapter import BaseSiteAdapter,  makeDate

class TestSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tst1')
        self.crazystring = u"tests:[bare amp(&) qt(&#39;) amp(&amp;) gt(&gt;) lt(&lt;) ATnT(AT&T) L(&pound;) Onna(女)]"
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        self.username=''
        self.is_adult=False
        self._setURL("http://"+self.getSiteDomain()+"?sid="+self.story.getMetadata('storyId'))

    @staticmethod
    def getSiteDomain():
        return 'test1.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"?sid=1234"

    def getSiteURLPattern(self):
        return BaseSiteAdapter.getSiteURLPattern(self)+r'/?\?sid=\d+$'

    def use_pagecache(self):
        return True

    def extractChapterUrlsAndMetadata(self):
        logger.debug('extractChapterUrlsAndMetadata: %s' % self.url)
        idstr = self.story.getMetadata('storyId')
        idnum = int(idstr)
        self.do_sleep()

        if idnum >= 1000:
            logger.warning("storyId:%s - Custom INI data will be used."%idstr)

            sections = ['teststory:%s'%idstr,'teststory:defaults']
            #print("self.get_config_list(sections,'valid_entries'):%s"%self.get_config_list(sections,'valid_entries'))
            for key in self.get_config_list(sections,'valid_entries'):
                if key.endswith("_list"):
                    nkey = key[:-len("_list")]
                    #print("addList:%s"%(nkey))
                    for val in self.get_config_list(sections,key):
                        #print("addList:%s->%s"%(nkey,val))
                        self.story.addToList(nkey,ensure_text(val).replace('{{storyId}}',idstr))
                else:
                    # Special cases:
                    if key in ['datePublished','dateUpdated']:
                        self.story.setMetadata(key,makeDate(self.get_config(sections,key),"%Y-%m-%d"))
                    else:
                        self.story.setMetadata(key,ensure_text(self.get_config(sections,key)).replace('{{storyId}}',idstr))
                    #print("set:%s->%s"%(key,self.story.getMetadata(key)))

            if self.has_config(sections,'chapter_urls'):
                for l in self.get_config(sections,'chapter_urls').splitlines() :
                    if l:
                        self.add_chapter(l[1+l.index(','):],l[:l.index(',')])
            else:
                for (j,chap) in enumerate(self.get_config_list(sections,'chaptertitles'),start=1):
                    self.add_chapter(chap,self.url+"&chapter=%d"%j)

            return

        if idnum >= 700 and idnum <= 710:
            self._setURL('http://test1.com?sid=%s'%(idnum+100))
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
            idstr = self.story.getMetadata('storyId')
            idnum = int(idstr)

        if (idstr == '665' or (idnum>710 and idnum<=720)) and not (self.is_adult or self.getConfig("is_adult")):
            logger.warning("self.is_adult:%s"%self.is_adult)
            raise exceptions.AdultCheckRequired(self.url)

        if idstr == '666':
            raise exceptions.StoryDoesNotExist(self.url)

        if idstr.startswith('670'):
            time.sleep(1.0)

        if idstr.startswith('671'):
            time.sleep(1.0)

        if self.getConfig("username"):
            self.username = self.getConfig("username")

        if idstr == '668' and self.username != "Me" :
            raise exceptions.FailedToLogin(self.url,self.username)

        if idstr == '664':
            self.story.setMetadata(u'title',"Test Story Title "+idstr+self.crazystring+"&nbsp;&nbsp;")
            self.story.setMetadata('author','Test Author aa bare amp(&) quote(&#39;) amp(&amp;)')
        else:
            self.story.setMetadata(u'title',"Test Story Title "+idstr)
            self.story.setMetadata('author','Test Author aa')
        self.setDescription(self.url,u'<div>Description '+self.crazystring+u''' Done
<p>
Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
</div>''')
        self.story.setMetadata('datePublished',makeDate("1975-03-15","%Y-%m-%d"))
        if idstr == '669':
            self.story.setMetadata('dateUpdated',datetime.datetime.now())
        else:
            self.story.setMetadata('dateUpdated',makeDate("1975-04-15","%Y-%m-%d"))

        if idstr != '674':
            self.story.setMetadata('numWords','123456')

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
            self.story.setMetadata('seriesUrl','http://test1.com/seriesid=1')
        elif idnum < 20:
            self.setSeries('魔法少女まどか★マギカ',idnum)
            self.story.setMetadata('seriesUrl','http://test1.com/seriesid=1')
        if idnum == 0:
            self.setSeries("A Nook Hyphen Test "+self.story.getMetadata('dateCreated'),idnum)
            self.story.setMetadata('seriesUrl','http://test1.com/seriesid=0')

        self.story.setMetadata('rating','Tweenie')

        if idstr == '673':
            self.story.addToList('author','Author From List 1')
            self.story.addToList('author','Author From List 2')
            self.story.addToList('author','Author From List 3')
            self.story.addToList('author','Author From List 4')
            self.story.addToList('author','Author From List 5')
            self.story.addToList('author','Author From List 6')
            self.story.addToList('author','Author From List 7')
            self.story.addToList('author','Author From List 8')
            self.story.addToList('author','Author From List 9')
            self.story.addToList('author','Author From List 0')
            self.story.addToList('author','Author From List q')
            self.story.addToList('author','Author From List w')
            self.story.addToList('author','Author From List e')
            self.story.addToList('author','Author From List r')
            self.story.addToList('author','Author From List t')
            self.story.addToList('author','Author From List y')
            self.story.addToList('author','Author From List u')
            self.story.addToList('author','Author From List i')
            self.story.addToList('author','Author From List o')

            self.story.addToList('authorId','98765')
            self.story.addToList('authorId','98765-1')
            self.story.addToList('authorId','98765-2')
            self.story.addToList('authorId','98765-3')
            self.story.addToList('authorId','98765-4')
            self.story.addToList('authorId','98765-5')
            self.story.addToList('authorId','98765-6')
            self.story.addToList('authorId','98765-7')
            self.story.addToList('authorId','98765-8')
            self.story.addToList('authorId','98765-9')
            self.story.addToList('authorId','98765-0')
            self.story.addToList('authorId','98765-q')
            self.story.addToList('authorId','98765-w')
            self.story.addToList('authorId','98765-e')
            self.story.addToList('authorId','98765-r')
            self.story.addToList('authorId','98765-t')
            self.story.addToList('authorId','98765-y')
            self.story.addToList('authorId','98765-u')
            self.story.addToList('authorId','98765-i')
            self.story.addToList('authorId','98765-o')

            self.story.addToList('authorUrl','http://author/url')
            self.story.addToList('authorUrl','http://author/url-1')
            self.story.addToList('authorUrl','http://author/url-2')
            self.story.addToList('authorUrl','http://author/url-3')
            self.story.addToList('authorUrl','http://author/url-4')
            self.story.addToList('authorUrl','http://author/url-5')
            self.story.addToList('authorUrl','http://author/url-6')
            self.story.addToList('authorUrl','http://author/url-7')
            self.story.addToList('authorUrl','http://author/url-8')
            self.story.addToList('authorUrl','http://author/url-9')
            self.story.addToList('authorUrl','http://author/url-0')
            self.story.addToList('authorUrl','http://author/url-q')
            self.story.addToList('authorUrl','http://author/url-w')
            self.story.addToList('authorUrl','http://author/url-e')
            self.story.addToList('authorUrl','http://author/url-r')
            self.story.addToList('authorUrl','http://author/url-t')
            self.story.addToList('authorUrl','http://author/url-y')
            self.story.addToList('authorUrl','http://author/url-u')
            self.story.addToList('authorUrl','http://author/url-i')
            self.story.addToList('authorUrl','http://author/url-o')

            self.story.addToList('category','Power Rangers')
            self.story.addToList('category','SG-1')
            self.story.addToList('genre','Porn')
            self.story.addToList('genre','Drama')
        elif idnum < 1000:
            self.story.setMetadata('authorId','98765')
            self.story.setMetadata('authorUrl','http://author/url')

        self.story.addToList('warnings','Swearing')
        self.story.addToList('warnings','Violence')

        if idstr == '80':
            self.story.addToList('category',u'Rizzoli &amp; Isles')
            self.story.addToList('characters','J. Rizzoli')
        elif idstr == '81':
            self.story.addToList('category',u'Pitch Perfect')
            self.story.addToList('characters','Chloe B.')
        elif idstr == '82':
            self.story.addToList('characters','Henry (Once Upon a Time)')
            self.story.addToList('category',u'Once Upon a Time (TV)')
        elif idstr == '83':
            self.story.addToList('category',u'Rizzoli &amp; Isles')
            self.story.addToList('characters','J. Rizzoli')
            self.story.addToList('category',u'Pitch Perfect')
            self.story.addToList('characters','Chloe B.')
            self.story.addToList('ships','Chloe B. &amp; J. Rizzoli')
        elif idstr == '90':
            self.story.setMetadata('characters','Henry (Once Upon a Time)')
            self.story.setMetadata('category',u'Once Upon a Time (TV)')
        else:
            self.story.addToList('category','Harry Potter')
            self.story.addToList('category','Furbie')
            self.story.addToList('category',u'Puella Magi Madoka Magica/魔法少女まどか★マギカ')
            self.story.addToList('category',u'Magical Girl Lyrical Nanoha')
            self.story.addToList('category',u'Once Upon a Time (TV)')
            self.story.addToList('characters','Bob Smith')
            self.story.addToList('characters','George Johnson')
            self.story.addToList('characters','Fred Smythe')
            self.story.addToList('ships','Harry Potter/Ginny Weasley')
            self.story.addToList('ships','Harry Potter/Ginny Weasley/Albus Dumbledore')
            self.story.addToList('ships','Harry Potter &amp; Hermione Granger')

        self.story.addToList('genre','Fantasy')
        self.story.addToList('genre','Comedy')
        self.story.addToList('genre','Sci-Fi')
        self.story.addToList('genre','Noir')

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

        chapters = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
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
        for c in chapters:
            self.add_chapter(c[0],c[1],{'test':'asdf'})


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        self.do_sleep()
        if self.story.getMetadata('storyId').startswith('670') or \
                self.story.getMetadata('storyId').startswith('672'):
            time.sleep(1.0)

        if "chapter=1" in url :
            text=u'''
<div>
<h3>Prologue</h3>
<p>This is a fake adapter for testing purposes.  Different sid's will give different errors:</p>
<p>sid&gt;=1000 will use custom test story data from your configuration(personal.ini)</p>
<p>Hard coded ids:</p>
<p>http://test1.com?sid=664 - Crazy string title</p>
<p>http://test1.com?sid=665, 711-720 - raises AdultCheckRequired</p>
<p>http://test1.com?sid=666 - raises StoryDoesNotExist</p>
<p>http://test1.com?sid=667 - raises FailedToDownload on chapters 2+</p>
<p>http://test1.com?sid=668 - raises FailedToLogin unless username='Me'</p>
<p>http://test1.com?sid=669 - Succeeds with Updated Date=now</p>
<p>http://test1.com?sid=670 - Succeeds, but sleeps 2sec on each chapter</p>
<p>http://test1.com?sid=671 - Succeeds, but sleeps 2sec metadata only</p>
<p>http://test1.com?sid=672 - Succeeds, quick meta, sleeps 2sec chapters only</p>
<p>http://test1.com?sid=673 - Succeeds, multiple authors, extra categories, genres</p>
<p>http://test1.com?sid=674 - Succeeds, no numWords set</p>
<p>http://test1.com?sid=700 - 710 - Succeeds, changes sid to 80X</p>
<p>http://test1.com?sid=0 - Succeeds, generates some text specifically for testing hyphenation problems with Nook STR/STRwG</p>
<p>Odd sid's will be In-Progress, evens complete.  sid&lt;10 will be assigned one of four languages and included in a series.</p>
</div>
'''
        elif self.story.getMetadata('storyId') == '0':
            text=u'''<div>
<h3>45. Pronglet Returns to Hogwarts: Chapter 7</h3>
<br />
    eyes… but I’m not convinced we should automatically<br />
<br /><br />
<b>Thanks to the latest to recommend me: Alastor</b><br />
<br /><br />
    “Sure, invite her along. Does she have children?”<br />
<br />
</div>
'''
        elif self.story.getMetadata('storyId') == '667':
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)
        elif 'test1.com' not in url:
            ## for chapter_urls setting.
            origurl = url
            (data,opened) = self._fetchUrlOpened(url,extrasleep=2.0)
            url = opened.geturl()
            if '#' in origurl and '#' not in url:
                url = url + origurl[origurl.index('#'):]
            if url != origurl:
                logger.debug("chapter URL redirected to: %s"%url)

            soup = self.make_soup(data)


            if 'wordpress.com' in url:
                bq = soup.find('div',{'class':'entry-content'})
                addiv = soup.find('div',{'id':re.compile(r'^atatags')})
                for tag in addiv.find_all_next('div'):
                    tag.extract()
                addiv.extract()
            elif '#' in url:
                anchorid = url.split('#')[1]
                if 'spacebattles.com' in url or 'sufficientvelocity.com' in url:
                    # XF2
                    soup = soup.find('article',{'data-content':anchorid})
                    bq = soup.find('div',{'class':'bbWrapper'})
                else:
                    soup = soup.find('li',id=anchorid)
                    bq = soup.find('blockquote')
                    bq.name='div'

            for iframe in bq.find_all('iframe'):
                iframe.extract() # calibre book reader & editor don't like iframes to youtube.

            for qdiv in bq.find_all('div',{'class':'quoteExpand'}):
                qdiv.extract() # Remove <div class="quoteExpand">click to expand</div>
            for qdiv in bq.find_all('div',{'class':re.compile(r'bbCodeBlock-(expand|shrink)Link')}):
                qdiv.extract() # Remove <div class="quoteExpand">click to expand</div>
            for tag in bq.find_all('div', class_="bbCodeBlock-expandContent"):
                tag.name='blockquote'

            return self.utf8FromSoup(url[:url.index('/',8)+1],bq)

        else:
            text=u'''
<div>
<h3 extra="value">Chapter title from site</h3>
<style>
 p { color: red; }
 body { color:blue; margin: 5%; }
</style>
<p>chapter URL:'''+url+'''</p>
<p style="color:blue;">Timestamp:'''+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'''</p>
<p><img src="data:image/png;base64,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"></p>
<p>Lorem '''+self.crazystring+u''' <i>italics</i>, <b>bold</b>, <u>underline</u> consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
br breaks<br><br>
Puella Magi Madoka Magica/魔法少女まどか★マギカ
<!-- a href="http://code.google.com/p/fanficdownloader/wiki/FanFictionDownLoaderPluginWithReadingList" title="Tilt-a-Whirl by Jim &amp; Sarah, on Flickr"><img src="http://i.imgur.com/bo8eD.png"></a --><br/>
br breaks<br><br>
Don't&#8212e;ver&#8212d;o&#8212;that&#8212a;gain, &#27861; &#xE9;
<hr>
horizontal rules
<hr size=1 noshade>
<p>"Lorem ipsum dolor sit amet", consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore--et dolore magna aliqua. 'Ut enim ad minim veniam', quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
<br>
<br>
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.<br/>
<br/>
<br/>
<br>
<br>
 <br/>
<br/>  <br/>
<br/>
"Lorem ipsum dolor sit amet", consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore--et dolore magna aliqua. 'Ut enim ad minim veniam', quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.<br>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
'''
        soup = self.make_soup(text)
        return self.utf8FromSoup(url,soup)

    def get_urls_from_page(self,url,normalize):
        logger.debug("Fake series test1.com")
        '''
        This method is to make it easier for adapters to detect a
        series URL, pick out the series metadata and list of storyUrls
        to return without needing to override get_urls_from_page
        entirely.
        '''
        ## easiest way to get all the weird URL possibilities and stay
        ## up to date with future changes.
        return {'name':'The Great Test',
                'desc':'<div>The Great Test Series of test1.com!</div>',
                'urllist':['http://test1.com?sid=1',
                           'http://test1.com?sid=2',
                           'http://test1.com?sid=3',
                           'http://test1.com?sid=4',
                           'http://test1.com?sid=5',
                           'http://test1.com?sid=6',
                           'http://test1.com?sid=7',
                           'http://test1.com?sid=8',
                           'http://test1.com?sid=9',]
                }


def getClass():
    return TestSiteAdapter

