# -*- coding: utf-8 -*-

# Copyright 2015 Fanficdownloader team, 2020 FanFicFare team
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
import collections
import email
import imaplib
import re

# unicode in py2, str in py3
from .six.moves.urllib.request import urlopen
from .six.moves.urllib.parse import (urlparse, urlunparse)
from .six import text_type as unicode
from .six import ensure_str

import logging
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup, Tag

from . import adapters
from .configurable import Configuration
from .exceptions import UnknownSite, FetchEmailFailed

def get_urls_from_page(url,configuration=None,normalize=False):
    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)
    try:
        adapter = adapters.getAdapter(configuration,url,anyurl=True)
        return adapter.get_urls_from_page(url,normalize)
    except UnknownSite:
        # no adapter with anyurl=True, must be a random site.

        # fake adapter just for get_request()
        # Also allows user to set website_encodings for [test1.com]
        # and affect this.
        logger.debug("Using [test1.com] settings for unknown site URL(%s)"%url)
        adapter = adapters.getAdapter(configuration,"test1.com",anyurl=True)
        data = adapter.get_request(url)

        return {'urllist':get_urls_from_html(data,url,configuration,normalize)}
    return {}

def get_urls_from_html(data,url=None,configuration=None,normalize=False,foremail=False):
    # logger.debug("get_urls_from_html")
    urls = collections.OrderedDict()

    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)

    if isinstance(data,(BeautifulSoup,Tag)):
        # logger.debug("Using pre-made soup")
        soup = data
    else:
        ## soup and re-soup because BS4/html5lib is more forgiving of
        ## incorrectly nested tags that way.
        # logger.debug("dbl souping")
        soup = BeautifulSoup(unicode(BeautifulSoup(data,"html5lib")),"html5lib")

    for a in soup.findAll('a'):
        if a.has_attr('href'):
            # logger.debug("a['href']:%s"%a['href'])
            href = form_url(url,a['href'])
            # logger.debug("1 urlhref:%s"%href)
            href = cleanup_url(href,configuration,foremail)
            try:
                # logger.debug("2 urlhref:%s"%href)
                adapter = adapters.getAdapter(configuration,href)
                # logger.debug("found adapter")
                if adapter.story.getMetadata('storyUrl') not in urls:
                    urls[adapter.story.getMetadata('storyUrl')] = [href]
                else:
                    urls[adapter.story.getMetadata('storyUrl')].append(href)
                # logger.debug("adapter storyUrl:%s"%adapter.story.getMetadata('storyUrl'))
            except Exception as e:
                # logger.debug(e)
                pass

    # Simply return the longest URL with the assumption that it contains the
    # most user readable metadata, if not normalized
    return list(urls.keys()) if normalize else [max(value, key=len) for key, value in urls.items()]

def get_urls_from_text(data,configuration=None,normalize=False,foremail=False):
    urls = collections.OrderedDict()
    try:
        # py3 can have issues with extended chars in txt emails
        data = ensure_str(data,errors='replace')
    except UnicodeDecodeError:
        data = data.decode('utf8') ## for when called outside calibre.

    if not configuration:
        configuration = Configuration(["test1.com"],"EPUB",lightweight=True)

    for href in re.findall(r'\(?http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\)?', data):
        ## detect and remove ()s around URL ala markdown.
        if href[0] == '(' and href[-1] == ')':
            href = href[1:-1]
        href = cleanup_url(href,configuration,foremail)
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
    return list(urls.keys()) if normalize else [max(value, key=len) for key, value in urls.items()]


