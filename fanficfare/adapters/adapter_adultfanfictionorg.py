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
        self.dateformat = "%Y-%m-%d"



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

    ##This is not working right now, so I'm commenting it out, but leaving it for future testing
    ## Login seems to be reasonably standard across eFiction sites.
    #def needToLoginCheck(self, data):
        ##This adapter will always require a login
    #    return True

#    <form name="login" method="post" action="">
#      <div class="top">E-mail: <span id="sprytextfield1">
#        <input name="email" type="text" id="email" size="20" maxlength="255" />
#        <span class="textfieldRequiredMsg">Email is required.</span><span class="textfieldInvalidFormatMsg">Invalid E-mail.</span></span></div>
#      <div class="top">Password: <span id="sprytextfield2">
#        <input name="pass1" type="password" id="pass1" size="20" maxlength="32" />
#        <span class="textfieldRequiredMsg">password is required.</span><span class="textfieldMinCharsMsg">Minimum 8 characters8.</span><span class="textfieldMaxCharsMsg">Exceeded 32 characters.</span></span></div>
#      <div class="top"><br /> <input name="loginsubmittop" type="hidden" id="loginsubmit" value="TRUE" />
#        <input type="submit" value="Login" />
#      </div>
#    </form>


    ##This is not working right now, so I'm commenting it out, but leaving it for future testing
    #def performLogin(self, url, soup):
    #    params = {}

    #    if self.password:
    #        params['email'] = self.username
    #        params['pass1'] = self.password
    #    else:
    #        params['email'] = self.getConfig("username")
    #        params['pass1'] = self.getConfig("password")
    #    params['submit'] = 'Login'

    #    # copy all hidden input tags to pick up appropriate tokens.
    #    for tag in soup.findAll('input',{'type':'hidden'}):
    #        params[tag['name']] = tag['value']

    #    logger.debug("Will now login to URL {0} as {1} with password: {2}".format(url, params['email'],params['pass1']))

    #    d = self.post_request(url, params, usecache=False)
    #    d = self.post_request(url, params, usecache=False)
    #    soup = self.make_soup(d)

        #if not (soup.find('form', {'name' : 'login'}) == None):
        #    logger.info("Failed to login to URL %s as %s" % (url, params['email']))
        #    raise exceptions.FailedToLogin(url,params['email'])
        #    return False
        #else:
    #    return True

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        ## You need to have your is_adult set to true to get this story
        if not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        url = self.url
        logger.debug("URL: "+url)

        data = self.get_request(url)

        if "The dragons running the back end of the site can not seem to find the story you are looking for." in data:
            raise exceptions.StoryDoesNotExist("{0}.{1} says: The dragons running the back end of the site can not seem to find the story you are looking for.".format(self.zone, self.getBaseDomain()))

        soup = self.make_soup(data)

        ##This is not working right now, so I'm commenting it out, but leaving it for future testing
        #self.performLogin(url, soup)


        ## Title
        ## Some of the titles have a backslash on the story page, but not on the Author's page
        ## So I am removing it from the title, so it can be found on the Author's page further in the code.
        ## Also, some titles may have extra spaces '  ', and the search on the Author's page removes them,
        ## so I have to here as well. I used multiple replaces to make sure, since I did the same below.
        a = soup.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a).replace('\\','').replace('  ',' ').replace('  ',' ').replace('  ',' ').strip())

        # Find the chapters:
        chapters = soup.find('ul',{'class':'dropdown-content'})
        for i, chapter in enumerate(chapters.findAll('a')):
            self.add_chapter(chapter,self.url+'&chapter='+unicode(i+1))


        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"profile.php\?no=\d+"))
        if a == None:
            # I know that the original author of fanficfare wants to always have metadata,
            # but I posit that if the story is there, even if we can't get the metadata from the
            # author page, the story should still be able to be downloaded, which is what I've done here.
            self.story.setMetadata('authorId','000000000')
            self.story.setMetadata('authorUrl','https://www.adult-fanfiction.org')
            self.story.setMetadata('author','Unknown')
            logger.warning('There was no author found for the story... Metadata will not be retreived.')
            self.setDescription(url,'>>>>>>>>>> No Summary Given <<<<<<<<<<')
        else:
            self.story.setMetadata('authorId',a['href'].split('=')[1])
            self.story.setMetadata('authorUrl',a['href'])
            self.story.setMetadata('author',stripHTML(a))

            ##The story page does not give much Metadata, so we go to the Author's page

            ##Get the first Author page to see if there are multiple pages.
            ##AFF doesn't care if the page number is larger than the actual pages,
            ##it will continue to show the last page even if the variable is larger than the actual page
            author_Url = '{0}&view=story&zone={1}&page=1'.format(self.story.getMetadata('authorUrl'), self.zone)
            #author_Url = self.story.getMetadata('authorUrl')+'&view=story&zone='+self.zone+'&page=1'

            ##I'm resetting the author page to the zone for this story
            self.story.setMetadata('authorUrl',author_Url)

            logger.debug('Getting the author page: {0}'.format(author_Url))
            adata = self.get_request(author_Url)

            if "The member you are looking for does not exist." in adata:
                raise exceptions.StoryDoesNotExist("{0}.{1} says: The member you are looking for does not exist.".format(self.zone, self.getBaseDomain()))
                #raise exceptions.StoryDoesNotExist(self.zone+'.'+self.getBaseDomain() +" says: The member you are looking for does not exist.")

            asoup = self.make_soup(adata)

            ##Getting the number of author pages
            pages = 0
            pagination=asoup.find('ul',{'class' : 'pagination'})
            if pagination:
                pages = pagination.findAll('li')[-1].find('a')
                if not pages == None:
                    pages = pages['href'].split('=')[-1]
                else:
                    pages = 0

            storya = None
            ##If there is only 1 page of stories, check it to get the Metadata,
            if pages == 0:
                a = asoup.findAll('li')
                for lc2 in a:
                    if lc2.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$")):
                        storya = lc2
                        break
            ## otherwise go through the pages
            else:
                page=1
                i=0
                while i == 0:
                    ##We already have the first page, so if this is the first time through, skip getting the page
                    if page != 1:
                        author_Url = '{0}&view=story&zone={1}&page={2}'.format(self.story.getMetadata('authorUrl'), self.zone, unicode(page))
                        logger.debug('Getting the author page: {0}'.format(author_Url))
                        adata = self.get_request(author_Url)
                        ##This will probably never be needed, since AFF doesn't seem to care what number you put as
                        ## the page number, it will default to the last page, even if you use 1000, for an author
                        ## that only hase 5 pages of stories, but I'm keeping it in to appease Saint Justin Case (just in case).
                        if "The member you are looking for does not exist." in adata:
                            raise exceptions.StoryDoesNotExist("{0}.{1} says: The member you are looking for does not exist.".format(self.zone, self.getBaseDomain()))
                    # we look for the li element that has the story here
                    asoup = self.make_soup(adata)

                    a = asoup.findAll('li')
                    for lc2 in a:
                        if lc2.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$")):
                            i=1
                            storya = lc2
                            break
                    page = page + 1
                    if page > int(pages):
                        break

            ##Split the Metadata up into a list
            ##We have to change the soup type to a string, then remove the newlines, and double spaces,
            ##then changes the <br/> to '-:-', which seperates the different elemeents.
            ##Then we strip the HTML elements from the string.
            ##There is also a double <br/>, so we have to fix that, then remove the leading and trailing '-:-'.
            ##They are always in the same order.
            ## EDIT 09/26/2016: Had some trouble with unicode errors... so I had to put in the decode/encode parts to fix it
            liMetadata = unicode(storya).replace('\n','').replace('\r','').replace('\t',' ').replace('  ',' ').replace('  ',' ').replace('  ',' ')
            liMetadata = stripHTML(liMetadata.replace(r'<br/>','-:-').replace('<!-- <br /-->','-:-'))
            liMetadata = liMetadata.strip('-:-').strip('-:-').encode('utf-8')
            for i, value in enumerate(liMetadata.decode('utf-8').split('-:-')):
                if i == 0:
                    # The value for the title has been manipulated, so may not be the same as gotten at the start.
                    # I'm going to use the href from the storya retrieved from the author's page to determine if it is correct.
                    if storya.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$"))['href'] != url:
                        raise exceptions.StoryDoesNotExist('Did not find story in author story list: {0}'.format(author_Url))
                elif i == 1:
                    ##Get the description
                    self.setDescription(url,stripHTML(value.strip()))
                else:
                    # the rest of the values can be missing, so instead of hardcoding the numbers, we search for them.
                    if 'Located :' in value:
                        self.story.setMetadata('category',value.replace(r'&gt;',r'>').replace(r'Located :',r'').strip())
                    elif 'Category :' in value:
                        # Get the Category
                        self.story.setMetadata('category',value.replace(r'&gt;',r'>').replace(r'Located :',r'').strip())
                    elif 'Content Tags :' in value:
                        # Get the Erotic Tags
                        value = stripHTML(value.replace(r'Content Tags :',r'')).strip()
                        for code in re.split(r'\s',value):
                            self.story.addToList('eroticatags',code)
                    elif 'Posted :' in value:
                        # Get the Posted Date
                        value = value.replace(r'Posted :',r'').strip()
                        if value.startswith('008'):
                            # It is unknown how the 200 became 008, but I'm going to change it back here
                            value = value.replace('008','200')
                        elif value.startswith('0000'):
                            # Since the date is showing as 0000,
                            # I'm going to put the memberdate here
                            value = asoup.find('div',{'id':'contentdata'}).find('p').get_text(strip=True).replace('Member Since','').strip()
                        self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
                    elif 'Edited :' in value:
                        # Get the 'Updated' Edited date
                        # AFF has the time for the Updated date, and we only want the date,
                        # so we take the first 10 characters only
                        value = value.replace(r'Edited :',r'').strip()[0:10]
                        if value.startswith('008'):
                            # It is unknown how the 200 became 008, but I'm going to change it back here
                            value = value.replace('008','200')
                            self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                        elif value.startswith('0000') or '-00-' in value:
                            # Since the date is showing as 0000,
                            # or there is -00- in the date,
                            # I'm going to put the Published date here
                            self.story.setMetadata('dateUpdated', self.story.getMetadata('datPublished'))
                        else:
                            self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))
                    else:
                        # This catches the blank elements, and the Review and Dragon Prints.
                        # I am not interested in these, so do nothing
                        zzzzzzz=0

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        #Since each chapter is on 1 page, we don't need to do anything special, just get the content of the page.
        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self.get_request(url))
        chaptertag = soup.find('ul',{'class':'pagination'}).parent.parent.parent.findNextSibling('li')
        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: {0}!  Missing required element!".format(url))
        # Change td to a div.
        chaptertag.name='div'

        return self.utf8FromSoup(url,chaptertag)
