# -*- coding: utf-8 -*-
# -- coding: utf-8 --
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
################################################################################
###   Written by GComyn
################################################################################
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
logger = logging.getLogger(__name__)
import re

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

################################################################################

def getClass():
    return AdultFanFictionOrgAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class AdultFanFictionOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        # logger.debug("AdultFanFictionOrgAdapter.__init__ - url='{0}'".format(url))

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        #Setting the 'Zone' for each "Site"
        self.zone = self.parsedUrl.netloc.split('.')[0]

        # normalized story URL.(checking self.zone against list
        # removed--it was redundant w/getAcceptDomains and
        # getSiteURLPattern both)
        self._setURL('https://{0}.{1}/story.php?no={2}'.format(self.zone, self.getBaseDomain(), self.story.getMetadata('storyId')))
        #self._setURL('https://' + self.zone + '.' + self.getBaseDomain() + '/story.php?no='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        #self.story.setMetadata('siteabbrev',self.getSiteAbbrev())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev',self.zone+'aff')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%B %d, %Y"

    ## Added because adult-fanfiction.org does send you to
    ## www.adult-fanfiction.org when you go to it and it also moves
    ## the site & examples down the web service front page so the
    ## first screen isn't dominated by 'adult' links.
    def getBaseDomain(self):
        return 'adult-fanfiction.org'

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.adult-fanfiction.org'

    @classmethod
    def getAcceptDomains(cls):
        # mobile.fimifction.com isn't actually a valid domain, but we can still get the story id from URLs anyway
        return ['anime.adult-fanfiction.org',
                'anime2.adult-fanfiction.org',
                'bleach.adult-fanfiction.org',
                'books.adult-fanfiction.org',
                'buffy.adult-fanfiction.org',
                'cartoon.adult-fanfiction.org',
                'celeb.adult-fanfiction.org',
                'comics.adult-fanfiction.org',
                'ff.adult-fanfiction.org',
                'games.adult-fanfiction.org',
                'hp.adult-fanfiction.org',
                'inu.adult-fanfiction.org',
                'lotr.adult-fanfiction.org',
                'manga.adult-fanfiction.org',
                'movies.adult-fanfiction.org',
                'naruto.adult-fanfiction.org',
                'ne.adult-fanfiction.org',
                'original.adult-fanfiction.org',
                'tv.adult-fanfiction.org',
                'xmen.adult-fanfiction.org',
                'ygo.adult-fanfiction.org',
                'yuyu.adult-fanfiction.org']


    @classmethod
    def getSiteExampleURLs(self):
        return ("https://anime.adult-fanfiction.org/story.php?no=123456789 "
              + "https://anime2.adult-fanfiction.org/story.php?no=123456789 "
              + "https://bleach.adult-fanfiction.org/story.php?no=123456789 "
              + "https://books.adult-fanfiction.org/story.php?no=123456789 "
              + "https://buffy.adult-fanfiction.org/story.php?no=123456789 "
              + "https://cartoon.adult-fanfiction.org/story.php?no=123456789 "
              + "https://celeb.adult-fanfiction.org/story.php?no=123456789 "
              + "https://comics.adult-fanfiction.org/story.php?no=123456789 "
              + "https://ff.adult-fanfiction.org/story.php?no=123456789 "
              + "https://games.adult-fanfiction.org/story.php?no=123456789 "
              + "https://hp.adult-fanfiction.org/story.php?no=123456789 "
              + "https://inu.adult-fanfiction.org/story.php?no=123456789 "
              + "https://lotr.adult-fanfiction.org/story.php?no=123456789 "
              + "https://manga.adult-fanfiction.org/story.php?no=123456789 "
              + "https://movies.adult-fanfiction.org/story.php?no=123456789 "
              + "https://naruto.adult-fanfiction.org/story.php?no=123456789 "
              + "https://ne.adult-fanfiction.org/story.php?no=123456789 "
              + "https://original.adult-fanfiction.org/story.php?no=123456789 "
              + "https://tv.adult-fanfiction.org/story.php?no=123456789 "
              + "https://xmen.adult-fanfiction.org/story.php?no=123456789 "
              + "https://ygo.adult-fanfiction.org/story.php?no=123456789 "
              + "https://yuyu.adult-fanfiction.org/story.php?no=123456789")

    def getSiteURLPattern(self):
        return r'https?://(anime|anime2|bleach|books|buffy|cartoon|celeb|comics|ff|games|hp|inu|lotr|manga|movies|naruto|ne|original|tv|xmen|ygo|yuyu)\.adult-fanfiction\.org/story\.php\?no=\d+$'

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        ## You need to have your is_adult set to true to get this story
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)
        else:
            d = self.post_request('https://www.adult-fanfiction.org/globals/ajax/age-verify.php', {"verify":"1"})
            if "Age verified successfully" not in d:
                raise exceptions.FailedToDownload("Failed to Verify Age: {0}".format(d))

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)
        # logger.debug(data)

        if "The dragons running the back end of the site can not seem to find the story you are looking for." in data:
            raise exceptions.StoryDoesNotExist("{0}.{1} says: The dragons running the back end of the site can not seem to find the story you are looking for.".format(self.zone, self.getBaseDomain()))

        soup = self.make_soup(data)

        ## Title
        ## Some of the titles have a backslash on the story page, but not on the Author's page
        ## So I am removing it from the title, so it can be found on the Author's page further in the code.
        ## Also, some titles may have extra spaces '  ', and the search on the Author's page removes them,
        ## so I have to here as well. I used multiple replaces to make sure, since I did the same below.
        h1 = soup.find('h1')
        # logger.debug("Title:%s"%h1)
        self.story.setMetadata('title',stripHTML(h1).replace('\\','').replace('  ',' ').replace('  ',' ').replace('  ',' ').strip())

        # Find the chapters from first list only
        chapters = soup.select_one('select.chapter-select').select('option')
        for chapter in chapters:
            self.add_chapter(chapter,self.url+'&chapter='+chapter['value'])


        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"profile.php\?id=\d+"))
        if a == None:
            # I know that the original author of fanficfare wants to always have metadata,
            # but I posit that if the story is there, even if we can't get the metadata from the
            # author page, the story should still be able to be downloaded, which is what I've done here.
            self.story.setMetadata('authorId','000000000')
            self.story.setMetadata('authorUrl','https://www.adult-fanfiction.org')
            self.story.setMetadata('author','Unknown')
            logger.warning('There was no author found for the story... Metadata will not be retreived.')
            self.setDescription(url,'>>>>>>>>>> No Summary Given, Unknown Author <<<<<<<<<<')
        else:
            self.story.setMetadata('authorId',a['href'].split('=')[1])
            self.story.setMetadata('authorUrl',a['href'])
            self.story.setMetadata('author',stripHTML(a))

            ## The story page does not give much Metadata, so we go to
            ## the Author's page.  Except it's actually a sub-req for
            ## list of author's stories for that subdomain
            author_Url = 'https://members.{0}/load-user-stories.php?subdomain={1}&uid={2}'.format(
                self.getBaseDomain(),
                self.zone,
                self.story.getMetadata('authorId'))

            logger.debug('Getting the load-user-stories page: {0}'.format(author_Url))
            adata = self.get_request(author_Url)

            none_found = "No stories found in this category."
            if none_found in adata:
                raise exceptions.StoryDoesNotExist("{0}.{1} says: {2}".format(self.zone, self.getBaseDomain(), none_found))

            asoup = self.make_soup(adata)
            # logger.debug(asoup)

            story_card = asoup.select_one('div.story-card:has(a[href="{0}"])'.format(url))
            # logger.debug(story_card)

            ## Category
            ## I've only seen one category per story so far, but just in case:
            for cat in story_card.select('div.story-card-category'):
                # remove Category:, old code suggests Located: is also
                # possible, so removing by <strong>
                cat.find("strong").decompose()
                self.story.addToList('category',stripHTML(cat))

            self.setDescription(url,story_card.select_one('div.story-card-description'))

            for tag in story_card.select('span.story-tag'):
                self.story.addToList('eroticatags',stripHTML(tag))

            ## created/updates share formatting
            for meta in story_card.select('div.story-card-meta-item span:last-child'):
                meta = stripHTML(meta)
                if 'Created: ' in meta:
                    meta = meta.replace('Created: ','')
                    self.story.setMetadata('datePublished', makeDate(meta, self.dateformat))

                if 'Updated: ' in meta:
                    meta = meta.replace('Updated: ','')
                    self.story.setMetadata('dateUpdated', makeDate(meta, self.dateformat))

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        #Since each chapter is on 1 page, we don't need to do anything special, just get the content of the page.
        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))
        chaptertag = soup.select_one('div.chapter-body')
        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: {0}!  Missing required element!".format(url))
        ## chapter text includes a copy of story title, author,
        ## chapter title, & eroticatags specific to the chapter.  Did
        ## before, too.

        return self.utf8FromSoup(url,chaptertag)
