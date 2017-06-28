#  -*- coding: utf-8 -*-

# Copyright 2017 FanFicFare team
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

from ..htmlcleanup import stripHTML

from base_xenforoforum_adapter import BaseXenForoForumAdapter

def getClass():
    return QuestionablequestingComAdapter

class QuestionablequestingComAdapter(BaseXenForoForumAdapter):

    def __init__(self, config, url):
        BaseXenForoForumAdapter.__init__(self, config, url)

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev','qq')

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'forum.questionablequesting.com'

    ## extracting threadmarks for chapters has diverged between SV/SB
    ## and QQ enough to require some differentiation.
    def extract_threadmarks(self,souptag):
        # try threadmarks if no '#' in url
        navdiv = souptag.find('div',{'class':'pageNavLinkGroup'})
        threadmarksa = navdiv.find('a',{'class':'threadmarksTrigger'})
        ## Loop on threadmark categories.
        threadmarks=[]
        if threadmarksa:
            soupmarks = self.make_soup(self._fetchUrl(self.getURLPrefix()+'/'+threadmarksa['href']))
            markas = []
            markas = soupmarks.find('div',{'class':'threadmarks'}).find_all('a',{'class':'PreviewTooltip'})
            for (atag,url,name) in [ (x,x['href'],stripHTML(x)) for x in markas ]:
                date = self.make_date(atag.find_next_sibling('div',{'class':'extra'}))
                threadmarks.append({'title':name,'url':self.getURLPrefix()+'/'+url,'date':date})
        return threadmarks
