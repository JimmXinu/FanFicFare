# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2015 FanFicFare team
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

# Software: eFiction
import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import sys

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return HPFanficArchiveComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class HPFanficArchiveComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["Windows-1252",
                       "utf8", "iso-8859-1"] 
                               # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ficsite')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.ficsite.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if 'Registered Users Only' in data \
                or 'There is no such account on our website' in data \
                or "That password doesn't match the one in our database" in data:
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
        params['cookiecheck'] = '1'
        params['submit'] = 'Submit'

        loginUrl = 'http://' + self.getSiteDomain() + '/user.php?action=login'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['penname']))

        d = self._fetchUrl(loginUrl, params)

        if "Member Account" not in d : #Member Account
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['penname']))
            raise exceptions.FailedToLogin(url,params['penname'])
            return False
        else:
            return True
    
    # I've added this because there are several warnings
    # that are used by this site.
    def getWarning(self, data):
        if "This story contains adult subject matter that may include coarse language, violence, and mild sexual content of a graphical nature. Reader discretion is requested. Thank you." in data:
            return '&ageconsent=ok&warning=5'
        elif "This story contains graphical material of an adult nature and a same sex primary relationship. Please do not read if this is not to your taste. Thank you." in data:
            return '&warning=7'
        elif "This story contains graphical material of an adult nature. Reader discretion is requested. Thank you." in data:
            return '&warning=6'
        else:
            return False
        
    
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if (self.is_adult or self.getConfig("is_adult")):
            addurl = '&index=1&ageconsent=ok&warning=5'
        else:
            addurl='&index=1'

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+addurl
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
        
        warning = self.getWarning(data)
        if warning != False:
            data = self._fetchUrl(url+warning)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        elif "This story contains adult subject matter that may include coarse language, violence, and mild sexual content of a graphical nature. Reader discretion is requested. Thank you." in data:
            raise exceptions.AccessDenied(self.getSiteDomain()+" says: This story contains adult subject matter that may include coarse language, violence, and mild sexual content of a graphical nature. Reader discretion is requested. Thank you.")
        elif "This story contains graphical material of an adult nature and a same sex primary relationship. Please do not read if this is not to your taste. Thank you." in data:
            raise exceptions.AccessDenied(self.getSiteDomain()+" says: This story contains graphical material of an adult nature and a same sex primary relationship. Please do not read if this is not to your taste. Thank you.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title and Author Div
        div = soup.find('div',{'id':'pagetitle'})
        ## Title
        a = div.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = div.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))
        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            val = labelspan.nextSibling
            value = unicode('')
            while val and not 'label' in defaultGetattr(val,'class'):
                # print("val:%s"%val)
                if not isinstance(val,Comment):
                    value += unicode(val)
                val = val.nextSibling
            label = labelspan.string
            # print("label:%s\nvalue:%s"%(label,value))

            if 'Summary' in label:
                self.setDescription(url,value)

            if 'Rated' in label:
                self.story.setMetadata('rating', stripHTML(value))

            if 'Word count' in label:
                self.story.setMetadata('numWords', stripHTML(value))

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                for cat in cats:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                for char in chars:
                    self.story.addToList('characters',char.string)

            if 'Genre' in label:
                genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1')) # XXX
                for genre in genres:
                    self.story.addToList('genre',genre.string)

            if 'Pairing' in label:
                ships = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=4'))
                for ship in ships:
                    self.story.addToList('ships',ship.string)

            if 'Warnings' in label:
                warnings = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2')) # XXX
                for warning in warnings:
                    self.story.addToList('warnings',warning.string)

            if 'Completed' in label:
                if 'Yes' in stripHTML(value):
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))

            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = self.make_soup(self._fetchUrl(series_url))
            # can't use ^viewstory...$ in case of higher rated stories with javascript href.
            storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+'))
            i=1
            for a in storyas:
                # skip 'report this' and 'TOC' links
                if 'contact.php' not in a['href'] and 'index' not in a['href']:
                    if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
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

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
