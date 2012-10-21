#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

import re, os, traceback
from zipfile import ZipFile
from xml.dom.minidom import parseString

from . import BeautifulSoup as bs

def get_dcsource(inputio):
    return get_update_data(inputio,getfilecount=False,getsoups=False)[0]

def get_dcsource_chaptercount(inputio):
    return get_update_data(inputio,getfilecount=True,getsoups=False)[:2] # (source,filecount)

def get_update_data(inputio,
                    getfilecount=True,
                    getsoups=True):
    epub = ZipFile(inputio, 'r')

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
                print("epubutils: found pre-existing cover image:%s"%src)
                oldcoverimghref = src
                oldcoverimgdata = epub.read(src)
                for item in contentdom.getElementsByTagName("item"):
                    if( relpath+item.getAttribute("href") == oldcoverimghref ):
                        oldcoverimgtype = item.getAttribute("media-type")
                        break
                oldcover = (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
            except Exception as e:
                print("Cover Image %s not found"%src)
                print("Exception: %s"%(unicode(e)))
                traceback.print_exc()

    filecount = 0
    soups = [] # list of xhmtl blocks
    images = {} # dict() longdesc->data
    if getfilecount:
        # spin through the manifest--only place there are item tags.
        for item in contentdom.getElementsByTagName("item"):
            # First, count the 'chapter' files.  FFDL uses file0000.xhtml,
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
                        soup = bs.BeautifulSoup(epub.read(href).decode("utf-8"))
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
                                print("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))
                                print("Exception: %s"%(unicode(e)))
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
                            
                        soups.append(soup)
                        
                    filecount+=1

    try:
        calibrebookmark = epub.read("META-INF/calibre_bookmarks.txt")
    except:
        pass
                    
    for k in images.keys():
        print("\tlongdesc:%s\n\tData len:%s\n"%(k,len(images[k])))
    return (source,filecount,soups,images,oldcover,calibrebookmark,logfile)

def get_path_part(n):
    relpath = os.path.dirname(n)
    if( len(relpath) > 0 ):
        relpath=relpath+"/"
    return relpath

def get_story_url_from_html(inputio,_is_good_url=None):

    #print("get_story_url_from_html called")
    epub = ZipFile(inputio, 'r')

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
        # First, count the 'chapter' files.  FFDL uses file0000.xhtml,
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
