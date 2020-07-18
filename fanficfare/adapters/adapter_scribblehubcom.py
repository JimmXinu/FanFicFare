# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2020 FanFicFare team
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
import logging, time, datetime
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves import http_cookiejar as cl


from .base_adapter import BaseSiteAdapter,  makeDate


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

    # Set cookie to ascending order before page loads, means we know date published
    def set_contents_cookie(self):
        cookie = cl.Cookie(version=0, name='toc_sorder', value='asc',
                           port=None, port_specified=False,
                           domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                           path='/', path_specified=True,
                           secure=False,
                           expires=time.time()+10000,
                           discard=False,
                           comment=None,
                           comment_url=None,
                           rest={'HttpOnly': None},
                           rfc2109=False)
        self.get_configuration().get_cookiejar().set_cookie(cookie)

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
    def extractChapterUrlsAndMetadata(self, get_cover=True):

        # Set the chapters list cookie to asc
        self.set_contents_cookie()

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
        # Can be fairly certain this will not 404 - we know the story id is valid
        contents_payload = {"action": "wi_gettocchp",
                            "strSID": self.story.getMetadata('storyId'),
                            "strmypostid": 0,
                            "strFic": "yes"}        
        
        contents_data = self._postUrl("https://www.scribblehub.com/wp-admin/admin-ajax.php", contents_payload)
        
        contents_soup = self.make_soup(contents_data)

        for i in range(1, int(contents_soup.find('ol',{'id':'ol_toc'}).get('count')) + 1):
            chapter_url = contents_soup.find('li',{'cnt':str(i)}).find('a').get('href')
            chapter_name = contents_soup.find('li',{'cnt':str(i)}).find('a').get('title')
            logger.debug("Found Chapter " + str(i) + ", name: " + chapter_name + ", url: " + chapter_url)
            self.add_chapter(chapter_name, chapter_url)


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
        
        # The date parsing is a bit of a bodge, plenty of corner cased I probably haven't thought of, but try anyway 
        # Complete
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]) == "Completed":
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')


        # Updated | looks like this: <span title="Last updated: Jul 16, 2020 01:02 AM">Jul 16, 2020</span> -- snip out the date
        # if we can't parse the date it's because it's today and it says somehting like "6 hours ago"
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]):
            date_str = soup.find_all("span", title=re.compile(r"^Last"))[0].get("title")
            try:
                self.story.setMetadata('dateUpdated', makeDate(date_str[14:-9], self.dateformat))
            except ValueError:  
                self.story.setMetadata('datePublished', datetime.date.today())

        # Cover Art - scribblehub has default coverart if it isn't set so this _should_ always work
        if get_cover:
            cover_url = ""
            cover_url = soup.find('div',{'class':'fic_image'}).find('img').get('src')
            if cover_url:
                self.setCoverImage(url,cover_url)
        
        # Lil recursive funciton to get Date Published: 
        # if we get a ValueError it's because it's today and it says somehting like "6 hours ago"
        # if we get AttributeError it's because that index doesn't exist, iterate up to 10 to try and find the 1st chapter, give up if not
        def find_date_published(index_val=1):
            try:
                self.story.setMetadata('datePublished', makeDate(stripHTML(soup.find('ol', {'class' : 'toc_ol'}).find('li', {'order' : str(index_val)}).find('span', {'class': 'fic_date_pub'})), self.dateformat))
                return
            except ValueError:
                self.story.setMetadata('datePublished', datetime.date.today())
                return
            except AttributeError:
                if index_val > 10:
                    logger.warn("Failed to retrieve date published for " + url)
                    return
                find_date_published(index_val + 1)
                return

        find_date_published()

        # Ratings, default to not rated. Scribble hub has no rating system, but has genres for mature and adult, so try to set to these
        self.story.setMetadata('rating', "Not Rated")

        if soup.find("a", {"gid" : "20"}):
            self.story.setMetadata('rating', "Mature")
        
        if soup.find("a", {"gid" : "902"}):
            self.story.setMetadata('rating', "Adult")


        # Extra metadata from URL + /stats/
        # Again we know the storyID is valid from before, so this shouldn't raise an exception, and if it does we might want to know about it..
        data = self._fetchUrl(url + 'stats/')
        soup = self.make_soup(data)
        
        def find_stats_data(element, row, metadata):
            if element in stripHTML(row.find('th')):
                self.story.setMetadata(metadata, stripHTML(row.find('td')))
        
        if soup.find('table',{'class': 'table_pro_overview'}):
            stats_table = soup.find('table',{'class': 'table_pro_overview'}).findAll('tr')
            for row in stats_table:
                find_stats_data("Total Views (All)", row, "views")
                find_stats_data("Word Count", row, "numWords")
                find_stats_data("Average Words", row, "averageWords")
        else:
            logger.debug('Failed to get additional metadata [see PR #512] from url: ' + url + "stats/")



    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'chp_raw'})
        if div.find('div', {'class' : 'wi_authornotes'}):
            div.find('div', {'class' : 'wi_authornotes'}).decompose()

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
