# -*- coding: utf-8 -*-
from __future__ import absolute_import

__license__   = 'GPL v3'
__copyright__ = '2018, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import re, os, traceback
from collections import defaultdict
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from xml.dom.minidom import parseString

# py2 vs py3 transition
from .six import ensure_text, text_type as unicode
from .six import string_types as basestring
from io import BytesIO

import bs4

def get_dcsource(inputio):
    return get_update_data(inputio,getfilecount=False,getsoups=False)[0]

def get_dcsource_chaptercount(inputio):
    return get_update_data(inputio,getfilecount=True,getsoups=False)[:2] # (source,filecount)

def get_cover_data(inputio):
    # (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
    return get_update_data(inputio,getfilecount=True,getsoups=False)[4]

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
        source=ensure_text(firstmetadom.getElementsByTagName("dc:source")[0].firstChild.data)
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
            src = None
            try:
                oldcoverhtmlhref = href
                oldcoverhtmldata = epub.read(href)
                oldcoverhtmltype = "application/xhtml+xml"
                for item in contentdom.getElementsByTagName("item"):
                    if( relpath+item.getAttribute("href") == oldcoverhtmlhref ):
                        oldcoverhtmltype = item.getAttribute("media-type")
                        break
                soup = make_soup(oldcoverhtmldata.decode("utf-8"))
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
            except Exception as e:
                ## Calibre's Polish Book corrupts sub-book covers.
                logger.warn("Cover (x)html file %s not found"%href)
                logger.warn("Exception: %s"%(unicode(e)))

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

    filecount = 0
    soups = [] # list of xhmtl blocks
    urlsoups = {} # map of xhtml blocks by url
    images = {} # dict() longdesc->data
    datamaps = defaultdict(dict) # map of data maps by url
    if getfilecount:
        # spin through the manifest--only place there are item tags.
        for item in contentdom.getElementsByTagName("item"):
            # First, count the 'chapter' files.  FFF uses file0000.xhtml,
            # but can also update epubs downloaded from Twisting the
            # Hellmouth, which uses chapter0.html.
            if( item.getAttribute("media-type") == "application/xhtml+xml" ):
                href=relpath+item.getAttribute("href")
                #print("---- item href:%s path part: %s"%(href,get_path_part(href)))
                if re.match(r'.*/log_page(_u\d+)?\.x?html',href):
                    try:
                        logfile = epub.read(href).decode("utf-8")
                    except:
                        pass # corner case I bumped into while testing.
                if re.match(r'.*/(file|chapter)\d+(_u\d+)?\.x?html',href):
                    # (_u\d+)? is from calibre convert naming files
                    # 3/OEBPS/file0005_u3.xhtml etc.
                    if getsoups:
                        soup = make_soup(epub.read(href).decode("utf-8"))
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
                                # don't report u'OEBPS/failedtoload',
                                # it indicates a failed download
                                # originally.
                                if newsrc != u'OEBPS/failedtoload':
                                    logger.warn("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))
                                    logger.warn("Exception: %s"%(unicode(e)),exc_info=True)
                        bodysoup = soup.find('body')
                        # ffdl epubs have chapter title h3
                        h3 = bodysoup.find('h3')
                        if h3:
                            h3.extract()
                        # TtH epubs have chapter title h2
                        h2 = bodysoup.find('h2')
                        if h2:
                            h2.extract()

                        for skip in bodysoup.findAll(attrs={'class':'skip_on_ffdl_update'}):
                            skip.extract()

                        ## <meta name="chapterurl" content="${url}"></meta>
                        #print("look for meta chapurl")
                        currenturl = None
                        chapurl = soup.find('meta',{'name':'chapterurl'})
                        if chapurl:
                            if chapurl['content'] not in urlsoups: # keep first found if more than one.
                            # print("Found chapurl['content']:%s"%chapurl['content'])
                                currenturl = chapurl['content']
                                urlsoups[chapurl['content']] = bodysoup
                        else:
                            # for older pre-meta.  Only temp.
                            chapa = bodysoup.find('a',{'class':'chapterurl'})
                            if chapa and chapa['href'] not in urlsoups: # keep first found if more than one.
                                urlsoups[chapa['href']] = bodysoup
                                currenturl = chapa['href']
                                chapa.extract()

                        chapterorigtitle = soup.find('meta',{'name':'chapterorigtitle'})
                        if chapterorigtitle:
                            datamaps[currenturl]['chapterorigtitle'] = chapterorigtitle['content']

                        chaptertitle = soup.find('meta',{'name':'chaptertitle'})
                        if chaptertitle:
                            datamaps[currenturl]['chaptertitle'] = chaptertitle['content']

                        soups.append(bodysoup)

                    filecount+=1

    try:
        calibrebookmark = epub.read("META-INF/calibre_bookmarks.txt")
    except:
        pass

    #for k in images.keys():
        #print("\tlongdesc:%s\n\tData len:%s\n"%(k,len(images[k])))
    #print("datamaps:%s"%datamaps)
    return (source,filecount,soups,images,oldcover,calibrebookmark,logfile,urlsoups,datamaps)

def get_path_part(n):
    relpath = os.path.dirname(n)
    if( len(relpath) > 0 ):
        relpath=relpath+"/"
    return relpath

def get_story_url_from_epub_html(inputio,_is_good_url=None):
    # print("get_story_url_from_epub_html called")
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
        if( item.getAttribute("media-type") == "application/xhtml+xml" ):
            filehref=relpath+item.getAttribute("href")
            soup = make_soup(epub.read(filehref).decode("utf-8"))
            for link in soup.findAll('a',href=re.compile(r'^http.*')):
                ahref=link['href']
                # print("href:(%s)"%ahref)
                # hack for bad ficsaver ffnet URLs.
                m = re.match(r"^http://www.fanfiction.net/s(?P<id>\d+)//$",ahref)
                if m != None:
                    ahref="http://www.fanfiction.net/s/%s/1/"%m.group('id')
                if _is_good_url == None or _is_good_url(ahref):
                    return ahref
        ## Looking in toc.ncx for fanficauthors.net story URL
        if( item.getAttribute("media-type") == "application/x-dtbncx+xml" ):
            filehref=relpath+item.getAttribute("href")
            tocncxdom = parseString(epub.read(filehref))
            for metatag in tocncxdom.getElementsByTagName("meta"):
                if metatag.getAttribute('name') == 'dtb:uid':
                    content = metatag.getAttribute('content')
                    if _is_good_url == None:
                        if _is_good_url(content):
                            return content
                    elif "fanficauthors.net" in content:
                        return content
    return None

def get_story_url_from_zip_html(inputio,_is_good_url=None):
    # print("get_story_url_from_zip_html called")
    zipf = ZipFile(inputio, 'r') # works equally well with inputio as a path or a blob

    # calibre's convert tends to put FFF's title_page towards the end,
    # shift it to the front to avoid internal links.
    filelist = zipf.namelist()
    tpl = [ x for x in filelist if 'title_page' in x ]
    for x in tpl:
        filelist.remove(x)
        filelist.insert(0,x)

    for item in filelist:
        # print(item)
        # only .htm, .html and .xhtml (or .xhtm for that matter)
        if re.match(r".*\.x?html?$", item):
            # print("matched")
            try:
                soup = make_soup(zipf.read(item).decode("utf-8"))
            except UnicodeDecodeError:
                # calibre converted to html zip fails with decode.
                soup = make_soup(zipf.read(item))
            for link in soup.findAll('a',href=re.compile(r'^http.*')):
                ahref=link['href']
                # print("href:(%s)"%ahref)
                if _is_good_url == None or _is_good_url(ahref):
                    return ahref
    return None

def reset_orig_chapters_epub(inputio,outfile):
    inputepub = ZipFile(inputio, 'r') # works equally well with a path or a blob

    ## build zip in memory in case updating in place(CLI).
    zipio = BytesIO()

    ## Write mimetype file, must be first and uncompressed.
    ## Older versions of python(2.4/5) don't allow you to specify
    ## compression by individual file.
    ## Overwrite if existing output file.
    outputepub = ZipFile(zipio, 'w', compression=ZIP_STORED)
    outputepub.debug = 3
    outputepub.writestr("mimetype", "application/epub+zip")
    outputepub.close()

    ## Re-open file for content.
    outputepub = ZipFile(zipio, "a", compression=ZIP_DEFLATED)
    outputepub.debug = 3

    changed = False

    unmerge_tocncxdoms = {}
    ## spin through file contents, saving any unmerge toc.ncx files.
    for zf in inputepub.namelist():
        ## logger.debug("zf:%s"%zf)
        if zf.endswith('/toc.ncx'):
            ## logger.debug("toc.ncx zf:%s"%zf)
            unmerge_tocncxdoms[zf] = parseString(inputepub.read(zf))

    tocncxdom = parseString(inputepub.read('toc.ncx'))
    ## spin through file contents.
    for zf in inputepub.namelist():
        if zf not in ['mimetype','toc.ncx'] and not zf.endswith('/toc.ncx'):
            entrychanged = False
            data = inputepub.read(zf)
            # if isinstance(data,unicode):
            #     logger.debug("\n\n\ndata is unicode\n\n\n")
            if re.match(r'.*/file\d+\.xhtml',zf):
                #logger.debug("zf:%s"%zf)
                data = data.decode('utf-8')
                soup = make_soup(data)

                chapterorigtitle = None
                tag = soup.find('meta',{'name':'chapterorigtitle'})
                if tag:
                    chapterorigtitle = tag['content']

                # toctitle is separate for add_chapter_numbers:toconly users.
                chaptertoctitle = None
                tag = soup.find('meta',{'name':'chaptertoctitle'})
                if tag:
                    chaptertoctitle = tag['content']
                    chaptertoctitle = chapterorigtitle

                chaptertitle = None
                tag = soup.find('meta',{'name':'chaptertitle'})
                if tag:
                    chaptertitle = tag['content']
                    chaptertitle_tag = tag

                #logger.debug("chaptertitle:(%s) chapterorigtitle:(%s)"%(chaptertitle, chapterorigtitle))
                if chaptertitle and chapterorigtitle and chapterorigtitle != chaptertitle:
                    origdata = data
                    # data = data.replace(u'<meta name="chaptertitle" content="'+chaptertitle+u'"></meta>',
                    #                     u'<meta name="chaptertitle" content="'+chapterorigtitle+u'"></meta>')
                    # data = data.replace(u'<title>'+chaptertitle+u'</title>',u'<title>'+chapterorigtitle+u'</title>')
                    # data = data.replace(u'<h3>'+chaptertitle+u'</h3>',u'<h3>'+chapterorigtitle+u'</h3>')
                    chaptertitle_tag['content'] = chapterorigtitle
                    title_tag = soup.find('title')
                    if title_tag and title_tag.string == chaptertitle:
                        title_tag.string.replace_with(chapterorigtitle)

                    h3_tag = soup.find('h3')
                    if h3_tag and h3_tag.string == chaptertitle:
                        h3_tag.string.replace_with(chapterorigtitle)

                    data = unicode(soup)

                    entrychanged = ( origdata != data )
                    changed = changed or entrychanged

                    if entrychanged:
                        logger.debug("\nentrychanged:%s\n"%zf)
                        _replace_tocncx(tocncxdom,zf,chaptertoctitle)
                        ## Also look for and update individual
                        ## book toc.ncx files for anthology in case
                        ## it's unmerged.
                        zf_toc = zf[:zf.rfind('/OEBPS/')]+'/toc.ncx'
                        mergedprefix_len = len(zf[:zf.rfind('/OEBPS/')])+1

                        if zf_toc in unmerge_tocncxdoms:
                            _replace_tocncx(unmerge_tocncxdoms[zf_toc],zf[mergedprefix_len:],chaptertoctitle)

                outputepub.writestr(zf,data.encode('utf-8'))
            else:
                # possibly binary data, thus no .encode().
                outputepub.writestr(zf,data)

    for tocnm, tocdom in unmerge_tocncxdoms.items():
        outputepub.writestr(tocnm,tocdom.toxml(encoding='utf-8'))

    outputepub.writestr('toc.ncx',tocncxdom.toxml(encoding='utf-8'))
    outputepub.close()
    # declares all the files created by Windows.  otherwise, when
    # it runs in appengine, windows unzips the files as 000 perms.
    for zf in outputepub.filelist:
        zf.create_system = 0

    # only *actually* write if changed.
    if changed:
        if isinstance(outfile,basestring):
            with open(outfile,"wb") as outputio:
                outputio.write(zipio.getvalue())
        else:
            outfile.write(zipio.getvalue())

    inputepub.close()
    zipio.close()

    return changed

def _replace_tocncx(tocncxdom,zf,chaptertoctitle):
    ## go after the TOC entry, too.
    # <navPoint id="file0005" playOrder="6">
    #   <navLabel>
    #     <text>5. (new) Chapter 4</text>
    #   </navLabel>
    #   <content src="OEBPS/file0005.xhtml"/>
    # </navPoint>
    for contenttag in tocncxdom.getElementsByTagName("content"):
        if contenttag.getAttribute('src') == zf:
            texttag = contenttag.parentNode.getElementsByTagName('navLabel')[0].getElementsByTagName('text')[0]
            texttag.childNodes[0].replaceWholeText(chaptertoctitle)
            #logger.debug("text label:%s"%texttag.toxml())
            continue

def make_soup(data):
    '''
    Convenience method for getting a bs4 soup.  bs3 has been removed.
    '''

    ## html5lib handles <noscript> oddly.  See:
    ## https://bugs.launchpad.net/beautifulsoup/+bug/1277464
    ## This should 'hide' and restore <noscript> tags.
    data = data.replace("noscript>","fff_hide_noscript>")

    ## soup and re-soup because BS4/html5lib is more forgiving of
    ## incorrectly nested tags that way.
    soup = bs4.BeautifulSoup(data,'html5lib')
    soup = bs4.BeautifulSoup(unicode(soup),'html5lib')

    for ns in soup.find_all('fff_hide_noscript'):
        ns.name = 'noscript'

    return soup
