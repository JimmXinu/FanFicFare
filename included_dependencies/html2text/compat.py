from __future__ import absolute_import
import sys


if sys.version_info[0] == 2:
    import six.moves.html_entities
    import six.moves.urllib.parse
    import six.moves.html_parser
    import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
    from cgi import escape as html_escape
else:
    import urllib.parse as urlparse
    import html.entities as htmlentitydefs
    import html.parser as HTMLParser
    import urllib.request as urllib
    from html import escape
    def html_escape(s):
        return escape(s, quote=False)
