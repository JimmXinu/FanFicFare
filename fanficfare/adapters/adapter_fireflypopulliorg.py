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
### Adapted by GComyn on December 15, 2016
###=================================================================================================
### I ran this through a linter, and formatted it as per the suggestions, hence some of the lines
### are "chopped"
###=================================================================================================
### I have started to use lines of # on the line just before a function so they are easier to find.
####################################################################################################
''' This adapter scrapes the metadata and chapter text from stories on firefly.populli.org '''
import logging
import re
import urllib2
import sys

from base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)


####################################################################################################
def getClass():
    return FireflyPopulliOrgSiteAdapter

####################################################################################################
class FireflyPopulliOrgSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.is_adult = False

        # normalized story URL.

        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('http://' + self.getSiteDomain() + '/archive/' +m.group('cat') +
             '/' + self.story.getMetadata('storyId') +'.shtml')
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        ## each adapter needs to have a unique abbreviation, whih is set here.
        self.story.setMetadata('siteabbrev', 'fga')

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
        return 'firefly.populli.org'

    ################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://" + cls.getSiteDomain() + "/archive/999/astoryname.shtml"

    ################################################################################################
    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain())+r'/archive/(?P<cat>\d+)/(?P<id>\S+)\.shtml'

    ################################################################################################
    def get_page(self, page):
        '''
        This will download the url from the web and return the data
        I'm using it since I call several places below, and this will
        cut down on the size of the file
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

        self.story.setMetadata('title', stripHTML(soup.find('h2')))

        # This site has the entire story on one page, so we will be using the normalized URL as
        # the chapterUrl and the Title as the chapter Title
        self.chapterUrls.append((self.story.getMetadata('title'), url))

        ## i would take this out, as it is not really needed, but the calibre plugin uses it,
        ## so it's staying
        self.story.setMetadata('numChapters', 1)

        # Find authorid and URL
        ## this site does not have dedicated pages for the authors, you have to use the searh engine.
        ## so that is what I will do. Some of the stories have multiple author names separated by
        ## commas or a colon. I'm going to take the first name as the author name, and use the rest
        ## as a coauthor site specific tag. I did it this way so we keep all of the information,
        ## because the author can be used in the filename, and if it's too long windows systems
        ## won't be able to use it.
        mdata = stripHTML(soup.find('a', href=re.compile('mailto')))
        if ':' in mdata:
            self.story.setMetadata('coauthor', ' '.join(mdata.split(':')[1:]).strip())
            mdata = mdata.split(':')[0]
        if ',' in mdata:
            self.story.setMetadata('coauthor', ', '.join(mdata.split(',')[1:]).strip())
            mdata = mdata.split(',')[0]
        
#        print mdata
#        self.story.getMetadata('coauthor')
#        sys.exit()
        self.story.setMetadata('authorId', mdata)
        self.story.setMetadata('author', mdata.title())

        # Some stories list multiple authors, but the search engine only uses 1 author, and since
        # we can't tell how many 'words' are in each name, I'm going to do a work around.
        author_name = mdata.split('  ')[0].strip()
        author_url = ('http://'+self.getSiteDomain()+'/cgi-bin/search.cgi?Author={}&SortBy=0'+
                      '&SortOrder=0&NumToList=0&FastSearch=0&ShortResults=0').format(author_name)
        story_found = False
        while not story_found:
            logger.debug('Getting author page: %s' % author_url)
            adata = self.get_page(author_url)
            if 'No stories found for your search choices.' in adata:
                author_name = ' '.join(author_name.split()[:-1])
                author_url = ('http://'+self.getSiteDomain(
                                    )+'/cgi-bin/search.cgi?Author={}&SortBy=0'+
                                        '&SortOrder=0&NumToList=0&FastSearch=0' +
                                        '&ShortResults=0').format(author_name)
                pass
            else:
                asoup = self.make_soup(adata)
                # Ok...this site does not have the stories encompassed by any sort of tag... so I have
                # to make it.
                stories = asoup.find_all('p', {'class':'search'})
                if stories:
                    for story in stories:
                        # There alot of nbsp's (non broken spaces) in here, so I'm going to remove them
                        # I'm also getting rid of the bold tags and the nextline characters to make it 
                        # easier to get the information below
                        story = repr(story).replace(b'\\xa0', '').replace('  ',' ').replace(
                            '<b>','').replace('</b>','').replace(r'\n','')
                        story = self.make_soup(story).find('p')
                        story_a = story.find('a')
                        title = self.story.getMetadata('title').split('-')[0].strip()
                        if story_a.get_text() == title:
                            story_found = True
                            break
                    if not story_found:
                        raise exceptions.StoryDoesNotExist(
                            "Could not find the story {} on the author's {} search page {}".format(
                                url, author_name, author_url))

        self.story.setMetadata('authorUrl', author_url)

        # The first element is the author, which we already have, so I'm going to drop it.
        # Some prequel and sequel have links, so we are going to process them here, and get the
        # series at the same time, then catch those that don't have links below
        links = story.find_all('a')
        for link in links:
            label = link.previousSibling.strip()
            if label == 'Series Title:':
                ## there is no way to tell which number of the series the story is, so we won't
                # put a number
                series_url = 'http://'+self.getSiteDomain()+'/'+link['href']
                self.story.setMetadata('series', link.get_text())
                self.story.setMetadata('seriesUrl', series_url)
            elif label == 'Prequel to:':
                value = link.string + ' (' + 'http://'+self.getSiteDomain()+link['href'] + ')'
                self.story.setMetadata('prequelto', value)
            elif label == 'Sequel to:':
                value = link.string + ' (' + 'http://'+self.getSiteDomain()+link['href'] + ')'
                self.story.setMetadata('sequelto', value)

        # Some stories have alot of text in the "summary", and I've tried to keep down on creating
        # new metadata from here, so I'm going to grab some, but the rest will be lumped into the
        # summary metadata.
        summary = ''
        mdatas = story.find_all('br')
        for mdata in mdatas:
            meta = mdata.nextSibling.string
            if meta:
                # some of the "sentences" have a colon in them, but are not actually labels... so
                # I'm checking to see if the colon is within the first 20 characters, and taking
                # that as a label... otherwise, it will be added to the summary section below. I've
                # decided that the entire section will be put into the summary section, unless it
                # has specific labels
                if meta.find(':') > 0 and meta.find(':') < 20:
                    label = meta.split(':', 2)[0].strip().lower()
                    value = meta[len(label)+1:].strip()
                else:
                    label = meta.string
                    value = ''
                if (label == 'series title' or label == 'author' or label == '[' or
                    label == 'prequel to'):
                    # we've either already got this or we don't want it so we'll pass
                    ## I'm handling it here, to get it out of the way for the rest of the code since
                    # anything not captured is put into the summary
                    pass
                elif label == 'details':
                    # for the details section, none of this is labeled, and some stories can have
                    # less than others, so I have to check what each is to determine where to put
                    # it.
                    for val in value.split('|'):
                        val = val.strip()
                        if len(val) == 0:
                            # we don't need the ones that don't have anything in it.
                            pass
                        elif val in ['Series', 'Standalone', 'Work-In-Progress']:
                            self.story.setMetadata('storytype', val)
                        elif val in ['G', 'NC-17', 'PG', 'PG-13', 'R']:
                            self.story.setMetadata('rating', val)
                        elif val.split()[0].replace(',','') in ['*slash*', 'gen', 'het']:
                            self.story.setMetadata('genre', val)
                        elif val[-1] == 'k':
                            self.story.setMetadata('size', val)
                        elif len(val) > 0:
                            # There is no update date, so I'm putting the date in both
                            self.story.setMetadata('datePublished',makeDate(val, self.dateformat))
                            self.story.setMetadata('dateUpdated',makeDate(val, self.dateformat))
                        else:
                            ## This should catch anything else, and shouldn't ever really be gotten
                            # to, but I'm going to have it print out in the debugger, just in case
                            logger.debug('Metadata not caught: %s' % str(meta))
                            zzzzzzzz = 0
                elif label == 'characters':
                    self.story.setMetadata('characters', value)
                elif label == 'pairings':
                    self.story.setMetadata('ships', value)
                elif label == 'warnings' or label == '[eta] warning':
                    self.story.setMetadata('warnings', value)
                elif label == 'sequel to':
                    self.story.setMetadata('sequelto', value)
                elif label == 'disclaimer':
                    self.story.setMetadata('disclaimer', value)
                elif label == 'spoilers':
                    self.story.setMetadata('spoilers', value)
                elif label == 'crossover with':
                    self.story.addToList('category', value)
                elif label == 'summary':
                    summary += value + '<br/>'
                else:
                    ## since this is not really a labled string, I'm adding the original string to
                    # the summary. This may cause some of the sentences from the other site specific
                    # labels to be separated, but this is the only way I can figure out how to do
                    # this, at this time.
                    summary += meta.string + '<br/>'

        self.setDescription(url, summary)

        # since this is the only "chapter" that will be retrieved, I'm going to save the soup here
        # so the getChapterText function doesn't have to use more bandwidth to get it again
        self.html = soup

    ################################################################################################
    def getChapterText(self, url):

        logger.debug('Using the html retrieved previously from: %s' % url)

        soup = self.html

        story = soup.find('blockquote')

        if None == story:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        ## now that we have the story, there needs to be a little cleanup before we send it to the
        # writers. Some of them really need editing to be cleaned up
        ## I am converting the text to raw unicode, then removing the <blockquote>, then removing
        # the end  of the section, which has alot of extraneous things, then adding my own div
        # wrapper, recreating the soup, then getting that div from the soup again, before sending to
        # the writers.
        story = repr(story).replace(b'\\xa0', '').replace('  ',' ').replace(r'\n','').strip()
        story = story[12:]
        story = story[:story.find('<p align="center" class="comments">Please <')]
        story = '<div class="chaptertext">' + story + '</div>'
        story = self.make_soup(story).find('div', {'class':'chaptertext'})

        return self.utf8FromSoup(url, story)
