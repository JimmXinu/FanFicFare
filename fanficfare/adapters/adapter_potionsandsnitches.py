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
import urllib
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class PotionsAndSnitchesOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','pns')

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/fanfiction/viewstory.php?sid='+self.story.getMetadata('storyId'))


    @staticmethod
    def getSiteDomain():
        return 'www.potionsandsnitches.org'

    @classmethod
    def getAcceptDomains(cls):
        return ['potionsandsnitches.org','potionsandsnitches.net']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.potionsandsnitches.org/fanfiction/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://")+r"(www\.)?potionsandsnitches\.(net|org)/fanfiction/viewstory\.php\?sid=\d+$"

    def extractChapterUrlsAndMetadata(self):

        url = self.url+'&index=1'
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        ## Title
        a = soup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/fanfiction/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'http://'+self.host+'/fanfiction/'+chapter['href'])


        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Summary' in label:
                ## Everything until the next div class='listbox'
                svalue = ""
                while 'listbox' not in defaultGetattr(value,'class'):
                    svalue += unicode(value)
                    value = value.nextSibling
                self.setDescription(url,svalue)
                #self.story.setMetadata('description',stripHTML(svalue))

            if 'Rated' in label:
                self.story.setMetadata('rating', value)

            if 'Word count' in label:
                self.story.setMetadata('numWords', value)

            if 'Read' in label:
                self.story.setMetadata('reads', value)

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

            if 'Characters' in label:
                chars = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                charstext = [char.string for char in chars]
                for char in charstext:
                    if "Snape and Harry (required)" in char:
                        self.story.addToList('characters',"Snape")
                        self.story.addToList('characters',"Harry")
                    else:
                        self.story.addToList('characters',char.string)

            if 'Warning' in label:
                warnings = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                for warning in warnings:
                    self.story.addToList('warnings',stripHTML(warning))

            if 'Genre' in label:
                genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                for genre in genres:
                    self.story.addToList('genre',stripHTML(genre))

            if 'Takes Place' in label:
                takesplaces = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                for takesplace in takesplaces:
                    self.story.addToList('takesplaces',stripHTML(takesplace))

            if 'Snape flavour' in label:
                snapeflavours = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                for snapeflavour in snapeflavours:
                    self.story.addToList('snapeflavours',stripHTML(snapeflavour))

            if 'Tags' in label:
                sitetags = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
                for sitetag in sitetags:
                    self.story.addToList('sitetags',stripHTML(sitetag))

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                # limit date values, there's some extra chars.
                self.story.setMetadata('datePublished', makeDate(stripHTML(value[:12]), "%d %b %Y"))

            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value[:12]), "%d %b %Y"))

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/fanfiction/'+a['href']

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

        divsort = soup.find('div',id='sort')
        stars = len(divsort.find_all('img',src='images/star.gif'))
        stars = stars + 0.5 * len(divsort.find_all('img',src='images/starhalf.gif'))
        self.story.setMetadata('stars',stars)

        a = divsort.find_all('a', href=re.compile(r'reviews.php\?type=ST&(amp;)?item='+self.story.getMetadata('storyId')+"$"))[1] # second one.
        self.story.setMetadata('reviews',stripHTML(a))
        

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return PotionsAndSnitchesOrgSiteAdapter

