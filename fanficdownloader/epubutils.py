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
            
    filecount = 0
    soups = [] # list of xhmtl blocks
    images = {} # dict() origsrc->data
    if getfilecount:
        # spin through the manifest--only place there are item tags.
        for item in contentdom.getElementsByTagName("item"):
            # First, count the 'chapter' files.  FFDL uses file0000.xhtml,
            # but can also update epubs downloaded from Twisting the
            # Hellmouth, which uses chapter0.html.
            if( item.getAttribute("media-type") == "application/xhtml+xml" ):
                href=relpath+item.getAttribute("href")
                print("---- item href:%s path part: %s"%(href,get_path_part(href)))
                if re.match(r'.*/(file|chapter)\d+\.x?html',href):
                    if getsoups:
                        soup = bs.BeautifulSoup(epub.read(href).decode("utf-8"))
                        for img in soup.findAll('img'):
                            try:
                                newsrc=get_path_part(href)+img['src']
                                # remove all .. and the path part above it, if present.
                                # Most for epubs edited by Sigil.
                                newsrc = re.sub(r"([^/]+/\.\./)","",newsrc)
                                origsrc=img['origsrc']
                                data = epub.read(newsrc)
                                images[origsrc] = data
                                img['src'] = img['origsrc']
                            except Exception as e:
                                print("Image %s not found!\n(originally:%s)"%(newsrc,origsrc))
                                print("Exception: %s"%(unicode(e)))
                                traceback.print_exc()
                        soup = soup.find('body')
                        soup.find('h3').extract()
                        soups.append(soup)
                        
                    filecount+=1

    for k in images.keys():
        print("\torigsrc:%s\n\tData len:%s\n"%(k,len(images[k])))
    return (source,filecount,soups,images)

def get_path_part(n):
    relpath = os.path.dirname(n)
    if( len(relpath) > 0 ):
        relpath=relpath+"/"
    return relpath
