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
    return QafFicComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class QafFicComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/atp/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','atp')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.qaf-fic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/atp/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/atp/viewstory.php?sid=")+r"\d+$"


    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        if self.is_adult or self.getConfig("is_adult"):
            # Weirdly, different sites use different warning numbers.
            # If the title search below fails, there's a good chance
            # you need a different number.  print data at that point
            # and see what the 'click here to continue' url says.
            addurl = "&warning=NC-17"
        else:
            addurl=""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url+addurl
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        m = re.search(r"'viewstory.php\?sid=\d+((?:&amp;ageconsent=ok)?&amp;warning=\s+)'",data)
        if m != None:
            if self.is_adult or self.getConfig("is_adult"):
                # We tried the default and still got a warning, so
                # let's pull the warning number from the 'continue'
                # link and reload data.
                addurl = m.group(1)
                # correct stupid &amp; error in url.
                addurl = addurl.replace("&amp;","&")
                url = self.url+addurl
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

        ## Title and author
        a = soup.find('div', {'id' : 'pagetitle'})

        aut = a.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',aut['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/atp/'+aut['href'])
        self.story.setMetadata('author',aut.string)
        aut.extract()

        self.story.setMetadata('title',stripHTML(a)[:(len(a.string)-3)])

        # Find the chapters:
        chapters=soup.find('select')
        if chapters != None:
            for chapter in chapters.findAll('option'):
                # just in case there's tags, like <i> in chapter titles.
                self.add_chapter(chapter,'https://'+self.host+'/atp/viewstory.php?sid='+self.story.getMetadata('storyId')+'&chapter='+chapter['value'])
        else:
            self.add_chapter(self.story.getMetadata('title'),url)


        asoup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl')))
        for list in asoup.findAll('div', {'class' : re.compile('listbox')}):
            a = list.find('a')
            if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in a['href']:
                break

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = list.findAll('span', {'class' : 'classification'})
        for labelspan in labels:
            label = labelspan.string
            value = labelspan.nextSibling

            if 'Summary' in label:
                ## Everything until the next span class='label'
                svalue = ""
                while value and 'classification' not in defaultGetattr(value,'class'):
                    if "Featured Stories" not in value:
                        svalue += unicode(value)
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
                self.story.setMetadata('datePublished', makeDate(stripHTML(value.split(' ::')[0]), self.dateformat))

            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        try:
            if list.find('a', href=re.compile(r"series.php")) != None:
                for series in asoup.findAll('a', href=re.compile(r"series.php\?seriesid=\d+")):
                    # Find Series name from series URL.
                    series_url = 'https://'+self.host+'/atp/'+series['href']
                    # use BeautifulSoup HTML parser to make everything easier to find.
                    seriessoup = self.make_soup(self._fetchUrl(series_url))
                    storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
                    i=1
                    for a in storyas:
                        if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                            name=seriessoup.find('div', {'id' : 'pagetitle'})
                            name.find('a').extract()
                            self.setSeries(name.text.split(' by[')[0], i)
                            self.story.setMetadata('seriesUrl',series_url)
                            i=0
                            break
                        i+=1
                    if i == 0:
                        break

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
