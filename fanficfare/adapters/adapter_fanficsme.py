#  -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team, 2018 FanFicFare team
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

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return FanFicsMeAdapter


logger = logging.getLogger(__name__)

class FanFicsMeAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        self.full_work_soup = None
        self.use_full_work_soup = True

        ## All Russian as far as I know.
        self.story.setMetadata('language','Russian')

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(),url)
        if m:
            self.story.setMetadata('storyId',m.group('id'))

            # normalized story URL.
            self._setURL('https://' + self.getSiteDomain() + '/fic'+self.story.getMetadata('storyId'))
        else:
            raise exceptions.InvalidStoryURL(url,
                                             self.getSiteDomain(),
                                             self.getSiteExampleURLs())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','ffme')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d.%m.%Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'fanfics.me'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/fic1234 https://"+cls.getSiteDomain()+"/read.php?id=1234 https://"+cls.getSiteDomain()+"/read.php?id=1234&chapter=2"

    def getSiteURLPattern(self):
        # https://fanfics.me/fic137282
        # https://fanfics.me/read.php?id=137282
        # https://fanfics.me/read.php?id=137282&chapter=2
        # https://fanfics.me/download.php?fic=137282&format=epub
        return r"https?://"+re.escape(self.getSiteDomain())+r"/(fic|read\.php\?id=|download\.php\?fic=)(?P<id>\d+)"

    ## Login
    def needToLoginCheck(self, data):
        return '<form name="autent" action="https://fanfics.me/autent.php" method="post">' in data

    def performLogin(self, url):
        '''
            <form name="autent" action="https://fanfics.me/autent.php" method="post">
                Имя:<br>
                <input class="input_3" type="text" name="name" id="name"><br>
                Пароль:<br>
                <input class="input_3" type="password" name="pass" id="pass"><br>
                <input type="checkbox" name="nocookie" id="nocookie" />&nbsp;<label for="nocookie">Чужой&nbsp;компьютер</label><br>
                <input class="modern_button" type="submit" value="Войти">
                <div class="lostpass center"><a href="/index.php?section=lostpass">Забыл пароль</a></div>
        '''
        params = {}
        if self.password:
            params['name'] = self.username
            params['pass'] = self.password
        else:
            params['name'] = self.getConfig("username")
            params['pass'] = self.getConfig("password")

        loginUrl = 'https://' + self.getSiteDomain() + '/autent.php'
        logger.info("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                            params['name']))
        ## must need a cookie or something.
        self.get_request(loginUrl, usecache=False)
        d = self.post_request(loginUrl, params, usecache=False)

        if self.needToLoginCheck(d):
            logger.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              params['name']))
            raise exceptions.FailedToLogin(url,params['name'])
            return False
        else:
            return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):

        url = self.url
        logger.info("url: "+url)

        data = self.get_request(url)

        soup = self.make_soup(data)

        ## restrict meta searches to header.
        fichead = soup.find('div',class_='FicHead')
        def get_meta_content(title):
            val_label = fichead.find('div',string=re.compile(u'^'+title+u':'))
            if val_label:
                return val_label.find_next('div')

        ## fanfics.me doesn't have separate adult--you have to set
        ## your age to 18+ in your user account
        ## Rating
        ## R, NC-17, PG-13 require login
        ## doesn't: General
        #('Рейтинг', 'rating', False, False)
        # val_label = fichead.find('div',string=u'Рейтинг:')
        # val = stripHTML(val_label.find_next('div'))
        # logger.debug(val)
        self.story.setMetadata('rating',stripHTML(get_meta_content(u'Рейтинг')))

        ## Need to login for any rating higher than General.
        if self.story.getMetadataRaw('rating') != 'General' and self.needToLoginCheck(data):
            self.performLogin(url)
            # reload after login.
            data = self.get_request(url,usecache=False)
            soup = self.make_soup(data)
            fichead = soup.find('div',class_='FicHead')

        ## Title
        ## <h1>Третья сторона&nbsp;<span class="small green">(гет)</span></h1>
        h = fichead.find('h1')
        span = h.find('span')
        ## I haven't found a term for what fanfics.me calls this, but
        ## it translates to Get Jen Slash Femslash
        self.story.addToList('category',stripHTML(span)[1:-1])
        span.extract()
        self.story.setMetadata('title',stripHTML(h))

        ## author(s):
        content = get_meta_content(u'Авторы?')
        if content:
            alist = content.find_all('a', class_='user')
            for a in alist:
                self.story.addToList('authorId',a['href'].split('/user')[-1])
                self.story.addToList('authorUrl','https://'+self.host+a['href'])
                self.story.addToList('author',stripHTML(a))
            # can be deliberately anonymous.
            if not alist:
                self.story.setMetadata('author','Anonymous')
                self.story.setMetadata('authorUrl','https://'+self.host)
                self.story.setMetadata('authorId','0')

        # translator(s) in different strings
        content = get_meta_content(u'Переводчикк?и?')
        if content:
            for a in content.find_all('a', class_='user'):
                self.story.addToList('translatorsId',a['href'].split('/user')[-1])
                self.story.addToList('translatorsUrl','https://'+self.host+a['href'])
                self.story.addToList('translators',stripHTML(a))

        # If there are translators, but no authors, copy translators to authors.
        if self.story.getList('translators') and not self.story.getList('author'):
            self.story.extendList('authorId',self.story.getList('translatorsId'))
            self.story.extendList('authorUrl',self.story.getList('translatorsUrl'))
            self.story.extendList('author',self.story.getList('translators'))

        # beta(s)
        content = get_meta_content(u'Бета')
        if content:
            for a in content.find_all('a', class_='user'):
                self.story.addToList('betasId',a['href'].split('/user')[-1])
                self.story.addToList('betasUrl','https://'+self.host+a['href'])
                self.story.addToList('betas',stripHTML(a))

        content = get_meta_content(u'Фандом')
        self.story.extendList('fandoms', [ stripHTML(a) for a in
                                           fichead.find_all('a',href=re.compile(r'/fandom\d+$')) ] )

        ## 'Characters' header has both ships and chars lists
        content = get_meta_content(u'Персонажи')
        if content:
            self.story.extendList('ships', [ stripHTML(a) for a in
                                             content.find_all('a',href=re.compile(r'/paring\d+_\d+$')) ] )
            for ship in self.story.getList('ships'):
                self.story.extendList('characters', ship.split('/'))
            self.story.extendList('characters', [ stripHTML(a) for a in
                                                  content.find_all('a',href=re.compile(r'/character\d+$')) ] )

        self.story.extendList('genre',stripHTML(get_meta_content(u'Жанр')).split(', '))
        ## fanfics.me includes 'AU' and 'OOC' as warnings...
        content = get_meta_content(u'Предупреждение')
        if content:
            self.story.extendList('warnings',stripHTML(content).split(', '))

        content = get_meta_content(u'События')
        if content:
            self.story.extendList('events', [ stripHTML(a) for a in
                                              content.find_all('a',href=re.compile(r'/find\?keyword=\d+$')) ] )

        ## Original work block
        content = get_meta_content(u'Оригинал')
        if content:
            # only going to record URL.
            titletd = content.find('td',string=u'Ссылка:')
            self.story.setMetadata('originUrl',stripHTML(titletd.find_next('td')))

        ## size block, only saving word count.
        content = get_meta_content(u'Размер')
        words = stripHTML(content.find('a'))
        words = re.sub(r'[^0-9]','',words) # only keep numbers
        self.story.setMetadata('numWords',words)

        ## status by color code
        statuscolors = {'red':'In-Progress',
                        'green':'Completed',
                        'blue':'Hiatus'}
        content = get_meta_content(u'Статус')
        self.story.setMetadata('status',statuscolors[content.span['class'][0]])

        # desc
        self.setDescription(url,soup.find('div',id='summary_'+self.story.getMetadata('storyId')))

        # cover
        div = fichead.find('div',class_='FicHead_cover')
        if div:
            # get the larger version.
            self.setCoverImage(self.url,div.img['src'].replace('_200_300',''))

        # dates
        # <span class="DateUpdate" title="Опубликовано 22.04.2020, изменено 22.04.2020">22.04.2020 - 22.04.2020</span>
        datespan = soup.find('span',class_='DateUpdate')
        dates = stripHTML(datespan).split(" - ")
        self.story.setMetadata('datePublished', makeDate(dates[0], self.dateformat))
        self.story.setMetadata('dateUpdated', makeDate(dates[1], self.dateformat))

        # series
        seriesdiv = soup.find('div',id='fic_info_content_serie')
        if seriesdiv:
            seriesa = seriesdiv.find('a', href=re.compile(r'/serie\d+$'))
            i=1
            for a in seriesdiv.find_all('a', href=re.compile(r'/fic\d+$')):
                if a['href'] == ('/fic'+self.story.getMetadata('storyId')):
                    self.setSeries(stripHTML(seriesa), i)
                    self.story.setMetadata('seriesUrl','https://'+self.host+seriesa['href'])
                    break
                i+=1


        chapteruls = soup.find_all('ul',class_='FicContents')
        if chapteruls:
            for ul in chapteruls:
                # logger.debug(ul.prettify())
                for chapter in ul.find_all('li'):
                    a = chapter.find('a')
                    # logger.debug(a.prettify())
                    if a and a.has_attr('href'):
                        # logger.debug(chapter.prettify())
                        self.add_chapter(stripHTML(a),'https://' + self.getSiteDomain() + a['href'])
        else:
            self.add_chapter(self.story.getMetadata('title'),
                             'https://' + self.getSiteDomain() +
                             '/read.php?id='+self.story.getMetadata('storyId')+'&chapter=0')

        return

    # grab the text for an individual chapter.
    def getChapterTextNum(self, url, index):
        logger.debug('Getting chapter text for: %s index: %s' % (url,index))
        m = re.match(r'.*&chapter=(\d+).*',url)
        if m:
            index=m.group(1)
            logger.debug("Using index(%s) from &chapter="%index)

        chapter_div = None
        if self.use_full_work_soup and self.getConfig("use_view_full_work",True) and self.num_chapters() > 1:
            logger.debug("USE view_full_work")
            ## Assumed view_adult=true was cookied during metadata
            if not self.full_work_soup:
                self.full_work_soup = self.make_soup(self.get_request(
                        'https://' + self.getSiteDomain() + '/read.php?id='+self.story.getMetadata('storyId')))

            whole_dl_soup = self.full_work_soup
            chapter_div = whole_dl_soup.find('div',{'id':'c%s'%(index)})
            if not chapter_div:
                self.use_full_work_soup = False
                logger.warning("c%s not found in view_full_work--ending use_view_full_work"%(index))
        if chapter_div == None:
            whole_dl_soup = self.make_soup(self.get_request(url))
            chapter_div = whole_dl_soup.find('div',{'id':'c%s'%(index)})
            if None == chapter_div:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chapter_div)
