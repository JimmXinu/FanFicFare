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

import ConfigParser, re

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

        if site.startswith("www."):
            sitewith = site
            sitewithout = site.replace("www.","")
        else:
            sitewith = "www."+site
            sitewithout = site
        
        self.addConfigSection(sitewith)
        self.addConfigSection(sitewithout)
        if fileform:
            self.addConfigSection(fileform)
            self.addConfigSection(sitewith+":"+fileform)
            self.addConfigSection(sitewithout+":"+fileform)
        self.addConfigSection("overrides")
        
        self.validEntries = [
            'category',
            'genre',
            'language',
            'characters',
            'ships',
            'series',
            'seriesUrl',
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
            'authorHTML',
            'seriesHTML',
            'lastupdate'
            ]

    def addConfigSection(self,section):
        self.sectionslist.insert(0,section)

    def isValidMetaEntry(self, key):
        return key in self.getValidMetaList()

    def getValidMetaList(self):
        return self.validEntries + self.getConfigList("extra_valid_entries")

    # used by adapters & writers, non-convention naming style
    def hasConfig(self, key):
        return self.has_config(self.sectionslist, key)

    def has_config(self, sections, key):
        for section in sections:
            try:
                self.get(section,key)
                #print("found %s in section [%s]"%(key,section))
                return True
            except:
                try:
                    self.get(section,"add_to_"+key)
                    #print("found add_to_%s in section [%s]"%(key,section))
                    return True
                except:
                    pass

        return False

    # used by adapters & writers, non-convention naming style
    def getConfig(self, key, default=""):
        return self.get_config(self.sectionslist,key,default)
    
    def get_config(self, sections, key, default=""):        
        val = default
        for section in sections:
            try:
                val = self.get(section,key)
                if val and val.lower() == "false":
                    val = False
                #print "getConfig(%s)=[%s]%s" % (key,section,val)
                break
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError), e:
                pass

        for section in sections[::-1]:
            # 'martian smiley' [::-1] reverses list by slicing whole list with -1 step.
            try:
                val = val + self.get(section,"add_to_"+key)
                #print "getConfig(add_to_%s)=[%s]%s" % (key,section,val)
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError), e:
                pass
            
        return val

    # split and strip each.
    def get_config_list(self, sections, key):
        vlist = re.split(r'(?<!\\),',self.get_config(sections,key)) # don't split on \,
        vlist = filter( lambda x : x !='', [ v.strip().replace('\,',',') for v in vlist ])
        #print "vlist("+key+"):"+str(vlist)
        return vlist        
    
    # used by adapters & writers, non-convention naming style
    def getConfigList(self, key):
        return self.get_config_list(self.sectionslist, key)

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
        
    def has_config(self, sections, key):
        return self.configuration.has_config(sections, key)

    def getConfig(self, key, default=""):
        return self.configuration.getConfig(key,default)

    def get_config(self, sections, key, default=""):
        return self.configuration.get_config(sections,key,default)

    def getConfigList(self, key):
        return self.configuration.getConfigList(key)

    def get_config_list(self, sections, key):
        return self.configuration.get_config_list(sections,key)
