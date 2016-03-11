# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2015 FanFicFare team
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

from .. import exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class TestSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tst1')
        self.crazystring = u"tests:[bare amp(&) qt(&#39;) amp(&amp;) gt(&gt;) lt(&lt;) ATnT(AT&T) L(&pound;) Onna(女)]"
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        self.username=''
        self.is_adult=False
        # happens inside BaseSiteAdapter.__init__
        # self._setURL(url)

    @staticmethod
    def getSiteDomain():
        return 'test1.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"?sid=1234"

    def getSiteURLPattern(self):
        return BaseSiteAdapter.getSiteURLPattern(self)+r'/?\?sid=\d+$'

    def extractChapterUrlsAndMetadata(self):
        idstr = self.story.getMetadata('storyId')
        idnum = int(idstr)
        self.do_sleep()

        if idnum >= 1000:
            logger.warn("storyId:%s - Custom INI data will be used."%idstr)

            sections = ['teststory:%s'%idstr,'teststory:defaults']
            #print("self.get_config_list(sections,'valid_entries'):%s"%self.get_config_list(sections,'valid_entries'))
            for key in self.get_config_list(sections,'valid_entries'):
                if key.endswith("_list"):
                    nkey = key[:-len("_list")]
                    #print("addList:%s"%(nkey))
                    for val in self.get_config_list(sections,key):
                        #print("addList:%s->%s"%(nkey,val))
                        self.story.addToList(nkey,val.decode('utf-8').replace('{{storyId}}',idstr))
                else:
                    # Special cases:
                    if key in ['datePublished','dateUpdated']:
                        self.story.setMetadata(key,makeDate(self.get_config(sections,key),"%Y-%m-%d"))
                    else:
                        self.story.setMetadata(key,self.get_config(sections,key).decode('utf-8').replace('{{storyId}}',idstr))
                    #print("set:%s->%s"%(key,self.story.getMetadata(key)))

            self.chapterUrls = []
            if self.has_config(sections,'chapter_urls'):
                for l in self.get_config(sections,'chapter_urls').splitlines() :
                    if l:
                        self.chapterUrls.append( (l[1+l.index(','):],l[:l.index(',')]) )
            else:
                for (j,chap) in enumerate(self.get_config_list(sections,'chaptertitles'),start=1):
                    self.chapterUrls.append( (chap,self.url+"&chapter=%d"%j) )
            # self.chapterUrls = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
            #                 ('Chapter 1, Xenos on Cinnabar',self.url+"&chapter=2"),
            #                 ]
            self.story.setMetadata('numChapters',len(self.chapterUrls))

            return

        if idnum >= 700 and idnum <= 710:
            self._setURL('http://test1.com?sid=%s'%(idnum+100))
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
            idstr = self.story.getMetadata('storyId')
            idnum = int(idstr)

        if idstr == '665' and not (self.is_adult or self.getConfig("is_adult")):
            logger.warn("self.is_adult:%s"%self.is_adult)
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
            self.story.setMetadata(u'title',"Test Story Title "+idstr+self.crazystring)
            self.story.setMetadata('author','Test Author aa bare amp(&) quote(&#39;) amp(&amp;)')
        else:
            self.story.setMetadata(u'title',"Test Story Title "+idstr)
            self.story.setMetadata('author','Test Author aa')
        self.setDescription(self.url,u'Description '+self.crazystring+u''' Done
<p>
Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
''')
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
            self.story.setMetadata('seriesUrl','http://test1.com?seriesid=1')
        if idnum == 0:
            self.setSeries("A Nook Hyphen Test "+self.story.getMetadata('dateCreated'),idnum)
            self.story.setMetadata('seriesUrl','http://test1.com?seriesid=0')

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
            self.story.addToList('category','Crossover')
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
        self.do_sleep()
        if self.story.getMetadata('storyId').startswith('670') or \
                self.story.getMetadata('storyId').startswith('672'):
            time.sleep(1.0)

        if "chapter=1" in url :
            text=u'''
<div>
<h3>Prologue</h3>
<p>This is a fake adapter for testing purposes.  Different sid's will give different errors:</p>
<h4>Config(personal.ini)</h4>
<p>sid&gt;=1000 will use custom test story data from your configuration(personal.ini)</p>
<p>Hard coded ids:</p>
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
            logger.debug('Getting chapter text from: %s' % url)

            try:
                origurl = url
                (data,opened) = self._fetchUrlOpened(url,extrasleep=2.0)
                url = opened.geturl()
                if '#' in origurl and '#' not in url:
                    url = url + origurl[origurl.index('#'):]
                logger.debug("chapter URL redirected to: %s"%url)

                soup = self.make_soup(data)

                if '#' in url:
                    anchorid = url.split('#')[1]
                    soup = soup.find('li',id=anchorid)

                bq = soup.find('blockquote')

                bq.name='div'

                for iframe in bq.find_all('iframe'):
                    iframe.extract() # calibre book reader & editor don't like iframes to youtube.

                for qdiv in bq.find_all('div',{'class':'quoteExpand'}):
                    qdiv.extract() # Remove <div class="quoteExpand">click to expand</div>

            except Exception as e:
                if self.getConfig('continue_on_chapter_error'):
                    bq = self.make_soup("""<div>
<p><b>Error</b></p>
<p>FanFicFare failed to download this chapter.  Because you have
<b>continue_on_chapter_error</b> set to <b>true</b> in your personal.ini, the download continued.</p>
<p>Chapter URL:<br>%s</p>
<p>Error:<br><pre>%s</pre></p>
</div>"""%(url,traceback.format_exc()))
                else:
                    raise

            return self.utf8FromSoup(url[:url.index('/',8)+1],bq)

        else:
            text=u'''
<div>
<h3 extra="value">Chapter title from site</h3>
<p>chapter URL:'''+url+'''</p>
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
<p>"Lorem ipsum dolor sit amet", consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore--et dolore magna aliqua. 'Ut enim ad minim veniam', quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
'''
        soup = self.make_soup(text)
        return self.utf8FromSoup(url,soup)

def getClass():
    return TestSiteAdapter

