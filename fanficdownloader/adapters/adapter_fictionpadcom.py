# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team
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

import time
import logging
logger = logging.getLogger(__name__)
import re
import urllib2
import time
import json

from .. import BeautifulSoup as bs
#from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class FictionPadSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','fpad')
        self.dateformat = "%Y-%m-%dT%H:%M:%SZ"
        self.is_adult=False
        self.username = None
        self.password = None
        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))
            
            # normalized story URL.
            self._setURL("https://"+self.getSiteDomain()
                         +"/author/"+m.group('author')
                         +"/stories/"+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

    @staticmethod
    def getSiteDomain():
        return 'fictionpad.com'

    @classmethod
    def getSiteExampleURLs(self):
        return "https://fictionpad.com/author/Author/stories/1234/Some-Title"
    
    def getSiteURLPattern(self):
        # http://fictionpad.com/author/Serdd/stories/4275
        return r"http(s)?://(www\.)?fictionpad\.com/author/(?P<author>[^/]+)/stories/(?P<id>\d+)"



    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url=self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
            find = "wordyarn.config.page = "
            data = data[data.index(find)+len(find):]
            data = data[:data.index("</script>")]
            data = data[:data.rindex(";")]
            data = data.replace('tables:','"tables":')
            tables = json.loads(data)['tables']
            #print("data:\n%s"%data)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        # looks like only one author per story allowed.
        author = tables['users'][0]
        story = tables['stories'][0]
        story_ver = tables['story_versions'][0]
        
        self.story.setMetadata('authorId',author['id'])
        self.story.setMetadata('author',author['display_name'])
        self.story.setMetadata('authorUrl','https://'+self.host+'/author/'+author['display_name']+'/stories')

        self.story.setMetadata('title',story_ver['title'])
        self.setDescription(url,story_ver['description'])
        print("story_ver['profile_image_url@2x']:%s"%story_ver['profile_image_url@2x'])
        if not ('assets/story_versions/covers' in story_ver['profile_image_url@2x']):
            self.setCoverImage(url,story_ver['profile_image_url@2x'])

        self.story.setMetadata('datePublished',makeDate(story['published_at'], self.dateformat))
        self.story.setMetadata('dateUpdated',makeDate(story['published_at'], self.dateformat))

        self.story.setMetadata('followers',story['followers_count'])
        self.story.setMetadata('comments',story['comments_count'])
        self.story.setMetadata('views',story['views_count'])
        self.story.setMetadata('likes',int(story['likes'])) # no idea why they floated these.
        self.story.setMetadata('dislikes',int(story['dislikes']))

        if story_ver['is_complete']:
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        self.story.setMetadata('rating', story_ver['maturity_level'])
        self.story.setMetadata('numWords', unicode(story_ver['word_count']))

        for i in tables['fandoms']:
            self.story.addToList('category',i['name'])
        
        for i in tables['genres']:
            self.story.addToList('genre',i['name'])
        
        for i in tables['characters']:
            self.story.addToList('characters',i['name'])

        for c in tables['chapters']:
            chtitle = "Chapter %d"%c['number']
            if c['title']:
                chtitle += " - %s"%c['title']
            self.chapterUrls.append((chtitle,c['body_url']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))
            
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = bs.BeautifulSoup(self._fetchUrl(url))
        return self.utf8FromSoup(url,soup)
    
def getClass():
    return FictionPadSiteAdapter

