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

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return ChosenTwoFanFicArchiveAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ChosenTwoFanFicArchiveAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','chosen2')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'chosentwofanfic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # checking to see if the is_adult is set to true
        if self.is_adult or self.getConfig("is_adult"):
            addURL = "&ageconsent=ok&warning=3"
        else:
            addURL = ""

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = '{0}&index=1{1}'.format(self.url,addURL)
        logger.debug("URL: "+url)

        data = self.get_request(url)

        if "Content is only suitable for mature adults. May contain explicit language and adult themes. Equivalent of NC-17." in data:
            raise exceptions.AdultCheckRequired(self.url)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied("{0} says: Access denied. This story has not been validated by the adminstrators of this site.".format(self.getSiteDomain()))

        soup = self.make_soup(data)


        ## Title
        ## Some stories have a banner that has it's own a tag before the actual text title...
        ## so I'm checking the pagetitle div for all a tags that match the criteria, then taking the last.
        a = soup.find('div',{'id':'pagetitle'}).findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))[-1]
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        # This site lists the newest member to the site before the div that has the story info
        # so I'm checking the pagetitle div for this as well
        a = soup.find('div',{'id':'pagetitle'}).find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+r"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            #self.add_chapter(chapter,'http://'+self.host+'/'+chapter['href'])
            self.add_chapter(chapter,'https://{0}/{1}{2}'.format(self.host, chapter['href'],addURL))


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

            if 'Disclaimer' in label:
                self.story.setMetadata('disclaimer', stripHTML(value))

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'https://'+self.host+'/'+a['href']

            seriessoup = self.make_soup(self.get_request(series_url))
            # can't use ^viewstory...$ in case of higher rated stories with javascript href.
            storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+'))
            i=1
            for a in storyas:
                # this site has several links to each story.
                if a.text == 'Latest Chapter':
                    if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in a['href']:
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

        soup = self.make_soup(self.get_request(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
