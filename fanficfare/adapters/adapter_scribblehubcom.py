# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2018 FanFicFare team
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
from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError
from ..six.moves.urllib.request import (build_opener, HTTPCookieProcessor, Request)
from ..six.moves.urllib.parse import urlencode, quote_plus
from ..six.moves import http_cookiejar as cl
from ..six import ensure_binary, ensure_text

from ..gziphttp import GZipProcessor

from ..configurable import Configuration



from .base_adapter import BaseSiteAdapter,  makeDate

# Need requests to curl the table of contents

# In general an 'adapter' needs to do these five things:

# - 'Register' correctly with the downloader
# - Site Login (if needed)
# - 'Are you adult?' check (if needed--some do one, some the other, some both)
# - Grab the chapter list
# - Grab the story meta-data (some (non-eFiction) adapters have to get it from the author page)
# - Grab the chapter texts

# Search for XXX comments--that's where things are most likely to need changing.

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return ScribbleHubComAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ScribbleHubComAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--sid is always 4th element in scribblehub url
        self.story.setMetadata('storyId', url.split("/")[4])

        # normalized story URL.
        # XXX Most sites don't have the /fanfic part.  Replace all to remove it usually.
        self._setURL('https://' + self.getSiteDomain() + '/series/' + self.story.getMetadata('storyId') + "/")
        self._setURL(url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','scrhub') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y" # XXX
    
    # Can't use postUrl or fetchUrl in configurable.py. Private method as a quick override
    # Scribblehuib needs a proper payload - all tried:
    # payload = "action=wi_gettocchp&strSID=" + self.story.getMetadata('storyId') + "&strmypostid=0&strFic=yes"
    # payload = {"action": "wi_gettocchp", "strSID": self.story.getMetadata('storyId'), "strmypostid": "0", "strFic": "yes"}
    # payload = {"":"action=wi_gettocchp&strSID=" + self.story.getMetadata('storyId') + "&strmypostid=0&strFic=yes"}
    # data = self._fetchUrlRawOpened("https://www.scribblehub.com/wp-admin/admin-ajax.php", payload)
    def _get_contents(self):
        payload = "action=wi_gettocchp&strSID=" + self.story.getMetadata('storyId') + "&strmypostid=0&strFic=yes"     
        req = Request("https://www.scribblehub.com/wp-admin/admin-ajax.php", data=payload.encode('utf-8'))
    
        ## Specific UA because too many sites are blocking the default python UA.
        opener = build_opener(HTTPCookieProcessor(cl.LWPCookieJar()),GZipProcessor())
        opener.addheaders = [('User-Agent', self.getConfig('user_agent')),
                            ('X-Clacks-Overhead','GNU Terry Pratchett')]

        encoded_data = opener.open(req, None, float(self.getConfig('connect_timeout',30.0))).read()
        data = Configuration._do_reduce_zalgo(self, Configuration._decode(self, encoded_data))

        return data
        


    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.scribblehub.com' # XXX

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/series/1234/storyname/"

    def getSiteURLPattern(self):
        return re.escape("https://"+self.getSiteDomain()+"/series/")+r"\S+$"

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

         ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            # Weirdly, different sites use different warning numbers.
            # If the title search below fails, there's a good chance
            # you need a different number.  print data at that point
            # and see what the 'click here to continue' url says.
            addurl = "&ageconsent=ok&warning=3"
        else:
            addurl=""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
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
                except HTTPError as e:
                    if e.code == 404:
                        raise exceptions.StoryDoesNotExist(self.url)
                    else:
                        raise e
            else:
                raise exceptions.AdultCheckRequired(self.url)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        pagetitle = soup.find('div',{'class':'fic_title'})
        self.story.setMetadata('title',stripHTML(pagetitle))

        # Find authorid and URL from main story page 
        self.story.setMetadata('authorId',stripHTML(soup.find('span',{'class':'auth_name_fic'})))
        self.story.setMetadata('authorUrl',soup.find('div',{'class':'author'}).find('div',{'property':'author'}).find('span',{'property':'name'}).find('a').get('href'))
        self.story.setMetadata('author',stripHTML(soup.find('span',{'class':'auth_name_fic'})))

        # Find the chapters:
        # This is where scribblehub is gonna get a lil bit messy..

        # Get the contents list from scribblehub, iterate through and add to chapters
        # Can be fairly certain this will not 404 - we know the story id is vlid thansk
        contents_soup = self.make_soup(self._get_contents())


        for i in range(1, int(contents_soup.find('ol',{'id':'ol_toc'}).get('count'))):
            chapter_url = contents_soup.find('li',{'cnt':str(i)}).find('a').get('href')
            chapter_name = contents_soup.find('li',{'cnt':str(i)}).find('a').get('title')
            logger.debug("Found Chapter " + str(i) + ", name: " + chapter_name + ", url: " + chapter_url)
            self.add_chapter(chapter_name, chapter_url)

        


        # for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
        #     # just in case there's tags, like <i> in chapter titles.
        #     self.add_chapter(chapter,'http://'+self.host+'/'+chapter['href']+addurl)


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        
        # Story Description
        if soup.find('div',{'class': 'wi_fic_desc'}):
            svalue = soup.find('div',{'class': 'wi_fic_desc'})
            self.setDescription(url,svalue)
            #self.story.setMetadata('description',stripHTML(svalue))

        # Categories
        if soup.find('span',{'class': 'wi_fic_showtags_inner'}):
            categories = soup.find('span',{'class': 'wi_fic_showtags_inner'}).findAll('a')
            for category in categories:
                self.story.addToList('category', stripHTML(category))
        
        # Genres
        if soup.find('a',{'class': 'fic_genre'}):
            genres = soup.findAll('a',{'class': 'fic_genre'})
            for genre in genres:
                self.story.addToList('genre', stripHTML(genre))
       
        # Content Warnings
        if soup.find('ul',{'class': 'ul_rate_expand'}):
            warnings = soup.find('ul',{'class': 'ul_rate_expand'}).findAll('a')
            for warn in warnings:
                self.story.addToList('warnings', stripHTML(warn))
        
        # Complete
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]) == "Completed":
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')


        # Updated
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]):
            date_str = soup.find_all("span", title=re.compile(r"^Last"))[0].get("title")
            self.story.setMetadata('dateUpdated', makeDate(date_str[14:-9], self.dateformat))


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'chp_raw'})
        div.find('div', {'class' : 'wi_authornotes'}).decompose()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
