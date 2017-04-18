#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2017 FanFicFare team
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

import logging
import json
import re
import sys  # ## used for debug purposes
import time
import urllib2
import datetime

from base_adapter import BaseSiteAdapter, makeDate

from .. import exceptions as exceptions
from ..htmlcleanup import stripHTML

logger = logging.getLogger(__name__)

####################################################################################################
def getClass():
    return WWWWebNovelComAdapter


####################################################################################################
class WWWWebNovelComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult = False

        # get storyId from url
        # http://gravitytales.com/novel/a-dragons-curiosity
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/')[2])

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
        return "http://"+cls.getSiteDomain()+"/novel/[storyId]"

####################################################################################################
    def getSiteURLPattern(self):
        return r"http://"+re.escape(self.getSiteDomain())+r"/novel/*(?P<id>[^/]+)"

####################################################################################################
    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        url = self.url

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist('Error 404: {0}'.format(self.url))
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## This is the block that holds the metadata
        bookdetails = soup.find('div', {'id':'contentElement'})

        ## Title
        title = bookdetails.h3
        for tag in title.find_all('span'):
            tag.extract()
        self.story.setMetadata('title',stripHTML(title))

        ## There could be 2 authors listed... probably the "translator" and the actual author.
        ## I'll get the 'author' from both sections, if there are 2.
        author = stripHTML(bookdetails.h4)
        self.story.setMetadata('author', author)
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', url)

        # Find authorid and URL from... author url.
        bookdesc = bookdetails.find('div', {'class':'desc'})
        addtosys = False
        paras = bookdesc.find_all()
        for para in paras:
            parat = stripHTML(para)
            if parat[:7] == 'Author:' and unicode(para)[:3] == '<p>':
                author2 = parat.replace('Author:', '').strip()
                if len(self.story.getMetadata('author')) != 0:
                    author = self.story.getMetadata('author') + ' [' + author2 + ']'
                else:
                    author = author2
                self.story.setMetadata('author', author)
                self.story.setMetadata('authorId', author)
                ## There is no authorUrl for this site, so I'm setting it to the story url
                ## otherwise it defaults to the file location
                self.story.setMetadata('authorUrl', url)
            elif parat[:6] == 'Title:' and unicode(para)[:3] == '<p>':
                if b'\\xa0' in repr(parat):
                    title = parat[7:]
                else:
                    title = parat[6:]
                ## Doing this incase the user is doing a partial download
                title_orig = self.story.getMetadata('title')
                if '(Ch' in title_orig:
                    title_orig = title_orig[:title_orig.index('(Ch')].strip()
                self.story.setMetadata('title', title_orig + ' {' + title + '}')
            elif parat[:7] == 'Genres:' and unicode(para)[:3] == '<p>':
                genres = parat[8:].split(', ')
                for genre in genres:
                    self.story.addToList('genre', genre)
            elif parat[:11] == 'Translator:' and unicode(para)[:3] == '<p>':
                self.story.setMetadata('translator', parat.replace('Translator:', '').strip())
            elif parat[:7] == 'Status:' and unicode(para)[:3] == '<p>':
                status = parat[8:].strip()
                self.story.setMetadata('status', status)
            elif parat[:8] == 'Synopsis':
                if unicode(para)[:3] == '<p>':
                    # This is so it will be only put into the synopsis once for the paragraph
                    addtosys = True
                    synopsis = unicode(para)
            elif addtosys and unicode(para)[:4] != '<div':
                if len(unicode(para)) != 7:
                    ## this will only add those paragraphs that have content
                    synopsis += ' ' + unicode(para)

        if not self.getConfig('keep_summary_html'):
            synopsis = stripHTML(synopsis)

        self.setDescription(url, unicode(synopsis))

        if get_cover:
            cover_meta = soup.find('div', {'id':'coverImg'})
            cover_url = cover_meta['style'].replace('background-image: url(', '').replace(');', '')
            self.setCoverImage(url, cover_url)

        ## Getting the ChapterUrls
        ## the chapter list is script generated, so we have to use JSON to get them
        for script in soup.find_all('script'):
            scriptt = unicode(script)
            if 'ChapterGroupList' in scriptt:
                scriptt = scriptt[scriptt.index('novelId')+8:]
                scriptt = scriptt[:scriptt.index(',')].strip()
                mchaplist = self._fetchUrl('http://'+self.getSiteDomain()+'/api/novels/chaptergroups/'+scriptt)
                mchaplistj = json.loads(mchaplist)
                for mchapg in mchaplistj:
                    gchaplist = self._fetchUrl('http://'+self.getSiteDomain()+'/api/novels/chaptergroup/'+unicode(mchapg['ChapterGroupId']))
                    gchaplistj = json.loads(gchaplist)
                    for chap in gchaplistj:
                        chaptitle = chap['Name']
                        chapUrl = url + '/' + chap['Slug']
                        self.chapterUrls.append((chaptitle,chapUrl))
                self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## There are no published or updated dates listed on this site. I am arbitrarily setting
        ## these dates to the packaged date for now. If anyone else has an idea of how to get
        ## the original dates, please let me know [GComyn]
        ### I'd like to use the original date of the file, if this is an update, but I'm not proficient
        ### enough with programming to get it at this time. [GComyn]
        self.story.setMetadata('datePublished', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))
        self.story.setMetadata('dateUpdated', makeDate(datetime.datetime.now().strftime ("%Y-%m-%d"), "%Y-%m-%d"))


    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
		
        data = self._fetchUrl(url)
        html = self.make_soup(data)

        story = html.find('div', {'id':'chapterContent'})
			
        if story == None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,story)
