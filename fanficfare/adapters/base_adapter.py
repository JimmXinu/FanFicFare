# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2016 FanFicFare team
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
from datetime import datetime, timedelta

import time
import logging
import urllib
import urllib2 as u2
import urlparse as up
import cookielib as cl
from functools import partial
import pickle

import bs4

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
    import chardet
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

    @staticmethod
    def get_empty_cookiejar():
        return cl.LWPCookieJar()

    @staticmethod
    def get_empty_pagecache():
        return {}

    def __init__(self, configuration, url):
        Configurable.__init__(self, configuration)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        self.override_sleep = None
        self.cookiejar = self.get_empty_cookiejar()
        self.opener = u2.build_opener(u2.HTTPCookieProcessor(self.cookiejar),GZipProcessor())
        # self.opener = u2.build_opener(u2.HTTPCookieProcessor(),GZipProcessor())
        ## Specific UA because too many sites are blocking the default python UA.
        self.opener.addheaders = [('User-Agent', self.getConfig('user_agent')),
                                  ('X-Clacks-Overhead','GNU Terry Pratchett')]
        self.storyDone = False
        self.metadataDone = False
        self.story = Story(configuration)
        self.story.setMetadata('site',self.getConfigSection())
        self.story.setMetadata('dateCreated',datetime.now())
        self.chapterUrls = [] # tuples of (chapter title,chapter url)
        self.chapterFirst = None
        self.chapterLast = None
        self.oldchapters = None
        self.oldchaptersmap = None
        self.oldchaptersdata = None
        self.oldimgs = None
        self.oldcover = None # (data of existing cover html, data of existing cover image)
        self.calibrebookmark = None
        self.logfile = None

        self.pagecache = self.get_empty_pagecache()

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

    def get_cookiejar(self):
        return self.cookiejar

    def set_cookiejar(self,cj):
        self.cookiejar = cj
        saveheaders = self.opener.addheaders
        self.opener = u2.build_opener(u2.HTTPCookieProcessor(self.cookiejar),GZipProcessor())
        self.opener.addheaders = saveheaders

    def load_cookiejar(self,filename):
        '''
        Needs to be called after adapter create, but before any fetchs
        are done.  Takes file *name*.
        '''
        self.get_cookiejar().load(filename, ignore_discard=True, ignore_expires=True)

    def get_pagecache(self):
        return self.pagecache

    def set_pagecache(self,d):
        self.pagecache=d

    def _get_cachekey(self, url, parameters=None, headers=None):
        keylist=[url]
        if parameters != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
        if headers != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(headers.items())))
        return '?'.join(keylist)

    def _has_cachekey(self,cachekey):
        return self.use_pagecache() and cachekey in self.get_pagecache()

    def _get_from_pagecache(self,cachekey):
        if self.use_pagecache():
            return self.get_pagecache().get(cachekey)
        else:
            return None

    def _set_to_pagecache(self,cachekey,data,redirectedurl):
        if self.use_pagecache():
            self.get_pagecache()[cachekey] = (data,redirectedurl)

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return False

    # def story_load(self,filename):
    #     d = pickle.load(self.story.metadata,filename)
    #     self.story.metadata = d['metadata']
    #     self.chapterUrls = d['chapterlist']
    #     self.story.metadataDone = True

    def _setURL(self,url):
        self.url = url
        self.parsedUrl = up.urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path
        self.story.setMetadata('storyUrl',self.url,condremoveentities=False)

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
    def _postUrl(self, url,
                 parameters={},
                 headers={},
                 extrasleep=None,
                 usecache=True):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        cachekey=self._get_cachekey(url, parameters, headers)
        if usecache and self._has_cachekey(cachekey):
            logger.debug("#####################################\npagecache HIT: %s"%safe_url(cachekey))
            data,redirecturl = self._get_from_pagecache(cachekey)
            return data

        logger.debug("#####################################\npagecache MISS: %s"%safe_url(cachekey))
        self.do_sleep(extrasleep)

        ## u2.Request assumes POST when data!=None.  Also assumes data
        ## is application/x-www-form-urlencoded.
        if 'Content-type' not in headers:
            headers['Content-type']='application/x-www-form-urlencoded'
        if 'Accept' not in headers:
            headers['Accept']="text/html,*/*"
        req = u2.Request(url,
                         data=urllib.urlencode(parameters),
                         headers=headers)
        data = self._decode(self.opener.open(req,None,float(self.getConfig('connect_timeout',30.0))).read())
        self._set_to_pagecache(cachekey,data,url)
        return data

    def _fetchUrlRaw(self, url,
                     parameters=None,
                     extrasleep=None,
                     usecache=True):

        return self._fetchUrlRawOpened(url,
                                       parameters,
                                       extrasleep,
                                       usecache)[0]

    def _fetchUrlRawOpened(self, url,
                           parameters=None,
                           extrasleep=None,
                           usecache=True):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        cachekey=self._get_cachekey(url, parameters)
        if usecache and self._has_cachekey(cachekey):
            logger.debug("#####################################\npagecache HIT: %s"%safe_url(cachekey))
            data,redirecturl = self._get_from_pagecache(cachekey)
            class FakeOpened:
                def __init__(self,data,url):
                    self.data=data
                    self.url=url
                def geturl(self): return self.url
                def read(self): return self.data
            return (data,FakeOpened(data,redirecturl))

        logger.debug("#####################################\npagecache MISS: %s"%safe_url(cachekey))
        self.do_sleep(extrasleep)
        if parameters != None:
            opened = self.opener.open(url.replace(' ','%20'),urllib.urlencode(parameters),float(self.getConfig('connect_timeout',30.0)))
        else:
            opened = self.opener.open(url.replace(' ','%20'),None,float(self.getConfig('connect_timeout',30.0)))
        data = opened.read()
        self._set_to_pagecache(cachekey,data,opened.url)

        return (data,opened)

    def set_sleep(self,val):
        logger.debug("\n===========\n set sleep time %s\n==========="%val)
        self.override_sleep = val

    def do_sleep(self,extrasleep=None):
        if extrasleep:
            time.sleep(float(extrasleep))
        if self.override_sleep:
            time.sleep(float(self.override_sleep))
        elif self.getConfig('slow_down_sleep_time'):
            time.sleep(float(self.getConfig('slow_down_sleep_time')))

    def _fetchUrl(self, url,
                  parameters=None,
                  usecache=True,
                  extrasleep=None):
        return self._fetchUrlOpened(url,
                                    parameters,
                                    usecache,
                                    extrasleep)[0]

    # parameters is a dict()
    def _fetchUrlOpened(self, url,
                        parameters=None,
                        usecache=True,
                        extrasleep=None):

        excpt=None
        for sleeptime in [0, 0.5, 4, 9]:
            time.sleep(sleeptime)
            try:
                (data,opened)=self._fetchUrlRawOpened(url,
                                                      parameters=parameters,
                                                      usecache=usecache,
                                                      extrasleep=extrasleep)
                return (self._decode(data),opened)
            except u2.HTTPError, he:
                excpt=he
                if he.code in (403,404,410):
                    logger.warn("Caught an exception reading URL: %s  Exception %s."%(unicode(safe_url(url)),unicode(he)))
                    break # break out on 404
            except Exception, e:
                excpt=e
                logger.warn("Caught an exception reading URL: %s sleeptime(%s) Exception %s."%(unicode(safe_url(url)),sleeptime,unicode(e)))

        logger.error("Giving up on %s" %safe_url(url))
        logger.debug(excpt, exc_info=True)
        raise(excpt)

    # Limit chapters to download.  Input starts at 1, list starts at 0
    def setChaptersRange(self,first=None,last=None):
        if first:
            self.chapterFirst=int(first)-1
        if last:
            self.chapterLast=int(last)-1
        self.story.set_chapters_range(first,last)

    # Does the download the first time it's called.
    def getStory(self):
        if not self.storyDone:
            self.getStoryMetadataOnly(get_cover=True)

            ## one-off step to normalize old chapter URLs if present.
            if self.oldchaptersmap:
                self.oldchaptersmap = dict((self.normalize_chapterurl(key), value) for (key, value) in self.oldchaptersmap.items())

            for index, (title,url) in enumerate(self.chapterUrls):
                newchap = False
                if (self.chapterFirst!=None and index < self.chapterFirst) or \
                        (self.chapterLast!=None and index > self.chapterLast):
                    self.story.addChapter(url,
                                          removeEntities(title),
                                          None)
                else:
                    data = None
                    if self.oldchaptersmap:
                        if url in self.oldchaptersmap:
                            data = self.utf8FromSoup(None,
                                                     self.oldchaptersmap[url],
                                                     partial(cachedfetch,self._fetchUrlRaw,self.oldimgs))
                    elif self.oldchapters and index < len(self.oldchapters):
                        data = self.utf8FromSoup(None,
                                                 self.oldchapters[index],
                                                 partial(cachedfetch,self._fetchUrlRaw,self.oldimgs))

                    # if already marked new -- ie, origtitle and title don't match
                    # logger.debug("self.oldchaptersdata[url]:%s"%(self.oldchaptersdata[url]))
                    newchap = (self.oldchaptersdata is not None and
                               url in self.oldchaptersdata and (
                            self.oldchaptersdata[url]['chapterorigtitle'] !=
                            self.oldchaptersdata[url]['chaptertitle']) )

                    if not data:
                        data = self.getChapterText(url)
                        # if had to fetch and has existing chapters
                        newchap = bool(self.oldchapters or self.oldchaptersmap)

                    if index == 0 and self.getConfig('always_reload_first_chapter'):
                        data = self.getChapterText(url)
                        # first chapter is rarely marked new
                        # anyway--only if it's replaced during an
                        # update.
                        newchap = False

                    self.story.addChapter(url,
                                          removeEntities(title),
                                          removeEntities(data),
                                          newchap)
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
                self.story.setMetadata('cover_image','default')

            # no new cover, set old cover, if there is one.
            if not self.story.cover and self.oldcover:
                self.story.oldcover = self.oldcover
                self.story.setMetadata('cover_image','old')

            # cheesy way to carry calibre bookmark file forward across update.
            if self.calibrebookmark:
                self.story.calibrebookmark = self.calibrebookmark
            if self.logfile:
                self.story.logfile = self.logfile

        return self.story

    def getStoryMetadataOnly(self,get_cover=True):
        if not self.metadataDone:
            self.doExtractChapterUrlsAndMetadata(get_cover=get_cover)

            if not self.story.getMetadataRaw('dateUpdated'):
                if self.story.getMetadataRaw('datePublished'):
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('datePublished'))
                else:
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('dateCreated'))

            self.metadataDone = True
            # normalize chapter urls.
            for index, (title,url) in enumerate(self.chapterUrls):
                self.chapterUrls[index] = (title,self.normalize_chapterurl(url))

        return self.story

    def setStoryMetadata(self,metahtml):
        if metahtml:
            self.story.load_html_metadata(metahtml)
            self.metadataDone = True
            if not self.story.getMetadataRaw('dateUpdated'):
                if self.story.getMetadataRaw('datePublished'):
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('datePublished'))
                else:
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('dateCreated'))

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
    def getConfigSections(cls):
        "Only needs to be overriden if has additional ini sections."
        return [cls.getConfigSection()]

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
    def getSiteExampleURLs(cls):
        """
        Return a string of space separated example URLs.
        Needs to be overriden in each adapter class.  It's the adapter
        writer's responsibility to make sure the example(s) pass the
        validateURL method.
        """
        return 'no such example'

    def doExtractChapterUrlsAndMetadata(self,get_cover=True):
        '''
        There are a handful of adapters that fetch a cover image while
        collecting metadata.  That isn't needed while *just*
        collecting metadata in FG in plugin.  Those few will override
        this instead of extractChapterUrlsAndMetadata()
        '''
        return self.extractChapterUrlsAndMetadata()

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
        strval = u"%s"%svalue # works for either soup or string
        if self.hasConfig('description_limit'):
            limit = int(self.getConfig('description_limit'))
            if limit and len(strval) > limit:
                svalue = strval[:limit]

        #print(u"[[[[[\n\n%s\n\n]]]]]]]]"%svalue) # works for either soup or string
        if self.getConfig('keep_summary_html'):
            if isinstance(svalue,basestring):
                # bs4/html5lib add html, header and body tags, which
                # we don't want.  utf8FromSoup will strip the body tags for us.
                svalue = bs4.BeautifulSoup(svalue,"html5lib").body
            self.story.setMetadata('description',self.utf8FromSoup(url,svalue))
        else:
            self.story.setMetadata('description',stripHTML(svalue))
        #print("\n\ndescription:\n"+self.story.getMetadata('description')+"\n\n")

    def setCoverImage(self,storyurl,imgurl):
        if self.getConfig('include_images'):
            return self.story.addImgUrl(storyurl,imgurl,self._fetchUrlRaw,cover=True,
                                        coverexclusion=self.getConfig('cover_exclusion_regexp'))
        else:
            return (None,None)

    # bs3 & bs4 are different here.
    # will move to a bs3 vs bs4 block if there's lots of changes.
    def get_attr_keys(self,soup):
        if hasattr(soup, '_getAttrMap') and getattr(soup, '_getAttrMap') is not None:
            # bs3
            #print "bs3 attrs:%s"%soup._getAttrMap().keys()
            return soup._getAttrMap().keys()
        elif hasattr(soup, 'attrs') and  isinstance(soup.attrs,dict):
            #print "bs4 attrs:%s"%soup.attrs.keys()
            # bs4
            return soup.attrs.keys()
        return []

    # This gives us a unicode object, not just a string containing bytes.
    # (I gave soup a unicode string, you'd think it could give it back...)
    # Now also does a bunch of other common processing for us.
    def utf8FromSoup(self,url,soup,fetch=None,allow_replace_br_with_p=True):
        if not fetch:
            fetch=self._fetchUrlRaw

        acceptable_attributes = self.getConfigList('keep_html_attrs',['href','name','class','id'])

        if self.getConfig("keep_style_attr"):
            acceptable_attributes.append('style')
        if self.getConfig("keep_title_attr"):
            acceptable_attributes.append('title')

        #print("include_images:"+self.getConfig('include_images'))
        if self.getConfig('include_images'):
            acceptable_attributes.extend(('src','alt','longdesc'))
            try:
                for img in soup.find_all('img'):
                    # some pre-existing epubs have img tags that had src stripped off.
                    if img.has_attr('src'):
                        (img['src'],img['longdesc'])=self.story.addImgUrl(url,img['src'],fetch,
                                                                          coverexclusion=self.getConfig('cover_exclusion_regexp'))
            except AttributeError as ae:
                logger.info("Parsing for img tags failed--probably poor input HTML.  Skipping images.")

        for attr in self.get_attr_keys(soup):
            if attr not in acceptable_attributes:
                del soup[attr] ## strip all tag attributes except href and name

        ## apply adapter's normalize_chapterurls to all links in
        ## chapter texts, if they match chapter URLs.  While this will
        ## be occasionally helpful by itself, it's really for the next
        ## feature: internal text links.
        if self.getConfig('normalize_text_links'):
            for alink in soup.find_all('a'):
                # try:
                if alink.has_attr('href'):
                    # logger.debug("normalize_text_links %s -> %s"%(alink['href'],self.normalize_chapterurl(alink['href'])))
                    alink['href'] = self.normalize_chapterurl(alink['href'])
                # except AttributeError as ae:
                #     logger.info("Parsing for normalize_text_links failed...")

        try:
            # as a generator, each tag will be returned even if there's a
            # mismatch at the end.
            for t in soup.recursiveChildGenerator(): # findAll(recursive=True):
                for attr in self.get_attr_keys(t):
                    if attr not in acceptable_attributes:
                        del t[attr] ## strip all tag attributes except acceptable_attributes

                # these are not acceptable strict XHTML.  But we do already have
                # CSS classes of the same names defined
                if t and hasattr(t,'name') and t.name is not None:
                    if t.name in self.getConfigList('replace_tags_with_spans',['u']):
                        t['class']=t.name
                        t.name='span'
                    if t.name in ('center'):
                        t['class']=t.name
                        t.name='div'
                    # removes paired, but empty non paragraph tags.
                    if t.name not in ('p') and t.string != None and len(t.string.strip()) == 0 :
                        t.extract()

                    # remove script tags cross the board.
                    if t.name=='script':
                        t.extract()

        except AttributeError, ae:
            if "%s"%ae != "'NoneType' object has no attribute 'next_element'":
                logger.error("Error parsing HTML, probably poor input HTML. %s"%ae)

        retval = unicode(soup)

        if self.getConfig('nook_img_fix') and not self.getConfig('replace_br_with_p'):
            # if the <img> tag doesn't have a div or a p around it,
            # nook gets confused and displays it on every page after
            # that under the text for the rest of the chapter.
            retval = re.sub(r"(?!<(div|p)>)\s*(?P<imgtag><img[^>]+>)\s*(?!</(div|p)>)",
                            "<div>\g<imgtag></div>",retval)

        # Don't want html, head or body tags in chapter html--writers add them.
        # This is primarily for epub updates.
        retval = re.sub(r"</?(html|head|body)[^>]*>\r?\n?","",retval)

        if self.getConfig("replace_br_with_p") and allow_replace_br_with_p:
            # Apply heuristic processing to replace <br> paragraph
            # breaks with <p> tags.
            retval = replace_br_with_p(retval)

        if self.getConfig('replace_hr'):
            # replacing a self-closing tag with a container tag in the
            # soup is more difficult than it first appears.  So cheat.
            retval = re.sub("<hr[^>]*>","<div class='center'>* * *</div>",retval)

        return retval

    def make_soup(self,data):
        '''
        Convenience method for getting a bs4 soup.  bs3 has been removed.
        '''

        ## html5lib handles <noscript> oddly.  See:
        ## https://bugs.launchpad.net/beautifulsoup/+bug/1277464
        ## This should 'hide' and restore <noscript> tags.
        data = data.replace("noscript>","fff_hide_noscript>")

        ## soup and re-soup because BS4/html5lib is more forgiving of
        ## incorrectly nested tags that way.
        soup = bs4.BeautifulSoup(data,'html5lib')
        soup = bs4.BeautifulSoup(unicode(soup),'html5lib')

        for ns in soup.find_all('fff_hide_noscript'):
            ns.name = 'noscript'

        return soup

    ## For adapters, especially base_xenforoforum to override.  Make
    ## sure to return unchanged URL if it's NOT a chapter URL...
    def normalize_chapterurl(self,url):
        return url

