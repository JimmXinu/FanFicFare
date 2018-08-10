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
    return SquidgeOrgPejaAdapter

## XXX IMPORTANT NOTE!!  This adapter is for squidge.org/peja ONLY!
## There are lots of other sites and stuff under squidge.org that
## we're not supporting.  If/When we ever want to support more
## sections of squidge.org, FFDL will need to be changed more
## fundamentally to find different adapters under the same domain.
##
## For now, I've only implemented the part for ini section names so
## if/when more adapters under squidge.org come along, existing ini
## files will still work correctly.

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SquidgeOrgPejaAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/peja/cgi-bin/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','wwomb')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.squidge.org'

    @classmethod # must be @classmethod, don't remove it.
    def getConfigSection(cls):
        # The config section name.  Only override if != site domain.
        return cls.getSiteDomain()+'/peja'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/peja/cgi-bin/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        # but not https://www.squidge.org/peja/cgi-bin/viewstory.php?sid=47746 -- that's the 'Site Map' negative look aead
        return r"https?"+re.escape("://"+self.getSiteDomain()+"/")+r"~?"+re.escape("peja/cgi-bin/viewstory.php?sid=")+r"(?!47746)\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        data = self._fetchUrl(url)

        if "fatal MySQL error was encountered" in data:
            raise exceptions.FailedToDownload("Site SQL Error--bad story")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        # Find authorid and URL from... author url.
        author = soup.find('div', {'id':"pagetitle"}).find('a')
        self.story.setMetadata('authorId',author['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/peja/cgi-bin/'+author['href'])
        self.story.setMetadata('author',author.string)

        authorSoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))

        # There are scripts within the metadata sections, so we need to
        # take them out [GComyn]
        for tag in authorSoup.findAll('script'):
            tag.extract()

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        title = authorSoup.find('a',{'href':'viewstory.php?sid='+self.story.getMetadata('storyId')})
        if not title:
            raise exceptions.StoryDoesNotExist(url)
        self.story.setMetadata('title',stripHTML(title))
        titleblock=title.parent.parent

        chapterselect=soup.find('select',{'name':'chapter'})
        if chapterselect:
            for ch in chapterselect.findAll('option'):
                self.add_chapter(ch,'https://'+self.host+'/peja/cgi-bin/viewstory.php?sid='+self.story.getMetadata('storyId')+'&chapter='+ch['value'])
        else:
            self.add_chapter(title,url)



        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="classification">Rated:</span> NC-17<br /> etc

        labels = titleblock.findAll('span',{'class':'classification'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string
            #print("label:%s value:%s"%(label,value))

            if 'Summary' in label:
                ## Everything until the next span class='label'
                svalue = ""
                while 'classification' not in defaultGetattr(value,'class'):
                    svalue += unicode(value)
                    value = value.nextSibling
                self.setDescription(url,svalue)
                #self.story.setMetadata('description',stripHTML(svalue))

            if 'Rated' in label:
                if value.endswith("["):
                    value = value[:-1]
                self.story.setMetadata('rating', value)

            if 'Characters' in label:
                for char in value.split(','):
                    self.story.addToList('characters',char.strip())

            if 'Genre' in label:
                for genre in value.split(','):
                    if genre.strip() != "None":
                        self.story.addToList('genre',genre.strip())

            if 'Warnings' in label:
                for warning in value.split(','):
                    if warning.strip() != 'None':
                        self.story.addToList('warnings',warning.strip())

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Fandoms' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'categories.php'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

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

                # site has started including a tracking script between Updated label and date--sometimes...
                svalue = ""
                while value is not None and 'classification' not in defaultGetattr(value,'class'):
                    if '<script' not in unicode(value):
                        svalue += unicode(value)
                    value = value.nextSibling
                    #print("svalue:%s"%svalue)

                self.story.setMetadata('dateUpdated', makeDate(stripHTML(svalue), self.dateformat))

        try:
            # Find Series name from series URL.
            # http://www.squidge.org/peja/cgi-bin/series.php?seriesid=254
            a = titleblock.find('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'https://'+self.host+'/peja/cgi-bin/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = self.make_soup(self._fetchUrl(series_url))
            storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
            i=1
            for a in storyas:
                if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                    self.setSeries(series_name, i)
                    self.story.setMetadata('seriesUrl',series_url)
                    break
                # don't count the 'site map' story.  See the url pattern method.
                if '47746' not in a['href']:
                    i+=1

        except:
            # I find it hard to care if the series parsing fails
            pass



    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        chaptext = soup.find('div',{'id':"story"}).find('span')

        if None == chaptext:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chaptext)
