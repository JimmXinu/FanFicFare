# -*- coding: utf-8 -*-

# Copyright 2022 FanFicFare team
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

from __future__ import absolute_import
import re

# .? for AO3's ']' in param names.
safe_url_re = re.compile(r'(?P<attr>(pass(word)?|name|login).?=)[^&]*(?P<amp>&|$)',flags=re.MULTILINE)
def safe_url(url):
    # return url with password attr (if present) obscured.
    return re.sub(safe_url_re,r'\g<attr>XXXXXXXX\g<amp>',url)

## Yes, I care about this debug out more than I really should.  But I
## do watch it alot.
def make_log(where,method,url,hit=True,bar='=',barlen=10):
    return "\n%(bar)s %(hit)s (%(method)s) %(where)s\n%(url)s"%{
        'bar':bar*barlen,
        'where':where,
        'method':method,
        'url':safe_url(url),
        'hit':'HIT' if hit==True else 'MISS' if hit==False else hit}
