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
import sys

from bs4.element import Comment
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return TomParisDormComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class TomParisDormComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','tpdorm')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d/%m/%y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.tomparisdorm.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

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
        self.story.setMetadata('authorUrl','http://'+self.host+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'http://'+self.host+'/'+chapter['href'])


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.
        
        ## Getting the Summary
        value = stripHTML(soup.find('div',{'class' : 'summary'})).strip('Summary')
        self.setDescription(url,value)
        
        # Get the rest of the Metadata
        mdsoup = soup.find('div',{'id' : 'output'})
        
        mdstr = unicode(mdsoup).replace('\n','').replace('\r','').replace('\t',' ').replace('  ',' ').replace('  ',' ').replace('  ',' ')
        mdstr = stripHTML(mdstr.replace(r'<br/>',r'-:-').replace('|','-:-'))
        mdstr = mdstr.replace(r'[Rev',r'-:-[Rev').replace(' -:- ','-:-').strip('-:-').strip('-:-')
        
        ##I am using this method, because the summary does not have a 'label', and the Metadata is always in this order (as far as I've tested)
        for i, value in enumerate(mdstr.split('-:-')):
            if 'Published:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('datePublished', makeDate(val, self.dateformat))

            elif 'Last Updated:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('dateUpdated', makeDate(val, self.dateformat))

            elif 'Rating:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('rating', stripHTML(val))

            elif 'Category:' in value:
                cats = mdsoup.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                for cat in cats:
                    self.story.addToList('category',cat.string)

            elif 'Characters:' in value:
                chars = mdsoup.findAll('a',href=re.compile(r'browse.php\?type=characters'))
                for char in chars:
                    self.story.addToList('characters',char.string)

            elif 'Genres:' in value:
                genres = mdsoup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=1')) # XXX
                for genre in genres:
                    self.story.addToList('genre',genre.string)

            elif 'Warnings:' in value:
                warnings = mdsoup.findAll('a',href=re.compile(r'browse.php\?type=class&type_id=2')) # XXX
                for warning in warnings:
                    self.story.addToList('warnings',warning.string)

            elif 'Challenge:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('challenge', stripHTML(val))

            elif 'Series:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('series', stripHTML(val))

            elif 'Chapters:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('numChapters', int(val))

            elif 'Completed:' in value:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            elif 'Word Count:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('numWords', int(stripHTML(val)))

            elif 'Read:' in value:
                val=value.split(':')[1].strip()
                self.story.setMetadata('readings', stripHTML(val))

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
