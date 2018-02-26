# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2016 FanFicFare team
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

import os, re
from collections import namedtuple
import urlparse
import string
import json
import datetime
from math import floor
from functools import partial
import logging
logger = logging.getLogger(__name__)
import urlparse as up

import bs4

import exceptions
from htmlcleanup import conditionalRemoveEntities, removeAllEntities
from configurable import Configurable, re_compile

Chapter = namedtuple('Chapter', 'url title html origtitle toctitle new')

SPACE_REPLACE=u'\s'
SPLIT_META=u'\,'

# Create convert_image method depending on which graphics lib we can
# load.  Preferred: calibre, PIL, none

imagetypes = {
    'jpg':'image/jpeg',
    'jpeg':'image/jpeg',
    'png':'image/png',
    'gif':'image/gif',
    'svg':'image/svg+xml',
    }

try:
    from calibre.utils.magick import Image
    from StringIO import StringIO
    from gif import GifInfo, CHECK_IS_ANIMATED
    convtype = {'jpg':'JPG', 'png':'PNG'}

    def convert_image(url,data,sizes,grayscale,
                      removetrans,imgtype="jpg",background='#ffffff'):

        if url.lower().endswith('.svg'):
            raise exceptions.RejectImage("Calibre image processing chokes on SVG images.")
        export = False
        img = Image()
        img.load(data)

        owidth, oheight = img.size
        nwidth, nheight = sizes
        scaled, nwidth, nheight = fit_image(owidth, oheight, nwidth, nheight)

        if normalize_format_name(img.format)=="gif" and GifInfo(StringIO(data),CHECK_IS_ANIMATED).frameCount > 1:
            raise exceptions.RejectImage("Animated gifs come out poorly--not going to use it.")

        if scaled:
            img.size = (nwidth, nheight)
            export = True

        if normalize_format_name(img.format) != imgtype:
            export = True

        if removetrans and img.has_transparent_pixels():
            canvas = Image()
            canvas.create_canvas(int(img.size[0]), int(img.size[1]), unicode(background))
            canvas.compose(img)
            img = canvas
            export = True

        if grayscale and img.type != "GrayscaleType":
            img.type = "GrayscaleType"
            export = True

        if export:
            return (img.export(convtype[imgtype]),imgtype,imagetypes[imgtype])
        else:
            logger.debug("image used unchanged")
            return (data,imgtype,imagetypes[imgtype])

except:

    # No calibre routines, try for PIL for CLI.
    try:
        import Image
        from StringIO import StringIO
        convtype = {'jpg':'JPEG', 'png':'PNG'}
        def convert_image(url,data,sizes,grayscale,
                          removetrans,imgtype="jpg",background='#ffffff'):
            export = False
            img = Image.open(StringIO(data))

            owidth, oheight = img.size
            nwidth, nheight = sizes
            scaled, nwidth, nheight = fit_image(owidth, oheight, nwidth, nheight)
            if scaled:
                img = img.resize((nwidth, nheight),Image.ANTIALIAS)
                export = True

            if normalize_format_name(img.format) != imgtype:
                if img.mode == "P":
                    # convert pallete gifs to RGB so jpg save doesn't fail.
                    img = img.convert("RGB")
                export = True

            if removetrans and img.mode == "RGBA":
                background = Image.new('RGBA', img.size, background)
                # Paste the image on top of the background
                background.paste(img, img)
                img = background.convert('RGB')
                export = True

            if grayscale and img.mode != "L":
                img = img.convert("L")
                export = True

            if export:
                outsio = StringIO()
                img.save(outsio,convtype[imgtype])
                return (outsio.getvalue(),imgtype,imagetypes[imgtype])
            else:
                # logger.debug("image used unchanged")
                return (data,imgtype,imagetypes[imgtype])

    except:
        # No calibre or PIL, simple pass through with mimetype.
        def convert_image(url,data,sizes,grayscale,
                          removetrans,imgtype="jpg",background='#ffffff'):
            return no_convert_image(url,data)

## also used for explicit no image processing.
def no_convert_image(url,data):
    parsedUrl = up.urlparse(url)

    ext=parsedUrl.path[parsedUrl.path.rfind('.')+1:].lower()

    if ext not in imagetypes:
        # not found at end of path, try end of whole URL in case of
        # parameter.
        ext = url[url.rfind('.')+1:].lower()
        if ext not in imagetypes:
            logger.debug("no_convert_image url:%s - no known extension"%url)
            # doesn't have extension? use jpg.
            ext='jpg'

    return (data,ext,imagetypes[ext])

def normalize_format_name(fmt):
    if fmt:
        fmt = fmt.lower()
        if fmt == 'jpeg':
            fmt = 'jpg'
    return fmt

def fit_image(width, height, pwidth, pheight):
    '''
    Fit image in box of width pwidth and height pheight.
    @param width: Width of image
    @param height: Height of image
    @param pwidth: Width of box
    @param pheight: Height of box
    @return: scaled, new_width, new_height. scaled is True iff new_width and/or new_height is different from width or height.
    '''
    scaled = height > pheight or width > pwidth
    if height > pheight:
        corrf = pheight/float(height)
        width, height = floor(corrf*width), pheight
    if width > pwidth:
        corrf = pwidth/float(width)
        width, height = pwidth, floor(corrf*height)
    if height > pheight:
        corrf = pheight/float(height)
        width, height = floor(corrf*width), pheight

    return scaled, int(width), int(height)

try:
    # doesn't really matter what, just checking for appengine.
    from google.appengine.api import apiproxy_stub_map

    is_appengine = True
except:
    is_appengine = False


try:
    from calibre.library.comments import sanitize_comments_html
