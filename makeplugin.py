#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2018, Jim Miller

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
    filename="FanFicFare.zip"
    exclude=['*.pyc','*~','*.xcf','*[0-9].png','*.po','*.pot','*default.mo','*Thumbs.db']
    
    os.chdir('calibre-plugin')
    files=['plugin-defaults.ini','plugin-example.ini','about.html',
           'images','translations']
    files.extend(glob('*.py'))
    files.extend(glob('plugin-import-name-*.txt'))
    # 'w' for overwrite
    createZipFile("../"+filename,"w",
                  files,
                  exclude=exclude)

    os.chdir('../included_dependencies')
    files=['bs4','chardet','html2text','soupsieve','backports',
           'cloudscraper','requests','requests_toolbelt','urllib3',
           'certifi','idna']
    ## Kept only for v2.85.1 support now.
    createZipFile("../"+filename,"a",
                  files,
                  exclude=exclude)

    os.chdir('..')
    # 'a' for append
    files=['fanficfare']
    createZipFile(filename,"a",
                  files,
                  exclude=exclude)

