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

from base_adapter import BaseSiteAdapter, utf8FromSoup, makeDate

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

        # used below to get correct characters.
        metatext = a.findNext(text=re.compile(r' - Reviews:'))
        if metatext == None: # indicates there's no Reviews, look for id: instead.
            metatext = a.findNext(text=re.compile(r' - id:'))

        # after Rating, the same bit of text containing id:123456 contains
        # Complete--if completed.
        if 'Complete' in a.findNext(text=re.compile(r'id:'+self.story.getMetadata('storyId'))):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # Parse genre(s) from <meta name="description" content="..."
        # <meta name="description" content="A Transformers/Beast Wars  - Humor fanfiction with characters Prowl & Sideswipe. Story summary: Sideswipe is bored. Prowl appears to be so, too  or at least, Sideswipe thinks he looks bored . So Sideswipe entertains them. After all, what's more fun than a race? Song-fic.">
        # <meta name="description" content="Chapter 1 of a Transformers/Beast Wars  - Adventure/Friendship fanfiction with characters Bumblebee. TFA: What would you do if you was being abused all you life? Follow NightRunner as she goes through her spark breaking adventure of getting away from her father..">
        # (fp)<meta name="description" content="Chapter 1 of a Sci-Fi  - Adventure/Humor fiction. Felix Max was just your regular hyperactive kid until he accidently caused his own fathers death. Now he has meta-humans trying to hunt him down with a corrupt goverment to back them up. Oh, and did I mention he has no Powers yet?.">
        # <meta name="description" content="Chapter 1 of a Bleach  - Adventure/Angst fanfiction with characters Ichigo K. & Neliel T. O./Nel. Time travel with a twist. Time can be a real bi***. Ichigo finds that fact out when he accidentally goes back in time. Is this his second chance or is fate just screwing with him. Not a crack fic.IchixNelXHime.">
        # <meta name="description" content="Chapter 1 of a Harry Potter and Transformers  - Humor/Adventure crossover fanfiction  with characters: Harry P. & Ironhide. IT’s one thing to be tossed thru the Veil for something he didn’t do. It was quite another to wake in his animigus form in a world not his own. Harry just knew someone was laughing at him somewhere. Mech/Mech pairings inside..">
        m = re.match(r"^(?:Chapter \d+ of a|A) (?:.*?)  (?:- (?P<genres>.*?) )?(?:crossover )?(?:fan)?fiction(?P<chars>[ ]+with characters)?",
                     soup.find('meta',{'name':'description'})['content'])
        if m != None:
            genres=m.group('genres')
            if genres != None:
                # Hurt/Comfort is one genre.
                genres=re.sub('Hurt/Comfort','Hurt-Comfort',genres)
                for g in genres.split('/'):
                    self.story.addToList('genre',g)

            if m.group('chars') != None:

                # At this point we've proven that there's character(s)
                # We can't reliably parse characters out of meta name="description".
                # There's no way to tell that "with characters Ichigo K. & Neliel T. O./Nel. " ends at "Nel.", not "T."
                # But we can pull them from the reviewstext line, now that we know about existance of chars.
                # reviewstext can take form of:
                # - English -  Shinji H. - Updated: 01-13-12 - Published: 12-20-11 - id:7654123
                # - English - Adventure/Angst -  Ichigo K. & Neliel T. O./Nel - Reviews:
                # - English - Humor/Adventure -  Harry P. & Ironhide - Reviews:
                mc = re.match(r" - (?P<lang>[^ ]+ - )(?P<genres>[^ ]+ - )? (?P<chars>.+?) - (Reviews|Updated|Published)",
                              metatext)
                chars = mc.group("chars")
                for c in chars.split(' & '):
                    self.story.addToList('characters',c)
        m = re.match(r" - (?P<lang>[^ ]+)",metatext)
        if m.group('lang') != None:
            self.story.setMetadata('language',m.group('lang'))
                    
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
        else:
            logging.debug('share button div not found')
        
        div = soup.find('div', {'id' : 'storytext'})
        
        if None == div:
            logging.debug('div id=storytext not found.  data:%s'%data)
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return utf8FromSoup(div)

def getClass():
    return FanFictionNetSiteAdapter

