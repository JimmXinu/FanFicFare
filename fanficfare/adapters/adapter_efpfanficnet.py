# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team, 2018 FanFicFare team
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
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return EFPFanFicNet

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class EFPFanFicNet(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','efp')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d/%m/%y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'efpfanfic.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/viewstory.php?sid=1234"

    def getSiteURLPattern(self):
        return r"https?://(www\.)?"+re.escape(self.getSiteDomain()+"/viewstory.php?sid=")+r"\d+$"

    ## Login seems to be reasonably standard across eFiction sites.
    def needToLoginCheck(self, data):
        if( 'Fai il login e leggi la storia!' in data or
            'Questa storia presenta contenuti non adatti ai minori' in data ):
            return True
        else:
            return False

    def performLogin(self, url):
        params = {}

        if self.password:
            params['penname'] = self.username
            params['password'] = self.password
        else:
            params['penname'] = self.getConfig("username")
            params['password'] = self.getConfig("password")
        params['cookiecheck'] = '1'
        params['submit'] = 'Invia'

        loginUrl = 'https://' + self.getSiteDomain() + '/user.php?sid='+self.story.getMetadata('storyId')
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['penname']))

        d = self._fetchUrl(loginUrl, params)

        if '<a class="menu" href="newaccount.php">' in d : # register for new account link
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['penname']))
            raise exceptions.FailedToLogin(url,params['penname'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        # if "Access denied. This story has not been validated by the adminstrators of this site." in data:
        #     raise exceptions.AccessDenied(self.getSiteDomain() +" says: Access denied. This story has not been validated by the adminstrators of this site.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        a = soup.find('a', href=re.compile(r'^viewstory\.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a))

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php\?uid=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','https://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapter selector
        select = soup.find('select', { 'name' : 'sid' } )

        if select is None:
            # no selector found, so it's a one-chapter story.
            self.add_chapter(self.story.getMetadata('title'),url)
        else:
            allOptions = select.findAll('option', {'value' : re.compile(r'viewstory')})
            for o in allOptions:
                url = u'https://%s/%s' % ( self.getSiteDomain(),
                                          o['value'])
                # just in case there's tags, like <i> in chapter titles.
                title = stripHTML(o)
                self.add_chapter(title,url)

        self.story.setMetadata('language','Italian')

        # normalize story URL to first chapter if later chapter URL was given:
        url = self.get_chapter(0,'url').replace('&i=1','')
        logger.debug("Normalizing to URL: "+url)
        self._setURL(url)
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])


        # eFiction sites don't help us out a lot with their meta data
        # formating, so it's a little ugly.

        storya = None
        authsoup = None
        storyblock = None
        authurl = self.story.getMetadata('authorUrl')

        ## author can have more than one page of stories.
        while storyblock == None:

            # no storya, but do have authsoup--we're looping on author pages.
            if authsoup != None:
                # last author link with offset should be the 'next' link.
                authurl = u'https://%s/%s' % ( self.getSiteDomain(),
                                              authsoup.findAll('a',href=re.compile(r'viewuser\.php\?uid=\d+&catid=&offset='))[-1]['href'] )

            # Need author page for most of the metadata.
            logger.debug("fetching author page: (%s)"%authurl)
            authsoup = self.make_soup(self._fetchUrl(authurl))
            #print("authsoup:%s"%authsoup)

            storyas = authsoup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+r'&i=1$'))
            for storya in storyas:
                #print("======storya:%s"%storya)
                storyblock = storya.findParent('div',{'class':'storybloc'})
                #print("======storyblock:%s"%storyblock)
                if storyblock != None:
                    continue

        self.setDescription(url,storyblock.find('div', {'class':'introbloc'}))

        noteblock = storyblock.find('div', {'class':'notebloc'})
        #print("%s"%noteblock)
        notetext = ("%s" % noteblock).replace("<br/>"," |")
        # <div class="notebloc">Autore: <a href="viewuser.php?uid=243036">Cendrillon89</a> | Pubblicata: 23/10/12 | Aggiornata: 30/10/12 | Rating: Arancione | Genere: Drammatico, Sentimentale | Capitoli: 10 | Completa<br />
        # Tipo di coppia: Het |  Personaggi: Akasuna no Sasori , Akatsuki, Nuovo Personaggio |   Note: OOC | Avvertimenti: Tematiche delicate<br />
        # Categoria: <a href="categories.php?catid=1&amp;parentcatid=1">Anime & Manga</a> > <a href="categories.php?catid=108&amp;parentcatid=108">Naruto</a> | Contesto: Naruto Shippuuden | Leggi le <a href="reviews.php?sid=1331275&amp;a=">3</a> recensioni</div>

        cats = noteblock.findAll('a',href=re.compile(r'browse.php\?type=categories'))
        for cat in cats:
            self.story.addToList('category',cat.string)

        for item in notetext.split("|"):
            if ":" in item:
                (label,value) = item.split(":")
                label=label.strip()
                value=value.strip()
            else:
                label=value=item.strip()

            if 'Pubblicata' in label:
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))

            if 'Aggiornata' in label:
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

            if label == "Completa":
                self.story.setMetadata('status', 'Completed')

            if label == "In corso":
                self.story.setMetadata('status', 'In-Progress')

            if 'Rating' in label:
                self.story.setMetadata('rating', value)

            if 'Personaggi' in label:
                for val in value.split(","):
                    self.story.addToList('characters',val)

            if 'Genere' in label:
                for val in value.split(","):
                    self.story.addToList('genre',val)

            if 'Coppie' in label:
                for val in value.split(","):
                    self.story.addToList('ships',val)

            if 'Avvertimenti' in label:
                for val in value.split(","):
                    if val != "None":
                        self.story.addToList('warnings',val)

            # 'extra' metadata for this adapter:

            if 'Tipo di coppia' in label:
                for val in value.split(","):
                    self.story.addToList('type',val)

            if 'Note' in label:
                for val in value.split(","):
                    if val != "None":
                        self.story.addToList('notes',val)

            if 'Contesto' in label:
                self.story.setMetadata('context', value)

            ## Note--efp doesn't provide word count.

        try:
            # Find Series name from series URL.
            a = soup.find('a', href=re.compile(r"viewseries.php\?ssid=\d+&i=1"))
            series_name = a.string
            series_url = 'https://'+self.host+'/'+a['href']

            # use BeautifulSoup HTML parser to make everything easier to find.
            seriessoup = self.make_soup(self._fetchUrl(series_url))
            # can't use ^viewstory...$ in case of higher rated stories with javascript href.
            storyas = seriessoup.findAll('a', href=re.compile(r'viewstory.php\?sid=\d+&i=1'))
            i=1
            for a in storyas:
                if a['href'] == ('viewstory.php?sid='+self.story.getMetadata('storyId'))+'&i=1':
                    self.setSeries(series_name, i)
                    self.story.setMetadata('seriesUrl',series_url)
                    break
                i+=1

        except:
            # I find it hard to care if the series parsing fails
            pass

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'class' : 'storia'})

        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # remove any header and 'o:p' tags.
        for tag in div.findAll("head") + div.findAll("o:p"):
            tag.extract()

        # change any html and body tags to div.
        for tag in div.findAll("html") + div.findAll("body"):
            tag.name='div'

        # remove extra bogus doctype.
        #<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        return re.sub(r"<!DOCTYPE[^>]+>","",self.utf8FromSoup(url,div))
