# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team
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

import imaplib
import email

from BeautifulSoup import BeautifulSoup 
from gziphttp import GZipProcessor

import adapters
from configurable import Configuration
from exceptions import UnknownSite

def get_urls_from_page(url,configuration=None,normalize=False):

    if not configuration:
        configuration = Configuration("test1.com","EPUB")

    data = None
    adapter = None
    try:
        adapter = adapters.getAdapter(configuration,url,anyurl=True)
        
        # special stuff to log into archiveofourown.org, if possible.
        # Unlike most that show the links to 'adult' stories, but protect
        # them, AO3 doesn't even show them if not logged in.  Only works
        # with saved user/pass--not going to prompt for list.
        if 'archiveofourown.org' in url:
            if adapter.getConfig("username"):
                if adapter.getConfig("is_adult"):
                    if '?' in url:
                        addurl = "&view_adult=true"
                    else:
                        addurl = "?view_adult=true"
                else:
                    addurl=""
                # just to get an authenticity_token.
                data = adapter._fetchUrl(url+addurl)
                # login the session.
                adapter.performLogin(url,data)
                # get the list page with logged in session.
    
        # this way it uses User-Agent or other special settings.  Only AO3
        # is doing login.
        data = adapter._fetchUrl(url,usecache=False)
    except UnknownSite:
        # no adapter with anyurl=True, must be a random site.
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
        #print("restrict search:%s"%soup)
    
    for a in soup.findAll('a'):
        if a.has_key('href'):
            #print("a['href']:%s"%a['href'])
            href = form_url(url,a['href'])
            #print("1 urlhref:%s"%href)
            # this (should) catch normal story links, some javascript
            # 'are you old enough' links, and 'Report This' links.
            # The 'normalized' set prevents duplicates.
            if 'story.php' in a['href']:
                #print("trying:%s"%a['href'])
                m = re.search(r"(?P<sid>(view)?story\.php\?(sid|psid|no|story|stid)=\d+)",a['href'])
                if m != None:
                    href = form_url(a['href'] if '//' in a['href'] else url,
                                    m.group('sid'))
                    
            try:
                href = href.replace('&index=1','')
                #print("2 urlhref:%s"%href)
                adapter = adapters.getAdapter(configuration,href)
                #print("found adapter")
                if adapter.story.getMetadata('storyUrl') not in normalized:
                    normalized.append(adapter.story.getMetadata('storyUrl'))
                    retlist.append(href)
            except Exception, e:
                #print e
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
       
def get_urls_from_imap(srv,user,passwd,folder,markread=True):
    
    mail = imaplib.IMAP4_SSL(srv)
    mail.login(user, passwd)
    mail.list()
    # Out: list of "folders" aka labels in gmail.
    mail.select(folder) # , readonly=True connect to inbox.
    
    result, data = mail.uid('search', None, "UNSEEN")
    
    #print("result:%s"%result)
    #print("data:%s"%data)
    urls=set()
    
    #latest_email_uid = data[0].split()[-1]
    for email_uid in data[0].split():

        result, data = mail.uid('fetch', email_uid, '(BODY.PEEK[])') #RFC822
    
        #print("result:%s"%result)
        #print("data:%s"%data)
    
        raw_email = data[0][1]
        
    #raw_email = data[0][1] # here's the body, which is raw text of the whole email
    # including headers and alternate payloads
    
        email_message = email.message_from_string(raw_email)
     
        #print "To:%s"%email_message['To']
        #print "From:%s"%email_message['From']
        #print "Subject:%s"%email_message['Subject']
    
    #    print("payload:%s"%email_message.get_payload())

        urllist=[]
        for part in email_message.walk():
            try:
            #print("part mime:%s"%part.get_content_type())
                if part.get_content_type() == 'text/plain':
                    urllist.extend(get_urls_from_text(part.get_payload(decode=True)))
                if part.get_content_type() == 'text/html':
                    urllist.extend(get_urls_from_html(part.get_payload(decode=True)))
            except Exception as e:
                print("Failed to read email content: %s"%e)
        #print "urls:%s"%get_urls_from_text(get_first_text_block(email_message))

        if urllist and markread:
            #obj.store(data[0].replace(' ',','),'+FLAGS','\Seen')
            r,d = mail.uid('store',email_uid,'+FLAGS','(\\SEEN)')
            #print("seen result:%s->%s"%(email_uid,r))
                
        [ urls.add(x) for x in urllist ]
    
    return urls
