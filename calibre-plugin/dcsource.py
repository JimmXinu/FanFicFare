#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Jim Miller'
__docformat__ = 'restructuredtext en'

from zipfile import ZipFile

from xml.dom.minidom import parseString

def get_dcsource(inputio):
    epub = ZipFile(inputio, 'r')

    ## Find the .opf file.
    container = epub.read("META-INF/container.xml")
    containerdom = parseString(container)
    rootfilenodelist = containerdom.getElementsByTagName("rootfile")
    rootfilename = rootfilenodelist[0].getAttribute("full-path")

    metadom = parseString(epub.read(rootfilename))
    firstmetadom = metadom.getElementsByTagName("metadata")[0]
    try:
        source=firstmetadom.getElementsByTagName("dc:source")[0].firstChild.data.encode("utf-8")
    except:
        source=None

    return source
