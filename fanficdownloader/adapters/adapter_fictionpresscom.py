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

    def getSiteExampleURLs(self):
        return "http://www.fictionpress.com/s/1234/1/ http://www.fictionpress.com/s/1234/12/ http://www.fictionpress.com/s/1234/1/Story_Title"

    def getSiteURLPattern(self):
        return r"http://www\.fictionpress\.com/s/\d+(/\d+)?(/|/[a-zA-Z0-9_-]+)?/?$"

    def extractChapterUrlsAndMetadata(self):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.url
        logging.debug("URL: "+url)
        
        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e
            
        if "Unable to locate story with id of " in data:
            raise exceptions.StoryDoesNotExist(self.url)
            
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"^/u/\d+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

            
        # start by finding a script towards the bottom that has a
        # bunch of useful stuff in it.
            
        # var storyid = 6577076;
        # var chapter = 1;
        # var chapters = 17;
        # var words = 42787;
        # var userid = 2645830;
        # var title = 'The+Invitation';
        # var title_t = 'The Invitation';
        # var summary = 'Dudley Dursley would be the first to say he lived a very normal life. But what happens when he gets invited to his cousin Harry Potter\'s wedding? Will Dudley get the courage to apologize for the torture he caused all those years ago? Harry/Ginny story.';
        # var categoryid = 224;
        # var cat_title = 'Harry Potter';
        # var datep = '12-21-10';
        # var dateu = '04-06-11';
        # var author = 'U n F a b u l o u s M e';

        for script in soup.findAll('script', src=None):
            if not script:
                continue
            if not script.string:
                continue
            if 'var storyid' in script.string:
                for line in script.string.split('\n'):
                    m = re.match(r"^ +var ([^ ]+) = '?(.*?)'?;$",line)
                    if m == None : continue
                    var,value = m.groups()
                    # remove javascript escaping from values.
                    value = re.sub(r'\\(.)',r'\1',value)
                    #print var,value
                    if 'words' in var:
                        self.story.setMetadata('numWords', value)
                    if 'title_t' in var:
                        self.story.setMetadata('title', value)
                    if 'summary' in var:
                        self.story.setMetadata('description', value)
                    if 'datep' in var:
                        self.story.setMetadata('datePublished',makeDate(value, '%m-%d-%y'))
                    if 'dateu' in var:
                        self.story.setMetadata('dateUpdated',makeDate(value, '%m-%d-%y'))
                    if 'cat_title' in var:
                        if "Crossover" in value:
                            value = re.sub(r' Crossover$','',value)
                            for c in value.split(' and '):
                                self.story.addToList('category',c)
                                # Screws up when the category itself
                                # contains ' and '.  But that's rare
                                # and the only alternative is to find
                                # the 'Crossover' category URL and
                                # parse that page to search for <a>
                                # with href /crossovers/(name)/(num)/
				# <a href="/crossovers/Harry_Potter/224/">Harry Potter</a>
				# <a href="/crossovers/Naruto/1402/">Naruto</a>
                        else:
                            self.story.addToList('category',value)
                break # for script in soup.findAll('script', src=None):
            
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

        ## Pull some additional data from html.  Find Rating and look around it.

        a = soup.find('a', href='http://www.fictionratings.com/')
        self.story.setMetadata('rating',a.string)

        # after Rating, the same bit of text containing id:123456 contains
        # Complete--if completed.
        if 'Complete' in a.findNext(text=re.compile(r'id:'+self.story.getMetadata('storyId'))):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # Parse genre(s) from <meta name="description" content="..."
        # <meta name="description" content="Chapter 1 of a Harry Potter  - Family/Friendship fanfiction. Dudley Dursley would be the first to say he lived a very normal life. But what happens when he gets invited to his cousin Harry Potter's wedding? Will Dudley get the courage to apologize for the torture he caused all those years ago? Harry/Ginny story..">
        # <meta name="description" content="A Gundam Wing/AC and Gundam Seed  - Romance/Sci-Fi crossover fanfiction  with characters:  & Kira Y.. Story summary: One-Shoot dividido en dos partes. Kira va en camino a rescatar a Lacus, pero él no es el unico. Dos personajes de diferentes universos Gundams. SEED vs ZERO.">
        # <meta name="description" content="Chapter 1 of a Alvin and the chipmunks and Alpha and Omega  crossover fanfiction  with characters: Alvin S. & Humphrey. You'll just have to read to find out... No Flames Plesae... and tell me what you want to see by PM'ing me....">
        # genre is after first -, but before first 'fanfiction'.
        m = re.match(r"^(?:Chapter \d+ of a|A) (?:.*?)  (?:- (?P<genres>.*?)) (?:crossover )?fanfiction",
                     soup.find('meta',{'name':'description'})['content'])
        if m != None:
            genres=m.group('genres')
            # Hurt/Comfort is one genre.
            genres=re.sub('Hurt/Comfort','Hurt-Comfort',genres)
            for g in genres.split('/'):
                self.story.addToList('genre',g)
        
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

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return utf8FromSoup(div)

def getClass():
    return FictionPressComSiteAdapter

