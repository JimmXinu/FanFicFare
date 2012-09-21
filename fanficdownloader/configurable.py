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

import ConfigParser

# All of the writers(epub,html,txt) and adapters(ffnet,twlt,etc)
# inherit from Configurable.  The config file(s) uses ini format:
# [sections] with key:value settings.
#
# [defaults]
# titlepage_entries: category,genre, status
# [www.whofic.com]
# titlepage_entries: category,genre, status,dateUpdated,rating
# [epub]
# titlepage_entries: category,genre, status,datePublished,dateUpdated,dateCreated
# [www.whofic.com:epub]
# titlepage_entries: category,genre, status,datePublished
# [overrides]
# titlepage_entries: category

class Configuration(ConfigParser.SafeConfigParser):

    def __init__(self, site, fileform):
        ConfigParser.SafeConfigParser.__init__(self)
        self.sectionslist = ['defaults']
        self.addConfigSection(site)
        if fileform:
            self.addConfigSection(fileform)
            self.addConfigSection(site+":"+fileform)
        self.addConfigSection("overrides")
        
        self.validEntries = [
            'category',
            'genre',
            'language',
            'characters',
            'ships',
            'series',
            'status',
            'datePublished',
            'dateUpdated',
            'dateCreated',
            'rating',
            'warnings',
            'numChapters',
            'numWords',
            'site',
            'storyId',
            'authorId',
            'extratags',
            'title',
            'storyUrl',
            'description',
            'author',
            'authorUrl',
            'formatname',
            'formatext',
            'siteabbrev',
            'version',
            # internal stuff.
            'langcode',
            'output_css',
            'authorHTML'
            ]
        
    def addConfigSection(self,section):
        self.sectionslist.insert(0,section)

    def isValidMetaEntry(self, key):
        return key in self.getValidMetaList()

    def getValidMetaList(self):
        vl = []
        vl.extend(self.validEntries)
        vl.extend(self.getConfigList("extra_valid_entries"))
        return vl

    def hasConfig(self, key):
        for section in self.sectionslist:
            try:
                self.get(section,key)
                #print("found %s in section [%s]"%(key,section))
                return True
            except:
                pass

        return False
        
    def getConfig(self, key, default=""):
        val = default
        for section in self.sectionslist:
            try:
                val = self.get(section,key)
                if val and val.lower() == "false":
                    val = False
                #print "getConfig(%s)=[%s]%s" % (key,section,val)
                return val
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError), e:
                pass

        return val

    # split and strip each.
    def getConfigList(self, key):
        vlist = self.getConfig(key).split(',')
        vlist = [ v.strip() for v in vlist ]
        #print "vlist("+key+"):"+str(vlist)
        return vlist        

# extended by adapter, writer and story for ease of calling configuration.
class Configurable(object):

    def __init__(self, configuration):
        self.configuration = configuration

    def isValidMetaEntry(self, key):
        return self.configuration.isValidMetaEntry(key)

    def getValidMetaList(self):
        return self.configuration.getValidMetaList()
    
    def hasConfig(self, key):
        return self.configuration.hasConfig(key)
        
    def getConfig(self, key, default=""):
        return self.configuration.getConfig(key)

    def getConfigList(self, key):
        return self.configuration.getConfigList(key)
        
