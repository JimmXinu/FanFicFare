#  -*- coding: utf-8 -*-

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
import logging
logger = logging.getLogger(__name__)
import re
import json
from datetime import datetime

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter

def getClass():
    return MangaDexOrgAdapter

class MangaDexOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            # Chapter URLs don't have the story ID, so get it from the API
            if m.group("novchap") == "chapter":
                self.story.setMetadata("storyId", str(json.loads(self._fetchUrl("https://" + self.getSiteDomain() + "/api/v2/chapter/" + m.group("id")))["data"]["mangaId"]))
            # Normal story URL, just set the story ID
            else:
                self.story.setMetadata("storyId", m.group("id"))

            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() + '/title/' + self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','md')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'mangadex.org'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/title/12345/manga-title https://"+cls.getSiteDomain()+"/title/12345 https://"+cls.getSiteDomain()+"/manga/12345"

    def getSiteURLPattern(self):
        return re.escape("https://"+self.getSiteDomain())+r"/(?P<novchap>title|manga|chapter)/0*(?P<id>\d+)/?[0-9]*"

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = "https://" + self.host + "/api/v2/manga/" + self.story.getMetadata('storyId')
        chaptersurl = url + "/chapters"
        tagsurl = "https://" + self.host + "/api/v2/tag"
        logger.info("url: "+url)

        try:
            data = json.loads(self._fetchUrl(url))["data"]

            if data["isHentai"] and not (self.is_adult or self.getConfig("is_adult")):
                raise exceptions.AdultCheckRequired(self.url)

            chapters = json.loads(self._fetchUrl(chaptersurl))["data"]
            tags = json.loads(self._fetchUrl(tagsurl))["data"]

        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # Filter chapters to selected languages, if any
        if self.getConfigList("language_filter"):
            chapters["chapters"] = list(filter(lambda ch: ch["language"] in self.getConfigList("language_filter"), chapters["chapters"]))

        # Sort chapters from first to last
        chapters["chapters"].sort(key=lambda ch: (float(ch["volume"]) if ch["volume"] != "" else 0.0, float(ch["chapter"]) if ch["chapter"] != "" else 0.0, ch["timestamp"]))

        # Filter groups to just those who did the filtered languages
        groups = []
        for chapter in chapters["chapters"]:
            for group in chapter["groups"]:
                if group not in groups:
                    groups.append(group)
        chapters["groups"] = list(filter(lambda gr: gr["id"] in groups, chapters["groups"]))

        ## Title
        self.story.setMetadata('title',data["title"])

        for author in data["author"]:
            self.story.addToList('authorId',"0")
            self.story.addToList('authorUrl','https://'+self.host+"/search?author="+author)
            self.story.addToList('author',author)
        for artist in data["artist"]:
            self.story.addToList('authorId',"0")
            self.story.addToList('authorUrl','https://'+self.host+"/search?artist="+artist)
            self.story.addToList('author',artist)
        for group in chapters["groups"]:
            self.story.addToList('authorId',group["id"])
            self.story.addToList('authorUrl','https://'+self.host+"/group/"+str(group["id"]))
            self.story.addToList('author',group["name"])

        newestChapter = None
        newestVolume = (0, 0) # For status metadata
        self.newestChapterNum = None # save for comparing during update.
        # Scan all chapters to find the oldest and newest as new chapters can
        # be added out of order--That WILL break the epub update.
        # Find the chapters:
        self.story.setMetadata('numChapters',len(chapters["chapters"]))
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))
        for index, chapter in enumerate(chapters["chapters"]):
            chapterDate = datetime.utcfromtimestamp(chapter["timestamp"])
            self.add_chapter(chapter["title"] if chapter["title"] != "" else (("Vol. " + chapter["volume"] + " " if chapter["volume"] != "" else "") + ("Ch. " + chapter["chapter"] if chapter["chapter"] != "" else "")),
                                "https://"+self.host+"/api/v2/chapter/"+chapter["hash"] + "?saver=" + str(self.getConfig("data_saver")).lower(),
                                {'date':chapterDate.strftime(self.getConfig("datechapter_format",self.getConfig("datePublished_format","%Y-%m-%d")))})
            if newestChapter == None or chapterDate > newestChapter:
                newestChapter = chapterDate
                self.newestChapterNum = index
            currentVolume = (float(chapter["volume"]) if chapter["volume"] != "" else 0, float(chapter["chapter"]) if chapter["chapter"] != "" else 0)
            if currentVolume > newestVolume:
                newestVolume = currentVolume

        # Description
        # Parse the BBCode into HTML
        description = data["description"]
        description = re.sub(r"\[(/?(b|i|u|s|sup|sub|code|h1|h2|h3|h4|h5|h6|ul|ol))\]", r"<\1>", description)
        description = re.sub(r"\[(/?)quote\]", r"<\1blockquote>", description)
        description = re.sub(r"\[(/?)list\]", r"<\1ul>", description)
        description = re.sub(r"\[(/?)h\]", r"<\1mark>", description)
        description = re.sub(r"\[hr\]", "<hr />", description)
        description = re.sub(r"\[/hr\]", "", description)
        description = re.sub(r"\[\*\](.*?)(\r?\n)", r"<li>\1</li>\2", description)
        description = re.sub(r"\[spoiler\].*?\[/spoiler\]", "[Spoiler]", description)
        description = re.sub(r"\[((left|center|right|justify))\]", r'<div style="text-align:\1;">', description)
        description = re.sub(r"\[(/(left|center|right|justify))\]", r"</div>", description)
        description = re.sub(r"\[url=(.*?)\]", r'<a href="\1">', description)
        description = re.sub(r"\[url](.*?)\[/url\]", r'<a href="\1">\1</a>', description)
        description = re.sub(r"\[/url]", r"</a>", description)
        description = re.sub(r"\[img=(.*?)\].*?\[/img\]", r'<img src="\1" />', description)
        description = re.sub(r"\[img](.*?)\[/img\]", r'<img src="\1" />', description)
        description = re.sub(r"\r?\n", "<br />", description)
        self.setDescription(url,description)

        # Tags
        for tag in data["tags"]:
            self.story.addToList(tags[str(tag)]["group"].lower(), tags[str(tag)]["name"])

        # Demographic
        self.story.setMetadata('demographic', ["Shounen", "Shoujo", "Seinen", "Josei"][data["publication"]["demographic"] - 1])

        # Language(s)
        languages = []
        for chapter in chapters["chapters"]:
            self.story.addToList('language', chapter["language"])

        # Original Language
        self.story.addToList('original_language', data["publication"]["language"])

        # Stats
        self.story.setMetadata('comments', data["comments"])

        self.story.setMetadata('views', data["views"])

        self.story.setMetadata('follows', data["follows"])

        # Publication Status
        self.story.setMetadata('publication_status', ["In-Progress", "Completed", "Cancelled", "Hiatus"][data["publication"]["status"] - 1])

        # Status
        if data["lastChapter"] == None:
            # If no chapter count, just fall back to the publication status
            self.story.setMetadata('status', self.story.getMetadata("publication_status"))
        else:
            # Otherwise Complete if equal, In-Progress if the current is less
            lastVolume = (float(data["lastVolume"]) if data["lastVolume"] != None else 0, float(data["lastChapter"]))
            self.story.setMetadata('status', "In-Progress" if newestVolume < lastVolume else "Completed")

        if len(chapters["chapters"]) > 0:
            # Timestamp from the first chapter
            self.story.setMetadata('datePublished', datetime.utcfromtimestamp(chapters["chapters"][0]["timestamp"]))

            # Timestamp from the latest chapter
            self.story.setMetadata('dateUpdated', datetime.utcfromtimestamp(chapters["chapters"][-1]["timestamp"]))

        # Cover
        self.setCoverImage(url,data["mainCover"])

    def hookForUpdates(self,chaptercount):
        if self.newestChapterNum and self.oldchapters and len(self.oldchapters) > self.newestChapterNum:
            logger.info("Existing epub has %s chapters\nNewest chapter is %s.  Discarding old chapters from there on."%(len(self.oldchapters), self.newestChapterNum+1))
            self.oldchapters = self.oldchapters[:self.newestChapterNum]
        return len(self.oldchapters)

    # Get an individual chapter. Not actually getting text as this is a manga site.
    def getChapterText(self, url):

        logger.debug('Getting chapter from: %s' % url)

        soup = self.make_soup('<div class="story"></div>')
        ## use the div because the full soup will also have <html><body>.
        ## need soup for .new_tag()
        div=soup.find('div')

        data=json.loads(self._fetchUrl(url))["data"]
        for page in data["pages"]:
            img=soup.new_tag("img")
            img["src"]=data["server"] + data["hash"] + "/" + page
            div.append(img)

        return self.utf8FromSoup(url,div)

    # Prevent tutorial manga from being found by only getting
    # links with the '.manga_title' class
    def get_series_from_page(self,url,data,normalize=False):
        '''
        This method is to make it easier for adapters to detect a
        series URL, pick out the series metadata and list of storyUrls
        to return without needing to override get_urls_from_page
        entirely.
        '''
        if self.host in url:
            soup = self.make_soup(data)
            retval = {}
            retval['urllist']=['https://'+self.host+a['href'] for i, a in enumerate(soup.select('a.manga_title')) if soup.select('a.manga_title').index(a) == i]
            retval['name']=stripHTML(soup.select_one("h6.card-header") if soup.select_one("h6.card-header") != None else "")
            return retval
        ## return dict with at least {'urllist':['storyUrl','storyUrl',...]}
        ## optionally 'name' and 'desc'?
        return {}