except:
    def sanitize_comments_html(t):
        ## should only be called by Calibre version, so this shouldn't
        ## trip.
        logger.debug("fake sanitize called...")
        return t

# The list comes from ffnet, the only multi-language site we support
# at the time of writing.  Values are taken largely from pycountry,
# but with some corrections and guesses.
langs = {
    "English":"en",
    "Spanish":"es",
    "French":"fr",
    "German":"de",
    "Chinese":"zh",
    "Japanese":"ja",
    "Dutch":"nl",
    "Portuguese":"pt",
    "Russian":"ru",
    "Italian":"it",
    "Bulgarian":"bg",
    "Polish":"pl",
    "Hungarian":"hu",
    "Hebrew":"he",
    "Arabic":"ar",
    "Swedish":"sv",
    "Norwegian":"no",
    "Danish":"da",
    "Finnish":"fi",
    "Filipino":"fil",
    "Esperanto":"eo",
    "Hindi":"hi",
    "Punjabi":"pa",
    "Farsi":"fa",
    "Greek":"el",
    "Romanian":"ro",
    "Albanian":"sq",
    "Serbian":"sr",
    "Turkish":"tr",
    "Czech":"cs",
    "Indonesian":"id",
    "Croatian":"hr",
    "Catalan":"ca",
    "Latin":"la",
    "Korean":"ko",
    "Vietnamese":"vi",
    "Thai":"th",
    "Devanagari":"hi",

    ## These are from/for AO3:

    u'العربية':'ar',
    u'беларуская':'be',
    u'Български език':'bg',
    u'Català':'ca',
    u'Čeština':'cs',
    u'Cymraeg':'cy',
    u'Dansk':'da',
    u'Deutsch':'de',
    u'Ελληνικά':'el',
    u'English':'en',
    u'Esperanto':'eo',
    u'Español':'es',
    u'eesti keel':'et',
    u'فارسی':'fa',
    u'Suomi':'fi',
    u'Wikang Filipino':'fil',
    u'Français':'fr',
    u'Gaeilge':'ga',
    u'Gàidhlig':'gd',
    u'עִבְרִית':'he',
    u'हिन्दी':'hi',
    u'Hrvatski':'hr',
    u'Magyar':'hu',
    u'Bahasa Indonesia':'id',
    u'Íslenska':'is',
    u'Italiano':'it',
    u'日本語':'ja',
    u'한국말':'ko',
    u'Lingua latina':'la',
    u'Lietuvių':'lt',
    u'Latviešu valoda':'lv',
    u'मराठी':'mr',
    u'بهاس ملايو ':'ms',
    u'Nederlands':'nl',
    u'Norsk':'no',
    u'ਪੰਜਾਬੀ':'pa',
    u'Polski':'pl',
    u'Português':'pt',
    u'Quenya':'qya',
    u'Română':'ro',
    u'Русский':'ru',
    u'Slovenčina':'sk',
    u'Shqip':'sq',
    u'српски':'sr',
    u'Svenska':'sv',
    u'ไทย':'th',
    u'tlhIngan-Hol':'tlh', # Klingon. Has a real ISO 639-2 code.
    #'Thermian':'', # Alien language from Galaxy Quest.
    u'Türkçe':'fr',
    u'українська':'uk',
    u'Tiếng Việt':'vi',
    u'中文':'zh',
    u'Bahasa Malaysia':'zsm',
}

class InExMatch:
    keys = []
    regex = None
    match = None
    negate = False

    def  __init__(self,line):
        if "=~" in line:
            (self.keys,self.match) = line.split("=~")
            self.match = self.match.replace(SPACE_REPLACE,' ')
            self.regex = re_compile(self.match,line)
        elif "!~" in line:
            (self.keys,self.match) = line.split("!~")
            self.match = self.match.replace(SPACE_REPLACE,' ')
            self.regex = re_compile(self.match,line)
            self.negate = True
        elif "==" in line:
            (self.keys,self.match) = line.split("==")
            self.match = self.match.replace(SPACE_REPLACE,' ')
        elif "!=" in line:
            (self.keys,self.match) = line.split("!=")
            self.match = self.match.replace(SPACE_REPLACE,' ')
            self.negate = True
        self.keys = map( lambda x: x.strip(), self.keys.split(",") )

    # For conditional, only one key
    def is_key(self,key):
        return key == self.keys[0]

    # For conditional, only one key
    def key(self):
        return self.keys[0]

    def in_keys(self,key):
        return key in self.keys

    def is_match(self,value):
        retval = False
        if self.regex:
            if self.regex.search(value):
                retval = True
            #print(">>>>>>>>>>>>>%s=~%s r: %s,%s=%s"%(self.match,value,self.negate,retval,self.negate != retval))
        else:
            retval = self.match == value
            #print(">>>>>>>>>>>>>%s==%s r: %s,%s=%s"%(self.match,value,self.negate,retval, self.negate != retval))

        return self.negate != retval

    def __str__(self):
        if self.negate:
            f='!'
        else:
            f='='
        if self.regex:
            s='~'
        else:
            s='='
        return u'InExMatch(%s %s%s %s)'%(self.keys,f,s,self.match)

## metakey[,metakey]=~pattern
## metakey[,metakey]==string
## *for* part lines.  Effect only when trailing conditional key=~regexp matches
## metakey[,metakey]=~pattern[&&metakey=~regexp]
## metakey[,metakey]==string[&&metakey=~regexp]
## metakey[,metakey]=~pattern[&&metakey==string]
## metakey[,metakey]==string[&&metakey==string]
def set_in_ex_clude(setting):
    dest = []
    # print("set_in_ex_clude:"+setting)
    for line in setting.splitlines():
        if line:
            (match,condmatch)=(None,None)
            if "&&" in line:
                (line,conditional) = line.split("&&")
                condmatch = InExMatch(conditional)
            match = InExMatch(line)
            dest.append([match,condmatch])
    return dest

