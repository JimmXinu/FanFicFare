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

from .. import BeautifulSoup as bs
from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

from base_adapter import BaseSiteAdapter,  makeDate

ffnetgenres=["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy", "Friendship", "General",
             "Horror", "Humor", "Hurt-Comfort", "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi",
             "Spiritual", "Supernatural", "Suspense", "Tragedy", "Western"]

class FanFictionNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','ffnet')
        
        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        # normalized story URL.
        self._setURL("http://"+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId')+"/1/")

        # ffnet update emails have the latest chapter URL.
        # Frequently, when they arrive, not all the servers have the
        # latest chapter yet and going back to chapter 1 to pull the
        # chapter list doesn't get the latest.  So save and use the
        # original URL given to pull chapter list & metadata.
        self.origurl = url
        if "http://m." in self.origurl:
            ## accept m(mobile)url, but use www.
            self.origurl = self.origurl.replace("http://m.","http://www.")

    @staticmethod
    def getSiteDomain():
        return 'www.fanfiction.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.fanfiction.net','m.fanfiction.net']

    def getSiteExampleURLs(self):
        return "http://www.fanfiction.net/s/1234/1/ http://www.fanfiction.net/s/1234/12/ http://www.fanfiction.net/s/1234/1/Story_Title"

    def getSiteURLPattern(self):
        return r"http://(www|m)?\.fanfiction\.net/s/\d+(/\d+)?(/|/[a-zA-Z0-9_-]+)?/?$"

    def extractChapterUrlsAndMetadata(self):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.origurl
        logging.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            #print("\n===================\n%s\n===================\n"%data)
            soup = bs.BeautifulSoup(data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e
            
        if "Unable to locate story with id of " in data:
            raise exceptions.StoryDoesNotExist(url)

        # some times "Chapter not found...", sometimes "Chapter text not found..."
        if "not found. Please check to see you are not using an outdated url." in data:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  'Chapter not found. Please check to see you are not using an outdated url.'" % url)

        try:
            # rather nasty way to check for a newer chapter.  ffnet has a
            # tendency to send out update notices in email before all
            # their servers are showing the update on the first chapter.
            try:
                chapcount = len(soup.find('select', { 'name' : 'chapter' } ).findAll('option'))
            # get chapter part of url.
            except:
                chapcount = 1
            chapter = url.split('/',)[5]
            tryurl = "http://%s/s/%s/%d/"%(self.getSiteDomain(),
                                           self.story.getMetadata('storyId'),
                                           chapcount+1)
            print('=Trying newer chapter: %s' % tryurl)
            newdata = self._fetchUrl(tryurl)
            if "not found. Please check to see you are not using an outdated url." \
                    not in newdata:
                print('=======Found newer chapter: %s' % tryurl)
                soup = bs.BeautifulSoup(newdata)
        except:
            pass
        
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
                    m = re.match(r"^ +var ([^ ]+) = '?(.*?)'?;\r?$",line)
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
                        self.setDescription(url,value)
                        #self.story.setMetadata('description', value)
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
        rating = a.string
        if 'Fiction' in rating: # if rating has 'Fiction ', strip that out for consistency with past.
            rating = rating[8:]
            
        self.story.setMetadata('rating',rating)

        # after Rating, the same bit of text containing id:123456 contains
        # Complete--if completed.
        gui_table1i = soup.find(id="gui_table1i")
        metatext = stripHTML(gui_table1i.find('div', {'style':'color:gray;'})).replace('Hurt/Comfort','Hurt-Comfort')
        metalist = metatext.split(" - ")
        #print("metatext:(%s)"%metalist)

        # rating is obtained above more robustly.
        if metalist[0].startswith('Rated:'):
            metalist=metalist[1:]

        # next is assumed to be language.
        self.story.setMetadata('language',metalist[0])
        metalist=metalist[1:]

        # next might be genre.
        genrelist = metalist[0].split('/') # Hurt/Comfort already changed above.
        goodgenres=True
        for g in genrelist:
            if g not in ffnetgenres:
                goodgenres=False
        if goodgenres:
            self.story.extendList('genre',genrelist)
            metalist=metalist[1:]

        # next might be characters, otherwise Reviews, Updated or Published
        if not ( metalist[0].startswith('Reviews') or metalist[0].startswith('Updated') or metalist[0].startswith('Published') ):
            self.story.extendList('characters',metalist[0].split(' & '))        
        
        if 'Status: Complete' in metatext:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        img = soup.find('img',{'class':'cimage'})
        if img:
            self.story.addImgUrl(self,url,img['src'],self._fetchUrlRaw,cover=True)
            
        return

    def getChapterText(self, url):
        logging.debug('Getting chapter text from: %s' % url)
        time.sleep(0.5) ## ffnet(and, I assume, fpcom) tends to fail
                        ## more if hit too fast.  This is in
                        ## additional to what ever the
                        ## slow_down_sleep_time setting is.
        data = self._fetchUrl(url)
        soup = bs.BeautifulSoup(data)

        ## Remove the 'share' button.
        sharediv = soup.find('div', {'class' : 'a2a_kit a2a_default_style'})
        if sharediv:
            sharediv.extract()
        
        div = soup.find('div', {'id' : 'storytextp'})
        
        if None == div:
            logging.debug('div id=storytextp not found.  data:%s'%data)
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return FanFictionNetSiteAdapter

