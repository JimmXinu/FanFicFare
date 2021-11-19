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
import os, re, sys, types
from contextlib import contextmanager
import logging

# py2 vs py3 transition
from ..six.moves.urllib.parse import urlparse

logger = logging.getLogger(__name__)

from .. import exceptions as exceptions
from .. import configurable as configurable

## must import each adapter here.

from . import base_efiction_adapter
from . import adapter_test1
from . import adapter_fanfictionnet
from . import adapter_fictionalleyarchiveorg
from . import adapter_fictionpresscom
from . import adapter_ficwadcom
from . import adapter_fimfictionnet
from . import adapter_mediaminerorg
from . import adapter_potionsandsnitches
from . import adapter_tenhawkpresents
from . import adapter_adastrafanficcom
from . import adapter_tthfanficorg
from . import adapter_twilightednet
from . import adapter_whoficcom
from . import adapter_siyecouk
from . import adapter_archiveofourownorg
from . import adapter_ficbooknet
from . import adapter_midnightwhispers
from . import adapter_ksarchivecom
from . import adapter_archiveskyehawkecom
from . import adapter_libraryofmoriacom
from . import adapter_wraithbaitcom
from . import adapter_ashwindersycophanthexcom
from . import adapter_chaossycophanthexcom
from . import adapter_erosnsapphosycophanthexcom
from . import adapter_lumossycophanthexcom
from . import adapter_occlumencysycophanthexcom
from . import adapter_phoenixsongnet
from . import adapter_walkingtheplankorg
from . import adapter_dokugacom
from . import adapter_iketernalnet
from . import adapter_storiesofardacom
from . import adapter_destinysgatewaycom
from . import adapter_ncisfictioncom
from . import adapter_fanfiktionde
from . import adapter_ponyfictionarchivenet
from . import adapter_themasquenet
from . import adapter_pretendercentrecom
from . import adapter_darksolaceorg
from . import adapter_finestoriescom
from . import adapter_hpfanficarchivecom
from . import adapter_hlfictionnet
from . import adapter_dracoandginnycom
from . import adapter_scarvesandcoffeenet
from . import adapter_wolverineandroguecom
from . import adapter_merlinficdtwinscouk
from . import adapter_thehookupzonenet
from . import adapter_bloodtiesfancom
from . import adapter_qafficcom
from . import adapter_efpfanficnet
from . import adapter_imagineeficcom
from . import adapter_potterheadsanonymouscom
from . import adapter_storiesonlinenet
from . import adapter_trekiverseorg
from . import adapter_literotica
from . import adapter_voracity2eficcom
from . import adapter_spikeluvercom
from . import adapter_bloodshedversecom
from . import adapter_fanfichu
from . import adapter_fictionmaniatv
from . import adapter_themaplebookshelf
from . import adapter_sheppardweircom
from . import adapter_samandjacknet
from . import adapter_csiforensicscom
from . import adapter_tgstorytimecom
from . import adapter_forumsspacebattlescom
from . import adapter_forumssufficientvelocitycom
from . import adapter_forumquestionablequestingcom
from . import adapter_ninelivesarchivecom
from . import adapter_masseffect2in
from . import adapter_quotevcom
from . import adapter_mcstoriescom
from . import adapter_buffygilescom
from . import adapter_andromedawebcom
from . import adapter_naiceanilmenet
from . import adapter_adultfanfictionorg
from . import adapter_fictionhuntcom
from . import adapter_royalroadcom
from . import adapter_chosentwofanficcom
from . import adapter_bdsmlibrarycom
from . import adapter_asexstoriescom
from . import adapter_gluttonyfictioncom
from . import adapter_valentchambercom
from . import adapter_looselugscom
from . import adapter_wwwgiantessworldnet
from . import adapter_lotrgficcom
from . import adapter_tomparisdormcom
from . import adapter_sugarquillnet
from . import adapter_starslibrarynet
from . import adapter_fanficauthorsnet
from . import adapter_fireflyfansnet
from . import adapter_shriftweborgbfa
from . import adapter_trekfanfictionnet
from . import adapter_wuxiaworldcom
from . import adapter_wwwlushstoriescom
from . import adapter_wwwutopiastoriescom
from . import adapter_sinfuldreamscomunicornfic
from . import adapter_sinfuldreamscomwhisperedmuse
from . import adapter_sinfuldreamscomwickedtemptation
from . import adapter_asianfanficscom
from . import adapter_webnovelcom
from . import adapter_mttjustoncenet
from . import adapter_narutoficorg
from . import adapter_starskyhutcharchivenet
from . import adapter_swordborderlineangelcom
from . import adapter_tasteofpoisoninkubationnet
from . import adapter_thedelphicexpansecom
from . import adapter_wwwaneroticstorycom
from . import adapter_lcfanficcom
from . import adapter_noveltrovecom
from . import adapter_inkbunnynet
from . import adapter_alternatehistorycom
from . import adapter_wattpadcom
from . import adapter_novelonlinefullcom
from . import adapter_wwwnovelallcom
from . import adapter_wuxiaworldco
from . import adapter_novelupdatescc
from . import adapter_hentaifoundrycom
from . import adapter_mugglenetfanfictioncom
from . import adapter_swiorgru
from . import adapter_fanficsme
from . import adapter_fanfictalkcom
from . import adapter_scifistoriescom
from . import adapter_silmarillionwritersguildorg
from . import adapter_chireadscom
from . import adapter_scribblehubcom
from . import adapter_fictionlive
from . import adapter_wuxiaworldsite
from . import adapter_thesietchcom
from . import adapter_fastnovelnet
from . import adapter_squidgeworldorg
from . import adapter_novelfull
from . import adapter_worldofxde
from . import adapter_psychficcom
from . import adapter_deviantartcom
from . import adapter_patreoncom

