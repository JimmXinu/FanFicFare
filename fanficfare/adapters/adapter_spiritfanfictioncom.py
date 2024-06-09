from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re

from bs4 import BeautifulSoup
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import PY3, text_type as unicode

from .base_adapter import BaseSiteAdapter,  makeDate

def getClass():
    return SpiritFanfictionComAdapter

class SpiritFanfictionComAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        # get storyId from url--url validation guarantees query is only sid=1234
        self.storyId = unicode(self.getStoryId(url))
        self.story.setMetadata('storyId', self.storyId)

        # normalized story URL
        self._setURL('https://' + self.getSiteDomain() + '/historia/'+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev',self.getSiteAbbrev())

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        if PY3:
            self.dateformat = "%Y-%m-%dT%H:%M:%S%z"
            self.datelength = len("2015-04-15T22:16:15-03:00")
        else:
            ## python 2 had really poor timezone support and doesn't
            ## recognize %z.  This is a somewhat cheesy way to ignore
            ## the -/+dddd timezone when under py2.
            self.dateformat = "%Y-%m-%dT%H:%M:%S"
            self.datelength = len("2015-04-15T22:16:15")

        self.chapter_photoUrl = {}


    @staticmethod
    def getSiteDomain():
        return 'www.spiritfanfiction.com'


    @classmethod
    def getAcceptDomains(cls):
        return ['www.spiritfanfiction.com',
                'www.socialspirit.com.br',
               ]


    @classmethod
    def getSiteExampleURLs(cls):
        #Accepted formats
        #https://www.spiritfanfiction.com/historia/1234
        #https://www.spiritfanfiction.com/historia/story-name-1234
        return "https://"+cls.getSiteDomain()+"/historia/story-name-1234 https://"+cls.getSiteDomain()+"/historia/1234"


    @classmethod
    def getSiteURLPattern(self):
        #logger.debug(r"https?://(" + r"|".join([x.replace('.','\.') for x in self.getAcceptDomains()]) + r")/historia/(?:[a-zA-Z0-9-]+-)?(?P<storyId>\d+)")
        return r"https?://(" + r"|".join([x.replace('.','\.') for x in self.getAcceptDomains()]) + r")/historia/(?:[a-zA-Z0-9-]+-)?(?P<storyId>\d+)"


    @classmethod
    def getSiteAbbrev(cls):
        return 'spirit'


    def getStoryId(self, url):

        # get storyId from url--url validation guarantees query correct
        m = re.match(self.getSiteURLPattern(), url)
        if m:
            return m.group('storyId')
        else:
            raise exceptions.InvalidStoryURL(url, self.getSiteDomain(), self.getSiteExampleURLs())


    def extractChapterUrlsAndMetadata(self):

        data = self.get_request(self.url)
        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # Now go hunting for all the meta data and the chapter list.

        # Title
        title = soup.find('h1', {'class':'tituloPrincipal'})
        self.story.setMetadata('title', stripHTML(title.find('strong')))

        # Authors
        # Find authorid and URL
        authors = soup.findAll('span', {'class':'usuario'})

        for author in authors:
            self.story.addToList('authorId', author.find('a')['href'].split('/')[-1])
            self.story.addToList('authorUrl', author.find('a')['href'])
            self.story.addToList('author', stripHTML(author.find('strong')))

        # Cover image
        cover_img = soup.find('img', {'class':'imagemResponsiva'})
        if cover_img:
            self.setCoverImage(self.url, cover_img['src'])

        newestChapter = None
        self.newestChapterNum = None # save for comparing during update.
        # Find the chapters:
        chapters = soup.findAll('table', {'class':'listagemCapitulos espacamentoTop'})
        for chapter in chapters:

            for row in chapter.findAll('tr', {'class': 'listagem-textoBg1'}):  # Find each row with chapter info
                a = row.find('a')  # Chapter link

                # Datetime
                date = a.find_next('time')['datetime']
                chapterDate = makeDate(date[:self.datelength], self.dateformat).date()

                chapter_title = stripHTML(a.find('strong'))

                self.add_chapter(chapter_title, a.get('href'), {'date': chapterDate})

                if newestChapter == None or chapterDate > newestChapter:
                    newestChapter = chapterDate
                    self.newestChapterNum = self.story.getMetadata('numChapters')

        logger.debug('numChapters: (%s)', self.story.getMetadata('numChapters'))

        # Summary
        div_element = soup.find('div', {'class':'clearfix'})
        summary = div_element.find('div', class_='texto')

        strong_tag = summary.find('strong', text='Sinopse:')
        if strong_tag:
            strong_tag.decompose()

        self.decode_emails(summary)
        for a_tag in summary.find_all('a', {'data-cfemail': True}):
            email_text = a_tag.string
            a_tag.replace_with(email_text)

        full_text = unicode(summary)
        self.story.setMetadata('description', full_text)


        def parse_until_br(attribute, start_index, element_list):
            # Initialize counter
            next_index = start_index
            for element in element_list[start_index:]:
                next_index += 1
                if element.name == 'br':
                    break
                elif element.name == 'strong':
                    if attribute == 'status':
                        if element.contents[0].text == 'Sim':
                            self.story.setMetadata(attribute, 'Completed')
                        elif element.contents[0].text == 'Não':
                            self.story.setMetadata(attribute, 'In-Progress')
                    elif attribute == 'characters':
                        terms = re.findall(r"[^&]+", stripHTML(element))
                        for term in terms:
                            self.story.addToList(attribute, term)
                    elif attribute == 'numWords':
                        self.story.setMetadata(attribute, stripHTML(element).replace('.',''))
                    else:
                        self.story.setMetadata(attribute, stripHTML(element))
                elif element.name == 'a':
                    if element.contents[0].name == 'strong':
                        self.story.addToList(attribute, stripHTML(element.contents[0]))
                elif element.name == 'time':
                    self.story.setMetadata(attribute, makeDate(element['datetime'][:self.datelength], self.dateformat))
            return next_index

        # Informações Gerais
        content_metadata = [
            ('Iniciado', 'datePublished'),
            ('Atualizada', 'dateUpdated'),
            ('Idioma', 'language'),
            ('Visualizações', 'hits'),
            ('Favoritos', 'kudos'),
            ('Comentários', 'comments'),
            ('Listas de leitura', 'bookmarks'),
            ('Palavras', 'numWords'),
            ('Concluído', 'status'),
            ('Categorias', 'category'),
            ('Personagens', 'characters'),
            ('Tags', 'freeformtags'),
            ('Gêneros:', 'genre'),
            ('Avisos:', 'warnings')
        ]
        tag_mapping = dict(content_metadata)

        information = div_element.find(lambda tag: tag.name == 'div' and
                                       tag.get('class') == ['texto', 'espacamentoTop'] and
                                       tag.get('id') != 'cphConteudo_cphConteudo_divDestaque')
        logger.debug('information: (%s)', information)
        info_contents = information.contents
        i = 0
        while i < len(info_contents):
            content = info_contents[i]
            stripped_tag = stripHTML(content)

            if stripped_tag in tag_mapping:
                i = parse_until_br(tag_mapping[stripped_tag], i+1, info_contents)
            else:
                i += 1

        # Classificação, Gêneros e Avisos
        # Finding div element with class "clearfix baixo"
        div_element = soup.find('div', {'class': 'clearfix baixo'})

        # Finding div element with class "classificacao"
        classificacao_element = div_element.find('div', class_='classificacao')

        # Extracting last word from class name
        if classificacao_element and 'class' in classificacao_element.attrs:
            class_value = classificacao_element.attrs['class']
            self.story.setMetadata('rating',class_value[-1].split('-')[-1])

        # Extracting text content "Gêneros" and "Avisos"
        contents = classificacao_element.find_next('div').contents
        i = 0
        while i < len(contents):
            content = contents[i]
            stripped_tag = stripHTML(content)

            if stripped_tag in tag_mapping:
                i = parse_until_br(tag_mapping[stripped_tag], i+1, contents)
            else:
                i += 1

    ## Normalize chapter URLs in case of title change
    def normalize_chapterurl(self,url):
        #https://www.spiritfanfiction.com/historia/story-name-1234/capitulo56
        url = re.sub(r"https?://("+self.getSiteDomain()+r"/historia/\d+/capitulo\d+)$",
                     r"https://\1",url)
        return url


    def getChapterText(self, url):
        logger.debug('Getting chapter text from: %s' % url)

        save_chapter_soup = self.make_soup("<div></div>")
        save_chapter = save_chapter_soup.find('div')

        chapter_dl_soup = self.make_soup(self.get_request(url))
        if None == chapter_dl_soup:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
        div_chapter = chapter_dl_soup.find('div', {'class':'clearfix'})
        chapter_text = div_chapter.find('div', class_='texto-capitulo')

        exclude_notes=self.getConfigList('exclude_notes')


        def append_tag(elem, tag, string=None, classes=None):
            '''bs4 requires tags be added separately.'''
            new_tag = save_chapter_soup.new_tag(tag)
            if string:
                new_tag.string=string
            if classes:
                new_tag['class']=[classes]
            elem.append(new_tag)
            return new_tag


        chapimg = chaphead = chapfoot = None
        # Chapter Image
        img_url = chapter_text.find('img', {'class':'imagemResponsiva'})
        if img_url:
            chapimg = chapter_dl_soup.new_tag('p', style="text-align: center")
            chapimg.insert(0, chapter_dl_soup.new_tag('img', src=img_url['src']))

        for tag in chapter_text.find_all('h2'):
            if tag.string.startswith('Notas do Autor'):
                chaphead = self.make_soup(unicode(tag.find_next_sibling('div', {'class': 'texto texto-capitulo-notas'})))
            elif tag.string.startswith('Notas Finais'):
                chapfoot = self.make_soup(unicode(tag.find_next_sibling('div', {'class': 'texto texto-capitulo-notas'})))
            else:
                # Apparently, not all chapters have the "Capítulo" text anymore, but it's the only other h2 in there
                chaptext = self.make_soup(unicode(tag.find_next_sibling('div', {'class': 'texto'})))
                # Decode emails
                self.decode_emails(chaptext)
                if chapimg != None:
                    if chaptext.div == None:
                        append_tag(chaptext, 'div')
                    chaptext.div.insert(0, chapimg)

        head_notes_div = append_tag(save_chapter,'div',classes="fff_chapter_notes fff_head_notes")
        if 'chapterheadnotes' not in exclude_notes:
            if chaphead != None:
                append_tag(head_notes_div,'b',"Notas do Autor:")
                self.decode_emails(chaphead)
                head_notes_div.append(chaphead)
                append_tag(head_notes_div,'hr')

        save_chapter.append(chaptext)

        foot_notes_div = append_tag(save_chapter,'div',classes="fff_chapter_notes fff_foot_notes")
        ## Can appear on every chapter
        if 'chapterfootnotes' not in exclude_notes:
            if chapfoot != None:
                append_tag(foot_notes_div,'hr')
                append_tag(foot_notes_div,'b',"Notas Finais:")
                self.decode_emails(chapfoot)
                foot_notes_div.append(chapfoot)

        ## remove empty head/food notes div(s)
        if not head_notes_div.find(True):
            head_notes_div.extract()
        if not foot_notes_div.find(True):
            foot_notes_div.extract()

        return self.utf8FromSoup(url,save_chapter)


    def decode_emails(self, html_text):

        def decode_email(encoded_email):
            email = ""
            r = int(encoded_email[:2], 16)
            for i in range(2, len(encoded_email), 2):
                char_code = int(encoded_email[i:i + 2], 16) ^ r
                email += chr(char_code)
            return email


        # Find all elements with class '__cf_email__'
        email_elements = html_text.find_all(class_='__cf_email__')
        for element in email_elements:
            # Get the data-cfemail attribute value
            encoded_email = element.get('data-cfemail')
            if encoded_email:
                # Decode the email address
                decoded_email = decode_email(encoded_email)
                # Replace the obfuscated email with the decoded email
                element.string = decoded_email
        return unicode(html_text)

