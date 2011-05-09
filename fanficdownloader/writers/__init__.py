# -*- coding: utf-8 -*-

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
