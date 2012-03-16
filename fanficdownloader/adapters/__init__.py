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

from .. import exceptions as exceptions

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
            
def getAdapter(config,url,fileform=None):
    ## fix up leading protocol.
    fixedurl = re.sub(r"(?i)^[htp]+[:/]+","http://",url.strip())
    if not fixedurl.startswith("http"):
        fixedurl = "http://%s"%url
    ## remove any trailing '#' locations.
    fixedurl = re.sub(r"#.*$","",fixedurl)
    
    ## remove any trailing '&' parameters--?sid=999 will be left.
    ## that's all that any of the current adapters need or want.
    fixedurl = re.sub(r"&.*$","",fixedurl)
    
    parsedUrl = up.urlparse(fixedurl)
    domain = parsedUrl.netloc.lower()
    if( domain != parsedUrl.netloc ):
        fixedurl = fixedurl.replace(parsedUrl.netloc,domain)

    logging.debug("site:"+domain)
    cls = getClassFor(domain)
    if not cls:
        logging.debug("trying site:www."+domain)
        cls = getClassFor("www."+domain)
        fixedurl = fixedurl.replace("http://","http://www.")
    if cls:
        adapter = cls(config,fixedurl) # raises InvalidStoryURL
        adapter.setSectionOrder(adapter.getSiteDomain(),fileform)
        return adapter
    # No adapter found.
    raise exceptions.UnknownSite( url, [cls.getSiteDomain() for cls in __class_list] )

def getClassFor(domain):
    for cls in __class_list:
        if cls.matchesSite(domain):
            return cls
