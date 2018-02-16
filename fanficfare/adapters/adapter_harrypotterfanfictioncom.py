# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2017 FanFicFare team
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
import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib
import urllib2


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class HarryPotterFanFictionComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','hp')
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only psid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/viewstory.php?psid='+self.story.getMetadata('storyId'))


    @staticmethod
    def getSiteDomain():
        return 'www.harrypotterfanfiction.com'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.harrypotterfanfiction.com','harrypotterfanfiction.com']

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.harrypotterfanfiction.com/viewstory.php?psid=1234"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://")+r"(www\.)?"+re.escape("harrypotterfanfiction.com/viewstory.php?psid=")+r"\d+$"

    def needToLoginCheck(self, data):
        if 'Registered Users Only' in data \
                or 'There is no such account on our website' in data \
                or "That password doesn't match the one in our database" in data:
          return True
        else:
          return False

    def extractChapterUrlsAndMetadata(self):

        url = self.url+'&index=1'
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        elif "ERROR locating story meta for psid" in data:
            raise exceptions.StoryDoesNotExist(self.url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        ## Title
        a = soup.find('a', href=re.compile(r'\?psid='+self.story.getMetadata('storyId')))
        self.story.setMetadata('title',stripHTML(a))
        ## javascript:if (confirm('Please note. This story may contain adult themes. By clicking here you are stating that you are over 17. Click cancel if you do not meet this requirement.')) location = '?psid=290995'
        if "This story may contain adult themes." in a['href'] and not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)


        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?showuid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        ## hpcom doesn't give us total words--but it does give
        ## us words/chapter.  I'd rather add than fetch and
        ## parse another page.
        words=0
        for tr in soup.find('table',{'class':'text'}).findAll('tr'):
            tdstr = tr.findAll('td')[2].string
            if tdstr and tdstr.isdigit():
                words+=int(tdstr)
        self.story.setMetadata('numWords',unicode(words))

        # Find the chapters:
        tablelist = soup.find('table',{'class':'text'})
        for chapter in tablelist.findAll('a', href=re.compile(r'\?chapterid=\d+')):
            #javascript:if (confirm('Please note. This story may contain adult themes. By clicking here you are stating that you are over 17. Click cancel if you do not meet this requirement.')) location = '?chapterid=433441&i=1'
            # just in case there's tags, like <i> in chapter titles.
            chpt=re.sub(r'^.*?(\?chapterid=\d+).*?',r'\1',chapter['href'])
            self.chapterUrls.append((stripHTML(chapter),'https://'+self.host+'/viewstory.php'+chpt))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## Finding the metadata is a bit of a pain.  Desc is the only thing this color.
        desctable= soup.find('table',{'bgcolor':'#f0e8e8'})
        self.setDescription(url,desctable)
        #self.story.setMetadata('description',stripHTML(desctable))

        ## Finding the metadata is a bit of a pain.  Most of the meta
        ## data is in a center.table without a bgcolor.
        #for center in soup.findAll('center'):
        table = soup.find('table',{'class':'storymaininfo'})
        if table:
            metastr = stripHTML(unicode(table)).replace('\n',' ').replace('\t',' ')

            m = re.match(r".*?Status: Completed.*?",metastr)
            if m:
                self.story.setMetadata('status','Completed')
            else:
                self.story.setMetadata('status','In-Progress')

            m = re.match(r".*?Rating: (.+?)Story",metastr)
            if m:
                self.story.setMetadata('rating', m.group(1))

            m = re.match(r".*?Genre\(s\): (.+?) Era.*?",metastr)
            if m:
                for g in m.group(1).split(','):
                    self.story.addToList('genre',g)

            m = re.match(r".*?Characters: (.+?) Genre.*?",metastr)
            if m:
                for g in m.group(1).split(','):
                    self.story.addToList('characters',g)

            m = re.match(r".*?Pairings: (.+?) +Status",metastr)
            if m:
                for g in m.group(1).split(','):
                    self.story.addToList('ships',g)

            m = re.match(r".*?(Warnings|Advisory): (.+).*?",metastr)
            if m:
                for w in m.group(2).split(','):
                    if w != 'Now Warnings':
                        self.story.addToList('warnings',w)

            m = re.match(r".*?First Published: ([0-9\.]+).*?",metastr)
            if m:
                self.story.setMetadata('datePublished',makeDate(m.group(1), "%Y.%m.%d"))

            # Updated can have more than one space after it. <shrug>
            m = re.match(r".*?Last Updated: ([0-9\.]+).*?",metastr)
            if m:
                self.story.setMetadata('dateUpdated',makeDate(m.group(1), "%Y.%m.%d"))

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)

        try:
            # remove everything after here--the site's chapters break
            # the BS4 parser.
            data = data[:data.index('<script type="text/javascript" src="reviewjs.js">')]
        except:
            # some older stories don't have the code at the end that breaks things.
            pass
        
        soup = self.make_soup(data)

        div = soup.find('div', {'id' : 'fluidtext'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)

def getClass():
    return HarryPotterFanFictionComSiteAdapter

