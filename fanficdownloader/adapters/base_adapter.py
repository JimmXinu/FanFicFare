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

import re
import datetime
import time
import logging
import urllib
import urllib2 as u2
import urlparse as up
from functools import partial

from .. import BeautifulSoup as bs
from ..htmlcleanup import stripHTML
from ..htmlheuristics import replace_br_with_p

logger = logging.getLogger(__name__)

try:
    from google.appengine.api import apiproxy_stub_map
    def urlfetch_timeout_hook(service, call, request, response):
        if call != 'Fetch':
            return
        # Make the default deadline 10 seconds instead of 5.
        if not request.has_deadline():
            request.set_deadline(10.0)

    apiproxy_stub_map.apiproxy.GetPreCallHooks().Append(
        'urlfetch_timeout_hook', urlfetch_timeout_hook, 'urlfetch')
    logger.info("Hook to make default deadline 10.0 installed.")
except:
    pass
    #logger.info("Hook to make default deadline 10.0 NOT installed--not using appengine")

from ..story import Story
from ..gziphttp import GZipProcessor
from ..configurable import Configurable
from ..htmlcleanup import removeEntities, removeAllEntities, stripHTML
from ..exceptions import InvalidStoryURL

try:
    from .. import chardet as chardet
except ImportError:
    chardet = None

class BaseSiteAdapter(Configurable):

    @classmethod
    def matchesSite(cls,site):
        return site in cls.getAcceptDomains()

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain()]

    def validateURL(self):
        return re.match(self.getSiteURLPattern(), self.url)

    def __init__(self, configuration, url):
        Configurable.__init__(self, configuration)
        
        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False
        
        self.opener = u2.build_opener(u2.HTTPCookieProcessor(),GZipProcessor())
        ## Specific UA because too many sites are blocking the default python UA.
        self.opener.addheaders = [('User-agent', self.getConfig('user_agent'))]
        self.storyDone = False
        self.metadataDone = False
        self.story = Story(configuration)
        self.story.setMetadata('site',self.getConfigSection())
        self.story.setMetadata('dateCreated',datetime.datetime.now())
        self.chapterUrls = [] # tuples of (chapter title,chapter url)
        self.chapterFirst = None
        self.chapterLast = None
        self.oldchapters = None
        self.oldimgs = None
        self.oldcover = None # (data of existing cover html, data of existing cover image)
        self.calibrebookmark = None
        self.logfile = None
        ## order of preference for decoding.
        self.decode = ["utf8",
                       "Windows-1252"] # 1252 is a superset of
                                       # iso-8859-1.  Most sites that
                                       # claim to be iso-8859-1 (and
                                       # some that claim to be utf8)
                                       # are really windows-1252.
        self._setURL(url)
        if not self.validateURL():
            raise InvalidStoryURL(url,
                                  self.getSiteDomain(),
                                  self.getSiteExampleURLs())        

    def _setURL(self,url):
        self.url = url
        self.parsedUrl = up.urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path        
        self.story.setMetadata('storyUrl',self.url)

