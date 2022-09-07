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
import re
from datetime import datetime, timedelta
from collections import defaultdict

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six import string_types as basestring
from ..six.moves.urllib.parse import urlparse, parse_qs, urlunparse

import logging
from functools import partial
import traceback
import copy

from bs4 import BeautifulSoup, Tag


from ..htmlheuristics import replace_br_with_p

logger = logging.getLogger(__name__)

from ..story import Story
from ..requestable import Requestable
from ..htmlcleanup import stripHTML
from ..exceptions import InvalidStoryURL, StoryDoesNotExist, HTTPErrorFFF

# quick convenience class
class TimeKeeper(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, timedelta)

    def add(self, name, td):
        self[name] = self[name] + td

    def __unicode__(self):
        keys = list(self.keys())
        keys.sort()
        return u"\n".join([ u"%s: %s"%(k,self[k]) for k in keys ])
import inspect
class BaseSiteAdapter(Requestable):

    @classmethod
    def matchesSite(cls,site):
        return site in cls.getAcceptDomains()

    @classmethod
    def getAcceptDomains(cls):
        return [cls.getSiteDomain()]

    def validateURL(self):
        return re.match(self.getSiteURLPattern(), self.url)

    def __init__(self, configuration, url):
        Requestable.__init__(self, configuration)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        self.storyDone = False
        self.metadataDone = False
        self.story = Story(configuration)
        self.story.setMetadata('site',self.getConfigSection())
        self.story.setMetadata('dateCreated',datetime.now())
        self.chapterUrls = [] # dicts of (chapter title,chapter url)
        self.chapterFirst = None
        self.chapterLast = None
        self.oldchapters = None
        self.oldchaptersmap = None
        self.oldchaptersdata = None
        self.oldimgs = None
        self.oldcover = None # (data of existing cover html, data of existing cover image)
        self.calibrebookmark = None
        self.logfile = None
        self.ignore_chapter_url_list = None
        self.parsed_QS = None

        self.section_url_names(self.getSiteDomain(),self.get_section_url)

        ## for doing some performance profiling.
        self.times = TimeKeeper()

        ## Save class inheritence list in metadata.  Must be added to
        ## extra_valid_entries to use.
        cl = [ c.__name__ for c in inspect.getmro(self.__class__)[::-1] ]
        cl.remove('object') # remove a few common-to-all classes
        cl.remove('BaseSiteAdapter')
        cl.remove('Configurable')
        cl.remove('Requestable')
        self.story.extendList('adapter_classes',cl)

        self._setURL(url)
        if not self.validateURL():
            raise InvalidStoryURL(url,
                                  self.getSiteDomain(),
                                  self.getSiteExampleURLs())

    @classmethod
    def get_section_url(cls,url):
        '''
        For adapters that have story URLs that can change.  This is
        applied both to the story URL (saved to metadata as
        sectionUrl) *and* any domain section names that it matches.
        So it is the adapter's responsibility to pass through
        *unchanged* any URLs that aren't its own.

        In addition to using for INI sections, now also used for
        reject list.
        '''
        return url

    def _setURL(self,url):
        self.url = url
        self.parsedUrl = urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path
        if self.parsedUrl.query:
            self.parsed_QS = parse_qs(self.parsedUrl.query)
        self.story.setMetadata('storyUrl',self.url)
        self.story.setMetadata('sectionUrl',self.get_section_url(self.url))

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

    def add_chapter(self,title,url,othermeta={}):
        ## Check for chapter URL in ignore_chapter_url_list.
        ## Normalize chapter urls, both from list and passed in, but
        ## don't save them that way to match previous behavior.
        if self.ignore_chapter_url_list == None:
            self.ignore_chapter_url_list = {}
            for u in self.getConfig('ignore_chapter_url_list').splitlines():
                self.ignore_chapter_url_list[self.normalize_chapterurl(u)] = True

        normal_chap_url = self.normalize_chapterurl(url)
        if normal_chap_url not in self.ignore_chapter_url_list:
            if self.getConfig('dedup_chapter_list',False):
                # leverage ignore list to implement dedup'ing
                self.ignore_chapter_url_list[normal_chap_url] = True

            meta = defaultdict(unicode,othermeta) # copy othermeta
            if title:
                title = stripHTML(title,remove_all_entities=False)
                # Put the basic 3 html entities back in.
                # bs4 is 'helpfully' removing them.
                title = title.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            else:
                ## A default value for when there's no chapter
                ## title. Cropped up once with adapter_novelonlinefullcom
                title = "Chapter %s"%(self.num_chapters()+1)
            meta.update({'title':title,'url':url}) # after other to make sure they are set
            self.chapterUrls.append(meta)
            self.story.setMetadata('numChapters', self.num_chapters())
            return True
        # return true/false for those adapters that count words by
        # summing chapter word counts.
        return False

    def num_chapters(self):
        return len(self.chapterUrls)

    def get_chapter(self,i,attr):
        return self.chapterUrls[i].get(attr,None)

    def get_chapters(self):
        return copy.deepcopy(self.chapterUrls)

    def del_chapter(self,i):
        del self.chapterUrls[i]
        self.story.setMetadata('numChapters', self.num_chapters())

    # Does the download the first time it's called.
    def getStory(self, notification=lambda x,y:x):
        if not self.storyDone:
            self.getStoryMetadataOnly(get_cover=True)

            ## one-off step to normalize old chapter URLs if present.
            if self.oldchaptersmap:
                self.oldchaptersmap = dict((self.normalize_chapterurl(key), value) for (key, value) in self.oldchaptersmap.items())

            percent = 0.0
            per_step = 1.0/self.story.getChapterCount()
            # logger.debug("self.story.getChapterCount():%s per_step:%s"%(self.story.getChapterCount(),per_step))
            for index, chap in enumerate(self.chapterUrls):
                title = chap['title']
                url = chap['url']
                #logger.debug("index:%s"%index)
                newchap = False
                passchap = dict(chap)
                if (self.chapterFirst!=None and index < self.chapterFirst) or \
                        (self.chapterLast!=None and index > self.chapterLast):
                    passchap['html'] = None
                else:
                    data = None
                    if self.oldchaptersmap:
                        if url in self.oldchaptersmap:
                            # logger.debug("index:%s title:%s url:%s"%(index,title,url))
                            # logger.debug(self.oldchaptersmap[url])
                            data = self.utf8FromSoup(None,
                                                     self.oldchaptersmap[url],
                                                     partial(cachedfetch,self.get_request_raw,self.oldimgs))
                    elif self.oldchapters and index < len(self.oldchapters):
                        data = self.utf8FromSoup(None,
                                                 self.oldchapters[index],
                                                 partial(cachedfetch,self.get_request_raw,self.oldimgs))

                    if self.getConfig('mark_new_chapters') == 'true':
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
                            logger.info("continue_on_chapter_error: (%s) %s"%(url,e))
                            logger.debug(traceback.format_exc())
                            url="chapter url removed due to failure"
                            self.story.chapter_error_count += 1
                        else:
                            raise

                    percent += per_step
                    notification(percent,self.url)
                    passchap['url'] = url
                    passchap['title'] = title
                    passchap['html'] = data
                    ## XXX -- add chapter text replacement here?
                    ## No?  Want to be able to configure by [writer]
                    ## It's a soup or soup part?
                self.story.addChapter(passchap, newchap)
            self.storyDone = True

            # include image, but no cover from story, add default_cover_image cover.
            if self.getConfig('include_images'):
                cover_image_url = None
                if self.getConfig('force_cover_image'):
                    cover_image_type = 'force'
                    cover_image_url = self.getConfig('force_cover_image')
                    logger.debug('force_cover_image')
                elif not self.story.cover and \
                        self.getConfig('default_cover_image'):
                    cover_image_type = 'default'
                    cover_image_url = self.getConfig('default_cover_image')
                    logger.debug('default_cover_image')
                if cover_image_url:
                    (src,longdesc) = self.story.addImgUrl(url, # chapter url as referrer
                                                          self.story.formatFileName(cover_image_url,
                                                                                    self.getConfig('allow_unsafe_filename')),
                                                          self.get_request_raw,
                                                          cover=True)
                    if src and src != 'failedtoload':
                        self.story.setMetadata('cover_image',cover_image_type)

            # copy oldcover tuple to story.
            self.story.oldcover = self.oldcover

            # cheesy way to carry calibre bookmark file forward across update.
            if self.calibrebookmark:
                self.story.calibrebookmark = self.calibrebookmark
            if self.logfile:
                self.story.logfile = self.logfile

        # logger.debug(u"getStory times:\n%s"%self.times)
        return self.story

    def getStoryMetadataOnly(self,get_cover=True):
        if not self.metadataDone:
            try:
                ## virtually all adapters were catching 404s during
                ## metdata fetch and raising StoryDoesNotExist.
                ## Consolidate in one place.
                self.doExtractChapterUrlsAndMetadata(get_cover=get_cover)
            except HTTPErrorFFF as e:
                if e.status_code in (404, 410) :
                    raise StoryDoesNotExist(self.url)
                else:
                    raise
            ## Due to some adapters calling getMetadata()etc, values
            ## may have been cached during metadata collection and
            ## *before* other values that their replace_metadata
            ## depends on.
            ##
            ## Re-arranging the collection order isn't a good
            ## solution--title could depend on category just as easily
            ## as category on title.
            ##
            ## This clears the cache before title page etc and Calibre
            ## at least.
            self.story.clear_processed_metadata_cache()

            if not self.story.getMetadataRaw('dateUpdated'):
                if self.story.getMetadataRaw('datePublished'):
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('datePublished'))
                else:
                    self.story.setMetadata('dateUpdated',self.story.getMetadataRaw('dateCreated'))

            self.metadataDone = True
            # normalize chapter urls.
            for index, chap in enumerate(self.chapterUrls):
                self.chapterUrls[index]['url'] = self.normalize_chapterurl(chap['url'])

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

        404s and 410s caught from doExtractChapterUrlsAndMetadata will
        be changed to StoryDoesNotExist.
        '''
        return self.extractChapterUrlsAndMetadata()

    def extractChapterUrlsAndMetadata(self):
        "Needs to be overriden in each adapter class.  Populates self.story metadata"

    def getChapterTextNum(self, url, index):
        "For adapters that also want to know the chapter index number."
        return self.getChapterText(url)

    def getChapterText(self, url):
        "Needs to be overriden in each adapter class."

    def before_get_urls_from_page(self,url,normalize):
        ## some sites need a login or other prep for 'from page' to
        ## work best.  Separate function to keep adapter code minimal.
        pass

    def get_urls_from_page(self,url,normalize):
        from ..geturls import get_urls_from_html
        '''
        This is a method in adapter now rather than the generic code
        that was in geturls.py to allow individual adapters to
        recognize and provide special handling if needed for series.
        Prompted largely by AO3 authors leaving links to other stories
        in story desc that were getting picked up.
        '''

        ## hook for logins, etc.
        self.before_get_urls_from_page(url,normalize)

        # this way it uses User-Agent or other special settings.
        data = self.get_request(url,usecache=True)
        series = self.get_series_from_page(url,data,normalize)
        if series:
            # just to make it easier for adapters.
            if isinstance(series.get('desc',None),(BeautifulSoup,Tag)):
                series['desc'] = self.utf8FromSoup(url,series['desc'])
            # NOTE: series desc imgs are *not* included in ebook.
            # Should they be removed?
            return series
        else:
            return {'urllist':get_urls_from_html(self.make_soup(data),
                                                 url,
                                                 configuration=self.configuration,
                                                 normalize=normalize)}

    def get_series_from_page(self,url,data,normalize=False):
        from ..geturls import get_urls_from_html
        '''
        This method is to make it easier for adapters to detect a
        series URL, pick out the series metadata and list of storyUrls
        to return without needing to override get_urls_from_page
        entirely.
        '''
        # return {}
        retval = {}
        ## return dict with at least {'urllist':['storyUrl','storyUrl',...]}
        ## 'name' and 'desc' are also used if given.

        ## for eFiction sites:
        ## http://www.dracoandginny.com/viewseries.php?seriesid=45
        # logger.debug("base get_series_from_page:%s"%url)
        try:
            if re.match(r".*(view)?series\.php\?s(erie)?sid=\d+.*",url): # seriesid or ssid
                # logger.debug("Attempting eFiction get_series_from_page")
                soup = self.make_soup(data)
                retval = {}
                nametag = soup.select_one('div#pagetitle') or soup.select_one('div#storytitle')
                # logger.debug(nametag)
                if nametag:
                    nametag.find('a').decompose()
                    retval['name'] = stripHTML(nametag)
                    # some have [ - ], some have ' by', some have both.
                    # order matters.
                    trailing_strip_list=['[ - ]',' by']
                    for s in trailing_strip_list:
                        # logger.debug(retval['name'])
                        if retval['name'].endswith(s):
                            # remove trailing s
                            retval['name'] = retval['name'][:-len(s)].strip()
                summaryspan = soup.select_one("div#titleblock span.label") or soup.select_one("div#titleblock span.classification")
                # logger.debug(summaryspan)
                if summaryspan and stripHTML(summaryspan) == "Summary:":
                    desc = ""
                    c = summaryspan.nextSibling
                    # logger.debug(c)
                    # strings and tags that aren't <span class='label'>
                    while c and not (isinstance(c,Tag) and c.name == 'span' and ('label' in c['class'] or 'classification' in c['class'])):
                        # logger.debug(c)
                        desc += unicode(c)
                        c = c.nextSibling
                        # logger.debug(c)
                    if desc:
                        # logger.debug(desc)
                        # strip spaces and trailing <br> tags.
                        desc = re.sub(r'( *<br/?>)+$','',desc.strip())
                        # logger.debug(desc)
                        retval['desc']=desc.strip()
                else:
                    # some(1?) sites
                    summarydiv = soup.select_one("div.summarytext") or soup.select_one("blockquote2") # fanfictalk.com
                    summarydiv.name='div' # force name to div.
                    if summarydiv:
                        retval['desc']=summarydiv

                # trying to get story urls for series from different
                # eFictions is a nightmare that the pre-existing
                # get_urls_from_html() handles well enough.
                # logger.debug(soup)
                retval['urllist']=get_urls_from_html(soup,
                                                     url,
                                                     configuration=self.configuration,
                                                     normalize=normalize)
        except Exception as e:
            logger.debug("get_series_from_page for eFiction failed:%s"%e)
            retval = {}
        return retval

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
                svalue = BeautifulSoup(svalue,"html5lib").body
            self.story.setMetadata('description',self.utf8FromSoup(url,svalue))
        else:
            self.story.setMetadata('description',stripHTML(svalue))
        #print("\n\ndescription:\n"+self.story.getMetadata('description')+"\n\n")

    def setCoverImage(self,storyurl,imgurl):
        if self.getConfig('include_images'):
            logger.debug("setCoverImage(%s,%s)"%(storyurl,imgurl))
            return self.story.addImgUrl(storyurl,imgurl,self.get_request_raw,cover=True,
                                        coverexclusion=self.getConfig('cover_exclusion_regexp'))
        else:
            return (None,None)

    # bs3 & bs4 were different here.
    def get_attr_keys(self,soup):
        if hasattr(soup, 'attrs') and isinstance(soup.attrs,dict):
            #print "bs4 attrs:%s"%soup.attrs.keys()
            # bs4
            return list(soup.attrs.keys())
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

    def remove_class_chapter(self,soup):
        def rm_chp_cls(t):
            t['class'].remove('chapter')
            if not t['class']: # remove if list empty now.
                del t['class']
        for t in soup.select('.chapter'):
            rm_chp_cls(t)
        # if soup is itself a tag with class='chapter', select doesn't
        # find it.
        if soup.has_attr('class') and 'chapter' in soup['class']:
            rm_chp_cls(soup)

    def _do_utf8FromSoup(self,url,soup,fetch=None,allow_replace_br_with_p=True):
        if not fetch:
            fetch=self.get_request_raw

        acceptable_attributes = self.getConfigList('keep_html_attrs',['href','name','class','id','data-orighref'])

        if self.getConfig("keep_style_attr"):
            acceptable_attributes.append('style')
        if self.getConfig("keep_title_attr"):
            acceptable_attributes.append('title')

        #print("include_images:"+self.getConfig('include_images'))
        if self.getConfig('include_images'):
            ## actually effects all tags' attrs, not just <img>, but I'm okay with that.
            acceptable_attributes.extend(('src','alt','longdesc'))
            for img in soup.find_all('img'):
                try:
                    # some pre-existing epubs have img tags that had src stripped off.
                    if img.has_attr('src'):
                        (img['src'],img['longdesc'])=self.story.addImgUrl(url,img['src'],fetch,
                                                                          coverexclusion=self.getConfig('cover_exclusion_regexp'))
                except AttributeError as ae:
                    logger.info("Parsing for img tags failed--probably poor input HTML.  Skipping img(%s)"%img)
        else:
            ## remove all img tags entirely
            for img in soup.find_all('img'):
                img.decompose()

        for attr in self.get_attr_keys(soup):
            if attr not in acceptable_attributes:
                del soup[attr] ## strip all tag attributes except configured

        ## some tags, notable chapter div from Base eFiction have
        ## class='chapter', which causes calibre convert to id it as a
        ## chapter and 'pagebreak' - AKA split the file.  Remove by
        ## default, but only if class otherwise allowed (minor perf opt).
        if 'class' in acceptable_attributes and self.getConfig('remove_class_chapter',True):
            self.remove_class_chapter(soup)

        ## Make relative links in text into absolute links using page
        ## URL.
        if self.getConfig('fix_relative_text_links'):
            for alink in soup.find_all('a'):
                if alink.has_attr('href'):
                    toppath=""
                    href = alink['href']
                    ## Mistakenly ended up with some // in image urls, like:
                    ## https://forums.spacebattles.com//styles/default/xenforo/clear.png
                    ## Removing one /, but not ://
                    if not href.startswith("file:"): # keep file:///
                        href = re.sub(r"([^:])//",r"\1/",href)
                    if href.startswith("http") or href.startswith("file:") or url == None:
                        hrefurl = href
                    else:
                        parsedUrl = urlparse(url)
                        if href.startswith("//") :
                            hrefurl = urlunparse(
                                (parsedUrl.scheme,
                                 '',
                                 href,
                                 '','',''))
                        elif href.startswith("/") :
                            hrefurl = urlunparse(
                                (parsedUrl.scheme,
                                 parsedUrl.netloc,
                                 href,
                                 '','',''))
                        else:
                            if parsedUrl.path.endswith("/"):
                                toppath = parsedUrl.path
                            else:
                                toppath = parsedUrl.path[:parsedUrl.path.rindex('/')+1]
                            hrefurl = urlunparse(
                                (parsedUrl.scheme,
                                 parsedUrl.netloc,
                                 toppath + href,
                                 '','',''))
                    alink['href'] = hrefurl
                    # logger.debug("\n===========\nparsedUrl.path:%s\ntoppath:%s\nhrefurl:%s\n\n"%(parsedUrl.path,toppath,hrefurl))

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
            # python doesn't have a do-while loop.
            found_empty=True
            do_resoup=False
            while found_empty==True:
                found_empty=False
                if do_resoup:
                    # re-soup when empty tags removed before looking
                    # for more because multiple 'whitespace' strings
                    # show up differently and doing stripHTML() also
                    # catches <br> etc.
                    soup = BeautifulSoup(unicode(soup),'html5lib')
                for t in soup.findAll(recursive=True):
                    for attr in self.get_attr_keys(t):
                        if attr not in acceptable_attributes:
                            del t[attr] ## strip all tag attributes except acceptable_attributes

                    if t and hasattr(t,'name') and t.name is not None:
                        # remove script tags cross the board.
                        # epub readers (Moon+, FBReader & Aldiko at least)
                        # don't like <style> tags in body.
                        if t.name in self.getConfigList('remove_tags',['script','style']):
                            t.decompose()
                            continue

                        # these are not acceptable strict XHTML.  But we
                        # do already have CSS classes of the same names
                        # defined
                        if t.name in self.getConfigList('replace_tags_with_spans',['u']):
                            t['class']=t.name
                            t.name='span'
                        if t.name in ('center'):
                            t['class']=t.name
                            t.name='div'

                        # Removes paired, but empty non paragraph
                        # tags.  Make another pass if any are found in
                        # case parent is now empty.  Could add
                        # significant time if deeply nested empty
                        # tags.
                        tmp = t
                        if tmp.name not in self.getConfigList('keep_empty_tags',['p','td','th']) and t.string != None and len(t.string.strip()) == 0:
                            found_empty==True
                            do_resoup=True
                            tmp.decompose()

        except AttributeError as ae:
            if "%s"%ae != "'NoneType' object has no attribute 'next_element'":
                logger.error("Error parsing HTML, probably poor input HTML. %s"%ae)

        retval = unicode(soup)

        if self.getConfig('nook_img_fix') and not self.getConfig('replace_br_with_p'):
            # if the <img> tag doesn't have a div or a p around it,
            # nook gets confused and displays it on every page after
            # that under the text for the rest of the chapter.
            retval = re.sub(r"(?!<(div|p)>)\s*(?P<imgtag><img[^>]+>)\s*(?!</(div|p)>)",
                            r"<div>\g<imgtag></div>",retval)

        # Don't want html, head or body tags in chapter html--writers add them.
        # This is primarily for epub updates.
        retval = re.sub(r"</?(html|head|body)[^>]*>\r?\n?","",retval)

        try:
            xbr = int(self.getConfig("replace_xbr_with_hr",default=0))
            if xbr > 0:
                start = datetime.now()
                retval = re.sub(r'(\s*<br[^>]*>\s*){%d,}'%xbr,
                                '<br/>\n<br/>\n<hr/>\n<br/>',retval)
                self.times.add("utf8FromSoup->replace_xbr_with_hr", datetime.now() - start)
        except:
            logger.debug("Ignoring non-int replace_xbr_with_hr(%s)"%self.getConfig("replace_xbr_with_hr"))

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
        ## https://bugs.launchpad.net/beautifulsoup/+bug/1277464 This
        ## should 'hide' and restore <noscript> tags.  Need to do
        ## </?noscript instead of noscript> as of Apr2022 when SB
        ## added a class attr to noscript.  2x replace() faster than
        ## re.sub() in simple test
        data = data.replace("<noscript","<fff_hide_noscript").replace("</noscript","</fff_hide_noscript")

        ## soup and re-soup because BS4/html5lib is more forgiving of
        ## incorrectly nested tags that way.
        soup = BeautifulSoup(data,'html5lib')
        soup = BeautifulSoup(unicode(soup),'html5lib')

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

    dateform = dateform.strip()
    string = string.strip()
    try:
        date = datetime.strptime(string, dateform)
    except ValueError:
        ## If parse fails and looking for 01-12 hours, try 01-24 hours too.
        ## A moderately cheesy way to support 12 and 24 hour clocks.
        if u"%I" in dateform:
            dateform = dateform.replace(u"%I",u"%H")
            date = datetime.strptime(string, dateform)
            add_hours = False
        else:
            raise

    if add_hours:
        date += timedelta(hours=12)

    return date
