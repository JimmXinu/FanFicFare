## Borrowed from http://techknack.net/python-urllib2-handlers/

import urllib2
from gzip import GzipFile
from StringIO import StringIO

class GZipProcessor(urllib2.BaseHandler):
    """A handler to add gzip capabilities to urllib2 requests
    """
    def http_request(self, req):
        req.add_header("Accept-Encoding", "gzip")
        return req
    https_request = http_request

    def http_response(self, req, resp):
        #print("Content-Encoding:%s"%resp.headers.get("Content-Encoding"))
        if resp.headers.get("Content-Encoding") == "gzip":
            gz = GzipFile(
                        fileobj=StringIO(resp.read()),
                        mode="r"
                      )
#            resp.read = gz.read
#            resp.readlines = gz.readlines
#            resp.readline = gz.readline
#            resp.next = gz.next
            old_resp = resp
            resp = urllib2.addinfourl(gz, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
        return resp
    https_response = http_response

# brave new world - 1:30 w/o, 1:10 with?  40 chapters, so 20s from sleeps.
# with gzip, no sleep: 47.469
# w/o gzip, no sleep: 47.736

# I Am What I Am 67 chapters
# w/o gzip: 57.168
# w/ gzip: 40.692