def form_url(parenturl,url):
     url = url.strip() # ran across an image with a space in the
                       # src. Browser handled it, so we'd better, too.

     if "//" in url or parenturl == None:
         returl = url
     else:
         parsedUrl = urlparse(parenturl)
         if url.startswith("/") :
             returl = urlunparse(
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
             returl = urlunparse(
                 (parsedUrl.scheme,
                  parsedUrl.netloc,
                  toppath + '/' + url,
                  '','',''))
     return returl

def cleanup_url(href,configuration,foremail=False):
    ## used to perform some common URL clean up.

    # this (should) catch normal story links, some javascript 'are you
    # old enough' links, and 'Report This' links.
    # logger.debug("pre cleanup_url(%s,%s)"%(href,foremail))
    if 'story.php' in href: ## various eFiction and similar.
        m = re.search(r"(?P<sid>(view)?story\.php\?(sid|psid|no|story|stid)=\d+)",href)
        if m != None:
            href = form_url(href,m.group('sid'))
    if foremail and 'forum' in href:
        ## xenforo emails, toss unread and page/post urls.  Emails are
        ## only sent for thread updates, I believe.  Should catch
        ## althist and QQ now as well as SB & SV.  XF2 emails now use
        ## /posts/ or /post- instead of #post-
        if '/threads/' in href:
            href = re.sub(r"/(unread|page-\d+)?(#post-\d+)?(\?new=1)?",r"/",href)
        if re.match(r'.*/post(-|s/)\d+/?$',href):
            href = ""
    # they've changed the domain at least once and the url a couple
    # times now...
    if foremail and ('click' in href or 'fiction/chapter' in href) and 'royalroad' in href:
        try:
            logger.debug("Doing royalroad click through link workaround(%s)"%href)
            adapter = adapters.getAdapter(configuration,"royalroad.com",anyurl=True)
            href = adapter.get_request_redirected(href)[1]
            href = href.replace('&index=1','')
        except Exception as e:
            logger.warning("Skipping royalroad email URL %s, got HTTP error %s"%(href,e))
    return href

def get_urls_from_imap(srv,user,passwd,folder,markread=True):

    # logger.debug("get_urls_from_imap srv:(%s)"%srv)
    mail = imaplib.IMAP4_SSL(srv)
    status = mail.login(user, passwd)
    if status[0] != 'OK':
        raise FetchEmailFailed("Failed to login to mail server")
    # Out: list of "folders" aka labels in gmail.
    status = mail.list()
    # logger.debug(status)

    folders = []
    try:
        for f in status[1]:
            m = re.match(r'^\(.*\) "?."? "?(?P<folder>.+?)"?$',ensure_str(f))
            if m:
                folders.append(m.group("folder").replace("\\",""))
                # logger.debug(folders[-1])
            else:
                logger.warning("Failed to parse IMAP folder line(%s)"%ensure_str(f))
    except:
        folders = []
        logger.warning("Failed to parse IMAP folder list, continuing without list.")

    if status[0] != 'OK':
        raise FetchEmailFailed("Failed to list folders on mail server")

    # Needs to be quoted incase there are spaces, etc.  imaplib
    # doesn't correctly quote folders with spaces.  However, it does
    # check and won't quote strings that already start and end with ",
    # so this is safe.  There may be other chars than " that need escaping.
    status = mail.select('"%s"'%folder.replace('"','\\"'))
    if status[0] != 'OK':
        # logger.debug(status)
        if folders:
            raise FetchEmailFailed("Failed to select folder(%s) on mail server (folder list:%s)"%(folder,folders))
        else:
            raise FetchEmailFailed("Failed to select folder(%s) on mail server"%folder)

    result, data = mail.uid('search', None, "UNSEEN")

    #logger.debug("result:%s"%result)
    #logger.debug("data:%s"%data)
    urls=set()

    #latest_email_uid = data[0].split()[-1]
    for email_uid in data[0].split():

        result, data = mail.uid('fetch', email_uid, '(BODY.PEEK[])') #RFC822

        # logger.debug("result:%s"%result)
        # logger.debug("data:%s"%data)

        raw_email = data[0][1]

    #raw_email = data[0][1] # here's the body, which is raw text of the whole email
    # including headers and alternate payloads

        try:
            email_message = email.message_from_string(ensure_str(raw_email))
        except Exception as e:
            logger.error("Failed decode email message: %s"%e,exc_info=True)
            continue

        # logger.debug("To:%s"%email_message['To'])
        # logger.debug("From:%s"%email_message['From'])
        # logger.debug("Subject:%s"%email_message['Subject'])
        # logger.debug("payload:%r"%email_message.get_payload(decode=True))

        urllist=[]
        for part in email_message.walk():
            try:
                # logger.debug("part mime:%s"%part.get_content_type())
                if part.get_content_type() == 'text/plain':
                    urllist.extend(get_urls_from_text(part.get_payload(decode=True),foremail=True))
                if part.get_content_type() == 'text/html':
                    urllist.extend(get_urls_from_html(part.get_payload(decode=True),foremail=True))
            except Exception as e:
                logger.error("Failed to read email content: %s"%e,exc_info=True)

        if urllist and markread:
            #obj.store(data[0].replace(' ',','),'+FLAGS','\Seen')
            r,d = mail.uid('store',email_uid,'+FLAGS','(\\SEEN)')
            #logger.debug("seen result:%s->%s"%(email_uid,r))

        [ urls.add(x) for x in urllist ]

    return urls

# used by drag-n-drop of email from thunderbird onto Calibre.
def get_urls_from_mime(mime_data):
    urllist=[]
    if mime_data.hasFormat('text/uri-list'):
        # logger.debug("text/uri-list")
        for qurl in mime_data.urls():
            f = qurl.toString()
            if f.endswith('%0D'):
                ## Firefox bookmarks, when dragged over, have an
                ## encoded trailing CR for... reasons?
                f = f[:-3]
            # logger.debug("filename:%s"%f)
            if f.endswith(".eml"):
                # logger.debug("calling urlopen(%s)"%f)
                # continue using .six.moves.urllib.request.urlopen,
                # should only ever be file://
                fhandle = urlopen(f)
                if hasattr(email,'message_from_binary_file'):
                    # py3
                    msg = email.message_from_binary_file(fhandle)
                    # logger.debug("email.message_from_binary_file")
                else:
                    # py2
                    msg = email.message_from_file(fhandle)
                    # logger.debug("email.message_from_file")
                if msg.is_multipart():
                    for part in msg.walk():
                        # logger.debug("part type:%s"%part.get_content_type())
                        if part.get_content_type() == "text/html":
                            # logger.debug("URL list:%s"%get_urls_from_html(part.get_payload(decode=True)))
                            urllist.extend(get_urls_from_html(part.get_payload(decode=True),foremail=True))
                        if part.get_content_type() == "text/plain":
                            # logger.debug("part content:text/plain")
                            # logger.debug("part content:%s"%part.get_payload(decode=True))
                            urllist.extend(get_urls_from_text(part.get_payload(decode=True),foremail=True))
                else:
                    # logger.debug(msg.get_payload(decode=True))
                    urllist.extend(get_urls_from_text(msg.get_payload(decode=True),foremail=True))
                if 'Content-Base' in msg:
                    ## try msg header Content-Base.  Only known case
                    ## is Thunderbird RSS because one person uses it
                    ## and isn't shy about asking for stuff.
                    urllist.extend(get_urls_from_text(msg['Content-Base'],foremail=True))

            else:
                urllist.extend(get_urls_from_text(f))
    elif mime_data.hasFormat('text/html'):
        # logger.debug("text/html")
        urllist.extend(get_urls_from_html(mime_data.html()))
    elif mime_data.hasFormat('text/plain'):
        # logger.debug("text/plain")
        urllist.extend(get_urls_from_text(mime_data.text()))
    return urllist
