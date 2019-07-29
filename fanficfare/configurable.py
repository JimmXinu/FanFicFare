# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2019 FanFicFare team
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
import codecs

# py2 vs py3 transition
from . import six
from .six.moves import configparser
from .six.moves.configparser import DEFAULTSECT, MissingSectionHeaderError, ParsingError
from .six.moves import urllib
from .six.moves.urllib.parse import urlencode
from .six.moves.urllib.request import (build_opener, HTTPCookieProcessor, Request)
from .six.moves.urllib.error import HTTPError
from .six.moves import http_cookiejar as cl
from .six import text_type as unicode
from .six import string_types as basestring
from .six import ensure_binary, ensure_text

import time
import logging
import sys
import pickle

from . import exceptions

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

try:
    import chardet
except ImportError:
    chardet = None

from .gziphttp import GZipProcessor
from .htmlcleanup import reduce_zalgo

# All of the writers(epub,html,txt) and adapters(ffnet,twlt,etc)
# inherit from Configurable.  The config file(s) uses ini format:
# [sections] with key:value settings.
#
# [defaults]
# titlepage_entries: category,genre, status
# [www.whofic.com]
# titlepage_entries: category,genre, status,dateUpdated,rating
# [epub]
# titlepage_entries: category,genre, status,datePublished,dateUpdated,dateCreated
# [www.whofic.com:epub]
# titlepage_entries: category,genre, status,datePublished
# [overrides]
# titlepage_entries: category

logger = logging.getLogger(__name__)

# Work around for fact that py3 apparently doesn't allow/ignore
# recursive imports like py2 does.
try:
    from . import adapters
except ImportError:
    import sys
    if "fanficfare.adapters" in sys.modules:
        adapters = sys.modules["fanficfare.adapters"]
    elif "calibre_plugins.fanficfare_plugin.fanficfare.adapters" in sys.modules:
        adapters = sys.modules["calibre_plugins.fanficfare_plugin.fanficfare.adapters"]

def re_compile(regex,line):
    try:
        return re.compile(regex,re.DOTALL)
    except Exception as e:
        raise exceptions.RegularExpresssionFailed(e,regex,line)

# fall back labels.
titleLabels = {
    'category':'Category',
    'genre':'Genre',
    'language':'Language',
    'status':'Status',
    'series':'Series',
    'characters':'Characters',
    'ships':'Relationships',
    'datePublished':'Published',
    'dateUpdated':'Updated',
    'dateCreated':'Packaged',
    'rating':'Rating',
    'warnings':'Warnings',
    'numChapters':'Chapters',
    'numWords':'Words',
    'words_added':'Words Added', # logpage only
    'site':'Site',
    'publisher':'Publisher',
    'storyId':'Story ID',
    'authorId':'Author ID',
    'extratags':'Extra Tags',
    'title':'Title',
    'storyUrl':'Story URL',
    'sectionUrl':'Story URL Section',
    'description':'Summary',
    'author':'Author',
    'authorUrl':'Author URL',
    'formatname':'File Format',
    'formatext':'File Extension',
    'siteabbrev':'Site Abbrev',
    'version':'Downloader Version'
    }

formatsections = ['html','txt','epub','mobi']
othersections = ['defaults','overrides']

def get_valid_sections():
    sites = adapters.getConfigSections()
    sitesections = list(othersections)
    for section in sites:
        sitesections.append(section)
        # also allows [www.base_efiction] and [www.base_xenforoforum]. Not
        # likely to matter.
        if section.startswith('www.'):
            # add w/o www if has www
            sitesections.append(section[4:])
        else:
            # add w/ www if doesn't www
            sitesections.append('www.%s'%section)

    allowedsections = []
    allowedsections.extend(formatsections)

    for section in sitesections:
        allowedsections.append(section)
        for f in formatsections:
            allowedsections.append('%s:%s'%(section,f))
    return allowedsections

def get_valid_list_entries():
    return list(['category',
                 'genre',
                 'characters',
                 'ships',
                 'warnings',
                 'extratags',
                 'author',
                 'authorId',
                 'authorUrl',
                 'lastupdate',
                 ])

boollist=['true','false']
base_xenforo2_list=['base_xenforo2forum',
                   'forums.sufficientvelocity.com',
                   ]
base_xenforo_list=base_xenforo2_list+['base_xenforoforum',
                   'forums.spacebattles.com',
                   'forum.questionablequesting.com',
                   'www.alternatehistory.com',
                   ]
