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
####################################################################################################
# Adapted by GComyn - December 06, 2016
# Updated on December 18, 2016 - formatting from linter
# Updated on January 07, 2017 - fixed metadata capturing after Jimm fixed the UnidecodeError problem
####################################################################################################

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions
from bs4 import Comment, BeautifulSoup

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError
from ..six.moves.urllib.parse import quote

from .base_adapter import BaseSiteAdapter,  makeDate

####################################################################################################
def getClass():
    '''This function is called by the downloader in all adapter_*.py files in this dir to register
    the adapter class. So it needs to be updated to reflect the class below it. That, plus
    getSiteDomain() take care of 'Registering'. '''
    return WWWLushStoriesComAdapter # XXX

####################################################################################################
class WWWLushStoriesComAdapter(BaseSiteAdapter): # XXX
    ''' Class name has to be unique.  Our convention is camel case the sitename with Adapter at the
    end. www is skipped. '''

    ################################################################################################
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        # This is an Adult site, so we are going to initialize the is_adult to false, then check in
        # the config section to make sure it is set.
        self.is_adult=False

        # get storyId from url
        storyId = self.parsedUrl.path.split('/')[3].replace('.aspx','')
        if '%' not in storyId:
            ## assume already escaped if contains %.  Assume needs escaping if it doesn't.
            try:
                storyId = quote(storyId)
            except KeyError:
                ## string from calibre is utf8, but lushstories.com
                ## expects extended chars to be in latin1 / iso-8859-1
                ## rather than utf8.
                storyId = quote(storyId.encode("iso-8859-1"))

        self.story.setMetadata('storyId',storyId)

        ## This site has the category as part of the url, so to normalize the url below, we get it
        ## here
        self.cat = self.parsedUrl.path.split('/')[2]

        # normalized story URL.
        # XXX Most sites don't have the /fanfic part.  Replace all to remove it usually.
        self._setURL('https://' + self.getSiteDomain() + '/stories/' + self.cat + '/' +
                     self.story.getMetadata('storyId') + '.aspx')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','lush') # XXX

        # The date format will vary from site to site.
        # The web page below shows the templates to get the correct format
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %b %Y" # XXX

        # since the 'story' is one page, I am going to set the variable to hold the soup from the
        # story here
        self.html = ''

    ################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        ''' The site domain.  Does have www here, if it uses it. '''
        return 'www.lushstories.com' # XXX

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(self):
        return "https://"+self.getSiteDomain()+"/stories/category/astoryname.aspx"

    ################################################################################################
    def getSiteURLPattern(self):
        return r"http(s)?://www\.lushstories\.com/stories/(?P<category>[^/]+)/(?P<id>.+?)\.aspx"

    ################################################################################################
    def _fetchUrl(self,url,parameters=None,extrasleep=None,usecache=True):
        ## lushstories.com sets unescaped cookies with cause
        ## httplib.py to fail.
        self.get_configuration().set_cookiejar(self.get_configuration().get_empty_cookiejar())
        return BaseSiteAdapter._fetchUrl(self,url,
                                         parameters=parameters,
                                         extrasleep=extrasleep,
                                         usecache=usecache)
    ################################################################################################
    def get_page(self, page):
        '''
        This will download the url from the web and return the data. I'm using it since I call
        several places below, and this will cut down on the size of the file
        '''
        try:
            page_data = self._fetchUrl(page)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('404 error: {}'.format(page))
            else:
                raise e
        return page_data

    ################################################################################################
    def extractChapterUrlsAndMetadata(self):
        ''' Getting the chapter list and the meta data, plus 'is adult' checking. '''

        ## This is an adult site, so if they have not set their is_adult in the personal.ini, it will
        ## fail
        if not(self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(
                'This is an adult site. You need to be an adult in your location to access it.')

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_page(url)

        if "Something hasn't worked as we'd hoped" in data:
            raise exceptions.StoryDoesNotExist(self.getSiteDomain() +
                " says: Something Hasn't Worked As We'd Hoped")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a).title())

        cover_img = soup.find('img',{'class':'storycover'})
        if cover_img:
            self.setCoverImage(url,cover_img['src'])


        # Find authorid and URL from... author url.
        # (fetch multiple authors)
        a = soup.find('a',{'class':'avatar'})
        self.story.setMetadata('authorId',a['href'].split('/')[-1])
        self.story.setMetadata('authorUrl',a['href']+'/stories')
        a = soup.find('a',{'class':'author'})
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        # The stories on this site are all on one page, so we use the original URL
        self.add_chapter(self.story.getMetadata('title'),self.url)
        self.story.setMetadata('status', 'Completed')

        #Need to get the metadata from the author's story page
        # The try/except is still needed, because some author pages are no longer on the site, but
        # the story is, but the UnicodeDecodeError is no longer needed, so was removed
        authorurl = self.story.getMetadata('authorUrl')
        try:
            adata = self._fetchUrl(authorurl)
        except (HTTPError) as e:
            ## Can't get the author's page, so we use what is on the story page
            tags = soup.find('div',{'id':'storytags'}).find('a')
            if tags:
                for tag in tags:
                    self.story.addToList('eroticatags',stripHTML(tag))
            labels = soup.findAll('label')
            if labels:
                for label in labels:
                    if label.string == 'Added:':
                        self.story.setMetadata('datePublished', makeDate(label.nextSibling.string.strip(
                            ), self.dateformat))
                    elif label.string == 'Words:':
                        self.story.setMetadata('numWords',label.nextSibling.string.strip())

            summary = stripHTML(soup.find('div',{'class':'oneliner'}))
            if len(summary) == 0:
                summary = '>>>>>>>>>> No Summary Found <<<<<<<<<<'
            else:
                summary = stripHTML(summary)
            self.setDescription(url,summary)
            # since the 'story' is one page, I am going to save the soup here, so we can use iter
            # to get the story text in the getChapterText function, instead of having to retrieve
            # it again.
            self.html = soup
            return

        asoup = self.make_soup(adata)

        ## This is messy and hackish, I know, but at this time I can't think of a better way.
        summary=""
        for story in asoup.findAll('div',{'class':'entrycontent'}):
            for link in story.find_all('a'):
                if '/stories/' in link['href']:
                    linkh = quote(link['href'].encode('utf-8', 'ignore'))
                    linkh = linkh.replace('%3A', ':')
