# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2020 FanFicFare team
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
    return ArchiveHPfanfictalkComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ArchiveHPfanfictalkComAdapter(BaseSiteAdapter):

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
        self.story.setMetadata('siteabbrev','ahpfftc')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'archive.hpfanfictalk.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
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
        url = self.url+'&index=1'+addurl
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

        ## Title and author
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # logger.debug(soup)

        # Now go hunting for all the meta data and the chapter list.

        pagetitle = soup.find('h3')
        # logger.debug(pagetitle)
        ## Title
        a = pagetitle.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = pagetitle.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',stripHTML(a))

        # Find the chapters:
        for chapter in soup.find_all('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'http://'+self.host+'/'+chapter['href'])

        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        listbox = soup.find('div', {'class':'listbox'})
        # this site has two divs with class=gb-50 and no immediate container.
        gb50s = soup.find_all('div', {'class':'gb-50'})

        def list_from_urls(parent, regex, metadata):
            urls = parent.find_all('a',href=re.compile(regex))
            for url in urls:
                self.story.addToList(metadata,stripHTML(url))

        list_from_urls(listbox,r'browse.php\?type=categories','category')
        list_from_urls(gb50s[0],r'browse.php\?type=characters','characters')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=11','ships')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=14','house')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=4','genre')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=13','themes')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=8','warnings')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=10','inclusivity')

        bq = soup.find('blockquote2')
        if bq:
            # blockquote2???  Whatever.  But we're changing it to a real tag.
            bq.name='div'
            self.setDescription(url,bq)

        # usually use something more precise for label search, but
        # site doesn't group much.
        labels = soup.find_all('b')
        for labelspan in labels:
            # logger.debug(labelspan)
            value = labelspan.nextSibling
            label = stripHTML(labelspan)
            # logger.debug(value)
            # logger.debug(label)

            if 'Rating' in label:
                # Mature Audiences · Incomplete
                (rating,status) = value.split('·')
                self.story.setMetadata('rating', rating)
                if 'Complete' in status:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Story Length' in label:
                stripHTML(value)
                # 10 chapters (45462 words)
                v = stripHTML(value)
                v = v.split('(')[1]
                v = v.split(' words')[0]
                self.story.setMetadata('numWords', v)

            if 'Published' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value).replace('·',''), self.dateformat))

            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

        # XXX Series not collected -- Site allows stories to be in
        # several series at once.  FFF isn't thrilled with that.
        # Example:
        # http://archive.hpfanfictalk.com/viewstory.php?sid=483

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
