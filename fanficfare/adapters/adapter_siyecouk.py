# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from .base_adapter import BaseSiteAdapter,  makeDate

logger = logging.getLogger(__name__)


# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return SiyeCoUkAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class SiyeCoUkAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata("storyId", self.parsed_QS["sid"])

        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/siye/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','siye') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y.%m.%d" # XXX

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.siye.co.uk' # XXX

    @classmethod
    def getAcceptDomains(cls):
        return ['www.siye.co.uk','siye.co.uk']

    @classmethod
    def stripURLParameters(cls, url):
        return url

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/siye/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://(www\.)?siye\.co\.uk/(siye/)?viewstory.php\?.*sid=\d+"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        # Except it doesn't this time. :-/
        url = self.url #+'&index=1'+addurl
        logger.debug("URL: "+url)

        data = self.get_request(url)

        soup = self.make_soup(data)
        # print data


        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        if a is None:
            raise exceptions.StoryDoesNotExist(self.url)
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/siye/'+a['href'])
        self.story.setMetadata('author',a.string)

        # need(or easier) to pull other metadata from the author's list page.
        authsoup = self.make_soup(self.get_request(self.story.getMetadata('authorUrl')))

        # remove author profile incase they've put the story URL in their bio.
        profile = authsoup.find('div',{'id':'profile'})
        if profile: # in case it changes.
            profile.extract()

        ## Title
        titlea = authsoup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(titlea))

        # Find the chapters (from soup, not authsoup):
        for chapter in soup.find_all('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+r"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.add_chapter(chapter,'https://'+self.host+'/siye/'+chapter['href'])

        if self.num_chapters() < 1:
            self.add_chapter(self.story.getMetadata('title'),url)

        # The stuff we can get from the chapter list/one-shot page are
        # in the first table with 95% width.
        metatable = soup.find('table',{'width':'95%'})

        # Categories
        cat_as = metatable.find_all('a', href=re.compile(r'categories.php'))
        for cat_a in cat_as:
            self.story.addToList('category',stripHTML(cat_a))

        for label in metatable.find_all('b'):
            # html5lib doesn't give me \n for <br> anymore.
            # I expect there's a better way, but this is what came to
            # mind today. -JM
            part = stripHTML(label)
            nxtbr = label.find_next_sibling('br')
            nxtsib = label.next_sibling
            value = ""
            while nxtsib != nxtbr:
                value += stripHTML(nxtsib)
                nxtsib = nxtsib.next_sibling
            # logger.debug("label:%s value:%s"%(part,value))

            if part.startswith("Characters:"):
                for item in value.split(', '):
                    if item == "Harry/Ginny":
                        self.story.addToList('characters',"Harry Potter")
                        self.story.addToList('characters',"Ginny Weasley")
                    elif item not in ("None","All"):
                        self.story.addToList('characters',item)

            if part.startswith("Genres:"):
                self.story.extendList('genre',value.split(', '))

            if part.startswith("Warnings:"):
                if value != "None":
                    self.story.extendList('warnings',value.split(', '))

            if part.startswith("Rating:"):
                self.story.setMetadata('rating',value)

            if part.startswith("Summary:"):
                # summary can include extra br and b tags go until Hitcount
                summary = ""
                nxt = label.next_sibling
                while nxt and "Hitcount:" not in stripHTML(nxt):
                    summary += "%s"%nxt
                    # logger.debug(summary)
                    nxt = nxt.next_sibling
                if summary.strip().endswith("<br/>"):
                    summary = summary.strip()[0:-len("<br/>")]
                self.setDescription(url,summary)

        # Stuff from author block:

        # SIYE formats stories in the author list differently when
        # their part of a series.  Look for non-series...
        divdesc = titlea.parent.parent.find('div',{'class':'desc'})
        if not divdesc:
            # ... now look for series.
            divdesc = titlea.parent.parent.findNextSibling('tr').find('div',{'class':'desc'})

        moremeta = stripHTML(divdesc)
        # logger.debug("moremeta:%s"%moremeta)
        # html5lib doesn't give me \n for <br> anymore.
        for part in moremeta.replace(' - ','\n').replace("Completed","\nCompleted").split('\n'):
            # logger.debug("part:%s"%part)
            try:
                (name,value) = part.split(': ')
            except:
                # not going to worry about fancier processing for the bits
                # that don't match.
                continue
            name=name.strip()
            value=value.strip()
            if name == 'Published':
                self.story.setMetadata('datePublished', makeDate(value, self.dateformat))
            if name == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.dateformat))
            if name == 'Completed':
                if value == 'Yes':
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')
            if name == 'Words':
                self.story.setMetadata('numWords', value)

        try:
            # Find Series name from series URL.
            a = titlea.findPrevious('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'https://'+self.host+'/'+a['href']

            seriessoup = self.make_soup(self.get_request(series_url))
            storyas = seriessoup.find_all('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
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

        # soup = self.make_soup(self.get_request(url))
        # BeautifulSoup objects to <p> inside <span>, which
        # technically isn't allowed.
        soup = self.make_soup(self.get_request(url))

        # not the most unique thing in the world, but it appears to be
        # the best we can do here.
        story = soup.find('span', {'style' : 'font-size: 100%;'})

        if story is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        story.name='div'

        return self.utf8FromSoup(url,story)
