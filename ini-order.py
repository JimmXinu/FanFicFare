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

import re
import sys
from io import open # so py2.7 has open with encoding param.

argv = sys.argv[1:]

sections = {}
cursectname = ""
cursectlines = []

with open(argv[0],"r", encoding="utf8") as infile:
    for line in infile:
        if re.match(r"^\[([^\]]+)\]$",line):
            sections[cursectname] = cursectlines
            cursectname = line.strip()
            cursectlines = [line]
        else:
            cursectlines.append(line)
    sections[cursectname] = cursectlines

leadsects = [
    "",
    "[defaults]",
    "[base_efiction]",
    "[base_xenforoforum]",
    "[base_xenforoforum:epub]",
    "[base_xenforo2forum]",
    "[base_xenforo2forum:epub]",
    "[epub]",
    "[html]",
    "[txt]",
    "[mobi]",
    "[test1.com]",
    "[test1.com:txt]",
    "[test1.com:html]",
    "[teststory:defaults]",
    "[teststory:1000]",
    "[overrides]",
    ]
followsects = [
    ]

with open(argv[1],"w", encoding="utf8") as outfile:
    kl = list(sections.keys())
    # to force [site:format] after [site]
    kl.sort(key=lambda x : x.replace(']',''))
#    print(kl)
    for k in leadsects:
        if k in sections:
            outfile.write("".join(sections[k]))

    for k in kl:
        if k not in (leadsects + followsects):
            outfile.write("".join(sections[k]))

    for k in followsects:
        outfile.write("".join(sections[k]))