## Two or three part lines.  Two part effect everything.
## Three part effect only those key(s) lists.
## pattern=>replacement
## metakey,metakey=>pattern=>replacement
## *Five* part lines.  Effect only when trailing conditional key=>regexp matches
## metakey[,metakey]=>pattern=>replacement[&&metakey=>regexp]
def make_replacements(replace):
    retval=[]
    for repl_line in replace.splitlines():
        line=repl_line
        try:
            (metakeys,regexp,replacement,condkey,condregexp)=(None,None,None,None,None)
            if "&&" in line:
                (line,conditional) = line.split("&&")
                (condkey,condregexp) = conditional.split("=>")
            if "=>" in line:
                parts = line.split("=>")
                if len(parts) > 2:
                    metakeys = map( lambda x: x.strip(), parts[0].split(",") )
                    (regexp,replacement)=parts[1:]
                else:
                    (regexp,replacement)=parts

            if regexp:
                regexp = re_compile(regexp,line)
                if condregexp:
                    condregexp = re_compile(condregexp,line)
                # A way to explicitly include spaces in the
                # replacement string.  The .ini parser eats any
                # trailing spaces.
                replacement=replacement.replace(SPACE_REPLACE,' ')
                retval.append([repl_line,metakeys,regexp,replacement,condkey,condregexp])
        except Exception as e:
            logger.error("Problem with Replacement Line:%s"%repl_line)
            raise exceptions.PersonalIniFailed(e,'replace_metadata unpacking failed',repl_line)
#            raise
    # print("replace lines:%s"%len(retval))
    return retval

