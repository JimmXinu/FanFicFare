# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team
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
import urlparse
from math import floor

from htmlcleanup import conditionalRemoveEntities, removeAllEntities

# Create convert_image method depending on which graphics lib we can
# load.  Preferred: calibre, PIL, none
try:
    from calibre.utils.magick import Image

    def convert_image(url,data,sizes,grayscale):
        export = False
        img = Image()
        img.load(data)
        
        owidth, oheight = img.size
        nwidth, nheight = sizes
        scaled, nwidth, nheight = fit_image(owidth, oheight, nwidth, nheight)
        if scaled:
            img.size = (nwidth, nheight)
            export = True
            
        if grayscale and img.type != "GrayscaleType":
            img.type = "GrayscaleType"
            export = True

        if normalize_format_name(img.format) != "jpg":
            export = True

        if export:
            return (img.export('JPG'),'jpg','image/jpeg')
        else:
            print("image used unchanged")
            return (data,'jpg','image/jpeg')
        
except:

    # No calibre routines, try for PIL for CLI.
    try:
        import Image
        from StringIO import StringIO
        def convert_image(url,data,sizes,grayscale):
            
            export = False
            img = Image.open(StringIO(data))
            
            owidth, oheight = img.size
            nwidth, nheight = sizes
            scaled, nwidth, nheight = fit_image(owidth, oheight, nwidth, nheight)
            if scaled:
                img = img.resize((nwidth, nheight),Image.ANTIALIAS)
                export = True
                
            if grayscale and img.mode != "L":
                img = img.convert("L")
                export = True

            if normalize_format_name(img.format) != "jpg":
                export = True

            if export:
                outsio = StringIO()
                img.save(outsio,'JPEG')
                return (outsio.getvalue(),'jpg','image/jpeg')
            else:
                print("image used unchanged")
                return (data,'jpg','image/jpeg')
        
    except:

        # No calibre or PIL, simple pass through with mimetype.
        imagetypes = {
            'jpg':'image/jpeg',
            'jpeg':'image/jpeg',
            'png':'image/png',
            'gif':'image/gif',
            'svg':'image/svg+xml',
            }

        def convert_image(url,data,sizes,grayscale):
            ext=url[url.rfind('.')+1:].lower()
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
    }

