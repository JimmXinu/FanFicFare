# -*- coding: utf-8 -*-
# Copyright 2018 FanFicFare team
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
### Adapted by GComyn on December 16, 2016
###=================================================================================================
### I ran this through a linter, and formatted it as per the suggestions, hence some of the lines
### are "chopped"
###=================================================================================================
### I have started to use lines of # on the line just before a function so they are easier to find.
####################################################################################################
from __future__ import absolute_import
''' This adapter scrapes the metadata and chapter text from stories on archive.shriftweb.org '''
import logging
import re
import sys

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)


####################################################################################################
def getClass():
    return BFAArchiveShriftwebOrgSiteAdapter

####################################################################################################
class BFAArchiveShriftwebOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.is_adult = False

        # normalized story URL.

        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/archive/' +m.group('cat') +
             '/' + self.story.getMetadata('storyId') +'.html')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        ## each adapter needs to have a unique abbreviation, whih is set here.
        self.story.setMetadata('siteabbrev', 'bfa')

        # The date format will vary from site to site.
        # The below website give the list of variables that can be used to formulate the
        # correct format
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%m/%d/%y"

        # This site has the entire story on one page, so I am initializing a variable to hold the
        # soup so that the getChaperText function doesn't have to use bandwidth to get it again.
        self.html = ''

    ################################################################################################
    @staticmethod
    def getSiteDomain():
        return 'archive.shriftweb.org'

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://" + cls.getSiteDomain() + "/archive/123/astoryname.html"

    ################################################################################################
    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r'/archive/(?P<cat>\d+)/(?P<id>\S+)\.html'

    ################################################################################################
    def get_page(self, page):
        '''
        This will download the url from the web and return the data
        I'm using it since I call several places below, and this will
        cut down on the size of the file
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

        url = self.url
        logger.debug("URL: " + url)

        data = self.get_page(url)

        # Since this is a site with the entire story on one page and there are no updates, I'm going
        # to set the status to complete.
        self.story.setMetadata('status', 'Completed')

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Title
        ## Some stories do not have the title in a tag that can be easily gotten.
        title = soup.find('h2')
        if not title:
            raise exceptions.StoryDoesNotExist('Cannot find title on the page {}'.format(url))

        rawtitle = stripHTML(title)
        self.story.setMetadata('title', rawtitle)

        # This site has the entire story on one page, so we will be using the normalized URL as
        # the chapterUrl and the Title as the chapter Title
        self.add_chapter(self.story.getMetadata('title'), url)

        ## i would take this out, as it is not really needed, but the calibre plugin uses it,
        ## so it's staying
        self.story.setMetadata('numChapters', 1)

        # Find authorid and URL
        ## this site does not have dedicated pages for the authors, you have to use the searh
        ## engine. so that is what I will do.
        mdata = stripHTML(soup.find('h2').find_next('a'))
        if not mdata:
            mdata = stripHTML(soup.find('a', href=re.compile('mailto')))
        elif '@' in mdata:
            mdata = mdata.split('@')[0]
        self.story.setMetadata('authorId', mdata)
        self.story.setMetadata('author', mdata.title())


        # Some stories list multiple authors, but the search engine only uses 1 author, and since
        # we can't tell how many 'words' are in each name, I'm going to do a work around.
        author_name = mdata.split('  ')[0].strip()
        author_url = ('http://'+self.getSiteDomain()+'/cgi-bin/search.cgi?Author={}&SortBy=0'+
                      '&SortOrder=0&NumToList=0&FastSearch=0&ShortResults=0').format(author_name)
        story_found = False
        while not story_found:
            asoup = self.make_soup(self.get_page(author_url))
            # Ok...this site does not have the stories encompassed by any sort of tag... so I have
            # to make it.
            stories_main = asoup.find('table', {'class':'content'}).find('td')
            if stories_main:
                if len(repr(stories_main).split('<b>',1)) == 1:
                    author_name = ' '.join(author_name.split()[:-1])
                    author_url = ('http://'+self.getSiteDomain(
                                      )+'/cgi-bin/search.cgi?Author={}&SortBy=0'+
                                          '&SortOrder=0&NumToList=0&FastSearch=0' +
                                          '&ShortResults=0').format(author_name)
                    pass
                else:
                    stories_main = u'<b>' + repr(stories_main).split('<b>',1)[1][:-5]
                    ## now that I have the stories in a format that I can manipulate, I'm going to
                    # split them up. The last 2 elements are not stories, so I a going to drop them.
                    stories = stories_main.replace('\\n','').split('<p>')[:-2]
                    for story in stories:
                        ## now I am going to turn this string back into a bs tag, removing the <b>
                        # tags for easier manipulation
                        story = '<div>' + story.replace('<b>', '').replace('</b>', '') + '</div>'
                        story = self.make_soup(story).find('div')
                        story_a = story.find('a')
                        ## some stories have special characters... need to fix them.
                        title = repr(rawtitle)[2:-1].replace('&amp;', '&')
                        if title in story_a.get_text():
                            story_found = True
                            break
                    if not story_found:
                        raise exceptions.StoryDoesNotExist(
                            "Could not find the story {} on the author's {} search page {}".format(
                                url, author_name, author_url))

        self.story.setMetadata('authorUrl', author_url)

        # The first element is the author, which we already have, so I'm going to drop it.
        mdatas = story.find_all('br')[1:]
        for mdata in mdatas:
            meta = mdata.nextSibling.string

            if meta:
                # This site doesn't seem to have any url links within the story listing (except for
                # the author and title, which we've already gotten), so I don't have to worry about
                # that.
                label = meta.split(':', 2)[0].strip().lower()
                value = meta[len(label)+1:].strip()
                if label == 'show':
                    # This site uses the show label for the category (as used on ffnet)
                    self.story.setMetadata('category', value)
                elif label == 'rating':
                    self.story.setMetadata('rating', value)
                elif label == 'category':
                    # This site uses the category for the genre (as used on ffnet)
                    self.story.setMetadata('genre', value)
                elif label == 'characters':
                    self.story.setMetadata('characters', value)
                elif label == 'pairings':
                    self.story.setMetadata('ships', value)
                elif label == 'summary':
                    self.setDescription(url, value)
                elif label == 'warnings':
                    self.story.setMetadata('warnings', value)
                elif label == 'archived on':
                    self.story.setMetadata('datePublished', makeDate(value, self.dateformat))
                else:
                    #There shouldn't be any other labels, but I'm putting this here to catch
                    # anything that might be missed
                    logger.debug('Missed metadata: %s' % meta)
            else:
                # there should always be something, but just in case, I'm going to print it out in
                # the debugger
                logger.debug('Missed metadata: %s' % mdata)


        # since this is the only "chapter" that will be retrieved, I'm going to save the soup here
        # so the getChapterText function doesn't have to use more bandwidth to get it again
        self.html = soup

    ################################################################################################
    def getChapterText(self, url):

        logger.debug('Using the html retrieved previously from: %s' % url)

        soup = self.html

        story = soup.find('body')

        if not story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        # the first center tag is the header for the story, which we have all the information for,
        # so we can drop it.
        story.find('center').extract()

        return self.utf8FromSoup(url, story)
