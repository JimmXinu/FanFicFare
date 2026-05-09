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
import re
import logging

from bs4 import Comment

logger = logging.getLogger(__name__)

from .. import exceptions

from .base_adapter import BaseSiteAdapter,  makeDate

try: # just a way to switch between CLI and PI
    ## webbrowser.open doesn't work on some linux flavors.
    ## piggyback Calibre's version.
    from calibre.gui2 import safe_open_url as open_url
except :
    from webbrowser import open as open_url

# Below pages work on the same general structure.
# Extracting works as expected.
valid_urls = [
    "grometsplaza.net",
    "selfbound.net",
    "maidbots.net",
    "dollstories.net",
    "packagedstories.net",
    "latexstories.net",
    "boundstories.net",
    "mummified.net"
]

class GrometsplazaSiteAdapter(BaseSiteAdapter):

    chapter_content = []

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        #self.is_adult=True

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','grometsplaza')
        self.story.setMetadata('source',url)

        ## set url
        self._setURL(url)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d.%m.%Y"

    @staticmethod
    def getSiteDomain():
       return 'grometsplaza.net'


    @classmethod
    def getAcceptDomains(cls):
        return valid_urls

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://" + cls.getSiteDomain() + "storieslr/storyname.html"


    def validateURL(self):
        return re.match(self.getSiteURLPattern(), self.url)

    def getSiteURLPattern(self):
        return r"https?://(?:www\.)?(?:%s)(?:/.*)?$" % "|".join(valid_urls)

    def extractChapterUrlsAndMetadata(self):

        url = self.url
        data = self.get_request(url)

        if "Apologies, but we were unable to find what you were looking for." in data:
            raise exceptions.StoryDoesNotExist(
                '{} says: Apologies, but we were unable to find what you were looking for.'.format(
                    self.url))

        soup = self.make_soup(data)

        ## Special Author Metadata:
        author_link = soup.find("h3", id="author").find('a')
        self.story.setMetadata('authorId', author_link.string)
        self.story.setMetadata('authorUrl', author_link['href'])

        self.set_metadata(soup, "title")
        self.set_metadata(soup, "author")
        self.set_metadata(soup, "copyright")
        self.set_metadata(soup, "published")
        self.set_metadata(soup, "grometsplaza:copyrightyear")
        self.set_metadata(soup, "grometsplaza:forumfeedback")
        self.set_metadata(soup, "part")

        self.story.addToList('category',  self.get_meta_value(soup, "grometsplaza:categories"))
        self.story.addToList('tags',  self.get_meta_value(soup, "grometsplaza:storycodes"))
        #self.story.addToList('datePublished',  self.get_meta_value(soup, "published"))

        self.generate_chapters_and_contents(soup, url)

    def generate_chapters_and_contents(self, soup, url):
        self.chapter_content = []
        paragraph = ""
        prologue = soup.find("div", id="prologue")
        if prologue is not None:
            for content in prologue.contents:
                if not isinstance(content, Comment):
                    paragraph = paragraph + "\n" + content.string.strip()

        if paragraph.strip() != "":
            self.add_chapter("Prologue", url)
            self.chapter_content.append(paragraph)

        chapters = soup.find_all('h4')
        i = 0
        for chapter in chapters:
            title = chapter.contents[0]
            if title:
                # add fake anchor parameter, to satisfy unique ids.
                self.add_chapter(title.string, url + "#chapter" + str(i))
                i += 1

        story = soup.find('div', id="main")
        # Find first p
        start = story.find("p")
        # Iterate over children. Each h4 is a new chapter, each p content
        paragraph = ""
        for sibling in start.find_next_siblings():
            if sibling.name == "h4":
                self.chapter_content.append(paragraph)
                paragraph = ""
            if sibling.name == "p":
                if not isinstance(sibling, Comment):
                    text = sibling.text
                    paragraph = paragraph + "\n" + text

        # Add last chapter
        self.chapter_content.append(paragraph)

    ## Overridden Class function
    def getChapterTextNum(self, url, index):
        logger.debug('Reusing already processed chapters')
        if None == self.chapter_content:
            raise exceptions.FailedToDownload(
                "Error downloading Chapter: %s!  Missing required element!" % url)

        return self.chapter_content[index]


    ## Local Functions
    def get_meta_value(self, soup, tag):
        for metadata in soup.find_all("meta"):
            name = metadata.attrs.get("name")
            val = metadata.attrs.get("content")

            if name == tag:
                return val
        return None

    def set_metadata(self, soup, tag):
        self.story.setMetadata(tag, self.get_meta_value(soup, tag))

def getClass():
    return GrometsplazaSiteAdapter
