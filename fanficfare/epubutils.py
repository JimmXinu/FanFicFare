# -*- coding: utf-8 -*-
from __future__ import absolute_import

__license__   = 'GPL v3'
__copyright__ = '2020, Jim Miller'
__docformat__ = 'restructuredtext en'

import logging
logger = logging.getLogger(__name__)

import os
import re
import warnings
from collections import defaultdict
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from xml.dom.minidom import parseString

# py2 vs py3 transition
from .six import ensure_text, text_type as unicode
from .six import string_types as basestring
from io import BytesIO

# from io import StringIO
# import cProfile, pstats
# from pstats import SortKey
# def do_cprofile(func):
#     def profiled_func(*args, **kwargs):
#         profile = cProfile.Profile()
#         try:
#             profile.enable()
#             result = func(*args, **kwargs)
#             profile.disable()
#             return result
#         finally:
#             # profile.sort_stats(SortKey.CUMULATIVE).print_stats(20)
#             s = StringIO()
#             sortby = SortKey.CUMULATIVE
#             ps = pstats.Stats(profile, stream=s).sort_stats(sortby)
#             ps.print_stats(20)
#             print(s.getvalue())
#     return profiled_func

import bs4

def get_dcsource(inputio):
    return get_update_data(inputio,getfilecount=False,getsoups=False)[0]

def get_dcsource_chaptercount(inputio):
    ## getsoups=True to check for continue_on_chapter_error chapters.
    return get_update_data(inputio,getfilecount=True,getsoups=True)[:2] # (source,filecount)

def get_cover_data(inputio):
    # (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
    return get_update_data(inputio,getfilecount=True,getsoups=False)[4]