class Story(Configurable):

    def __init__(self, configuration):
        Configurable.__init__(self, configuration)
        try:
            ## calibre plugin will set externally to match PI version.
            self.metadata = {'version':os.environ['CURRENT_VERSION_ID']}
        except:
            self.metadata = {'version':'4.4'}
        self.replacements = []
        self.in_ex_cludes = {}
        self.chapters = [] # chapters will be namedtuple of Chapter(url,title,html,etc)
        self.chapter_first = None
        self.chapter_last = None
        self.imgurls = []
        self.imgtuples = []
        # save processed metadata, dicts keyed by 'key', then (removeentities,dorepl)
        # {'key':{(removeentities,dorepl):"value",(...):"value"},'key':... }
        self.processed_metadata_cache = {}
        self.processed_metadata_list_cache = {}

        self.cover=None # *href* of new cover image--need to create html.
        self.oldcover=None # (oldcoverhtmlhref,oldcoverhtmltype,oldcoverhtmldata,oldcoverimghref,oldcoverimgtype,oldcoverimgdata)
        self.calibrebookmark=None # cheesy way to carry calibre bookmark file forward across update.
        self.logfile=None # cheesy way to carry log file forward across update.

        self.replacements_prepped = False

    def prepare_replacements(self):
        if not self.replacements_prepped and not self.is_lightweight():
            # logger.debug("prepare_replacements")
            # logger.debug("sections:%s"%self.configuration.sectionslist)

            ## Look for config parameter, split and add each to metadata field.
            for (config,metadata) in [("extracategories","category"),
                                      ("extragenres","genre"),
                                      ("extracharacters","characters"),
                                      ("extraships","ships"),
                                      ("extrawarnings","warnings")]:
                for val in self.getConfigList(config):
                    self.addToList(metadata,val)

            self.replacements =  make_replacements(self.getConfig('replace_metadata'))

            in_ex_clude_list = ['include_metadata_pre','exclude_metadata_pre',
                                'include_metadata_post','exclude_metadata_post']
            for ie in in_ex_clude_list:
                ies = self.getConfig(ie)
                # print("%s %s"%(ie,ies))
                if ies:
                    iel = []
                    self.in_ex_cludes[ie] = set_in_ex_clude(ies)
                    # print("%s %s"%(ie,len(self.in_ex_cludes[ie])))
            self.replacements_prepped = True


    def set_chapters_range(self,first=None,last=None):
        self.chapter_first=first
        self.chapter_last=last

    def join_list(self, key, vallist):
        return self.getConfig("join_string_"+key,u", ").replace(SPACE_REPLACE,' ').join(map(unicode, [ x for x in vallist if x is not None ]))

    def setMetadata(self, key, value, condremoveentities=True):

        # delete
        if key in self.processed_metadata_cache:
            del self.processed_metadata_cache[key]
        # keep as list type, but set as only value.
        if self.isList(key):
            self.addToList(key,value,condremoveentities=condremoveentities,clear=True)
        else:
            ## still keeps &lt; &lt; and &amp;
            if condremoveentities:
                self.metadata[key]=conditionalRemoveEntities(value)
            else:
                self.metadata[key]=value

        if key == "language":
            try:
                # getMetadata not just self.metadata[] to do replace_metadata.
                self.setMetadata('langcode',langs[self.getMetadata(key)])
            except:
                self.setMetadata('langcode','en')

        if key == 'dateUpdated' and value:
            # Last Update tags for Bill.
            self.addToList('lastupdate',value.strftime("Last Update Year/Month: %Y/%m"),clear=True)
            self.addToList('lastupdate',value.strftime("Last Update: %Y/%m/%d"))

        if key == 'sectionUrl' and value:
            self.addUrlConfigSection(value) # adapter/writer share the
                                            # same configuration.
                                            # ignored if config
                                            # is_lightweight()
            self.replacements_prepped = False

    def do_in_ex_clude(self,which,value,key):
        # sets self.replacements and self.in_ex_cludes if needed
        # do_in_ex_clude is always called from doReplacements, so redundant.
        # self.prepare_replacements()

        if value and which in self.in_ex_cludes:
            include = 'include' in which
            keyfound = False
            found = False
            for (match,condmatch) in self.in_ex_cludes[which]:
                keyfndnow = False
                if match.in_keys(key):
                    # key in keys and either no conditional, or conditional matched
                    if condmatch == None or condmatch.is_key(key):
                        keyfndnow = True
                    else:
                        condval = self.getMetadata(condmatch.key())
                        keyfndnow = condmatch.is_match(condval)
                    keyfound |= keyfndnow
                        # print("match:%s %s\ncondmatch:%s %s\n\tkeyfound:%s\n\tfound:%s"%(
                        #         match,value,condmatch,condval,keyfound,found))
                    if keyfndnow:
                        found = isinstance(value,basestring) and match.is_match(value)
                    if found:
                        # print("match:%s %s\n\tkeyfndnow:%s\n\tfound:%s"%(
                        #         match,value,keyfndnow,found))
                        if not include:
                            value = None
                        break
            if include and keyfound and not found:
                value = None
        return value

    def doReplacements(self,value,key,return_list=False,seen_list=[]):
        # sets self.replacements and self.in_ex_cludes if needed
        self.prepare_replacements()

        value = self.do_in_ex_clude('include_metadata_pre',value,key)
        value = self.do_in_ex_clude('exclude_metadata_pre',value,key)

        retlist = [value]
        for replaceline in self.replacements:
            if replaceline in seen_list: # recursion on pattern, bail
                # print("bailing on %s"%replaceline)
                continue
            #print("replacement tuple:%s"%replaceline)
            (repl_line,metakeys,regexp,replacement,condkey,condregexp) = replaceline
            if (metakeys == None or key in metakeys) \
                    and isinstance(value,basestring) \
                    and regexp.search(value):
                doreplace=True
                if condkey and condkey != key: # prevent infinite recursion.
                    condval = self.getMetadata(condkey)
                    doreplace = condval != None and condregexp.search(condval)

                if doreplace:
                    # split into more than one list entry if
                    # SPLIT_META present in replacement string.  Split
                    # first, then regex sub, then recurse call replace
                    # on each.  Break out of loop, each split element
                    # handled individually by recursion call.
                    if SPLIT_META in replacement:
                        retlist = []
                        for splitrepl in replacement.split(SPLIT_META):
                            try:
                                tval = regexp.sub(splitrepl,value)
                            except:
                                logger.error("Exception with replacement line,value:(%s),(%s)"%(repl_line,value))
                                raise
                            retlist.extend(self.doReplacements(tval,
                                                               key,
                                                               return_list=True,
                                                               seen_list=seen_list+[replaceline]))
                        break
                    else:
                        # print("replacement,value:%s,%s->%s"%(replacement,value,regexp.sub(replacement,value)))
                        try:
                            value = regexp.sub(replacement,value)
                            retlist = [value]
                        except:
                            logger.error("Exception with replacement line,value:(%s),(%s)"%(repl_line,value))
                            raise

        for val in retlist:
            retlist = map(partial(self.do_in_ex_clude,'include_metadata_post',key=key),retlist)
            retlist = map(partial(self.do_in_ex_clude,'exclude_metadata_post',key=key),retlist)

        if return_list:
            return retlist
        else:
            return self.join_list(key,retlist)

    # for saving an html-ified copy of metadata.
    def dump_html_metadata(self):
        lines=[]
        for k,v in sorted(self.metadata.iteritems()):
            classes=['metadata']
            if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                classes.append("datetime")
                val = v.isoformat()
            elif isinstance(v,list):
                classes.append("list")
                if '' in v:
                    v.remove('')
                if None in v:
                    v.remove(None)
                #logger.debug("k:%s v:%s"%(k,v))
                # force ints/floats to strings.
                val = "<ul>\n<li>%s</li>\n</ul>" % "</li>\n<li>".join([ "%s"%x for x in v ])
            elif isinstance(v, (int)):
                classes.append("int")
                val = v
            else:
                val = v

            # don't include items passed in for calibre cols, etc.
            if not k.startswith('calibre_') and k not in ['output_css']:
                lines.append("<p><span class='label'>%s</span>: <div class='%s' id='%s'>%s</div><p>\n"%(
                        self.get_label(k),
                        " ".join(classes),
                        k,val))
        return "\n".join(lines)

    # for loading an html-ified copy of metadata.
    def load_html_metadata(self,data):
        soup = bs4.BeautifulSoup(data,'html5lib')
        for tag in soup.find_all('div','metadata'):
            val = None
            if 'datetime' in tag['class']:
                v = tag.string
                try:
                    val = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    try:
                        val = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        try:
                            val = datetime.datetime.strptime(v, '%Y-%m-%d')
                        except ValueError:
                            pass
            elif 'list' in tag['class']:
                val = []
                for i in tag.find_all('li'):
                    val.append(i.string)
            elif 'int' in tag['class']:
                val = int(tag.string)
            else:
                val = unicode("\n".join([ unicode(c) for c in tag.contents ]))

            #logger.debug("key(%s)=val(%s)"%(tag['id'],val))
            if val:
                self.metadata[tag['id']]=val

        # self.metadata = json.loads(s, object_hook=datetime_decoder)

    def getChapterCount(self):
        ## returns chapter count adjusted for start-end range.
        url_chapters = value = int(self.getMetadata("numChapters").replace(',',''))
        if self.chapter_first:
            value = url_chapters - (int(self.chapter_first) - 1)
        if self.chapter_last:
            value = value - (url_chapters - int(self.chapter_last))
        return value

    def getMetadataRaw(self,key):
        if self.isValidMetaEntry(key) and self.metadata.has_key(key):
            return self.metadata[key]

    def getMetadata(self, key,
                    removeallentities=False,
                    doreplacements=True):
        # check for a cached value to speed processing
        if key in self.processed_metadata_cache \
                and (removeallentities,doreplacements) in self.processed_metadata_cache[key]:
            return self.processed_metadata_cache[key][(removeallentities,doreplacements)]

        value = None
        if not self.isValidMetaEntry(key):
            pass # cache not valid entry, too.
