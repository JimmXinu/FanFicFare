# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2015 FanFicFare team
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

import collections
import email
import imaplib
import re
import urllib2 as u2
import urlparse

import logging
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
from gziphttp import GZipProcessor

import adapters
from configurable import Configuration
from exceptions import UnknownSite

def get_urls_from_page(url,configuration=None,normalize=False):

    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)

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

        if 'fimfiction.net' in url and adapter.getConfig("is_adult"):
            data = adapter._fetchUrl(url)
            adapter.set_adult_cookie()

        if 'tthfanfic.org' in url and adapter.getConfig("is_adult"):
            ## Simple fetch works in testing, but actual pages use a
            ## POST and has a 'ctkn' value, so we do too.
            # adapter._fetchUrl("https://www.tthfanfic.org/setmaxrating.php?sitemaxrating=5")
            adapter.setSiteMaxRating(url)

        # this way it uses User-Agent or other special settings.
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

def get_urls_from_html(data,url=None,configuration=None,normalize=False,restrictsearch=None,email=False):
    urls = collections.OrderedDict()

    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)

    ## soup and re-soup because BS4/html5lib is more forgiving of
    ## incorrectly nested tags that way.
    soup = BeautifulSoup(unicode(BeautifulSoup(data,"html5lib")),"html5lib")
    if restrictsearch:
        soup = soup.find(*restrictsearch)
        #logger.debug("restrict search:%s"%soup)

    for a in soup.findAll('a'):
        if a.has_attr('href'):
            #logger.debug("a['href']:%s"%a['href'])
            href = form_url(url,a['href'])
            #logger.debug("1 urlhref:%s"%href)
            href = cleanup_url(href,email)
            try:
                #logger.debug("2 urlhref:%s"%href)
                adapter = adapters.getAdapter(configuration,href)
                #logger.debug("found adapter")
                if adapter.story.getMetadata('storyUrl') not in urls:
                    urls[adapter.story.getMetadata('storyUrl')] = [href]
                else:
                    urls[adapter.story.getMetadata('storyUrl')].append(href)
            except Exception, e:
                #logger.debug e
                pass

    # Simply return the longest URL with the assumption that it contains the
    # most user readable metadata, if not normalized
    return urls.keys() if normalize else [max(value, key=len) for key, value in urls.items()]

def get_urls_from_text(data,configuration=None,normalize=False,email=False):
    urls = collections.OrderedDict()
    try:
        data = unicode(data)
    except UnicodeDecodeError:
        data=data.decode('utf8') ## for when called outside calibre.

    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)

    for href in re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', data):
        href = cleanup_url(href,email)
        try:
            adapter = adapters.getAdapter(configuration,href)
            if adapter.story.getMetadata('storyUrl') not in urls:
                urls[adapter.story.getMetadata('storyUrl')] = [href]
            else:
                urls[adapter.story.getMetadata('storyUrl')].append(href)
        except:
            pass

    # Simply return the longest URL with the assumption that it contains the
    # most user readable metadata, if not normalized
    return urls.keys() if normalize else [max(value, key=len) for key, value in urls.items()]


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

def cleanup_url(href,email=False):
    ## used to perform some common URL clean up.

    # this (should) catch normal story links, some javascript 'are you
    # old enough' links, and 'Report This' links.
    if 'story.php' in href: ## various eFiction and similar.
        m = re.search(r"(?P<sid>(view)?story\.php\?(sid|psid|no|story|stid)=\d+)",href)
        if m != None:
            href = form_url(href,m.group('sid'))
    elif email and '/threads/' in href:
        ## xenforo emails, toss unread and page/post urls.  Emails are
        ## only sent for thread updates, I believe.  Email only so
        ## get_urls_from_page can still get post URLs.
        href = re.sub(r"/(unread|page-\d+)?(#post-\d+)?",r"/",href)
    href = href.replace('&index=1','')
    return href

def get_urls_from_imap(srv,user,passwd,folder,markread=True):

    logger.debug("get_urls_from_imap srv:(%s)"%srv)
    mail = imaplib.IMAP4_SSL(srv)
    mail.login(user, passwd)
    mail.list()
    # Out: list of "folders" aka labels in gmail.
    mail.select('"%s"'%folder) # Needs to be quoted incase there are
                               # spaces, etc.  imaplib doesn't
                               # correctly quote folders with spaces.
                               # However, it does check and won't
                               # quote strings that already start and
                               # end with ", so this is safe.

    result, data = mail.uid('search', None, "UNSEEN")

    #logger.debug("result:%s"%result)
    #logger.debug("data:%s"%data)
    urls=set()

    #latest_email_uid = data[0].split()[-1]
    for email_uid in data[0].split():

        result, data = mail.uid('fetch', email_uid, '(BODY.PEEK[])') #RFC822

        #logger.debug("result:%s"%result)
        #logger.debug("data:%s"%data)

        raw_email = data[0][1]

    #raw_email = data[0][1] # here's the body, which is raw text of the whole email
    # including headers and alternate payloads

        email_message = email.message_from_string(raw_email)

        #logger.debug "To:%s"%email_message['To']
        #logger.debug "From:%s"%email_message['From']
        #logger.debug "Subject:%s"%email_message['Subject']

    #    logger.debug("payload:%s"%email_message.get_payload())

        urllist=[]
        for part in email_message.walk():
            try:
            #logger.debug("part mime:%s"%part.get_content_type())
                if part.get_content_type() == 'text/plain':
                    urllist.extend(get_urls_from_text(part.get_payload(decode=True),email=True))
                if part.get_content_type() == 'text/html':
                    urllist.extend(get_urls_from_html(part.get_payload(decode=True),email=True))
            except Exception as e:
                logger.error("Failed to read email content: %s"%e,exc_info=True)
        #logger.debug "urls:%s"%get_urls_from_text(get_first_text_block(email_message))

        if urllist and markread:
            #obj.store(data[0].replace(' ',','),'+FLAGS','\Seen')
            r,d = mail.uid('store',email_uid,'+FLAGS','(\\SEEN)')
            #logger.debug("seen result:%s->%s"%(email_uid,r))

        [ urls.add(x) for x in urllist ]

    return urls