def get_valid_set_options():
    '''
    dict() of names of boolean options, but as a tuple with
    valid sites, valid formats and valid values (None==all)

    This is to further restrict keywords to certain sections and/or
    values.  get_valid_keywords() below is the list of allowed
    keywords.  Any keyword listed here must also be listed there.

    This is what's used by the code when you save personal.ini in
    plugin that stops and points out possible errors in keyword
    *values*.  It doesn't flag 'bad' keywords.  Note that it's
    separate from color highlighting and most keywords need to be
    added to both.
    '''

    valdict = {'collect_series':(None,None,boollist),
               'include_titlepage':(None,None,boollist),
               'include_tocpage':(None,None,boollist),
               'is_adult':(None,None,boollist),
               'keep_style_attr':(None,None,boollist),
               'keep_title_attr':(None,None,boollist),
               'make_firstimage_cover':(None,None,boollist),
               'never_make_cover':(None,None,boollist),
               'nook_img_fix':(None,None,boollist),
               'replace_br_with_p':(None,None,boollist),
               'replace_hr':(None,None,boollist),
               'sort_ships':(None,None,boollist),
               'strip_chapter_numbers':(None,None,boollist),
               'mark_new_chapters':(None,None,boollist+['latestonly']),
               'titlepage_use_table':(None,None,boollist),

               'use_ssl_unverified_context':(None,None,boollist),
               'continue_on_chapter_error':(None,None,boollist),
               'conditionals_use_lists':(None,None,boollist),

               'add_chapter_numbers':(None,None,boollist+['toconly']),

               'check_next_chapter':(['fanfiction.net'],None,boollist),
               'tweak_fg_sleep':(['fanfiction.net'],None,boollist),
               'skip_author_cover':(['fanfiction.net'],None,boollist),

               'fix_fimf_blockquotes':(['fimfiction.net'],None,boollist),
               'fail_on_password':(['fimfiction.net'],None,boollist),
               'keep_prequel_in_description':(['fimfiction.net'],None,boollist),
               'include_author_notes':(['fimfiction.net'],None,boollist),
               'do_update_hook':(['fimfiction.net',
                                  'archiveofourown.org'],None,boollist),
               'always_login':(['archiveofourown.org']+base_xenforo_list,None,boollist),
               'use_archived_author':(['archiveofourown.org'],None,boollist),
               'use_view_full_work':(['archiveofourown.org'],None,boollist),
               'remove_authorfootnotes_on_update':(['archiveofourown.org'],None,boollist),

               'force_login':(['phoenixsong.net'],None,boollist),
               'non_breaking_spaces':(['fictionmania.tv'],None,boollist),
               'universe_as_series':(['storiesonline.net','finestories.com'],None,boollist),
               'strip_text_links':(['bloodshedverse.com','asexstories.com'],None,boollist),
               'centeredcat_to_characters':(['tthfanfic.org'],None,boollist),
               'pairingcat_to_characters_ships':(['tthfanfic.org'],None,boollist),
               'romancecat_to_characters_ships':(['tthfanfic.org'],None,boollist),

               'use_meta_keywords':(['literotica.com'],None,boollist),
               'chapter_categories_use_all':(['literotica.com'],None,boollist),
               'clean_chapter_titles':(['literotica.com'],None,boollist),
               'description_in_chapter':(['literotica.com'],None,boollist),

               'inject_chapter_title':(['asianfanfics.com'],None,boollist),

               'auto_sub':(['asianfanfics.com'],None,boollist),

               # eFiction Base adapters allow bulk_load
               # kept forgetting to add them, so now it's automatic.
               'bulk_load':(adapters.get_bulk_load_sites(),
                            None,boollist),

               'include_logpage':(None,['epub'],boollist+['smart']),
               'logpage_at_end':(None,['epub'],boollist),

               'calibre_series_meta':(None,['epub'],boollist),

               'windows_eol':(None,['txt'],boollist),

               'include_images':(None,['epub','html'],boollist),
               'grayscale_images':(None,['epub','html'],boollist),
               'no_image_processing':(None,['epub','html'],boollist),
               'normalize_text_links':(None,['epub','html'],boollist),
               'internalize_text_links':(None,['epub','html'],boollist),

               'capitalize_forumtags':(base_xenforo_list,None,boollist),
               'minimum_threadmarks':(base_xenforo_list,None,None),
               'first_post_title':(base_xenforo_list,None,None),
               'always_include_first_post':(base_xenforo_list,None,boollist),
               'always_reload_first_chapter':(base_xenforo_list,None,boollist),
               'always_use_forumtags':(base_xenforo_list,None,boollist),
               'use_reader_mode':(base_xenforo_list,None,boollist),
               'author_avatar_cover':(base_xenforo_list,None,boollist),
               'remove_spoilers':(base_xenforo_list+['royalroad.com'],None,boollist),
               'legend_spoilers':(base_xenforo_list+['royalroad.com'],None,boollist),
               'apocrypha_to_omake':(base_xenforo_list,None,boollist),
               'replace_failed_smilies_with_alt_text':(base_xenforo_list,None,boollist),
               'use_threadmark_wordcounts':(base_xenforo_list,None,boollist),
               'always_include_first_post_chapters':(base_xenforo_list,None,boollist),
               'use_threadmarks_description':(base_xenforo2_list,None,boollist),
               'use_threadmarks_status':(base_xenforo2_list,None,boollist),
               'use_threadmarks_cover':(base_xenforo2_list,None,boollist),
               'fix_pseudo_html': (['webnovel.com'], None, boollist),
               'fix_excess_space': (['novelonlinefull.com', 'novelall.com'], ['epub', 'html'], boollist)
               }

    return dict(valdict)

