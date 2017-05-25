# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2017 FanFicFare team
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
#############################################################################
### Adapted by GComyn
### Original - November 23, 2016
###     adapted from adapter_efpfanficnet.py
#############################################################################
###   Updated November 25, 2016
###     Added another Metadata item in 'authorinfo'
###     Fixed the Metadata processing to take into account that some of the
###         stories have the authorinfo div, and to make it more systematic
#############################################################################
import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return WWWArea52HKHNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class WWWArea52HKHNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # Getting the storyId from url - http://www.area52hkh.net/[Folder]/[AuthorID]/[STORYID].php
        # I'm setting these variables here, because I use them later.
        self.folder = self.parsedUrl.path.split('/',)[1]
        self.authorId = self.parsedUrl.path.split('/',)[2]
        self.storyId = self.parsedUrl.path.split('/',)[3].replace('.php','').replace('.htm','').replace('.html','')
        self.extension = self.parsedUrl.path.split('.')[1]

        self.story.setMetadata('storyId', self.storyId)
        self.story.setMetadata('authorId',self.authorId)

        # normalized story URL.
        self._setURL('http://{0}/{1}/{2}/{3}.{4}'.format(self.getSiteDomain(),
                                                         self.folder,
                                                         self.story.getMetadata('authorId'),
                                                         self.story.getMetadata('storyId'),
                                                         self.extension))


        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','a52hkh')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.area52hkh.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://www.area52hkh.net/folder/author/astoryname.php"

    def getSiteURLPattern(self):
#        return r"http(s)?://www\.lushstories\.com/stories/(?P<category>[^/]+)/(?P<id>\S+)\.aspx"
        return r"http://www\.area52hkh\.net/as([a-z])/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)\.(php|htm|html)"