## This bit of complexity allows adapters to be added by just adding
## importing.  It eliminates the long if/else clauses we used to need
## to pick out the adapter.

## List of registered site adapters.
__class_list = []
__domain_map = {}

def imports():
    out = []
    for name, val in globals().items():
        if isinstance(val, types.ModuleType):
            out.append(val.__name__)
    return out

for x in imports():
    if "fanficfare.adapters.adapter_" in x:
        #print x
        cls = sys.modules[x].getClass()
        __class_list.append(cls)
        for site in cls.getAcceptDomains():
            l = __domain_map.get(site,[])
            l.append(cls)
            __domain_map[site]=l

def get_url_chapter_range(url_in):
    # Allow chapter range with URL.
    # like test1.com?sid=5[4-6] or [4,6]
    mc = re.match(r"^(?P<url>.*?)(?:\[(?P<begin>\d+)?(?P<comma>[,-])?(?P<end>\d+)?\])?$",url_in)
    #print("url:(%s) begin:(%s) end:(%s)"%(mc.group('url'),mc.group('begin'),mc.group('end')))
    url = mc.group('url')
    ch_begin = mc.group('begin')
    ch_end = mc.group('end')
    if ch_begin and not mc.group('comma'):
        ch_end = ch_begin
    return url,ch_begin,ch_end

# Call as ' with busy_cursor:"
@contextmanager
def lightweight_adapter(url):
    adapter = None
    try:
        if not getNormalStoryURL.__dummyconfig:
            getNormalStoryURL.__dummyconfig = configurable.Configuration(["test1.com"],"EPUB",lightweight=True)
        adapter = getAdapter(getNormalStoryURL.__dummyconfig,url)
        yield adapter
    except:
        yield None
    finally:
        del adapter

def getNormalStoryURL(url):
    r = getNormalStoryURLSite(url)
    if r:
        return r[0]
    else:
        return None

# kludgey function static/singleton
# Note it's *not* on lightweight_adapter because it can't reference
# itself in its definition.
getNormalStoryURL.__dummyconfig = None

