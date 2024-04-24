# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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
from .. import translit


from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition

from .base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return FicBookNetAdapter


logger = logging.getLogger(__name__)

class FicBookNetAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.path.split('/',)[2])


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/readfic/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','fbn')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%d %m %Y"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'ficbook.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/readfic/12345 https://"+cls.getSiteDomain()+"/readfic/93626/246417#part_content"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/readfic/")+r"\d+"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        url=self.url
        logger.debug("URL: "+url)
        data = self.get_request(url)

        soup = self.make_soup(data)

        adult_div = soup.find('div',id='adultCoverWarning')
        if adult_div:
            if self.is_adult or self.getConfig("is_adult"):
                adult_div.extract()
            else:
                raise exceptions.AdultCheckRequired(self.url)


        ## Title
        a = soup.find('section',{'class':'chapter-info'}).find('h1')
        # kill '+' marks if present.
        sup = a.find('sup')
        if sup:
            sup.extract()
        self.story.setMetadata('title',stripHTML(a))
        logger.debug("Title: (%s)"%self.story.getMetadata('title'))

        # Find authorid and URL from... author url.
        # assume first avatar-nickname -- there can be a second marked 'beta'.
        a = soup.find('a',{'class':'creator-username'})
        self.story.setMetadata('authorId',a.text) # Author's name is unique
        self.story.setMetadata('authorUrl','https://'+self.host+a['href'])
        self.story.setMetadata('author',a.text)
        logger.debug("Author: (%s)"%self.story.getMetadata('author'))

        fullmon = {"yanvarya":"01", u"января":"01",
           "fievralya":"02", u"февраля":"02",
           "marta":"03", u"марта":"03",
           "aprielya":"04", u"апреля":"04",
           "maya":"05", u"мая":"05",
           "iyunya":"06", u"июня":"06",
           "iyulya":"07", u"июля":"07",
           "avghusta":"08", u"августа":"08",
           "sentyabrya":"09", u"сентября":"09",
           "oktyabrya":"10", u"октября":"10",
           "noyabrya":"11", u"ноября":"11",
           "diekabrya":"12", u"декабря":"12" }

        # Find the chapters:
        pubdate = None
        chapters = soup.find('ul', {'class' : 'list-of-fanfic-parts'})
        if chapters != None:
            for chapdiv in chapters.findAll('li', {'class':'part'}):
                chapter=chapdiv.find('a',href=re.compile(r'/readfic/'+self.story.getMetadata('storyId')+r"/\d+#part_content$"))
                churl='https://'+self.host+chapter['href']

                # Find the dates
                date_str = chapdiv.find('span', {'title': True})['title'].split(' г.')[0]
                # Remove additional characters
                date_str = date_str.replace('\u202f', '').replace('г. в', '').strip()
                for month_name, month_num in fullmon.items():
                    date_str = date_str.replace(month_name, month_num)
                chapterdate = makeDate(date_str,"%d %m %Y %H:%M")
                self.add_chapter(chapter,churl,
                                 {'date':chapterdate.strftime(self.getConfig("datechapter_format",self.getConfig("datePublished_format","%Y-%m-%d %H:%M")))})

                datespan = chapdiv.find('span')
                if pubdate == None and datespan:
                    pubdate = translit.translit(stripHTML(datespan))
                update = translit.translit(stripHTML(datespan))
        else:
            self.add_chapter(self.story.getMetadata('title'),url)
            self.story.setMetadata('numChapters',1)
            pubdate=translit.translit(stripHTML(soup.find('div',{'class':'title-area'}).find('span')))
            update=pubdate

        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))

        if not ',' in pubdate:
            pubdate=datetime.date.today().strftime(self.dateformat)
        if not ',' in update:
            update=datetime.date.today().strftime(self.dateformat)
        pubdate=pubdate.split(',')[0]
        update=update.split(',')[0]

        for (name,num) in fullmon.items():
            if name in pubdate:
                pubdate = pubdate.replace(name,num)
            if name in update:
                update = update.replace(name,num)

        ## remove extra ' г.' on date.
        update = update.replace(' г.','')
        pubdate = pubdate.replace(' г.','')
        self.story.setMetadata('dateUpdated', makeDate(update, self.dateformat))
        self.story.setMetadata('datePublished', makeDate(pubdate, self.dateformat))
        self.story.setMetadata('language','Russian')

        ## after site change, I don't see word count anywhere.
        # pr=soup.find('a', href=re.compile(r'/printfic/\w+'))
        # pr='https://'+self.host+pr['href']
        # pr = self.make_soup(self.get_request(pr))
        # pr=pr.findAll('div', {'class' : 'part_text'})
        # i=0
        # for part in pr:
        #     i=i+len(stripHTML(part).split(' '))
        # self.story.setMetadata('numWords', unicode(i))


        dlinfo = soup.find('div',{'class':'fanfic-main-info'})

        i=0
        fandoms = dlinfo.find('div', {'class' : 'mb-10'}).findAll('a', href=re.compile(r'/fanfiction/\w+'))
        for fandom in fandoms:
            self.story.addToList('category',fandom.string)
            i=i+1
        if i > 1:
            self.story.addToList('genre', u'Кроссовер')

        tags = soup.find('div',{'class':'tags'})
        if tags:
            for genre in tags.findAll('a',href=re.compile(r'/tags/')):
                self.story.addToList('genre',stripHTML(genre))

        ratingdt = dlinfo.find('div',{'class':re.compile(r'badge-rating-.*')})
        self.story.setMetadata('rating', stripHTML(ratingdt.find('span')))

        # meta=table.findAll('a', href=re.compile(r'/ratings/'))
        # i=0
        # for m in meta:
        #     if i == 0:
        #         self.story.setMetadata('rating', stripHTML(m))
        #         i=1
        #     elif i == 1:
        #         if not "," in m.nextSibling:
        #             i=2
        #         self.story.addToList('genre', m.find('b').text)
        #     elif i == 2:
        #         self.story.addToList('warnings', m.find('b').text)

        if dlinfo.find('div', {'class':'badge-status-finished'}):
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        paircharsdt = soup.find('strong',string='Пэйринг и персонажи:')
        # site keeps both ships and indiv chars in /pairings/ links.
        if paircharsdt:
            for paira in paircharsdt.find_next('div').find_all('a', href=re.compile(r'/pairings/')):
                if 'pairing-highlight' in paira['class']:
                    self.story.addToList('ships',stripHTML(paira))
                    chars=stripHTML(paira).split('/')
                    for char in chars:
                        self.story.addToList('characters',char)
                else:
                    self.story.addToList('characters',stripHTML(paira))

        summary=soup.find('div', itemprop='description')
        # To get rid of an empty div on the title page.
        if summary.get_text():
            self.setDescription(url,summary)
            #self.story.setMetadata('description', summary.text)

        stats = soup.find('div', {'class' : 'mb-15 text-center'})
        targetdata = stats.find_all('span', {'class' : 'main-info'})
        for data in targetdata:
            svg_class = data.find('svg')['class'][0] if data.find('svg') else None
            value = int(stripHTML(data)) if stripHTML(data).isdigit() else 0

            if svg_class == 'ic_thumbs-up' and value > 0:
                self.story.setMetadata('likes', value)
            elif svg_class == 'ic_bubble-dark' and value > 0:
                self.story.setMetadata('reviews', value)
            elif svg_class == 'ic_bookmark' and value > 0:
                self.story.setMetadata('bookmarks', value)

        follows = int(stats.find('fanfic-follow-button')[':follow-count'])
        if follows > 0:
            self.story.setMetadata('follows', follows)

        collection = soup.find('fanfic-collections-link').find_parent('div')
        if collection:
            num_collections = int(collection.find('fanfic-collections-link')[':initial-count'])
            if num_collections > 0:
                self.story.setMetadata('numcollections', num_collections)
            if "collections" in self.getConfigList('extra_valid_entries'):
                collUrl = 'https://' + self.getSiteDomain() + soup.find('fanfic-collections-link')['url']
                p = self.get_request(collUrl)
                soupColl = self.make_soup(p)
                targetcoll = soupColl.find_all('div', {'class' : 'collection-thumb-info'})
                for coll in targetcoll:
                    o = coll.find('a', href=re.compile(r'/collections/'))
                    self.story.addToList('collections', stripHTML(o))

                if soupColl.find('div', {'class' : 'paging-description'}):
                    collpg = soupColl.find('div', {'class' : 'paging-description'}).select_one('div.paging-description b:last-child').text
                    print(collpg)
                    for c in range(int(collpg), 1, -1):
                        soupColl = self.make_soup(self.get_request(collUrl + '?p=' + str(c)))
                        targetcoll = soupColl.find_all('div', {'class' : 'collection-thumb-info'})
                        for coll in targetcoll:
                            o = coll.find('a', href=re.compile(r'/collections/'))
                            self.story.addToList('collections', stripHTML(o))

                logger.debug("Collections: (%s)"%self.story.getMetadata('collections'))


        targetpages = soup.find('strong',string='Размер:').find_next('div')
        if targetpages:
            pages = int(', '.join(re.findall(r'([\d,]+)\s+(?:страницы|страниц)', targetpages.text)))
            if pages != None and pages > 0:
                self.story.setMetadata('pages', pages)

        # Find dedication.
        ded = soup.find('div', {'class' : 'js-public-beta-dedication'})
        if ded != None:
            self.story.setMetadata('dedication',ded)

        # Find author comment
        comm = soup.find('div', {'class' : 'js-public-beta-author-comment'})
        if comm != None:
            self.story.setMetadata('authorcomment',comm)


    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))

        chapter = soup.find('div', {'id' : 'content'})
        if chapter == None: ## still needed?
            chapter = soup.find('div', {'class' : 'public_beta_disabled'})

        if None == chapter:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        # Remove ads that show up when using NSAPA proxy.
        if self.getConfig("use_nsapa_proxy",True):
            for ads in chapter.find_all('div', {'class' : 'ads-in-text'}):
                ads.extract()

        exclude_notes=self.getConfigList('exclude_notes')
        if 'headnotes' not in exclude_notes:
            # Find the headnote
            head_note = soup.find('div', {'class': 'part-comment-top'})
            if head_note:
                head_notes_content = head_note.find('div', {'class': 'js-public-beta-comment-before'}).get_text(strip=True)
                # Create the structure for the headnote
                head_notes_div_tag = soup.new_tag('div', attrs={'class': 'fff_chapter_notes fff_head_notes'})
                head_b_tag = soup.new_tag('b')
                head_b_tag.string = 'Примечания:'
                head_blockquote_tag = soup.new_tag('blockquote')
                head_blockquote_tag.string = head_notes_content
                head_notes_div_tag.append(head_b_tag)
                head_notes_div_tag.append(head_blockquote_tag)
                # Prepend the headnotes to the chapter
                chapter.insert(0, head_notes_div_tag)

        if 'footnotes' not in exclude_notes:
            # Find the endnote
            end_note = soup.find('div', {'class': 'part-comment-bottom'})
            if end_note:
                end_notes_content = end_note.find('div', {'class': 'js-public-beta-comment-after'}).get_text(strip=True)
                # Create the structure for the footnote
                end_notes_div_tag = soup.new_tag('div', attrs={'class': 'fff_chapter_notes fff_foot_notes'})
                end_b_tag = soup.new_tag('b')
                end_b_tag.string = 'Примечания:'
                end_blockquote_tag = soup.new_tag('blockquote')
                end_blockquote_tag.string = end_notes_content
                end_notes_div_tag.append(end_b_tag)
                end_notes_div_tag.append(end_blockquote_tag)
                # Append the endnotes to the chapter
                chapter.append(end_notes_div_tag)

        return self.utf8FromSoup(url,chapter)