#        return r"http://www\.area52hkh\.net/as([a-z])/(?P<author>[^/]+)/([a-zA-Z0-9_-]+)\.php"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)

        # Now go hunting for all the meta data and the chapter list.

        ## Title and Series
        if self.extension == 'htm':
            raise exceptions.StoryDoesNotExist('This story is in a format that has not been coded yet.')

        elif self.extension == 'php':
            a = soup.find('h1')
            self.story.setMetadata('title',stripHTML(a))

            # Find authorid and URL from... author url.
            a = soup.find('a', href=re.compile(r"/author.php\?name=\S+"))
            self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
            self.story.setMetadata('author',a.string)

            # There is only one 'chapter' for each story, so we go with the self.url
            # and the title of the story for the heading
            self.chapterUrls.append((self.story.getMetadata('title'),url))

            self.story.setMetadata('numChapters',len(self.chapterUrls))

            storya = None
            authsoup = None
            storyblock = None
            authurl = self.story.getMetadata('authorUrl')

            ## author can have more than one page of stories.

            while storyblock == None:
            ## Here is a sample of one of the storyblocks
                #<div class="story">
                #<p class="title"><a href="/[folder]/[author]/[story].php" target="story">Story Title</a> &nbsp;&nbsp;&nbsp;<i>Part:</i> 1/3 of Series Title</p>
                #<table>
                #    <tr>
                #        <td class="image"><img src="/_images/show_s.gif" class="icon" alt="SG1" title="SG1"><br></td>
                #        <td class="detail">
                #            <i>Date Archived:</i> [Published Date]<br>
                #            <i>Pairing:</i> [Ships]<br>
                #            <i>Categories:</i> [Categories]<br>
                #            <i>Season/Episode:</i>[Season]
                #        </td>
                #        <td class="detail">
                #            <i>Size:</i> [Size]  <br>
                #            <img src="/_images/info.gif" class="icon" alt="More Info" title="More Info" onmouseover="swap(12575,'block');" onmouseout="swap(12575,'none');">
                #            <div class="info" id="i12575">
                #                [[[Text Written here]]]
                #            </div><br>
                #            <i>Rating:</i> [Rating]<br>
                #            <i>Warnings:</i> [warnings]<br>
                #            <i>Spoilers:</i> [spoilers]
                #        </td>
                #    </tr>
                #</table>
                #<p class="summary"><i>Summary:</i> [Summary]</p>
                #</div>

                # no storya, but do have authsoup--we're looping on author pages.
                if authsoup != None:
                    # last author link with offset should be the 'Next' link.
                    nextpage = authsoup.find('div',{'id':'links'}).find('a',{'title':'Next'})
                    authurl = u'http://%s/%s' % ( self.getSiteDomain(), nextpage['href'] )

                # Need author page for most of the metadata.
                logger.debug("fetching author page: (%s)"%authurl)
                authsoup = self.make_soup(self._fetchUrl(authurl))

                storyas = authsoup.findAll('a', href=re.compile(r'/'+self.folder+'/'+self.story.getMetadata('authorId')+'/'+self.story.getMetadata('storyId')+'.php'))
                for storya in storyas:
                    storyblock = storya.findParent('div',{'class':'story'})
                    if storyblock != None:
                        continue

            #checking to see if it is part of a series/bigger story
            series = storyblock.find('p',{'class':'title'})

            #Some storyblocks have images, which interfers with the retreival of the metadata, so I
            # am going to remove it.
            for tag in storyblock.find_all('img'):
                tag.extract()

            #Remove the title link, since we already have the title above
            series.find('a').extract()

            ## I've seen a non-breaking space in some of the storyblocks
            ## so we are going to remove them.
            series =  stripHTML(str(series.renderContents()).replace(b"\xc2\xa0",'')).strip()
            if len(series) > 0:
                self.story.setMetadata('series',series)

            ## Now we get the rest of the metadata
            ### some details have an imbedded div for extra info from the author
            ### this is being extracted, and put into a Metadata item called 'authorinfo'
            infodiv = storyblock.find('div',{'class':'info'})
            if infodiv != None:
                self.story.setMetadata('authorinfo',stripHTML(infodiv))
                infodiv.extract()

            details = storyblock.findAll('i')
            for detail in details:
                detail_text = stripHTML(detail)
                value = detail.nextSibling
                value_text = value.string.strip()
                if 'Date Archived' in detail_text:
                    self.story.setMetadata('datePublished', makeDate(value_text, self.dateformat))
                    self.story.setMetadata('dateUpdated', makeDate(value_text, self.dateformat))
                elif 'Pairing'  in detail_text:
                    self.story.setMetadata('ships', value_text)
                elif 'Categories'  in detail_text:
                    self.story.setMetadata('category',value_text)
                elif 'Season/Episode'  in detail_text:
                    self.story.setMetadata('season',value_text)
                elif 'Size'  in detail_text:
                    self.story.setMetadata('size',value_text)
                elif 'Rating'  in detail_text:
                    self.story.setMetadata('rating',value_text)
                elif 'Warnings'  in detail_text:
                    self.story.setMetadata('warnings',value_text)
                elif 'Spoilers'  in detail_text:
                    if value_text != 'None':
                        self.story.setMetadata('spoilers',value_text)
                elif 'Summary' in detail_text:
                    if not self.getConfig("keep_summary_html"):
                        value = stripHTML(value).replace('Summary:','').strip()
                    else:
                        value = str(value).replace('<i>Summary:</i>','').strip()
                    self.setDescription(url, value)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'all'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # removing the headers
        for tag in div.findAll('h1') + div.findAll('h2'):
            tag.extract()

        # removing the info paragraph
        for tag in div.findAll("p",{'id':'info'}):
            tag.extract()

        # removing the aright paragraph.
        #<p class="aright">
        for tag in div.findAll("p",{'class':'aright'}):
            tag.extract()

        # removing the first link, which is a link to the main page of the site.
        tag = div.find('a')
        tag.extract()

        return self.utf8FromSoup(url,div)
