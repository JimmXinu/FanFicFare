# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import urlparse
import time

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter, makeDate

class LiteroticaSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.

        self.story.setMetadata('siteabbrev','litero')

        # normalize to first chapter.  Not sure if they ever have more than 2 digits.
        storyId = self.parsedUrl.path.split('/',)[2]
        # replace later chapters with first chapter but don't remove numbers
        # from the URL that disambiguate stories with the same title.
        storyId = re.sub("-ch-?\d\d", "", storyId)
        self.story.setMetadata('storyId', storyId)

        ## accept m(mobile)url, but use www.
        url = re.sub("^(www|german|spanish|french|dutch|italian|romanian|portuguese|other)\.i",
                              "\1",
                              url)

        ## strip ?page=...
        url = re.sub("\?page=.*$", "", url)

        ## set url
        self._setURL(url)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = '%m/%d/%y'

    @staticmethod
    def getSiteDomain():
        return 'literotica.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.literotica.com',
                'www.i.literotica.com',
                'german.literotica.com',
                'german.i.literotica.com',
                'spanish.literotica.com',
                'spanish.i.literotica.com',
                'french.literotica.com',
                'french.i.literotica.com',
                'dutch.literotica.com',
                'dutch.i.literotica.com',
                'italian.literotica.com',
                'italian.i.literotica.com',
                'romanian.literotica.com',
                'romanian.i.literotica.com',
                'portuguese.literotica.com',
                'portuguese.i.literotica.com',
                'other.literotica.com',
                'other.i.literotica.com']

    @classmethod
    def getSiteExampleURLs(self):
        return "http://www.literotica.com/s/story-title https://www.literotica.com/s/story-title http://portuguese.literotica.com/s/story-title http://german.literotica.com/s/story-title"

    def getSiteURLPattern(self):
        return r"https?://(www|german|spanish|french|dutch|italian|romanian|portuguese|other)(\.i)?\.literotica\.com/s/([a-zA-Z0-9_-]+)"

    def extractChapterUrlsAndMetadata(self):
        """
        NOTE: Some stories can have versions, 
              e.g. /my-story-ch-05-version-10
        NOTE: If two stories share the same title, a running index is added,
              e.g.: /my-story-ch-02-1
        Strategy:
            * Go to author's page, search for the current story link,
            * If it's in a tr.root-story => One-part story
                * , get metadata and be done
            * If it's in a tr.sl => Chapter in series
                * Search up from there until we find a tr.ser-ttl (this is the
                story)
                * Gather metadata
                * Search down from there for all tr.sl until the next
                tr.ser-ttl, foreach
                    * Chapter link is there
        """

        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        logger.debug("Chapter/Story URL: <%s> " % self.url)
        try:
            data1 = self._fetchUrl(self.url)
            soup1 = bs.BeautifulSoup(data1)
            #strip comments from soup
            [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, bs.Comment))]
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # author
        a = soup1.find("span", "b-story-user-y")
        self.story.setMetadata('authorId', urlparse.parse_qs(a.a['href'].split('?')[1])['uid'][0])
        authorurl = a.a['href']
        if authorurl.startswith('//'):
            authorurl = self.parsedUrl.scheme+':'+authorurl
        self.story.setMetadata('authorUrl', authorurl)
        self.story.setMetadata('author', a.text)

        # get the author page
        try:
            dataAuth = self._fetchUrl(authorurl)
            soupAuth = bs.BeautifulSoup(dataAuth)
            #strip comments from soup
            [comment.extract() for comment in soupAuth.findAll(text=lambda text:isinstance(text, bs.Comment))]
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(authorurl)
            else:
                raise e

        ## Find link to url in author's page
        ## site has started using //domain.name/asdf urls remove https?: from front
        storyLink = soupAuth.find('a', href=self.url[self.url.index(':')+1:])

        if storyLink is not None:
            urlTr = storyLink.parent.parent
            if urlTr['class'] == "sl":
                isSingleStory = False
            else:
                isSingleStory = True
        else:
            raise exceptions.FailedToDownload("Couldn't find story <%s> on author's page <%s>" % (url, authorurl))

        if isSingleStory:
            self.story.setMetadata('title', storyLink.text)
            self.story.setMetadata('description', urlTr.findAll("td")[1].text)
            self.story.addToList('eroticatags', urlTr.findAll("td")[2].text)
            date = urlTr.findAll('td')[-1].text
            self.story.setMetadata('datePublished', makeDate(date, self.dateformat))
            self.story.setMetadata('dateUpdated',makeDate(date, self.dateformat))
            self.chapterUrls = [(storyLink.text, self.url)]
        else:
            seriesTr = urlTr.previousSibling
            while seriesTr['class'] != 'ser-ttl':
                seriesTr = seriesTr.previousSibling
            m = re.match("^(?P<title>.*?):\s(?P<numChapters>\d+)\sPart\sSeries$", seriesTr.find("strong").text)
            self.story.setMetadata('title', m.group('title'))
            self.story.setMetadata('numChapters', int(m.group('numChapters')))

            ## Walk the chapters
            chapterTr = seriesTr.nextSibling
            self.chapterUrls = []
            dates = []
            descriptions = []
            while chapterTr is not None and chapterTr['class'] == 'sl':
                descriptions.append(chapterTr.findAll("td")[1].text)
                chapterLink = chapterTr.find("td", "fc").find("a")
                self.chapterUrls.append((chapterLink.text, "http:" + chapterLink["href"]))
                self.story.addToList('eroticatags', chapterTr.findAll("td")[2].text)
                dates.append(makeDate(chapterTr.findAll('td')[-1].text, self.dateformat))
                chapterTr = chapterTr.nextSibling

            ## Set description to joint chapter descriptions
            self.story.setMetadata('description', " / ".join(descriptions))

            ## Set the oldest date as publication date, the newest as update date
            dates.sort()
            self.story.setMetadata('datePublished', dates[0])
            self.story.setMetadata('dateUpdated', dates[-1])

            # normalize on first chapter URL.
            self._setURL(self.chapterUrls[0][1])

        # set storyId to 'title-author' to avoid duplicates
        # self.story.setMetadata('storyId', 
        #     re.sub("[^a-z0-9]", "", self.story.getMetadata('title').lower())
        #     + "-"
        #     + re.sub("[^a-z0-9]", "", self.story.getMetadata('author').lower()))

        return

    def getChapterText(self, url):
        logger.debug('Getting chapter text from <%s>' % url)
        # time.sleep(0.5)
        data1 = self._fetchUrl(url)
        soup1 = bs.BeautifulSoup(data1)

        #strip comments from soup
        [comment.extract() for comment in soup1.findAll(text=lambda text:isinstance(text, bs.Comment))]

        # get story text
        story1 = soup1.find('div', 'b-story-body-x').p
        story1.name='div'
        story1.append('<br />')
        storytext = self.utf8FromSoup(url,story1)

        # find num pages
        pgs = int(soup1.find("span", "b-pager-caption-t r-d45").string.split(' ')[0])
        logger.debug("pages: "+str(pgs))

        # get all the pages
        for i in xrange(2, pgs+1):
            try:
                logger.debug("fetching page "+str(i))
                time.sleep(0.5)
                data2 = self._fetchUrl(url, {'page': i})
                soup2 = bs.BeautifulSoup(data2)
                [comment.extract() for comment in soup2.findAll(text=lambda text:isinstance(text, bs.Comment))]
                story2 = soup2.find('div', 'b-story-body-x').p
                story2.name='div'
                story2.append('<br />')
                storytext += self.utf8FromSoup(url,story2)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    raise exceptions.StoryDoesNotExist(url)
                else:
                    raise e
        return storytext


def getClass():
    return LiteroticaSiteAdapter



