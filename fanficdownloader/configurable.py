# -*- coding: utf-8 -*-

# Copyright 2014 Fanficdownloader team
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
from ConfigParser import DEFAULTSECT, MissingSectionHeaderError, ParsingError

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

import adapters

class Configuration(ConfigParser.SafeConfigParser):

    def __init__(self, site, fileform):
        ConfigParser.SafeConfigParser.__init__(self)

        self.linenos=dict() # key by section or section,key -> lineno
        
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
        
        self.listTypeEntries = [
            'category',
            'genre',
            'characters',
            'ships',
            'warnings',
            'extratags',
            'author',
            'authorId',
            'authorUrl',
            'lastupdate',
            ]
        
        self.validEntries = self.listTypeEntries + [
            'series',
            'seriesUrl',
            'language',
            'status',
            'datePublished',
            'dateUpdated',
            'dateCreated',
            'rating',
            'numChapters',
            'numWords',
            'site',
            'storyId',
            'title',
            'storyUrl',
            'description',
            'formatname',
            'formatext',
            'siteabbrev',
            'version',
            # internal stuff.
            'authorHTML',
            'seriesHTML',
            'langcode',
            'output_css',
            ]

    def addConfigSection(self,section):
        self.sectionslist.insert(0,section)

    def isListType(self,key):
        return key in self.listTypeEntries or self.hasConfig("include_in_"+key)
        
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


    def test_config(self):
        errors=[]
        
        sites = adapters.getConfigSections()
        sitesections = ['defaults','overrides']
        for section in sites:
            sitesections.append(section)
            if section.startswith('www.'):
                # add w/o www if has www
                sitesections.append(section[4:])
            else:
                # add w/ www if doesn't www
                sitesections.append('www.%s'%section)
        
        allowedsections = []
        forms=['html','txt','epub','mobi']
        allowedsections.extend(forms)

        for section in sitesections:
            allowedsections.append(section)
            for f in forms:
                allowedsections.append('%s:%s'%(section,f))
        
        for section in self.sections():
            if section not in allowedsections and 'teststory:' not in section:
                errors.append((self.get_lineno(section),"Bad Section Name: %s"%section))
        
        return errors

    def get_lineno(self,section,key=None):
        if key:
            return self.linenos.get(section+','+key,None)
        else:
            return self.linenos.get(section,None)
    
    ## Copied from Python library so as to make it save linenos too.
    #
    # Regular expressions for parsing section headers and options.
    #
    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                        self.linenos[sectname]=lineno
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    if not e:
                        e = ParsingError(fpname)
                    e.append(lineno, u'(Line outside section) '+line)
                    #raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos-1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                        self.linenos[cursect['__name__']+','+optname]=lineno                        
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, line)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e
    
# extended by adapter, writer and story for ease of calling configuration.
class Configurable(object):

    def __init__(self, configuration):
        self.configuration = configuration

    def isListType(self,key):
        return self.configuration.isListType(key)

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
