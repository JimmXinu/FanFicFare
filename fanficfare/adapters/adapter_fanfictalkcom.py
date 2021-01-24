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
    return FanfictalkComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class FanfictalkComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/archive/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ahpfftc')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y"

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain(),'archive.hpfanfictalk.com']

    @classmethod
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return [cls.getConfigSection(),'archive.hpfanfictalk.com']

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'fanfictalk.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/archive/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://(archive\.hp)?"+re.escape(self.getSiteDomain())+r"(/archive)?/viewstory\.php\?sid=\d+$"

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
            data = self.get_request(url)
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

        pagetitle = soup.select_one('div#pagetitle')
        # logger.debug(pagetitle)
        ## Title
        a = pagetitle.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        for a in pagetitle.find_all('a', href=re.compile(r"viewuser.php\?uid=\d+")):
            self.story.addToList('authorId',a['href'].split('=')[1])
            self.story.addToList('authorUrl','https://'+self.host+'/'+a['href'])
            self.story.addToList('author',stripHTML(a))

        # Find the chapters:
        for chapter in soup.find_all('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+r"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'https://'+self.host+'/archive/'+chapter['href'])

        # categories
        for a in soup.select("div#sort a"):
            self.story.addToList('category',stripHTML(a))

        # this site has two divs with class=gb-50 and no immediate container.
        gb50s = soup.find_all('div', {'class':'gb-50'})

        def list_from_urls(parent, regex, metadata):
            urls = parent.find_all('a',href=re.compile(regex))
            for url in urls:
                self.story.addToList(metadata,stripHTML(url))

        list_from_urls(gb50s[0],r'browse.php\?type=characters','characters')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=11','ships')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=10','representation')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=7','storytype')
        list_from_urls(gb50s[0],r'browse.php\?type=class&type_id=14','house')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=8','warnings')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=15','contentwarnings')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=4','genre')
        list_from_urls(gb50s[1],r'browse.php\?type=class&type_id=13','tropes')

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

            if 'Words:' in label:
                stripHTML(value)
                self.story.setMetadata('numWords', stripHTML(value).replace('·',''))

            if 'Published:' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value).replace('·',''), self.dateformat))

            if 'Updated:' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value).replace('·',''), self.dateformat))

        # Site allows stories to be in several series at once.  FFF
        # isn't thrilled with that, we have series00, series01, etc.
        # Example:
        # https://fanfictalk.com/archive/viewstory.php?sid=483

        if self.getConfig("collect_series"):
            seriesspan = soup.find('span',label='Series')
            for i, seriesa in enumerate(seriesspan.find_all('a', href=re.compile(r"viewseries\.php\?seriesid=\d+"))):
                # logger.debug(seriesa)
                series_name = stripHTML(seriesa)
                series_url = 'https://'+self.host+'/archive/'+seriesa['href']

                seriessoup = self.make_soup(self.get_request(series_url))
                storyas = seriessoup.find_all('a', href=re.compile(r'viewstory.php\?sid=\d+'))
                # logger.debug(storyas)
                j=1
                found = False
                for storya in storyas:
                    # logger.debug(storya)
                    ## allow for JS links.
                    if ('viewstory.php?sid='+self.story.getMetadata('storyId')) in storya['href']:
                        found = True
                        break
                    j+=1
                if found:
                    series_index = j
                    self.story.setMetadata('series%02d'%i,"%s [%s]"%(series_name,series_index))
                    self.story.setMetadata('series%02dUrl'%i,series_url)
                    if i == 0:
                        self.setSeries(series_name, series_index)
                        self.story.setMetadata('seriesUrl',series_url)
                else:
                    logger.debug("Story URL not found in series (%s) page, not including."%series_url)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))

        div = soup.find('div', {'id' : 'story'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