def getNormalStoryURLSite(url):
    with lightweight_adapter(url) as adapter:
        if adapter:
            return (adapter.url,adapter.getSiteDomain())
        else:
            return None

## Originally defined for INI [storyUrl] sections where story URL
## contains a title that can change, now also used for reject list.
## waaaay faster with classmethod.
def get_section_url(url):
    cls =  _get_class_for(url)[0]
    if cls:
        return cls.get_section_url(url)
    else:
        ## might be a url from a removed adapter.
        ## return unchanged in that case.
        return url

def getAdapter(config,url,anyurl=False):

    #logger.debug("trying url:"+url)
    (cls,fixedurl) = _get_class_for(url)
    #logger.debug("fixedurl:"+fixedurl)
    if cls:
        if anyurl:
            fixedurl = cls.getSiteExampleURLs().split()[0]
        adapter = cls(config,fixedurl) # raises InvalidStoryURL
        return adapter
    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def getSiteSections():
    # doesn't include base sections. Sections rather than site DNS because of squidge/peja
    return [cls.getConfigSection() for cls in __class_list]

def getConfigSections():
    # does include base sections.
    sections = set()
    for cls in __class_list:
        sections.update(cls.getConfigSections())
    return sections

def get_bulk_load_sites():
    # for now, all eFiction Base adapters are assumed to allow bulk_load.
    sections = set()
    for cls in [x for x in __class_list if issubclass(x,base_efiction_adapter.BaseEfictionAdapter) ]:
        sections.update( [ x.replace('www.','') for x in cls.getConfigSections() ] )
    return sections

def getSiteExamples():
    l=[]
    for cls in sorted(__class_list, key=lambda x : x.getConfigSection()):
        l.append((cls.getConfigSection(),cls.getSiteExampleURLs().split()))
    return l

def getConfigSectionsFor(url):
    (cls,fixedurl) = _get_class_for(url)
    if cls:
        return cls.getConfigSections()

    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def _get_class_for(url):
    ## fix up leading protocol.
    fixedurl = re.sub(r"(?i)^[htp]+(s?)[:/]+",r"http\1://",url.strip())
    if fixedurl.startswith("//"):
        fixedurl = "http:%s"%url
    if not fixedurl.startswith("http"):
        fixedurl = "http://%s"%url

    ## remove any trailing '#' locations, except for #post-12345 for
    ## XenForo
    if not "#post-" in fixedurl:
        fixedurl = re.sub(r"#.*$","",fixedurl)

    parsedUrl = urlparse(fixedurl)
    domain = parsedUrl.netloc.lower()
    if( domain != parsedUrl.netloc ):
        fixedurl = fixedurl.replace(parsedUrl.netloc,domain)

    clslst = _get_classlist_fromlist(domain)
    ## assumes all adapters for a domain will have www or not have www
    ## but not mixed.
    if not clslst and domain.startswith("www."):
        domain = domain.replace("www.","")
        #logger.debug("trying site:without www: "+domain)
        clslst = _get_classlist_fromlist(domain)
        fixedurl = re.sub(r"^http(s?)://www\.",r"http\1://",fixedurl)
    if not clslst:
        #logger.debug("trying site:www."+domain)
        clslst =_get_classlist_fromlist("www."+domain)
        fixedurl = re.sub(r"^http(s?)://",r"http\1://www.",fixedurl)

    cls = None
    if clslst:
        if len(clslst) == 1:
            cls = clslst[0]
        elif len(clslst) > 1:
            for c in clslst:
                if c.getSiteURLFragment() in fixedurl:
                    cls = c
                    break

    if cls:
        fixedurl = cls.stripURLParameters(fixedurl)

    return (cls,fixedurl)

def _get_classlist_fromlist(domain):
    try:
        return __domain_map[domain]
    except KeyError:
        pass # return none.