def cachedfetch(realfetch,cache,url):
    if url in cache:
        return cache[url]
    else:
        return realfetch(url)

fullmon = {u"January":u"01", u"February":u"02", u"March":u"03", u"April":u"04", u"May":u"05",
           u"June":u"06","July":u"07", u"August":u"08", u"September":u"09", u"October":u"10",
           u"November":u"11", u"December":u"12" }

def makeDate(string,dateform):
    # Surprise!  Abstracting this turned out to be more useful than
    # just saving bytes.

    # fudge english month names for people who's locale is set to
    # non-english.  All our current sites date in english, even if
    # there's non-english content. -- ficbook.net now makes that a
    # lie.  It has to do something even more complicated to get
    # Russian month names correct everywhere.
    do_abbrev = "%b" in dateform

    if u"%B" in dateform or do_abbrev:
        dateform = dateform.replace(u"%B",u"%m").replace(u"%b",u"%m")
        for (name,num) in fullmon.items():
            if do_abbrev:
                name = name[:3] # first three for abbrev
            if name in string:
                string = string.replace(name,num)
                break

    # Many locales don't define %p for AM/PM.  So if %p, remove from
    # dateform, look for 'pm' in string, remove am/pm from string and
    # add 12 hours if pm found.
    add_hours = False
    if u"%p" in dateform:
        dateform = dateform.replace(u"%p",u"")
        if 'pm' in string or 'PM' in string:
            add_hours = True
        string = string.replace(u"AM",u"").replace(u"PM",u"").replace(u"am",u"").replace(u"pm",u"")

    date = datetime.strptime(string.encode('utf-8'),dateform.encode('utf-8'))

    if add_hours:
        date += timedelta(hours=12)

    return date

# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(password|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)
