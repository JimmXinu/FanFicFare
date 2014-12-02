#  -*- coding: utf-8 -*-

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
logger = logging.getLogger(__name__)
import re
import urllib2

#from .. import BeautifulSoup as bs
import bs4 as bs

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return ArchiveOfOurOwnOrgAdapter


logger = logging.getLogger(__name__)

class ArchiveOfOurOwnOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
							   
							   
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])
        
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            
            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/works/'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ao3')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%b-%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'archiveofourown.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/works/123456 http://"+cls.getSiteDomain()+"/collections/Some_Archive/works/123456 http://"+cls.getSiteDomain()+"/works/123456/chapters/78901"

    def getSiteURLPattern(self):
        # http://archiveofourown.org/collections/Smallville_Slash_Archive/works/159770
        # Discard leading zeros from story ID numbers--AO3 doesn't use them in it's own chapter URLs.
        return r"https?://"+re.escape(self.getSiteDomain())+r"(/collections/[^/]+)?/works/0*(?P<id>\d+)"
        
    ## Login
    def needToLoginCheck(self, data):
        if 'This work is only available to registered users of the Archive.' in data \
                or "The password or user name you entered doesn't match our records" in data:
            return True
        else:
            return False
        
    def performLogin(self, url, data):

        params = {}
        if self.password:
            params['user_session[login]'] = self.username
            params['user_session[password]'] = self.password
        else:
            params['user_session[login]'] = self.getConfig("username")
            params['user_session[password]'] = self.getConfig("password")
        params['user_session[remember_me]'] = '1'
        params['commit'] = 'Log in'
        #params['utf8'] = u'✓'#u'\x2713' # gets along with out it, and it confuses the encoder.
        params['authenticity_token'] = data.split('input name="authenticity_token" type="hidden" value="')[1].split('" /></div>')[0]

        loginUrl = 'http://' + self.getSiteDomain() + '/user_sessions'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['user_session[login]']))
    
        d = self._postUrl(loginUrl, params)
        #logger.info(d)
    
        if "Successfully logged in" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['user_session[login]']))
            raise exceptions.FailedToLogin(url,params['user_session[login]'])
            return False
        else:
            return True

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            addurl = "?view_adult=true"
        else:
            addurl=""

        metaurl = self.url+addurl
        url = self.url+'/navigate'+addurl
        logger.info("url: "+url)
        logger.info("metaurl: "+metaurl)

        try:
            data = self._fetchUrl(url)
            meta = self._fetchUrl(metaurl)

            if "This work could have adult content. If you proceed you have agreed that you are willing to see such content." in meta:
                raise exceptions.AdultCheckRequired(self.url)
            
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Sorry, we couldn&#x27;t find the work you were looking for." in data:
            raise exceptions.StoryDoesNotExist(self.url)
            
        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url,data)
            data = self._fetchUrl(url,usecache=False)
            meta = self._fetchUrl(metaurl,usecache=False)
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        for tag in soup.findAll('div',id='admin-banner'):
            tag.extract()
        metasoup = bs.BeautifulSoup(meta)
        for tag in metasoup.findAll('div',id='admin-banner'):
            tag.extract()

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('a', href=re.compile(r"/works/\d+$"))
        self.story.setMetadata('title',stripHTML(a))
		
        # Find authorid and URL from... author url.
        alist = soup.findAll('a', href=re.compile(r"/users/\w+/pseuds/\w+"))
        if len(alist) < 1: # ao3 allows for author 'Anonymous' with no author link.
            self.story.setMetadata('author','Anonymous')
            self.story.setMetadata('authorUrl','http://archiveofourown.org/')
            self.story.setMetadata('authorId','0')
        else:
            for a in alist:
                self.story.addToList('authorId',a['href'].split('/')[-1])
                self.story.addToList('authorUrl',a['href'])
                self.story.addToList('author',a.text)

        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest, on AO3 it's
        # possible for authors to insert new chapters out-of-order or
        # change the dates of earlier ones by editing them--That WILL
        # break epub update.
        # Find the chapters:
        chapters=soup.findAll('a', href=re.compile(r'/works/'+self.story.getMetadata('storyId')+"/chapters/\d+$"))
        self.story.setMetadata('numChapters',len(chapters))
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        if len(chapters)==1:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+chapters[0]['href']+addurl))
        else:
            for index, chapter in enumerate(chapters):
                # strip just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']+addurl))
                # (2013-09-21)
                date = stripHTML(chapter.findNext('span'))[1:-1]
                chapterDate = makeDate(date,self.dateformat)
                if newestChapter == None or chapterDate > newestChapter:
                    newestChapter = chapterDate
                    self.newestChapterNum = index

        a = metasoup.find('blockquote',{'class':'userstuff'})
        if a != None:
            self.setDescription(url,a)
            #self.story.setMetadata('description',a.text)
		
        a = metasoup.find('dd',{'class':"rating tags"})
        if a != None:
            self.story.setMetadata('rating',stripHTML(a.text))
		
        a = metasoup.find('dd',{'class':"fandom tags"})
        fandoms = a.findAll('a',{'class':"tag"})
        for fandom in fandoms:
            self.story.addToList('fandoms',fandom.string)
            self.story.addToList('category',fandom.string)
		
        a = metasoup.find('dd',{'class':"warning tags"})
        if a != None:
            warnings = a.findAll('a',{'class':"tag"})
            for warning in warnings:
                self.story.addToList('warnings',warning.string)
		
        a = metasoup.find('dd',{'class':"freeform tags"})
        if a != None:
            genres = a.findAll('a',{'class':"tag"})
            for genre in genres:
                self.story.addToList('freeformtags',genre.string)
                self.story.addToList('genre',genre.string)
                
        a = metasoup.find('dd',{'class':"category tags"})
        if a != None:
            genres = a.findAll('a',{'class':"tag"})
            for genre in genres:
                if genre != "Gen":
                    self.story.addToList('ao3categories',genre.string)
                    self.story.addToList('genre',genre.string)
		
        a = metasoup.find('dd',{'class':"character tags"})
        if a != None:
            chars = a.findAll('a',{'class':"tag"})
            for char in chars:
                self.story.addToList('characters',char.string)
                
        a = metasoup.find('dd',{'class':"relationship tags"})
        if a != None:
            ships = a.findAll('a',{'class':"tag"})
            for ship in ships:
                self.story.addToList('ships',ship.string)
		
        a = metasoup.find('dd',{'class':"collections"})
        if a != None:
            collections = a.findAll('a')
            for collection in collections:
                self.story.addToList('collections',collection.string)
		
        stats = metasoup.find('dl',{'class':'stats'})
        dt = stats.findAll('dt')
        dd = stats.findAll('dd')
        for x in range(0,len(dt)):
            label = dt[x].text
            value = dd[x].text

            if 'Words:' in label:
                self.story.setMetadata('numWords', value)
				
            if 'Comments:' in label:
                self.story.setMetadata('comments', value)
				
            if 'Kudos:' in label:
                self.story.setMetadata('kudos', value)
				
            if 'Hits:' in label:
                self.story.setMetadata('hits', value)
				
            if 'Bookmarks:' in label:
                self.story.setMetadata('bookmarks', value)
				
            if 'Chapters:' in label:
                if value.split('/')[0] == value.split('/')[1]:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')


            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
				
            if 'Completed' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

		
        # Find Series name from series URL.
        ddseries = metasoup.find('dd',{'class':"series"})

        if ddseries:
            for i, a in enumerate(ddseries.findAll('a', href=re.compile(r"/series/\d+"))):
                series_name = stripHTML(a)
                series_url = 'http://'+self.host+a['href']
                series_index = int(stripHTML(a.previousSibling).replace(', ','').split(' ')[1]) # "Part # of" or ", Part #"
                self.story.setMetadata('series%02d'%i,"%s [%s]"%(series_name,series_index))
                self.story.setMetadata('series%02dUrl'%i,series_url)
                if i == 0:
                    self.setSeries(series_name, series_index)
                    self.story.setMetadata('seriesUrl',series_url)

    def hookForUpdates(self,chaptercount):
        if self.oldchapters and len(self.oldchapters) > self.newestChapterNum:
            print("Existing epub has %s chapters\nNewest chapter is %s.  Discarding old chapters from there on."%(len(self.oldchapters), self.newestChapterNum+1))
            self.oldchapters = self.oldchapters[:self.newestChapterNum]
        return len(self.oldchapters)
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
		
        chapter=bs.BeautifulSoup('<div class="story"></div>').find('div')
        data = self._fetchUrl(url)
        soup = bs.BeautifulSoup(data)

        exclude_notes=self.getConfigList('exclude_notes')

        if 'authorheadnotes' not in exclude_notes:
            headnotes = soup.find('div', {'class' : "preface group"}).find('div', {'class' : "notes module"})
            if headnotes != None:
                headnotes = headnotes.find('blockquote', {'class' : "userstuff"})
                if headnotes != None:
                    chapter.append("<b>Author's Note:</b>")
                    chapter.append(headnotes)
        
        if 'chaptersummary' not in exclude_notes:
            chapsumm = soup.find('div', {'id' : "summary"})
            if chapsumm != None:
                chapsumm = chapsumm.find('blockquote')
                chapter.append("<b>Summary for the Chapter:</b>")
                chapter.append(chapsumm)
                
        if 'chapterheadnotes' not in exclude_notes:
            chapnotes = soup.find('div', {'id' : "notes"})
            if chapnotes != None:
                chapnotes = chapnotes.find('blockquote')
                if chapnotes != None:
                    chapter.append("<b>Notes for the Chapter:</b>")
                    chapter.append(chapnotes)
		
        text = soup.find('div', {'class' : "userstuff module"})
        chtext = text.find('h3', {'class' : "landmark heading"})
        if chtext:
            chtext.extract()
        chapter.append(text)
		
        if 'chapterfootnotes' not in exclude_notes:
            chapfoot = soup.find('div', {'class' : "end notes module", 'role' : "complementary"})
            if chapfoot != None:
                chapfoot = chapfoot.find('blockquote')
                chapter.append("<b>Notes for the Chapter:</b>")
                chapter.append(chapfoot)
		
        if 'authorfootnotes' not in exclude_notes:
            footnotes = soup.find('div', {'id' : "work_endnotes"})
            if footnotes != None:
                footnotes = footnotes.find('blockquote')
                chapter.append("<b>Author's Note:</b>")
                chapter.append(footnotes)
			
        if None == soup:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)
