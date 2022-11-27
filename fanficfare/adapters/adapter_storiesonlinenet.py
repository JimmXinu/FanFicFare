# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2020 FanFicFare team
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

from __future__ import absolute_import
import logging
import random

logger = logging.getLogger(__name__)
import re
from datetime import datetime
#
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six.moves.urllib.parse import urlparse, urlunparse
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return StoriesOnlineNetAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class StoriesOnlineNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        # logger.debug("StoriesOnlineNetAdapter.__init__ - url='%s'" % url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            if '-'  in self.story.getMetadata('storyId'):
                self.story.setMetadata('storyId',self.story.getMetadata('storyId').split('-')[0])
                logger.debug("storyId date removed:%s\n"%self.story.getMetadata('storyId'))

            # chapter URLs don't have the same embedded title in URL as story.
            title = ""
            if not m.group('chapter') and m.group('title'):
                title = m.group('title')
            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() + '/s/'+self.story.getMetadata('storyId')+title)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev',self.getSiteAbbrev())

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d %I:%M:%S %p"

    @classmethod
    def getSiteAbbrev(cls):
        return 'strol'

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'storiesonline.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://"+cls.getSiteDomain()+"/s/1234 http://"+cls.getSiteDomain()+"/s/1234:4010 https://"+cls.getSiteDomain()+"/s/1234 https://"+cls.getSiteDomain()+"/s/1234:4010"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain())+r"/(s|library)/(storyInfo.php\?id=)?(?P<id>\d+)(?P<chapter>:\d+)?(?P<title>/.+)?((;\d+)?$|(:i)?$)?"

    @classmethod
    def getTheme(cls):
        # preferred theme
        return "Classic"

    def needToLoginCheck(self, data):
        return 'Free Registration' in data \
                or "Invalid Password!" in data \
                or "Invalid User Name!" in data \
                or "Log In" in data \
                or "Access to unlinked chapters requires" in data \
                or "Log in to Storiesonline" in data \
                or "WLPC log in System" in data

    def performLogin(self, url):

        if self.password:
            username = self.username
            password = self.password
        else:
            username = self.getConfig("username")
            password = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/sol-secure/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                             username))

        if not username or not password:
            logger.info("Login Required for URL %s" % loginUrl)
            raise exceptions.FailedToLogin(url,username)

        ## Double POST requirement has been removed as of Oct 2021

        (data,useurl) = self.get_request_redirected(loginUrl,usecache=False)
        # logger.debug(data)
        if not self.needToLoginCheck(data):
            ## hitting login URL reminds system we're logged in?
            logger.debug("don't need to login")
            return
        soup = self.make_soup(data)
        params = {}
        params['email'] = username
        postAction = soup.find('form')['action']

        parsedUrl = urlparse(useurl)
        postUrl = urlunparse((parsedUrl.scheme,
                              parsedUrl.netloc,
                              postAction,
                              '','',''))
        params['password'] = password
        params['cmd'] = 'LOGIN'

        data = self.post_request(postUrl,params,usecache=False)

        if self.needToLoginCheck(data):
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              username))
            raise exceptions.FailedToLogin(url,username)

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        url = self.url
        logger.debug("URL: "+url)

        ## Hit story URL to check for changed title part -- if the
        ## title has changed or (more likely?) the ID number has
        ## been reassigned to a different title, this will 404
        ## Note that the site ignores extra letters, so if the real
        ## URL is /story-title then /story-titleaaaa will still work.
        try:
            data = self.get_request(url)
        except exceptions.HTTPErrorFFF as e:
            if e.status_code in (401, 403, 410):
                data = 'Log In' # to trip needToLoginCheck
            elif e.status_code == 404:
                raise exceptions.FailedToDownload("Page Not Found - Story ID Reused? (%s)" % url)
            else:
                raise e
        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self.get_request(url,usecache=False)

        ## Premium account might redirect to a chapter, while regular
        ## account doesn't redirect to the URL with embedded /story-title
        ## So pull url from <a href="/s/000/story-title" rel="bookmark">
        ## regardless.
        soup = self.make_soup(data)
        a = soup.find('a',rel="bookmark")
        url = 'https://'+self.host+a['href']

        ## Premium has "?ind=1" to force index.
        ## May not be needed w/o premium
        ## used to be :i
        if "?ind=1" not in url:
            url = url+"?ind=1"
        logger.info("use url: "+url)
        data = self.get_request(url)
        ## To include /title-in-url, but not ind=1
        self._setURL(url.replace("?ind=1",""))
        # logger.debug(data)

        if "Access denied. This story has not been validated by the adminstrators of this site." in data:
            raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")
        elif "Error! The story you're trying to access is being filtered by your choice of contents filtering." in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Error! The story you're trying to access is being filtered by your choice of contents filtering.")
        elif "Error! Daily Limit Reached" in data or "Sorry! You have reached your daily limit of" in data:
            raise exceptions.FailedToDownload(self.getSiteDomain() +" says: Error! Daily Limit Reached")

        soup = self.make_soup(data)
        # logger.debug(data)

        ## Title
        a = soup.find('h1')
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.  Sometimes in top,
        # other times in footer.
        authfrom = soup.find('div', {'id':'top-header'})
        if authfrom is None or 'author' not in str(authfrom):
            authfrom = soup.find('footer')
        alist = authfrom.findAll('a', {'rel' : 'author'})
        for a in alist:
            self.story.addToList('authorId',a['href'].split('/')[2])
            self.story.addToList('authorUrl','https://'+self.host+a['href'])
            self.story.addToList('author',stripHTML(a).replace("'s Page",""))

        # The rest of the metadata is within the article tag.
        soup = soup.find('article')

        # Find the chapters:
        chapters = soup.findAll('a', href=re.compile(r'^/s/'+self.story.getMetadata('storyId')+r":\d+(/.*)?$"))
        if len(chapters) != 0:
            logger.debug("Number of chapters: {0}".format(len(chapters)))
            for chapter in chapters:
                # just in case there's tags, like <i> in chapter titles.
                self.add_chapter(chapter,'https://'+self.host+chapter['href'])
        else:
            self.add_chapter(self.story.getMetadata('title'),'https://'+self.host+'/s/'+self.story.getMetadata('storyId'))


        self.getStoryMetadataFromAuthorPage()

        # Some books have a cover in the index page.
        # Samples are:
        #     https://storiesonline.net/s/11999
        #     https://storiesonline.net/s/10823
        if get_cover:
            # logger.debug("Looking for the cover image...")
            cover_url = ""
            img = soup.find('img')
            if img:
                cover_url=img['src']
            # logger.debug("cover_url: %s"%cover_url)
            if cover_url:
                self.setCoverImage(url,cover_url)

        # Remove all the metadata elements to leave and preamble text. This is usually
        # a notice or a forward.
        if self.num_chapters() > 1:
            header = soup.find('header')
            header.extract()
        else:
            soup = soup.find('header')
        # Remove some tags based on their class or id
        elements_to_remove = ['#det-link', '#s-details', '#index-list', '#s-title', '#s-auth', '.copy']
        if not self.getConfig('include_images'):
            elements_to_remove.append('img')
        for element_name in elements_to_remove:
            elements = soup.select(element_name)
            for element in elements:
                element.extract()
        if len(soup.contents ) > 0 and (len(soup.text.strip()) > 0 or len(soup.find_all('img')) > 0):
            self.story.setMetadata('notice', self.utf8FromSoup(url, soup))


    def getStoryMetadataFromAuthorPage(self):
        # surprisingly, the detailed page does not give enough details, so go to author's page
        story_row = self.findStoryRow()

        if story_row.name == 'tr':
            # classic theme
            self.has_universes = False

            title_cell = story_row.find('td', {'class' : 'lc2'})
            for cat in title_cell.findAll('div', {'class' : 'typediv'}):
                self.story.addToList('genre',cat.text)

            # in lieu of word count.
            self.story.setMetadata('size', story_row.find('td', {'class' : 'num'}).text)

            score = story_row.findNext('th', {'class' : 'ynum'}).text
            if re.match(r"[\d,\.]+",score):
                self.story.setMetadata('score', score)

            description_element = story_row.findNext('td', {'class' : 'lc4'})
            # logger.debug(description_element)

            self.parseDescriptionField(description_element)

            self.parseOtherAttributes(description_element)
        else:
            # modern theme (or minimalist theme, should also work)
            description_element = story_row.find('div', {'class' : 'sdesc'})

            self.parseDescriptionField(description_element)

            misc_element = story_row.find('div', {'class' : 'misc'})
            self.parseOtherAttributes(misc_element)


    def findStoryRow(self):
        page=0
        story_found = False
        while not story_found:
            page = page + 1
            try:
                data = self.get_request(self.story.getList('authorUrl')[0] + "/" + unicode(page))
            except exceptions.HTTPErrorFFF as e:
                if e.status_code == 404:
                    raise exceptions.FailedToDownload("Story not found in Author's list--Set Access Level to Full Access and change Listings Theme back to "+self.getTheme())
            asoup = self.make_soup(data)

            story_row = asoup.find('tr', {'id' : 'sr' + self.story.getMetadata('storyId')})
            if story_row:
                logger.debug("Found story row on page %d" % page)
                story_found = True
                self.has_universes = "/universes" in data
                break

            story_row = asoup.find('div', {'id' : 'sr' + self.story.getMetadata('storyId')})
            if story_row:
                logger.debug("Found story row on page %d" % page)
                story_found = True
                self.has_universes = "/universes" in data
                break

        return story_row


    def parseDescriptionField(self, description_element):
        # Parse the description field for the series or universe and the
        # actual description.

        try:
            a = description_element.find('a', href=re.compile(r"/series/\d+/.*"))
            # logger.debug("Looking for series - a='{0}'".format(a))
            if a:
                # if there's a number after the series name, series_contents is a two element list:
                # [<a href="...">Title</a>, u' (2)']
                series_contents = a.parent.contents
                i = 0 if len(series_contents) == 1 else series_contents[1].strip(' ()')
                seriesUrl = 'https://'+self.host+a['href']
                self.story.setMetadata('seriesUrl',seriesUrl)
                series_name = stripHTML(a)
                # logger.debug("Series name= %s" % series_name)
                series_soup = self.make_soup(self.get_request(seriesUrl))
                if series_soup:
                    # logger.debug("Retrieving Series - looking for name")
                    series_name = stripHTML(series_soup.find('h1', {'id' : 'ptitle'}))
                    series_name = re.sub(r' . a (series by|collection from).*$','',series_name)
                    # logger.debug("Series name: '%s'" % series_name)
                self.setSeries(series_name, i)
                # Check if series is in a universe
                if self.has_universes:
                    universe_url = self.story.getList('authorUrl')[0]  + "&type=uni"
                    universes_soup = self.make_soup(self.get_request(universe_url) )
                    # logger.debug("Universe url='{0}'".format(universe_url))
                    if universes_soup:
                        universes = universes_soup.findAll('div', {'class' : 'ser-box'})
                        # logger.debug("Number of Universes: %d" % len(universes))
                        for universe in universes:
                            # logger.debug("universe.find('a')={0}".format(universe.find('a')))
                            # The universe id is in an "a" tag that has an id but nothing else. It is the first tag.
                            # The id is prefixed with the letter "u".
                            universe_id = universe.find('a')['id'][1:]
                            # logger.debug("universe_id='%s'" % universe_id)
                            universe_name = stripHTML(universe.find('div', {'class' : 'ser-name'})).partition(' ')[2]
                            # logger.debug("universe_name='%s'" % universe_name)
                            # If there is link to the story, we have the right universe
                            story_a = universe.find('a', href=re.compile('/s/'+self.story.getMetadata('storyId')))
                            if story_a:
                                # logger.debug("Story is in a series that is in a universe! The universe is '%s'" % universe_name)
                                self.story.setMetadata("universe", universe_name)
                                self.story.setMetadata('universeUrl','https://'+self.host+ '/library/universe.php?id=' + universe_id)
                                break
                    # else:
                    #     logger.debug("No universe page")
        except:
            raise
        try:
            a = description_element.find('a', href=re.compile(r"/universe/\d+/.*"))
            # logger.debug("Looking for universe - a='{0}'".format(a))
            if a:
                self.story.setMetadata("universe",stripHTML(a))
                # Assumed only one universe, but it does have a URL--use universeHTML
                universe_name = stripHTML(a)
                universeUrl = 'https://'+self.host+a['href']
                # logger.debug("Retrieving Universe - about to get page - universeUrl='{0}".format(universeUrl))
                universe_soup = self.make_soup(self.get_request(universeUrl))
                # logger.debug("Retrieving Universe - have page")
                if universe_soup:
                    # logger.debug("Retrieving Universe - looking for name")
                    universe_name = stripHTML(universe_soup.find('h1', {'id' : 'ptitle'}))
                    universe_name = re.sub(r' .\s+A Universe from the Mind.*$','',universe_name)
                    # logger.debug("Universes name: '{0}'".format(universe_name))

                self.story.setMetadata('universeUrl',universeUrl)
                # logger.debug("Setting universe name: '{0}'".format(universe_name))
                self.story.setMetadata('universe',universe_name)
                if self.getConfig("universe_as_series") and not self.story.getMetadata('seriesUrl'):
                    # logger.debug("universe_as_series")
                    # take position in universe page as number in series.
                    for i, storya in enumerate(universe_soup.find_all('a',href=re.compile(r'^/s/\d+/'))):
                        if storya['href'].split('/')[2] == self.story.getMetadata('storyId'):
                            self.setSeries(universe_name, i+1)
                            self.story.setMetadata('seriesUrl',universeUrl)
                            break
            # else:
            #     logger.debug("Do not have a universe")
        except:
            raise

        # There's nothing around the desc to grab it by, and there's a
        # variable number of links before it.
        for line in description_element.contents:
            content = stripHTML(line)
            line = unicode(line)
            if content == '' or line.strip() == '' or line.startswith("<span") or line.startswith("<br"):
                # skip empty, <span (universe, series or context) and <br>.
                # logger.debug("Discard: %s"%line)
                pass
            else:
                # logger.debug("Use: %s"%line)
                self.setDescription('https://'+self.host+'/s/'+self.story.getMetadata('storyId'),line)
                break

    def parseDate(self,label):
        # date is passed as a timestamp and converted in JS.  used to
        # use noscript value instead, but found one story that didn't
        # include it.
        # <script> tag processing not working?
        # logger.debug('parseDate label: "%s"' % label)
        script = label.findNext('script')
        # logger.debug("script:(%s)"%script)
        # logger.debug("script.text:(%s)"%script.text)
        # logger.debug("script:(stripHTML(%s))"%stripHTML(script))
        noscript = label.findNext('noscript').text
        # I honestly have no idea why both script.text and
        # stripHTML(script) return empty string, but they do. BS or
        # html5lib maybe?
        script = "%s"%label.findNext('script')
        try:
            timestamp = script[script.index("Date(")+5:]
            # remove milliseconds that JS likes.
            timestamp = timestamp[:timestamp.index(")")-3]
            # logger.debug("timestamp:(%s)"%timestamp)
            value = datetime.fromtimestamp(float(timestamp))
        except:
            value = makeDate(stripHTML(noscript), self.dateformat)
        # logger.debug('Have a date field label: "%s", noscript: "%s", timestamp: "%s", value: "%s"' % (label, noscript, timestamp, value))
        return value

    def parseOtherAttributes(self, other_attribute_element):
        for b in other_attribute_element.findAll('b'):
            #logger.debug('Getting metadata: "%s"' % b)
            label = b.text
            if label in ['Posted:', 'Concluded:', 'Updated:']:
                value = self.parseDate(b)
                #logger.debug('Have a date field label: "%s", value: "%s"' % (label, value))
            else:
                value = b.nextSibling
            #logger.debug('label: "%s", value: "%s"' % (label, value))

            if 'Sex' in label:  # storiesonline.net uses '<b>Sex Contents:</b> No Sex'
                self.story.setMetadata('rating', value)
            if 'Age' in label:  # finestories.com,scifistories.com use '<b>Age Rating:</b> Older than XX | '
                self.story.setMetadata('rating', value.split('|')[0])
            if 'Score' in label and re.match(r"[\d,\.]+",value):
                self.story.setMetadata('score', value)
            if 'Tags' in label or 'Codes' in label:
                for code in re.split(r'\s*,\s*', value.strip()):
                    self.story.addToList('sitetags', code)
            if 'Genre' in label:
                for code in re.split(r'\s*,\s*', value.strip()):
                    self.story.addToList('genre', code)

            if 'Posted' in label:
                self.story.setMetadata('datePublished', value)
                self.story.setMetadata('dateUpdated', value)
            if 'Concluded' in label:
                self.story.setMetadata('dateUpdated', value)
            if 'Updated' in label:
                self.story.setMetadata('dateUpdated', value)

        status = other_attribute_element.find('span', {'class':'ab'})
        if status != None:
            if 'Incomplete and Inactive' in status.text:
                self.story.setMetadata('status', 'Incomplete')
            else:
                self.story.setMetadata('status', 'In-Progress')
            if "Last Activity" in status.text:
                value = self.parseDate(status)
                self.story.setMetadata('dateUpdated', value)
        else:
            self.story.setMetadata('status', 'Completed')

    def getMoreText(self, html):
        try:
            story_id = int(re.compile('var story_id=(\d+)').findall(html)[0])
            try:
                pid = re.compile('var pid=(\d+)').findall(html)[0]
            except:
                pid = 'undefined'
            ci = re.compile("var ci='([^']+)'").findall(html)[0]
            tto = re.compile("var tto='([^']+)'").findall(html)[0]
            url = "https://"+self.getSiteDomain()+"/res/responders/tl.php?r="+unicode(random.randint(1, 100001))
            params = {}
            params['cmd'] = 'gt'
            params['data[]'] = [story_id, pid, ci, story_id + 5, tto]
            ver = self.post_request(url, params)

            url = "https://"+self.getSiteDomain()+"/res/responders/tl.php?r="+unicode(random.randint(1, 100001))
            params = {}
            params['cmd'] = 'gr'
            params['data[]'] = [ver]
            return self.post_request(url, params)

        except Exception as e:
            logger.error(e)
            return None

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        html = self.get_request(url)
        soup = self.make_soup(html)

        # The story text is wrapped in article tags. Most of the page header and
        # footer are outside of this.
        chaptertag = soup.find('article')

        # There might be a div with a "load more" button
        srtag = soup.find('div', id='sr')

        if srtag != None:
            logger.debug('Getting more chapter text for: %s' % url)
            moretext = self.getMoreText(html)
            if moretext != None:
                moresoup = self.make_soup(moretext)
                srtag.replace_with(moresoup)
            else:
                logger.info("Failed to get more text for %s" % url)

        # some big chapters are split over several pages
        pager = chaptertag.find('div', {'class' : 'pager'})

        self.cleanPage(chaptertag)

        if pager != None:

            urls=pager.findAll('a')
            urls=urls[:len(urls)-1]
            # logger.debug("pager urls:%s"%urls)
            pager.extract()

            for ur in urls:
                soup = self.make_soup(self.get_request("https://"+self.getSiteDomain()+ur['href']))

                pagetag = soup.find('article')

                self.cleanPage(pagetag)

                for tag in pagetag.contents[1:]:
                    chaptertag.append(tag)


        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chaptertag)

    def cleanPage(self,pagetag):
        "Consolidate 'page' clean up code so it can be called."
        # logger.debug("cleanPage start: {0}".format(pagetag))

        chapter_title = None
        if self.getConfig('inject_chapter_title'):
            h2tag = pagetag.find('h2')
            if h2tag:
                # I'm seeing an h1 now, but it's not logged in?
                # Something's broken...
                chapter_title = h2tag.extract()

        # Strip te header section
        tag = pagetag.find('header')
        if tag:
            #logger.debug("remove before header: {0}".format(tag))
            tag.extract()

        # some big chapters are split over several pages
        # remove FIRST pager and everything before it.
        tag = pagetag.find('div', {'class' : 'pager'})
        while tag != None:
            # logger.debug("remove before pager: {0}".format(tag))
            prev = tag.previousSibling
            tag.extract()
            tag = prev

        # Find the "Continues" marker on the current page and
        # remove everything after that.  This is actually
        # effecting the *previous* 'page'.  EXCEPT!--they are
        # putting a 'conTag' at the *top* now, too.  So this
        # was nuking every page but the first and last.  Now
        # only if 'Continues'
        for contag in pagetag.findAll('span', {'class' : 'conTag'}):
            # remove everything after continues...
            if 'Continuation' in contag.text:
                tag = contag
                while tag != None:
                    # logger.debug("remove before Continuation: {0}".format(tag))
                    prev = tag.previousSibling
                    tag.extract()
                    tag = prev
            elif 'Continues' in contag.text:
                tag = contag
                while tag != None:
                    # logger.debug("remove after Continues: {0}".format(tag))
                    nxt = tag.nextSibling
                    tag.extract()
                    tag = nxt

        # some big chapters are split over several pages
        # remove LAST pager and everything before it.
        # Only needed on last page.
        tag = pagetag.find('div', {'class' : 'pager'})
        while tag != None:
            # logger.debug("remove after pager: {0}".format(tag))
            nxt = tag.nextSibling
            tag.extract()
            tag = nxt

        # If it is a chapter, there are dates at the start for when it was posted or modified. These plus
        # everything before them can be discarded.
        postedDates = pagetag.findAll('div', {'class' : 'date'})
        # logger.debug(postedDates)
        if postedDates:
            a = postedDates[0].previousSibling
            while a != None:
                # logger.debug("before dates: {0}".format(a))
                b = a.previousSibling
                a.extract()
                a = b
            for a in pagetag.findAll('div', {'class' : 'date'}):
                a.extract()

        # Kill the vote form and everything after it.
        a = pagetag.find('div', {'class' : 'vform'})
        # logger.debug("Chapter end= '{0}'".format(a))
        while a != None:
            b = a.nextSibling
            a.extract()
            a=b

        # For chapters, remove next chapter link and everything after it
        a = pagetag.find('h3', {'class' : 'end'})
        # logger.debug("Chapter end= '{0}'".format(a))
        while a != None:
            b = a.nextSibling
            a.extract()
            a=b
        # inject_chapter_title
        if chapter_title:
            chapter_title.name='h3'
            pagetag.insert(0,chapter_title)