def get_valid_scalar_entries():
    return list(['series',
                 'seriesUrl',
                 'language',
                 'status',
                 'datePublished',
                 'dateUpdated',
                 'dateCreated',
                 'rating',
                 'numChapters',
                 'numWords',
                 'words_added', # logpage only.
                 'site',
                 'publisher',
                 'storyId',
                 'title',
                 'titleHTML',
                 'storyUrl',
                 'sectionUrl',
                 'description',
                 'formatname',
                 'formatext',
                 'siteabbrev',
                 'version',
                 # internal stuff.
                 'authorHTML',
                 'seriesHTML',
                 'langcode',
                 'output_css',
                 'cover_image',
                 ])

def get_valid_entries():
    return get_valid_list_entries() + get_valid_scalar_entries()

# *known* keywords -- or rather regexps for them.
def get_valid_keywords():
    '''
    Among other things, this list is used by the color highlighting in
    personal.ini editing in plugin.  Note that it's separate from
    value checking and most keywords need to be added to both.
    '''
    return list(['(in|ex)clude_metadata_(pre|post)',
                 'add_chapter_numbers',
                 'add_genre_when_multi_category',
                 'adult_ratings',
                 'allow_unsafe_filename',
                 'always_overwrite',
                 'anthology_tags',
                 'anthology_title_pattern',
                 'background_color',
                 'bulk_load',
                 'chapter_end',
                 'chapter_start',
                 'chapter_title_strip_pattern',
                 'chapter_title_def_pattern',
                 'chapter_title_add_pattern',
                 'chapter_title_new_pattern',
                 'chapter_title_addnew_pattern',
                 'title_chapter_range_pattern',
                 'mark_new_chapters',
                 'check_next_chapter',
                 'skip_author_cover',
                 'collect_series',
                 'comma_entries',
                 'connect_timeout',
                 'convert_images_to',
                 'cover_content',
                 'cover_exclusion_regexp',
                 'custom_columns_settings',
                 'dateCreated_format',
                 'datePublished_format',
                 'dateUpdated_format',
                 'default_cover_image',
                 'description_limit',
                 'do_update_hook',
                 'use_archived_author',
                 'use_view_full_work',
                 'always_login',
                 'exclude_notes',
                 'remove_authorfootnotes_on_update',
                 'exclude_editor_signature',
                 'extra_logpage_entries',
                 'extra_subject_tags',
                 'extra_titlepage_entries',
                 'extra_valid_entries',
                 'extratags',
                 'extracategories',
                 'extragenres',
                 'extracharacters',
                 'extraships',
                 'extrawarnings',
                 'fail_on_password',
                 'file_end',
                 'file_start',
                 'fileformat',
                 'find_chapters',
                 'fix_fimf_blockquotes',
                 'keep_prequel_in_description',
                 'include_author_notes',
                 'force_login',
                 'generate_cover_settings',
                 'grayscale_images',
                 'image_max_size',
                 'include_images',
                 'include_logpage',
                 'logpage_at_end',
                 'calibre_series_meta',
                 'include_subject_tags',
                 'include_titlepage',
                 'include_tocpage',
                 'chardet_confidence_limit',
                 'is_adult',
                 'join_string_authorHTML',
                 'keep_style_attr',
                 'keep_title_attr',
                 'keep_html_attrs',
                 'replace_tags_with_spans',
                 'keep_empty_tags',
                 'keep_summary_html',
                 'logpage_end',
                 'logpage_entries',
                 'logpage_entry',
                 'logpage_start',
                 'logpage_update_end',
                 'logpage_update_start',
                 'make_directories',
                 'make_firstimage_cover',
                 'make_linkhtml_entries',
                 'max_fg_sleep',
                 'max_fg_sleep_at_downloads',
                 'min_fg_sleep',
                 'never_make_cover',
                 'no_image_processing',
                 'non_breaking_spaces',
                 'nook_img_fix',
                 'output_css',
                 'output_filename',
                 'output_filename_safepattern',
                 'password',
                 'post_process_cmd',
                 'rating_titles',
                 'remove_transparency',
                 'replace_br_with_p',
                 'replace_hr',
                 'replace_metadata',
                 'slow_down_sleep_time',
                 'sort_ships',
                 'sort_ships_splits',
                 'strip_chapter_numbers',
                 'strip_chapter_numeral',
                 'strip_text_links',
                 'centeredcat_to_characters',
                 'pairingcat_to_characters_ships',
                 'romancecat_to_characters_ships',
                 'use_meta_keywords',
                 'chapter_categories_use_all',
                 'clean_chapter_titles',
                 'conditionals_use_lists',
                 'description_in_chapter',
                 'inject_chapter_title',
                 'auto_sub',
                 'titlepage_end',
                 'titlepage_entries',
                 'titlepage_entry',
                 'titlepage_no_title_entry',
                 'titlepage_start',
                 'titlepage_use_table',
                 'titlepage_wide_entry',
                 'tocpage_end',
                 'tocpage_entry',
                 'tocpage_start',
                 'tweak_fg_sleep',
                 'universe_as_series',
                 'use_ssl_unverified_context',
                 'user_agent',
                 'username',
                 'website_encodings',
                 'wide_titlepage_entries',
                 'windows_eol',
                 'wrap_width',
                 'zip_filename',
                 'zip_output',
                 'capitalize_forumtags',
                 'continue_on_chapter_error',
                 'chapter_title_error_mark',
                 'minimum_threadmarks',
                 'first_post_title',
                 'always_include_first_post',
                 'always_reload_first_chapter',
                 'always_use_forumtags',
                 'use_reader_mode',
                 'author_avatar_cover',
                 'reader_posts_per_page',
                 'remove_spoilers',
                 'legend_spoilers',
                 'apocrypha_to_omake',
                 'skip_threadmarks_categories',
                 'normalize_text_links',
                 'internalize_text_links',
                 'replace_failed_smilies_with_alt_text',
                 'use_threadmark_wordcounts',
                 'always_include_first_post_chapters',
                 'use_threadmarks_description',
                 'use_threadmarks_status',
                 'use_threadmarks_cover',
                 'datethreadmark_format',
                 'fix_pseudo_html',
                 'fix_excess_space',
                 'ignore_chapter_url_list',
                 'max_zalgo',
                 ])

