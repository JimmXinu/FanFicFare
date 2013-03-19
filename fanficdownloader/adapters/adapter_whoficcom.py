# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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

from .. import BeautifulSoup as bs
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

class WhoficComSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','whof')
        self.decode = ["Windows-1252",
                       "utf8"] # 1252 is a superset of iso-8859-1.
                               # Most sites that claim to be
                               # iso-8859-1 (and some that claim to be
                               # utf8) are really windows-1252.
        
    @staticmethod
    def getSiteDomain():
        return 'www.whofic.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return re.escape("http://"+self.getSiteDomain()+"/viewstory.php?sid=")+"\d+$"

    def extractChapterUrlsAndMetadata(self):

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        # fetch the first chapter.  From that we will:
        # - determine title, authorname, authorid
        # - get chapter list, if not one-shot.

        url = self.url+'&chapter=1'
        logger.debug("URL: "+url)
        
        # use BeautifulSoup HTML parser to make everything easier to find.
        try:
            soup = bs.BeautifulSoup(self._fetchUrl(url))
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # pull title(title) and author from the HTML title.
        title = soup.find('title').string
        logger.debug('Title: %s' % title)
        title = title.split('::')[1].strip()
        self.story.setMetadata('title',title.split(' by ')[0].strip())
        self.story.setMetadata('author',title.split(' by ')[1].strip())

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])

        # Find the chapter selector 
        select = soup.find('select', { 'name' : 'chapter' } )
    	 
        if select is None:
    	   # no selector found, so it's a one-chapter story.
    	   self.chapterUrls.append((self.story.getMetadata('title'),url))
        else:
    	   allOptions = select.findAll('option')
    	   for o in allOptions:
    	     url = self.url + "&chapter=%s" % o['value']
             # just in case there's tags, like <i> in chapter titles.
    	     title = "%s" % o
             title = re.sub(r'<[^>]+>','',title)
    	     self.chapterUrls.append((title,url))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## Whofic.com puts none of the other meta data in the chapters
        ## or even the story chapter index page.  Need to scrape the
        ## author page to find it.

        # <table width="100%" bordercolor="#333399" border="0" cellspacing="0" cellpadding="2"><tr><td>
        # <b><a href="viewstory.php?sid=38220">Accompaniment 2</a></b> by <a href="viewuser.php?uid=12412">clandestinemiscreant</a>  [<a href="reviews.php?sid=38220">Reviews</a> - <a href="reviews.php?sid=38220">0</a>] <br>
        # This is a series of short stories written as an accompaniment to Season 2, Season 28 for us oldies, and each is unrelated except for that one factor. Each story is canon, in that it does not change established events at time of airing, based on things mentioned and/or implied and missing or deleted scenes that were not seen in the final aired episodes.<br>
        # <font size="-1"><b><a href="categories.php?catid=15">Tenth Doctor</a></b> - All Ages - None - Humor, Hurt/Comfort, Romance<br>
        # <i>Characters:</i> Rose Tyler<br>
        # <i>Series:</i> None<br>
        # <i>Published:</i> 2010.08.15 - <i>Updated:</i> 2010.08.16 - <i>Chapters:</i> 4 - <i>Completed:</i> Yes - <i>Word Count:</i> 4890 </font>
        # </td></tr></table>
             
        logger.debug("Author URL: "+self.story.getMetadata('authorUrl'))
        soup = bs.BeautifulStoneSoup(self._fetchUrl(self.story.getMetadata('authorUrl')),
                                     selfClosingTags=('br')) # normalize <br> tags to <br />
        # find this story in the list, parse it's metadata based on
        # lots of assumptions about the html, since there's little
        # tagging.
        # Found a story once that had the story URL in the desc for a
        # series on the same author's page.  Now using the reviews
        # link instead to find the appropriate metadata.
        a = soup.find('a', href=re.compile(r'reviews.php\?sid='+self.story.getMetadata('storyId')))
        metadata = a.findParent('td')
        metadatachunks = self.utf8FromSoup(None,metadata).split('<br />')
        # process metadata for this story.
        self.setDescription(url,metadatachunks[1])
        #self.story.setMetadata('description', metadatachunks[1])

        # First line of the stuff with ' - ' separators
        moremeta = metadatachunks[2]
        moremeta = re.sub(r'<[^>]+>','',moremeta) # strip tags.
        
        moremetaparts = moremeta.split(' - ')
        
        # first part is category--whofic.com has categories
        # Doctor One-11, Torchwood, etc.  We're going to
        # prepend any with 'Doctor' or 'Era' (Multi-Era, Other
        # Era) as 'Doctor Who'.
        #
        # Also push each in as 'extra tags'.
        category = moremetaparts[0]
        if 'Doctor' in category or 'Era' in category :
            self.story.addToList('category','Doctor Who')
            
        for cat in category.split(', '):
            self.story.addToList('category',cat)

        # next in that line is age rating.
        self.story.setMetadata('rating',moremetaparts[1])

        # after that is a possible list fo specific warnings,
        # Explicit Violence, Swearing, etc
        if "None" not in moremetaparts[2]:
            for warn in moremetaparts[2].split(', '):
                self.story.addToList('warnings',warn)

        # then genre.  It's another comma list.  All together
        # in genre, plus each in extra tags.
        genre=moremetaparts[3]
        for g in genre.split(r', '):
            self.story.addToList('genre',g)

        # line 3 is characters.
        chars = metadatachunks[3]
        charsearch="<i>Characters:</i>"
        if charsearch in chars:
            chars = chars[metadatachunks[3].index(charsearch)+len(charsearch):]
            for c in chars.split(','):
                if c.strip() != u'None':
                    self.story.addToList('characters',c)
            
        # the next line is stuff with ' - ' separators *and* names--with tags.
        moremeta = metadatachunks[5]
        moremeta = re.sub(r'<[^>]+>','',moremeta) # strip tags.
        
        moremetaparts = moremeta.split(' - ')

        for part in moremetaparts:
            (name,value) = part.split(': ')
            name=name.strip()
            value=value.strip()
            if name == 'Published':
                self.story.setMetadata('datePublished', makeDate(value, '%Y.%m.%d'))
            if name == 'Updated':
                self.story.setMetadata('dateUpdated', makeDate(value, '%Y.%m.%d'))
            if name == 'Completed':
                if value == 'Yes':
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')
            if name == 'Word Count':
                self.story.setMetadata('numWords', value)

        try:
            # Find Series name from series URL.
            a = metadata.find('a', href=re.compile(r"series.php\?seriesid=\d+"))
            series_name = a.string
            series_url = 'http://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = bs.BeautifulSoup(self._fetchUrl(series_url))
            storyas = seriessoup.findAll('a', href=re.compile(r'^viewstory.php\?sid=\d+$'))
            i=1
            for a in storyas:
                if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId')):
                    self.setSeries(series_name, i)
                    self.story.setMetadata('seriesUrl',series_url)
                    break
                i+=1
            
        except:
            # I find it hard to care if the series parsing fails
            pass
            
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        

        # hardly a great identifier, I know, but whofic really doesn't
        # give us anything better to work with.
        span = soup.find('span', {'style' : 'font-size: 100%;'})

        if None == span:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return self.utf8FromSoup(url,span)

def getClass():
    return WhoficComSiteAdapter

