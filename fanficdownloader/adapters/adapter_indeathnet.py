# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team
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

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return InDeathNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class InDeathNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

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
            
            # normalized story URL.
            self._setURL('http://www.' + self.getSiteDomain() + '/blog/archive/'+self.story.getMetadata('storyId')+'-'+m.group('name')+'/')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','idn')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %B %Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'indeath.net'


    @classmethod
    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/blog/archive/123-story-in-death/"

    def getSiteURLPattern(self):
        # http://www.indeath.net/blog/archive/169-ransom-in-death/
        return re.escape("http://")+re.escape(self.getSiteDomain())+r"/blog/(archive/)?(?P<id>\d+)\-(?P<name>[a-z0-9\-]*)/?$"     
        
            
    def getDateFromComponents(self, postmonth, postday):
        ym = re.search("Entries\ in\ (?P<mon>January|February|March|April|May|June|July|August|September|October|November|December)\ (?P<year>\d{4})",postmonth)
        d = re.search("(?P<day>\d{2})\ (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",postday)
        postdate = makeDate(d.group('day')+' '+ym.group('mon')+' '+ym.group('year'),self.dateformat)
        return postdate

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        try:
            data = self._fetchUrl(url)
            
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.meta)
            else:
                raise e
                
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        h = soup.find('a', id="blog_title")
        t = h.find('span')
        self.story.setMetadata('title',stripHTML(t.contents[0]).strip())
		
        s = t.find('div')        
        if s != None:
            self.setDescription(url,s)
		
        # Find authorid and URL from first link in Recent Entries (don't yet reference 'recent entries' - let's see if that is required)
        a = soup.find('a', href=re.compile(r"http://www.indeath.net/user/\d+\-[a-z0-9]+/$"))		#http://www.indeath.net/user/9083-cyrex/
        m = re.search('http://www.indeath.net/user/(?P<id>\d+)\-(?P<name>[a-z0-9]*)/$',a['href'])
        self.story.setMetadata('authorId',m.group('id'))
        self.story.setMetadata('authorUrl',a['href'])
        self.story.setMetadata('author',m.group('name'))

        # Find the chapters:
        chapters=soup.findAll('a', title="View entry", href=re.compile(r'http://www.indeath.net/blog/'+self.story.getMetadata('storyId')+"/entry\-(\d+)\-([^/]*)/$"))

        #reverse the list since newest at the top
        chapters.reverse()
        
        # Get date published & updated from first & last entries
        posttable=soup.find('div', id="main_column")
        
        postmonths=posttable.findAll('th', text=re.compile(r'Entries\ in\ '))
        postmonths.reverse()
        
        postdates=posttable.findAll('span', _class="desc", text=re.compile('\d{2}\ (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'))
        postdates.reverse()
        
        self.story.setMetadata('datePublished',self.getDateFromComponents(postmonths[0],postdates[0]))
        self.story.setMetadata('dateUpdated',self.getDateFromComponents(postmonths[len(postmonths)-1],postdates[len(postdates)-1]))
        
        # Process List of Chapters              
        self.story.setMetadata('numChapters',len(chapters))
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        for x in range(0,len(chapters)):
            # just in case there's tags, like <i> in chapter titles.
            chapter=chapters[x]
            if len(chapters)==1:
                self.chapterUrls.append((self.story.getMetadata('title'),chapter['href']))
            else:
            	ct = stripHTML(chapter)
            	tnew = re.match("(?i)"+self.story.getMetadata('title')+r" - (?P<newtitle>.*)$",ct)
            	if tnew:
            		chaptertitle = tnew.group('newtitle')
            	else:
            		chaptertitle = ct
                self.chapterUrls.append((chaptertitle,chapter['href']))
	
		
        
        
    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
		
        #chapter=bs.BeautifulSoup('<div class="story"></div>')
        data = self._fetchUrl(url)
        soup = bs.BeautifulSoup(data,selfClosingTags=('br','hr','span','center'))

        chapter = soup.find("div", "entry_content")
        
        if None == chapter:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)

