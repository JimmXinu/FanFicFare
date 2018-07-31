# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2018 FanFicFare team
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


#from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

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
    def getSiteExampleURLs(cls):
        return "https://fictionpad.com/author/Author/stories/1234/Some-Title"

    def getSiteURLPattern(self):
        # http://fictionpad.com/author/Serdd/stories/4275
        return r"http(s)?://(www\.)?fictionpad\.com/author/(?P<author>[^/]+)/stories/(?P<id>\d+)"

# <form method="post" action="/signin">
#     <input name="authenticity_token" type="hidden" value="u+cfdXh46dRnwVnSlmE2B2BFmHgu760paqgBG6KQeos=" />
#     <input type="hidden" name="remember" value="1">
#     <strong class="help-start text-center">or with FictionPad</strong>
#     <label class="control-label hidden-placeholder">Pseudonym or Email Address</label>
#     <input name="login" class="input-block-level" type="text" placeholder="Pseudonym or Email Address" maxlength="50" required autofocus>
#     <label class="control-label hidden-placeholder">Password</label>
#     <input name="password" class="input-block-level" type="password" placeholder="Password" minlength="6" required>
#     <button type="submit" class="btn btn-primary btn-block">Sign In</button>
#     <p class="help-end">
#         <a href="/passwordreset">Forgot your password?</a>
#     </p>
# </form>
    def performLogin(self):
        params = {}

        if self.password:
            params['login'] = self.username
            params['password'] = self.password
        else:
            params['login'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['remember'] = '1'

        loginUrl = 'http://' + self.getSiteDomain() + '/signin'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['login']))

        ## need to pull empty login page first to get authenticity_token
        soup = self.make_soup(self._fetchUrl(loginUrl))
        params['authenticity_token']=soup.find('input', {'name':'authenticity_token'})['value']

        data = self._postUrl(loginUrl, params)

        if "Invalid email/pseudonym and password combination." in data:
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['login']))
            raise exceptions.FailedToLogin(loginUrl,params['login'])


    def extractChapterUrlsAndMetadata(self):
        # fetch the chapter.  From that we will get almost all the
        # metadata and chapter list

        url=self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
            if "This is a mature story.  Please sign in to read it." in data:
                self.performLogin()
                data = self._fetchUrl(url)

            find = "wordyarn.config.page = "
            data = data[data.index(find)+len(find):]
            data = data[:data.index("</script>")]
            data = data[:data.rindex(";")]
            data = data.replace('tables:','"tables":')
            tables = json.loads(data)['tables']
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(url)
            else:
                raise e

        # looks like only one author per story allowed.
        author = tables['users'][0]
        story = tables['stories'][0]
        story_ver = tables['story_versions'][0]
        logger.debug("story:%s"%story)

        self.story.setMetadata('authorId',author['id'])
        self.story.setMetadata('author',author['display_name'])
        self.story.setMetadata('authorUrl','https://'+self.host+'/author/'+author['display_name']+'/stories')

        self.story.setMetadata('title',story_ver['title'])
        self.setDescription(url,story_ver['description'])

        if not ('assets/story_versions/covers' in story_ver['profile_image_url@2x']):
            self.setCoverImage(url,story_ver['profile_image_url@2x'])

        self.story.setMetadata('datePublished',makeDate(story['published_at'], self.dateformat))
        self.story.setMetadata('dateUpdated',makeDate(story['published_at'], self.dateformat))

        self.story.setMetadata('followers',story['followers_count'])
        self.story.setMetadata('comments',story['comments_count'])
        self.story.setMetadata('views',story['views_count'])
        self.story.setMetadata('likes',int(story['likes'])) # no idea why they floated these.
        if 'dislikes' in story:
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
            self.add_chapter(chtitle,c['body_url'])


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        if not url:
            data = u"<em>This chapter has no text.</em>"
        else:
            data = self._fetchUrl(url)
        soup = self.make_soup(u"<div id='story'>"+data+u"</div>")
        return self.utf8FromSoup(url,soup)

def getClass():
    return FictionPadSiteAdapter

