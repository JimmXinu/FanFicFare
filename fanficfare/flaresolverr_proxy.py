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

import requests

from . import exceptions
from .fetcher import RequestsFetcher, FetcherResponse, make_log
from .six.moves.http_cookiejar import Cookie
from .six.moves.urllib.parse import urlencode
from .six import string_types as basestring, text_type, binary_type
from .six import ensure_binary, ensure_text

FLARESOLVERR_SESSION="FanFicFareSession"
## no convinced this is a good idea yet.
USE_FS_SESSION=False

class FlareSolverr_ProxyFetcher(RequestsFetcher):
    def __init__(self, getConfig_fn, getConfigList_fn):
        logger.debug("using FlareSolverr_ProxyFetcher")
        super(FlareSolverr_ProxyFetcher, self).__init__(getConfig_fn,
                                                 getConfigList_fn)
        self.super_request = super(FlareSolverr_ProxyFetcher,self).request
        self.fs_session = None

    def make_retries(self):
        retry = super(FlareSolverr_ProxyFetcher, self).make_retries()
        ## don't do connect retries in proxy mode.
        retry.connect = 0
        return retry

    def do_fs_request(self, cmd, url=None, headers=None, parameters=None):
        if USE_FS_SESSION and not self.fs_session:
            # manually setting the session causes FS to use that
            # string as the session id.
            resp = self.super_request('POST',
                                      self.getConfig("flaresolverr_proxy_protocol", "http")+'://'+\
                                      self.getConfig("flaresolverr_proxy_address", "localhost")+\
                                          ':'+self.getConfig("flaresolverr_proxy_port", '8191')+'/v1',
                                      headers={'Content-Type':'application/json'},
                                      json={'cmd':'sessions.create',
                                            'session':FLARESOLVERR_SESSION}
                                      )
            # XXX check resp for error?  What errors could occur?
            # logger.debug(json.dumps(resp.json, sort_keys=True,
            #                         indent=2, separators=(',', ':')))
            self.fs_session = resp.json['session']

        fs_data = {'cmd': cmd,
                   'url':url,
                   #'userAgent': 'Mozilla/5.0',
                   'maxTimeout': int(self.getConfig("flaresolverr_proxy_timeout","60000")),
                   # download:True causes response to be base64 encoded
                   # which makes images work.
                   'cookies':cookiejar_to_jsonable(self.get_cookiejar()),
                   'postData':encode_params(parameters),
                   }
        if self.getConfig('use_flaresolverr_proxy') == 'withimages':
            # download param removed in FlareSolverr v2+, but optional
            # for FFF users still on FlareSolver v1.
            fs_data['download'] = True
        if self.fs_session:
            fs_data['session']=self.fs_session

        return self.super_request('POST',
                                  self.getConfig("flaresolverr_proxy_protocol", "http")+'://'+\
                                  self.getConfig("flaresolverr_proxy_address", "localhost")+\
                                      ':'+self.getConfig("flaresolverr_proxy_port", '8191')+'/v1',
                                  headers={'Content-Type':'application/json'},
                                  json=fs_data,
                                  )

    def request(self, method, url, headers=None, parameters=None):
        '''Returns a FetcherResponse regardless of mechanism'''
        if method not in ('GET','POST'):
            raise NotImplementedError()

        logger.debug(
            make_log('FlareSolverr_ProxyFetcher', method, url, hit='REQ', bar='-'))
        cmd = ('request.'+method).lower()

        try:
            resp = self.do_fs_request(cmd, url, headers, parameters)
        except requests.exceptions.ConnectionError as ce:
            raise exceptions.FailedToDownload("Connection to flaresolverr proxy server failed.  Is flaresolverr started?")

        if( resp.json['status'] == 'ok' and
            'solution' in resp.json and
            'status' in resp.json['solution']
            ):
            status_code = resp.json['solution']['status']
            logger.debug("response code:%s"%status_code)
            # logger.debug(json.dumps(resp.json, sort_keys=True,
            #                         indent=2, separators=(',', ':')))
            url = resp.json['solution']['url']
            for c in cookiejson_to_jarable(resp.json['solution']['cookies']):
                self.get_cookiejar().set_cookie(c)
            data = None
            ## FSv2 check removed in favor of
            ## use_flaresolverr_proxy:withimages in the hope one day
            ## FS will have download option again.
            if self.getConfig('use_flaresolverr_proxy') == 'withimages':
                try:
                    # v1 flaresolverr has 'download' option.
                    data = base64.b64decode(resp.json['solution']['response'])
                except Exception as e:
                    logger.warning("Base64 decode of FlareSolverr response failed.  FSv2 doesn't work with use_flaresolverr_proxy:withimages.")
            ## Allows for user misconfiguration, IE,
            ## use_flaresolverr_proxy:withimages with FSv2.  Warning
            ## instead of error out--until they hit an image and crash
            ## FSv2.2 at least.  But hopefully that will be fixed.
            if data is None:
                # Without download (or with FlareSolverr v2), don't
                # need base64 decode, and image downloads won't work.
                if 'headers' in resp.json['solution'] and \
                        'content-type' in resp.json['solution']['headers'] and \
                        'image' in resp.json['solution']['headers']['content-type']:
                    raise exceptions.HTTPErrorFFF(
                        url,
                        428, # 404 & 410 trip StoryDoesNotExist
                        # 428 ('Precondition Required') gets the
                        # error_msg through to the user.
                        "FlareSolverr v2 doesn't support image download (or use_flaresolverr_proxy!=withimages)",# error_msg
                        None # data
                        )
                data = resp.json['solution']['response']
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
                    ensure_text(url),
                    status_code,
                    ensure_text(data)
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
        ## Ran into a site setting a cookie for year 9999, which
        ## caused datetime.datetime.utcfromtimestamp() to fail.
        ## 30000000000 == 2920-08-30 05:20:00.  If 900 years isn't
        ## enough, somebody can fix it then.
        ## (current global_cookie/
        expireKey = 'expires' if 'expires' in c else 'expiry'
        logger.debug("expireKey:%s"%expireKey)
        if c[expireKey] > 30000000000:
            c[expireKey] = 30000000000
            # logger.debug(c['name'])
            # import datetime
            # logger.debug(datetime.datetime.utcfromtimestamp(c[expireKey]))

        retval.append(Cookie(0, # version
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
                             c[expireKey],
                             c[expireKey] == -1, # discard
                             None, # comment,
                             None, # comment_url,
                             {}, # rest
                             ))
    return retval

def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    (lifted from requests)
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError('cannot encode objects that are not 2-tuples')

    if isinstance(value, dict):
        value = value.items()

    return list(value)

def encode_params(data):
    """Encode parameters in a piece of data.

    Will successfully encode parameters when passed as a dict or a list of
    2-tuples. Order is retained if data is a list of 2-tuples but arbitrary
    if parameters are supplied as a dict.
    (lifted from requests)
    """

    if isinstance(data, (text_type, binary_type)):
        return data
    elif hasattr(data, 'read'):
        return data
    elif hasattr(data, '__iter__'):
        result = []
        for k, vs in to_key_val_list(data):
            if isinstance(vs, basestring) or not hasattr(vs, '__iter__'):
                vs = [vs]
            for v in vs:
                if v is not None:
                    result.append(
                        (k.encode('utf-8') if isinstance(k, text_type) else k,
                         v.encode('utf-8') if isinstance(v, text_type) else v))
        return urlencode(result, doseq=True)
    else:
        return data
