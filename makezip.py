#!/usr/bin/python
# -*- coding: utf-8 -*-

# epubmerge.py 1.0

# Copyright 2011, Jim Miller

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, zipfile, sys
from glob import glob

def addFolderToZip(myZipFile,folder,exclude=[]):
    folder = folder.encode('ascii') #convert path to ascii for ZipFile Method
    excludelist=[]
    for ex in exclude:
        excludelist.extend(glob(folder+"/"+ex))
    for file in glob(folder+"/*"):
        if file in excludelist:
            continue
        if os.path.isfile(file):
            #print file
            myZipFile.write(file, file, zipfile.ZIP_DEFLATED)
        elif os.path.isdir(file):
            addFolderToZip(myZipFile,file,exclude=exclude)

def createZipFile(filename,mode,files,exclude=[]):
    myZipFile = zipfile.ZipFile( filename, mode ) # Open the zip file for writing
    excludelist=[]
    for ex in exclude:
        excludelist.extend(glob(ex))
    for file in files:
        if file in excludelist:
            continue
        file = file.encode('ascii') #convert path to ascii for ZipFile Method
        if os.path.isfile(file):
            (filepath, filename) = os.path.split(file)
            #print file
            myZipFile.write( file, filename, zipfile.ZIP_DEFLATED )
        if os.path.isdir(file):
            addFolderToZip(myZipFile,file,exclude=exclude)
    myZipFile.close()
    return (1,filename)

