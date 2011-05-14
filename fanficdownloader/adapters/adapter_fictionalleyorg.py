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
import logging
import re
import urllib
import urllib2

import fanficdownloader.BeautifulSoup as bs
from fanficdownloader.htmlcleanup import stripHTML
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

class FictionAlleyOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fa')
        self.decode = "ISO-8859-1" ## fa *lies*.  It claims to be UTF8 in the headers, but it isn't.
        self.story.addToList("category","Harry Potter")
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('authorId',m.group('auth'))
            self.story.setMetadata('storyId',m.group('id'))
            logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
            # normalized story URL.
            self._setURL(url)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
            
    @staticmethod
    def getSiteDomain():
        return 'www.fictionalley.org'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/authors/drt/DA.html http://"+self.getSiteDomain()+"/authors/drt/JOTP01a.html"

    def getSiteURLPattern(self):
        # http://www.fictionalley.org/authors/drt/DA.html
        # http://www.fictionalley.org/authors/drt/JOTP01a.html
        return re.escape("http://"+self.getSiteDomain())+"/authors/(?P<auth>[a-zA-Z0-9_]+)/(?P<id>[a-zA-Z0-9_]+)\.html"

    def _postFetchWithIAmOld(self,url):
        if self.is_adult or self.getConfig("is_adult"):
            params={'iamold':'Yes',
                    'action':'ageanswer'}
            logging.info("Attempting to get cookie for %s" % url)
            ## posting on list doesn't work, but doesn't hurt, either.
            data = self._postUrl(url,params)
        else:
            data = self._fetchUrl(url)
        return data

    def extractChapterUrlsAndMetadata(self):

        ## could be either chapter list page or one-shot text page.
        url = self.url
        logging.debug("URL: "+url)

        try:
            data = self._postFetchWithIAmOld(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        chapterdata = data
        # If chapter list page, get the first chapter to look for adult check
        chapterlinklist = soup.findAll('a',{'class':'chapterlink'})
        if chapterlinklist:
            chapterdata = self._postFetchWithIAmOld(chapterlinklist[0]['href'])
            
        if "Are you over seventeen years old" in chapterdata:
            raise exceptions.AdultCheckRequired(self.url)
        
        if not chapterlinklist:
            # no chapter list, chapter URL: change to list link.
            # second a tag inside div breadcrumbs
            storya = soup.find('div',{'class':'breadcrumbs'}).findAll('a')[1]
            self._setURL(storya['href'])
            url=self.url
            logging.debug("Normalizing to URL: "+url)
            ## title's right there...
            self.story.setMetadata('title',storya.string)
            data = self._fetchUrl(url)
            soup = bs.BeautifulSoup(data)
            chapterlinklist = soup.findAll('a',{'class':'chapterlink'})
        else:
            ## still need title from somewhere.  If chapterlinklist,
            ## then chapterdata contains a chapter, find title the
            ## same way.
            chapsoup = bs.BeautifulSoup(chapterdata)
            storya = chapsoup.find('div',{'class':'breadcrumbs'}).findAll('a')[1]
            self.story.setMetadata('title',storya.string)
            del chapsoup

        del chapterdata
        
        ## authorid already set.
        ## <h1 class="title" align="center">Just Off The Platform II by <a href="http://www.fictionalley.org/authors/drt/">DrT</a></h1>
        authora=soup.find('h1',{'class':'title'}).find('a')
        self.story.setMetadata('author',authora.string)
        self.story.setMetadata('authorUrl',authora['href'])

        print chapterlinklist
        if len(chapterlinklist) == 1:
            self.chapterUrls.append((self.story.getMetadata('title'),chapterlinklist[0]['href']))
        else:
            # Find the chapters:
            for chapter in chapterlinklist:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## Go scrape the rest of the metadata from the author's page.
        data = self._fetchUrl(self.story.getMetadata('authorUrl'))
        soup = bs.BeautifulSoup(data)

        # <dl><dt><a class = "Rid story" href = "http://www.fictionalley.org/authors/aafro_man_ziegod/TMH.html">
        # [Rid] The Magical Hottiez</a> by <a class = "pen_name" href = "http://www.fictionalley.org/authors/aafro_man_ziegod/">Aafro Man Ziegod</a> </small></dt>
        # <dd><small class = "storyinfo"><a href = "http://www.fictionalley.org/ratings.html" target = "_new">Rating:</a> PG-13 - Spoilers: PS/SS, CoS, PoA, GoF, QTTA, FB - 4264 hits - 5060 words<br />
        # Genre: Humor, Romance - Main character(s): None - Ships: None - Era: Multiple Eras<br /></small>
        # Chaos ensues after Witch Weekly, seeking to increase readers, decides to create a boyband out of five seemingly talentless wizards: Harry Potter, Draco Malfoy, Ron Weasley, Neville Longbottom, and Oliver "Toss Your Knickers Here" Wood.<br />
        # <small class = "storyinfo">Published: June 3, 2002 (between Goblet of Fire and Order of Phoenix) - Updated: June 3, 2002</small>
        # </dd></dl>
        
        storya = soup.find('a',{'href':self.story.getMetadata('storyUrl')})
        storydd = storya.findNext('dd')

        # Rating: PG - Spoilers: None - 2525 hits - 736 words
        # Genre: Humor - Main character(s): H, R - Ships: None - Era: Multiple Eras
        # Harry and Ron are back at it again! They reeeeeeally don't want to be back, because they know what's awaiting them. "VH1 Goes Inside..." is back! Why? 'Cos there are soooo many more couples left to pick on.
        # Published: September 25, 2004 (between Order of Phoenix and Half-Blood Prince) - Updated: September 25, 2004 
               
        ## change to text and regexp find.
        metastr = stripHTML(storydd).replace('\n',' ').replace('\t',' ')

        m = re.match(r".*?Rating: (.+?) -.*?",metastr)
        if m:
            self.story.setMetadata('rating', m.group(1))

        m = re.match(r".*?Genre: (.+?) -.*?",metastr)
        if m:
            for g in m.group(1).split(','):
                self.story.addToList('genre',g)
        
        m = re.match(r".*?Published: ([a-zA-Z]+ \d\d?, \d\d\d\d).*?",metastr)
        if m:
            self.story.setMetadata('datePublished',makeDate(m.group(1), "%B %d, %Y"))

        m = re.match(r".*?Updated: ([a-zA-Z]+ \d\d?, \d\d\d\d).*?",metastr)
        if m:
            self.story.setMetadata('dateUpdated',makeDate(m.group(1), "%B %d, %Y"))

        m = re.match(r".*? (\d+) words Genre.*?",metastr)
        if m:
            self.story.setMetadata('numWords', m.group(1))
            
        for small in storydd.findAll('small'):
            small.extract() ## removes the <small> tags, leaving only the summary.
        self.story.setMetadata('description',stripHTML(storydd))
        
        return

    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
	# find <!-- headerend --> & <!-- footerstart --> and
	# replaced with matching div pair for easier parsing.
	# Yes, it's an evil kludge, but what can ya do?  Using
	# something other than div prevents soup from pairing
	# our div with poor html inside the story text.
	data = data.replace('<!-- headerend -->','<crazytagstringnobodywouldstumbleonaccidently id="storytext">').replace('<!-- footerstart -->','</crazytagstringnobodywouldstumbleonaccidently>')
        
        soup = bs.BeautifulStoneSoup(data,
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        body = soup.findAll('body') ## some stories use a nested body and body
                                    ## tag, in which case we don't
                                    ## need crazytagstringnobodywouldstumbleonaccidently
                                    ## and use the second one instead.
        if len(body)>1:
            text = body[1]
            text.name='div' # force to be a div to avoid multiple body tags.
        else:
            text = soup.find('crazytagstringnobodywouldstumbleonaccidently', {'id' : 'storytext'})
            text.name='div' # change to div tag.
            
        if not data or not text:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return utf8FromSoup(text)

def getClass():
    return FictionAlleyOrgSiteAdapter

