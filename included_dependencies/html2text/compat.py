from __future__ import absolute_import
import sys


import six.moves.html_entities
import six.moves.urllib.parse
import six.moves.html_parser
import six.moves.urllib.request
import six.moves.urllib.parse
import six.moves.urllib.error
from html import escape
def html_escape(s):
    return escape(s, quote=False)
