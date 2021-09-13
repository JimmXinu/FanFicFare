# -*- coding: utf-8 -*-

# Copyright 2021 FanFicFare team
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

import base64
import time
import json
import logging
logger = logging.getLogger(__name__)

from . import exceptions
from .fetcher import RequestsFetcher, FetcherResponse, make_log
from .six.moves.http_cookiejar import Cookie

class FlareSolverr_ProxyFetcher(RequestsFetcher):
    def __init__(self, getConfig_fn, getConfigList_fn):
        logger.debug("using FlareSolverr_ProxyFetcher")
        super(FlareSolverr_ProxyFetcher, self).__init__(getConfig_fn,
                                                 getConfigList_fn)
        self.super_request = super(FlareSolverr_ProxyFetcher,self).request

    def request(self, method, url, headers=None, parameters=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()

        ## XXX
        ##
        ## create, use then destroy a session on the proxy?  Would
        ## need to add some kind of 'end session' thing. Proc wide
        ## singleton with session value?

        logger.debug(
            make_log('FlareSolverr_ProxyFetcher', method, url, hit='REQ', bar='-'))
        cmd = ('request.'+method).lower()

        resp = self.super_request('POST',
                                  'http://'+self.getConfig("flaresolverr_proxy_address", "localhost")+\
                                      ':'+self.getConfig("flaresolverr_proxy_port", '8191')+'/v1',
                                  headers={'Content-Type':'application/json'},
                                  json={'cmd': cmd,
                                        'url':url,
                                        #'userAgent': 'Mozilla/5.0',
                                        'maxTimeout': 60000,
                                        'download': True,
                                        # causes response to be base64
                                        # encoded which makes images
                                        # work.
                                        'cookies':cookiejar_to_jsonable(self.cookiejar)
                                        }
                                  )
        if( resp.json['status'] == 'ok' and
            'solution' in resp.json and
            'status' in resp.json['solution']
            ):
            status_code = resp.json['solution']['status']
            logger.debug("response code:%s"%status_code)
            logger.debug(json.dumps(resp.json, sort_keys=True,
                                    indent=2, separators=(',', ':')))
            data = base64.b64decode(resp.json['solution']['response'])
            url = resp.json['solution']['url']
            for c in cookiejson_to_jarable(resp.json['solution']['cookies']):
                self.cookiejar.set_cookie(c)
        else:
            logger.debug("flaresolverr error resp:")
            logger.debug(json.dumps(resp.json, sort_keys=True,
                                    indent=2, separators=(',', ':')))
            status_code = 428  # 404 & 410 trip StoryDoesNotExist
                               # 428 ('Precondition Required') gets the
                               # error_msg through to the user.
            data = resp.json['message']
        if status_code != 200:
                raise exceptions.HTTPErrorFFF(
                    url,
                    status_code,
                    data
                    )

        return FetcherResponse(data,
                               url,
                               False)

def cookiejar_to_jsonable(cookiejar):
    retval = []
    for c in cookiejar:
        cval = {
            'name':c.name,
            'value':c.value,
            'domain':c.domain,
            'path':c.path,
            }
        if c.expires:
            cval['expires'] = c.expires

        retval.append(cval)
    return retval

def cookiejson_to_jarable(data):
    retval = []
    for c in data:
        retval.append(Cookie(None, # version
                             c['name'],
                             c['value'],
                             None, # port
                             False, # port_specified,
                             c['domain'],
                             True, # domain_specified,
                             c['domain'].startswith('.'), # domain_initial_dot,
                             c['path'],
                             c['path'] == None or c['path'] == '', # path_specified,
                             c['secure'],
                             c['expires'],
                             c['expires'] == -1, # discard
                             None, # comment,
                             None, # comment_url,
                             {}, # rest
                             ))
    return retval

# "cookies":[
#       {
#         "domain":"www.hentai-foundry.com",
#         "expires":-1,
#         "httpOnly":false,
#         "name":"YII_CSRF_TOKEN",
#         "path":"/",
#         "secure":false,
#         "session":true,
#         "size":164,
#         "value":"952f8cf13b88ad98a3ea485a7360b9671f026b85s%3A88%3A%22YWFRTn43ekJFUkFzeUJrSXdmQTRzbXgya3pCNGd1d26UvTvOzIHijrHnfb3ttZYX2RAJX4HbBjbBWifMIUjjJQ%3D%3D%22%3B"
#       },
#       {
#         "domain":"www.hentai-foundry.com",
#         "expires":-1,
#         "httpOnly":false,
#         "name":"PHPSESSID",
#         "path":"/",
#         "secure":false,
#         "session":true,
#         "size":59,
#         "value":"Uiw6N47QIPB29hs-gHC161vH%2CUjjMbrtNrVKb0ZxatDtkdoj"
#       }
#     ],
