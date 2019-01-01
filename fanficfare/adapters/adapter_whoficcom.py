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

# Software: eFiction
from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

class WhoficComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','whof')
        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = '%Y.%m.%d'

    @staticmethod
    def getSiteDomain():
        return 'www.whofic.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?"+re.escape("://"+self.getSiteDomain()+"/viewstory.php?sid=")+"\d+$"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    def extractChapterUrlsAndMetadata(self):

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # fetch the first chapter.  From that we will:
        # - determine title, authorname, authorid
        # - get chapter list, if not one-shot.

        url = self.url+'&chapter=1'
        logger.debug("URL: "+url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            soup = self.make_soup(self._fetchUrl(url))
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # pull title(title) and author from the HTML title.
        title = stripHTML(soup.find('title'))
        logger.debug('Title: %s' % title)
        title = title.split('::')[1].strip()
        self.story.setMetadata('title',title.split(' by ')[0].strip())
        self.story.setMetadata('author',title.split(' by ')[1].strip())

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])

        # Find the chapter selector
        select = soup.find('select', { 'name' : 'chapter' } )

        if select is None:
            # no selector found, so it's a one-chapter story.
            self.add_chapter(self.story.getMetadata('title'),url)
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = self.url + "&chapter=%s" % o['value']
                # just in case there's tags, like <i> in chapter titles.
                title = "%s" % o
                title = re.sub(r'<[^>]+>','',title)
                self.add_chapter(title,url)


        ## Whofic.com puts none of the other meta data in the chapters
        ## or even the story chapter index page.  Need to scrape the
        ## author page to find it.

        logger.debug("Author URL: "+self.story.getMetadata('authorUrl'))
        soup = self.make_soup(self._fetchUrl(self.story.getMetadata('authorUrl'))) # normalize <br> tags to <br />
        # find this story in the list, parse it's metadata based on
        # lots of assumptions about the html, since there's little
        # tagging.
        # Found a story once that had the story URL in the desc for a
        # series on the same author's page.  Now using the reviews
        # link instead to find the appropriate metadata.  Also avoids
        # 'I am old enough' JS
        a = soup.find('a', href=re.compile(r'reviews.php\?sid='+self.story.getMetadata('storyId')))
        metadata = a.findParent('div')

        # <div class="storyBlock">
        # <p><strong><a href="javascript:if (confirm('I am old enough to read adult stories')) location = 'viewstory.php?sid=62517&warning=Adult'">Les Fleurs Du Mal</a></strong> by <a href="viewuser.php?uid=35616">JustMcShane</a>  [<a href="reviews.php?sid=62517">Reviews</a> - <a href="reviews.php?sid=62517">0</a>]<br />
        # An unexpected detour leads to the Doctor and Ace teaming up with the FBI to investigate a series of disturbingly specific floral-themed murders. But with Ace's increasingly strange dreams, a hyper-empathetic consultant who can't seem to empathize quite so well any more, and one Doctor Hannibal Lecter in the mix, the murders may be the least of their problems...</p>
        # <ul class="list-inline pipe">
        # 	<li class="list-inline-item small"><a href="#"><a href="categories.php?catid=7">Seventh Doctor</a></a></li>
        # 	<li class="list-inline-item small">Adult</li>
        # 	<li class="list-inline-item small">Explicit Violence, Swearing</li>
        # 	<li class="list-inline-item small">Action/Adventure, Crossover</li>
        # </ul>
        # <p class="small"><b>Characters:</b> Ace McShane, Other Character(s), The Doctor (7th)<br />
        # <b>Series:</b> None</p>
        # <ul class="list-inline pipe">
        # 	<li class="list-inline-item small"><b>Published:</b> 2018.12.24</li>
        # 	<li class="list-inline-item small"><b>Updated:</b> 2018.12.29</li>
        # 	<li class="list-inline-item small"><b>Chapters:</b> 2</li>
        # 	<li class="list-inline-item small"><b>Completed:</b> No</li>
        # 	<li class="list-inline-item small"><b>Word count:</b> 6363</li>
        # </ul>
        # </div>
        # logger.warn(metadata)

        cat_as = metadata.find_all('a', href=re.compile(r'categories.php'))
        for cat_a in cat_as:
            category = stripHTML(cat_a)
            self.story.addToList('category',category)
            # first part is category--whofic.com has categories Doctor
            # One-11, Torchwood, etc.  We're going to prepend any with
            # 'Doctor' or 'Era' (Multi-Era, Other Era) as 'Doctor
            # Who'.
            if 'Doctor' in category or 'Era' in category :
                self.story.addToList('category','Doctor Who')

        uls = metadata.find_all('ul')
        # first ul, category found by URL above, skip to second.
        lis = uls[0].find_all('li')
        v = stripHTML(lis[1])
        if v:
            self.story.setMetadata('rating',v)
        v = stripHTML(lis[2])
        if v and v != 'None': # skip when explicitly 'None'.
            self.story.extendList('warnings',v.split(', '))
        v = stripHTML(lis[3])
        if v:
            self.story.extendList('genre',v.split(', '))

        # Remove first ul list.
        uls[0].extract()

        # second ul list has titles.
        for li in uls[1].find_all('li'):
            (title,value) = stripHTML(li).split(':')
            if title=='Published':
                self.story.setMetadata('datePublished', makeDate(value, self.dateformat))
            if title=='Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, self.dateformat))
            if title=='Word count':
                self.story.setMetadata('numWords', value)
            if title=='Completed':
                if value=='Yes':
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

        # Remove second ul list.
        uls[1].extract()

        # Find Series name from series URL.
        a = metadata.find('a', href=re.compile(r"series.php\?seriesid=\d+"))
        if a != None:
            series_name = a.string
            series_url = 'https://'+self.host+'/'+a['href']
            try:
                seriessoup = self.make_soup(self._fetchUrl(series_url))
                storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
                i=1
                for a in storyas:
                    if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                        self.setSeries(series_name, i)
                        self.story.setMetadata('seriesUrl',series_url)
                        break
                    i+=1
            except:
                # I've changed it a little to put the series name and url in even if the page is no longer available [GComyn]
                self.setSeries(series_name, 0)
                self.story.setMetadata('seriesUrl',series_url)

        # logger.warn(metadata) #.find_all('p')

        ps = metadata.find_all('p')

        # first p is links and desc separated by <br>, can discard br
        # and everything before.
        br = ps[0].find('br')
        while br.previous_sibling:
            br.previous_sibling.extract()
        br.extract()
        ps[0].name='div' # switch to a div.
        self.setDescription(self.story.getMetadata('authorUrl'),ps[0])

        # second p is Characters & Series separated by <br>, series
        # above, can discard br and everything after.
        br = ps[1].find('br')
        while br.next_sibling:
            br.next_sibling.extract()
        br.extract()
        chars = stripHTML(ps[1]).split(':')[1]
        if chars != 'None':
            self.story.extendList('characters',chars.split(', '))

        # logger.warn(metadata)

    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))


        # hardly a great identifier, I know, but whofic really doesn't
        # give us anything better to work with.
        span = soup.find('span', {'style' : 'font-size: 100%;'})

        if None == span:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # chapter select at end of page included in span.
        for form in span.find_all('form'):
            form.extract()

        span.name='div'
        return self.utf8FromSoup(url,span)

def getClass():
    return WhoficComSiteAdapter

