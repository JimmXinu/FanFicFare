#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2014, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

from collections import namedtuple

import re, os, traceback, json, datetime
from zipfile import ZipFile
from xml.dom.minidom import parseString

import bs4 as bs

UpdateData = namedtuple('UpdateData',
                        'source filecount soups images oldcover '
                        'calibrebookmark logfile metadata')

def get_dcsource(inputio):
    return get_update_data(inputio,getfilecount=False,getsoups=False).source

def get_dcsource_chaptercount(inputio):
    nt = get_update_data(inputio,getfilecount=True,getsoups=False)
    return (nt.source,nt.filecount)

def get_epub_metadata(inputio):
    return get_update_data(inputio,getfilecount=False,getsoups=False).metadata

def get_update_data(inputio,
                    getfilecount=True,
                    getsoups=True):
    epub = ZipFile(inputio, 'r') # works equally well with inputio as a path or a blob

    ## Find the .opf file.
    container = epub.read("META-INF/container.xml")
    containerdom = parseString(container)
    rootfilenodelist = containerdom.getElementsByTagName("rootfile")
    rootfilename = rootfilenodelist[0].getAttribute("full-path")

    contentdom = parseString(epub.read(rootfilename))
    firstmetadom = contentdom.getElementsByTagName("metadata")[0]
    try:
        source=firstmetadom.getElementsByTagName("dc:source")[0].firstChild.data.encode("utf-8")
    except:
        source=None

    ## Save the path to the .opf file--hrefs inside it are relative to it.
    relpath = get_path_part(rootfilename)

    oldcover = None
    calibrebookmark = None
    logfile = None
    # Looking for pre-existing cover.
    for item in contentdom.getElementsByTagName("reference"):
        if item.getAttribute("type") == "cover":
            # there is a cover (x)html file, save the soup for it.
            href=relpath+item.getAttribute("href")
            oldcoverhtmlhref = href
            oldcoverhtmldata = epub.read(href)
            oldcoverhtmltype = "application/xhtml+xml"
            for item in contentdom.getElementsByTagName("item"):
                if( relpath+item.getAttribute("href") == oldcoverhtmlhref ):
                    oldcoverhtmltype = item.getAttribute("media-type")
                    break
            soup = bs.BeautifulSoup(oldcoverhtmldata.decode("utf-8"))
            src = None
            # first img or image tag.
            imgs = soup.findAll('img')
            if imgs:
                src = get_path_part(href)+imgs[0]['src']
            else:
                imgs = soup.findAll('image')
                if imgs:
                    src=get_path_part(href)+imgs[0]['xlink:href']

            if not src:
                continue
            try:
                # remove all .. and the path part above it, if present.
                # Mostly for epubs edited by Sigil.
                src = re.sub(r"([^/]+/\.\./)","",src)
                #print("epubutils: found pre-existing cover image:%s"%src)
                oldcoverimghref = src
                oldcoverimgdata = epub.read(src)
                for item in contentdom.getElementsByTagName("item"):
                    if( relpath+item.getAttribute("href") == oldcoverimghref ):
                        oldcoverimgtype = item.getAttribute("media-type")
                        break
                oldcover = (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
            except Exception as e:
                logger.warn("Cover Image %s not found"%src)
                logger.warn("Exception: %s"%(unicode(e)))
                traceback.print_exc()

    filecount = 0
    soups = [] # list of xhmtl blocks
    images = {} # dict() longdesc->data
    if getfilecount:
        # spin through the manifest--only place there are item tags.
        for item in contentdom.getElementsByTagName("item"):
            # First, count the 'chapter' files.  FFF uses file0000.xhtml,
            # but can also update epubs downloaded from Twisting the
            # Hellmouth, which uses chapter0.html.
            if( item.getAttribute("media-type") == "application/xhtml+xml" ):
                href=relpath+item.getAttribute("href")
                #print("---- item href:%s path part: %s"%(href,get_path_part(href)))
                if re.match(r'.*/log_page\.x?html',href):
                    try:
                        logfile = epub.read(href).decode("utf-8")
                    except:
                        pass # corner case I bumped into while testing.
                if re.match(r'.*/(file|chapter)\d+\.x?html',href):
                    if getsoups:
                        soup = bs.BeautifulSoup(epub.read(href).decode("utf-8"),"html5lib")
                        for img in soup.findAll('img'):
                            newsrc=''
                            longdesc=''
                            try:
                                newsrc=get_path_part(href)+img['src']
                                # remove all .. and the path part above it, if present.
                                # Mostly for epubs edited by Sigil.
                                newsrc = re.sub(r"([^/]+/\.\./)","",newsrc)
                                longdesc=img['longdesc']
                                data = epub.read(newsrc)
                                images[longdesc] = data
                                img['src'] = img['longdesc']
                            except Exception as e:
                                logger.warn("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))
                                logger.warn("Exception: %s"%(unicode(e)))
                                traceback.print_exc()
                        soup = soup.find('body')
                        # ffdl epubs have chapter title h3
                        h3 = soup.find('h3')
                        if h3:
                            h3.extract()
                        # TtH epubs have chapter title h2
                        h2 = soup.find('h2')
                        if h2:
                            h2.extract()

                        for skip in soup.findAll(attrs={'class':'skip_on_ffdl_update'}):
                            skip.extract()

                        soups.append(soup)

                    filecount+=1

    try:
        calibrebookmark = epub.read("META-INF/calibre_bookmarks.txt")
    except:
        pass


    metadata = {}
    try:
        for meta in firstmetadom.getElementsByTagName("meta"):
            if meta.getAttribute("name")=="fanficfare:story_metadata":
                #print("meta.getAttribute(content):%s"%meta.getAttribute("content"))
                metadata=jsonloads(meta.getAttribute("content"))
    except Exception as e:
        pass
        # logger.info("metadata %s not found")
        # logger.info("Exception: %s"%(unicode(e)))
        # traceback.print_exc()

    #for k in images.keys():
        #print("\tlongdesc:%s\n\tData len:%s\n"%(k,len(images[k])))
    return UpdateData(source,filecount,soups,images,oldcover,
                      calibrebookmark,logfile,metadata)

def get_path_part(n):
    relpath = os.path.dirname(n)
    if( len(relpath) > 0 ):
        relpath=relpath+"/"
    return relpath

def get_story_url_from_html(inputio,_is_good_url=None):

    #print("get_story_url_from_html called")
    epub = ZipFile(inputio, 'r') # works equally well with inputio as a path or a blob

    ## Find the .opf file.
    container = epub.read("META-INF/container.xml")
    containerdom = parseString(container)
    rootfilenodelist = containerdom.getElementsByTagName("rootfile")
    rootfilename = rootfilenodelist[0].getAttribute("full-path")

    contentdom = parseString(epub.read(rootfilename))
    #firstmetadom = contentdom.getElementsByTagName("metadata")[0]

    ## Save the path to the .opf file--hrefs inside it are relative to it.
    relpath = get_path_part(rootfilename)

    # spin through the manifest--only place there are item tags.
    for item in contentdom.getElementsByTagName("item"):
        # First, count the 'chapter' files.  FFF uses file0000.xhtml,
        # but can also update epubs downloaded from Twisting the
        # Hellmouth, which uses chapter0.html.
        #print("---- item:%s"%item)
        if( item.getAttribute("media-type") == "application/xhtml+xml" ):
            filehref=relpath+item.getAttribute("href")
            soup = bs.BeautifulSoup(epub.read(filehref).decode("utf-8"))
            for link in soup.findAll('a',href=re.compile(r'^http.*')):
                ahref=link['href']
                #print("href:(%s)"%ahref)
                # hack for bad ficsaver ffnet URLs.
                m = re.match(r"^http://www.fanfiction.net/s(?P<id>\d+)//$",ahref)
                if m != None:
                    ahref="http://www.fanfiction.net/s/%s/1/"%m.group('id')
                if _is_good_url == None or _is_good_url(ahref):
                    return ahref
    return None

## why json doesn't define a date/time format is beyond me...
def datetime_decoder(d):
    if isinstance(d, list):
        pairs = enumerate(d)
    elif isinstance(d, dict):
        pairs = d.items()
    result = []
    for k,v in pairs:
        if isinstance(v, basestring):
            try:
                # The %f format code is only supported in Python >= 2.6.
                # For Python <= 2.5 strip off microseconds
                # v = datetime.datetime.strptime(v.rsplit('.', 1)[0],
                #     '%Y-%m-%dT%H:%M:%S')
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                try:
                    v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    try:
                        v = datetime.datetime.strptime(v, '%Y-%m-%d')
                    except ValueError:
                        pass
        elif isinstance(v, (dict, list)):
            v = datetime_decoder(v)
        result.append((k, v))
    if isinstance(d, list):
        return [x[1] for x in result]
    elif isinstance(d, dict):
        return dict(result)

def jsonloads(obj):
    return json.loads(obj, object_hook=datetime_decoder)
