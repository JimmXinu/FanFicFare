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
    'min': 'minutes',
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

    # If the date is displayed as Yesterday
    if "Yesterday" in reldatein:
            value = unicode(int(1))
            unit = 'days'
            logger.debug("val:%s unit_string:%s unit:%s"%(value, unit, unit))
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
                date = today - time_ago
                
                return date.strftime("%b %d, %Y")
    elif "just now" in reldatein:
        return datetime.utcnow().strftime("%b %d, %Y")

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

fullmon = {u"January":u"01", u"February":u"02", u"March":u"03", u"April":u"04", u"May":u"05",
           u"June":u"06","July":u"07", u"August":u"08", u"September":u"09", u"October":u"10",
           u"November":u"11", u"December":u"12" }

def makeDate(string,dateform):
    # Surprise!  Abstracting this turned out to be more useful than
    # just saving bytes.

    # fudge english month names for people who's locale is set to
    # non-USenglish.  Most current sites date in english, even if
    # there's non-english content -- ficbook.net, OTOH, has to do
    # something even more complicated to get Russian month names
    # correct everywhere.
    do_abbrev = "%b" in dateform

    if u"%B" in dateform or do_abbrev:
        dateform = dateform.replace(u"%B",u"%m").replace(u"%b",u"%m")
        for (name,num) in fullmon.items():
            if do_abbrev:
                name = name[:3] # first three for abbrev
            if name in string:
                string = string.replace(name,num)
                break

    # Many locales don't define %p for AM/PM.  So if %p, remove from
    # dateform, look for 'pm' in string, remove am/pm from string and
    # add 12 hours if pm found.
    add_hours = False
    if u"%p" in dateform:
        dateform = dateform.replace(u"%p",u"")
        if 'pm' in string or 'PM' in string:
            add_hours = True
        string = string.replace(u"AM",u"").replace(u"PM",u"").replace(u"am",u"").replace(u"pm",u"")

    dateform = dateform.strip()
    string = string.strip()
    try:
        date = datetime.strptime(string, dateform)
    except ValueError:
        ## If parse fails and looking for 01-12 hours, try 01-24 hours too.
        ## A moderately cheesy way to support 12 and 24 hour clocks.
        if u"%I" in dateform:
            dateform = dateform.replace(u"%I",u"%H")
            date = datetime.strptime(string, dateform)
            add_hours = False
        else:
            raise

    if add_hours:
        date += timedelta(hours=12)

    return date
