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

import re
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
        navdiv = souptag.find('div',{'class':'threadmarkMenus'})
        # was class=threadmarksTrigger.  thread cats are currently
        # only OverlayTrigger <a>s in threadmarkMenus, but I wouldn't
        # be surprised if that changed.  Don't want to do use just
        # href=re because there's more than one copy on the page; plus
        # could be included in a post.  Would be easier if <noscript>s
        # weren't being stripped, but that's a different issue.
        threadmarksas = navdiv.find_all('a',{'class':'OverlayTrigger','href':re.compile('threadmarks.*category_id=')})
        ## Loop on threadmark categories.
        threadmarks=[]
        tmcat_num=None

        for threadmarksa in threadmarksas:
            tmcat_num = threadmarksa['href'].split('category_id=')[1]
            # get from earlier <a> now.
            tmcat_name = stripHTML(threadmarksa.find_previous('a',{'class':'threadmarksTrigger'}))
            prepend = ""
            if tmcat_name in self.getConfigList('skip_threadmarks_categories'):
                continue

            if tmcat_name == 'Apocrypha' and self.getConfig('apocrypha_to_omake'):
                tmcat_name = 'Omake'

            if tmcat_name != "Threadmarks":
                prepend = tmcat_name+" - "

            soupmarks = self.make_soup(self._fetchUrl(self.getURLPrefix()+'/'+threadmarksa['href']))
            markas = []
            markas = soupmarks.find('div',{'class':'threadmarkList'}).find_all('a',{'class':'PreviewTooltip'})
            for tmcat_index, atag in enumerate(markas):
                url,name = atag['href'],stripHTML(atag)
                date = self.make_date(atag.find_next_sibling('div',{'class':'extra'}))
                threadmarks.append({"tmcat_name":tmcat_name,"tmcat_num":tmcat_num,"tmcat_index":tmcat_index,'title':name,'url':self.getURLPrefix()+'/'+url,'date':date})

        return threadmarks