# *known* entry keywords -- or rather regexps for them.
def get_valid_entry_keywords():
    return list(['%s_(label|format)',
                 '(default_value|include_in|join_string|keep_in_order)_%s',])

# Moved here for test_config.
def make_generate_cover_settings(param):
    vlist = []
    for line in param.splitlines():
        if "=>" in line:
            try:
                (template,regexp,setting) = [ x.strip() for x in line.split("=>") ]
                re_compile(regexp,line)
                vlist.append((template,regexp,setting))
            except Exception as e:
                raise exceptions.PersonalIniFailed(e,line,param)

    return vlist


class Configuration(configparser.SafeConfigParser):

    def __init__(self, sections, fileform, lightweight=False):
        site = sections[-1] # first section is site DN.
        configparser.SafeConfigParser.__init__(self)

        self.lightweight = lightweight
        self.use_pagecache = False # default to false for old adapters.

        self.linenos=dict() # key by section or section,key -> lineno

        ## [injected] section has even less priority than [defaults]
        self.sectionslist = ['defaults','injected']

        ## add other sections (not including site DN) after defaults,
        ## but before site-specific.
        for section in sections[:-1]:
            self.addConfigSection(section)

        if site.startswith("www."):
            sitewith = site
            sitewithout = site.replace("www.","")
        else:
            sitewith = "www."+site
            sitewithout = site

        self.addConfigSection(sitewith)
        self.addConfigSection(sitewithout)

        if fileform:
            self.addConfigSection(fileform)
            ## add other sections:fileform (not including site DN)
            ## after fileform, but before site-specific:fileform.
            for section in sections[:-1]:
                self.addConfigSection(section+":"+fileform)
            self.addConfigSection(sitewith+":"+fileform)
            self.addConfigSection(sitewithout+":"+fileform)
        self.addConfigSection("overrides")

        self.listTypeEntries = get_valid_list_entries()

        self.validEntries = get_valid_entries()

        self.url_config_set = False

        self.override_sleep = None
        self.cookiejar = self.get_empty_cookiejar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookiejar),GZipProcessor())

        self.pagecache = self.get_empty_pagecache()
        self.save_cache_file = None
        self.save_cookiejar_file = None

    def section_url_names(self,domain,section_url_f):
        ## domain is passed as a method to limit the damage if/when an
        ## adapter screws up _section_url
        domain = domain.replace('www.','') ## let's not confuse the issue any more than it is.
        try:
            ## OrderDict (the default for ConfigParser) has to be
            ## reconstructed completely because removing and re-adding
            ## a section would mess up the order.
            ## assumes _dict and _sections from ConfigParser parent.
            self._sections = self._dict((section_url_f(k) if (domain in k and 'http' in k) else k, v) for k, v in six.viewitems(self._sections))
            # logger.debug(self._sections.keys())
        except Exception as e:
            logger.warn("Failed to perform section_url_names: %s"%e)

    def addUrlConfigSection(self,url):
        if not self.lightweight: # don't need when just checking for normalized URL.
            # replace if already set once.
            if self.url_config_set:
                self.sectionslist[self.sectionslist.index('overrides')+1]=url
            else:
                self.addConfigSection(url,'overrides')
                self.url_config_set=True

    def addConfigSection(self,section,before=None):
        if section not in self.sectionslist: # don't add if already present.
            if before is None:
                self.sectionslist.insert(0,section)
            else:
                ## because sectionslist is hi-pri first, lo-pri last,
                ## 'before' means after in the list.
                self.sectionslist.insert(self.sectionslist.index(before)+1,section)

    def isListType(self,key):
        return key in self.listTypeEntries or self.hasConfig("include_in_"+key)

    def isValidMetaEntry(self, key):
        return key in self.getValidMetaList()

    def getValidMetaList(self):
        return self.validEntries + self.getConfigList("extra_valid_entries")

    # used by adapters & writers, non-convention naming style
    def hasConfig(self, key):
        return self.has_config(self.sectionslist, key)

    def has_config(self, sections, key):
        for section in sections:
            try:
                self.get(section,key)
                #print("found %s in section [%s]"%(key,section))
                return True
            except:
                try:
                    self.get(section,key+"_filelist")
                    #print("found %s_filelist in section [%s]"%(key,section))
                    return True
                except:
                    try:
                        self.get(section,"add_to_"+key)
                        #print("found add_to_%s in section [%s]"%(key,section))
                        return True
                    except:
                        pass

        return False

    # used by adapters & writers, non-convention naming style
    def getConfig(self, key, default=""):
        return self.get_config(self.sectionslist,key,default)

    def get_config(self, sections, key, default=""):
        val = default

        val_files = []
        if not key.endswith("_filelist"):
            ## <key>_filelist overrides <key>, but add_to_<key> is
            ## still used.  By using self.get_config_list(),
            ## add_to_<key>_filelist also works. (But not
            ## <key>_filelist_filelist--that way lies madness--and
            ## infinite recursion.)  self.get_config_list() also does
            ## the list split & clean up.
            val_files = self.get_config_list(sections, key+"_filelist")

        file_val = False
        if val_files:
            val = ''
            for v in val_files:
                try:
                    val = val + self._fetchUrl(v)
                    file_val = True
                except:
                    pass
            if not file_val:
                logger.warn("All files for (%s) failed!  Using (%s) instead. Filelist: (%s)"%
                            (key+"_filelist",key,val_files))

        if not file_val:
            for section in sections:
                try:
                    val = self.get(section,key)
                    if val and val.lower() == "false":
                        val = False
                    #print("getConfig(%s)=[%s]%s" % (key,section,val))
                    break
                except (configparser.NoOptionError, configparser.NoSectionError) as e:
                    pass

        for section in sections[::-1]:
            # 'martian smiley' [::-1] reverses list by slicing whole list with -1 step.
            try:
                val = val + self.get(section,"add_to_"+key)
                #print("getConfig(add_to_%s)=[%s]%s" % (key,section,val))
            except (configparser.NoOptionError, configparser.NoSectionError) as e:
                pass

        return val

    # split and strip each.
    def get_config_list(self, sections, key, default=[]):
        vlist = re.split(r'(?<!\\),',self.get_config(sections,key)) # don't split on \,
        vlist = [x for x in [ v.strip().replace('\,',',') for v in vlist ] if x !='']
        #print("vlist("+key+"):"+unicode(vlist))
        if not vlist:
            return default
        else:
            return vlist

    # used by adapters & writers, non-convention naming style
    def getConfigList(self, key, default=[]):
        return self.get_config_list(self.sectionslist, key, default)

    # Moved here for test_config.
    def get_generate_cover_settings(self):
        return make_generate_cover_settings(self.getConfig('generate_cover_settings'))

    def get_lineno(self,section,key=None):
        if key:
            return self.linenos.get(section+','+key,None)
        else:
            return self.linenos.get(section,None)

    ## Copied from Python 2.7 library so as to make read utf8.
    def read(self, filenames):
        """Read and parse a filename or a list of filenames.
        Files that cannot be opened are silently ignored; this is
        designed so that you can specify a list of potential
        configuration file locations (e.g. current directory, user's
        home directory, systemwide directory), and all existing
        configuration files in the list will be read.  A single
        filename may also be given.
        Return list of successfully read files.
        """
        if isinstance(filenames, basestring):
            filenames = [filenames]
        read_ok = []
        for filename in filenames:
            try:
                fp = codecs.open(filename,encoding='utf-8')
            except IOError:
                continue
            self._read(fp, filename)
            fp.close()
            read_ok.append(filename)
        return read_ok

    ## Copied from Python 2.7 library so as to make it save linenos too.
    #
    # Regular expressions for parsing section headers and options.
    #
    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                        self.linenos[sectname]=lineno
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    if not e:
                        e = ParsingError(fpname)
                    e.append(lineno, u'(Line outside section) '+line)
                    #raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self.OPTCRE.match(line) # OPTCRE instead of
                                                 # _optcre so it works
                                                 # with python 2.6
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos-1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                        self.linenos[cursect['__name__']+','+optname]=lineno
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, line)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

    def test_config(self):
        errors=[]

        ## too complicated right now to enforce
        ## get_valid_set_options() warnings on teststory and
        ## [storyUrl] sections.
        allow_all_sections_re = re.compile(r'^(teststory:(defaults|[0-9]+)|https?://.*)$')
        allowedsections = get_valid_sections()

        clude_metadata_re = re.compile(r'(add_to_)?(in|ex)clude_metadata_(pre|post)$')

        replace_metadata_re = re.compile(r'(add_to_)?replace_metadata$')
        from .story import set_in_ex_clude, make_replacements

        custom_columns_settings_re = re.compile(r'(add_to_)?custom_columns_settings$')

        generate_cover_settings_re = re.compile(r'(add_to_)?generate_cover_settings$')

        valdict = get_valid_set_options()

        for section in self.sections():
            allow_all_section = allow_all_sections_re.match(section)
            if section not in allowedsections and not allow_all_section:
                errors.append((self.get_lineno(section),"Bad Section Name: [%s]"%section))
            else:
                sitename = section.replace('www.','')
                if ':' in sitename:
                    formatname = sitename[sitename.index(':')+1:]
                    sitename = sitename[:sitename.index(':')]
                elif sitename in formatsections:
                    formatname = sitename
                    sitename = None
                elif sitename in othersections:
                    formatname = None
                    sitename = None

                ## check each keyword in section.  Due to precedence
                ## order of sections, it's possible for bad lines to
                ## never be used.
                for keyword,value in self.items(section):
                    try:

                        ## check regex bearing keywords first.  Each
                        ## will raise exceptions if flawed.
                        if clude_metadata_re.match(keyword):
                            set_in_ex_clude(value)

                        if replace_metadata_re.match(keyword):
                            make_replacements(value)

                        if generate_cover_settings_re.match(keyword):
                            make_generate_cover_settings(value)

                        # if custom_columns_settings_re.match(keyword):
                        #custom_columns_settings:
                        # cliches=>#acolumn
                        # themes=>#bcolumn,a
                        # timeline=>#ccolumn,n
                        # "FanFiction"=>#collection

                        if not allow_all_section:
                            def make_sections(x):
                                return '['+'], ['.join(x)+']'
                            if keyword in valdict:
                                (valsites,valformats,vals)=valdict[keyword]
                                if valsites != None and sitename != None and sitename not in valsites:
                                    errors.append((self.get_lineno(section,keyword),"%s not valid in section [%s] -- only valid in %s sections."%(keyword,section,make_sections(valsites))))
                                if valformats != None and formatname != None and formatname not in valformats:
                                    errors.append((self.get_lineno(section,keyword),"%s not valid in section [%s] -- only valid in %s sections."%(keyword,section,make_sections(valformats))))
                                if vals != None and value not in vals:
                                    errors.append((self.get_lineno(section,keyword),"%s not a valid value for %s"%(value,keyword)))

                        ## skipping output_filename_safepattern
                        ## regex--not used with plugin and this isn't
                        ## used with CLI/web yet.

                    except Exception as e:
                        errors.append((self.get_lineno(section,keyword),"Error:%s in (%s:%s)"%(e,keyword,value)))

        return errors

