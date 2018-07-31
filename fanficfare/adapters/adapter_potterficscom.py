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
import datetime
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter

# This function is called by the downloader in all adapter_*.py files
# in this dir to register the adapter class.  So it needs to be
# updated to reflect the class below it.  That, plus getSiteDomain()
# take care of 'Registering'.
def getClass():
    return PotterFicsComAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class PotterFicsComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL. gets rid of chapter if there, left with chapter index URL
            nurl = "https://"+self.getSiteDomain()+"/historias/"+self.story.getMetadata('storyId')
            self._setURL(nurl)
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())


        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','potficscom')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'www.potterfics.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://www.potterfics.com/historias/12345 https://www.potterfics.com/historias/12345/capitulo-1 "

    def getSiteURLPattern(self):
        #https://www.potterfics.com/historias/127583
        #https://www.potterfics.com/historias/127583/capitulo-1
        #https://www.potterfics.com/historias/127583/capitulo-4
        #https://www.potterfics.com/historias/92810              -> Complete story
        #https://www.potterfics.com/historias/111194             -> Complete, single chap
        p = r"https?://"+re.escape(self.getSiteDomain()+"/historias/")+\
            r"(?P<id>\d+)(/capitulo-(?P<ch>\d+))?/?$"
        return p

    def needToLoginCheck(self, data):
        # partials used to avoid having to figure out what was wrong
        # with included utf8 higher chars.
        if 'Para ver esta historia, por favor inicia tu sesi' in data \
                or '<script>alert("El nombre de usuario o contrase' in data:
            return True
        else:
            return False

    def performLogin(self,url):
        params = {}

        if self.password:
            params['login_usuario'] = self.username
            params['login_password'] = self.password
        else:
            params['login_usuario'] = self.getConfig("username")
            params['login_password'] = self.getConfig("password")
        params['login_ck'] = '1'

        loginUrl = 'https://www.potterfics.com/secciones/usuarios/login.php'
        logger.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              params['login_usuario']))
        d = self._postUrl(loginUrl,params)

        #print("d:%s"%d)
        if '<script>alert("El nombre de usuario o contrase' in d:
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['login_usuario']))
            raise exceptions.FailedToLogin(url,params['login_usuario'])
            return False
        else:
            return True

    def extractChapterUrlsAndMetadata(self):

        #this converts '/historias/12345' to 'https://www.potterfics.com/historias/12345'
        def makeAbsoluteURL(url):
            if url[0] == '/':
                url = 'https://'+self.getSiteDomain()+url
            return url

        #use this to get month numbers from Spanish months
        SpanishMonths = {
            'enero'      : '01',
            'febrero'    : '02',
            'marzo'      : '03',
            'abril'      : '04',
            'mayo'       : '05',
            'junio'      : '06',
            'julio'      : '07',
            'agosto'     : '08',
            'septiembre' : '09',
            'octubre'    : '10',
            'noviembre'  : '11',
            'diciembre'  : '12'
            }

        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        if "Esta historia no existe. Probablemente ha sido eliminada." in data:
            raise exceptions.StoryDoesNotExist(self.url)

        ##print data

        #deal with adult content login
        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url,usecache=False)

        #set constant meta for this site:
        #Set Language = Spanish
        self.story.setMetadata('language', 'Spanish')
        #Set Category = Harry Potter
        #  This is better done in plugin-defaults.ini and defaults.ini
        #  by adding a section for this site with the line:
        #  extracategories:Harry Potter
        #self.story.addToList('category','Harry Potter')

        #get the rest of the meta
        # use BeautifulSoup HTML parser to make everything easier to find.
        #self closing br and img present!
        soup = self.make_soup(data)

        #we want the second table directly under the body, contains all the metadata
        table = soup.html.body.findAll('table', recursive=False)[1]
        #within that, we want the first row, three cell
        cell = table.tr.find_all('td')[2]

        #find first metadata block--isn't first if logged in
        mb = cell.div.findNextSibling('div',{'align':'left'})
        #Get meta...
        self.story.setMetadata('title', stripHTML(mb.b))
        #strip out brackets on rating
        self.story.setMetadata('rating', mb.span.string[1:-1])
        #Completion status is denoted by the presence of this image:
        if mb.find('img',title="Historia terminada"):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        #find next metadata block
        #author details
        mb = mb.findNextSibling('div')
        self.story.setMetadata('author', mb.b.a.string.strip())
        self.story.setMetadata('authorUrl', makeAbsoluteURL(mb.b.a['href']))
        self.story.setMetadata('authorId', self.story.getMetadata('authorUrl').split('/')[4])
        #dates and times
        mb = mb.find('span')
        #posted/published = Escrita
        date = mb.find(text=re.compile('Escrita el ')).strip().split()
        year = int(date[7][:-1]) # need to remove the last char from year, it is a comma
        month = int(SpanishMonths[date[5].lower()])
        day = int(date[3])
        time = date[8].split(':')
        hour = int(time[0])
        minute = int(time[1])
        self.story.setMetadata('datePublished', datetime.datetime(year, month, day, hour, minute))
        #updated = Actualizada
        date = mb.find(text=re.compile('Actualizada el ')).strip().split()
        year = int(date[7][:-1]) # need to remove the last char from year, it is a comma
        month = int(SpanishMonths[date[5].lower()])
        day = int(date[3])
        time = date[8].split(':')
        hour = int(time[0])
        minute = int(time[1])
        self.story.setMetadata('dateUpdated', datetime.datetime(year, month, day, hour, minute))

        mb = mb.span.findNextSibling('span').findNextSibling('span')
        wc = mb.find(text=re.compile(' palabras en total')).strip()
        self.story.setMetadata('numWords', wc.split()[0])

        #then we come to categories and genres. Oh dear. On this site, categories hold everything from genre, to ships, to crossovers.
        #To make things worse, there is also another genre field, which often holds similar/duplicate info. Links to genre pages do not work
        #though, so perhaps those will be phased out?
        #for now, put them all into the genre list
        links = mb.findAll('a',href=re.compile('/(categorias|generos)/\d+'))
        genlist = [i.string.strip() for i in links]
        self.story.extendList('genre',genlist)

        #get the chapter urls
        #we can go back to the table cell we found before
        #get its last element and work backwards to find the last ordered list on the page
        list = cell.contents[len(cell)-1].findPrevious('ol')
        revs = 0
        chnum = 0
        for li in list:
            chnum += 1
            chTitle = unicode(chnum) + '. ' + li.a.b.string.strip()
            chURL = makeAbsoluteURL(li.a['href'])
            self.add_chapter(chTitle,chURL)
            #Get reviews, add to total
            revs += int(li.div.a.string.split()[0])

        self.story.setMetadata('reviews', revs)

        #Now for the description... this may be tricky...
        #if it is there (doesn't have to be), it will be before the chapter list,
        #separated by a horizontal rule, and after the google ad bar

        #get list's parent div
        mb = list.parent
        #get the div before that, will either be the description, or the google ad bar
        mb = mb.findPreviousSibling('div')
        if 'google_ad_client' in unicode(mb):
            #couldn't find description, leaving it blank
            pass
        else:
            self.setDescription(url,mb)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'id' : 'cuerpoHistoria'})
        if None == div:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,div)
