# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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
import logging
import string
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
import re

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six import string_types as basestring
from ..six import ensure_binary
from io import BytesIO

## XML isn't as forgiving as HTML, so rather than generate as strings,
## use DOM to generate the XML files.
from xml.dom.minidom import getDOMImplementation

import bs4

from .base_writer import BaseStoryWriter
from ..htmlcleanup import stripHTML,removeEntities
from ..story import commaGroups

logger = logging.getLogger(__name__)

class EpubWriter(BaseStoryWriter):

    @staticmethod
    def getFormatName():
        return 'epub'

    @staticmethod
    def getFormatExt():
        return '.epub'

    def __init__(self, config, story):
        BaseStoryWriter.__init__(self, config, story)

        self.EPUB_CSS = string.Template('''${output_css}''')

        self.EPUB_TITLE_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
</head>
<body class="fff_titlepage">
<h3><a href="${storyUrl}">${title}</a> by ${authorHTML}</h3>
<div>
''')

        self.EPUB_TITLE_ENTRY = string.Template('''
<b>${label}:</b> ${value}<br />
''')

        self.EPUB_NO_TITLE_ENTRY = string.Template('''
${value}<br />
''')

        self.EPUB_TITLE_PAGE_END = string.Template('''
</div>

</body>
</html>
''')

        self.EPUB_TABLE_TITLE_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
</head>
<body class="fff_titlepage">
<h3><a href="${storyUrl}">${title}</a> by ${authorHTML}</h3>
<table class="full">
''')

        self.EPUB_TABLE_TITLE_ENTRY = string.Template('''
<tr><td><b>${label}:</b></td><td>${value}</td></tr>
''')

        self.EPUB_TABLE_TITLE_WIDE_ENTRY = string.Template('''
<tr><td colspan="2"><b>${label}:</b> ${value}</td></tr>
''')

        self.EPUB_TABLE_NO_TITLE_ENTRY = string.Template('''
<tr><td colspan="2">${label}${value}</td></tr>
''')

        self.EPUB_TABLE_TITLE_PAGE_END = string.Template('''
</table>

</body>
</html>
''')

        self.EPUB_TOC_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
</head>
<body class="fff_tocpage">
<div>
<h3>Table of Contents</h3>
''')

        self.EPUB_TOC_ENTRY = string.Template('''
<a href="file${index04}.xhtml">${chapter}</a><br />
''')

        self.EPUB_TOC_PAGE_END = string.Template('''
</div>
</body>
</html>
''')

        self.EPUB_CHAPTER_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${chapter}</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
<meta name="chapterurl" content="${url}" />
<meta name="chapterorigtitle" content="${origchapter}" />
<meta name="chaptertoctitle" content="${tocchapter}" />
<meta name="chaptertitle" content="${chapter}" />
</head>
<body class="fff_chapter">
<h3 class="fff_chapter_title">${chapter}</h3>
''')

        self.EPUB_CHAPTER_END = string.Template('''
</body>
</html>
''')

        self.EPUB_LOG_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Update Log</title>
<link href="stylesheet.css" type="text/css" rel="stylesheet"/>
</head>
<body class="fff_logpage">
<h3>Update Log</h3>
''')

        self.EPUB_LOG_UPDATE_START = string.Template('''
<p class='log_entry'>
''')

        self.EPUB_LOG_ENTRY = string.Template('''
<b>${label}:</b> <span id="${id}">${value}</span>
''')

        self.EPUB_LOG_UPDATE_END = string.Template('''
</p>
<hr/>
''')

        self.EPUB_LOG_PAGE_END = string.Template('''
</body>
</html>
''')

        self.EPUB_LOG_PAGE_END = string.Template('''
