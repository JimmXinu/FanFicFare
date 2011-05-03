# -*- coding: utf-8 -*-

import ConfigParser

# All of the writers(epub,html,txt) and adapters(ffnet,twlt,etc)
# inherit from Configurable.  The config file(s) uses ini format:
# [sections] with key:value settings.
#
# There's a [defaults] section which is overriden by the writer's
# section [epub], which is overriden by the adapter's section for each
# site.
#
# [defaults]
# titlepage_entries: category,genre, status
# [epub]
# titlepage_entries: category,genre, status,datePublished,dateUpdated,dateCreated
# [www.whofic.com]
# titlepage_entries: category,genre, status,dateUpdated,rating

class Configurable(object):

    def __init__(self, config):
        self.config = config
        self.sectionslist = ['defaults']

    def addConfigSection(self,section):
        self.sectionslist.insert(0,section)

    def getConfig(self, key):
        val = ""
        for section in self.sectionslist:
            try:
                val = self.config.get(section,key)
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
        
