# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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

## A few exceptions for different things for adapters

class FailedToDownload(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

class AccessDenied(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

class RejectImage(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

class InvalidStoryURL(Exception):
    def __init__(self,url,domain,example):
        self.url=url
        self.domain=domain
        self.example=example
        
    def __str__(self):
        return "Bad Story URL: (%s) for site: (%s) Example: (%s)" % (self.url, self.domain, self.example)

class FailedToLogin(Exception):
    def __init__(self,url, username, passwdonly=False):
        self.url=url
        self.username=username
        self.passwdonly=passwdonly
        
    def __str__(self):
        if self.passwdonly:
            return "URL Failed, password required: (%s) " % (self.url)
        else:
            return "Failed to Login for URL: (%s) with username: (%s)" % (self.url, self.username)

class AdultCheckRequired(Exception):
    def __init__(self,url):
        self.url=url
        
    def __str__(self):
        return "Story requires confirmation of adult status: (%s)" % self.url

class StoryDoesNotExist(Exception):
    def __init__(self,url):
        self.url=url
        
    def __str__(self):
        return "Story does not exist: (%s)" % self.url

class UnknownSite(Exception):
    def __init__(self,url,supported_sites_list):
        self.url=url
        self.supported_sites_list=supported_sites_list
        self.supported_sites_list.sort()

    def __str__(self):
        return "Unknown Site(%s).  Supported sites: (%s)" % (self.url, ", ".join(self.supported_sites_list))

class FailedToWriteOutput(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

class PersonalIniFailed(Exception):
    def __init__(self,error,part,line):
        self.error=error
        self.part=part
        self.line=line

    def __str__(self):
        return "personal.ini Error '%s' in '%s' in line '%s'"%(self.error,self.part,self.line)

class RegularExpresssionFailed(PersonalIniFailed):
    def __init__(self,error,part,line):
        PersonalIniFailed.__init__(self,error,part,line)

    def __str__(self):
        return "Regular Expression Error '%s' in part '%s' in line '%s'"%(self.error,self.part,self.line)

class FetchEmailFailed(Exception):
    def __init__(self,error):
        self.error=error

    def __str__(self):
        return self.error