#### methods for fetching.  Moved here from base_adapter when
#### *_filelist feature was added.

    @staticmethod
    def get_empty_cookiejar():
        return cl.LWPCookieJar()

    @staticmethod
    def get_empty_pagecache():
        return {}

    def get_cookiejar(self):
        return self.cookiejar

    def set_cookiejar(self,cj,save_cookiejar_file=None):
        self.cookiejar = cj
        self.save_cookiejar_file = save_cookiejar_file
        saveheaders = self.opener.addheaders
        self.opener = build_opener(HTTPCookieProcessor(self.cookiejar),GZipProcessor())
        self.opener.addheaders = saveheaders

    def load_cookiejar(self,filename):
        '''
        Needs to be called after adapter create, but before any fetchs
        are done.  Takes file *name*.
        '''
        self.get_cookiejar().load(filename, ignore_discard=True, ignore_expires=True)

    def get_pagecache(self):
        return self.pagecache

    def set_pagecache(self,d,save_cache_file=None):
        self.save_cache_file = save_cache_file
        self.pagecache=d

    def _get_cachekey(self, url, parameters=None, headers=None):
        keylist=[url]
        if parameters != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(parameters.items())))
        if headers != None:
            keylist.append('&'.join('{0}={1}'.format(key, val) for key, val in sorted(headers.items())))
        return unicode('?'.join(keylist))

    def _has_cachekey(self,cachekey):
        return self.use_pagecache and cachekey in self.get_pagecache()

    def _get_from_pagecache(self,cachekey):
        if self.use_pagecache:
            return self.get_pagecache().get(cachekey)
        else:
            return None

    def _set_to_pagecache(self,cachekey,data,redirectedurl):
        if self.use_pagecache:
            self.get_pagecache()[cachekey] = (data,ensure_text(redirectedurl))
            if self.save_cache_file:
                with open(self.save_cache_file,'wb') as jout:
                    pickle.dump(self.get_pagecache(),jout,protocol=2)
            if self.save_cookiejar_file:
                self.get_cookiejar().save(self.save_cookiejar_file)