#            return value

        elif self.isList(key):
            # join_string = self.getConfig("join_string_"+key,u", ").replace(SPACE_REPLACE,' ')
            # value = join_string.join(self.getList(key, removeallentities, doreplacements=True))
            value = self.join_list(key,self.getList(key, removeallentities, doreplacements=True))
            if doreplacements:
                value = self.doReplacements(value,key+"_LIST")
        elif self.metadata.has_key(key):
            value = self.metadata[key]
            if value:
                if key in ["numWords","numChapters"]+self.getConfigList("comma_entries",[]):
                    try:
                        value = commaGroups(unicode(value))
                    except Exception as e:
                        logger.warn("Failed to add commas to %s value:(%s) exception(%s)"%(key,value,e))
                if key in ("dateCreated"):
                    value = value.strftime(self.getConfig(key+"_format","%Y-%m-%d %H:%M:%S"))
                if key in ("datePublished","dateUpdated"):
                    value = value.strftime(self.getConfig(key+"_format","%Y-%m-%d"))
                if isinstance(value, (datetime.date, datetime.datetime, datetime.time)) and self.hasConfig(key+"_format"):
                    # logger.info("DATE: %s"%key)
                    value = value.strftime(self.getConfig(key+"_format"))
                if key == "title" and (self.chapter_first or self.chapter_last) and self.getConfig("title_chapter_range_pattern"):
                    first = self.chapter_first or "1"
                    last = self.chapter_last or self.getMetadata("numChapters")
                    templ = string.Template(self.getConfig("title_chapter_range_pattern"))
                    value = templ.substitute({'title':value,
                                              'first':commaGroups(first),
                                              'last':commaGroups(last)})

            if doreplacements:
                value=self.doReplacements(value,key)
            if removeallentities and value != None:
                value = removeAllEntities(value)
        else: #if self.getConfig("default_value_"+key):
            value = self.getConfig("default_value_"+key)

        # save a cached value to speed processing
        if key not in self.processed_metadata_cache:
            self.processed_metadata_cache[key] = {}
        self.processed_metadata_cache[key][(removeallentities,doreplacements)] = value

        return value

    def getAllMetadata(self,
                       removeallentities=False,
                       doreplacements=True,
                       keeplists=False):
        '''
        All single value *and* list value metadata as strings (unless
        keeplists=True, then keep lists).
        '''
        allmetadata = {}

        # special handling for authors/authorUrls
        linkhtml="<a class='%slink' href='%s'>%s</a>"
        if self.isList('author'): # more than one author, assume multiple authorUrl too.
            htmllist=[]
            for i, v in enumerate(self.getList('author')):
                if len(self.getList('authorUrl')) <= i:
                    aurl = None
                else:
                    aurl = self.getList('authorUrl')[i]
                auth = v
                # make sure doreplacements & removeallentities are honored.
                if doreplacements:
                    aurl=self.doReplacements(aurl,'authorUrl')
                    auth=self.doReplacements(auth,'author')
                if removeallentities:
                    aurl=removeAllEntities(aurl)
                    auth=removeAllEntities(auth)

                htmllist.append(linkhtml%('author',aurl,auth))
            self.setMetadata('authorHTML',self.join_list("join_string_authorHTML",htmllist))
        else:
            self.setMetadata('authorHTML',linkhtml%('author',self.getMetadata('authorUrl', removeallentities, doreplacements),
                                                    self.getMetadata('author', removeallentities, doreplacements)))

        self.setMetadata('titleHTML',linkhtml%('title',
                                               self.getMetadata('storyUrl', removeallentities, doreplacements),
                                               self.getMetadata('title', removeallentities, doreplacements)))

        self.extendList("extratags",self.getConfigList("extratags"))

        if self.getMetadataRaw('seriesUrl'):
            self.setMetadata('seriesHTML',linkhtml%('series',
                                                    self.getMetadata('seriesUrl', removeallentities, doreplacements),
                                                    self.getMetadata('series', removeallentities, doreplacements)))
        elif self.getMetadataRaw('series'):
            self.setMetadata('seriesHTML',self.getMetadataRaw('series'))

        # logger.debug("make_linkhtml_entries:%s"%self.getConfig('make_linkhtml_entries'))
        for k in self.getConfigList('make_linkhtml_entries'):
            # Assuming list, because it has to be site specific and
            # they are all lists.  Bail if kUrl list not the same
            # length.
            # logger.debug("\nk:%s\nlist:%s\nlistURL:%s"%(k,self.getList(k),self.getList(k+'Url')))
            if len(self.getList(k+'Url')) != len(self.getList(k)):
                continue
            htmllist=[]
            for i, v in enumerate(self.getList(k)):
                url = self.getList(k+'Url')[i]
                # make sure doreplacements & removeallentities are honored.
                if doreplacements:
                    url=self.doReplacements(url,k+'Url')
                    v=self.doReplacements(v,k)
                if removeallentities:
                    url=removeAllEntities(url)
                    v=removeAllEntities(v)

                htmllist.append(linkhtml%(k,url,v))
            # join_string = self.getConfig("join_string_"+k+"HTML",u", ").replace(SPACE_REPLACE,' ')
            self.setMetadata(k+'HTML',self.join_list("join_string_"+k+"HTML",htmllist))

        for k in self.getValidMetaList():
            if self.isList(k) and keeplists:
                allmetadata[k] = self.getList(k, removeallentities, doreplacements)
            else:
                allmetadata[k] = self.getMetadata(k, removeallentities, doreplacements)

        return allmetadata

    def get_sanitized_description(self):
        '''
        For calibre version so this code can be consolidated between
        fff_plugin.py and jobs.py
        '''
        orig = description = self.getMetadata("description")
        # logger.debug("description:%s"%description)
        if not description:
            description = ''
        else:
            if not self.getConfig('keep_summary_html'):
                ## because of the html->MD text->html dance, text only
                ## (or MD/MD-like) descs come out better.
                description = sanitize_comments_html(description)
                # logger.debug("desc using sanitize_comments_html")
        # if orig != description:
        #     logger.debug("\nchanged description\n%s\n%s"%(orig,description))
        return description

    # just for less clutter in adapters.
    def extendList(self,listname,l):
        for v in l:
            self.addToList(listname,v.strip())

    def addToList(self,listname,value,condremoveentities=True,clear=False):
        if listname in self.processed_metadata_list_cache:
            del self.processed_metadata_list_cache[listname]
        if value==None:
            return
        if condremoveentities:
            value = conditionalRemoveEntities(value)
        if clear or not self.isList(listname) or not listname in self.metadata:
            # Calling addToList to a non-list meta will overwrite it.
            self.metadata[listname]=[]
        # prevent duplicates.
        if not value in self.metadata[listname]:
            self.metadata[listname].append(value)

    def isList(self,listname):
        'Everything set with an include_in_* is considered a list.'
        return self.isListType(listname) or \
            ( self.isValidMetaEntry(listname) and self.metadata.has_key(listname) \
                  and isinstance(self.metadata[listname],list) )

    def getList(self,listname,
                removeallentities=False,
                doreplacements=True,
                includelist=[],
                skip_cache=False):
        #print("getList(%s,%s)"%(listname,includelist))
        retlist = []

        # check for a cached value to speed processing
        if not skip_cache and listname in self.processed_metadata_list_cache \
                and (removeallentities,doreplacements) in self.processed_metadata_list_cache[listname]:
            return self.processed_metadata_list_cache[listname][(removeallentities,doreplacements)]

        if not self.isValidMetaEntry(listname):
            retlist = []
        else:
            # includelist prevents infinite recursion of include_in_'s
            if self.hasConfig("include_in_"+listname) and listname not in includelist:
                for k in self.getConfigList("include_in_"+listname):
                    ldorepl = doreplacements
                    if k.endswith('.NOREPL'):
                        k = k[:-len('.NOREPL')]
                        ldorepl = False
                    retlist.extend(self.getList(k,removeallentities=False,
                                                doreplacements=ldorepl,includelist=includelist+[listname],
                                                skip_cache=True))
            else:

                if not self.isList(listname):
                    retlist = [self.getMetadata(listname,removeallentities=False,
                                                doreplacements=doreplacements)]
                else:
                    retlist = self.getMetadataRaw(listname)
                    if retlist is None:
                        retlist = []

            # reorder ships so b/a and c/b/a become a/b and a/b/c.  Only on '/',
            # use replace_metadata to change separator first if needed.
            # ships=>[ ]*(/|&amp;|&)[ ]*=>/
            if listname == 'ships' and self.getConfig('sort_ships') and doreplacements and retlist:
                # retlist = [ '/'.join(sorted(x.split('/'))) for x in retlist ]
                ## empty default of /=>/
                sort_ships_splits = self.getConfig('sort_ships_splits',"/=>/")

                for line in sort_ships_splits.splitlines():
                    if line:
                        ## logger.debug("sort_ships_splits:%s"%line)
                        ## logger.debug(retlist)
                        (splitre,splitmerge) = line.split("=>")
                        splitmerge = splitmerge.replace(SPACE_REPLACE,' ')
                        newretlist = []
                        for x in retlist:
                            curlist = []
                            for y in re.split(splitre,x):
                                ## logger.debug("x:(%s) y:(%s)"%(x,y))
                                ## for SPLIT_META(\,)
                                if x != y and doreplacements: # doreplacements always true here (currently)
                                    y = self.doReplacements(y,'ships_CHARS',return_list=True)
                                else:
                                    ## needs to be a list to extend curlist.
                                    y=[x]
                                if y[0]: ## skip if empty
                                    curlist.extend(y)
                                ## logger.debug("curlist:%s"%(curlist,))
                            newretlist.append( splitmerge.join(sorted(curlist)) )

                        retlist = newretlist
                        ## logger.debug(retlist)

            if retlist:
                if doreplacements:
                    newretlist = []
                    for val in retlist:
                        newretlist.extend(self.doReplacements(val,listname,return_list=True))
                    retlist = newretlist

                if removeallentities:
                    retlist = map(removeAllEntities,retlist)

                retlist = filter( lambda x : x!=None and x!='' ,retlist)

            if listname == 'genre' and self.getConfig('add_genre_when_multi_category') and len(self.getList('category',
                                                                                                            removeallentities=False,
                                                                                                            # to avoid inf loops if genre/cat substs
                                                                                                            doreplacements=False
                                                                                                            )) > 1:
                retlist.append(self.getConfig('add_genre_when_multi_category'))

            if retlist:
                if listname in ('author','authorUrl','authorId') or self.getConfig('keep_in_order_'+listname):
                    # need to retain order for author & authorUrl so the
                    # two match up.
                    retlist = unique_list(retlist)
                else:
                    # remove dups and sort.
                    retlist = sorted(list(set(retlist)))
            else:
                retlist = []

        if not skip_cache:
            if listname not in self.processed_metadata_list_cache:
                self.processed_metadata_list_cache[listname] = {}
            self.processed_metadata_list_cache[listname][(removeallentities,doreplacements)] = retlist

        return retlist

    def getSubjectTags(self, removeallentities=False):
        # set to avoid duplicates subject tags.
        subjectset = set()

        tags_list = self.getConfigList("include_subject_tags") + self.getConfigList("extra_subject_tags")

        # metadata all go into dc:subject tags, but only if they are configured.
        for (name,value) in self.getAllMetadata(removeallentities=removeallentities,keeplists=True).iteritems():
            if name+'.SPLIT' in tags_list:
                flist=[]
                if isinstance(value,list):
                    for tag in value:
                        flist.extend(tag.split(','))
                else:
                    flist.extend(value)
                for tag in flist:
                    subjectset.add(tag)
            elif name in tags_list:
                if isinstance(value,list):
                    for tag in value:
                        subjectset.add(tag)
                else:
                    subjectset.add(value)

        if None in subjectset:
            subjectset.remove(None)
        if '' in subjectset:
            subjectset.remove('')

        return list(subjectset | set(self.getConfigList("extratags")))

    def addChapter(self, url, title, html, newchap=False):
        # logger.debug("addChapter(%s,%s)"%(url,newchap))
        if self.getConfig('strip_chapter_numbers') and \
                self.getConfig('chapter_title_strip_pattern'):
            title = re.sub(self.getConfig('chapter_title_strip_pattern'),"",title)
        self.chapters.append( Chapter(url,title,html,title,title,newchap) )

    def getChapters(self,fortoc=False):
        "Chapters will be Chapter namedtuples"
        retval = []

        ## only add numbers if more than one chapter.  Ditto (new) marks.
        if len(self.chapters) > 1:
            addnums = ( self.getConfig('add_chapter_numbers') == "true"
                        or (self.getConfig('add_chapter_numbers') == "toconly" and fortoc) )

            marknew = self.getConfig('mark_new_chapters')=='true'

            defpattern = self.getConfig('chapter_title_def_pattern','${title}') # default val in case of missing defaults.ini
            if addnums and marknew:
                pattern = self.getConfig('chapter_title_add_pattern')
                newpattern = self.getConfig('chapter_title_addnew_pattern')
            elif addnums:
                pattern = self.getConfig('chapter_title_add_pattern')
                newpattern = pattern
            elif marknew:
                pattern = defpattern
                newpattern = self.getConfig('chapter_title_new_pattern')
            else:
                pattern = defpattern
                newpattern = pattern

            if self.getConfig('add_chapter_numbers') in ["true","toconly"]:
                tocpattern = self.getConfig('chapter_title_add_pattern')
            else:
                tocpattern = defpattern

            # logger.debug("Patterns: (%s)(%s)"%(pattern,newpattern))
            templ = string.Template(pattern)
            newtempl = string.Template(newpattern)
            toctempl = string.Template(tocpattern)

            for index, chap in enumerate(self.chapters):
                if chap.new:
                    usetempl = newtempl
                else:
                    usetempl = templ
                # logger.debug("chap.url, chap.new: (%s)(%s)"%(chap.url,chap.new))
                retval.append( Chapter(chap.url,
                                       # 'new'
                                       usetempl.substitute({'index':index+1,'title':chap.title}),
                                       chap.html,
                                       # 'orig'
                                       templ.substitute({'index':index+1,'title':chap.title}),
                                       # 'toc'
                                       toctempl.substitute({'index':index+1,'title':chap.title}),
                                       chap.new) )
        else:
            retval = self.chapters

        return retval

    def get_filename_safe_metadata(self,pattern=None):
        origvalues = self.getAllMetadata()
        values={}
        if not pattern:
            pattern = re_compile(self.getConfig("output_filename_safepattern",
                                                r"(^\.|/\.|[^a-zA-Z0-9_\. \[\]\(\)&'-]+)"),
                                 "output_filename_safepattern")
        for k in origvalues.keys():
            if k == 'formatext': # don't do file extension--we set it anyway.
                values[k]=self.getMetadata(k)
            else:
                values[k]=re.sub(pattern,'_', removeAllEntities(self.getMetadata(k)))
        return values

    def formatFileName(self,template,allowunsafefilename=True):
        # fall back default:
        if not template:
            template="${title}-${siteabbrev}_${storyId}${formatext}"

        if allowunsafefilename:
            values = self.getAllMetadata()
        else:
            values = self.get_filename_safe_metadata()

        return string.Template(template).substitute(values).encode('utf8')

    # pass fetch in from adapter in case we need the cookies collected
    # as well as it's a base_story class method.
    def addImgUrl(self,parenturl,url,fetch,cover=False,coverexclusion=None):
        # otherwise it saves the image in the epub even though it
        # isn't used anywhere.
        if cover and self.getConfig('never_make_cover'):
            return (None,None)

        url = url.strip() # ran across an image with a space in the
                          # src. Browser handled it, so we'd better, too.

        # appengine (web version) isn't allowed to do images--just
        # gets too big too fast and breaks things.
        if is_appengine:
            return (None,None)

        ## Mistakenly ended up with some // in image urls, like:
        ## https://forums.spacebattles.com//styles/default/xenforo/clear.png
        ## Removing one /, but not ://
        if not url.startswith("file"): # keep file:///
            url = re.sub(r"([^:])//",r"\1/",url)
        if url.startswith("http") or url.startswith("file") or parenturl == None:
            imgurl = url
        else:
            parsedUrl = urlparse.urlparse(parenturl)
            if url.startswith("//") :
                imgurl = urlparse.urlunparse(
                    (parsedUrl.scheme,
                     '',
                     url,
                     '','',''))
            elif url.startswith("/") :
                imgurl = urlparse.urlunparse(
                    (parsedUrl.scheme,
                     parsedUrl.netloc,
                     url,
                     '','',''))
            else:
                toppath=""
                if parsedUrl.path.endswith("/"):
                    toppath = parsedUrl.path
                else:
                    toppath = parsedUrl.path[:parsedUrl.path.rindex('/')+1]
                imgurl = urlparse.urlunparse(
                    (parsedUrl.scheme,
                     parsedUrl.netloc,
                     toppath + url,
                     '','',''))
                # logger.debug("\n===========\nparsedUrl.path:%s\ntoppath:%s\nimgurl:%s\n\n"%(parsedUrl.path,toppath,imgurl))

        # apply coverexclusion to explicit covers, too.  Primarily for ffnet imageu.
        #print("[[[[[\n\n %s %s \n\n]]]]]]]"%(imgurl,coverexclusion))
        if cover and coverexclusion and re.search(coverexclusion,imgurl):
            return (None,None)

        prefix='ffdl'
        if imgurl not in self.imgurls:

            try:
                if imgurl.endswith('failedtoload'):
                    return ("failedtoload","failedtoload")

                parsedUrl = urlparse.urlparse(imgurl)
                if self.getConfig('no_image_processing'):
                    (data,ext,mime) = no_convert_image(imgurl,
                                                       fetch(imgurl,referer=parenturl))
                else:
                    try:
                        sizes = [ int(x) for x in self.getConfigList('image_max_size') ]
                    except Exception, e:
                        raise exceptions.FailedToDownload("Failed to parse image_max_size from personal.ini:%s\nException: %s"%(self.getConfigList('image_max_size'),e))
                    grayscale = self.getConfig('grayscale_images')
                    imgtype = self.getConfig('convert_images_to')
                    if not imgtype:
                        imgtype = "jpg"
                    removetrans = self.getConfig('remove_transparency')
                    removetrans = removetrans or grayscale or imgtype=="jpg"
                    if 'ffdl-' in imgurl:
                        raise exceptions.FailedToDownload("ffdl image is internal only...")
                    (data,ext,mime) = convert_image(imgurl,
                                                    fetch(imgurl,referer=parenturl),
                                                    sizes,
                                                    grayscale,
                                                    removetrans,
                                                    imgtype,
                                                    background="#"+self.getConfig('background_color'))
            except Exception, e:
                logger.info("Failed to load or convert image, \nparent:%s\nskipping:%s\nException: %s"%(parenturl,imgurl,e))
                return ("failedtoload","failedtoload")

            # explicit cover, make the first image.
            if cover:
                if len(self.imgtuples) > 0 and 'cover' in self.imgtuples[0]['newsrc']:
                    # remove existing cover, if there is one.
                    del self.imgurls[0]
                    del self.imgtuples[0]
                self.imgurls.insert(0,imgurl)
                newsrc = "images/cover.%s"%ext
                self.cover=newsrc
                self.setMetadata('cover_image','specific')
                self.imgtuples.insert(0,{'newsrc':newsrc,'mime':mime,'data':data})
            else:
                self.imgurls.append(imgurl)
                # First image, copy not link because calibre will replace with it's cover.
                # Only if: No cover already AND
                #          make_firstimage_cover AND
                #          NOT never_make_cover AND
                #          either no coverexclusion OR coverexclusion doesn't match
                if self.cover == None and \
                        self.getConfig('make_firstimage_cover') and \
                        not self.getConfig('never_make_cover') and \
                        not (coverexclusion and re.search(coverexclusion,imgurl)):
                    newsrc = "images/cover.%s"%ext
                    self.cover=newsrc
                    self.setMetadata('cover_image','first')
                    self.imgtuples.append({'newsrc':newsrc,'mime':mime,'data':data})
                    self.imgurls.append(imgurl)

                newsrc = "images/%s-%s.%s"%(
                    prefix,
                    self.imgurls.index(imgurl),
                    ext)
                self.imgtuples.append({'newsrc':newsrc,'mime':mime,'data':data})

            #logger.debug("\nimgurl:%s\nnewsrc:%s\nimage size:%d\n"%(imgurl,newsrc,len(data)))
        else:
            newsrc = self.imgtuples[self.imgurls.index(imgurl)]['newsrc']

        #print("===============\n%s\nimg url:%s\n============"%(newsrc,self.imgurls[-1]))

        return (newsrc, imgurl)

    def getImgUrls(self):
        retlist = []
        for i, url in enumerate(self.imgurls):
            #parsedUrl = urlparse.urlparse(url)
            retlist.append(self.imgtuples[i])
        return retlist

    def __str__(self):
        return "Metadata: " +unicode(self.metadata)

def commaGroups(s):
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

# http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
def unique_list(seq):
    seen = set()
    seen_add = seen.add
    try:
        return [x for x in seq if not (x in seen or seen_add(x))]
    except:
        logger.debug("unique_list exception seq:%s"%seq)
        raise
