# -*- coding: utf-8 -*-

# Copyright 2023 FanFicFare team
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
from .. import exceptions
from .base_adapter import BaseSiteAdapter, makeDate
import re
import json
import logging
logger = logging.getLogger(__name__)

def getClass():
    return SoFurryComAdapter

class SoFurryComAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.username = self.getConfig("username")
        self.password = self.getConfig("password")
        self.dateformat = "%Y-%m-%dT%H:%M:%S%z"
        self.story.setMetadata('siteabbrev','sf')
        self.story.setMetadata('status', 'Completed')
        # self.story.setMetadata('language', "English")
        self.chaptered = None
        self.is_adult = self.getConfig("is_adult")

    @staticmethod
    def getSiteDomain():
        return 'sofurry.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/s/z1V1z3Zn https://"+cls.getSiteDomain()+"/u/username/gallery?folder=abcd1234"

    def _setURL(self,url):
        match = re.search(self.getSiteURLPattern(), url)
        if not match:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())
        self.is_story_url = bool(match.group('story_url'))
        if match.group('story_url'):
            self.story.setMetadata('storyId', match.group('story_id'))
            url = match.group('story_url')
        else:
            self.story.setMetadata('storyId', match.group('folder_id'))
            url = match.group('folder_url')

        super(SoFurryComAdapter, self)._setURL(url)

    def getSiteURLPattern(self):
        return r"(?P<folder_url>https?://"+re.escape(self.getSiteDomain())+r"/u/.+/gallery\?folder=(?P<folder_id>[a-zA-Z0-9]+))|(?P<story_url>https?://"+re.escape(self.getSiteDomain())+r"/s/(?P<story_id>[a-zA-Z0-9]+))(?=[?#\s]|$)"

    def performLogin(self, url):
        loginUrl = 'https://sofurry.com/login'

        data = self.get_request("https://sofurry.com/fe/auth/sofurry",usecache=False)
        soup = self.make_soup(data)
        params = {}
        params['_token'] = soup.find('meta', {'name':'csrf-token'}).get('content')
        if self.password:
            params['email'] = self.username
            params['password'] = self.password
        else:
            params['email'] = self.getConfig("username")
            params['password'] = self.getConfig("password")

        if not params['username'] and not params['password']:
            logger.warning("Login credentials are missing.")
            raise exceptions.FailedToLogin(url,params['email'])

        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl, params['email']))
        logger.debug("CSRF Token %s", params['_token'])

        try:
            d = self.post_request(loginUrl, params, usecache=False)
        except exceptions.HTTPErrorFFF as e:
            # After successful login the website can return 404, see issue #1385
            if e.status_code == 404:
                d = self.get_request("https://sofurry.com/fe/auth/sofurry",usecache=False)
            else:
                raise e

        if 'src="/img/user/' not in d :
            logger.info("Failed to login to URL %s as %s" % (loginUrl, params['email']))
            raise exceptions.FailedToLogin(url,params['email'])

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        logger.info("url: "+self.url)

        try:
            data = self.get_request(self.url,usecache=True)
        except exceptions.HTTPErrorFFF as e:
            # Members only stories return 401
            if e.status_code == 401:
                self.performLogin(self.url)
                data = self.get_request(self.url,usecache=True)
            else:
                raise e

        soup = self.make_soup(data)
        if (self.getConfig("always_login") and 'src="/img/user/' not in data):
            self.performLogin(self.url)
            data = self.get_request(self.url,usecache=False)
            soup = self.make_soup(data)

        if self.is_story_url:
            turbo_stream = self.get_request(self.url+".data",usecache=True)
            turbo_stream_dict = self.decode(turbo_stream)
            self.story.setMetadata('author', turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["author"]["username"])
            self.story.setMetadata('authorUrl', "https://"+self.getSiteDomain()+"/u/"+turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["author"]["handle"])
            self.story.setMetadata('authorId', turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["author"]["handle"])
        else:
            split_url = self.url.split("?")
            turbo_stream = self.get_request(split_url[0]+".data?"+split_url[1],usecache=True)
            turbo_stream_dict = self.decode(turbo_stream)
            self.story.setMetadata('author', turbo_stream_dict["profile"]["data"]["profile"]["username"])
            self.story.setMetadata('authorUrl', "https://"+self.getSiteDomain()+"/u/"+turbo_stream_dict["profile"]["data"]["profile"]["handle"])
            self.story.setMetadata('authorId', turbo_stream_dict["profile"]["data"]["profile"]["handle"])

        story_tags = []
        numWords = 0

        if not self.is_story_url:
            dateformat ='%Y-%m-%dT%H:%M:%S.%f%z'
            stories_in_folder = []
            page = 0
            fetch_next_page = True
            while fetch_next_page:
                data = self.get_request("https://"+self.getSiteDomain()+"/api/profile?handle={}&tab=folder&folder_id={}&page={}&per_page=100".format(turbo_stream_dict["profile"]["data"]["profile"]["handle"], self.story.getMetadata('storyId'), page), usecache=True)
                folder_dict = json.loads(data)

                if len(folder_dict["submissions"]["data"]) == 0 and turbo_stream_dict["root"]["data"]["user"] == None:
                    self.performLogin(self.url)
                    split_url = self.url.split("?")
                    turbo_stream_dict = self.decode(self.get_request(split_url[0]+".data?"+split_url[1],usecache=False))
                    data = self.get_request("https://"+self.getSiteDomain()+"/api/profile?handle={}&tab=folder&folder_id={}&page={}&per_page=100".format(turbo_stream_dict["profile"]["data"]["profile"]["handle"], self.story.getMetadata('storyId'), page), usecache=False)
                    folder_dict = json.loads(data)
                elif len(folder_dict["submissions"]["data"]) == 0 and turbo_stream_dict["root"]["data"]["user"] != None:
                    raise exceptions.FailedToDownload("Empty Folder")

                fetch_next_page = folder_dict["submissions"]["hasNextPage"]
                stories_in_folder.extend(folder_dict["submissions"]["data"])
                page += 1

            self.story.setMetadata('title', folder_dict["folder"]["name"])

            self.stories_descriptions = {}
            for story in reversed(stories_in_folder):
                if story["type"] != "story":
                    logger.debug("Skipping %s, %s", story["id"], story["title"])
                    continue

                story_title = story["title"]
                story_url = "https://"+self.getSiteDomain()+"/s/{}.data".format(story["id"])

                if story["wordCount"] != None:
                    numWords += int(story["wordCount"])
                else:
                    logger.debug("Story has no word count. Final count may be inaccurate.")

                story_tags.extend(story["tags"])
                self.stories_descriptions[story["id"]] = story["description"]

                try:
                    data = self.get_request(story_url,usecache=True)
                except exceptions.HTTPErrorFFF as e:
                    if e.status_code == 401:
                        self.performLogin(story_url)
                        data = self.get_request(story_url,usecache=True)
                    else:
                        raise e

                story_turbostream = self.decode(data)
                story_chapters = [d for d in story_turbostream["routes/submission.$id"]["data"]["submission"]["content"] if d['extension'] in ["txt", "html"]]
                len_chapters = len(story_chapters)
                for chapter in story_chapters:
                    # Chapter urls expire X-Amz-Expires=600 (10 minutes)
                    chapter_title = story_title +" - "+ chapter["title"] if chapter["title"] and len_chapters > 1 else story_title
                    self.add_chapter(chapter_title, chapter["displayUrl"],
                            {'date':makeDate(story["publishedAt"],dateformat).strftime(self.getConfig("datechapter_format",self.getConfig("datePublished_format","%Y-%m-%d"))),
                            'numWords': chapter["meta"]["wordCount"],
                            "SourceStoryId": story["id"]})

            self.story.extendList('genre', list(set(story_tags)))
            self.story.setMetadata('numWords', numWords)

            self.story.setMetadata('dateUpdated', makeDate(stories_in_folder[0]["publishedAt"], dateformat))
            self.story.setMetadata('datePublished', makeDate(stories_in_folder[-1]["publishedAt"], dateformat))
            logger.debug(self.story.getMetadata('datePublished'))
            return

        self.story.setMetadata('title', turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["title"])

        chapters = turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["content"]
        for chapter in chapters:
            chap_title = chapter["title"] or turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["title"]
            self.add_chapter(chap_title,chapter["displayUrl"],
            {'numWords':chapter["meta"]["wordCount"]})

            numWords += int(chapter["meta"]["wordCount"])

        self.story.setMetadata('numWords', numWords)

        div_chap_tags = soup.select(r'div.px-4.md\:px-8.py-6.space-y-4.lg\:flex-1.lg\:border-r.lg\:border-border > div.flex.flex-wrap.gap-1\.5 > a')
        story_tags.extend([stripHTML(tag) for tag in div_chap_tags])
        self.story.extendList('genre', story_tags)

        date_posted = turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["publishedAt"]
        self.story.setMetadata('datePublished', makeDate(date_posted, self.dateformat))
        logger.debug(self.story.getMetadata('datePublished'))

        rated = turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["rating"]
        if rated >= 20:
            self.story.setMetadata('rating', "Adult")
        elif rated >= 10:
            self.story.setMetadata('rating', "Mature")
        else:
            self.story.setMetadata('rating', "Clean")
        logger.debug(self.story.getMetadata('rating'))

        self.setDescription(self.url, turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["description"])

        if get_cover:
            img = turbo_stream_dict["routes/submission.$id"]["data"]["submission"]["coverUrl"]
            if img:
                self.setCoverImage(self.url,img)

    def getChapterTextNum(self, url, index):
        logger.debug('Getting chapter '+url)

        if self.is_story_url:
            data = self.get_request(url,usecache=True)

            return self.utf8FromSoup(url,self.make_soup(data))

        chapter_html = ""
        story_id = self.get_chapter(index, "SourceStoryId")
        desc = self.stories_descriptions.pop(story_id, None)
        if self.getConfig("include_description_in_chapters", False) and desc:
            chapter_html += "<div class=\"fff_chapter_notes fff_head_notes\"><b>Description:</b><blockquote>" + \
                desc + \
            "</blockquote></div>"

        chapter_html += "<div class=\"{} fff_chapter_content\">".format(story_id) + \
                self.get_request(url,usecache=True) + \
        "</div>"

        return self.utf8FromSoup(url,self.make_soup(chapter_html))

    def before_get_urls_from_page(self,url,normalize):
        if self.password and self.getConfig("always_login"):
            self.performLogin(url)

    @staticmethod
    def decode(payload):
        """Turn a turbo-stream body str into a Python object."""
        # Negative slot numbers stand for a fixed value instead of pointing anywhere.
        SENTINELS = {
            -1: None,           # a gap in an array
            -2: float("nan"),
            -3: float("-inf"),
            -4: -0.0,
            -5: None,           # null
            -6: float("inf"),
            -7: None,           # undefined
        }

        # Take the first line only. Later lines stream extra data and are skipped
        # here; add them back if a response ever spans more than one line.
        table = json.loads(payload.split("\n", 1)[0])

        # Remember every finished value by its slot number. This lets shared values
        # resolve once and lets a value that points back at itself terminate.
        done = {}

        def resolve(slot):
            if slot in SENTINELS:            # negative slot -> a literal like null
                return SENTINELS[slot]
            if slot in done:                 # already built -> reuse it
                return done[slot]

            entry = table[slot]

            if not isinstance(entry, (list, dict)):   # plain string / number / bool
                done[slot] = entry
                return entry

            if isinstance(entry, dict):      # object: {"_<key slot>": <value slot>}
                obj = done[slot] = {}        # store it before filling, in case it
                for key_ref, value_ref in entry.items():   # points back at itself
                    key = resolve(int(key_ref[1:]))         # drop the "_" prefix
                    obj[key] = resolve(value_ref)
                return obj

            if entry and isinstance(entry[0], str):   # tagged value, e.g. ["D", ...]
                return resolve_tagged(slot, entry)

            array = done[slot] = []          # array: every item points at a slot
            for item_ref in entry:
                array.append(resolve(item_ref))
            return array

        def resolve_tagged(slot, entry):
            tag, args = entry[0], entry[1:]
            if tag == "D":                   # Date, kept as its ISO-8601 string
                done[slot] = args[0]
            elif tag == "U":                 # URL, kept as a plain string
                done[slot] = args[0]
            elif tag == "B":                 # BigInt
                done[slot] = int(args[0])
            elif tag == "R":                 # RegExp -> {pattern, flags}
                done[slot] = {"pattern": args[0], "flags": args[1] if len(args) > 1 else ""}
            elif tag == "Y":                 # Symbol.for(x) -> its string key
                done[slot] = args[0]
            elif tag == "S":                 # Set -> list
                out = done[slot] = []
                out.extend(resolve(ref) for ref in args)
            elif tag == "M":                 # Map -> dict (pairs: key, value, key...)
                out = done[slot] = {}
                for i in range(0, len(args), 2):
                    out[resolve(args[i])] = resolve(args[i + 1])
            elif tag == "N":                 # object with no prototype -> plain dict
                out = done[slot] = {}
                for key_ref, value_ref in args[0].items():
                    out[resolve(int(key_ref[1:]))] = resolve(value_ref)
            elif tag == "Z":                 # alias: reuse the value in another slot
                done[slot] = resolve(args[0])
            else:
                raise ValueError(f"unknown turbo-stream tag: {tag!r}")
            return done[slot]

        return resolve(0)