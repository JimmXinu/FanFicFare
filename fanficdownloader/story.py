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

from htmlcleanup import conditionalRemoveEntities, removeAllEntities

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
            self.metadata = {'version':'4.3'}
        self.replacements = []
        self.chapters = [] # chapters will be tuples of (title,html)
        self.listables = {} # some items (extratags, category, warnings & genres) are also kept as lists.

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