## website encoding(s)--in theory, each website reports the character
## encoding they use for each page.  In practice, some sites report it
## incorrectly.  Each adapter has a default list, usually "utf8,
## Windows-1252" or "Windows-1252, utf8".  The special value 'auto'
## will call chardet and use the encoding it reports if it has +90%
## confidence.  'auto' is not reliable.  1252 is a superset of
## iso-8859-1.  Most sites that claim to be iso-8859-1 (and some that
## claim to be utf8) are really windows-1252.
    def _decode(self,data):
        if not hasattr(data,'decode'):
            ## py3 str() from pickle doesn't have .decode and is
            ## already decoded.
            return data
        decode = self.getConfigList('website_encodings',
                                    default=["utf8",
                                             "Windows-1252",
                                             "iso-8859-1"])
        for code in decode:
            try:
                logger.debug("Encoding:%s"%code)
                errors=None
                if ':' in code:
                    (code,errors)=code.split(':')
                if code == "auto":
                    if not chardet:
                        logger.info("chardet not available, skipping 'auto' encoding")
                        continue
                    detected = chardet.detect(data)
                    #print(detected)
                    if detected['confidence'] > float(self.getConfig("chardet_confidence_limit",0.9)):
                        logger.debug("using chardet detected encoding:%s(%s)"%(detected['encoding'],detected['confidence']))
                        code=detected['encoding']
                    else:
                        logger.debug("chardet confidence too low:%s(%s)"%(detected['encoding'],detected['confidence']))
                        continue
                if errors == 'ignore': # only allow ignore.
                    return data.decode(code,errors='ignore')
                else:
                    return data.decode(code)
            except Exception as e:
                logger.debug("code failed:"+code)
                logger.debug(e)
                pass
        logger.info("Could not decode story, tried:%s Stripping non-ASCII."%decode)
        return "".join([x for x in data if ord(x) < 128])

    def _progressbar(self):
        if self.getConfig('progressbar'):
            sys.stdout.write('.')
            sys.stdout.flush()

    def _do_reduce_zalgo(self,data):
        max_zalgo = int(self.getConfig('max_zalgo',-1))
        if max_zalgo > -1:
            logger.debug("Applying max_zalgo:%s"%max_zalgo)
            return reduce_zalgo(data,max_zalgo)
        else:
            return data

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
        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        cachekey=self._get_cachekey(url, parameters, headers)
        if usecache and self._has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("#####################################\npagecache(POST) HIT: %s"%safe_url(cachekey))
            data,redirecturl = self._get_from_pagecache(cachekey)
            return data

        logger.debug("#####################################\npagecache(POST) MISS: %s"%safe_url(cachekey))
        if not cachekey.startswith('file:'): # don't sleep for file: URLs.
            self.do_sleep(extrasleep)

        ## Request assumes POST when data!=None.  Also assumes data
        ## is application/x-www-form-urlencoded.
        if 'Content-type' not in headers:
            headers['Content-type']='application/x-www-form-urlencoded'
        if 'Accept' not in headers:
            headers['Accept']="text/html,*/*"

        if "xf2test" in url:
            import base64
            base64string = base64.encodestring(b"xf2demo2019:dBfbyHVvRCsYtLg846r3").replace(b'\n', b'')
            headers['Authorization']=b"Basic %s" % base64string

        req = Request(url,
                      data=ensure_binary(urlencode(parameters)),
                      headers=headers)

        ## Specific UA because too many sites are blocking the default python UA.
        self.opener.addheaders = [('User-Agent', self.getConfig('user_agent')),
                                  ('X-Clacks-Overhead','GNU Terry Pratchett')]

        data = self._do_reduce_zalgo(self._decode(self.opener.open(req,None,float(self.getConfig('connect_timeout',30.0))).read()))
        self._progressbar()
        ## postURL saves data to the pagecache *after* _decode() while
        ## fetchRaw saves it *before* _decode()--because raw.
        self._set_to_pagecache(cachekey,data,url)
        return data

    def _fetchUrl(self, url,
                  parameters=None,
                  usecache=True,
                  extrasleep=None):
        return self._fetchUrlOpened(url,
                                    parameters,
                                    usecache,
                                    extrasleep)[0]

    def _fetchUrlRawOpened(self, url,
                           parameters=None,
                           extrasleep=None,
                           usecache=True,
                           referer=None):
        '''
        When should cache be cleared or not used? logins...

        extrasleep is primarily for ffnet adapter which has extra
        sleeps.  Passed into fetchs so it can be bypassed when
        cache hits.
        '''
        if self.getConfig('force_https'): ## For developer testing only.
            url = url.replace("http:","https:")
        cachekey=self._get_cachekey(url, parameters)
        if usecache and self._has_cachekey(cachekey) and not cachekey.startswith('file:'):
            logger.debug("#####################################\npagecache(GET) HIT: %s"%safe_url(cachekey))
            data,redirecturl = self._get_from_pagecache(cachekey)
            class FakeOpened:
                def __init__(self,data,url):
                    self.data=data
                    self.url=url
                def geturl(self): return self.url
                def read(self): return self.data
            return (data,FakeOpened(data,redirecturl))

        logger.debug("#####################################\npagecache(GET) MISS: %s"%safe_url(cachekey))
        # print(self.get_pagecache().keys())
        if not cachekey.startswith('file:'): # don't sleep for file: URLs.
            self.do_sleep(extrasleep)

        ## Specific UA because too many sites are blocking the default python UA.
        headers = [('User-Agent', self.getConfig('user_agent')),
                   ## starslibrary.net throws a "HTTP Error 403: Bad
                   ## Behavior" over the X-Clacks-Overhead.  Which
                   ## both against standard and rather a dick-move.
                   #('X-Clacks-Overhead','GNU Terry Pratchett'),
                   ]
        if referer:
            ## hpfanficarchive.com complains about Referer: None.
            ## Could have defaulted to "" instead, but this way it's
            ## not present at all
            headers.append(('Referer',referer))

        if "xf2test" in url:
            import base64
            base64string = base64.encodestring(b"xf2demo2019:dBfbyHVvRCsYtLg846r3").replace(b'\n', b'')
            headers.append(('Authorization', b"Basic %s" % base64string))

        self.opener.addheaders = headers

        if parameters != None:
            opened = self.opener.open(url.replace(' ','%20'),
                                      ensure_binary(urlencode(parameters)),
                                      float(self.getConfig('connect_timeout',30.0)))
        else:
            opened = self.opener.open(url.replace(' ','%20'),
                                      None,
                                      float(self.getConfig('connect_timeout',30.0)))
        self._progressbar()
        data = opened.read()
        ## postURL saves data to the pagecache *after* _decode() while
        ## fetchRaw saves it *before* _decode()--because raw.
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

    # parameters is a dict()
    def _fetchUrlOpened(self, url,
                        parameters=None,
                        usecache=True,
                        extrasleep=None,
                        referer=None):

        excpt=None
        if url.startswith("file://"):
            # only one try for file:s.
            sleeptimes = [0]
        else:
            sleeptimes = [0, 0.5, 4, 9]
        for sleeptime in sleeptimes:
            time.sleep(sleeptime)
            try:
                (data,opened)=self._fetchUrlRawOpened(url,
                                                      parameters=parameters,
                                                      usecache=usecache,
                                                      extrasleep=extrasleep,
                                                      referer=referer)
                return (self._do_reduce_zalgo(self._decode(data)),opened)
            except HTTPError as he:
                excpt=he
                if he.code in (403,404,410):
                    logger.debug("Caught an exception reading URL: %s  Exception %s."%(unicode(safe_url(url)),unicode(he)))
                    break # break out on 404
            except Exception as e:
                excpt=e
                logger.debug("Caught an exception reading URL: %s sleeptime(%s) Exception %s."%(unicode(safe_url(url)),sleeptime,unicode(e)))
                raise

        logger.debug("Giving up on %s" %safe_url(url))
        logger.debug(excpt, exc_info=True)
        raise(excpt)


