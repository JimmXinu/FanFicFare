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
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

# By virtue of being recent and requiring both is_adult and user/pass,
# adapter_fanficcastletvnet.py is the best choice for learning to
# write adapters--especially for sites that use the eFiction system.
# Most sites that have ".../viewstory.php?sid=123" in the story URL
# are eFiction.

# For non-eFiction sites, it can be considerably more complex, but
# this is still a good starting point.

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
    return SheppardWeirComAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SheppardWeirComAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        # XXX Most sites don't have the /fanfic part.  Replace all to remove it usually.
        self._setURL('https://' + self.getSiteDomain() + '/fanfics/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','swf') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y" # XXX

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'sheppardweir.com' # XXX

    @classmethod
    def getSiteExampleURLs(self):
        return "https://"+self.getSiteDomain()+"/fanfics/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/fanfics/viewstory.php?sid=")+r"\d+$"

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

        loginUrl = 'https://' + self.getSiteDomain() + '/fanfics/user.php?action=login'
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
            addurl = "&ageconsent=ok&warning=4" # XXX
        else:
            addurl=""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+'&index=1'+addurl
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

        # The actual text that is used to announce you need to be an
        # adult varies from site to site.  Again, print data before
        # the title search to troubleshoot.
        if "Age Consent Required" in data: # XXX
            raise exceptions.AdultCheckRequired(self.url)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        pagetitle = soup.find('div',{'id':'pagetitle'})
        ## Title
        a = pagetitle.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        # (fetch multiple authors)
        alist = soup.findAll('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        for a in alist:
            self.story.addToList('authorId',a['href'].split('=')[1])
            self.story.addToList('authorUrl','https://'+self.host+'/fanfics/'+a['href'])
            self.story.addToList('author',a.string)


        # Reviews
        reviewdata = soup.find('div', {'id' : 'sort'})
        a = reviewdata.findAll('a', href=re.compile(r'reviews.php\?type=ST&(amp;)?item='+self.story.getMetadata('storyId')+"$"))[1] # second one.
        self.story.setMetadata('reviews',stripHTML(a))


        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'https://'+self.host+'/fanfics/'+chapter['href']+addurl)


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # Summary
        summarydata = unicode(soup.find('div',{'class':'content'}))
        start='<span class="label">Summary: </span>'
        end='</div>'
        summarydata = summarydata[summarydata.index(start)+len(start):summarydata.rindex(end)]
        self.setDescription(url,self.make_soup(summarydata))

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Rated' in label:
                self.story.setMetadata('rating', value)

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                charstext = [char.string for char in chars]
                for char in charstext:
                    self.story.addToList('characters',char.string)

            ## Not all sites use Genre, but there's no harm to
            ## leaving it in.  Check to make sure the type_id number
            ## is correct, though--it's site specific.
            if 'Genre' in label:
                genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1')) # XXX
                genrestext = [genre.string for genre in genres]
                self.genre = ', '.join(genrestext)
                for genre in genrestext:
                    self.story.addToList('genre',genre.string)

            ## Not all sites use Warnings, but there's no harm to
            ## leaving it in.  Check to make sure the type_id number
            ## is correct, though--it's site specific.
            if 'Warnings' in label:
                warnings = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2')) # XXX
                warningstext = [warning.string for warning in warnings]
                self.warning = ', '.join(warningstext)
                for warning in warningstext:
                    self.story.addToList('warnings',warning.string)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                value=value.replace(' - ','')
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))

            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'https://'+self.host+'/fanfics/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = self.make_soup(self._fetchUrl(series_url))
            storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
            i=1
            for a in storyas:
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
