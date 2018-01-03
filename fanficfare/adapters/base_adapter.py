# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2017 FanFicFare team
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
from collections import defaultdict

import logging
import urlparse as up
from functools import partial
import traceback
import copy

import bs4

from ..htmlcleanup import stripHTML
from ..htmlheuristics import replace_br_with_p

logger = logging.getLogger(__name__)

from ..story import Story
from ..configurable import Configurable
from ..htmlcleanup import removeEntities, removeAllEntities, stripHTML
from ..exceptions import InvalidStoryURL

# quick convenience class
class TimeKeeper(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, timedelta)

    def add(self, name, td):
        self[name] = self[name] + td

    def __unicode__(self):
        keys = self.keys()
        keys.sort()
        return u"\n".join([ u"%s: %s"%(k,self[k]) for k in keys ])

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

        self.section_url_names(self.getSiteDomain(),self._section_url)

        ## for doing some performance profiling.
        self.times = TimeKeeper()

        self._setURL(url)
        if not self.validateURL():
            raise InvalidStoryURL(url,
                                  self.getSiteDomain(),
                                  self.getSiteExampleURLs())

    def use_pagecache(self):
        '''
        adapters that will work with the page cache need to implement
        this and change it to True.
        '''
        return False

    def _section_url(self,url):
        '''
        For adapters that have story URLs that can change.  This is
        applied both to the story URL (saved to metadata as
        sectionUrl) *and* any domain section names that it matches.
        So it is the adapter's responsibility to pass through
        *unchanged* any URLs that aren't its own.
        '''
        return url

    def _setURL(self,url):
        self.url = url
        self.parsedUrl = up.urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path
        self.story.setMetadata('storyUrl',self.url,condremoveentities=False)
        self.story.setMetadata('sectionUrl',self._section_url(self.url),condremoveentities=False)

    # Limit chapters to download.  Input starts at 1, list starts at 0
    def setChaptersRange(self,first=None,last=None):
        if not first:
            first = self.getConfig("first_chapter",default=None)
        if not last:
            last = self.getConfig("last_chapter",default=None)
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
                #logger.debug("index:%s"%index)
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
                            # logger.debug("index:%s title:%s url:%s"%(index,title,url))
                            # logger.debug(self.oldchaptersmap[url])
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

                    try:
                        if not data:
                            data = self.getChapterTextNum(url,index)
                            # if had to fetch and has existing chapters
                            newchap = bool(self.oldchapters or self.oldchaptersmap)

                        if index == 0 and self.getConfig('always_reload_first_chapter'):
                            data = self.getChapterTextNum(url,index)
                            # first chapter is rarely marked new
                            # anyway--only if it's replaced during an
                            # update.
                            newchap = False
                    except Exception as e:
                        if self.getConfig('continue_on_chapter_error',False):
                            data = self.make_soup("""<div>
<p><b>Error</b></p>
<p>FanFicFare failed to download this chapter.  Because
<b>continue_on_chapter_error</b> is set to <b>true</b>, the download continued.</p>
<p>Chapter URL:<br>%s</p>
<p>Error:<br><pre>%s</pre></p>
</div>"""%(url,traceback.format_exc().replace("&","&amp;").replace(">","&gt;").replace("<","&lt;")))
                            title = title+self.getConfig("chapter_title_error_mark","(CHAPTER ERROR)")
                            url="chapter url removed due to failure"
                        else:
                            raise

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

        # logger.debug(u"getStory times:\n%s"%self.times)
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

        # logger.debug(u"getStoryMetadataOnly times:\n%s"%self.times)
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
    def getSiteURLFragment(self):
        "Needs to be overriden in case of adapters that share a domain."
        return self.getSiteDomain()

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

    def getChapterTextNum(self, url, index):
        "For adapters that also want to know the chapter index number."
        return self.getChapterText(url)

    def getChapterText(self, url):
        "Needs to be overriden in each adapter class."
        pass

    # Just for series, in case we choose to change how it's stored or represented later.
    def setSeries(self,name,num):
        if self.getConfig('collect_series'):
            ## fractional series can come from calibre injected series.
            num = float(num)
            if num.is_integer():
                num = int(num)
            self.story.setMetadata('series','%s [%s]'%(name, num))

    def setDescription(self,url,svalue):
        #print("\n\nsvalue:\n%s\n"%svalue)
        strval = u"%s"%svalue # works for either soup or string
        if self.hasConfig('description_limit'):
            if self.getConfig('keep_summary_html'):
                # remove extra whitespaces since HTML ignores them anyway.
                # some sites waste a lot of the description_limit on
                # spaces otherwise.
                strval = re.sub(r'[ \t\n\r\f\v]{2,}',' ',strval) # \s is localized.
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
        start = datetime.now()
        soup = copy.copy(soup) # To prevent side effects by changing
                               # stuff in soup.  Added to prevent
                               # image problems when same chapter URL
                               # included more than once (base_xenforo
                               # always_include_first_post setting)
        self.times.add("utf8FromSoup->copy", datetime.now() - start)
        ## _do_utf8FromSoup broken out to separate copy & timing and
        ## allow for inherit override.
        retval = self._do_utf8FromSoup(url,soup,fetch,allow_replace_br_with_p)
        self.times.add("utf8FromSoup", datetime.now() - start)
        return retval

    def _do_utf8FromSoup(self,url,soup,fetch=None,allow_replace_br_with_p=True):
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
            for t in soup.findAll(recursive=True):
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
            start = datetime.now()
            retval = replace_br_with_p(retval)
            self.times.add("utf8FromSoup->replace_br_with_p", datetime.now() - start)

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

def cachedfetch(realfetch,cache,url,referer=None):
    if url in cache:
        return cache[url]
    else:
        return realfetch(url,referer=referer)

fullmon = {u"January":u"01", u"February":u"02", u"March":u"03", u"April":u"04", u"May":u"05",
           u"June":u"06","July":u"07", u"August":u"08", u"September":u"09", u"October":u"10",
           u"November":u"11", u"December":u"12" }

def makeDate(string,dateform):
    # Surprise!  Abstracting this turned out to be more useful than
    # just saving bytes.

    # fudge english month names for people who's locale is set to
    # non-USenglish.  Most current sites date in english, even if
    # there's non-english content -- ficbook.net, OTOH, has to do
    # something even more complicated to get Russian month names
    # correct everywhere.
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

