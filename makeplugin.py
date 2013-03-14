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

import os
from glob import glob

from makezip import createZipFile

if __name__=="__main__":
    filename="FanFictionDownLoader.zip"
    exclude=['*.pyc','*~','*.xcf','*[0-9].png']
    # from top dir. 'w' for overwrite
    createZipFile(filename,"w",
                  ['plugin-defaults.ini','plugin-example.ini','fanficdownloader','downloader.py','defaults.ini'],
                  exclude=exclude)
    #from calibre-plugin dir. 'a' for append
    os.chdir('calibre-plugin')
    files=['about.txt','images',]
    files.extend(glob('*.py'))
    files.extend(glob('plugin-import-name-*.txt'))
    createZipFile("../"+filename,"a",
                  files,exclude=exclude)
