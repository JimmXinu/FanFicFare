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

import os, re, sys, glob, types
from os.path import dirname, basename, normpath
import logging
import urlparse as up

logger = logging.getLogger(__name__)

from .. import exceptions as exceptions
from ..configurable import Configuration

## must import each adapter here.

import adapter_test1
import adapter_fanfictionnet
import adapter_fanficcastletvnet
import adapter_fictionalleyorg
import adapter_fictionpresscom
import adapter_ficwadcom
import adapter_fimfictionnet
import adapter_harrypotterfanfictioncom
import adapter_mediaminerorg
import adapter_potionsandsnitches
import adapter_tenhawkpresentscom
import adapter_adastrafanficcom
import adapter_twcslibrarynet
import adapter_tthfanficorg
import adapter_twilightednet
import adapter_whoficcom
import adapter_siyecouk
import adapter_archiveofourownorg
import adapter_ficbooknet
import adapter_portkeyorg
import adapter_mugglenetcom
import adapter_hpfandomnet
import adapter_nfacommunitycom
import adapter_midnightwhispersca
import adapter_ksarchivecom
import adapter_archiveskyehawkecom
import adapter_squidgeorgpeja
import adapter_libraryofmoriacom
import adapter_wraithbaitcom
import adapter_chaossycophanthexcom
import adapter_dramioneorg
import adapter_erosnsapphosycophanthexcom
import adapter_lumossycophanthexcom
import adapter_occlumencysycophanthexcom
import adapter_phoenixsongnet
import adapter_walkingtheplankorg
import adapter_ashwindersycophanthexcom
import adapter_thehexfilesnet
import adapter_dokugacom
import adapter_iketernalnet
import adapter_onedirectionfanfictioncom
import adapter_storiesofardacom
import adapter_samdeanarchivenu
import adapter_destinysgatewaycom
import adapter_ncisfictionnet
import adapter_thealphagatecom
import adapter_fanfiktionde
import adapter_ponyfictionarchivenet
import adapter_ncisficcom
import adapter_nationallibrarynet
import adapter_themasquenet
import adapter_pretendercentrecom
import adapter_darksolaceorg
import adapter_finestoriescom
import adapter_hpfanficarchivecom
import adapter_twilightarchivescom
import adapter_nhamagicalworldsus
import adapter_hlfictionnet
import adapter_dracoandginnycom
import adapter_scarvesandcoffeenet
import adapter_thepetulantpoetesscom
import adapter_wolverineandroguecom
import adapter_sinfuldesireorg
import adapter_merlinficdtwinscouk
import adapter_thehookupzonenet
import adapter_bloodtiesfancom
import adapter_indeathnet
import adapter_qafficcom
import adapter_efpfanficnet
import adapter_potterficscom
import adapter_efictionestelielde
import adapter_pommedesangcom
import adapter_restrictedsectionorg
import adapter_imagineeficcom
import adapter_psychficcom
import adapter_asr3slashzoneorg
import adapter_potterheadsanonymouscom
import adapter_fictionpadcom
import adapter_storiesonlinenet
import adapter_trekiverseorg
import adapter_literotica
import adapter_voracity2eficcom
import adapter_spikeluvercom
import adapter_bloodshedversecom
import adapter_nocturnallightnet
import adapter_fanfichu
import adapter_fanfictioncsodaidokhu
import adapter_fictionmaniatv
import adapter_tolkienfanfiction
import adapter_themaplebookshelf
import adapter_fannation
import adapter_sheppardweircom
import adapter_samandjacknet
import adapter_csiforensicscom
import adapter_lotrfanfictioncom
import adapter_fhsarchivecom
import adapter_fanfictionjunkiesde
import adapter_tgstorytimecom
import adapter_itcouldhappennet
import adapter_forumsspacebattlescom
import adapter_forumssufficientvelocitycom
import adapter_forumquestionablequestingcom
import adapter_ninelivesarchivecom
import adapter_masseffect2in
import adapter_quotevcom
import adapter_mcstoriescom
import adapter_lucifaelff
import adapter_buffygilescom
import adapter_andromedawebcom
import adapter_artemisfowlcom
import adapter_naiceanilmenet
import adapter_deepinmysoulnet
import adapter_haremlucifaelcom
import adapter_kiarepositorymujajinet
import adapter_fanfictionlucifaelcom
import adapter_adultfanfictionorg
import adapter_fictionhuntcom

## This bit of complexity allows adapters to be added by just adding
## importing.  It eliminates the long if/else clauses we used to need
## to pick out the adapter.

## List of registered site adapters.
__class_list = []
__domain_map = {}

def imports():
    for name, val in globals().items():
        if isinstance(val, types.ModuleType):
            yield val.__name__

for x in imports():
    if "fanficfare.adapters.adapter_" in x:
        #print x
        cls = sys.modules[x].getClass()
        __class_list.append(cls)
        for site in cls.getAcceptDomains():
            __domain_map[site]=cls

def getNormalStoryURL(url):
    r = getNormalStoryURLSite(url)
    if r:
        return r[0]
    else:
        return None

def getNormalStoryURLSite(url):
    # print("getNormalStoryURLSite:%s"%url)
    if not getNormalStoryURL.__dummyconfig:
        getNormalStoryURL.__dummyconfig = Configuration(["test1.com"],"EPUB",lightweight=True)
    # pulling up an adapter is pretty low over-head.  If
    # it fails, it's a bad url.
    try:
        adapter = getAdapter(getNormalStoryURL.__dummyconfig,url)
        url = adapter.url
        site = adapter.getSiteDomain()
        del adapter
        return (url,site)
    except:
        return None

# kludgey function static/singleton
getNormalStoryURL.__dummyconfig = None

def getAdapter(config,url,anyurl=False):

    #logger.debug("trying url:"+url)
    (cls,fixedurl) = getClassFor(url)
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
    for cls in filter( lambda x : issubclass(x,base_efiction_adapter.BaseEfictionAdapter),
                       __class_list):
        sections.update( [ x.replace('www.','') for x in cls.getConfigSections() ] )
    return sections

def getSiteExamples():
    l=[]
    for cls in sorted(__class_list, key=lambda x : x.getConfigSection()):
        l.append((cls.getConfigSection(),cls.getSiteExampleURLs().split()))
    return l

def getConfigSectionsFor(url):
    (cls,fixedurl) = getClassFor(url)
    if cls:
        return cls.getConfigSections()

    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def getClassFor(url):
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

    parsedUrl = up.urlparse(fixedurl)
    domain = parsedUrl.netloc.lower()
    if( domain != parsedUrl.netloc ):
        fixedurl = fixedurl.replace(parsedUrl.netloc,domain)

    cls = getClassFromList(domain)
    if not cls and domain.startswith("www."):
        domain = domain.replace("www.","")
        #logger.debug("trying site:without www: "+domain)
        cls = getClassFromList(domain)
        fixedurl = re.sub(r"^http(s?)://www\.",r"http\1://",fixedurl)
    if not cls:
        #logger.debug("trying site:www."+domain)
        cls = getClassFromList("www."+domain)
        fixedurl = re.sub(r"^http(s?)://",r"http\1://www.",fixedurl)

    if cls:
        fixedurl = cls.stripURLParameters(fixedurl)

    return (cls,fixedurl)

def getClassFromList(domain):
    try:
        return __domain_map[domain]
    except KeyError:
        pass # return none.