</body>
</html>
''')

        self.EPUB_COVER = string.Template('''
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head><title>Cover</title><style type="text/css" title="override_css">
@page {padding: 0pt; margin:0pt}
body { text-align: center; padding:0pt; margin: 0pt; }
div { margin: 0pt; padding: 0pt; }
</style></head><body class="fff_coverpage"><div>
<img src="${coverimg}" alt="cover"/>
</div></body></html>
''')

    def writeLogPage(self, out):
        """
        Write the log page, but only include entries that there's
        metadata for.  START, ENTRY and END are expected to already be
        string.Template().  START and END are expected to use the same
        names as Story.metadata, but ENTRY should use id, label and value.
        """
        if self.hasConfig("logpage_start"):
            START = string.Template(self.getConfig("logpage_start"))
        else:
            START = self.EPUB_LOG_PAGE_START

        if self.hasConfig("logpage_end"):
            END = string.Template(self.getConfig("logpage_end"))
        else:
            END = self.EPUB_LOG_PAGE_END

        # if there's a self.story.logfile, there's an existing log
        # to add to.
        if self.story.logfile:
            logger.debug("existing logfile found, appending")
            # logger.debug("existing data:%s"%self._getLastLogData(self.story.logfile))
            replace_string = "</body>" # "</h3>"
            self._write(out,self.story.logfile.replace(replace_string,self._makeLogEntry(self._getLastLogData(self.story.logfile))+replace_string))
        else:
            # otherwise, write a new one.
            self._write(out,START.substitute(self.story.getAllMetadata()))
            self._write(out,self._makeLogEntry())
            self._write(out,END.substitute(self.story.getAllMetadata()))

    # self parsing instead of Soup because it should be simple and not
    # worth the overhead.
    def _getLastLogData(self,logfile):
        """
        Make a dict() of the most recent(last) log entry for each piece of metadata.
        Switch rindex to index to search from top instead of bottom.
        """
        values = {}
        for entry in self.getConfigList("logpage_entries") + self.getConfigList("extra_logpage_entries"):
            try:
                # <span id="dateUpdated">1975-04-15</span>
                # logger.debug(entry)
                if self.getConfig("force_old_logpage_behavior"):
                    ## option just in case it goes badly
                    span = '<span id="%s">'%entry
                    idx = logfile.rindex(span)+len(span)
                    values[entry] = logfile[idx:logfile.index('</span>',idx)]
                else:
                    ## old code above failed when description (or
                    ## other entry) contained </span> or if
                    ## logpage_entry was changed in non-compatible
                    ## ways.

                    ## This version should be better, but for the
                    ## default logpage_entry, just changing to
                    ## logfile.index('</span>\n',idx) would have been
                    ## enough.
                    if self.hasConfig("logpage_entry"):
                        ENTRY = string.Template(self.getConfig("logpage_entry"))
                    else:
                        ENTRY = self.EPUB_LOG_ENTRY
                    label=self.get_label(entry)
                    valmarker = 'A_VERY_UNLIKELY_STRING' # for re escaping
                    entryre = ENTRY.substitute({'id':entry,
                                                'label':label,
                                                'value':valmarker})
                    entryre = re.escape(entryre).replace(valmarker,r'(?P<value>.+?)')
                    ## find all, use the last.
                    m = re.findall(entryre,logfile,flags=re.MULTILINE|re.DOTALL)
                    # if entry in ("description","dateCreated") :
                    #     logger.debug("\n\n")
                    #     logger.debug(entryre)
                    #     # logger.debug(logfile)
                    #     logger.debug(m)
                    if m:
                        values[entry]=m[-1]
                        # logger.debug(logfile[idx:-1])
            except Exception as e:
                #print("e:%s"%e)
                pass

        return values

    def _makeLogEntry(self, oldvalues={}):
        if self.hasConfig("logpage_update_start"):
            START = string.Template(self.getConfig("logpage_update_start"))
        else:
            START = self.EPUB_LOG_UPDATE_START

        if self.hasConfig("logpage_entry"):
            ENTRY = string.Template(self.getConfig("logpage_entry"))
        else:
            ENTRY = self.EPUB_LOG_ENTRY

        if self.hasConfig("logpage_update_end"):
            END = string.Template(self.getConfig("logpage_update_end"))
        else:
            END = self.EPUB_LOG_UPDATE_END

        retval = START.substitute(self.story.getAllMetadata())

        ## words_added is calculated from logpage because it's the
        ## only place we know the previous version's word count.
        new_words = self.story.getMetadata('numWords')
        old_words = oldvalues.get('numWords',None)
        if new_words and old_words:
            self.story.setMetadata('words_added',commaGroups(unicode(int(new_words.replace(',',''))-int(old_words.replace(',','')))))

        for entry in self.getConfigList("logpage_entries") + self.getConfigList("extra_logpage_entries"):
            if self.isValidMetaEntry(entry):
                val = self.story.getMetadata(entry)
                if val and ( entry not in oldvalues or val != oldvalues[entry] ):
                    # logger.debug("oldlog(%s):%s"%(entry,oldvalues.get(entry,None)))
                    # logger.debug("newlog(%s):%s"%(entry,val))
                    label=self.get_label(entry)
                    retval = retval + ENTRY.substitute({'id':entry,
                                                        'label':label,
                                                        'value':val})
            else:
                # could be useful for introducing extra text, but
                # mostly it makes it easy to tell when you get the
                # keyword wrong.
                retval = retval + entry

        retval = retval + END.substitute(self.story.getAllMetadata())

        if self.getConfig('replace_hr'):
            # replacing a self-closing tag with a container tag in the
            # soup is more difficult than it first appears.  So cheat.
            retval = re.sub("<hr[^>]*>","<div class='center'>* * *</div>",retval)

        return retval

    def writeStoryImpl(self, out):

        if self.story.oldcover and \
                ( (self.getConfig('use_old_cover') and
                   self.story.getMetadata('cover_image') != 'force' ) or not self.story.cover ):
            # logger.debug("use_old_cover:%s"%self.getConfig('use_old_cover'))
            self.use_oldcover = True
            self.story.setMetadata('cover_image','old')
        else:
            self.use_oldcover = False

        ## Python 2.5 ZipFile is rather more primative than later
        ## versions.  It can operate on a file, or on a BytesIO, but
        ## not on an open stream.  OTOH, I suspect we would have had
        ## problems with closing and opening again to change the
        ## compression type anyway.
        zipio = BytesIO()

        ## mimetype must be first file and uncompressed.  Python 2.5
        ## ZipFile can't change compression type file-by-file, so we
        ## have to close and re-open
        outputepub = ZipFile(zipio, 'w', compression=ZIP_STORED)
        outputepub.debug=3
        outputepub.writestr('mimetype','application/epub+zip')
        outputepub.close()

        ## Re-open file for content.
        outputepub = ZipFile(zipio, 'a', compression=ZIP_DEFLATED)
        outputepub.debug=3

        epub3 = self.getConfig("epub_version",default="2.0").startswith("3")
        # epub3 wants manifest items that have <svg> tags marked.  I
        # don't want to completely change how this writer operates.
        # So we'll flag as we go and generate content.opf later.  Only
        # used with application/xhtml+xml files but currently set for all.
        svg_files = {} # filename -> bool contains '<svg'

        ## Only need to check for svg with epub3.
        if epub3:
            def write_to_epub(href, data):
                outputepub.writestr(href,data)
                svg_files[href] = b'<svg' in ensure_binary(data)
        else:
            def write_to_epub(href, data):
                outputepub.writestr(href,data)

        ## Create META-INF/container.xml file.  The only thing it does is
        ## point to content.opf
        containerdom = getDOMImplementation().createDocument(None, "container", None)
        containertop = containerdom.documentElement
        containertop.setAttribute("version","1.0")
        containertop.setAttribute("xmlns","urn:oasis:names:tc:opendocument:xmlns:container")
        rootfiles = containerdom.createElement("rootfiles")
        containertop.appendChild(rootfiles)
        rootfiles.appendChild(newTag(containerdom,"rootfile",{"full-path":"content.opf",
                                                              "media-type":"application/oebps-package+xml"}))
        write_to_epub("META-INF/container.xml",containerdom.toprettyxml(encoding='utf-8'))
        containerdom.unlink()
        del containerdom

        ## Epub has two metadata files with real data.  We're putting
        ## them in content.opf (pointed to by META-INF/container.xml)
        ## and toc.ncx (pointed to by content.opf)

        ## content.opf contains metadata, a 'manifest' list of all
        ## other included files, and another 'spine' list of the items in the
        ## file

        uniqueid= 'fanficfare-uid:%s-u%s-s%s' % (
            self.getMetadata('site'),
            self.story.getList('authorId')[0],
            self.getMetadata('storyId'))

        contentdom = getDOMImplementation().createDocument(None, "package", None)
        package = contentdom.documentElement
        ## might want 3.1 or something in future.
        if epub3:
            package.setAttribute("version","3.0")
            ## for the calibre: settings, especially calibre:title-page
            package.setAttribute("prefix","calibre: https://calibre-ebook.com")
        else:
            package.setAttribute("version","2.0")
        logger.info("Saving EPUB Version "+package.getAttribute("version"))
        package.setAttribute("xmlns","http://www.idpf.org/2007/opf")
        package.setAttribute("unique-identifier","fanficfare-uid")
        metadata=newTag(contentdom,"metadata",
                        attrs={"xmlns:dc":"http://purl.org/dc/elements/1.1/",
                               "xmlns:opf":"http://www.idpf.org/2007/opf"})
        package.appendChild(metadata)

        metadata.appendChild(newTag(contentdom,"dc:identifier",
                                    text=uniqueid,
                                    attrs={"id":"fanficfare-uid"}))

        if self.getMetadata('title'):
            metadata.appendChild(newTag(contentdom,"dc:title",text=self.getMetadata('title'),
                                        attrs={"id":"id"}))

        def creator_attrs(idnum):
            if epub3:
                return {"id":"id-%d"%idnum}
            else:
                return {"opf:role":"aut"}
        idnum = 1
        if self.getMetadata('author'):
            if self.story.isList('author'):
                for auth in self.story.getList('author'):
                    metadata.appendChild(newTag(contentdom,"dc:creator",
                                                attrs=creator_attrs(idnum),
                                                text=auth))
                    idnum += 1
            else:
                metadata.appendChild(newTag(contentdom,"dc:creator",
                                            attrs=creator_attrs(idnum),
                                            text=self.getMetadata('author')))
                idnum += 1

        metadata.appendChild(newTag(contentdom,"dc:contributor",text="FanFicFare [https://github.com/JimmXinu/FanFicFare]",
                                    attrs={"id":"id-%d"%idnum}))
        idnum += 1
        # metadata.appendChild(newTag(contentdom,"dc:rights",text=""))
        if self.story.getMetadata('langcode'):
            langcode=self.story.getMetadata('langcode')
        else:
            langcode='en'
        metadata.appendChild(newTag(contentdom,"dc:language",text=langcode))

        #  published, created, updated, calibre
        #  Leave calling self.story.getMetadataRaw directly in case date format changes.
        if epub3:
            ## epub3 requires an updated modified date on every change of
            ## any kind, not just *content* change.
            from ..dateutils import utcnow
            metadata.appendChild(newTag(contentdom,"meta",
                                        attrs={"property":"dcterms:modified"},
                                        text=utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")))
        else:
            if self.story.getMetadataRaw('datePublished'):
                metadata.appendChild(newTag(contentdom,"dc:date",
                                            attrs={"opf:event":"publication"},
                                            text=self.story.getMetadataRaw('datePublished').strftime("%Y-%m-%d")))

            if self.story.getMetadataRaw('dateCreated'):
                metadata.appendChild(newTag(contentdom,"dc:date",
                                            attrs={"opf:event":"creation"},
                                            text=self.story.getMetadataRaw('dateCreated').strftime("%Y-%m-%d")))

            if self.story.getMetadataRaw('dateUpdated'):
                metadata.appendChild(newTag(contentdom,"dc:date",
                                            attrs={"opf:event":"modification"},
                                            text=self.story.getMetadataRaw('dateUpdated').strftime("%Y-%m-%d")))
                metadata.appendChild(newTag(contentdom,"meta",
                                            attrs={"name":"calibre:timestamp",
                                                   "content":self.story.getMetadataRaw('dateUpdated').strftime("%Y-%m-%dT%H:%M:%S")}))

        series = self.story.getMetadata('series')
        if series and self.getConfig('calibre_series_meta'):
            series_index = "0.0"
            if '[' in series:
                # logger.debug(series)
                ## assumed "series [series_index]"
                series_index = series[series.rindex(' [')+2:-1]
                series = series[:series.rindex(' [')]

                ## calibre always outputs a series_index and it's
                ## always a float with 1 or 2 decimals.  FFF usually
                ## has either an integer or no index. (injected
                ## calibre series is the only float at this time)
                series_index = "%.2f" % float(series_index)

            metadata.appendChild(newTag(contentdom,"meta",
                                        attrs={"name":"calibre:series",
                                               "content":series}))
            metadata.appendChild(newTag(contentdom,"meta",
                                        attrs={"name":"calibre:series_index",
                                               "content":series_index}))

        if self.getMetadata('description'):
            metadata.appendChild(newTag(contentdom,"dc:description",text=
                                        self.getMetadata('description')))

        for subject in self.story.getSubjectTags():
            metadata.appendChild(newTag(contentdom,"dc:subject",text=subject))


        if self.getMetadata('site'):
            metadata.appendChild(newTag(contentdom,"dc:publisher",
                                        text=self.getMetadata('site')))

        if self.getMetadata('storyUrl'):
            if epub3:
                metadata.appendChild(newTag(contentdom,"dc:identifier",
                                            text="URL:"+self.getMetadata('storyUrl')))
            else:
                metadata.appendChild(newTag(contentdom,"dc:identifier",
                                            attrs={"opf:scheme":"URL"},
                                            text=self.getMetadata('storyUrl')))
            metadata.appendChild(newTag(contentdom,"dc:source",
                                        text=self.getMetadata('storyUrl')))

        if epub3:
            # <meta refines="#id" property="title-type">main</meta>
            metadata.appendChild(newTag(contentdom,"meta",
                                        attrs={"property":"title-type",
                                               "refines":"#id",
                                               },
                                        text="main"))

            # epub3 removes attrs that identify dc:creator and
            # dc:contributor types and instead put them here.
            # 'aut' for 1-(idnum-1)
            for j in range(1,idnum-1):
                #<meta property="role" refines="#id-1" scheme="marc:relators">aut</meta>
                metadata.appendChild(newTag(contentdom,"meta",
                                            attrs={"property":"role",
                                                   "refines":"#id-%d"%j,
                                                   "scheme":"marc:relators",
                                                   },
                                            text="aut"))

            metadata.appendChild(newTag(contentdom,"meta",
                                        attrs={"property":"role",
                                               "refines":"#id-%d"%(idnum-1),
                                               "scheme":"marc:relators",
                                               },
                                        text="bkp"))

        ## end of metadata, create manifest.
        items = [] # list of (id, href, type, title) tuples(all strings)
        itemrefs = [] # list of strings -- idrefs from .opfs' spines
        items.append(("ncx","toc.ncx","application/x-dtbncx+xml",None)) ## we'll generate the toc.ncx file,
                                                                   ## but it needs to be in the items manifest.

        guide = None
        coverIO = None

        imgcount=0
        coverimgid = "image0000"
        if self.use_oldcover:
            logger.debug("using old cover")
            (oldcoverhtmlhref,
             oldcoverhtmltype,
             oldcoverhtmldata,
             oldcoverimghref,
             oldcoverimgtype,
             oldcoverimgdata) = self.story.oldcover
            write_to_epub(oldcoverhtmlhref,oldcoverhtmldata)
            write_to_epub(oldcoverimghref,oldcoverimgdata)

            items.append((coverimgid,
                          oldcoverimghref,
                          oldcoverimgtype,
                          None))
            items.append(("cover",oldcoverhtmlhref,oldcoverhtmltype,None))
            itemrefs.append("cover")
            metadata.appendChild(newTag(contentdom,"meta",{"content":coverimgid,
                                                           "name":"cover"}))
            guide = newTag(contentdom,"guide")
            guide.appendChild(newTag(contentdom,"reference",attrs={"type":"cover",
                                                                   "title":"Cover",
                                                                   "href":oldcoverhtmlhref}))
            imgcount+=1

        if self.getConfig('include_images'):
            for imgmap in self.story.getImgUrls():
                imgfile = "OEBPS/"+imgmap['newsrc']
                # don't overwrite old cover.
                if not self.use_oldcover or imgfile != oldcoverimghref:
                    write_to_epub(imgfile,imgmap['data'])
                    items.append(("image%04d"%imgcount,
                                  imgfile,
                                  imgmap['mime'],
                                  None))
                    imgcount+=1
                    if 'cover' in imgfile:
                        # make sure coverimgid is set to the cover, not
                        # just the first image.
                        coverimgid = items[-1][0]


        items.append(("style","OEBPS/stylesheet.css","text/css",None))

        if self.story.cover and not self.use_oldcover:
            # Note that the id of the cover xhmtl *must* be 'cover'
            # for it to work on Nook.
            items.append(("cover","OEBPS/cover.xhtml","application/xhtml+xml",None))
            itemrefs.append("cover")
            #
            # <meta name="cover" content="cover.jpg"/>
            metadata.appendChild(newTag(contentdom,"meta",{"content":coverimgid,
                                                           "name":"cover"}))
            # cover stuff for later:
            # at end of <package>:
            # <guide>
            # <reference type="cover" title="Cover" href="Text/cover.xhtml"/>
            # </guide>
            guide = newTag(contentdom,"guide")
            guide.appendChild(newTag(contentdom,"reference",attrs={"type":"cover",
                                                       "title":"Cover",
                                                       "href":"OEBPS/cover.xhtml"}))

            if self.hasConfig("cover_content"):
                COVER = string.Template(self.getConfig("cover_content"))
            else:
                COVER = self.EPUB_COVER
            coverIO = BytesIO()
            self._write(coverIO,COVER.substitute(dict(list(self.story.getAllMetadata().items())+list({'coverimg':self.story.cover}.items()))))

        if self.getConfig("include_titlepage"):
            items.append(("title_page","OEBPS/title_page.xhtml","application/xhtml+xml","Title Page"))
            itemrefs.append("title_page")
        if self.includeToCPage():
            items.append(("toc_page","OEBPS/toc_page.xhtml","application/xhtml+xml","Table of Contents"))
            itemrefs.append("toc_page")

        ## save where to insert logpage.
        logpage_indices = (len(items),len(itemrefs))

        dologpage = ( self.getConfig("include_logpage") == "smart" and \
                          (self.story.logfile or self.story.getMetadataRaw("status") == "In-Progress") )  \
                     or self.getConfig("include_logpage") == "true"

        ## collect chapter urls and file names for internalize_text_links option.
        chapurlmap = {}
        for index, chap in enumerate(self.story.getChapters(fortoc=True)):
            if chap['html']:
                i=index+1
                items.append(("file%s"%chap['index04'],
                              "OEBPS/file%s.xhtml"%chap['index04'],
                              "application/xhtml+xml",
                              chap['title']))
                itemrefs.append("file%s"%chap['index04'])
                chapurlmap[chap['url']]="file%s.xhtml"%chap['index04'] # url -> relative epub file name.

        if dologpage:
            if self.getConfig("logpage_at_end") == "true":
                ## insert logpage after chapters.
                logpage_indices = (len(items),len(itemrefs))
            items.insert(logpage_indices[0],("log_page","OEBPS/log_page.xhtml","application/xhtml+xml","Update Log"))
            itemrefs.insert(logpage_indices[1],"log_page")

        # write stylesheet.css file.
        write_to_epub("OEBPS/stylesheet.css",self.EPUB_CSS.substitute(self.story.getAllMetadata()))

        # write title page.
        if self.getConfig("titlepage_use_table"):
            TITLE_PAGE_START  = self.EPUB_TABLE_TITLE_PAGE_START
            TITLE_ENTRY       = self.EPUB_TABLE_TITLE_ENTRY
            WIDE_TITLE_ENTRY  = self.EPUB_TABLE_TITLE_WIDE_ENTRY
            NO_TITLE_ENTRY    = self.EPUB_TABLE_NO_TITLE_ENTRY
            TITLE_PAGE_END    = self.EPUB_TABLE_TITLE_PAGE_END
        else:
            TITLE_PAGE_START  = self.EPUB_TITLE_PAGE_START
            TITLE_ENTRY       = self.EPUB_TITLE_ENTRY
            WIDE_TITLE_ENTRY  = None # only wide in tables.
            NO_TITLE_ENTRY    = self.EPUB_NO_TITLE_ENTRY
            TITLE_PAGE_END    = self.EPUB_TITLE_PAGE_END

        if coverIO:
            write_to_epub("OEBPS/cover.xhtml",coverIO.getvalue())
            coverIO.close()

        titlepageIO = BytesIO()
        self.writeTitlePage(out=titlepageIO,
                            START=TITLE_PAGE_START,
                            ENTRY=TITLE_ENTRY,
                            WIDE_ENTRY=WIDE_TITLE_ENTRY,
                            END=TITLE_PAGE_END,
                            NO_TITLE_ENTRY=NO_TITLE_ENTRY)
        if titlepageIO.getvalue(): # will be false if no title page.
            write_to_epub("OEBPS/title_page.xhtml",titlepageIO.getvalue())
        titlepageIO.close()

        # write toc page.
        tocpageIO = BytesIO()
        self.writeTOCPage(tocpageIO,
                          self.EPUB_TOC_PAGE_START,
                          self.EPUB_TOC_ENTRY,
                          self.EPUB_TOC_PAGE_END)
        if tocpageIO.getvalue(): # will be false if no toc page.
            write_to_epub("OEBPS/toc_page.xhtml",tocpageIO.getvalue())
        tocpageIO.close()

        if dologpage:
            # write log page.
            logpageIO = BytesIO()
            self.writeLogPage(logpageIO)
            write_to_epub("OEBPS/log_page.xhtml",logpageIO.getvalue())
            logpageIO.close()

        if self.hasConfig('chapter_start'):
            CHAPTER_START = string.Template(self.getConfig("chapter_start"))
        else:
            CHAPTER_START = self.EPUB_CHAPTER_START

        if self.hasConfig('chapter_end'):
            CHAPTER_END = string.Template(self.getConfig("chapter_end"))
        else:
            CHAPTER_END = self.EPUB_CHAPTER_END

        for index, chap in enumerate(self.story.getChapters()): # (url,title,html)
            # logger.debug("chapter:%s %s %s"%(len(chap['html']), chap['title'],chap['url']))
            if chap['html']:
                chap_data = chap['html']
                if self.getConfig('internalize_text_links'):
                    soup = bs4.BeautifulSoup(chap['html'],'html5lib')
                    changed=False
                    for alink in soup.find_all('a'):
                        ## Chapters can be inserted in the middle
                        ## which can break existing internal links.
                        ## So let's save the original href and update.
                        # logger.debug("found %s"%alink)
                        if alink.has_attr('data-orighref') and alink['data-orighref'] in chapurlmap:
                            alink['href']=chapurlmap[alink['data-orighref']]
                            # logger.debug("set1  %s"%alink)
                            changed=True
                        elif alink.has_attr('href') and alink['href'] in chapurlmap:
                            if not alink['href'].startswith('file'):
                                # only save orig href if not already internal.
                                alink['data-orighref']=alink['href']
                            alink['href']=chapurlmap[alink['href']]
                            # logger.debug("set2  %s"%alink)
                            changed=True
                    if changed:
                        chap_data = unicode(soup)
                        # Don't want html, head or body tags in
                        # chapter html--bs4 insists on adding them.
                        chap_data = re.sub(r"</?(html|head|body)[^>]*>\r?\n?","",chap_data)

                # logger.debug('Writing chapter text for: %s' % chap.title)
                chap['url']=removeEntities(chap['url'])
                chap['chapter']=removeEntities(chap['chapter'])
                chap['title']=removeEntities(chap['title'])
                chap['origchapter']=removeEntities(chap['origtitle'])
                chap['tocchapter']=removeEntities(chap['toctitle'])
                # escape double quotes in all vals.
                for k,v in chap.items():
                    if isinstance(v,basestring): chap[k]=v.replace('"','&quot;')
                fullhtml = CHAPTER_START.substitute(chap) + \
                    chap_data.strip() + \
                    CHAPTER_END.substitute(chap)
                # strip to avoid ever growning numbers of newlines.
                # ffnet(& maybe others) gives the whole chapter text
                # as one line.  This causes problems for nook(at
                # least) when the chapter size starts getting big
                # (200k+)
                fullhtml = re.sub(r'(</p>|<br ?/>)\n*',r'\1\n',fullhtml)

                # logger.debug("write OEBPS/file%s.xhtml"%chap['index04'])
                write_to_epub("OEBPS/file%s.xhtml"%chap['index04'],fullhtml.encode('utf-8'))
                del fullhtml

        if self.story.calibrebookmark:
            write_to_epub("META-INF/calibre_bookmarks.txt",self.story.calibrebookmark)

        manifest = contentdom.createElement("manifest")
        package.appendChild(manifest)
        for item in items:
            (id,href,type,title)=item
            attrs = {'id':id,
                     'href':href,
                     'media-type':type}
            if epub3:
                props = []
                if id=='cover':
                    ## Flag the cover *page*--epub3 only flags cover *img*
                    props.append('calibre:title-page')
                if id==coverimgid and (self.story.cover or self.use_oldcover):
                    props.append('cover-image')
                if type == 'application/xhtml+xml' and svg_files[href]:
                    ## epub3 wants content files containing <svg> tags
                    ## flagged in the metadata.
                    props.append('svg')
                if props:
                    attrs['properties'] = ' '.join(props)
            manifest.appendChild(newTag(contentdom, "item", attrs=attrs))
        if epub3:
            # epub3 nav
            # <item href="nav.xhtml" id="nav" media-type="application/xhtml+xml" properties="nav"/>
            manifest.appendChild(newTag(contentdom,"item",
                                        attrs={'href':'nav.xhtml',
                                               'id':'nav',
                                               'media-type':'application/xhtml+xml',
                                               'properties':'nav'
                                               }))


        spine = newTag(contentdom,"spine",attrs={"toc":"ncx"})
        if self.getConfig('page_progression_direction_rtl'):
            spine.setAttribute("page-progression-direction","rtl")
        package.appendChild(spine)
        for itemref in itemrefs:
            spine.appendChild(newTag(contentdom,"itemref",
                                     attrs={"idref":itemref,
                                            "linear":"yes"}))
        # guide only exists if there's a cover.
        if guide:
            package.appendChild(guide)

        # write content.opf to zip.
        contentxml = contentdom.toprettyxml(encoding='utf-8')
        # tweak for brain damaged Nook STR.  Nook insists on name before content.
        contentxml = contentxml.replace(ensure_binary('<meta content="%s" name="cover"/>'%coverimgid),
                                        ensure_binary('<meta name="cover" content="%s"/>'%coverimgid))

        # write_to_epub used, but already passed using svg_files
        write_to_epub("content.opf",contentxml)

        contentdom.unlink()
        del contentdom

        ## create toc.ncx file
        tocncxdom = getDOMImplementation().createDocument(None, "ncx", None)
        ncx = tocncxdom.documentElement
        ncx.setAttribute("version","2005-1")
        ncx.setAttribute("xmlns","http://www.daisy.org/z3986/2005/ncx/")
        head = tocncxdom.createElement("head")
        ncx.appendChild(head)
        head.appendChild(newTag(tocncxdom,"meta",
                                attrs={"name":"dtb:uid", "content":uniqueid}))
        head.appendChild(newTag(tocncxdom,"meta",
                                attrs={"name":"dtb:depth", "content":"1"}))
        head.appendChild(newTag(tocncxdom,"meta",
                                attrs={"name":"dtb:totalPageCount", "content":"0"}))
        head.appendChild(newTag(tocncxdom,"meta",
                                attrs={"name":"dtb:maxPageNumber", "content":"0"}))

        docTitle = tocncxdom.createElement("docTitle")
        docTitle.appendChild(newTag(tocncxdom,"text",text=self.getMetadata('title')))
        ncx.appendChild(docTitle)

        tocnavMap = tocncxdom.createElement("navMap")
        ncx.appendChild(tocnavMap)

        # <navPoint id="<id>" playOrder="<risingnumberfrom0>">
        #   <navLabel>
        #     <text><chapter title></text>
        #   </navLabel>
        #   <content src="<chapterfile>"/>
        # </navPoint>
        index=0
        for item in items:
            (id,href,type,title)=item
            # only items to be skipped, cover.xhtml, images, toc.ncx, stylesheet.css, should have no title.
            if title :
                navPoint = newTag(tocncxdom,"navPoint",
                                  attrs={'id':id,
                                         'playOrder':unicode(index)})
                tocnavMap.appendChild(navPoint)
                navLabel = newTag(tocncxdom,"navLabel")
                navPoint.appendChild(navLabel)
                ## the xml library will re-escape as needed.
                navLabel.appendChild(newTag(tocncxdom,"text",text=stripHTML(title)))
                navPoint.appendChild(newTag(tocncxdom,"content",attrs={"src":href}))
                index=index+1

        # write_to_epub used, but already passed using svg_files
        write_to_epub("toc.ncx",tocncxdom.toprettyxml(encoding='utf-8'))
        tocncxdom.unlink()
        del tocncxdom

        if epub3:
            ## create nav.xhtml file
            tocnavdom = getDOMImplementation().createDocument(None, "html", None)
            navxhtml = tocnavdom.documentElement
            navxhtml.setAttribute("xmlns","http://www.w3.org/1999/xhtml")
            navxhtml.setAttribute("xmlns:epub","http://www.idpf.org/2007/ops")
            navxhtml.setAttribute("lang",langcode)
            navxhtml.setAttribute("xml:lang",langcode)
            head = tocnavdom.createElement("head")
            navxhtml.appendChild(head)
            head.appendChild(newTag(tocnavdom,"title",text="Navigation"))
            # <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
            head.appendChild(newTag(tocnavdom,"meta",
                                    attrs={"http-equiv":"Content-Type",
                                           "content":"text/html; charset=utf-8"}))

            body = tocnavdom.createElement("body")
            navxhtml.appendChild(body)
            nav = newTag(tocnavdom,"nav",
                         attrs={"epub:type":"toc"})
            body.appendChild(nav)
            ol = newTag(tocnavdom,"ol")
            nav.appendChild(ol)

            for item in items:
                (id,href,type,title)=item
                # only items to be skipped, cover.xhtml, images, toc.nav,
                # stylesheet.css, should have no title.
                if title:
                    li = newTag(tocnavdom,"li")
                    ol.appendChild(li)
                    atag = newTag(tocnavdom,"a",
                                  attrs={"href":href},
                                  text=stripHTML(title))
                    li.appendChild(atag)

            if self.story.cover and not self.use_oldcover:
                # <nav epub:type="landmarks" hidden="">
                #   <ol>
                #     <li><a href="OEBPS/cover.xhtml" epub:type="cover">Cover</a></li>
                #   </ol>
                # </nav>
                nav = newTag(tocnavdom,"nav",
                             attrs={"epub:type":"landmarks",
                                    "hidden":""})
                body.appendChild(nav)
                ol = newTag(tocnavdom,"ol")
                nav.appendChild(ol)
                li = newTag(tocnavdom,"li")
                ol.appendChild(li)
                atag = newTag(tocnavdom,"a",
                              attrs={"href":"OEBPS/cover.xhtml",
                                     "epub:type":"cover"},
                              text="Cover")
                li.appendChild(atag)

            # write_to_epub used, but already passed using svg_files
            write_to_epub("nav.xhtml",tocnavdom.toprettyxml(encoding='utf-8'))
            tocnavdom.unlink()
            del tocnavdom

        # declares all the files created by Windows.  otherwise, when
        # it runs in appengine, windows unzips the files as 000 perms.
        for zf in outputepub.filelist:
            zf.create_system = 0
        outputepub.close()
        out.write(zipio.getvalue())
        zipio.close()

## Utility method for creating new tags.
def newTag(dom,name,attrs=None,text=None):
    tag = dom.createElement(name)
    if( attrs is not None ):
        for attr in attrs.keys():
            tag.setAttribute(attr,attrs[attr])
    if( text is not None ):
        tag.appendChild(dom.createTextNode(text))
    return tag
