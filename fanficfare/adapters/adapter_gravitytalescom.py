#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2018 FanFicFare team
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
## Adapted by GComyn on April 21, 2017
####################################################################################################

from __future__ import absolute_import
import logging
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    # If feedparser ever becomes an included dependency for FanFicFare
    import feedparser
except ImportError:
    try:
        # A version of feedparser is available in the Calibre plugin version
        from calibre.web.feeds import feedparser
    except ImportError:
        # logger.warn('No version of feedparser module available, falling back to naive published and updated date')
        feedparser = None

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML


####################################################################################################
def getClass():
    return GravityTalesComSiteAdapter


####################################################################################################
class GravityTalesComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult = False

        # get storyId from url
        # http://gravitytales.com/novel/a-dragons-curiosity
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/')[2])

        # normalized story URL.
        self._setURL("http://"+self.getSiteDomain()\
                         +"/novel/"+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','gtcom')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        ## There are no dates listed on this site, so am commenting this out
        #self.dateformat = "%Y-%b-%d"

####################################################################################################
    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'gravitytales.com'

####################################################################################################
    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/novel/a-story-name"

####################################################################################################
    def getSiteURLPattern(self):
        return r"http://"+re.escape(self.getSiteDomain())+r"/(novel|post)/*(?P<id>[^/]+)"

####################################################################################################
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        url = self.url

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## This is the block that holds the metadata
        bookdetails = soup.find('div', {'class':'main-content'})

        ## Title
        title = bookdetails.h3
        for tag in title.find_all('span'):
            tag.extract()
        self.story.setMetadata('title',stripHTML(title))

        author = stripHTML(bookdetails.h4)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', url)

        # Find authorid and URL from... author url.
        bookdesc = bookdetails.find('div', {'class':'desc'})
        addtosys = False
        paras = bookdesc.find_all()
        synopsis = ''
        for para in paras:
            parat = stripHTML(para)
            ## I had a section of code that took the author name from the list, and added it to
            ## the author name from the <h4>... and a section that took the title from the list,
            ## and added it to the title from the <h3>...
            ## but decided to remove them and let it be added to the synopsis.
            if parat[:7] == 'Genres:' and unicode(para)[:2] == '<p':
                genres = parat[8:].split(', ')
                for genre in genres:
                    self.story.addToList('genre', genre)
            elif parat[:11] == 'Translator:' and unicode(para)[:2] == '<p':
                self.story.setMetadata('translator', parat.replace('Translator:', '').strip())
            elif parat[:7] == 'Status:' and unicode(para)[:2] == '<p':
                status = parat[8:].strip()
                self.story.setMetadata('status', status)
            elif unicode(para)[:2] == '<p' or unicode(para)[:2] == '<h' or unicode(para)[:2] == '<u':
                synopsis += ' ' + unicode(para)

        if not self.getConfig('keep_summary_html'):
            synopsis = stripHTML(synopsis)

        while '<br/> <br/>' in synopsis:
            synopsis = synopsis.replace('<br/> <br/>', '<br/>')

        self.setDescription(url, unicode(synopsis))

        ## this is constantly being forbidden, so I'm commenting it out for now.
#        if get_cover:
#            cover_meta = soup.find('div', {'id':'coverImg'})
#            cover_url = cover_meta['style'].replace('background-image: url(', '').replace(');', '')
#            self.setCoverImage(url, cover_url)

        ## Getting the ChapterUrls
        ## fetch from separate chapters url.
        chap_url = self.story.getMetadata('storyUrl')+"/chapters"
        chap_soup = self.make_soup(self._fetchUrl(chap_url))
        found_chaps = {}
        for alink in chap_soup.find_all('a',href=re.compile(self.getSiteDomain())): # ignore anchor links
            ## Some stories have that same chapters in different sections
            if alink['href'] not in found_chaps:
                self.add_chapter(alink,alink['href'])
                found_chaps[alink['href']] = alink['href']

        if feedparser:
            # Parse published and updated date from latest RSS feed entry. The RSS feed urls seems to appear due to
            # some JavaScript on the page, so get the URL by mangling the URL (this is not very robust, but probably
            # good enough)
            rss_feed_url = url.replace('/novel/', '/feed/')
            feed = feedparser.parse(rss_feed_url)
            date_updated = datetime.fromtimestamp(
                time.mktime(feed.entries[0].published_parsed)) if feed.entries else datetime.now()
        else:
            # Fall back to the previous method of generating the published and update date...
            date_updated = datetime.now()

        # Since the original published date isn't available, we'll simply use the updated date
        self.story.setMetadata('datePublished', date_updated)
        self.story.setMetadata('dateUpdated', date_updated)

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        data = self._fetchUrl(url)
        html = self.make_soup(data)

        story = html.find('div', {'id':'chapterContent'})

        if story == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,story)
