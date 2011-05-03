# -*- coding: utf-8 -*-

from htmlcleanup import conditionalRemoveEntities

class Story:
    
    def __init__(self):
        self.metadata = {}
        self.chapters = [] # chapters will be tuples of (title,html)
        self.listables = {} # some items (extratags, category, warnings & genres) are also kept as lists.

    def setMetadata(self, key, value):
        self.metadata[key]=conditionalRemoveEntities(value)

    def getMetadataRaw(self,key):
        if self.metadata.has_key(key):
            return self.metadata[key]
        
    def getMetadata(self, key):
        if self.getLists().has_key(key):
            return ', '.join(self.getList(key))
        if self.metadata.has_key(key):
            value = self.metadata[key]
            if value:
                if key == "numWords":
                    value = commaGroups(value)
                if key == "dateCreated":
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                if key == "datePublished" or key == "dateUpdated":
                 value = value.strftime("%Y-%m-%d")
            return value

    def addToList(self,listname,value):
        if not self.listables.has_key(listname):
            self.listables[listname]=[]
        # prevent duplicates.
        if not value in self.listables[listname]:
            self.listables[listname].append(conditionalRemoveEntities(value))

    def getList(self,listname):
        if not self.listables.has_key(listname):
            return []
        return self.listables[listname]

    def getLists(self):
        return self.listables
    
    def addChapter(self, title, html):
        self.chapters.append( (title,html) )

    def getChapters(self):
        "Chapters will be tuples of (title,html)"
        return self.chapters
    
    def __str__(self):
        return "Metadata: " +str(self.metadata) + "\nListables: " +str(self.listables) #+ "\nChapters: "+str(self.chapters)

def commaGroups(s):
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