# extended by adapter, writer and story for ease of calling configuration.
class Configurable(object):

    def __init__(self, configuration):
        self.configuration = configuration

        ## use_pagecache() is on adapters--not all have been updated
        ## to deal with caching correctly
        if hasattr(self, 'use_pagecache'):
            self.configuration.use_pagecache = self.use_pagecache()

    def section_url_names(self,domain,section_url_f):
        return self.configuration.section_url_names(domain,section_url_f)

    def get_configuration(self):
        return self.configuration

    def is_lightweight(self):
        return self.configuration.lightweight

    def addUrlConfigSection(self,url):
        self.configuration.addUrlConfigSection(url)

    def isListType(self,key):
        return self.configuration.isListType(key)

    def isValidMetaEntry(self, key):
        return self.configuration.isValidMetaEntry(key)

    def getValidMetaList(self):
        return self.configuration.getValidMetaList()

    def hasConfig(self, key):
        return self.configuration.hasConfig(key)

    def has_config(self, sections, key):
        return self.configuration.has_config(sections, key)

    def getConfig(self, key, default=""):
        return self.configuration.getConfig(key,default)

    def get_config(self, sections, key, default=""):
        return self.configuration.get_config(sections,key,default)

    def getConfigList(self, key, default=[]):
        return self.configuration.getConfigList(key,default)

    def get_config_list(self, sections, key):
        return self.configuration.get_config_list(sections,key)

    def get_label(self, entry):
        if self.hasConfig(entry+"_label"):
            label=self.getConfig(entry+"_label")
        elif entry in titleLabels:
            label=titleLabels[entry]
        else:
            label=entry.title()
        return label

    def do_sleep(self,extrasleep=None):
        return self.configuration.do_sleep(extrasleep)

    def set_decode(self,decode):
        self.configuration.decode = decode

    def _postUrl(self, url,
                 parameters={},
                 headers={},
                 extrasleep=None,
                 usecache=True):
        return self.configuration._postUrl(url,
                                           parameters,
                                           headers,
                                           extrasleep,
                                           usecache)

    def _fetchUrlRawOpened(self, url,
                           parameters=None,
                           extrasleep=None,
                           usecache=True,
                           referer=None):
        return self.configuration._fetchUrlRawOpened(url,
                                                     parameters,
                                                     extrasleep,
                                                     usecache,
                                                     referer=referer)

    def _fetchUrlOpened(self, url,
                        parameters=None,
                        usecache=True,
                        extrasleep=None,
                        referer=None):
        return self.configuration._fetchUrlOpened(url,
                                                  parameters,
                                                  usecache,
                                                  extrasleep,
                                                  referer=referer)

    def _fetchUrl(self, url,
                  parameters=None,
                  usecache=True,
                  extrasleep=None,
                  referer=None):
        return self._fetchUrlOpened(url,
                                    parameters,
                                    usecache,
                                    extrasleep,
                                    referer=referer)[0]
    def _fetchUrlRaw(self, url,
                     parameters=None,
                     extrasleep=None,
                     usecache=True,
                     referer=None):
        return self._fetchUrlRawOpened(url,
                                       parameters,
                                       extrasleep,
                                       usecache,
                                       referer=referer)[0]


# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(password|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)
