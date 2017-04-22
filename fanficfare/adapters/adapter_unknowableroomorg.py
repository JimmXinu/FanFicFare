# -*- coding: utf-8 -*-

# Copyright 2017 FanFicFare team
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
####################################################################################################
### Adapted by GComyn on December 19, 2016
####################################################################################################
''' This adapter will download stories from the site unknowableroom.org '''
import logging
import re
import time
import urllib2
import sys

from base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

####################################################################################################
def getClass():
    return UnknowableRoomOrgSiteAdapter

####################################################################################################
class UnknowableRoomOrgSiteAdapter(BaseSiteAdapter):

    ################################################################################################
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','urorg')

        # 1252 is a superset of iso-8859-1.  Most sites that claim to be  iso-8859-1 (and some that
        # claim to be  utf8) are really windows-1252.
        self.decode = ["Windows-1252", "utf8", "iso-8859-1"] 

        # Setting the adult status to false initially
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[1])

        # normalized story URL.
        self._setURL('http://'+self.getSiteDomain()+'/'+self.story.getMetadata('storyId') + '/1')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"

    ################################################################################################
    @staticmethod
    def getSiteDomain():
        return 'unknowableroom.org'

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/1234/1"

    ################################################################################################
    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r"/\d+/\d"

    ################################################################################################
    def get_page(self, page):
        '''
        This will download the url from the web and return the data
        I'm using it since I call several pages below, and this will cut down
        on the size of the file
        '''
        try:
            page_data = self._fetchUrl(page)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(page))
            else:
                raise e
        return page_data

    ################################################################################################
    def extractChapterUrlsAndMetadata(self):

        ## There is no way to tell if a fic is complete or not, so we can't set the status, which
        # will default to 'Unknown'

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_page(url)

        if "<!DOCTYPE html" not in data:
            raise exceptions.StoryDoesNotExist(url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Find authorid and URL from... author url.
        a = soup.find('a', {'class':'user'})
        if a:
            self.story.setMetadata('authorId',a['href'].split('/')[-1])
            self.story.setMetadata('authorUrl','http://'+self.host+a['href']+'/fics')
            self.story.setMetadata('author',a.string)
        else:
            author = soup.find('h1').string
            author = author[author.rfind('by')+2:].strip()
            self.story.setMetadata('authorId', author)
            self.story.setMetadata('authorUrl', 'http://'+self.getSiteDomain())
            self.story.setMetadata('author', author)
            
        ## Title
        self.story.setMetadata('title',stripHTML(soup.find('h1')).replace(
            'by '+self.story.getMetadata('author'), '').strip())

        # Find the chapters:
        for chapter in soup.find('select').find_all('option', value=re.compile(
            '/'+self.story.getMetadata('storyId')+r'/\d+')):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+chapter['value']))

        ## One chapter stories do not have a listing for the chapters, so we have to check to make
        ## sure, and if there aren't any chapterUrls, we set it to the Url entered.
        if len(self.chapterUrls) == 0:
            self.chapterUrls.append((self.story.getMetadata('title'), url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        # Most of the metadata can be gotten from the story page, but it can all be gotten from the
        # author's fic page, so we are going to get it from there. Unless there is no author page,
        # then we have to use what we can get.
        if self.story.getMetadata('authorUrl') != 'http://'+self.getSiteDomain():
            adata = self.get_page(self.story.getMetadata('authorUrl'))
            asoup = self.make_soup(adata)

            story_found = False
            for story in asoup.find('ul', {'id':'fic_list'}).find_all('li'):
                if self.story.getMetadata('title') == stripHTML(story.a):
                    story_found = True
                    break
                else:
                    story_found = False
            
            if not story_found:
                raise exceptions.StoryDoesNotExist("Cannot find story '{}' on author's page '{}'".format(
                    url, self.story.getMetadata('authorUrl')))

            if story_found:
                self.setDescription(url, stripHTML(story.p).strip())

                # The metadata is contained in a <cite> tag, with only a bold tag and seperated by a
                # period (.).
                # It has 6 'elements'
                # 0 = Rating
                # 1 = chapters and words
                # 2 = Genre
                # 3 = Characters
                # 4 = Posted Date
                # 5 = Updated Date
                metad = stripHTML(story.cite).replace('.,', ',').split('.')
                self.story.setMetadata('rating',metad[0])
                self.story.setMetadata('numWords', metad[1].split()[2])
                self.story.setMetadata('genre',metad[2])
                self.story.setMetadata('characters',metad[3])
                # The dates have letters in them, so we have to remove them.
                date_pub = metad[4].replace('Created ','').replace('st,', ',').replace('nd,', ',').replace(
                    'rd,', ',').replace('th,', ',').strip()
                date_upd = metad[5].replace('Updated ','').replace('st,', ',').replace('nd,', ',').replace(
                    'rd,', ',').replace('th,', ',').strip()
                self.story.setMetadata('datePublished', makeDate(date_pub, self.dateformat))
                self.story.setMetadata('dateUpdated', makeDate(date_pub, self.dateformat))
#        else:

        if not self.story.getMetadata('rating'):
            # There was no author page, so we get what we can from the page
            self.setDescription(url, '>>>>>>>>>> No Summary Found <<<<<<<<<<')
            metad = soup.find('div', {'class':'info'})
            for mdata in metad.find_all('b'):
                if mdata.string == 'Rating:':
                    self.story.setMetadata('rating', mdata.next_sibling)
                elif mdata.string == 'Created:':
                    value = mdata.next_sibling.replace('st,', ',').replace('nd,', ',').replace(
                        'rd,', ',').replace('th,', ',').replace('.', '').strip()
                    self.story.setMetadata('datePublished', makeDate(value, self.dateformat))
                elif mdata.string == 'Updated:':
                    value = mdata.next_sibling.replace('st,', ',').replace('nd,', ',').replace(
                        'rd,', ',').replace('th,', ',').replace('.', '').strip()
                    self.story.setMetadata('dateUpdated', makeDate(value, self.dateformat))

        # I'm going to add the disclaimer 
        disclaimer = soup.find('strong', {'id':'disclaimer'})
        if disclaimer:
            self.story.setMetadata('disclaimer', stripHTML(disclaimer).replace(
                'Disclaimer:', '').strip())

    ################################################################################################
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        data = self.get_page(url)

        soup = self.make_soup(data)

        story = soup.find('div', {'id' : 'fic'})

        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        ## I'm going to take the attributes off all of the tags
        ## because they usually refer to the style that we removed above.
        for tag in story.findAll('p')+story.findAll('span'):
            tag.attrs = None

        return self.utf8FromSoup(url, story)
