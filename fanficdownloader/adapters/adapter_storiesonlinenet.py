# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
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
    return StoriesOnlineNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class StoriesOnlineNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2].split(':')[0])
        if 'storyInfo' in self.story.getMetadata('storyId'):
            self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/s/'+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','strol')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'storiesonline.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/s/1234 http://"+cls.getSiteDomain()+"/s/1234:4010"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r"/s/\d+((:\d+)?(;\d+)?$|(:i)?$)?"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if self.needToLogin \
                or 'Free Registration' in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data \
                or "Log In" in data \
                or "Access to unlinked chapters requires" in data:
            self.needToLogin = True
        return self.needToLogin
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['theusername'] = self.username
            params['thepassword'] = self.password
        else:
            params['theusername'] = self.getConfig("username")
            params['thepassword'] = self.getConfig("password")
        params['rememberMe'] = '1'
        params['page'] = 'http://'+self.getSiteDomain()+'/'
        params['submit'] = 'Login'
    
        loginUrl = 'http://' + self.getSiteDomain() + '/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['theusername']))
    
        d = self._fetchUrl(loginUrl, params,usecache=False)
    
        if "My Account" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['theusername']))
            raise exceptions.FailedToLogin(url,params['theusername'])
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

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        self.needToLogin = False
        try:
            data = self._fetchUrl(url+":i")
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            elif e.code == 401:
                self.needToLogin = True
                data = ''
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url+":i",usecache=False)
        
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        elif "Error! The story you're trying to access is being filtered by your choice of contents filtering." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Error! The story you're trying to access is being filtered by your choice of contents filtering.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        #print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a))
        
        notice = soup.find('div', {'class' : 'notice'})
        if notice:
            self.story.setMetadata('notice',unicode(notice))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"/a/\w+"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',stripHTML(a).replace("'s Page",""))

        # Find the chapters:
        chapters = soup.findAll('a', href=re.compile(r'^/s/'+self.story.getMetadata('storyId')+":\d+$"))
        if len(chapters) != 0:
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['href']))
        else:
            self.chapterUrls.append((self.story.getMetadata('title'),'http://'+self.host+'/s/'+self.story.getMetadata('storyId')))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # surprisingly, the detailed page does not give enough details, so go to author's page
        page=0
        i=0
        while i == 0:
            asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')+"/"+str(page)))

            a = asoup.findAll('td', {'class' : 'lc2'})
            for lc2 in a:
                if lc2.find('a', href=re.compile(r'^/s/'+self.story.getMetadata('storyId'))):
                    i=1
                    break
                if a[len(a)-1] == lc2:
                    page=page+1

        for cat in lc2.findAll('div', {'class' : 'typediv'}):
            self.story.addToList('genre',cat.text)

        # in lieu of word count.
        self.story.setMetadata('size', lc2.findNext('td', {'class' : 'num'}).text)
        
        lc4 = lc2.findNext('td', {'class' : 'lc4'})
        desc = lc4.contents[0]

        try:
            a = lc4.find('a', href=re.compile(r"/series/\d+/.*"))
            if a:
                # if there's a number after the series name, series_contents is a two element list:
                # [<a href="...">Title</a>, u' (2)']
                series_contents = a.parent.contents
                i = 0 if len(series_contents) == 1 else series_contents[1].strip(' ()')
                seriesUrl = 'http://'+self.host+a['href']
                self.story.setMetadata('seriesUrl',seriesUrl)
                series_name = stripHTML(a)
                logger.debug("Series name= %s" % series_name)
                series_soup = bs.BeautifulSoup(self._fetchUrl(seriesUrl))
                if series_soup:
                    logger.debug("Retrieving Series - looking for name")
                    series_name = series_soup.find('span', {'id' : 'ptitle'}).text.partition(' — ')[0]
                    logger.debug("Series name: '{0}'".format(series_name))
                self.setSeries(series_name, i)
                desc = lc4.contents[2]
                # Check if series is in a universe
                universe_url = self.story.getMetadata('authorUrl')  + "&type=uni"
                universes_soup = bs.BeautifulSoup(self._fetchUrl(universe_url) )
                logger.debug("Universe url='{0}'".format(universe_url))
                if universes_soup:
                    universes = universes_soup.findAll('div', {'class' : 'ser-box'})
                    logger.debug("Number of Universes: %d" % len(universes))
                    for universe in universes:
                        logger.debug("universe.find('a')={0}".format(universe.find('a')))
                        # The universe id is in an "a" tag that has an id but nothing else. It is the first tag.
                        # The id is prefixed with the letter "u".
                        universe_id = universe.find('a')['id'][1:]
                        logger.debug("universe_id='%s'" % universe_id)
                        universe_name = universe.find('div', {'class' : 'ser-name'}).text.partition(' ')[2]
                        logger.debug("universe_name='%s'" % universe_name)
                        # If there is link to the story, we have the right universe
                        story_a = universe.find('a', href=re.compile('/s/'+self.story.getMetadata('storyId')))
                        if story_a:
                            logger.debug("Story is in a series that is in a universe! The universe is '%s'" % universe_name)
                            self.story.setMetadata("universe", universe_name)
                            self.story.setMetadata('universeUrl','http://'+self.host+ '/library/universe.php?id=' + universe_id)
                            break
                else:
                    logger.debug("No universe page")
        except:
            pass
        try:
            a = lc4.find('a', href=re.compile(r"/universe/\d+/.*"))
            logger.debug("Looking for universe - a='{0}'".format(a))
            if a:
                self.story.setMetadata("universe",stripHTML(a))
                desc = lc4.contents[2]
                # Assumed only one universe, but it does have a URL--use universeHTML
                universe_name = stripHTML(a)
                universeUrl = 'http://'+self.host+a['href']
                logger.debug("Retrieving Universe - about to get page - universeUrl='{0}".format(universeUrl))
                universe_soup = bs.BeautifulSoup(self._fetchUrl(universeUrl))
                logger.debug("Retrieving Universe - have page")
                if universe_soup:
                    logger.debug("Retrieving Universe - looking for name")
                    universe_name = universe_soup.find('h1', {'id' : 'ptitle'}).text.partition(' &mdash;')[0]
                    logger.debug("Universes name: '{0}'".format(universe_name))

                self.story.setMetadata('universeUrl',universeUrl)
                logger.debug("Setting universe name: '{0}'".format(universe_name))
                self.story.setMetadata('universe',universe_name)
                if self.getConfig("universe_as_series"):
                    self.setSeries(universe_name, 0)
                    self.story.setMetadata('seriesUrl',universeUrl)
            else:
                logger.debug("Do not have a universe")
        except:
            pass

        self.setDescription('http://'+self.host+'/s/'+self.story.getMetadata('storyId'),desc)
            
        for b in lc4.findAll('b'):
            #logger.debug('Getting metadata: "%s"' % b)
            label = b.text
            if label in ['Posted:', 'Concluded:', 'Updated:']:
                value = b.findNext('noscript').text
                #logger.debug('Have a date field label: "%s", value: "%s"' % (label, value))
            else:
                value = b.nextSibling
            #logger.debug('label: "%s", value: "%s"' % (label, value))
            
            if 'Sex' in label:
                self.story.setMetadata('rating', value)
                
            if 'Tags' in label:
                for code in re.split(r'\s*,\s*', value.strip()):
                     self.story.addToList('sitetags',code)
                    
            if 'Posted' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
            if 'Concluded' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
