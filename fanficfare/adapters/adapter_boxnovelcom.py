from __future__ import absolute_import
from datetime import datetime, timedelta
import logging
import re
import json

logger = logging.getLogger(__name__)

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from .base_adapter import BaseSiteAdapter, makeDate


def getClass():
    return BoxNovelComAdapter

logger = logging.getLogger(__name__)

class BoxNovelComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self._setURL(re.match(r"(http.+?/novel/.+?)(?:/|$)", url).group(1) + '/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','bnc')

        # No language given on site. Assume all of it is in English.
        self.story.setMetadata('language','English')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        return 'boxnovel.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://"+cls.getSiteDomain()+"/novel/title-of-the-novel-part120 https://"+cls.getSiteDomain()+"/novel/title-of-the-novel-part-120/chapter-120/"

    def getSiteURLPattern(self):
        return r"https?://"+re.escape(self.getSiteDomain()+"/novel/") + r"[\d\-a-zA-Z]+"

    def extractChapterUrlsAndMetadata(self,get_cover=True):
        url=self.url
        logger.debug("URL: "+url)
        data = self.get_request(url)
        soup = self.make_soup(data)

        # Getting the storyId from the class to avoid using the title as storyId
        for cls in soup.find('body')['class']:
            if cls.startswith('postid-'):
                post_id = cls.split('-')[1]
                break
        self.story.setMetadata('storyId', post_id)
        logger.debug("storyId: (%s)"%self.story.getMetadata('storyId'))

        # Title
        title = soup.find('div',{'class':'post-title'}).h1
        self.story.setMetadata('title',stripHTML(title))

        # Find author. The site doesn't give numeric authorId so this will have to do.
        a = soup.find('div',{'class':'author-content'}).findAll('a')
        for a in a:
            self.story.addToList('authorUrl',a['href'])
            self.story.addToList('authorId',a.text)
            self.story.addToList('author',a.text)
        logger.debug("authorId: (%s)"%self.story.getMetadata('authorId'))
        logger.debug("authorUrl: (%s)"%self.story.getMetadata('authorUrl'))

        # Alternative or original title
        alt = soup.find('h5', string=re.compile(r'\s*Alternative\s*'))
        if alt:
            alttitle = alt.find_parent().find_next_sibling()
            self.story.setMetadata('alttitle',stripHTML(alttitle))

        summary=soup.find('div', {'class':'description-summary'}).find('p', class_='c_000')
        if not summary:
            # Older style summary i assume?
            summary=soup.find('div', {'id':'editdescription'})
            # We are removing the div with the website's name
            marker = summary.find('div', string=re.compile(r'\s*B0XNʘVEL.C0M\s*'))
            if marker:
                marker.extract()
            summary = re.sub(r'\n+</div>$', '</div>', str(summary))
        if summary:
            self.setDescription(url,summary)

        ffmeta = soup.find('div', {'class':'tab-summary'})

        # The category will be eg. 'Chinese Web Novel'. I suppose it is good enough
        category = ffmeta.find('h5', string=re.compile(r'\s*Type\s*')).find_parent().find_next_sibling()
        self.story.setMetadata('category', stripHTML(category))

        # Tags
        tags = ffmeta.find('div', {'class':'genres-content'}).findAll('a')
        for tag in tags:
            self.story.addToList('genre',stripHTML(tag))

        if 'Completed' in ffmeta.find('h5', string=re.compile(r'\s*Status\s*')).find_parent().find_next_sibling():
            self.story.setMetadata('status', 'Completed')
        else:
            self.story.setMetadata('status', 'In-Progress')

        avrgrate = ffmeta.find('span',{'id':'averagerate'})
        if avrgrate is not None:
            avrg = float(stripHTML(avrgrate))
            self.story.setMetadata('averrating', avrg)

        if get_cover:
            cover = ffmeta.find('div', {'class':"summary_image"})
            if cover is not None:
                cover = cover.a.img['data-src']
                logger.debug("Cover for %s (%s)"%(url,cover))
                self.setCoverImage(url,cover)

        # Find the chapters. The post is necessary as the website doesn't reveal the chapter index.
        tocurl = url + 'ajax/chapters/'
        params = {}
        chaptersTOC = self.make_soup(self.post_request(tocurl,params,usecache=False))
        chapters = chaptersTOC.find('ul', {'class':'main version-chap no-volumn'}).findAll('li', {'class':'wp-manga-chapter'})
        if chapters is not None:
            last = len(chapters) - 1
            for i, chapter in enumerate(reversed(chapters)):
                chapterUrl=chapter.find('a')
                chapterTitle = stripHTML(chapterUrl)

                date = stripHTML(chapter.find('span', {'class':'chapter-release-date'}))
                if 'ago' in date:
                    ago, unit = int(date.split()[0]), date.split()[1]
                    if 'hours' in unit:
                        time_delta = timedelta(hours=ago)
                    if 'days' in unit:
                        time_delta = timedelta(days=ago)
                    chapterDate = makeDate((datetime.now() - time_delta).strftime('%Y-%m-%d'), '%Y-%m-%d')
                else:
                    chapterDate = makeDate(date, '%B %d, %Y')
                if i == 0:
                    pubdate = chapterDate
                if i == last:
                    update = chapterDate

                self.add_chapter(chapterTitle,chapterUrl['href'],{'date':chapterDate.strftime(self.getConfig("datechapter_format","%Y-%m-%d"))})
        else:
            raise exceptions.FailedToDownload("Missing required element for %s! POST failed?" % url)

        self.story.setMetadata('dateUpdated', update)
        self.story.setMetadata('datePublished', pubdate)
        logger.debug("numChapters: (%s)"%self.story.getMetadata('numChapters'))

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)
        soup = self.make_soup(self.get_request(url))

        chapter = soup.find('div', {'class' : 'cha-words'})
        if not chapter:
            # Old style chapter HTML?
            chapter = soup.find('div', {'class' : 'reading-content'}).find('div', {'class' : 'text-left'})
            if not chapter:
                raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        ads = chapter.findAll('div', {'class':'adsbyvli'})
        for x in ads:
            x.find_parent().extract()

        # Watermark?
        try:
            chapter.find('div', string=re.compile(r"\s*B0XNʘVEL.C0M\s*")).extract()
        except (AttributeError, TypeError):
            pass

        return self.utf8FromSoup(url,chapter)
