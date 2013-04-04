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
    return DarkSolaceOrgAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class DarkSolaceOrgAdapter(BaseSiteAdapter):

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
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/elysian/viewstory.php?sid='+self.story.getMetadata('storyId'))
        
        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','dksl')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"
            
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'dark-solace.org'
        
    @classmethod
    def getAcceptDomains(cls):
        return ['www.dark-solace.org','dark-solace.org']

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/elysian/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+"(www\.)?"+re.escape(self.getSiteDomain()+"/elysian/viewstory.php?sid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'This story contains adult content not suitable for children' in data \
                or "That password doesn't match the one in our database" in data \
                or "Registered Users Only" in data:
            return True
        else:
            return False
        
    def performLogin(self, url):
        params = {}

        if self.password:
            params['penname'] = self.username
            params['password'] = self.password
        else:
            params['penname'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['rememberme'] = '1'
        params['action'] = 'login'
        params['submit'] = 'Submit'
    
        loginUrl = 'http://' + self.getSiteDomain() + '/elysian/user.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['penname']))
    
        d = self._postUrl(loginUrl, params)
    
        if "Member Account" not in d : #User Account Page
            logger.info("Failed to login to URL %s as %s, or have no authorization to access the story" % (loginUrl, params['penname']))
            raise exceptions.FailedToLogin(url,params['penname'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        
        if self.is_adult or self.getConfig("is_adult"):
            # Weirdly, different sites use different warning numbers.
            # If the title search below fails, there's a good chance
            # you need a different number.  print data at that point
            # and see what the 'click here to continue' url says.
            addurl = "&ageconsent=ok&warning=5"
        else:
            addurl=""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+'&index=1'+addurl
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)
            
        m = re.search(r"'viewstory.php\?sid=\d+((?:&amp;ageconsent=ok)?&amp;warning=\d+)'",data)
        if m != None:
            if self.is_adult or self.getConfig("is_adult"):
                # We tried the default and still got a warning, so
                # let's pull the warning number from the 'continue'
                # link and reload data.
                addurl = m.group(1)
                # correct stupid &amp; error in url.
                addurl = addurl.replace("&amp;","&")
                url = self.url+'&index=1'+addurl
                logger.debug("URL 2nd try: "+url)

                try:
                    data = self._fetchUrl(url)
                except urllib2.HTTPError, e:
                    if e.code == 404:
                        raise exceptions.StoryDoesNotExist(self.url)
                    else:
                        raise e    
            else:
                raise exceptions.AdultCheckRequired(self.url)
            
        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
            
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.
        
        ## Title and author
        div = soup.find('div', {'id' : 'pagetitle'})
        
        aut = div.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/elysian/'+aut['href'])
        self.story.setMetadata('author',aut.string)
        aut.extract()

        # first a tag in pagetitle is title
        self.story.setMetadata('title',stripHTML(div.find('a')))

        # Find the chapters:
        # chapters=soup.find('select', {'name' : 'chapter'})
        # if chapters != None:
        #     for chapter in chapters.findAll('option'):
        #         self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/elysian/viewstory.php?sid='+self.story.getMetadata('storyId')+'&chapter='+chapter['value']))
        # else:
        #     self.chapterUrls.append((self.story.getMetadata('title'),url+"&chapter=1"))

        for chapa in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+
                                                       self.story.getMetadata('storyId')+'&chapter=\d+')):
            self.chapterUrls.append((stripHTML(chapa),'http://'+self.host+'/elysian/'+chapa['href']))
        
        self.story.setMetadata('numChapters',len(self.chapterUrls))
        
        asoup = bs.BeautifulSoup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        
        # for metalist in asoup.findAll('div', {'class' : re.compile('listbox\s+')}):
        #     a = metalist.find('a', href=re.compile(r'viewstory.php\?sid='))
        #     if a != None:
        #         if 'viewstory.php?sid='+self.story.getMetadata('storyId') in a['href']:
        #             break

        metalist = asoup.find('a', href=re.compile(r'viewstory.php\?sid='+
                                                   self.story.getMetadata('storyId')+'($|[^\d])')).parent.parent

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""
                

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = metalist.findAll('span', {'class' : 'label'})
        for labelspan in labels:
            label = labelspan.text
            value = labelspan.nextSibling

            if 'Summary' in label:
                ## Everything until the next span class='label'
                svalue = ""
                while not (defaultGetattr(value,'class') == 'label' or "Chapters: " in stripHTML(value)):
                    svalue += str(value)
                    value = value.nextSibling
                self.setDescription(url,svalue)
                #self.story.setMetadata('description',stripHTML(svalue))

            if 'Rated' in label:
                self.story.setMetadata('rating', value[:len(value)-2])

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'categories.php\?catid=\d+'))
                for cat in cats:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                for char in value.string.split(', '):
                    if not 'None' in char:
                        self.story.addToList('characters',char)

            if 'Genre' in label:
                for genre in value.string.split(', '):
                    if not 'None' in genre:
                        self.story.addToList('genre',genre)

            if 'Warnings' in label:
                for warning in value.string.split(', '):
                    if not 'None' in warning:
                        self.story.addToList('warnings',warning)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        try:
            # Find Series name from series URL.
            a = metalist.find('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/elysian/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
            # can't use ^viewstory...$ in case of higher rated stories with javascript href.
            storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+'))
            i=1
            for a in storyas:
                # skip 'report this' and 'TOC' links
                if 'contact.php' not in a['href'] and 'index' not in a['href']:
                    if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in a['href']:
                        self.setSeries(series_name, i)
                        self.story.setMetadata('seriesUrl',series_url)
                        break
                    i+=1
            
        except:
            # I find it hard to care if the series parsing fails
            pass
            
    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulSoup(self._fetchUrl(url))
        
        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,div)
