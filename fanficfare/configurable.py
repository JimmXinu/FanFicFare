# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2021 FanFicFare team
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
import sys
import re
import codecs

# py2 vs py3 transition
from . import six
from .six.moves import configparser
from .six.moves.configparser import DEFAULTSECT, ParsingError
if six.PY2:
    ConfigParser = configparser.SafeConfigParser
else: # PY3
    ConfigParser = configparser.ConfigParser

if not hasattr(ConfigParser, 'read_file'):
    # read_file added in py3.2, readfp removed in py3.12
    ConfigParser.read_file = ConfigParser.readfp

from .six import string_types as basestring

import logging
logger = logging.getLogger(__name__)

from . import exceptions
from . import fetchers
from .fetchers import fetcher_nsapa_proxy
from .fetchers import fetcher_flaresolverr_proxy

## has to be up here for brotli-dict to load correctly.
from .browsercache import BrowserCache

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


# Work around for fact that py3 apparently doesn't allow/ignore
# recursive imports like py2 does.
try:
    from . import adapters
except ImportError:
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
                   'forums.spacebattles.com',
                   'www.alternatehistory.com',
                   ]
base_xenforo_list=base_xenforo2_list+['base_xenforoforum',
                   'forum.questionablequesting.com',
                   ]
## base_otw_adapter sites
otw_list=['archiveofourown.org',
          'squidgeworld.org',
          'www.adastrafanfic.com',
          'www.cfaarchive.org',
          'superlove.sayitditto.net',
          ]
wpc_list=['storiesonline.net',
          'finestories.com',
          'storyroom.com',
          'scifistories.com',
          ]
