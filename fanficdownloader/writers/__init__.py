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

## This could (should?) use a dynamic loader like adapters, but for
## now, it's static, since there's so few of them.

from fanficdownloader.exceptions import FailedToDownload

from writer_html import HTMLWriter
from writer_txt  import TextWriter
from writer_epub import EpubWriter

def getWriter(type,config,story):
    if type == "html":
        return HTMLWriter(config,story)
    if type == "txt":
        return TextWriter(config,story)
    if type == "epub":
        return EpubWriter(config,story)

    raise FailedToDownload("(%s) is not a supported download format."%type)
