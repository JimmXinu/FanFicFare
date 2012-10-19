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
logger = logging.getLogger(__name__)
import re
import urllib2

from .. import BeautifulSoup as bs
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
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
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

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/works/123456 http://"+self.getSiteDomain()+"/collections/Some_Archive/works/123456"

    def getSiteURLPattern(self):
        # http://archiveofourown.org/collections/Smallville_Slash_Archive/works/159770
        return re.escape("http://")+re.escape(self.getSiteDomain())+r"(/collections/[^/]+)?/works/(?P<id>\d+)"
        
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
                raise exceptions.StoryDoesNotExist(self.meta)
            else:
                raise e
                
        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url,data)
            data = self._fetchUrl(url)
            meta = self._fetchUrl(metaurl)
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        metasoup = bs.BeautifulSoup(meta)

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('a', href=re.compile(r"^/works/\d+$"))
        self.story.setMetadata('title',a.string)
		
        # Find authorid and URL from... author url.
        alist = soup.findAll('a', href=re.compile(r"^/users/\w+/pseuds/\w+"))
        if len(alist) < 1: # ao3 allows for author 'Anonymous' with no author link.
            self.story.setMetadata('author','Anonymous')
            self.story.setMetadata('authorUrl','http://archiveofourown.org/')
            self.story.setMetadata('authorId','0')
        else:
            for a in alist:
                self.story.addToList('authorId',a['href'].split('/')[2])
                self.story.addToList('authorUrl','http://'+self.host+a['href'])
                self.story.addToList('author',a.text)

        # Find the chapters:
        chapters=soup.findAll('a', href=re.compile(r'/works/'+self.story.getMetadata('storyId')+"/chapters/\d+$"))
        self.story.setMetadata('numChapters',len(chapters))
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        for x in range(0,len(chapters)):
            # just in case there's tags, like <i> in chapter titles.
            chapter=chapters[x]
            if len(chapters)==1:
                self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+chapter['href']+addurl))
            else:
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']+addurl))



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
                if warning.string == "Author Chose Not To Use Archive Warnings":
                    warning.string = "No Archive Warnings Apply"
                if warning.string != "No Archive Warnings Apply":
                    self.story.addToList('warnings',warning.string)
		
        a = metasoup.find('dd',{'class':"freeform tags"})
        if a != None:
            genres = a.findAll('a',{'class':"tag"})
            for genre in genres:
                self.story.addToList('freefromtags',genre.string)
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

		
        try:
            # Find Series name from series URL.
            a = metasoup.find('dd',{'class':"series"})
            b = a.find('a', href=re.compile(r"/series/\d+"))
            series_name = b.string
            series_url = 'http://'+self.host+'/fanfic/'+b['href']
            series_index = int(a.text.split(' ')[1])
            self.setSeries(series_name, series_index)
            
        except:
            # I find it hard to care if the series parsing fails
            pass

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
		
        chapter=bs.BeautifulSoup('<div class="story"></div>')
        data = self._fetchUrl(url)
        soup = bs.BeautifulSoup(data,selfClosingTags=('br','hr'))
		
        headnotes = soup.find('div', {'class' : "preface group"}).find('div', {'class' : "notes module"})
        if headnotes != None:
            headnotes = headnotes.find('blockquote', {'class' : "userstuff"})
            if headnotes != None:
                chapter.append("<b>Author's Note:</b>")
                chapter.append(headnotes)
        
        chapsumm = soup.find('div', {'id' : "summary"})
        if chapsumm != None:
            chapsumm = chapsumm.find('blockquote')
            chapter.append("<b>Summary for the Chapter:</b>")
            chapter.append(chapsumm)
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
		
        chapfoot = soup.find('div', {'class' : "end notes module", 'role' : "complementary"})
        if chapfoot != None:
            chapfoot = chapfoot.find('blockquote')
            chapter.append("<b>Notes for the Chapter:</b>")
            chapter.append(chapfoot)
		
        footnotes = soup.find('div', {'id' : "work_endnotes"})
        if footnotes != None:
            footnotes = footnotes.find('blockquote')
            chapter.append("<b>Author's Note:</b>")
            chapter.append(footnotes)
			
        if None == soup:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter)
