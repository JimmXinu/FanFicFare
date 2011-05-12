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
import urllib2
import time

import fanficdownloader.BeautifulSoup as bs
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

class FictionPressComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fpcom')
        
        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # normalized story URL.
        self._setURL("http://"+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId')+"/1/")

    @staticmethod
    def getSiteDomain():
        return 'www.fictionpress.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fictionpress.com']

    def getSiteExampleURLs(self):
        return "http://www.fictionpress.com/s/1234/1/ http://www.fictionpress.com/s/1234/12/ http://www.fictionpress.com/s/1234/1/Story_Title"

    def getSiteURLPattern(self):
        return r"http://www\.fictionpress\.com/s/\d+/\d+(/|/[a-zA-Z0-9_]+)?$"

    def extractChapterUrlsAndMetadata(self):

        # fetch the chapter.  From that we will get metadata and chapter list
        # You'd think this would be very similar to ffnet.  But you'd be wrong.

        url = self.url
        logging.debug("URL: "+url)
        logging.debug('Getting metadata from: %s' % url)
        
        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            soup = bs.BeautifulSoup(self._fetchUrl(url))
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
            
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # <title>Starr and Temple Detective Agency, a Sci-Fi fanfic - FictionPress.com</title>
        title = soup.find('title')
        m = re.match(r"^(.*?), a (.*?) fanfic - FictionPress.com",title.string)
        title,category = m.groups()
        self.story.setMetadata('title', title)
        self.story.addToList('category',category)
            
        # Find the chapter selector 
        select = soup.find('select', { 'name' : 'chapter' } )
    	 
        if select is None:
    	   # no selector found, so it's a one-chapter story.
    	   self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = u'http://%s/s/%s/%s/' % ( self.getSiteDomain(),
                                            self.story.getMetadata('storyId'),
                                            o['value'])
                # just in case there's tags, like <i> in chapter titles.
                title = u"%s" % o
                title = re.sub(r'<[^>]+>','',title)
                self.chapterUrls.append((title,url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## Pull some additional data from html.

        # Find Rating and look around it.
        a = soup.find('a', href=re.compile(r'^http://www.fictionratings.com'))
        # "Fiction Rated: K+"
        self.story.setMetadata('rating',a.string.split()[-1])

        # after Rating, the same bit of text containing id:123456 contains
        # Complete--if completed, and Published/Updated dates.
        # - Published: 02-07-11 - Updated: 02-07-11 - Complete - id:2889508
        dataline = a.findNext(text=re.compile(r'id:'+self.story.getMetadata('storyId')))
        if dataline:
            if 'Complete' in dataline:
                self.story.setMetadata('status', 'Completed')
            else:
                self.story.setMetadata('status', 'In-Progress')

            m = re.match(r".*?Published: ([0-9-]+) - Updated: ([0-9-]+).*?",dataline)
            if m:
                published,updated = m.groups()
                self.story.setMetadata('datePublished',makeDate(published, '%m-%d-%y'))
                self.story.setMetadata('dateUpdated',makeDate(updated, '%m-%d-%y'))
                               
        # category, genres, then desc.
        # <meta name="description" content="Sci-Fi, Sci-Fi/Crime,  Gabriel Starr is a hardboiled former Planetary Marine turned cyborg detective. Philo Temple is a child genius who helped build him. Together, they form a detective agency in a retro-futuristic world of alien gangsters, beatiful dames, and blazing ray guns">
        # Parse genre(s) and description from <meta name="description" content="..."
        m = re.match(r"^(?P<category>.*?), (?P<genres>.*?), (?P<desc>.*?)$",
                     soup.find('meta',{'name':'description'})['content'])
        if m != None:
            self.story.setMetadata('description', m.group('desc'))
            genres=m.group('genres')
            # Hurt/Comfort is one genre.
            genres=re.sub('Hurt/Comfort','Hurt-Comfort',genres)
            for g in genres.split('/'):
                self.story.addToList('genre',g)

        # Number of words only on author page.
        # status, category, etc could also be parsed from here, but this way the one
        # off-page hit is isolated.
        logging.debug('Getting more metadata from: %s' % self.story.getMetadata('authorUrl'))
        soup = bs.BeautifulStoneSoup(self._fetchUrl(self.story.getMetadata('authorUrl')),
                                     selfClosingTags=('br')) # normalize <br> tags to <br />
        # Find the link for this story.
        a = soup.find('a', href=re.compile(r'^/s/'+self.story.getMetadata('storyId')+'/'))
        # Find the 'data line' after it.
        # Complete - Sci-Fi - Fiction Rated: T - English - Suspense/Hurt/Comfort - Chapters: 1 - Words: 2,762 - Reviews: 2 - Updated: 2-7-11 - Published: 2-7-11
        dataline = a.findNext(text=re.compile(r'Words: '))
        if dataline:
            m = re.match(r".*?Words: ([0-9,]+).*?",dataline)
            if m:
                words = m.group(1)
                self.story.setMetadata('numWords',words)
        
        return


    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        time.sleep(0.5) ## ffnet(and, I assume, fpcom) tends to fail
                        ## more if hit too fast.  This is in
                        ## additional to what ever the
                        ## slow_down_sleep_time setting is.
        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.

        div = soup.find('div', {'id' : 'storytext'})
        ## fp puts a padding style on the div that we don't want.
        del div['style']

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return utf8FromSoup(div)

def getClass():
    return FictionPressComSiteAdapter

