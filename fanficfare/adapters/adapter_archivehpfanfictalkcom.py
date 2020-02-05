# -*- coding: utf-8 -*-

# Copyright 2020 FanFicFare team
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
from .base_efiction_adapter import BaseEfictionAdapter


class ArchiveHPfanfictalkComAdapter(BaseEfictionAdapter):

    @staticmethod
    def getSiteDomain():
        return 'archive.hpfanfictalk.com'

    @classmethod
    def getSiteAbbrev(self):
        return 'ahpfftc'

    @classmethod
    def getDateFormat(self):
        return "%d %B %Y"

    @classmethod
    def getProtocol(self):
        """
        Some, but not all site now require https.
        """
        return "https"

    # def handleMetadataPair(self, key, value):
    #     if key == 'MyCustomKey':
    #         self.story.setMetadata('somekye', value)
    #     else:
    #         super().handleMetadata(key, value)

# Category: Harry Potter - J. K. Rowling
# .listbox > div:nth-child(1) > b:nth-child(1) > a:nth-child(1)
# html body div.gb-80.content div.gb-full div#output div.listbox div b a
# /html/body/div[2]/div/div[2]/div[2]/div/b[1]/a[1]

# Genre: Bullying, Depression, F/M, Suicidal Thoughts
# <span class label="Genre"> && <span class label="Themes">
# <span class label="Inclusivity"> && <span class label="Advisories">

# Language: English

# Characters: Bill Weasley, Ginny Weasley, Harry Potter, Minerva McGonagall
# <span class label="Characters">

# Relationships: Harry Potter/Ginny Weasley
# <span class label="Pairings">

# Status: Completed
# See Rating below

# Series:
# <span class label="Series">

# Published: 2017-11-09
# div.gb-full:nth-child(1) > div:nth-child(7) > div:nth-child(2)
# html body div.gb-80.content div.gb-full div.gb-full div
# /html/body/div[2]/div/div[5]/div[2]
# <div align="center">  <b>Published:</b> 13 Mar 2017 · <b>Updated:</b>
# 06 Dec 2019</div>

# Updated: 2017-11-09
# See above

# Packaged: 2019-10-13 08:44:30

# Rating: Mature Audiences
# same as Category, <b>Rating:</b> Mature Audiences · Incomplete

# Chapters: 1
# <hr class="style2"> <b>Story Length:</b> 26 chapters (230198 words)

# Words: 4,520
# See Chapters above

# Publisher: archive.hpfanfictalk.com

# Summary:
# /html/body/div[2]/div/div[2]/div[2]/blockquote2
# .listbox > blockquote2:nth-child(4)
# html body div.gb-80.content div.gb-full div#output div.listbox blockquote2


def getClass():
    return ArchiveHPfanfictalkComAdapter