def get_oldcover(epub,relpath,contentdom,item):
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
        imgs = soup.find_all('img')
        if imgs:
            src = get_path_part(href)+imgs[0]['src']
        else:
            imgs = soup.find_all('image')
            if imgs:
                src=get_path_part(href)+imgs[0]['xlink:href']

        if not src:
            return None
    except Exception as e:
        ## Calibre's Polish Book corrupts sub-book covers.
        logger.warning("Cover (x)html file %s not found"%href)
        logger.warning("Exception: %s"%(unicode(e)))

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
        return (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
    except Exception as e:
        logger.warning("Cover Image %s not found"%src)
        logger.warning("Exception: %s"%(unicode(e)))
    return None

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
            oldcover = get_oldcover(epub,relpath,contentdom,item)

    filecount = 0
    soups = [] # list of xhmtl blocks
    urlsoups = {} # map of xhtml blocks by url
    images = {} # dict() longdesc->(epubsrc, data)
    datamaps = defaultdict(dict) # map of data maps by url
    if getfilecount:
        # spin through the manifest--only place there are item tags.
        for item in contentdom.getElementsByTagName("item"):
            href=relpath+item.getAttribute("href")
            # First, count the 'chapter' files.  FFF uses file0000.xhtml,
            # but can also update epubs downloaded from Twisting the
            # Hellmouth, which uses chapter0.html.
            if item.getAttribute("media-type") == "application/xhtml+xml":
                # for epub3--only works on Calibre tagged covers.
                # Back tracking to find the cover *page* from the
                # cover *image* isn't currently done.
                if "calibre:title-page" in item.getAttribute("properties"):
                    oldcover = get_oldcover(epub,relpath,contentdom,item)
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
                        for img in soup.find_all('img'):
                            newsrc=''
                            longdesc=''
                            ## skip <img src="data:image..."
                            ## NOTE - also only applying this processing if img has a longdesc (aka origurl)
                            ## in past, would error out entirely.
                            if img.has_attr('src') and img.has_attr('longdesc') and not img['src'].startswith('data:image') and not img['src'].startswith('failedtoload'):
                                try:
                                    newsrc=get_path_part(href)+img['src']
                                    # remove all .. and the path part above it, if present.
                                    # Mostly for epubs edited by Sigil.
                                    newsrc = re.sub(r"([^/]+/\.\./)","",newsrc)
                                    longdesc=img['longdesc']
                                    img['src'] = img['longdesc']
                                    # logger.debug("html -->img:%s"%longdesc)
                                    if longdesc not in images:
                                        data = epub.read(newsrc)
                                        images[longdesc] = (newsrc, data)
                                        # logger.debug("-->html Add oldimages:%s"%newsrc)
                                except Exception as e:
                                    logger.warning("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))
                                    # logger.warning("Exception: %s"%(unicode(e)),exc_info=True)
                        ## Inline and embedded CSS url() images
                        for inline in soup.select('*[style]') + soup.select('style'):
                            style = ''
                            if inline.name == 'style':
                                style = inline.string
                            if inline.has_attr('style'):
                                style = inline['style']
                            if 'url(' in style:
                                ## the pattern will also accept mismatched '/", which is broken CSS.
                                for style_url in re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style):
                                    if style_url.startswith('failedtoload'):
                                        continue
                                    logger.debug("Updating inline/embedded style url(%s)"%style_url)
                                    newsrc=''
                                    longdesc=''
                                    try:
                                        newsrc=get_path_part(href)+style_url
                                        # remove all .. and the path part above it, if present.
                                        # Mostly for epubs edited by Sigil.
                                        newsrc = re.sub(r"([^/]+/\.\./)","",newsrc)
                                        # logger.debug("htmlcss -->img:%s"%href)
                                        if style_url not in images:
                                            data = epub.read(newsrc)
                                            images[style_url] = (newsrc, data)
                                            # logger.debug("-->htmlcss Add oldimages:%s"%newsrc)
                                            # logger.debug("\nimg %s len(%s)\n"%(newsrc,len(data)))
                                    except Exception as e:
                                        logger.warning("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))

                        bodysoup = soup.find('body')
                        # ffdl epubs have chapter title h3
                        h3 = bodysoup.find('h3')
                        if h3:
                            h3.extract()
                        # TtH epubs have chapter title h2
                        h2 = bodysoup.find('h2')
                        if h2:
                            h2.extract()

                        for skip in bodysoup.find_all(attrs={'class':'skip_on_ffdl_update'}):
                            skip.extract()

                        ## <meta name="chapterurl" content="${url}"></meta>
                        #print("look for meta chapurl")
                        currenturl = None
                        chapurl = soup.find('meta',{'name':'chapterurl'})
                        if chapurl:
                            # logger.debug("chapurl['content']:%s"%chapurl['content'])
                            if chapurl['content'] == "chapter url removed due to failure":
                                # don't count/include continue_on_chapter_error chapters.
                                continue
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
            ## CSS files -- only process when also getting soups for
            ## update.  output_css is configured, but 'extra_css' like
            ## otw workskin might vary.
            if item.getAttribute("media-type") == "text/css" and getsoups:
                style = epub.read(href).decode("utf-8")
                if 'url(' in style:
                    # logger.debug("%s CSS url:%s"%(href,style))
                    ## the pattern will also accept mismatched '/", which is broken CSS.
                    for style_url in re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style):
                        logger.debug("Updating sheet style url(%s)"%style_url)
                        newsrc=''
                        longdesc=''
                        try:
                            newsrc=get_path_part(href)+style_url
                            # remove all .. and the path part above it, if present.
                            # Mostly for epubs edited by Sigil.
                            newsrc = re.sub(r"([^/]+/\.\./)","",newsrc)
                            # logger.debug("css -->img:%s"%href)
                            if style_url not in images:
                                data = epub.read(newsrc)
                                images[style_url] = (newsrc, data)
                                # logger.debug("css -->Add oldimages:%s"%newsrc)
                                # logger.debug("\nimg %s len(%s)\n"%(newsrc,len(data)))
                        except Exception as e:
                            logger.warning("Image %s not found!\n(originally:%s)"%(newsrc,longdesc))
        ## Find all images in file.  Some redundancy with above
        ## finding images in chapters and css, but also keeps images
        ## in the epub that aren't referenced by removed chapters in
        ## case of deliberate chapter reload.  Images will still be
        ## discarded on epub write if not used.
        ## Done on a second spin through manifest to ensure chapter
        ## <img longdesc imgurls get registered first.
        for item in contentdom.getElementsByTagName("item"):
            href=relpath+item.getAttribute("href")
            if item.getAttribute("media-type").startswith("image/") and getsoups:
                img_url = href.replace("OEBPS/","")
                # logger.debug("-->img img:%s"%img_url)
                if img_url not in images:
                    data = epub.read(href)
                    # logger.debug("-->img Add oldimages:%s"%href)
                    images[img_url] = (img_url, data)
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
            for link in soup.find_all('a',href=re.compile(r'^http.*')):
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
            for link in soup.find_all('a',href=re.compile(r'^http.*')):
                ahref=link['href']
                # print("href:(%s)"%ahref)
                if _is_good_url == None or _is_good_url(ahref):
                    return ahref
    return None

# @do_cprofile
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

    unmerge_navxhtmldoms = {}
    ## spin through file contents, saving any unmerge toc.ncx files.
    for zf in inputepub.namelist():
        ## logger.debug("zf:%s"%zf)
        if zf.endswith('/nav.xhtml'):
            ## logger.debug("toc.ncx zf:%s"%zf)
            unmerge_navxhtmldoms[zf] = parseString(inputepub.read(zf))

    tocncxdom = parseString(inputepub.read('toc.ncx'))
    if 'nav.xhtml' in inputepub.namelist():
        navxhtmldom = parseString(inputepub.read('nav.xhtml'))
    else:
        navxhtmldom = None
    ## spin through file contents.
    for zf in inputepub.namelist():
        if zf not in ['mimetype','toc.ncx','nav.xhtml'] and not zf.endswith('/toc.ncx') and not zf.endswith('/nav.xhtml'):
            entrychanged = False
            data = inputepub.read(zf)
            # if isinstance(data,unicode):
            #     logger.debug("\n\n\ndata is unicode\n\n\n")
            if re.match(r'.*/file\d+\.xhtml',zf):
                #logger.debug("zf:%s"%zf)
                data = data.decode('utf-8')
                # should be re-reading an FFF file, single soup should
                # be good enough and halve processing time.
                soup = make_soup(data,dblsoup=False)

                chapterorigtitle = None
                tag = soup.find('meta',{'name':'chapterorigtitle'})
                if tag:
                    chapterorigtitle = tag['content']

                # toctitle is separate for add_chapter_numbers:toconly users.
                chaptertoctitle = None
                tag = soup.find('meta',{'name':'chaptertoctitle'})
                if tag:
                    chaptertoctitle = tag['content']
                else:
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
                        # logger.debug("\nentrychanged:%s\n"%zf)
                        _replace_tocncx(tocncxdom,zf,chaptertoctitle)
                        if navxhtmldom:
                            _replace_navxhtml(navxhtmldom,zf,chaptertoctitle)
                        ## Also look for and update individual
                        ## book toc.ncx files for anthology in case
                        ## it's unmerged.
                        zf_toc = zf[:zf.rfind('/OEBPS/')]+'/toc.ncx'
                        mergedprefix_len = len(zf[:zf.rfind('/OEBPS/')])+1

                        if zf_toc in unmerge_tocncxdoms:
                            _replace_tocncx(unmerge_tocncxdoms[zf_toc],zf[mergedprefix_len:],chaptertoctitle)
                        if zf_toc in unmerge_navxhtmldoms:
                            _replace_navxhtml(unmerge_navxhtmldoms[zf_toc],zf[mergedprefix_len:],chaptertoctitle)

                outputepub.writestr(zf,data.encode('utf-8'))
            else:
                # possibly binary data, thus no .encode().
                outputepub.writestr(zf,data)

    for tocnm, tocdom in unmerge_tocncxdoms.items():
        outputepub.writestr(tocnm,tocdom.toxml(encoding='utf-8'))
    for navnm, navdom in unmerge_navxhtmldoms.items():
        outputepub.writestr(navnm,navdom.toxml(encoding='utf-8'))

    outputepub.writestr('toc.ncx',tocncxdom.toxml(encoding='utf-8'))
    if navxhtmldom:
        outputepub.writestr('nav.xhtml',navxhtmldom.toxml(encoding='utf-8'))
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

def _replace_navxhtml(navxhtmldom,zf,chaptertoctitle):
    ## go after the TOC entry, too.
    # <li><a href="OEBPS/file0003.xhtml">3. (new) Chapter 2, Sinmay on Kintikin</a></li>
    for atag in navxhtmldom.getElementsByTagName("a"):
        if atag.getAttribute('href') == zf:
            atag.childNodes[0].replaceWholeText(chaptertoctitle)
            # logger.debug("a href=%s label:%s"%(zf,atag.toxml()))
            continue

def make_soup(data,dblsoup=True):
    '''
    Convenience method for getting a bs4 soup.  bs3 has been removed.
    '''

    ## html5lib handles <noscript> oddly.  See:
    ## https://bugs.launchpad.net/beautifulsoup/+bug/1277464
    ## This should 'hide' and restore <noscript> tags.
    data = data.replace("noscript>","fff_hide_noscript>")

    ## soup and re-soup because BS4/html5lib is more forgiving of
    ## incorrectly nested tags that way.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        soup = bs4.BeautifulSoup(data,'html5lib')
        if dblsoup:
            soup = bs4.BeautifulSoup(unicode(soup),'html5lib')

    for ns in soup.find_all('fff_hide_noscript'):
        ns.name = 'noscript'

    return soup