## website encoding(s)--in theory, each website reports the character
## encoding they use for each page.  In practice, some sites report it
## incorrectly.  Each adapter has a default list, usually "utf8,
## Windows-1252" or "Windows-1252, utf8".  The special value 'auto'
## will call chardet and use the encoding it reports if it has +90%
## confidence.  'auto' is not reliable.
    def _decode(self,data):
        if self.getConfig('website_encodings'):
            decode = self.getConfigList('website_encodings')
        else:
            decode = self.decode
        
        for code in decode:
            try:
                #print code
                if code == "auto":
                    if not chardet:
                        logger.info("chardet not available, skipping 'auto' encoding")
                        continue
                    detected = chardet.detect(data)
                    #print detected
                    if detected['confidence'] > 0.9:
                        code=detected['encoding']
                    else:
                        continue
                return data.decode(code)
            except:
                logger.debug("code failed:"+code)
                pass
        logger.info("Could not decode story, tried:%s Stripping non-ASCII."%decode)
        return "".join([x for x in data if ord(x) < 128])

    # Assumes application/x-www-form-urlencoded.  parameters, headers are dict()s
    def _postUrl(self, url, parameters={}, headers={}):
        if self.getConfig('slow_down_sleep_time'):
            time.sleep(float(self.getConfig('slow_down_sleep_time')))

        ## u2.Request assumes POST when data!=None.  Also assumes data
        ## is application/x-www-form-urlencoded.
        if 'Content-type' not in headers:
            headers['Content-type']='application/x-www-form-urlencoded'
        if 'Accept' not in headers:
            headers['Accept']="text/html,*/*"
        req = u2.Request(url,
                         data=urllib.urlencode(parameters),
                         headers=headers)
        return self._decode(self.opener.open(req).read())

    def _fetchUrlRaw(self, url, parameters=None):
        if parameters != None:
            return self.opener.open(url.replace(' ','%20'),urllib.urlencode(parameters)).read()
        else:
            return self.opener.open(url.replace(' ','%20')).read()
    
    # parameters is a dict()
    def _fetchUrl(self, url, parameters=None):
        if self.getConfig('slow_down_sleep_time'):
            time.sleep(float(self.getConfig('slow_down_sleep_time')))

        excpt=None
        for sleeptime in [0, 0.5, 4, 9]:
            time.sleep(sleeptime)	
            try:
                return self._decode(self._fetchUrlRaw(url,parameters))
            except Exception, e:
                excpt=e
                logger.warn("Caught an exception reading URL: %s  Exception %s."%(unicode(url),unicode(e)))
                
        logger.error("Giving up on %s" %url)
        logger.exception(excpt)
        raise(excpt)

    # Limit chapters to download.  Input starts at 1, list starts at 0
    def setChaptersRange(self,first=None,last=None):
        if first:
            self.chapterFirst=int(first)-1
        if last:
            self.chapterLast=int(last)-1
    
    # Does the download the first time it's called.
    def getStory(self):
        if not self.storyDone:
            self.getStoryMetadataOnly()

            for index, (title,url) in enumerate(self.chapterUrls):
                if (self.chapterFirst!=None and index < self.chapterFirst) or \
                        (self.chapterLast!=None and index > self.chapterLast):
                    self.story.addChapter(url,
                                          removeEntities(title),
                                          None)
                else:
                    if self.oldchapters and index < len(self.oldchapters):
                        data = self.utf8FromSoup(None,
                                                 self.oldchapters[index],
                                                 partial(cachedfetch,self._fetchUrlRaw,self.oldimgs))
                    else:
                        data = self.getChapterText(url)
                    self.story.addChapter(url,
                                          removeEntities(title),
                                          removeEntities(data))
            self.storyDone = True
            
            # include image, but no cover from story, add default_cover_image cover.
            if self.getConfig('include_images') and \
                    not self.story.cover and \
                    self.getConfig('default_cover_image'):
                self.story.addImgUrl(None,
                                     #self.getConfig('default_cover_image'),
                                     self.story.formatFileName(self.getConfig('default_cover_image'),
                                                               self.getConfig('allow_unsafe_filename')),
                                     self._fetchUrlRaw,
                                     cover=True)

            # no new cover, set old cover, if there is one.
            if not self.story.cover and self.oldcover:
                self.story.oldcover = self.oldcover
                
            # cheesy way to carry calibre bookmark file forward across update.
            if self.calibrebookmark:
                self.story.calibrebookmark = self.calibrebookmark
            if self.logfile:
                self.story.logfile = self.logfile
                
        return self.story

    def getStoryMetadataOnly(self):
        if not self.metadataDone:
            self.extractChapterUrlsAndMetadata()
            
            if not self.story.getMetadataRaw('dateUpdated'):
                self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('datePublished'))

            self.metadataDone = True
        return self.story

    def hookForUpdates(self,chaptercount):
        "Usually not needed."
        return chaptercount

    ###############################
    
    @staticmethod
    def getSiteDomain():
        "Needs to be overriden in each adapter class."
        return 'no such domain'
    
    @classmethod
    def getConfigSection(cls):
        "Only needs to be overriden if != site domain."
        return cls.getSiteDomain()
    
    @classmethod
    def stripURLParameters(cls,url):
        "Only needs to be overriden if URL contains more than one parameter"
        ## remove any trailing '&' parameters--?sid=999 will be left.
        ## that's all that any of the current adapters need or want.
        return re.sub(r"&.*$","",url)
    
    ## URL pattern validation is done *after* picking an adaptor based
    ## on domain instead of *as* the adaptor selector so we can offer
    ## the user example(s) for that particular site.
    ## Override validateURL(self) instead if you need more control.
    def getSiteURLPattern(self):
        "Used to validate URL.  Should be override in each adapter class."
        return '^http://'+re.escape(self.getSiteDomain())
    
    @classmethod
    def getSiteExampleURLs(self):
        """
        Needs to be overriden in each adapter class.  It's the adapter
        writer's responsibility to make sure the example(s) pass the
        URL validate.
        """
        return 'no such example'
    
    def extractChapterUrlsAndMetadata(self):
        "Needs to be overriden in each adapter class.  Populates self.story metadata and self.chapterUrls"
        pass

    def getChapterText(self, url):
        "Needs to be overriden in each adapter class."
        pass

    # Just for series, in case we choose to change how it's stored or represented later.
    def setSeries(self,name,num):
        if self.getConfig('collect_series'):
            self.story.setMetadata('series','%s [%s]'%(name, int(num)))

    def setDescription(self,url,svalue):
        #print("\n\nsvalue:\n%s\n"%svalue)
        if self.getConfig('keep_summary_html'):
            if isinstance(svalue,basestring):
                svalue = bs.BeautifulSoup(svalue)
            self.story.setMetadata('description',self.utf8FromSoup(url,svalue))
        else:
            self.story.setMetadata('description',stripHTML(svalue))
        #print("\n\ndescription:\n"+self.story.getMetadata('description')+"\n\n")

    def setCoverImage(self,storyurl,imgurl):
        if self.getConfig('include_images'):
            self.story.addImgUrl(storyurl,imgurl,self._fetchUrlRaw,cover=True)

    # This gives us a unicode object, not just a string containing bytes.
    # (I gave soup a unicode string, you'd think it could give it back...)
    # Now also does a bunch of other common processing for us.
    def utf8FromSoup(self,url,soup,fetch=None):
        if not fetch:
            fetch=self._fetchUrlRaw

        acceptable_attributes = ['href','name','class','id']
        if self.getConfig("keep_style_attr"):
            acceptable_attributes.append('style')
        #print("include_images:"+self.getConfig('include_images'))
        if self.getConfig('include_images'):
            acceptable_attributes.extend(('src','alt','longdesc'))
            for img in soup.findAll('img'):
                # some pre-existing epubs have img tags that had src stripped off.
                if img.has_key('src'):
                    img['longdesc']=img['src']
                    img['src']=self.story.addImgUrl(url,img['src'],fetch,
                                                    coverexclusion=self.getConfig('cover_exclusion_regexp'))

        for attr in soup._getAttrMap().keys():
            if attr not in acceptable_attributes:
                del soup[attr] ## strip all tag attributes except href and name
                
        for t in soup.findAll(recursive=True):
            for attr in t._getAttrMap().keys():
                if attr not in acceptable_attributes:
                    del t[attr] ## strip all tag attributes except href and name

            # these are not acceptable strict XHTML.  But we do already have 
	    # CSS classes of the same names defined
            if t.name in ('u'):
                t['class']=t.name
                t.name='span'
            if t.name in ('center'):
                t['class']=t.name
                t.name='div'
	    # removes paired, but empty tags.
            if t.string != None and len(t.string.strip()) == 0 :
                t.extract()

        retval = soup.__str__('utf8').decode('utf-8')

        if self.getConfig('nook_img_fix'):
            # if the <img> tag doesn't have a div or a p around it,
            # nook gets confused and displays it on every page after
            # that under the text for the rest of the chapter.
            retval = re.sub(r"(?!<(div|p)>)\s*(?P<imgtag><img[^>]+>)\s*(?!</(div|p)>)",
                            "<div>\g<imgtag></div>",retval)
            
        # Don't want body tags in chapter html--writers add them.
        # This is primarily for epub updates.
        retval = re.sub(r"</?body>\r?\n?","",retval)
        
        if self.getConfig("replace_br_with_p"):
            # Apply heuristic processing to replace <br> paragraph
            # breaks with <p> tags.
            retval = replace_br_with_p(retval)
            
        if self.getConfig('replace_hr'):
            # replacing a self-closing tag with a container tag in the
            # soup is more difficult than it first appears.  So cheat.
            retval = retval.replace("<hr />","<div class='center'>* * *</div>")

        return retval

def cachedfetch(realfetch,cache,url):
    if url in cache:
        return cache[url]
    else:
        return realfetch(url)
    
fullmon = {"January":"01", "February":"02", "March":"03", "April":"04", "May":"05",
           "June":"06","July":"07", "August":"08", "September":"09", "October":"10",
           "November":"11", "December":"12" }

def makeDate(string,dateform):
    # Surprise!  Abstracting this turned out to be more useful than
    # just saving bytes.

    # fudge english month names for people who's locale is set to
    # non-english.  All our current sites date in english, even if
    # there's non-english content. -- ficbook.net now makes that a
    # lie.  It has to do something even more complicated to get
    # Russian month names correct everywhere.
    do_abbrev = "%b" in dateform
        
    if "%B" in dateform or do_abbrev:
        dateform = dateform.replace("%B","%m").replace("%b","%m")
        for (name,num) in fullmon.items():
            if do_abbrev:
                name = name[:3] # first three for abbrev
            if name in string:
                string = string.replace(name,num)
                break
            
    return datetime.datetime.strptime(string,dateform)

