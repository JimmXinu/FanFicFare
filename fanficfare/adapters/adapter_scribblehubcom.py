# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2020 FanFicFare team
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
import logging, time, datetime
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six.moves import http_cookiejar as cl


from .base_adapter import BaseSiteAdapter,  makeDate


# In general an 'adapter' needs to do these five things:

# - 'Register' correctly with the downloader
# - Site Login (if needed)
# - 'Are you adult?' check (if needed--some do one, some the other, some both)
# - Grab the chapter list
# - Grab the story meta-data (some (non-eFiction) adapters have to get it from the author page)
# - Grab the chapter texts

# Search for XXX comments--that's where things are most likely to need changing.

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return ScribbleHubComAdapter # XXX

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class ScribbleHubComAdapter(BaseSiteAdapter): # XXX

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        m = re.match(self.getSiteURLPattern(),url)
        # logger.debug("id:%s"%m.group('id'))
        # logger.debug("title:%s"%m.group('title'))

        # get storyId from url
        self.story.setMetadata('storyId', m.group('id'))

        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/series/' + self.story.getMetadata('storyId') + '/' + m.group('title') + '/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','scrhub') # XXX

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%b %d, %Y" # XXX


    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.scribblehub.com' # XXX

    @classmethod
    def getSiteExampleURLs(cls):
        # https://www.scribblehub.com/series/133207/wait-theres-another-wayne/
        # https://www.scribblehub.com/read/133207-wait-theres-another-wayne/chapter/138505/
        return "https://"+cls.getSiteDomain()+"/series/1234/storyname/"

    def getSiteURLPattern(self):
        return re.escape("https://"+self.getSiteDomain())+r"/(series|read)/(?P<id>\d+)[/-](?P<title>[^/]+)"

    # Set cookie to ascending order before page loads, means we know date published
    def set_contents_cookie(self):
        cookie = cl.Cookie(version=0, name='toc_sorder', value='asc',
                           port=None, port_specified=False,
                           domain=self.getSiteDomain(), domain_specified=False, domain_initial_dot=False,
                           path='/', path_specified=True,
                           secure=False,
                           expires=time.time()+10000,
                           discard=False,
                           comment=None,
                           comment_url=None,
                           rest={'HttpOnly': None},
                           rfc2109=False)
        self.get_configuration().get_cookiejar().set_cookie(cookie)

         ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self, get_cover=True):

        # Set the chapters list cookie to asc
        self.set_contents_cookie()


        # index=1 makes sure we see the story chapter index.  Some
        # sites skip that for one-chapter stories.
        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        soup = self.make_soup(data)


        ## Title
        pagetitle = soup.find('div',{'class':'fic_title'})
        self.story.setMetadata('title',stripHTML(pagetitle))

        # Find authorid and URL from main story page
        self.story.setMetadata('authorId',stripHTML(soup.find('span',{'class':'auth_name_fic'})))
        self.story.setMetadata('authorUrl',soup.find('div',{'class':'author'}).find('div',{'property':'author'}).find('span',{'property':'name'}).find('a').get('href'))
        self.story.setMetadata('author',stripHTML(soup.find('span',{'class':'auth_name_fic'})))

        # Find the chapters:
        # This is where scribblehub is gonna get a lil bit messy..

        # Get the contents list from scribblehub, iterate through and add to chapters
        # Can be fairly certain this will not 404 - we know the story id is valid
        contents_payload = {"action": "wi_gettocchp",
                            "strSID": self.story.getMetadata('storyId'),
                            "strmypostid": 0,
                            "strFic": "yes"}

        contents_data = self.post_request("https://www.scribblehub.com/wp-admin/admin-ajax.php", contents_payload)

        contents_soup = self.make_soup(contents_data)

        for i in range(1, int(contents_soup.find('ol',{'id':'ol_toc'}).get('count')) + 1):
            chapter_url = contents_soup.find('li',{'cnt':str(i)}).find('a').get('href')
            chapter_name = contents_soup.find('li',{'cnt':str(i)}).find('a').get('title')
            # logger.debug("Found Chapter " + str(i) + ", name: " + chapter_name + ", url: " + chapter_url)
            self.add_chapter(chapter_name, chapter_url)


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        # utility method
        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""

        # <span class="label">Rated:</span> NC-17<br /> etc

        # Story Description
        if soup.find('div',{'class': 'wi_fic_desc'}):
            svalue = soup.find('div',{'class': 'wi_fic_desc'})
            self.setDescription(url,svalue)

        # Categories
        if soup.find('span',{'class': 'wi_fic_showtags_inner'}):
            categories = soup.find('span',{'class': 'wi_fic_showtags_inner'}).findAll('a')
            for category in categories:
                self.story.addToList('category', stripHTML(category))

        # Genres
        if soup.find('a',{'class': 'fic_genre'}):
            genres = soup.findAll('a',{'class': 'fic_genre'})
            for genre in genres:
                self.story.addToList('genre', stripHTML(genre))

        # Fandoms
        if soup.find('div', string="Fandom"):
            fandoms = soup.find('div', string="Fandom").next_sibling.find_all('a')
            for fandom in fandoms:
                self.story.addToList('fandoms', stripHTML(fandom))

        # Content Warnings
        if soup.find('ul',{'class': 'ul_rate_expand'}):
            warnings = soup.find('ul',{'class': 'ul_rate_expand'}).findAll('a')
            for warn in warnings:
                self.story.addToList('warnings', stripHTML(warn))

        # The date parsing is a bit of a bodge, plenty of corner cased I probably haven't thought of, but try anyway
        # Complete
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]) == "Completed":
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')


        # Updated | looks like this: <span title="Last updated: Jul 16, 2020 01:02 AM">Jul 16, 2020</span> -- snip out the date
        # if we can't parse the date it's because it's today and it says somehting like "6 hours ago"
        if stripHTML(soup.find_all("span", title=re.compile(r"^Last"))[0]):
            date_str = soup.find_all("span", title=re.compile(r"^Last"))[0].get("title")
            try:
                self.story.setMetadata('dateUpdated', makeDate(date_str[14:-9], self.dateformat))
            except ValueError:
                self.story.setMetadata('dateUpdated', datetime.datetime.now())

        # Cover Art - scribblehub has default coverart if it isn't set so this _should_ always work
        if get_cover:
            cover_url = ""
            cover_url = soup.find('div',{'class':'fic_image'}).find('img').get('src')
            if cover_url:
                self.setCoverImage(url,cover_url)

        try:
            self.story.setMetadata('datePublished', makeDate(stripHTML(soup.find('span', {'class': 'fic_date_pub'})), self.dateformat))
        except ValueError:
            # if we get a ValueError it's because it's today and it says somehting like "6 hours ago"
            self.story.setMetadata('datePublished', datetime.datetime.now())

        # Ratings, default to not rated. Scribble hub has no rating system, but has genres for mature and adult, so try to set to these
        self.story.setMetadata('rating', "Not Rated")

        if soup.find("a", {"gid" : "20"}):
            self.story.setMetadata('rating', "Mature")

        if soup.find("a", {"gid" : "902"}):
            self.story.setMetadata('rating', "Adult")


        # Extra metadata from URL + /stats/
        # Again we know the storyID is valid from before, so this shouldn't raise an exception, and if it does we might want to know about it..
        data = self.get_request(url + 'stats/')
        soup = self.make_soup(data)

        def find_stats_data(element, row, metadata):
            if element in stripHTML(row.find('th')):
                self.story.setMetadata(metadata, stripHTML(row.find('td')))

        if soup.find('table',{'class': 'table_pro_overview'}):
            stats_table = soup.find('table',{'class': 'table_pro_overview'}).findAll('tr')
            for row in stats_table:
                find_stats_data("Total Views (All)", row, "views")
                find_stats_data("Word Count", row, "numWords")
                find_stats_data("Average Words", row, "averageWords")
        else:
            logger.debug('Failed to get additional metadata [see PR #512] from url: ' + url + "stats/")



    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))

        div = soup.find('div', {'id' : 'chp_raw'})

        exclude_notes = self.getConfigList('exclude_notes')

        if 'authornotes' in exclude_notes:
            # Remove author's notes
            for author_notes in div.find_all('div', {'class' : 'wi_authornotes'}):
                author_notes.decompose()
        else:
            # Reformat the author's notes
            for author_notes in div.find_all('div', {'class' : 'wi_authornotes'}):
                author_notes['class'] = ['fff_chapter_notes']
                notes_div = soup.new_tag('div')

                new_tag = soup.new_tag('b')
                new_tag.string = "Author's note:"
                notes_div.append(new_tag)

                author_notes_body = author_notes.find('div', {'class' : 'wi_authornotes_body'})
                if author_notes_body:
                    new_tag = soup.new_tag('blockquote')
                    new_tag.append(author_notes_body)
                    notes_div.append(new_tag)

                # Clear old children from the note, then add this
                author_notes.clear()
                author_notes.append(notes_div)

        if 'newsboxes' in exclude_notes:
            # Remove author's notes
            for news in div.find_all('div', {'class' : 'wi_news'}):
                news.decompose()
        else:
            # Reformat the news boxes
            for news in div.find_all('div', {'class' : 'wi_news'}):
                news['class'] = ['fff_chapter_notes']
                notes_div = soup.new_tag('div')

                news_title = news.find('div', {'class' : 'wi_news_title'})
                if news_title:
                    new_tag = soup.new_tag('b')
                    new_tag.string = news_title.get_text()
                    notes_div.append(new_tag)

                news_body = news.find('div', {'class' : 'wi_news_body'})
                if news_body:
                    new_tag = soup.new_tag('blockquote')
                    new_tag.append(news_body)
                    notes_div.append(new_tag)

                # Clear old children from the news box, then add this
                news.clear()
                news.append(notes_div)

        if 'spoilers' in exclude_notes:
            # Remove spoiler boxes
            for spoiler in div.find_all('div', {'class' : 'sp-wrap'}):
                spoiler.decompose()
        else:
            # Reformat the spoiler boxes
            for spoiler in div.find_all('div', {'class' : 'sp-wrap'}):
                spoiler['class'] = ['fff_chapter_notes']
                spoiler_div = soup.new_tag('div')

                spoiler_title = spoiler.find('div', {'class' : 'sp-head'})
                if spoiler_title:
                    new_tag = soup.new_tag('b')
                    new_tag.string = spoiler_title.get_text()
                    spoiler_div.append(new_tag)

                spoiler_body = spoiler.find('div', {'class' : 'sp-body'})
                if spoiler_body:
                    # Remove [collapse] text
                    spdiv = spoiler_body.find('div', {'class' : 'spdiv'})
                    if spdiv: # saw one with no spdiv tag.
                        spdiv.decompose()

                    new_tag = soup.new_tag('blockquote')
                    new_tag.append(spoiler_body)
                    spoiler_div.append(new_tag)

                # Clear old children from the spoiler box, then add this
                spoiler.clear()
                spoiler.append(spoiler_div)

        # Reformat inline footnote popups
        for footnote in div.find_all('sup', {'class' : 'modern-footnotes-footnote'}):
            footnote.decompose()
        for note in div.find_all('span', {'class' : 'modern-footnotes-footnote__note'}):
            if 'footnotes' in exclude_notes:
                note.decompose()
            else:
                note['class'] = ['fff_inline_footnote']
                note.string = ' (' + note.get_text() + ')'

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
