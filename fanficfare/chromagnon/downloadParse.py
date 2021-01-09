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
Parse the Chrome Download Table History File
Its a SQLite3 table
"""

from __future__ import absolute_import
from __future__ import print_function
import datetime
import sqlite3
import sys
import six

def parse(filename, urlLength):
    """
    filename: path to the history file
    urlLength: maximum url length to display
    """

    # Connecting to the DB
    try:
        history = sqlite3.connect(filename)
    except sqlite3.Error as error:
        print("==> Error while opening the history file !")
        print("==> Details :", error.message)
        sys.exit("==> Exiting...")

    # Retrieving all useful data
    result = history.execute("SELECT id, \
                              full_path, \
                              url, \
                              start_time, \
                              received_bytes, \
                              total_bytes, \
                              state \
                              FROM downloads;")

    output = []
    for line in result:
        output.append(DownloadEntry(line, urlLength))
    return output

class DownloadEntry(object):
    """Object to store download entries"""
    COLUMN_STR = {'st': "startTime",
                  'p': "path",
                  'u': "url",
                  'rb': "receivedBytes",
                  'tb': "totalBytes",
                  'pt': "percentReceived",
                  's': "state"}
    STATE_STR = ["In Progress",
                 "Complete",
                 "Cancelled",
                 "Removing",
                 "Interrupted"]

    def __init__(self, item, urlLength):
        """Parse raw input"""
        self.path = item[1]
        if len(item[2]) > urlLength and urlLength > 0:
            self.url = item[2][0:urlLength - 3] + "..."
        else:
            self.url = item[2]
        self.startTime = datetime.datetime(1601, 1, 1) + \
                         datetime.timedelta(microseconds=\
                         item[3])
        self.receivedBytes = item[4]
        self.totalBytes = item[5]
        self.state = DownloadEntry.STATE_STR[item[6]]
        if int(item[5]) == 0:
            self.percentReceived = "0%"
        else:
            self.percentReceived = "%d%%" % \
                                   int(float(item[4])/float(item[5])*100)

    def columnToStr(self, column):
        """Returns column content specified by argument"""
        return six.text_type(self.__getattribute__(DownloadEntry.COLUMN_STR[column]))