#                
        status = lc4.find('span', {'class' : 'ab'})
        if  status != None:
            self.story.setMetadata('status', 'In-Progress')
            if "Last Activity" in status.text:
                # date is passed as a timestamp and converted in JS.
                value = status.findNext('noscript').text
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
        else:
            self.story.setMetadata('status', 'Completed')

            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        div = soup.find('div', {'id' : 'story'})
        
        # some big chapters are split over several pages
        pager = div.find('span', {'class' : 'pager'})
        if pager != None:
            a = pager.previousSibling
            while a != None:
                logger.debug("before pager: {0}".format(a))
                b = a.previousSibling
                a.extract()
                a = b

            urls=pager.findAll('a')
            urls=urls[:len(urls)-1]
            pager.extract()
            div.contents = div.contents[2:]
#            logger.debug(div)
                        
            for ur in urls:
                soup = bs.BeautifulSoup(self._fetchUrl("http://"+self.getSiteDomain()+ur['href']),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
                div1 = soup.find('div', {'id' : 'story'})
                
                # Find the "Continues" marker on the current page and remove everything after that. 
                continues = div.find('span', {'class' : 'conTag'})
                if continues != None:
                    while continues != None:
#                        logger.debug("removing end: {0}".format(continues))
                        b = continues.nextSibling
                        continues.extract()
                        continues = b

                # Find the "Continued" marker and delete everything before that
                continued = div1.find('span', {'class' : 'conTag'})
                if continued != None:
                    a = continued.previousSibling
                    while a != None:
#                        logger.debug("before conTag: {0}".format(a))
                        b = a.previousSibling
                        a.extract()
                        a = b
                # Remove the pager from the end if this is the last page
                endPager = div1.find('span', {'class' : 'pager'})
                if endPager != None:
                    b = endPager.nextSibling
                    while endPager != None:
                        logger.debug("removing end: {0}".format(endPager))
                        b = endPager.nextSibling
                        endPager.extract()
                        endPager = b
                    div1.contents = div1.contents[:len(div1) - 2]
#                logger.debug("after removing pager: {0}".format(div1))
                for tag in div1.contents[2:]:
                    div.append(tag)

        # If it is a chapter, there are dates at the start for when it was posted or modified. These plus 
        # everything before them can be discarded. 
        postedDates = div.findAll('div', {'class' : 'date'})
        if postedDates:
            a = postedDates[0].previousSibling
            while a != None:
#                logger.debug("before dates: {0}".format(a))
                b = a.previousSibling
                a.extract()
                a = b
            for a in div.findAll('div', {'class' : 'date'}):
                a.extract()

        # For single chapter stories, there is a copyright statement. Remove this and everything
        # before it.
        copy = div.find('h4', {'class': 'copy'})
        while copy != None:
#            logger.debug("before copyright: {0}".format(copy))
            b = copy.previousSibling
            copy.extract()
            copy = b

        # For a story or the last chapter, remove voting form and the in library box
        a = div.find('div', {'id' : 'vote-form'})
        if a != None:
            a.extract()
        a = div.find('div', {'id' : 'b-man-div'})
        if a != None:
            a.extract()

        # Kill the "The End" header and everything after it.
        a = div.find(['h2', 'h3'], {'class' : 'end'})
        logger.debug("Chapter end= '{0}'".format(a))
        while a != None:
            b = a.nextSibling
            a.extract()
            a=b


        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
