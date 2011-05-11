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

import time
import datetime
import logging
import re
import urllib
import urllib2

import fanficdownloader.BeautifulSoup as bs
from fanficdownloader.htmlcleanup import stripHTML
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup

class MediaMinerOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','mm')
        self.decode = "utf8"
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/fanfic/view_st.php/'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
            
    @staticmethod
    def getSiteDomain():
        return 'www.mediaminer.org'

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain()]

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/fanfic/view_st.php/123456 http://"+self.getSiteDomain()+"/fanfic/view_ch.php/1234123/123444#fic_c"

    def getSiteURLPattern(self):
        ##  http://www.mediaminer.org/fanfic/view_st.php/76882
        ##  http://www.mediaminer.org/fanfic/view_ch.php/167618/594087#fic_c
        return re.escape("http://"+self.getSiteDomain())+\
            "/fanfic/view_(st|ch)\.php/"+r"(?P<id>\d+)(/\d+#fic_c)?$"

    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logging.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        ## Title
        title = soup.find('title').string
        ## MediaMiner - Fan Fic: Par Tout Autre Nom
        ## MediaMiner: Question and Answer ( One-Shot )
        ## MediaMiner: Moaning to Wake the Dead ( Chapter 1 )
        title = re.match(r'^MediaMiner(?: - Fan Fic)?:(.*?)(?: \( .*? \))?$',title).group(1)

        # [ A - All Readers ], strip '[ ' ' ]'
        rating = soup.find("font",{"class":"smtxt"}).string[1:-1]
        self.story.setMetadata('title',title)
        self.story.setMetadata('rating',rating)

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/fanfic/src.php/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # save date from first for later.
        firstdate=None
        
        # Find the chapters
        select = soup.find('select',{'name':'cid'})
        if not select:
            self.chapterUrls.append((title,self.url))
        else:
            for option in select.findAll("option"):
                chapter = stripHTML(option.string)
                ## chapter can be: Chapter 7 [Jan 23, 2011]
                ##             or: Vigilant Moonlight ( Chapter 1 ) [Jan 30, 2004]
                ##        or even: Prologue ( Prologue ) [Jul 31, 2010]
                m = re.match(r'^(.*?) (\( .*? \))? \[(.*?)\]$',chapter)
                chapter = m.group(1)
                # save date from first for later.
                if not firstdate:
                    firstdate = m.group(3)
                self.chapterUrls.append((chapter,'http://'+self.host+'/fanfic/view_ch.php/'+self.story.getMetadata('storyId')+'/'+option['value']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # category
        # <a href="/fanfic/src.php/a/567">Ranma 1/2</a>
        for a in soup.findAll('a',href=re.compile(r"^/fanfic/src.php/a/")):
            self.story.addToList('category',a.string)
        
        # genre
        # <a href="/fanfic/src.php/a/567">Ranma 1/2</a>
        for a in soup.findAll('a',href=re.compile(r"^/fanfic/src.php/g/")):
            self.story.addToList('genre',a.string)

        # if firstdate, then the block below will only have last updated.
        if firstdate:
            self.story.setMetadata('datePublished', 
                                   datetime.datetime.fromtimestamp(time.mktime(time.strptime(firstdate, "%b %d, %Y"))))
        # Everything else is in <tr bgcolor="#EEEED4">

        metastr = stripHTML(soup.find("tr",{"bgcolor":"#EEEED4"})).replace('\n',' ').replace('\r',' ').replace('\t',' ')
        print metastr
        # Latest Revision: August 03, 2010
        m = re.match(r".*?(?:Latest Revision|Uploaded On): ([a-zA-Z]+ \d\d, \d\d\d\d)",metastr)
        if m:
            self.story.setMetadata('dateUpdated', 
                                   datetime.datetime.fromtimestamp(time.mktime(time.strptime(m.group(1), "%B %d, %Y"))))
            if not firstdate:
                self.story.setMetadata('datePublished',
                                       self.story.getMetadataRaw('dateUpdated'))
                
        else:
            self.story.setMetadata('dateUpdated',
                                   self.story.getMetadataRaw('datePublished'))

        # Words: 123456
        m = re.match(r".*?\| Words: (\d+) \|",metastr)
        if m:
            self.story.setMetadata('numWords', m.group(1))
            
        # Summary: ....
        m = re.match(r".*?Summary: (.*)$",metastr) 
        if m:
            self.story.setMetadata('description', m.group(1))

        # completed
        m = re.match(r".*?Status: Completed.*?",metastr)
        if m:
            self.story.setMetadata('status','Completed')
        else:
            self.story.setMetadata('status','In-Progress')

        return

    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.

        anchor = soup.find('a',{'name':'fic_c'})

        if None == anchor:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        for div in anchor.findAllNext('div',{'align':'left'}):
            div.name='p' # convert to <p> mediaminer uses div with a
                         # margin for paragraphs.
            anchor.append(div) # cheat!  stuff all the content divs
                               # into anchor just as a holder.
        
        return utf8FromSoup(anchor)

def getClass():
    return MediaMinerOrgSiteAdapter