class Story:
    
    def __init__(self):
        try:
            self.metadata = {'version':os.environ['CURRENT_VERSION_ID']}
        except:
            self.metadata = {'version':'4.4'}
        self.replacements = []
        self.chapters = [] # chapters will be tuples of (title,html)
        self.imgurls = []
        self.imgtuples = []
        self.listables = {} # some items (extratags, category, warnings & genres) are also kept as lists.
        self.cover=None

    def setMetadata(self, key, value):
        ## still keeps &lt; &lt; and &amp;
        self.metadata[key]=conditionalRemoveEntities(value)
        if key == "language":
            try:
                self.metadata['langcode'] = langs[self.metadata[key]]
            except:
                self.metadata['langcode'] = 'en'

    def getMetadataRaw(self,key):
        if self.metadata.has_key(key):
            return self.metadata[key]

    def doReplacments(self,value):
        for (p,v) in self.replacements:
            if (isinstance(value,str) or isinstance(value,unicode)) and re.match(p,value):
                value = re.sub(p,v,value)                
        return value;
        
    def getMetadata(self, key, removeallentities=False):
        value = None
        if self.getLists().has_key(key):
            value = ', '.join(self.getList(key))
        if self.metadata.has_key(key):
            value = self.metadata[key]
            if value:
                if key == "numWords":
                    value = commaGroups(value)
                if key == "dateCreated":
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                if key == "datePublished" or key == "dateUpdated":
                 value = value.strftime("%Y-%m-%d")

        value=self.doReplacments(value)
        if removeallentities and value != None:
            return removeAllEntities(value)
        else:
            return value

    def getAllMetadata(self, removeallentities=False):
        '''
        All single value *and* list value metadata as strings.
        '''
        allmetadata = {}
        for k in self.metadata.keys():
            allmetadata[k] = self.getMetadata(k, removeallentities)
        for l in self.listables.keys():
            allmetadata[l] = self.getMetadata(l, removeallentities)

        return allmetadata
        
    def addToList(self,listname,value):
        if value==None:
            return
        value = conditionalRemoveEntities(value)
        if not self.listables.has_key(listname):
            self.listables[listname]=[]
        # prevent duplicates.
        if not value in self.listables[listname]:
            self.listables[listname].append(value)

    def getList(self,listname):
        if not self.listables.has_key(listname):
            return []
        return filter( lambda x : x!=None and x!='' ,
                       map(self.doReplacments,self.listables[listname]) )

    def getLists(self):
        lsts = {}
        for ln in self.listables.keys():
            lsts[ln] = self.getList(ln)
        return lsts
    
    def addChapter(self, title, html):
        self.chapters.append( (title,html) )

    def getChapters(self):
        "Chapters will be tuples of (title,html)"
        return self.chapters

    # pass fetch in from adapter in case we need the cookies collected
    # as well as it's a base_story class method.
    def addImgUrl(self,configurable,parenturl,url,fetch,cover=False):

        # appengine (web version) isn't allowed to do images--just
        # gets too big too fast and breaks things.
        if is_appengine:
            return
        
        if url.startswith("http") or url.startswith("file") or parenturl == None:
            imgurl = url
        else:
            parsedUrl = urlparse.urlparse(parenturl)
            if url.startswith("/") :
                imgurl = urlparse.urlunparse(
                    (parsedUrl.scheme,
                     parsedUrl.netloc,
                     url,
                     '','',''))
            else:
                imgurl = urlparse.urlunparse(
                    (parsedUrl.scheme,
                     parsedUrl.netloc,
                     parsedUrl.path + url,
                     '','',''))

        prefix='ffdl'
        if imgurl not in self.imgurls:
            parsedUrl = urlparse.urlparse(imgurl)
            sizes = [ int(x) for x in configurable.getConfigList('image_max_size') ]
            try:
                (data,ext,mime) = convert_image(imgurl,
                                                fetch(imgurl),
                                                sizes,
                                                configurable.getConfig('grayscale_images'))
            except Exception, e:
                print("Failed to load image, skipping:\n%s\nException: %s"%(imgurl,e))
                return "failedtoload"
            
            # explicit cover, make the first image.
            if cover and not configurable.getConfig('never_make_cover'):
                if len(self.imgtuples) > 0 and 'cover' in self.imgtuples[0]['newsrc']:
                    # remove existing cover, if there is one.
                    del self.imgurls[0]
                    del self.imgtuples[0]
                self.imgurls.insert(0,imgurl)
                newsrc = "images/cover.%s"%ext
                self.cover=newsrc
                self.imgtuples.insert(0,{'newsrc':newsrc,'mime':mime,'data':data})
            else:
                self.imgurls.append(imgurl)
                # First image, copy not link because calibre will replace with it's cover.
                if len(self.imgurls)==1 and \
                        configurable.getConfig('make_firstimage_cover') and \
                        not configurable.getConfig('never_make_cover'):
                    newsrc = "images/cover.%s"%ext
                    self.cover=newsrc
                    self.imgtuples.append({'newsrc':newsrc,'mime':mime,'data':data})
                    self.imgurls.append(imgurl)
            
                newsrc = "images/%s-%s.%s"%(
                    prefix,
                    self.imgurls.index(imgurl),
                    ext)
                self.imgtuples.append({'newsrc':newsrc,'mime':mime,'data':data})
                
            print("\nimgurl:%s\nnewsrc:%s\nimage size:%d\n"%(imgurl,newsrc,len(data)))
        else:
            newsrc = self.imgtuples[self.imgurls.index(imgurl)]['newsrc']
            
        #print("===============\n%s\nimg url:%s\n============"%(newsrc,self.imgurls[-1]))
        
        return newsrc

    def getImgUrls(self):
        retlist = []
        for i, url in enumerate(self.imgurls):
            #parsedUrl = urlparse.urlparse(url)
            retlist.append(self.imgtuples[i])
        return retlist
    
    def __str__(self):
        return "Metadata: " +str(self.metadata) + "\nListables: " +str(self.listables) #+ "\nChapters: "+str(self.chapters)

    def setReplace(self,replace):
        for line in replace.splitlines():
            if "=>" in line:
                self.replacements.append(map( lambda x: x.strip(), line.split("=>") ))
    
def commaGroups(s):
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

