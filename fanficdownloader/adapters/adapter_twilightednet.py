# -*- coding: utf-8 -*-

import time
import datetime
import logging
import re
import urllib
import urllib2

import fanficdownloader.BeautifulSoup as bs
from fanficdownloader.htmlcleanup import stripHTML

from base_adapter import BaseSiteAdapter, utf8FromSoup

class TwilightedNetSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tw')
        self.decode = "utf8"
        self.story.addToList("category","Twilight")
        self.username = "NoneGiven" # if left empty, twilighted.net doesn't return any message at all.
        self.password = ""
        
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        logging.debug("storyId: (%s)"%self.story.getMetadata('storyId'))
        
        # normalized story URL.
        self._setURL('http://' + self.getSiteDomain() + '/viewstory.php?sid='+self.story.getMetadata('storyId'))

            
    @staticmethod
    def getSiteDomain():
        return 'www.twilighted.net'

    @classmethod
    def getAcceptDomains(cls):
        return ['www.twilighted.net','twilighted.net']

    def getSiteExampleURLs(self):
        return "http://www.twilighted.net/viewstory.php?sid=1234 http://twilighted.net/viewstory.php?sid=5678"

    def getSiteURLPattern(self):
        return re.escape("http://")+r"(www\.)?"+re.escape("twilighted.net/viewstory.php?sid=")+r"\d+$"

    def needToLoginCheck(self, data):
        if 'Registered Users Only.' in data \
                or 'There is no such account on our website' in data \
                or "That password doesn't match the one in our database." in data:
          return True
        else:
          return False

    def performLogin(self, url):
        data = {}

        if self.password:
            data['penname'] = self.username
            data['password'] = self.password
        else:
            data['penname'] = self.getConfig("username")
            data['password'] = self.getConfig("password")
        data['cookiecheck'] = '1'
        data['submit'] = 'Submit'
    
        urlvals = urllib.urlencode(data)
        loginUrl = 'http://' + self.getSiteDomain() + '/user.php?action=login'
        logging.debug("Will now login to URL (%s) as (%s)" % (loginUrl,
                                                              data['penname']))
    
        d = self._fetchUrl(loginUrl, urlvals)
    
        if self.needToLoginCheck(d) :
            logging.info("Failed to login to URL %s as %s" % (loginUrl,
                                                              data['penname']))
            raise adapters.FailedToLogin(url,data['penname'])
            return False
        else:
            return True

    def extractChapterUrlsAndMetadata(self):

        url = self.url+'&index=1'
        logging.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise adapters.StoryDoesNotExist(self.url)
            else:
                raise e

        if self.needToLoginCheck(data):
            # need to log in for this one.
            self.performLogin(url)
            data = self._fetchUrl(url)

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = bs.BeautifulSoup(data)

        ## Title
        a = soup.find('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"$"))
        self.story.setMetadata('title',a.string)
        
        # Find authorid and URL from... author url.
        a = soup.find('a', href=re.compile(r"viewuser.php"))
        self.story.setMetadata('authorId',a['href'].split('=')[1])
        self.story.setMetadata('authorUrl','http://'+self.host+'/'+a['href'])
        self.story.setMetadata('author',a.string)

        # Find the chapters:
        for chapter in soup.findAll('a', href=re.compile(r'viewstory.php\?sid='+self.story.getMetadata('storyId')+"&chapter=\d+$")):
            # just in case there's tags, like <i> in chapter titles.
            self.chapterUrls.append((stripHTML(chapter),'http://'+self.host+'/'+chapter['href']))

        self.story.setMetadata('numChapters',len(self.chapterUrls))

        ## <meta name='description' content='&lt;p&gt;Description&lt;/p&gt; ...' >
        ## Summary, strangely, is in the content attr of a <meta name='description'> tag
        ## which is escaped HTML.  Unfortunately, we can't use it because they don't
        ## escape (') chars in the desc, breakin the tag.
        #meta_desc = soup.find('meta',{'name':'description'})
        #metasoup = bs.BeautifulStoneSoup(meta_desc['content'])
        #self.story.setMetadata('description',stripHTML(metasoup))

        def defaultGetattr(d,k):
            try:
                return d[k]
            except:
                return ""
        
        # <span class="label">Rated:</span> NC-17<br /> etc
        labels = soup.findAll('span',{'class':'label'})
        for labelspan in labels:
            value = labelspan.nextSibling
            label = labelspan.string

            if 'Summary' in label:
                ## Everything until the next span class='label'
                svalue = str(value)
                while not defaultGetattr(value,'class') == 'label':
                    svalue += str(value)
                    value = value.nextSibling
                self.story.setMetadata('description',stripHTML(svalue))

            if 'Rated' in label:
                self.story.setMetadata('rating', value.strip())

            if 'Word count' in label:
                self.story.setMetadata('numWords', value.strip())

            if 'Categories' in label:
                cats = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=categories'))
                catstext = [cat.string for cat in cats]
                for cat in catstext:
                    self.story.addToList('category',cat.string)

            ## twilighted.net doesn't use genre.
            # if 'Genre' in label:
            #     genres = labelspan.parent.findAll('a',href=re.compile(r'browse.php\?type=class'))
            #     genrestext = [genre.string for genre in genres]
            #     self.genre = ', '.join(genrestext)
            #     for genre in genrestext:
            #         self.addSubject(genre.string)

            if 'Completed' in label:
                if 'Yes' in value:
                    self.story.setMetadata('status', 'Completed')
                else:
                    self.story.setMetadata('status', 'In-Progress')

            if 'Published' in label:
                self.story.setMetadata('datePublished', datetime.datetime.fromtimestamp(time.mktime(time.strptime(value.strip(), "%B %d, %Y"))))
            
            if 'Updated' in label:
                # there's a stray [ at the end.
                #value = value[0:-1]
                self.story.setMetadata('dateUpdated', datetime.datetime.fromtimestamp(time.mktime(time.strptime(value.strip(), "%B %d, %Y"))))


    def getChapterText(self, url):

        logging.debug('Getting chapter text from: %s' % url)

        soup = bs.BeautifulStoneSoup(self._fetchUrl(url),
                                     selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        
        span = soup.find('div', {'id' : 'story'})

        if None == span:
            raise adapters.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)
    
        return utf8FromSoup(span)

def getClass():
    return TwilightedNetSiteAdapter