#                    print self.url
#                    print linkh
                    if self.url == linkh:
#                        print 'Got here'
                        for p in story.findAll('p'):
                            if 'Added:' in stripHTML(p):
                                for i, a in enumerate(p.findAll('a')):
                                    if i == 0:
                                        self.story.setMetadata('category',a.string)
                                    elif 'comments' in a['href']:
                                        pass
                                    else:
                                        self.story.addToList('eroticatags',a.string)
                                value = stripHTML(p)
                                for metad in value.split("|"):
                                    metad = metad.strip()
                                    if metad.startswith('Added'):
                                        value = metad.replace('Added:','').strip()
                                        self.story.setMetadata('datePublished', makeDate(
                                            value, self.dateformat))
                                    elif metad.startswith('Words'):
                                        self.story.setMetadata('numWords',metad.replace(
                                            'Words:','').strip())
                            else:
                                summary += stripHTML(p)+'. '
                        break
#                    print '---'
            if self.story.getMetadata('datePublished'):
                break
        if not self.story.getMetadata('datePublished'):
            raise exceptions.StoryDoesNotExist('Metadata No retrieved')
        self.setDescription(url,summary.strip())

        # since the 'story' is one page, I am going to save the soup here, so we can use iter
        # to get the story text in the getChapterText function, instead of having to retrieve
        # it again.
        self.html = soup

    ################################################################################################
    def getChapterText(self, url):
        ''' grab the text for an individual chapter. '''

        logger.debug('Using the html retrieved previously from: %s' % url)

        soup = self.html
        fullhtml = []
        oneliner = soup.find('div', {'class':'oneliner'})
        story = soup.find('div', {'class':'storycontent'})

        if story == None:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        if oneliner !=None:
            fullhtml.append(self.utf8FromSoup(url, oneliner))

        fullhtml.append(self.utf8FromSoup(url, story))

        return ''.join(fullhtml)