ffnet_list=[
    'fanfiction.net',
    'fictionpress.com',
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
               'include_tocpage':(None,None,boollist+['always']),
               'is_adult':(None,None,boollist),
               'keep_style_attr':(None,None,boollist),
               'keep_title_attr':(None,None,boollist),
               'make_firstimage_cover':(None,None,boollist),
               'use_old_cover':(None,None,boollist),
               'never_make_cover':(None,None,boollist),
               'nook_img_fix':(None,None,boollist),
               'replace_br_with_p':(None,None,boollist),
               'replace_hr':(None,None,boollist),
               'remove_empty_p':(None,None,boollist),
               'sort_ships':(None,None,boollist),
               'strip_chapter_numbers':(None,None,boollist),
               'remove_class_chapter':(None,None,boollist),
               'mark_new_chapters':(None,None,boollist+['latestonly']),
               'titlepage_use_table':(None,None,boollist),
               'decode_emails':(None,None,boollist),

               'use_ssl_unverified_context':(None,None,boollist),
               'use_ssl_default_seclevelone':(None,None,boollist),
               'use_cloudscraper':(None,None,boollist),
               'use_basic_cache':(None,None,boollist),
               'use_nsapa_proxy':(None,None,boollist),
               'use_flaresolverr_proxy':(None,None,boollist+['withimages','directimages']),
               'use_flaresolverr_session':(None,None,boollist),

               ## currently, browser_cache_path is assumed to be
               ## shared and only ffnet uses it so far
               'browser_cache_path':(['defaults'],None,None),
               'use_browser_cache':(None,None,boollist+['directimages']),
               'use_browser_cache_only':(None,None,boollist),
               'open_pages_in_browser':(None,None,boollist),

               'continue_on_chapter_error':(None,None,boollist),
               'conditionals_use_lists':(None,None,boollist),
               'dedup_chapter_list':(None,None,boollist),

               'add_chapter_numbers':(None,None,boollist+['toconly']),

               'check_next_chapter':(ffnet_list,None,boollist),
               'meta_from_last_chapter':(ffnet_list,None,boollist),
               'tweak_fg_sleep':(None,None,boollist),
               'skip_author_cover':(ffnet_list,None,boollist),
               'try_shortened_title_urls':(['fanfiction.net'],None,boollist),

               'fix_fimf_blockquotes':(['fimfiction.net'],None,boollist),
               'keep_prequel_in_description':(['fimfiction.net'],None,boollist),
               'scrape_bookshelf':(['fimfiction.net'],None,boollist+['legacy']),
               'include_author_notes':(['fimfiction.net','readonlymind.com','royalroad.com','syosetu.com'],None,boollist),
               'do_update_hook':(otw_list,None,boollist),
               'always_login':(['syosetu.com','fimfiction.net','inkbunny.net']+otw_list+base_xenforo_list+wpc_list,None,boollist),
               'use_archived_author':(otw_list,None,boollist),
               'use_view_full_work':(otw_list+['fanfics.me'],None,boollist),
               'use_workskin':(otw_list,None,boollist),
               'remove_authorfootnotes_on_update':(otw_list,None,boollist),
               'use_archive_transformativeworks_org':(['archiveofourown.org'],None,boollist),
               'use_archiveofourown_gay':(['archiveofourown.org'],None,boollist),

               'non_breaking_spaces':(['fictionmania.tv'],None,boollist),
               'download_text_version':(['fictionmania.tv'],None,boollist),
               'universe_as_series':(wpc_list,None,boollist),
               'strip_text_links':(['bloodshedverse.com','asexstories.com'],None,boollist),
               'centeredcat_to_characters':(['tthfanfic.org'],None,boollist),
               'pairingcat_to_characters_ships':(['tthfanfic.org'],None,boollist),
               'romancecat_to_characters_ships':(['tthfanfic.org'],None,boollist),

               'use_meta_keywords':(['literotica.com'],None,boollist),
               'chapter_categories_use_all':(['literotica.com'],None,boollist),
               'clean_chapter_titles':(['literotica.com'],None,boollist),
               'description_in_chapter':(['literotica.com'],None,boollist),
               'fetch_stories_from_api':(['literotica.com'],None,boollist),
               'order_chapters_by_date':(['literotica.com'],None,boollist),

               'inject_chapter_title':(['asianfanfics.com']+wpc_list,None,boollist),
               'inject_chapter_image':(['asianfanfics.com'],None,boollist),
               'append_datepublished_to_storyurl':(wpc_list,None,boollist),

               'auto_sub':(['asianfanfics.com'],None,boollist),

               # eFiction Base adapters allow bulk_load
               # kept forgetting to add them, so now it's automatic.
               'bulk_load':(adapters.get_bulk_load_sites(),
                            None,boollist),

               'include_logpage':(None,['epub'],boollist+['smart']),
               'logpage_at_end':(None,['epub'],boollist),

               'calibre_series_meta':(None,['epub'],boollist),
               'force_update_epub_always':(None,['epub'],boollist),

               'windows_eol':(None,['txt'],boollist),

               'include_images':(None,['epub','html'],boollist+['coveronly']),
               'jpg_quality':(None,['epub','html'],None),
               'additional_images':(None,['epub','html'],None),
               'grayscale_images':(None,['epub','html'],boollist),
               'no_image_processing':(None,['epub','html'],boollist),
               'dedup_img_files':(None,['epub','html'],boollist),
               'convert_inline_images':(None,['epub','html'],boollist),
               'fix_relative_text_links':(None,['epub','html'],boollist),
               'normalize_text_links':(None,['epub','html'],boollist),
               'internalize_text_links':(None,['epub','html'],boollist),
               'remove_class_chapter':(None,['epub','html'],boollist),

               'capitalize_forumtags':(base_xenforo_list,None,boollist),
               'minimum_threadmarks':(base_xenforo_list,None,None),
               'first_post_title':(base_xenforo_list,None,None),
               'always_include_first_post':(base_xenforo_list,None,boollist),
               'always_reload_first_chapter':(base_xenforo_list,None,boollist),
               'always_use_forumtags':(base_xenforo_list,None,boollist),
               'use_reader_mode':(base_xenforo_list,None,boollist),
               'author_avatar_cover':(base_xenforo_list,None,boollist),
               'remove_spoilers':(base_xenforo_list+['royalroad.com'],None,boollist),
               'legend_spoilers':(base_xenforo_list+['royalroad.com', 'fiction.live'],None,boollist),
               'details_spoilers':(base_xenforo_list,None,boollist),
               'apocrypha_to_omake':(base_xenforo_list,None,boollist),
               'replace_failed_smilies_with_alt_text':(base_xenforo_list,None,boollist),
               'use_threadmark_wordcounts':(base_xenforo_list,None,boollist),
               'always_include_first_post_chapters':(base_xenforo_list,None,boollist),
               'order_threadmarks_by_date':(base_xenforo_list,None,boollist),
               'reveal_invisible_text':(base_xenforo_list,None,boollist),
               'use_threadmarks_description':(base_xenforo2_list,None,boollist),
               'use_threadmarks_status':(base_xenforo2_list,None,boollist),
               'use_threadmarks_cover':(base_xenforo2_list,None,boollist),
               'skip_sticky_first_posts':(base_xenforo2_list,None,boollist),
               'include_dice_rolls':(base_xenforo2_list,None,boollist+['svg']),
               'include_chapter_banner_images':(['wattpad.com'],None,boollist),
               'dateUpdated_method':(['wattpad.com'],None,['modifyDate', 'lastPublishedPart']),
               'fix_excess_space': (['novelonlinefull.com', 'novelall.com'], ['epub', 'html'], boollist),
               'dedup_order_chapter_list': (['wuxiaworld.xyz'], None, boollist),
               'show_nsfw_cover_images': (['fiction.live'], None, boollist),
               'show_timestamps': (['fiction.live'], None, boollist),
               'prepend_section_titles': (['syosetu.com','kakuyomu.jp'], None, boollist+['firstepisode']),
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
                 'newforanthology' # internal for plugin anthologies
                                   # to mark chapters (new) in new
                                   # stories
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
                 'add_category_when_multi_category',
                 'adult_ratings',
                 'allow_unsafe_filename',
                 'always_overwrite',
                 'anthology_tags',
                 'anthology_title_pattern',
                 'anthology_merge_keepsingletocs',
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
                 'meta_from_last_chapter',
                 'skip_author_cover',
                 'try_shortened_title_urls',
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
                 'force_cover_image',
                 'force_img_self_referer_regexp',
                 'description_limit',
                 'do_update_hook',
                 'use_archived_author',
                 'use_view_full_work',
                 'use_workskin',
                 'always_login',
                 'exclude_notes',
                 'remove_authorfootnotes_on_update',
                 'use_archive_transformativeworks_org',
                 'use_archiveofourown_gay',
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
                 'scrape_bookshelf',
                 'include_author_notes',
                 'force_login',
                 'generate_cover_settings',
                 'grayscale_images',
                 'image_max_size',
                 'include_images',
                 'jpg_quality',
                 'additional_images',
                 'include_logpage',
                 'logpage_at_end',
                 'calibre_series_meta',
                 'force_update_epub_always',
                 'include_subject_tags',
                 'include_titlepage',
                 'include_tocpage',
                 'chardet_confidence_limit',
                 'is_adult',
                 'join_string_authorHTML',
                 'keep_style_attr',
                 'keep_title_attr',
                 'keep_html_attrs',
                 'remove_class_chapter',
                 'replace_tags_with_spans',
                 'keep_empty_tags',
                 'remove_tags',
                 'keep_summary_html',
                 'logpage_end',
                 'logpage_entries',
                 'logpage_entry',
                 'logpage_start',
                 'logpage_update_end',
                 'logpage_update_start',
                 'make_directories',
                 'make_firstimage_cover',
                 'use_old_cover',
                 'make_linkhtml_entries',
                 'max_fg_sleep',
                 'max_fg_sleep_at_downloads',
                 'min_fg_sleep',
                 'never_make_cover',
                 'cover_min_size',
                 'no_image_processing',
                 'no_image_processing_regexp',
                 'dedup_img_files',
                 'convert_inline_images',
                 'non_breaking_spaces',
                 'download_text_version',
                 'nook_img_fix',
                 'output_css',
                 'output_filename',
                 'output_filename_safepattern',
                 'password',
                 'post_process_cmd',
                 'rating_titles',
                 'remove_transparency',
                 'replace_br_with_p',
                 'replace_chapter_text',
                 'replace_hr',
                 'remove_empty_p',
                 'replace_xbr_with_hr',
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
                 'order_chapters_by_date',
                 'fetch_stories_from_api',
                 'inject_chapter_title',
                 'inject_chapter_image',
                 'append_datepublished_to_storyurl',
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
                 'use_ssl_default_seclevelone',
                 'http_proxy',
                 'https_proxy',
                 'use_cloudscraper',
                 'use_basic_cache',
                 'use_browser_cache',
                 'use_browser_cache_only',
                 'open_pages_in_browser',
                 'use_nsapa_proxy',
                 'nsapa_proxy_address',
                 'nsapa_proxy_port',
                 'use_flaresolverr_proxy',
                 'flaresolverr_proxy_address',
                 'flaresolverr_proxy_port',
                 'flaresolverr_proxy_protocol',
                 'flaresolverr_proxy_timeout',
                 'use_flaresolverr_session',
                 'flaresolverr_session',
                 'browser_cache_path',
                 'browser_cache_age_limit',
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
                 'continue_on_chapter_error_try_limit',
                 'minimum_threadmarks',
                 'first_post_title',
                 'always_include_first_post',
                 'always_reload_first_chapter',
                 'always_use_forumtags',
                 'use_reader_mode',
                 'author_avatar_cover',
                 'reader_posts_per_page',
                 'threadmarks_per_page',
                 'remove_spoilers',
                 'legend_spoilers',
                 'details_spoilers',
                 'apocrypha_to_omake',
                 'skip_threadmarks_categories',
                 'fix_relative_text_links',
                 'normalize_text_links',
                 'internalize_text_links',
                 'replace_failed_smilies_with_alt_text',
                 'use_threadmark_wordcounts',
                 'always_include_first_post_chapters',
                 'threadmark_category_order',
                 'order_threadmarks_by_date',
                 'order_threadmarks_by_date_categories',
                 'reveal_invisible_text',
                 'use_threadmarks_description',
                 'use_threadmarks_status',
                 'use_threadmarks_cover',
                 'skip_sticky_first_posts',
                 'include_dice_rolls',
                 'include_chapter_banner_images',
                 'dateUpdated_method',
                 'datethreadmark_format',
                 'fix_pseudo_html',
                 'fix_excess_space',
                 'dedup_order_chapter_list',
                 'ignore_chapter_url_list',
                 'dedup_chapter_list',
                 'show_timestamps',
                 'show_nsfw_cover_images',
                 'show_spoiler_tags',
                 'max_zalgo',
                 'decode_emails',
                 'epub_version',
                 'prepend_section_titles',
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


class Configuration(ConfigParser):

    def __init__(self, sections, fileform, lightweight=False,
                 basic_cache=None, browser_cache=None):
        self.site = sections[-1] # first section is site DN.
        logger.debug("config site:%s"%self.site)
        ConfigParser.__init__(self)

        self.fetcher = None # the network layer for getting pages the
        self.sleeper = None
        # caching layer for getting pages, create one if not given.
        self.basic_cache = basic_cache or fetchers.BasicCache()
        # don't create a browser cache by default.
        self.browser_cache = browser_cache
        self.filelist_fetcher = None # used for _filelist

        self.lightweight = lightweight

        self.linenos=dict() # key by section or section,key -> lineno

        ## [injected] section has even less priority than [defaults]
        self.sectionslist = ['defaults','injected']

        ## add other sections (not including site DN) after defaults,
        ## but before site-specific.
        for section in sections[:-1]:
            self.addConfigSection(section)

        if self.site.startswith("www."):
            sitewith = self.site
            sitewithout = self.site.replace("www.","")
        else:
            sitewith = "www."+self.site
            sitewithout = self.site

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
            logger.warning("Failed to perform section_url_names: %s"%e)

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
                    val = val + self._read_file_opener(v)
                    file_val = True
                except:
                    pass
            if not file_val:
                logger.warning("All files for (%s) failed!  Using (%s) instead. Filelist: (%s)"%
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
        vlist = [x for x in [ v.strip().replace(r'\,',',') for v in vlist ] if x !='']
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
        replace_chapter_text_re = re.compile(r'(add_to_)?replace_chapter_text$')
        from .story import set_in_ex_clude, make_replacements, make_chapter_text_replacements

        custom_columns_settings_re = re.compile(r'(add_to_)?custom_columns_settings$')
        custom_columns_flags_re = re.compile(r'^[rna](_anthaver)?')

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

                        if replace_chapter_text_re.match(keyword):
                            make_chapter_text_replacements(value)

                        if generate_cover_settings_re.match(keyword):
                            make_generate_cover_settings(value)

                        if custom_columns_settings_re.match(keyword):
                            # logger.debug((keyword,value))
                            for line in value.splitlines():
                                if line != '':
                                    try:
                                        (meta,custcol) = [ x.strip() for x in line.split("=>") ]
                                    except Exception as e:
                                        errors.append((self.get_lineno(section,keyword),"Failed to parse (%s) line '%s'(%s)"%(keyword,line,e)))
                                        continue
                                    flag='r'
                                    if "," in custcol:
                                        (custcol,flag) = [ x.strip() for x in custcol.split(",") ]
                                    if not custcol.startswith('#'):
                                        errors.append((self.get_lineno(section,keyword),"Custom column name must start with '#' (%s) found for %s"%(custcol,keyword)))
                                    if not custom_columns_flags_re.match(flag):
                                        errors.append((self.get_lineno(section,keyword),"%s not a valid flag value for %s"%(flag,keyword)))

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

    def _read_file_opener(self,fn):
        '''
        For reading urls from _filelist entries.  Used to use same
        fetch routines as for getting stories, but a) those make
        dependencies a mess and b) that has a lot more complication
        now with different caching.
        '''

        if not self.filelist_fetcher:
            # always use base requests fetcher for _filelist--odds are
            # much higher user wants a file:// than something through
            # browser cache or a proxy.
            self.filelist_fetcher = fetchers.RequestsFetcher(self.getConfig,
                                                             self.getConfigList)
        ( data, redirecturl ) = self.filelist_fetcher.get_request_redirected(fn)
        retval = None
        # NOT using website encoding reduce_zalgo etc decoding because again,
        # much more likely to be file://
        for code in self.getConfigList('filelist_encodings',
                                       default=["utf8",
                                                "Windows-1252",
                                                "iso-8859-1"]):
            try:
                retval = data.decode(code)
                break
            except:
                logger.debug("failed decode (%s) as (%s)"%(fn,code))
        return retval

#### methods for fetching.  Moved here from base_adapter when
#### *_filelist feature was added.

    def get_fetcher(self,
                    make_new = False):
        cookiejar = None
        if self.fetcher is not None and make_new:
            cookiejar = self.get_fetcher().get_cookiejar()
            # save and re-apply cookiejar when make_new.
        if not self.fetcher or make_new:

            if self.getConfig('use_flaresolverr_proxy',False):
                logger.debug("use_flaresolverr_proxy:%s"%self.getConfig('use_flaresolverr_proxy'))
                fetchcls = fetcher_flaresolverr_proxy.FlareSolverr_ProxyFetcher
                if (self.getConfig('include_images') and
                    self.getConfig('use_flaresolverr_proxy') != 'withimages' and
                    self.getConfig('use_flaresolverr_proxy') != 'directimages') and not self.getConfig('use_browser_cache'):
                    logger.warning("FlareSolverr v2+ doesn't work with images: include_images automatically set false")
                    logger.warning("Set use_flaresolverr_proxy:withimages if your are using FlareSolver v1 and want images")
                    logger.warning("Set use_flaresolverr_proxy:directimages to download images directly while using FlareSolver")
                    self.set('overrides', 'include_images', 'false')
            elif self.getConfig('use_nsapa_proxy',False):
                logger.debug("use_nsapa_proxy:%s"%self.getConfig('use_nsapa_proxy'))
                fetchcls = fetcher_nsapa_proxy.NSAPA_ProxyFetcher
            elif self.getConfig('use_cloudscraper',False):
                logger.debug("use_cloudscraper:%s"%self.getConfig('use_cloudscraper'))
                fetchcls = fetchers.CloudScraperFetcher
            else:
                fetchcls = fetchers.RequestsFetcher
            self.fetcher = fetchcls(self.getConfig,
                                    self.getConfigList)

            ########################################################
            ## Adding fetcher decorators.  Order matters--last added,
            ## first called.  If ProgressBarDecorator is added before
            ## Cache, it's never called for cache hits, for example.

            ## cache decorator terminates the chain when found.
            logger.debug("use_browser_cache:%s"%self.getConfig('use_browser_cache'))
            if self.getConfig('use_browser_cache'):
                logger.debug("browser_cache_path:%s"%self.getConfig('browser_cache_path'))
                try:
                    ## make a data list of decorators to re-apply if
                    ## there are many more.
                    if self.browser_cache is None:
                        self.browser_cache = BrowserCache(self.site,
                                                          self.getConfig,
                                                          self.getConfigList)
                    fetchers.BrowserCacheDecorator(self.browser_cache).decorate_fetcher(self.fetcher)
                except Exception as e:
                    logger.warning("Failed to setup BrowserCache(%s)"%e)
                    raise

            ## doesn't sleep when fromcache==True
            ## saved for set_sleep
            self.sleeper = fetchers.SleepDecorator()
            self.sleeper.decorate_fetcher(self.fetcher)

            ## cache decorator terminates the chain when found.
            logger.debug("use_basic_cache:%s"%self.getConfig('use_basic_cache'))
            if self.getConfig('use_basic_cache') and self.basic_cache is not None:
                fetchers.BasicCacheDecorator(self.basic_cache).decorate_fetcher(self.fetcher)

            if self.getConfig('progressbar'):
                fetchers.ProgressBarDecorator().decorate_fetcher(self.fetcher)
        if cookiejar is not None:
            self.fetcher.set_cookiejar(cookiejar)
        return self.fetcher

    ## used by plugin to change time for ffnet.
    def set_sleep_override(self,val):
        return self.sleeper.set_sleep_override(val)

    def get_cookiejar(self,filename=None,mozilla=False):
        return self.get_fetcher().get_cookiejar(filename,mozilla)

    def set_cookiejar(self,cookiejar):
        self.get_fetcher().set_cookiejar(cookiejar)

    def get_basic_cache(self):
        return self.basic_cache

    ## replace cache, then replace fetcher (while keeping cookiejar)
    ## to replace fetcher decorators.
    def set_basic_cache(self,cache):
        self.basic_cache = cache
        self.get_fetcher(make_new=True)

    def get_browser_cache(self):
        # logger.debug("1configuration.get_browser_cache:%s"%self.browser_cache)
        if self.browser_cache is None:
            # force generation of browser cache if not there
            self.get_fetcher()
        # logger.debug("2configuration.get_browser_cache:%s"%self.browser_cache)
        return self.browser_cache

    ## replace cache, then replace fetcher (while keeping cookiejar)
    ## to replace fetcher decorators.
    def set_browser_cache(self,cache):
        self.browser_cache = cache
        logger.debug("configuration.set_browser_cache:%s"%self.browser_cache)
        self.get_fetcher(make_new=True)

# extended by adapter, writer and story for ease of calling configuration.
class Configurable(object):

    def __init__(self, configuration):
        self.configuration = configuration

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

