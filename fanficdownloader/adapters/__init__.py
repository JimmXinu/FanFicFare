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
import adapter_castlefansorg
import adapter_fictionalleyorg
import adapter_fictionpresscom
import adapter_ficwadcom
import adapter_fimfictionnet
import adapter_harrypotterfanfictioncom
import adapter_mediaminerorg
import adapter_potionsandsnitchesnet
import adapter_tenhawkpresentscom
import adapter_adastrafanficcom
import adapter_thewriterscoffeeshopcom
import adapter_tthfanficorg
import adapter_twilightednet
import adapter_twiwritenet
import adapter_whoficcom
import adapter_siyecouk
import adapter_archiveofourownorg
import adapter_ficbooknet
import adapter_portkeyorg
import adapter_mugglenetcom
import adapter_hpfandomnet
import adapter_thequidditchpitchorg
import adapter_nfacommunitycom
import adapter_midnightwhispersca
import adapter_ksarchivecom
import adapter_archiveskyehawkecom
import adapter_squidgeorgpeja
import adapter_libraryofmoriacom
import adapter_wraithbaitcom
import adapter_checkmatedcom
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
import adapter_stargateatlantisorg
import adapter_thealphagatecom
import adapter_fanfiktionde
import adapter_ponyfictionarchivenet
import adapter_sg1heliopoliscom
import adapter_ncisficcom
import adapter_nationallibrarynet
import adapter_themasquenet
import adapter_pretendercentrecom
import adapter_darksolaceorg
import adapter_finestoriescom
import adapter_hpfanficarchivecom
import adapter_twilightarchivescom
import adapter_wizardtalesnet
import adapter_nhamagicalworldsus
import adapter_hlfictionnet
import adapter_grangerenchantedcom
import adapter_dracoandginnycom
import adapter_scarvesandcoffeenet
import adapter_thepetulantpoetesscom
import adapter_wolverineandroguecom
import adapter_sinfuldesireorg
import adapter_merlinficdtwinscouk
import adapter_thehookupzonenet
import adapter_bloodtiesfancom
import adapter_indeathnet
import adapter_jlaunlimitedcom
import adapter_qafficcom
import adapter_efpfanficnet
import adapter_potterficscom
import adapter_efictionestelielde
import adapter_dotmoonnet
import adapter_pommedesangcom
import adapter_restrictedsectionorg
import adapter_imagineeficcom
import adapter_buffynfaithnet
import adapter_psychficcom
import adapter_hennethannunnet
import adapter_tokrafandomnetcom

## This bit of complexity allows adapters to be added by just adding
## importing.  It eliminates the long if/else clauses we used to need
## to pick out the adapter.
    
## List of registered site adapters.
__class_list = []

def imports():
    for name, val in globals().items():
        if isinstance(val, types.ModuleType):
            yield val.__name__

for x in imports():
    if "fanficdownloader.adapters.adapter_" in x:
        #print x
        __class_list.append(sys.modules[x].getClass())

def getNormalStoryURL(url):
    if not getNormalStoryURL.__dummyconfig:
        getNormalStoryURL.__dummyconfig = Configuration("test1.com","EPUB")
    # pulling up an adapter is pretty low over-head.  If
    # it fails, it's a bad url.
    try:
        adapter = getAdapter(getNormalStoryURL.__dummyconfig,url)
        url = adapter.url
        del adapter
        return url
    except:
        return None;

# kludgey function static/singleton
getNormalStoryURL.__dummyconfig = None

def getAdapter(config,url):

    #logger.debug("trying url:"+url)
    (cls,fixedurl) = getClassFor(url)
    #logger.debug("fixedurl:"+fixedurl)
    if cls:
        adapter = cls(config,fixedurl) # raises InvalidStoryURL
        return adapter
    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def getConfigSections():
    return [cls.getConfigSection() for cls in __class_list]

def getConfigSectionFor(url):
    (cls,fixedurl) = getClassFor(url)
    if cls:
        return cls.getConfigSection()
    
    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def getClassFor(url):
    ## fix up leading protocol.
    fixedurl = re.sub(r"(?i)^[htps]+[:/]+","http://",url.strip())
    if not fixedurl.startswith("http"):
        fixedurl = "http://%s"%url
    ## remove any trailing '#' locations.
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
        fixedurl = fixedurl.replace("http://www.","http://")
    if not cls:
        #logger.debug("trying site:www."+domain)
        cls = getClassFromList("www."+domain)
        fixedurl = fixedurl.replace("http://","http://www.")
        
    fixedurl = cls.stripURLParameters(fixedurl)
    
    return (cls,fixedurl)
    
def getClassFromList(domain):
    for cls in __class_list:
        if cls.matchesSite(domain):
            return cls
