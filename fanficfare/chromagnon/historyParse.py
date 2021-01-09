#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, Jean-Rémy Bancel <jean-remy.bancel@telecom-paristech.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Chromagon Project nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Jean-Rémy Bancel BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Parse the Chrome History File
Its a SQLite3 file
"""

from __future__ import absolute_import
from __future__ import print_function
import datetime
import re
import sqlite3
import sys

from . import cacheParse
import six

def parse(filename, start, end, checkCache, cachePath, urlLength):
    """
    filename: path to the history file
    start: beginning of the time window
    end: end of the time window
    checkCache: check if each page in the history is in the cache
    cachePath: path to cache directory
    """

    # Connecting to the DB
    try:
        history = sqlite3.connect(filename)
    except sqlite3.Error as error:
        print("==> Error while opening the history file !")
        print("==> Details :", error.message)
        sys.exit("==> Exiting...")

    reference = datetime.datetime(1601, 1, 1)

    # Retrieving all useful data
    result = history.execute("SELECT visits.visit_time, \
                               visits.from_visit, \
                               visits.transition, \
                               urls.url, \
                               urls.title, \
                               urls.visit_count, \
                               urls.typed_count, \
                               urls.last_visit_time \
                               FROM urls,visits \
                               WHERE urls.id=visits.url\
                               AND visits.visit_time>%d\
                               AND visits.visit_time<%d\
                               ORDER BY visits.visit_time;"%\
                               (int((start-reference).total_seconds()*1000000),\
                               int((end-reference).total_seconds()*1000000)))\

    # Parsing cache
    cache = None
    if checkCache:
        cache = cacheParse.parse(cachePath)

    output = []
    for line in result:
        output.append(HistoryEntry(line, cache, urlLength))
    return output

class Transition():
    """Object representing transition between history pages"""

    CORE_STRING = ["Link",\
                   "Typed",\
                   "Auto Bookmark",\
                   "Auto Subframe",\
                   "Manual Subframe",\
                   "Generated",\
                   "Start Page",\
                   "Form Submit",\
                   "Reload",\
                   "Keyword",\
                   "Keywork Generated"]
    QUALIFIER_STRING = [(0x01000000, "Forward or Back Button"),
                        (0x02000000, "Address Bar"),
                        (0x04000000, "Home Page"),
                        (0x10000000, "Beginning of Chain"),
                        (0x20000000, "End of Chain"),
                        (0x40000000, "Client Redirection"),
                        (0x80000000, "Server Redirection")]

    def __init__(self, transition):
        """
        Parsing the transtion according to
        content/common/page_transition_types.h
        """
        self.core = transition & 0xFF
        self.qualifier = transition & 0xFFFFFF00

    def __str__(self):
        string = Transition.CORE_STRING[self.core]
        for mask, description in Transition.QUALIFIER_STRING:
            if self.qualifier & mask != 0:
                string += ", %s"%description
        return string

class HistoryEntry(object):
    """Object to store database entries"""
    COLUMN_STR = {'vt': "visitTime",
                  'fv': "fromVisit",
                  'tr': "transition",
                  'u':  "url",
                  'tl': "title",
                  'vc': "visitCount",
                  'tc': "typedCount",
                  'lv': "lastVisitTime",
                  'cc': "inCache"}

    def __init__(self, item, cache, urlLength):
        """Parse raw input"""
        self.visitTime = datetime.datetime(1601, 1, 1) + \
                         datetime.timedelta(microseconds=\
                         item[0])
        self.fromVisit = item[1]
        self.transition = Transition(item[2])
        if len(item[3]) > urlLength and urlLength > 0:
            self.url = item[3][0:urlLength - 3] + "..."
        else:
            self.url = item[3]
        self.title = item[4]
        self.visitCount = item[5]
        self.typedCount = item[6]
        self.lastVisitTime = datetime.datetime(1601, 1, 1) + \
                             datetime.timedelta(microseconds=\
                             item[7])

        # Searching in the cache if there is a copy of the page
        # TODO use a hash table to search instead of heavy exhaustive search
        self.inCache = False
        if cache != None:
            for item in cache:
                if item.keyToStr() == self.url:
                    self.inCache = True
                    break

    def toStr(self):
        return [six.text_type(self.visitTime),\
                six.text_type(self.fromVisit),\
                six.text_type(self.transition),\
                six.text_type(self.url),\
                six.text_type(self.title),\
                six.text_type(self.visitCount),\
                six.text_type(self.typedCount),\
                six.text_type(self.lastVisitTime)]

    def columnToStr(self, column):
        """Returns column content specified by argument"""
        return six.text_type(self.__getattribute__(HistoryEntry.COLUMN_STR[column]))
