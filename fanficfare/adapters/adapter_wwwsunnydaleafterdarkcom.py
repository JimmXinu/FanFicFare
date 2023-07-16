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

from __future__ import absolute_import
from ..htmlcleanup import stripHTML

# Software: eFiction
from .base_efiction_adapter import BaseEfictionAdapter

class WWWSunnydaleAfterDarkComAdapter(BaseEfictionAdapter):

    @classmethod
    def getProtocol(self):
        """
        Some, but not all site now require https.
        """
        return "https"

    @staticmethod
    def getSiteDomain():
        return 'www.sunnydaleafterdark.com'

    @classmethod
    def getSiteAbbrev(self):
        return 'sad'

    @classmethod
    def getDateFormat(self):
        return r"%m/%d/%y"

    def extractChapterUrlsAndMetadata(self):
        ## Call super of extractChapterUrlsAndMetadata().
        ## base_efiction leaves the soup in self.html.
        super(WWWSunnydaleAfterDarkComAdapter, self).extractChapterUrlsAndMetadata()

        ## attempt to fetch rating from title line:
        ## "Do You Think This Is Love? by Supernatural Beings [PG]"
        r = stripHTML(self.html.find("div", {"id": "pagetitle"}))
        if '[' in r and ']' in r:
            self.story.setMetadata('rating',
                                   r[r.index('[')+1:r.index(']')])

    def make_soup(self, data):
        soup = super(WWWSunnydaleAfterDarkComAdapter, self).make_soup(data)
        ## This site uses Javascript to "hide" warnings, for spoiler reasons
        ## <span class="label">Warnings: <span class="revealSpoiler" onclick="this.getElementsByClassName('spoiler')[0].classList.remove('spoiler');">(Click Here To Reveal) <span class="spoiler">Warning A, Warning B, Warning Y, Warning Z</span></span></span>
        ## We need to remove the revealSpoiler spans and replace them with the contents
        ## of the enclosed spoiler spans.
        infobox = soup.find("div", "infobox")
        if infobox is not None:
            for revealSpoiler in infobox.find_all("span", class_="revealSpoiler"):
                parent = revealSpoiler.parent
                spoiler = revealSpoiler.find("span", class_="spoiler")
                spoiler.extract()
                revealSpoiler.replace_with(spoiler)
                spoiler.unwrap()
                parent.smooth()
        return soup

    def handleMetadataPair(self, key, value):
        ## Inexplicably puts the entire Genres string inside the label span
        ## Likewise Warnings, which also have the spoiler javascript (removed in make_soup)
        if key.startswith("Genre") or key.startswith("Warning"):
            key, value = key.split(': ')
        super(WWWSunnydaleAfterDarkComAdapter, self).handleMetadataPair(key, value)


def getClass():
    return WWWSunnydaleAfterDarkComAdapter

