# -*- coding: utf-8 -*-

# Copyright 2013 Fanficdownloader team, 2015 FanFicFare team
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
import time
import logging
logger = logging.getLogger(__name__)
import re
import sys

from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from base_adapter import BaseSiteAdapter,  makeDate

################################################################################

def getClass():
    return AdultFanFictionOrgAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class AdultFanFictionOrgAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        logger.debug("AdultFanFictionOrgAdapter.__init__ - url='{0}'".format(url))

        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of iso-8859-1.
                            # Most sites that claim to be
                            # iso-8859-1 (and some that claim to be
                            # utf8) are really windows-1252.

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])

        #Setting the 'Zone' for each "Site"
        self.zone = self.parsedUrl.netloc.split('.')[0]

        # normalized story URL. (checking self.zone against list
        # removed--it was redundant w/getAcceptDomains and
        # getSiteURLPattern both)
        self._setURL('http://' + self.zone + '.' + self.getBaseDomain() + '/story.php?no='+self.story.getMetadata('storyId'))

        # Each adapter needs to have a unique site abbreviation.
        #self.story.setMetadata('siteabbrev',self.getSiteAbbrev())

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev',self.zone+'aff')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"
        

    ##This method will be moved to the sub-adapters
    # @classmethod
    # def getSiteAbbrev(self):
    #     return self.zone+'aff'

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
        return ("http://anime.adult-fanfiction.org/story.php?no=123456789 "
              + "http://anime2.adult-fanfiction.org/story.php?no=123456789 "
              + "http://bleach.adult-fanfiction.org/story.php?no=123456789 "
              + "http://books.adult-fanfiction.org/story.php?no=123456789 "
              + "http://buffy.adult-fanfiction.org/story.php?no=123456789 "
              + "http://cartoon.adult-fanfiction.org/story.php?no=123456789 "
              + "http://celeb.adult-fanfiction.org/story.php?no=123456789 "
              + "http://comics.adult-fanfiction.org/story.php?no=123456789 "
              + "http://ff.adult-fanfiction.org/story.php?no=123456789 "
              + "http://games.adult-fanfiction.org/story.php?no=123456789 "
              + "http://hp.adult-fanfiction.org/story.php?no=123456789 "
              + "http://inu.adult-fanfiction.org/story.php?no=123456789 "
              + "http://lotr.adult-fanfiction.org/story.php?no=123456789 "
              + "http://manga.adult-fanfiction.org/story.php?no=123456789 "
              + "http://movies.adult-fanfiction.org/story.php?no=123456789 "
              + "http://naruto.adult-fanfiction.org/story.php?no=123456789 "
              + "http://ne.adult-fanfiction.org/story.php?no=123456789 "
              + "http://original.adult-fanfiction.org/story.php?no=123456789 "
              + "http://tv.adult-fanfiction.org/story.php?no=123456789 "
              + "http://xmen.adult-fanfiction.org/story.php?no=123456789 "
              + "http://ygo.adult-fanfiction.org/story.php?no=123456789 "
              + "http://yuyu.adult-fanfiction.org/story.php?no=123456789")

    def getSiteURLPattern(self):
        return r'http?://(anime|anime2|bleach|books|buffy|cartoon|celeb|comics|ff|games|hp|inu|lotr|manga|movies|naruto|ne|original|tv|xmen|ygo|yuyu)\.adult-fanfiction\.org/story\.php\?no=\d+$'

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

    #    d = self._postUrl(url, params, usecache=False)
    #    d = self._fetchUrl(url, params, usecache=False)
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

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code in 404:
                raise exceptions.StoryDoesNotExist("Code: 404. %s"%self.url)
            elif e.code == 410:
                raise exceptions.StoryDoesNotExist("Code: 410. %s"%self.url)
            elif e.code == 401:
                self.needToLogin = True
                data = ''
            else:
                raise e

        if "The dragons running the back end of the site can not seem to find the story you are looking for." in data:
            raise exceptions.StoryDoesNotExist(self.zone+'.'+self.getBaseDomain() 
                                               +" says: The dragons running the back end of the site can not seem to find the story you are looking for.")

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        
        ##This is not working right now, so I'm commenting it out, but leaving it for future testing
        #self.performLogin(url, soup)

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        ## Some of the titles have a backslash on the story page, but not on the Author's page
        ## So I am removing it from the title, so it can be found on the Author's page further in the code.
        ## Also, some titles may have extra spaces '  ', and the search on the Author's page removes them,
        ## so I have to here as well. I used multiple replaces to make sure, since I did the same below.
        a = soup.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',stripHTML(a).replace('\\','').replace('  ',' ').replace('  ',' ').replace('  ',' ').strip())

        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"profile.php\?no=\d+"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl',a['href'])
        self.story.setMetadata('author',stripHTML(a))

        # Find the chapters:
        chapters = soup.find('div',{'id':'snav'})
        for i, chapter in enumerate(chapters.findAll('a')):
            self.chapterUrls.append((stripHTML(chapter),self.url+'&chapter='+str(i+1)))
        
        self.story.setMetadata('numChapters', len(self.chapterUrls))

        ##The story page does not give much Metadata, so we go to the Author's page
        
        ##Get the first Author page to see if there are multiple pages. 
        ##AFF doesn't care if the page number is larger than the actual pages, 
        ##it will continue to show the last page even if the variable is larger than the actual page
        author_Url = self.story.getMetadata('authorUrl')+'&view=story&zone='+self.zone+'&page=1'

        ##I'm resetting the author page to the zone for this story
        self.story.setMetadata('authorUrl',author_Url)

        logger.debug('Getting the author page: {0}'.format(author_Url))
        try:
            adata = self._fetchUrl(author_Url)
        except urllib2.HTTPError, e:
            if e.code in 404:
                raise exceptions.StoryDoesNotExist("Author Page: Code: 404. %s"%author_Url)
            elif e.code == 410:
                raise exceptions.StoryDoesNotExist("Author Page: Code: 410. %s"%author_Url)
            else:
                raise e

        if "The member you are looking for does not exist." in adata:
            raise exceptions.StoryDoesNotExist(self.zone+'.'+self.getBaseDomain() +" says: The member you are looking for does not exist.")

        asoup = self.make_soup(adata)

        ##Getting the number of pages
        pages=asoup.find('div',{'class' : 'pagination'}).findAll('li')[-1].find('a')
        if not pages == None:
            pages = pages['href'].split('=')[-1]
        else:
            pages = 0
        logger.info(pages)
        ##If there is only 1 page of stories, check it to get the Metadata, 
        if pages == 0:
            a = asoup.findAll('li')
            for lc2 in a:
                if lc2.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$")):
                    break
        ## otherwise go through the pages 
        else:
            page=1
            i=0
            while i == 0:
                ##We already have the first page, so if this is the first time through, skip getting the page
                if page != 1:
                    author_Url = self.story.getMetadata('authorUrl')+'&view=story&zone='+self.zone+'&page='+str(page)
                    logger.debug('Getting the author page: {0}'.format(author_Url))
                    try:
                        adata = self._fetchUrl(author_Url)
                    except urllib2.HTTPError, e:
                        if e.code in 404:
                            raise exceptions.StoryDoesNotExist("Author Page: Code: 404. %s"%author_Url)
                        elif e.code == 410:
                            raise exceptions.StoryDoesNotExist("Author Page: Code: 410. %s"%author_Url)
                        else:
                            raise e
                    ##This will probably never be needed, since AFF doesn't seem to care what number you put as 
                    ## the page number, it will default to the last page, even if you use 1000, for an author
                    ## that only hase 5 pages of stories, but I'm keeping it in to appease Saint Justin Case (just in case).
                    if "The member you are looking for does not exist." in adata:
                        raise exceptions.StoryDoesNotExist(self.zone+'.'+self.getBaseDomain() +" says: The member you are looking for does not exist.")
    
                asoup = self.make_soup(adata)
    
                a = asoup.findAll('li')
                for lc2 in a:
                    if lc2.find('a', href=re.compile(r'story.php\?no='+self.story.getMetadata('storyId')+"$")):
                        i=1
                        break
                page = page + 1
                if page > pages:
                    break

        ##Split the Metadata up into a list
        ##We have to change the soup type to a string, then remove the newlines, and double spaces, 
        ##then changes the <br/> to '-:-', which seperates the different elemeents.
        ##Then we strip the HTML elements from the string.
        ##There is also a double <br/>, so we have to fix that, then remove the leading and trailing '-:-'.
        ##They are always in the same order.
        liMetadata = stripHTML(str(lc2).replace('\n','').replace('\r','').replace('\t',' ').replace('  ',' ').replace('  ',' ').replace('  ',' ').replace(r'<br/>','-:-'))
        liMetadata = liMetadata.replace(r'-:--:-','-:-').strip('-:-').strip('-:-')

        for i, value in enumerate(liMetadata.split('-:-')):
            ##The item 6 is the reviews... We are disregarding them.
            ##The item 7 is the 'Dragon Prints'... not sure what they are, so disregarding them.
            ##The 0 item is the title
            if i == 0:
                if value <> self.story.getMetadata('title'):
                    raise exceptions.StoryDoesNotExist('Did not find story in author story list: {0}'.format(author_Url))
            elif i == 1:
                ##Get the description
                self.story.setMetadata('description',stripHTML(value.strip()))
            elif i == 2:
                ##The Get the Category
                self.story.setMetadata('category',value.replace(r'&gt;',r'>').replace(r'Located :',r'').strip())
            elif i == 3:
                ##Get the Erotic Tags
                value = stripHTML(value.replace(r'Content Tags :',r'')).strip()
                for code in re.split(r'\s',value):
                    self.story.addToList('eroticatags',code)
            elif i == 4:
                ##Get the Posted Date
                value = value.replace(r'Posted :',r'').strip()
                self.story.setMetadata('datePublished', makeDate(stripHTML(value), self.dateformat))
            elif i == 5:
                ##Get the 'Updated' Edited date
                ##AFF has the time for the Updated date, and we only want the date,
                ##so we take the first 10 characters only
                value = value.replace(r'Edited :',r'').strip()[0:10]
                self.story.setMetadata('dateUpdated', makeDate(stripHTML(value), self.dateformat))

    # grab the text for an individual chapter.
    def getChapterText(self, url):
        #Since each chapter is on 1 page, we don't need to do anything special, just get the content of the page.
        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))
        chaptertag = soup.find('div',{'class' : 'pagination'}).parent.findNext('td')

        if None == chaptertag:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url,chaptertag)
