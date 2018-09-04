# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class FicwadComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fw')

        # get storyId from url--url validation guarantees second part is storyId
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        self.username = "NoneGiven"
        self.password = ""

    @staticmethod
    def getSiteDomain():
        return 'ficwad.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://ficwad.com/story/1234"

    def getSiteURLPattern(self):
        return r"https?:"+re.escape(r"//"+self.getSiteDomain())+"/story/\d+?$"

    def performLogin(self,url):
        params = {}

        if self.password:
            params['username'] = self.username
            params['password'] = self.password
        else:
            params['username'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/account/login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['username']))
        d = self._postUrl(loginUrl,params,usecache=False)

        if "Login attempt failed..." in d:
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['username']))
            raise exceptions.FailedToLogin(url,params['username'])
            return False
        else:
            return True

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):

        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url = self.url
        logger.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            data = self._fetchUrl(url)
            # non-existent/removed story urls get thrown to the front page.
            if "<h4>Featured Story</h4>" in data:
                raise exceptions.StoryDoesNotExist(self.url)
            soup = self.make_soup(data)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # if blocked, attempt login.
        if soup.find("div",{"class":"blocked"}) or soup.find("li",{"class":"blocked"}):
            if self.performLogin(url): # performLogin raises
                                       # FailedToLogin if it fails.
                soup = self.make_soup(self._fetchUrl(url,usecache=False))

        divstory = soup.find('div',id='story')
        storya = divstory.find('a',href=re.compile("^/story/\d+$"))
        if storya : # if there's a story link in the divstory header, this is a chapter page.
            # normalize story URL on chapter list.
            self.story.setMetadata('storyId',storya['href'].split('/',)[2])
            url = "https://"+self.getSiteDomain()+storya['href']
            logger.debug("Normalizing to URL: "+url)
            self._setURL(url)
            try:
                soup = self.make_soup(self._fetchUrl(url))
            except HTTPError as e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(self.url)
                else:
                    raise e

        # if blocked, attempt login.
        if soup.find("div",{"class":"blocked"}) or soup.find("li",{"class":"blocked"}):
            if self.performLogin(url): # performLogin raises
                                       # FailedToLogin if it fails.
                soup = self.make_soup(self._fetchUrl(url,usecache=False))

        # title - first h4 tag will be title.
        titleh4 = soup.find('div',{'class':'storylist'}).find('h4')
        self.story.setMetadata('title', stripHTML(titleh4.a))

        if 'Deleted story' in self.story.getMetadata('title'):
            raise exceptions.StoryDoesNotExist("This story was deleted. %s"%self.url)
        
        # Find authorid and URL from... author url.
        a = soup.find('span',{'class':'author'}).find('a', href=re.compile(r"^/a/"))
        self.story.setMetadata('authorId',a['href'].split('/')[2])
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # description
        storydiv = soup.find("div",{"id":"story"})
        self.setDescription(url,storydiv.find("blockquote",{'class':'summary'}).p)
        #self.story.setMetadata('description', storydiv.find("blockquote",{'class':'summary'}).p.string)

        # most of the meta data is here:
        metap = storydiv.find("p",{"class":"meta"})
        self.story.addToList('category',metap.find("a",href=re.compile(r"^/category/\d+")).string)

        # warnings
        # <span class="req"><a href="/help/38" title="Medium Spoilers">[!!] </a> <a href="/help/38" title="Rape/Sexual Violence">[R] </a> <a href="/help/38" title="Violence">[V] </a> <a href="/help/38" title="Child/Underage Sex">[Y] </a></span>
        spanreq = metap.find("span",{"class":"story-warnings"})
        if spanreq: # can be no warnings.
            for a in spanreq.findAll("a"):
                self.story.addToList('warnings',a['title'])

        ## perhaps not the most efficient way to parse this, using
        ## regexps for each rather than something more complex, but
        ## IMO, it's more readable and amenable to change.
        metastr = stripHTML(unicode(metap)).replace('\n',' ').replace('\t',' ').replace(u'\u00a0',' ')

        m = re.match(r".*?Rating: (.+?) -.*?",metastr)
        if m:
            self.story.setMetadata('rating', m.group(1))

        ## Genre appears even if list is empty.  But there are a
        ## limited number of genres allowed by the site.
        m = re.match(r".*?Genres: ((?:(?:Angst|Crossover|Drama|Erotica|Fantasy|Horror|Humor|Parody|Romance|Sci-fi)(?:,)?)+) -.*?",metastr)
        if m:
            for g in m.group(1).split(','):
                self.story.addToList('genre',g)

        m = re.match(r".*?Characters: (.*?) -.*?",metastr)
        if m:
            for g in m.group(1).split(','):
                if g:
                    self.story.addToList('characters',g)

        m = re.match(r".*?Published: ([0-9-]+?) -.*?",metastr)
        if m:
            self.story.setMetadata('datePublished',makeDate(m.group(1), "%Y-%m-%d"))

        # Updated can have more than one space after it. <shrug>
        m = re.match(r".*?Updated: ([0-9-]+?) +-.*?",metastr)
        if m:
            self.story.setMetadata('dateUpdated',makeDate(m.group(1), "%Y-%m-%d"))

        m = re.match(r".*? - ([0-9,]+?) words.*?",metastr)
        if m:
            self.story.setMetadata('numWords',m.group(1))

        if metastr.endswith("Complete"):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        # get the chapter list first this time because that's how we
        # detect the need to login.
        storylistul = soup.find('ul',{'class':'storylist'})
        if not storylistul:
            # no list found, so it's a one-chapter story.
            self.add_chapter(self.story.getMetadata('title'),url)
        else:
            chapterlistlis = storylistul.findAll('li')
            for chapterli in chapterlistlis:
                if "blocked" in chapterli['class']:
                    # paranoia check.  We should already be logged in by now.
                    raise exceptions.FailedToLogin(url,self.username)
                else:
                    #print "chapterli.h4.a (%s)"%chapterli.h4.a
                    self.add_chapter(chapterli.h4.a.string,
                                     u'https://%s%s'%(self.getSiteDomain(),
                                                      chapterli.h4.a['href']))
        return


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = self.make_soup(self._fetchUrl(url))

        span = soup.find('div', {'id' : 'storytext'})

        if None == span:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,span)

def getClass():
    return FicwadComSiteAdapter

