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

    def extractChapterUrlsAndMetadata(self):
        logger.debug('extractChapterUrlsAndMetadata: %s' % self.url)
        idstr = self.story.getMetadata('storyId')
        idnum = int(idstr)

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
            self._setURL('http://'+self.getSiteDomain()+'?sid=%s'%(idnum+100))
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

        prefix = self.getSiteDomain() if self.getSiteDomain() != 'test1.com' else ""
        if idstr == '664':
            self.story.setMetadata(u'title',prefix+"Test Story Title "+idstr+self.crazystring+"&nbsp;&nbsp;")
            self.story.setMetadata('author',prefix+'Test Author aa bare amp(&) quote(&#39;) amp(&amp;)')
        else:
            self.story.setMetadata(u'title',prefix+"Test Story Title "+idstr)
            self.story.setMetadata('author',prefix+'Test Author aa')
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
            self.story.setMetadata('seriesUrl','http://'+self.getSiteDomain()+'/seriesid=1')
        elif idnum < 20:
            self.setSeries('魔法少女まどか★マギカ',idnum)
            self.story.setMetadata('seriesUrl','http://'+self.getSiteDomain()+'/seriesid=1')
        if idnum == 0:
            self.setSeries("A Nook Hyphen Test "+self.story.getMetadata('dateCreated'),idnum)
            self.story.setMetadata('seriesUrl','http://'+self.getSiteDomain()+'/seriesid=0')

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
                    ]
        if self.getSiteDomain() == 'test4.com':
            for i in range(9,idnum):
                chapters.append(('Chapter %s'%i,
                                 self.url+"&chapter=%s"%i))
        for c in chapters:
            self.add_chapter(c[0],c[1],{'test':'asdf'})


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        if( self.getConfig('slow_down_sleep_time',False)
            or self.story.getMetadata('storyId').startswith('670')
            or self.story.getMetadata('storyId').startswith('672') ):
            import random
            t = float(self.getConfig('slow_down_sleep_time',1.0))
            rt = random.uniform(t*0.5, t*1.5)
            logger.debug("random sleep(%0.2f-%0.2f):%0.2f"%(t*0.5, t*1.5,rt))
            time.sleep(rt)

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
        elif self.story.getMetadata('storyId') == '667' and "chapter=2" in url:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)
        elif self.getSiteDomain() not in url:
            ## for chapter_urls setting.
            origurl = url
            (data,url) = self.get_request_redirected(url)
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
<div class='chapter'>
<h3 extra="value">Chapter title from site</h3>
<style>
 p { color: red; }
 body { color:blue; margin: 5%; }
</style>
<p>chapter URL:'''+url+'''</p>
<p style="color:blue;">Timestamp:'''+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'''</p>
<p class='chapter ptag'>Lorem '''+self.crazystring+u''' <i>italics</i>, <b>bold</b>, <u>underline</u>, <s>Strike through</s> consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
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
        logger.debug("Fake series "+self.getSiteDomain())
        '''
        This method is to make it easier for adapters to detect a
        series URL, pick out the series metadata and list of storyUrls
        to return without needing to override get_urls_from_page
        entirely.
        '''
        ## easiest way to get all the weird URL possibilities and stay
        ## up to date with future changes.
        return {'name':'The Great Test',
                'desc':'<div>The Great Test Series of '+self.getSiteDomain()+'!</div>',
                'urllist':['http://'+self.getSiteDomain()+'?sid=1',
                           'http://'+self.getSiteDomain()+'?sid=2',
                           'http://'+self.getSiteDomain()+'?sid=3',
                           'http://'+self.getSiteDomain()+'?sid=4',
                           'http://'+self.getSiteDomain()+'?sid=5',
                           'http://'+self.getSiteDomain()+'?sid=6',
                           'http://'+self.getSiteDomain()+'?sid=7',
                           'http://'+self.getSiteDomain()+'?sid=8',
                           'http://'+self.getSiteDomain()+'?sid=9',]
                }


def getClass():
    return TestSiteAdapter

'''
from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)

from .adapter_test1 import TestSiteAdapter

class Test2SiteAdapter(TestSiteAdapter):

    def __init__(self, config, url):
        TestSiteAdapter.__init__(self, config, url)

    @staticmethod
    def getSiteDomain():
        return 'test2.com'

def getClass():
    return Test2SiteAdapter
'''
