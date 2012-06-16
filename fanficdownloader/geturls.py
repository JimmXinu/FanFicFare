# -*- coding: utf-8 -*-

# Copyright 2012 Fanficdownloader team
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


import urlparse
import urllib2 as u2
import ConfigParser

from BeautifulSoup import BeautifulSoup 
from gziphttp import GZipProcessor

import adapters

def get_urls_from_page(url):
    
    opener = u2.build_opener(u2.HTTPCookieProcessor(),GZipProcessor())
    soup = BeautifulSoup(opener.open(url).read())
    
    normalized = set() # normalized url
    retlist = [] # orig urls.
    config = ConfigParser.SafeConfigParser()
    
    for a in soup.findAll('a'):
        if a.has_key('href'):
            href = form_url(url,a['href'])
            try:
                adapter = adapters.getAdapter(config,href,"EPUB")
                if adapter.story.getMetadata('storyUrl') not in normalized:
                    normalized.add(adapter.story.getMetadata('storyUrl'))
                    retlist.append(href)
            except:
                pass

    return retlist

def form_url(parenturl,url):
     url = url.strip() # ran across an image with a space in the
                       # src. Browser handled it, so we'd better, too.
 
     if "//" in url or parenturl == None:
         returl = url
     else:
         parsedUrl = urlparse.urlparse(parenturl)
         if url.startswith("/") :
             returl = urlparse.urlunparse(
                 (parsedUrl.scheme,
                  parsedUrl.netloc,
                  url,
                  '','',''))
         else:
             toppath=""
             if parsedUrl.path.endswith("/"):
                 toppath = parsedUrl.path
             else:
                 toppath = parsedUrl.path[:parsedUrl.path.rindex('/')]
             returl = urlparse.urlunparse(
                 (parsedUrl.scheme,
                  parsedUrl.netloc,
                  toppath + '/' + url,
                  '','',''))
     return returl
       
