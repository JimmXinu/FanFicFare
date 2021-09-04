# -*- coding: utf-8 -*-

# Copyright 2018 FanFicFare team
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

from datetime import datetime, timedelta
import re

# py2 vs py3 transition
from .six import text_type as unicode

import logging
logger = logging.getLogger(__name__)

## There's a windows / py3 bug that prevents using 0.
## So Jan 2, 1970 instead.
UNIX_EPOCHE = datetime.fromtimestamp(86400)

## Currently used by adapter_webnovelcom & adapter_wwwnovelallcom

relrexp = re.compile(r'^(?P<val>\d+) *(?P<unit>[^ ]+).*$')

# Keep this explicit instead of replacing parentheses in case we
# discover a format that is not so easily translated as a
# keyword-argument to timedelta.
unit_to_keyword = {
    'second(s)': 'seconds',
    'minute(s)': 'minutes',
    'hour(s)': 'hours',
    'day(s)': 'days',
    'week(s)': 'weeks',
    'seconds': 'seconds',
    'minutes': 'minutes',
    'hours': 'hours',
    'days': 'days',
    'weeks': 'weeks',
    'second': 'seconds',
    'minute': 'minutes',
    'mins': 'minutes',
    'hour': 'hours',
    'day': 'days',
    'week': 'weeks',
    'mth': 'months',
    'h': 'hours',
    'd': 'days',
    'yr': 'years',
}

def parse_relative_date_string(reldatein):
    # logger.debug("parse_relative_date_string(%s)"%reldatein)
    # discards trailing ' ago' if present
    m = re.match(relrexp,reldatein)

    if m:
        value = m.group('val')
        unit_string = m.group('unit')

        unit = unit_to_keyword.get(unit_string)
        logger.debug("val:%s unit_string:%s unit:%s"%(value, unit_string, unit))
        ## I'm not going to worry very much about accuracy for a site
        ## that considers '2 years ago' an acceptable time stamp.
        if "year" in unit_string or unit and ('year' in unit):
            value = unicode(int(value)*365)
            unit = 'days'
        elif "month" in unit_string or unit and ('month' in unit):
            value = unicode(int(value)*31)
            unit = 'days'
        logger.debug("val:%s unit_string:%s unit:%s"%(value, unit_string, unit))
        if unit:
            kwargs = {unit: int(value)}

            # "naive" dates without hours and seconds are created in
            # writers.base_writer.writeStory(), so we don't have to strip
            # hours and minutes from the base date. Using datetime objects
            # would result in a slightly different time (since we calculate
            # the last updated date based on the current time) during each
            # update, since the seconds and hours change.
            today = datetime.utcnow()
            time_ago = timedelta(**kwargs)
            return today - time_ago
    # This is "just as wrong" as always returning the current
    # date, but prevents unneeded updates each time
    logger.warning('Failed to parse relative date string: %r, falling back to unix epoche', reldatein)
    return UNIX_EPOCHE
