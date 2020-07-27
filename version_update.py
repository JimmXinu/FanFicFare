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

import codecs, sys, re

from tempfile import mkstemp
from os import rename, close, unlink

#print(sys.argv[1:])

## Files that contain version numbers that will need to be updated.
version_files = [
    # 'version_test.sml',
    # 'version_test.txt',
    'setup.py',
    'calibre-plugin/__init__.py',
    # 'webservice/app.yaml',
    'fanficfare/cli.py',
    ]

## save version from this file for index.html link.
# save_file='version_test.txt'
save_file='webservice/app.yaml'
saved_version = None

def main(args):
   ## major minor micro
    '''
__version__ = (2, 3, 6)
    version="2.3.6",
version: 2-3-06a
version="2.3.6"
'''
    version_re = \
        r'^(?P<prefix>[ ]*(__)?)version(?P<infix>(__)?[ =:"\\(]+)' \
        r'(?P<major>[0-9]+)(?P<dot1>[, \\.-]+)' \
        r'(?P<minor>[0-9]+)(?P<dot2>[, \\.-]+)' \
        r'(?P<micro>[0-9]+[a-z]?)(?P<suffix>[",\\)]*\r?\n)$'

    version_subs = r'\g<prefix>version\g<infix>%s\g<dot1>%s\g<dot2>%s\g<suffix>' % tuple(args)
    
    do_loop(version_files, version_re, version_subs)

    index_files = []
    # index_files = ['webservice/index.html']
    # if saved_version:
    #     ## only do major/minor, always leave micro 0 in index.html.
    #     index_re = 'https://([0-9-]+[a-z]?)\\.fanficfare\\.appspot\\.com'
    #     index_subs = 'https://%s-%s-0.fanficfare.appspot.com'%saved_version[0:2]
    #     do_loop(index_files, index_re, index_subs)

    release = 'Release'
    if int(args[-1]) > 0:
        release = 'Test'
    print('\ngit add %s'%(" ".join(version_files+index_files)))
    print('git commit -m "Bump %s Version %s"'%(release,'.'.join(args)))

def do_loop(files, pattern, substring):
    global saved_version
    for source_file_path in files:
        print("src:"+source_file_path)
        fh, target_file_path = mkstemp()
        with codecs.open(target_file_path, 'w', 'utf-8') as target_file:
            with codecs.open(source_file_path, 'r', 'utf-8') as source_file:
                for line in source_file:
                    repline = re.sub(pattern, substring, line)
                    if line != repline and source_file_path == save_file:
                        m = re.match(pattern,line)
                        saved_version = (m.group('major'),m.group('minor'),m.group('micro'))
                        print("<-%s->%s"%(line,repline))
                    target_file.write(repline)
        close(fh)
        unlink(source_file_path)
        rename(target_file_path,source_file_path)

if __name__ == '__main__':
    args = sys.argv[1:]
    try:
        if len(args) != 3:
            raise Exception()
        [int(x) for x in args]
    except:
        print("Requires exactly 3 numeric args: major minor micro")
        exit()
    main(args)
#    print(saved_version)
