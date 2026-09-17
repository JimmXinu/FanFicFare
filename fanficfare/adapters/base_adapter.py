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

import re
import os
from datetime import datetime, timedelta
from collections import defaultdict


from urllib.parse import urlparse, parse_qs, urljoin

import logging
from functools import partial
import traceback
import copy

from bs4 import BeautifulSoup, Tag


from ..htmlheuristics import replace_br_with_p

logger = logging.getLogger(__name__)

from ..story import Story
from ..requestable import Requestable
from ..htmlcleanup import stripHTML, decode_email
from ..exceptions import InvalidStoryURL, StoryDoesNotExist, HTTPErrorFFF, ConflictingOptions

# was defined here before, imported for all the adapters that still
# expect it.
from ..dateutils import makeDate

# quick convenience class
class TimeKeeper(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, timedelta)

    def add(self, name, td):
        self[name] = self[name] + td

    def __str__(self):
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
        self.totp = None # Timed One Time Password(TOTP) for 2FA
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
        self.add_img_names = None

        self.calibrebookmark = None
        self.logfile = None
        self.ignore_chapter_url_list = None
        self.dedup_chapter_urls = set()
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

    @classmethod
    def get_url_search(cls,url):
        '''
        For adapters that have story URLs that can change.  This is
        used for searching the Calibre library by identifiers:url for
        sites (generally) that contain author or title that can
        change, but also have a unique identifier that doesn't.

        returns string containing Calibre search string (which contains a regexp)
        '''
        # older idents can be uri vs url and have | instead of : after
        # http, plus many sites are now switching to https.
        # logger.debug(url)
        regexp = r'identifiers:"~ur(i|l):~^https?%s$"'%(re.sub(r'^https?','',re.escape(url)))
        # logger.debug(regexp)
        return regexp

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

    def get_ignore_chapter_url_list(self):
        if self.ignore_chapter_url_list == None:
            self.ignore_chapter_url_list = set()
            for u in self.getConfig('ignore_chapter_url_list').splitlines():
                self.ignore_chapter_url_list.add(self.normalize_chapterurl(u))
        return self.ignore_chapter_url_list

    def add_chapter(self,title,url,othermeta={}):
        ## Check for chapter URL in ignore_chapter_url_list.
        ## Normalize chapter urls, both from list and passed in
        normal_chap_url = self.normalize_chapterurl(url)
        if normal_chap_url not in self.get_ignore_chapter_url_list():
            if self.getConfig('dedup_chapter_list',False):
                ## Note that update_preserve_deleted_chapters also
                ## dedups chapter urls in the exceedingly rare case of
                ## duplicate chapter URLs that are later all removed.
                if normal_chap_url in self.dedup_chapter_urls:
                    logger.debug("dedup_chapter_list: Skipping dup chapter url %s"%url)
                    return False
                else:
                    self.dedup_chapter_urls.add(normal_chap_url)

            meta = defaultdict(str,othermeta) # copy othermeta
            if title:
                title = stripHTML(title,remove_all_entities=False)
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

    def _chapter_text(self, html_or_soup):
        """Normalize chapter content for change detection.

        Strips the epubutils-style title/skip blocks and HTML, then
        collapses whitespace so stored and freshly downloaded chapters
        can be compared on text alone.  Accepts either an html string
        or a BeautifulSoup object."""
        if not html_or_soup:
            return ''
        try:
            from bs4 import BeautifulSoup as _BS
            if isinstance(html_or_soup, str):
                soup = _BS(html_or_soup, 'html.parser')
            else:
                soup = html_or_soup
        except Exception:
            soup = _BS(str(html_or_soup), 'html.parser')
        # mirror epubutils.get_update_data stripping of the chapter
        # title and skip_on_ffdl_update blocks
        hx = soup.select_one('.fff_chapter_title')
        if not hx:
            hx = soup.select_one('body > h2, h3')
        if hx:
            hx.extract()
        for skip in soup.find_all(attrs={'class': 'skip_on_ffdl_update'}):
            skip.extract()
        body = soup.find('body') or soup
        text = stripHTML(body)
        return re.sub(r'\s+', ' ', text).strip()

    def _chapter_needs_recheck(self, url, index, total_site_chapters):
        """Determine if a chapter should be re-downloaded for edit detection.

        The edit-check window is the LAST recent_count chapters of the
        OLD EPUB in reading order, NOT the last recent_count chapters of
        the site.  With a site-based window the "most recent" site
        chapters are usually brand-new ones that are not in the epub at
        all, so no previously-downloaded chapter ever gets re-checked;
        an epub-based window keeps re-checking the chapters the reader
        most recently got (the ones authors most often edit) even after
        the site has grown far past them.  index/total_site_chapters
        are accepted for API compatibility but no longer used here.
        """
        recent_count = int(self.getConfig('update_check_recent_chapters', 0) or 0)

        if recent_count > 0 and self.oldchaptersmap:
            try:
                if list(self.oldchaptersmap.keys()).index(url) >= \
                        len(self.oldchaptersmap) - recent_count:
                    return True
            except ValueError:
                pass

        return False

    def preserve_deleted_chapters(self):
        """True when chapters missing from the site should be preserved
        in the updated epub."""
        retval = self.getConfig('update_preserve_deleted_chapters')
        if retval and (self.chapterFirst is not None or \
                           self.chapterLast is not None):
            ## Chapter ranges are applied to the chapter list *from
            ## the site*.  If it changes (which is the whole point of
            ## update_preserve_deleted_chapters), things get confused
            ## and chapters aren't preserved correctly.
            ##
            ## It will make more of a difference if/when
            ## saving/reusing chapter is implemented.
            ## https://github.com/JimmXinu/FanFicFare/issues/1413
            raise ConflictingOptions("Cannot use chapter range with update_preserve_deleted_chapters:true")
        return retval

    def recheck_recent_chapters(self):
        """True when edit detection wants previously-downloaded chapters
        re-downloaded during an update (recent-window)."""
        return bool(int(self.getConfig('update_check_recent_chapters') or 0))

    def _recheck_chapter(self, url, index):
        """Re-download a chapter for edit detection and keep the fresh
        version only if its content differs from the stored one.

        Returns the html bytes/string to use for the chapter.  Falls
        back to the stored chapter on download/parse failure so an
        edit-check problem never drops a chapter.
        """
        try:
            fresh_data = self.getChapterTextNum(url, index)
            if self._chapter_text(fresh_data) != self._chapter_text(self.oldchaptersmap[url]):
                # Content changed, use fresh version
                self.story.chapter_updated_count += 1
                logger.info("Chapter %d (%s) content changed, using updated version" % (index+1, url))
                return fresh_data
            # Content unchanged, reuse old
            return self.utf8FromSoup(None,
                                     self.oldchaptersmap[url])
        except Exception as e:
            logger.warning("Edit check for %s failed, reusing old: %s" % (url, e))
            return self.utf8FromSoup(None,
                                     self.oldchaptersmap[url])

    def _preserve_deleted_chapters(self):
        """Carry forward chapters that were in the old epub but are no
        longer on the site.

        Preserved chapters are inserted at their original position
        relative to the remaining site chapters so chronological order
        is kept.  After assembly the final chapters are renumbered so
        the 'number'/'index04'/'index' fields (used by chapter_title
        patterns) are stable even though preserved chapters were
        inserted mid-list.
        """
        if not (self.preserve_deleted_chapters() and self.oldchaptersmap):
            return

        site_urls = set(ch['url'] for ch in self.chapterUrls)
        old_urls_in_order = list(self.oldchaptersmap.keys())
        preserve_list = []
        for old_url in old_urls_in_order:
            ## apply ignore_chapter_url_list otherwise any chapters user
            ## adds to ignore_chapter_url_list will be preserved.
            normal_chap_url = self.normalize_chapterurl(old_url)
            if old_url not in site_urls and \
                    normal_chap_url not in self.get_ignore_chapter_url_list():
                preserve_list.append(old_url)

        for old_url in preserve_list:
            old_soup = self.oldchaptersmap[old_url]

            # Preserve this chapter as a deleted chapter
            # Restore the chapter's real title.  The old soup
            # no longer carries it (epubutils.get_update_data
            # strips the leading fff_chapter_title heading), so
            # prefer the chaptertitle/origtitle recorded in the
            # epub's <meta> tags, then any h3 left in the old
            # soup, then the URL slug as a last resort.
            old_data = self.oldchaptersdata.get(old_url, {}) \
                if self.oldchaptersdata else {}
            old_title = old_data.get('chaptertitle') or \
                old_data.get('chapterorigtitle')
            if not old_title:
                old_h3 = old_soup.find('h3') if old_soup else None
                if old_h3:
                    old_title = old_h3.get_text(strip=True)
            if not old_title:
                old_title = old_url.split('/')[-1].replace('-', ' ').replace('_', ' ')
            preserved_chap = {
                'url': old_url,
                'title': old_title,
                'html': self.utf8FromSoup(None, old_soup) if old_soup else '',
                'preserved_chapter_mark': self.getConfig('preserved_chapter_mark','(Preserved Deleted Chapter)'),
            }
            # Use addChapter() so the chapter dict gets all the
            # fields getChapters() expects ('new', 'number',
            # 'index04', 'index', 'origtitle', 'toctitle').
            # addChapter() appends; then move the chapter into
            # its chronological slot, before the first surviving
            # site chapter that originally followed it.
            self.story.addChapter(dict(preserved_chap), newchap=False)
            preserved = self.story.chapters.pop()
            ch_index = len(self.story.chapters)
            last_survivor_index = -1
            for i, existing in enumerate(self.story.chapters):
                if existing['url'] in old_urls_in_order:
                    last_survivor_index = i
                    if old_urls_in_order.index(existing['url']) > old_urls_in_order.index(old_url):
                        ch_index = i
                        break
            else:
                # No surviving site chapter originally followed
                # this one (everything after it on the site was
                # deleted).  Insert just after the last surviving
                # old chapter so it lands BEFORE brand-new
                # chapters instead of after them.
                if last_survivor_index >= 0:
                    ch_index = last_survivor_index + 1
            self.story.chapters.insert(ch_index, preserved)
            logger.info("Preserved deleted chapter: %s" % old_url)

        # Renumber chapters to match the final chronological order.
        # No-op when all chapters were appended in order.
        for i, ch in enumerate(self.story.chapters):
            ch['number'] = i + 1
            num = '%04d' % (i + 1)
            ch['index04'] = num
            ch['index'] = num

    def _report_update_counters(self):
        """Log the final book's chapter composition: chapters carried
        from the old epub and chapters genuinely added.  Counted after
        assembly so the totals reflect the epub that will actually be
        written."""
        old_urls = set((self.oldchaptersmap or {}).keys())
        final_urls = {ch['url'] for ch in self.story.chapters}
        new_urls = final_urls - old_urls
        self.story.chapter_added_count = len(new_urls)
        self.story.chapter_written_count = len(self.story.chapters)
        logger.info("UPDATE_COUNTERS updated="+str(self.story.chapter_updated_count)+" added="+str(self.story.chapter_added_count)+" written="+str(self.story.chapter_written_count)+" old_urls="+str(len(old_urls))+" new_urls="+str(len(new_urls)))

    def img_url_trans(self,imgurl):
        "Hook for transforming img urls in adapter"
        return imgurl

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
            continue_on_chapter_error_try_limit = 5
            try:
                continue_on_chapter_error_try_limit = int(self.getConfig('continue_on_chapter_error_try_limit',
                                                                         continue_on_chapter_error_try_limit))
            except:
                logger.warning('Parsing continue_on_chapter_error_try_limit:%s failed, using %s'%(
                        self.getConfig('continue_on_chapter_error_try_limit'),
                        continue_on_chapter_error_try_limit))

            def do_error_chapter(txt,title):
                data = self.make_soup(txt)
                title = title+self.getConfig("chapter_title_error_mark","(CHAPTER ERROR)")
                url="chapter url removed due to failure"
                return data, title, url

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
                            # Check if edit detection wants us to
                            # re-check this chapter.
                            if self._chapter_needs_recheck(
                                    url, index, len(self.chapterUrls)):
                                data = self._recheck_chapter(url, index)
                            else:
                                # logger.debug("index:%s title:%s url:%s"%(index,title,url))
                                # logger.debug(self.oldchaptersmap[url])
                                data = self.utf8FromSoup(None,
                                                         self.oldchaptersmap[url])
                    elif self.oldchapters and index < len(self.oldchapters):
                        data = self.utf8FromSoup(None,
                                                 self.oldchapters[index])

                    if self.getConfig('mark_new_chapters') == 'true':
                        # if already marked new -- ie, origtitle and title don't match
                        # logger.debug("self.oldchaptersdata[url]:%s"%(self.oldchaptersdata[url]))
                        newchap = (self.oldchaptersdata is not None and
                                   url in self.oldchaptersdata and (
                                self.oldchaptersdata[url]['chapterorigtitle'] !=
                                self.oldchaptersdata[url]['chaptertitle']) )

                    try:
                        if not data:
                            if( self.getConfig('continue_on_chapter_error') and
                                continue_on_chapter_error_try_limit > 0 and # for -1 == infinite
                                self.story.chapter_error_count >= continue_on_chapter_error_try_limit ):
                                logger.info("continue_on_chapter_error: (%s) continue_on_chapter_error_try_limit(%s) exceeded"%(url,continue_on_chapter_error_try_limit))
                                self.story.chapter_error_count += 1
                                data, title, url = do_error_chapter("""<div>
<p><b>Error</b></p>
<p>FanFicFare didn't try to download this chapter, due to earlier chapter errors.</p><p>
Because <b>continue_on_chapter_error:true</b> is set, processing continued, but because
<b>continue_on_chapter_error_try_limit</b>(%s) has been exceeded, this chapter did not
try to download.</p>
<p>Chapter URL:<br><a href="%s">%s</a></p>
</div>"""%(continue_on_chapter_error_try_limit,url,url),title)
                            else:
                                data = self.getChapterTextNum(url,index)
                                # if had to fetch and has existing chapters
                                newchap = bool(self.oldchapters or self.oldchaptersmap)

                        if index == 0 and self.getConfig('always_reload_first_chapter'):
                            data = self.getChapterTextNum(url,index)
                            # preserve newchap from edit detection if active
                            if not self.recheck_recent_chapters():
                                newchap = False
                    except Exception as e:
                        if self.getConfig('continue_on_chapter_error',False):
                            logger.info("continue_on_chapter_error: (%s) %s"%(url,e))
                            logger.debug(traceback.format_exc())
                            self.story.chapter_error_count += 1
                            data, title, url = do_error_chapter("""<div>
<p><b>Error</b></p>
<p>FanFicFare failed to download this chapter.  Because
<b>continue_on_chapter_error</b> is set to <b>true</b>, the download continued.</p>
<p>Chapter URL:<br><a href="%s">%s</a></p>
<p>Error:<br><pre>%s</pre></p>
</div>"""%(url,url,traceback.format_exc().replace("&","&amp;").replace(">","&gt;").replace("<","&lt;")),title)
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

            # Carry forward chapters that are no longer on the site
            # (preservation) and renumber, then report the chapter
            # composition of the final book.
            self._preserve_deleted_chapters()
            self._report_update_counters()

            self.storyDone = True

            # copy oldcover tuple to story.
            self.story.oldcover = self.oldcover

            # include image, but no cover from story, add default_cover_image cover.
            if self.getConfig('include_images'):
                cover_image_url = None
                if self.getConfig('force_cover_image'):
                    cover_image_type = 'force'
                    cover_image_url = self.getConfig('force_cover_image')
                    logger.debug('force_cover_image')
                elif( self.getConfig('default_cover_image') and
                      not self.story.cover and
                      not (self.story.oldcover and
                           self.getConfig('use_old_cover')) ):
                    ## oldcover will only ever be available during
                    ## epub update.  FFF was including default image
                    ## even when oldcover was used if they had
                    ## different names--such as calibre injected
                    ## cover
                    cover_image_type = 'default'
                    cover_image_url = self.getConfig('default_cover_image')
                    logger.debug('default_cover_image')
                if cover_image_url:
                    (src,longdesc) = self.story.addImgUrl(url, # chapter url as referrer
                                                          self.story.formatFileName(cover_image_url,
                                                                                    self.getConfig('allow_unsafe_filename')),
                                                          self.get_request_raw,
                                                          cover=cover_image_type)
                    if src and not src.startswith('failedtoload'):
                        self.story.setMetadata('cover_image',cover_image_type)

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

        ## load existing epub images in story ImageStore so they
        ## are re-used, but not processed again.  Prior system was
        ## simple url->data cache wedged in front of fetch.
        if self.oldimgs:
            self.story.load_oldimgs(self.oldimgs)

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
        data = self.get_request(url,usecache=False)
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
                        desc += str(c)
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
            if isinstance(svalue,str):
                # bs4/html5lib add html, header and body tags, which
                # we don't want.  utf8FromSoup will strip the body tags for us.
                svalue = BeautifulSoup(svalue,"html5lib").body
            self.story.setMetadata('description',self.utf8FromSoup(url,svalue))
        else:
            self.story.setMetadata('description',stripHTML(svalue))
        #print("\n\ndescription:\n"+self.story.getMetadata('description')+"\n\n")

    def setCoverImage(self,storyurl,imgurl):
        ## Why isn't explicitly set cover image cached/retrieved from
        ## epub on update?
        ## - CLI especially calls metadata collection before reading
        ## update epub because it might need the title etc to find the
        ## update file.
        ## - setCoverImage(& therefore addImgUrl) called during metadata
        ## collection so we know if cover download worked or not.
        ## - Where would epub remember cover URL? cover.xhtml <img
        ## longdesc=> is the obvious place, but covers are poked more
        ## than other images by other tools.
        ## - Some users change the cover, but don't want to change first
        ## image, may cause problems if cover orig url remembered.
        if self.getConfig('include_images'):
            logger.debug("setCoverImage(%s,%s)"%(storyurl,imgurl))
            return self.story.addImgUrl(storyurl,
                                        self.img_url_trans(imgurl),
                                        self.get_request_raw,cover="specific",
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

    def is_additional_image(self,url):
        if self.add_img_names is None:
            self.add_img_names = [ "images/"+os.path.basename(imgfn) for imgfn in self.getConfigList('additional_images') ]
        return url in self.add_img_names

    def include_css_urls(self,parenturl,style):
        FONT_EXTS = ('ttf','otf','woff','woff2')
        # logger.debug("include_css_urls(%s,%s)"%(parenturl,style))
        ## pass in the style string, will be returned with URLs
        ## replaced and images will be added.
        newstyle = style
        if 'url(' in style:
            ## url(href)
            ## url("href")
            ## url('href')
            ## the pattern will also accept mismatched '/", which is broken CSS.
            for style_url in re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style):
                ## additional_images don't get processing.  Applies
                ## only to CSS url(), that should be the only time
                ## additional_images is used.
                if self.is_additional_image(style_url):
                    logger.debug("Skipping sheet style url(%s), in additional_images"%style_url)
                    continue
                if style_url.rsplit('.')[-1].lower() in FONT_EXTS:
                    logger.debug("Skipping sheet style url(%s), assumed font"%style_url)
                    continue
                logger.debug("Adding style url(%s)"%style_url)

                try:
                    # longdesc(aka origurl) isn't saved anywhere in CSS.
                    (src,longdesc)=self.story.addImgUrl(parenturl,self.img_url_trans(style_url),
                                                        self.get_request_raw,
                                                        # no CSS image may be cover.
                                                        coverexclusion=r'.')
                    newstyle = newstyle.replace(style_url,src)
                except AttributeError as ae:
                    logger.info("CSS url() image failed.  Skipping url(%s)"%style_url)
        return newstyle

    # This gives us a str object, not just a string containing bytes.
    # (I gave soup a str string, you'd think it could give it back...)
    # Now also does a bunch of other common processing for us.
    def utf8FromSoup(self,url,soup,fetch=None,allow_replace_br_with_p=True):
        start = datetime.now()
        soup = copy.copy(soup) # To prevent side effects by changing
                               # stuff in soup.  Added to prevent
                               # image problems when same chapter URL
                               # included more than once (base_xenforo
                               # always_include_first_post setting)
        if not soup:
            raise TypeError("utf8FromSoup called with soup (%s)"%soup)
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

        if self.getConfig("decode_emails",True):
            # <a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="c7ada8afa9a3a8a287a2aaa6aeabe9a4a8aa">[email&#160;protected]</a>
            # <a href="/cdn-cgi/l/email-protection#e3a18f8a8d87ae8c969086d2d7d0a3b3abac8d869790cd8c9184"><span class="__cf_email__" data-cfemail="296b4540474d64465c5a4c181d1a69796166474c5d5a07465b4e">[email&#160;protected]</span></a>
            for emailtag in soup.select('a.__cf_email__') + soup.select('span.__cf_email__'):
                tagtext = '(tagtext not set yet)'
                try:
                    tagtext = str(emailtag)
                    emaildata = emailtag['data-cfemail']
                    if not emaildata:
                        continue
                    addr = decode_email(emaildata)
                    repltag = emailtag
                    if( emailtag.name == 'span' and
                        emailtag.parent.name == 'a' and
                        emailtag.parent['href'].startswith('/cdn-cgi/l/email-protection') ):
                        repltag = emailtag.parent
                    repltag.name='span'
                    if repltag.has_attr('href'):
                        del repltag['href']
                    repltag['class']='decoded_email'
                    repltag.string = addr
                except Exception as e:
                    logger.info("decode_emails failed on (%s)"%tagtext)
                    logger.info(e)
                    logger.debug(traceback.format_exc())

        acceptable_attributes = self.getConfigList('keep_html_attrs',['href','name','class','id','data-orighref'])

        if self.getConfig("keep_style_attr"):
            acceptable_attributes.append('style')
        if self.getConfig("keep_title_attr"):
            acceptable_attributes.append('title')

        #print("include_images:"+self.getConfig('include_images'))
        if self.getConfig('include_images') == 'true': # not false or coveronly
            ## actually effects all tags' attrs, not just <img>, but I'm okay with that.
            acceptable_attributes.extend(('src','alt','longdesc'))
            for img in soup.find_all('img'):
                try:
                    # some pre-existing epubs have img tags that had src stripped off.
                    if img.has_attr('src'):
                        (img['src'],longdesc)=self.story.addImgUrl(url,self.img_url_trans(img['src']),fetch,
                                                                   coverexclusion=self.getConfig('cover_exclusion_regexp'))
                        if longdesc:
                            # logger.debug("---set longdesc:%s"%longdesc)
                            img['longdesc'] = longdesc
                except AttributeError as ae:
                    logger.info("Parsing for img tags failed--probably poor input HTML.  Skipping img(%s)"%img)
            ## Inline CSS url() images
            for inline in soup.select('*[style]'):
                # Only if there's something in that tag.  mostly for
                # empty <span style=> where media embed failed on XF
                # sites.  Prevents including unseeable images.
                if inline.contents:
                    inline['style'] = self.include_css_urls(url,inline['style'])
            ## Embedded CSS <style> tag url() images
            for embedded in soup.select('style'):
                embedded.string = self.include_css_urls(url,embedded.string)
        elif self.getConfig('keep_img_tags'):
            logger.debug("keep_img_tags")
            ## keep <img>s normalize src attrs.
            acceptable_attributes.extend(('src','alt'))
            for img in soup.find_all('img'):
                if img.has_attr('src'):
                    img['src'] = urljoin(url,img['src'])
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
                if alink.has_attr('href') and alink['href']: # Saw some links with href=""
                    ## hrefurl now also the flag for been-handled / needs-handled
                    hrefurl = None
                    toppath=""
                    href = alink['href']
                    ## Mistakenly ended up with some // in image urls, like:
                    ## https://forums.spacebattles.com//styles/default/xenforo/clear.png
                    ## Removing one /, but not ://
                    if not href.startswith("file:"): # keep file:///
                        href = re.sub(r"([^:])//",r"\1/",href)
                    ## Link to an #anchor tag, keep if target tag also
                    ## in chapter text--any tag's id, not just <a>s
                    ## Came up in issue #952
                    ## Somebody put a '.' in the ID; this should
                    ## handle identifiers that otherwise appear to be
                    ## selectors themselves.  #966
                    try:
                        # logger.debug("Search for internal link anchor href:(%s)"%href)
                        if href[0] == "#" and soup.select_one("[id='%s'], [name='%s']"%(href[1:],href[1:])):
                            # logger.debug("Found internal link anchor href:(%s)"%href)
                            hrefurl = href
                    except Exception as e:
                        logger.debug("Search for internal link anchor failed href:(%s)"%href)

                    if href.startswith("http") or href.startswith("file:") or url == None:
                        hrefurl = href

                    ## make link absolute if not one of the above.
                    if not hrefurl:
                        hrefurl = urljoin(url,href)
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
                    soup = BeautifulSoup(str(soup),'html5lib')
                for t in soup.find_all(recursive=True):
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
                        if t.name in ['center']:
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

        retval = str(soup)

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

        if self.getConfig('remove_empty_p'):
            # Remove <p> tags that contain only whitespace and/or <br>
            # tags.  Generally for AO3/OTW because their document
            # converter tends to add them where not intended.
            retval = re.sub(r"<p[^>]*>\s*(\s*<br ?/?>\s*)*\s*</p>","",retval)

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
        soup = BeautifulSoup(str(soup),'html5lib')

        for ns in soup.find_all('fff_hide_noscript'):
            ns.name = 'noscript'

        return soup

    ## For adapters, especially base_xenforoforum to override.  Make
    ## sure to return unchanged URL if it's NOT a chapter URL...
    def normalize_chapterurl(self,url):
        return url
