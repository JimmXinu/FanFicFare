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
import urlparse
import time

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

class LiteroticaSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        
        self.story.setMetadata('siteabbrev','litero')

        # normalize to first chapter.  Not sure if they ever have more than 2 digits.
        storyid = self.parsedUrl.path.split('/',)[2]
        if re.match(r'-ch\d\d$',storyid):
            storyid = storyid[:-2]+'01'
        self.story.setMetadata('storyId',storyid)
        
        self.origurl = url
        if "//www.i." in self.origurl:
            ## accept m(mobile)url, but use www.
            self.origurl = self.origurl.replace("//www.i.","//www.")

        # normalized story URL.
        self._setURL(url[:url.index('//')+2]+self.getSiteDomain()\
                         +"/s/"+self.story.getMetadata('storyId'))

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = '%m/%d/%y'
        
    @staticmethod
    def getSiteDomain():
        return 'www.literotica.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.literotica.com', 'www.i.literotica.com']

    @classmethod
    def getSiteExampleURLs(self):
        #return "http://www.literotica.com/s/story-title http://www.literotica.com/stories/showstory.php?id=1234 http://www.i.literotica.com/stories/showstory.php?id=1234"
        return "http://www.literotica.com/s/story-title https://www.literotica.com/s/story-title"

    def getSiteURLPattern(self):
        return r"https?://www(\.i)?\.literotica\.com/s/([a-zA-Z0-9_-]+)"

    def extractChapterUrlsAndMetadata(self):

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)
        
        url1 = self.origurl
        logger.debug("first page URL: "+url1)

        try:
            data1 = self._fetchUrl(url1)
            soup1 = bs.BeautifulSoup(data1)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url1)
            else:
                raise e

        #strip comments from soup
        [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # author
        a = soup1.find("span", "b-story-user-y")
        self.story.setMetadata('authorId', urlparse.parse_qs(a.a['href'].split('?')[1])['uid'][0])
        authorurl = a.a['href']
        if authorurl.startswith('//'):
            authorurl = self.parsedUrl.scheme+':'+authorurl
        self.story.setMetadata('authorUrl', authorurl)
        self.story.setMetadata('author', a.text)

        # get the author page
        try:
            dataAuth = self._fetchUrl(authorurl)
            soupAuth = bs.BeautifulSoup(dataAuth)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(authorurl)
            else:
                raise e

        ## site has started using //domain.name/asdf urls remove https?: from front
        storyLink = soupAuth.find('a', href=url1[url1.index(':')+1:])

        if storyLink is not None:
            # pull the published date from the author page
            # default values from single link.  Updated below if multiple chapter.
            date = storyLink.parent.parent.findAll('td')[-1].text
            self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
            self.story.setMetadata('dateUpdated',makeDate(date, self.dateformat))

        # find num of pages
        # find a "3 Pages:" string on the page and parse it
        pgs = soup1.find("span", "b-pager-caption-t r-d45").string.split(' ')[0]

        # If there are multiple pages, find and request the last page
        if "1" != pgs:
            logger.debug("last page number: "+pgs)
            try:
                data2 = self._fetchUrl(url1, {'page': pgs})
                soup2 = bs.BeautifulSoup(data2)
                [comment.extract() for comment in soup2.findAll(text=lambda text:isinstance(text, bs.Comment))]
            except urllib2.HTTPError, e:
                if e.code == 404:
                    # TODO: Probably should reformat this
                    raise exceptions.StoryDoesNotExist(url1, {'page': pgs})
                else:
                    raise e
        else:
            #If we're already on the last page, copy the soup
            soup2 = soup1

        # parse out the list of chapters
        chaps = soup2.find('div', id='b-series')
        if chaps:  # may be one post only
            #self.chapterUrls = [(ch.a.text, ch.a['href']) for ch in chaps.findAll('li')]

            # if there are chapters, lets pull them and title from the
            # author page because *this* chapter is omitted from the
            # list on the last page.
            row = storyLink.parent.parent.previousSibling
            while row['class'] != 'ser-ttl':
                row = row.previousSibling

            seriesTitle = stripHTML(row)
            if seriesTitle:
                # this regex is deliberately greedy. We want to get the biggest match before a ':'
                self.story.setMetadata('title', re.match('(.*):[^:]*$', seriesTitle).group(1))
            else:
                self.story.setMetadata('title', soup1.h1.string)

            # now chapter list.  Assumed oldest to newest.
            self.chapterUrls = []
            row = row.nextSibling
                
            self.story.setMetadata('datePublished',makeDate(stripHTML(row.find('td',{'class':'dt'})), self.dateformat))
            while row['class'] == 'sl':
                # pages include full URLs.
                chapurl = row.a['href']
                if chapurl.startswith('//'):
                    chapurl = self.parsedUrl.scheme+':'+chapurl
                self.chapterUrls.append((row.a.string,chapurl))
                if not row.nextSibling:
                    break
                row = row.nextSibling

            row = row.previousSibling
            self.story.setMetadata('dateUpdated',makeDate(stripHTML(row.find('td',{'class':'dt'})), self.dateformat))
                
        else:  # if one post only
            self.chapterUrls = [(soup1.h1.string, url1)]
            self.story.setMetadata('title', soup1.h1.string)

        # normalize on first chapter URL.
        self._setURL(self.chapterUrls[0][1])

        # reset storyId to first chapter.
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])

        self.story.setMetadata('numChapters', len(self.chapterUrls))

        self.story.setMetadata('category', soup1.find('div', 'b-breadcrumbs').findAll('a')[1].string)
        self.story.setMetadata('description', soup1.find('meta', {'name': 'description'})['content'])
        
        # li tags inside div class b-s-story-tag-list
        for li in soup1.find('div', {'class':'b-s-story-tag-list'}).findAll('a'):
            self.story.addToList('eroticatags',stripHTML(li))

        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        time.sleep(0.5)
        data1 = self._fetchUrl(url)
        soup1 = bs.BeautifulSoup(data1)

        #strip comments from soup
        [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # get story text
        story1 = soup1.find('div', 'b-story-body-x').p
        story1.name='div'
        story1.append('<br />')
        storytext = self.utf8FromSoup(url,story1)

        # find num pages
        pgs = int(soup1.find("span", "b-pager-caption-t r-d45").string.split(' ')[0])
        logger.debug("pages: "+str(pgs))

        # get all the pages
        for i in xrange(2, pgs+1):
            try:
                logger.debug("fetching page "+str(i))
                time.sleep(0.5)
                data2 = self._fetchUrl(url, {'page': i})
                soup2 = bs.BeautifulSoup(data2)
                [comment.extract() for comment in soup2.findAll(text=lambda text:isinstance(text, bs.Comment))]
                story2 = soup2.find('div', 'b-story-body-x').p
                story2.name='div'
                story2.append('<br />')
                storytext += self.utf8FromSoup(url,story2)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(url)
                else:
                    raise e
        return storytext


def getClass():
    return LiteroticaSiteAdapter



