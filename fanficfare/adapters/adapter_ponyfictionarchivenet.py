# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2018 FanFicFare team
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

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return PonyFictionArchiveNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class PonyFictionArchiveNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # normalized story URL.
        if "explicit" in self.parsedUrl.netloc:
            self._setURL('http://explicit.' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
            self.dateformat = "%d/%b/%y"
        else:
            self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))
            self.dateformat = "%d %b %Y"

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','pffa')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'ponyfictionarchive.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.ponyfictionarchive.net','ponyfictionarchive.net','explicit.ponyfictionarchive.net']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234 http://explicit."+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+"(www\.|explicit\.)?"+re.escape(self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"


    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            # Weirdly, different sites use different warning numbers.
            # If the title search below fails, there's a good chance
            # you need a different number.  print data at that point
            # and see what the 'click here to continue' url says.
            addurl = "&warning=9"
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
        a = soup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'http://'+self.host+'/'+chapter['href']+addurl)


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        genres = soup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1'))
        for genre in genres:
            self.story.addToList('genre',genre.string)

        warnings = soup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=3'))
        for warning in warnings:
            self.story.addToList('warnings',warning.string)

        status = soup.find('a',href=re.compile(r'browse.php\?type=class&type_id=2'))
        if status: # apparently this site can have stories with neither In-Progress or Complete.
            self.story.setMetadata('status',status.string)

        try:
            # explicit.site and .site have some differences now...
            section = soup.findAll('span', {'class' : 'General'})[1]
            self.story.setMetadata('rating', section.previousSibling.previousSibling.string)

            value = section.nextSibling
            svalue = ""
            while 'label' not in defaultGetattr(value,'class'):
                svalue += unicode(value)
                value = value.nextSibling
            self.setDescription(url,svalue)

        except:
            # find rating in data
            # <br /> &bull; Mature &bull; <br />
            lead = "<br /> &bull; "
            trail = " &bull; <br />"
            rating = data[data.index(lead)+len(lead):data.index(trail)]
            if len(rating)<20: # minor sanity check.
                self.story.setMetadata('rating',rating)
            descstr = data[data.index(trail)+len(trail):] # from desc on
            descstr = descstr[:descstr.index('<span class="label">')] # remove after desc.
            self.setDescription(url,descstr)

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Characters' in label:
                chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                for char in chars:
                    self.story.addToList('characters',char.string)

            if 'Completed' in label:
                if 'Yes' in value:
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
