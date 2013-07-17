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

import re
import urlparse
import urllib2 as u2

from BeautifulSoup import BeautifulSoup 
from gziphttp import GZipProcessor

import adapters
from configurable import Configuration

def get_urls_from_page(url,configuration=None,normalize=False):

    if not configuration:
        configuration = Configuration("test1.com","EPUB")

    data = None
    
    # special stuff to log into archiveofourown.org, if possible.
    # Unlike most that show the links to 'adult' stories, but protect
    # them, AO3 doesn't even show them if not logged in.  Only works
    # with saved user/pass--not going to prompt for list.
    if 'archiveofourown.org' in url:
        ao3adapter = adapters.getAdapter(configuration,"http://www.archiveofourown.org/works/0")
        if ao3adapter.getConfig("username"):
            if ao3adapter.getConfig("is_adult"):
                addurl = "?view_adult=true"
            else:
                addurl=""
            # just to get an authenticity_token.
            data = ao3adapter._fetchUrl(url+addurl)
            # login the session.
            ao3adapter.performLogin(url,data)
            # get the list page with logged in session.
            data = ao3adapter._fetchUrl(url)

    if not data:
        opener = u2.build_opener(u2.HTTPCookieProcessor(),GZipProcessor())
        data = opener.open(url).read()

    # kludge because I don't see it on enough sites to be worth generalizing yet.
    restrictsearch=None
    if 'scarvesandcoffee.net' in url:
        restrictsearch=('div',{'id':'mainpage'})

    return get_urls_from_html(data,url,configuration,normalize,restrictsearch)

def get_urls_from_html(data,url=None,configuration=None,normalize=False,restrictsearch=None):

    normalized = [] # normalized url
    retlist = [] # orig urls.
    
    if not configuration:
        configuration = Configuration("test1.com","EPUB")

    soup = BeautifulSoup(data)
    if restrictsearch:
        soup = soup.find(*restrictsearch)
        print("restrict search:%s"%soup)
    
    for a in soup.findAll('a'):
        if a.has_key('href'):
            href = form_url(url,a['href'])
            # this (should) catch normal story links, some javascript
            # 'are you old enough' links, and 'Report This' links.
            # The 'normalized' set prevents duplicates.
            if 'story.php' in a['href']:
                #print("trying:%s"%a['href'])
                m = re.search(r"(?P<sid>(view)?story\.php\?(sid|psid|no|story|stid)=\d+)",a['href'])
                if m != None:
                    href = form_url(url,m.group('sid'))
                    
            try:
                href = href.replace('&index=1','')
                adapter = adapters.getAdapter(configuration,href)
                if adapter.story.getMetadata('storyUrl') not in normalized:
                    normalized.append(adapter.story.getMetadata('storyUrl'))
                    retlist.append(href)
            except:
                pass

    if normalize:
        return normalized
    else:
        return retlist

def get_urls_from_text(data,configuration=None,normalize=False):

    normalized = [] # normalized url
    retlist = [] # orig urls.
    data=unicode(data)
    
    if not configuration:
        configuration = Configuration("test1.com","EPUB")
    
    for href in re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', data):
        # this (should) catch normal story links, some javascript
        # 'are you old enough' links, and 'Report This' links.
        # The 'normalized' set prevents duplicates.
        if 'story.php' in href:
            m = re.search(r"(?P<sid>(view)?story\.php\?(sid|psid|no|story|stid)=\d+)",href)
            if m != None:
                href = form_url(href,m.group('sid'))
        try:
            href = href.replace('&index=1','')
            adapter = adapters.getAdapter(configuration,href)
            if adapter.story.getMetadata('storyUrl') not in normalized:
                normalized.append(adapter.story.getMetadata('storyUrl'))
                retlist.append(href)
        except:
            pass

    if normalize:
        return normalized
    else:
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
       
