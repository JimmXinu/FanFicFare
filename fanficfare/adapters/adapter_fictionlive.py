# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2020 FanFicFare team
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

#### Hazel's fiction.live fanficfare adapter
# what an *adventure* this was. fiction.live is an angular web3.0 app that does async background stuff everywhere.
# they're not kidding about it being live.
# can I wrangle it's stories into books for offline reading? yes I 98% can!

### won't support, because they aren't part of the text
# chat, threads, chat replies on vote options

### can't support because wtf this is a book
# music / audio embeds
# per-user achivement tracking with fancy achievement-get animations
# story scripting (shows script tags visible in the text, not computed values or input fields)

import json
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

from .base_adapter import BaseSiteAdapter
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

from ..six import text_type as unicode, ensure_text

def getClass():
    return FictionLiveAdapter

class FictionLiveAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.story.setMetadata('siteabbrev','flive')
        self._setURL(url);
        self.story_id = self.parsedUrl.path.split('/')[3]
        self.story.setMetadata('storyId', self.story_id)

    @staticmethod
    def getSiteDomain():
        return "fiction.live"

    @classmethod
    def getAcceptDomains(cls):
        return ["fiction.live"] # I still remember anonkun, but the domain has now lapsed

    def getSiteURLPattern(self):
        # I'd like to thank regex101.com for helping me screw this up less
        return r"https?://fiction\.live/[^/]*/[^/]*/([a-zA-Z0-9\-]+)(/(home)?)?$"

    @classmethod
    def getSiteExampleURLs(cls):
        return ("https://fiction.live/stories/Example-Story-Title/17CharacterIDhere/home "
                +"https://fiction.live/stories/Example-Story-With-Long-ID/-20CharacterIDisHere "
                +"https://fiction.live/Sci-fi/Example-Story-With-URL-Genre/17CharacterIDhere/ "
                +"https://fiction.live/stories/Example-Story-With-UUID/00000000-0000-4000-0000-000000000000/")

    def parse_timestamp(self, timestamp):
        # fiction.live date format is unix-epoch milliseconds. not a good fit for fanficfare's makeDate.
        # doesn't use a timezone object and returns tz-naive datetimes. I *think* I can leave the rest to fanficfare
        return datetime.fromtimestamp(timestamp / 1000.0, None)

    def doExtractChapterUrlsAndMetadata(self, get_cover=True):

        metadata_url = "https://fiction.live/api/node/{s_id}/"
        response = self._fetchUrl(metadata_url.format(s_id = self.story_id))

        if not response: # this is how fiction.live responds to nonsense urls -- HTTP200 with empty response
            raise exceptions.StoryDoesNotExist("Empty response for " + self.url)

        data = json.loads(response)

        ## get metadata for multi route chapters
        if 'multiRoute' in data and data['multiRoute'] == True:
            route_metadata_url = "https://fiction.live/api/anonkun/routes/{s_id}/"
            response = self._fetchUrl(route_metadata_url.format(s_id = self.story_id))

            if not response: # this is how fiction.live responds to nonsense urls -- HTTP200 with empty response
                raise exceptions.StoryDoesNotExist("Empty response for " + self.url)

            data["route_metadata"] = json.loads(response)

        self.extract_metadata(data, get_cover)
        self.add_chapters(data)

    def extract_metadata(self, data, get_cover):
        # on one hand, we've got nicely-formatted JSON and can just index into the thing we want, no parsing needed.
        # on the other, nearly *everything* in this api is optional. found that out the hard way.

        # not optional
        self.story.setMetadata('title', stripHTML(data['t']))
        self.story.setMetadata('status', data['storyStatus'])
        self.story.setMetadata('rating', data['contentRating'])

        # stories have ut, rt, ct, and cht. fairly sure that ut = update time and rt = release time.
        # ct is 'creation time' and everything in the api has it -- you can create stories and edit before publishing
        # no idea about cht
        self.story.setMetadata("dateUpdated", self.parse_timestamp(data['ut']))
        self.story.setMetadata("datePublished", self.parse_timestamp(data['rt']))

        # nearly everything optional from here out

        if 'w' in data: self.story.setMetadata('numWords', data['w'])
        if 'likeCount' in data: self.story.setMetadata('likes', data['likeCount'])
        if 'rInput' in data: self.story.setMetadata('reader_input', data['rInput'].title())

        summary = stripHTML(data['d']) if 'd' in data else ""
        firstblock = data['b'].strip() if 'b' in data else ""
        self.setDescription(self.url, summary if not firstblock else summary + "\n<br />\n" + firstblock)

        tags = data['ta'] if 'ta' in data else []

        if (data['contentRating'] == "nsfw" or 'smut' in tags) and \
           not (self.is_adult or self.getConfig("is_adult")):
            raise exceptions.AdultCheckRequired(self.url)

        show_spoiler_tags = self.getConfig('show_spoiler_tags')
        spoiler_tags = data['spoilerTags'] if 'spoilerTags' in data else []
        for tag in tags[:5]:
            self.story.addToList('key_tags', tag)
        for tag in tags[5:]:
            if show_spoiler_tags or not tag in spoiler_tags:
                self.story.addToList('tags', tag)

        authors = data['u'] # non-optional
        if len(authors) > 1:
            for author in data['u']:
                if '_id' in author and author['n']: # some stories have spurious co-authors (may have been fixed?)
                    self.story.addToList('author', author['n'])
                    self.story.addToList('authorUrl', "https://fiction.live/user/" + author['n'] + "/")
                    self.story.addToList('authorId', author['_id'])
        else: # TODO: can avoid this?
            author = authors[0]
            self.story.setMetadata('author', author['n'])
            self.story.setMetadata('authorUrl', "https://fiction.live/user/" + author['n'] + "/")
            self.story.setMetadata('authorId', author['_id'])

        if 'isLive' in data and data['isLive']:
            self.story.setMetadata('live', "Now! (at time of download)")
        elif 'nextLive' in data and data['nextLive']:
            # formatted to match site, not other fanficfare timestamps
            next_live_time = self.parse_timestamp(data['nextLive'])
            self.story.setMetadata('live', next_live_time)

        show_nsfw_cover_images = self.getConfig('show_nsfw_cover_images')
        nsfw_cover = data['nsfwCover'] if 'nsfwCover' in data else False
        if get_cover and 'i' in data:
            if show_nsfw_cover_images or not nsfw_cover:
                coverUrl = data['i'][0]
                self.setCoverImage(self.url, coverUrl)
                self.story.setMetadata('cover_image', "<a href=\"" + coverUrl + "\" />") # TODO: is this needed?

        # gonna need these later for adding details to achievement-granting links in the text
        try:
            self.achievements = data['achievements']['achievements']
        except KeyError:
            self.achievements = []

    def add_chapters(self, data):

        ## chapter urls are for the api. they return json and aren't user-navigatable, or the same as on the website
        chunkrange_url = "https://fiction.live/api/anonkun/chapters/{s_id}/{start}/{end}/"

        ## api url to get content of a multi route chapter. requires only the route id and no timestamps
        route_chunkrange_url = "https://fiction.live/api/anonkun/route/{c_id}/chapters"

        def add_chapter_url(title, start, end):
            "Adds a chapter url based on the start/end chunk-range timestamps."
            chapter_url = chunkrange_url.format(s_id = data['_id'], start = start, end = end)
            self.add_chapter(title, chapter_url)

        def add_route_chapter_url(title, route_id):
            "Adds a route chapter url based on the route id."
            chapter_url = route_chunkrange_url.format(c_id = route_id)
            self.add_chapter(title, chapter_url)

        ### chapter addition loop. bit complex, as both first and last chapters have special handling

        ## first thing to do is seperate out the appendices
        appendices, maintext, routes = [], [], []
        chapters = data['bm'] if 'bm' in data else [{"title": "Home", "ct": data['ct']}]

        for c in chapters:
            appendices.append(c) if c['title'].startswith('#special') else maintext.append(c)

        ## not all stories use multiple routes. Those that do have a route id and a title for each route
        if 'route_metadata' in data and data['route_metadata']:
            for r in data['route_metadata']:
                routes.append({"id": r['_id'], "title": r['t']})

        # loop setup
        chapter_iter = iter(maintext)
        first_chapter = next(chapter_iter)

        chapter_start = 0
        # this *goddamn* api. don't want to start the chunk-range from 0 if there's an appendix before the text!
        if 'isFirst' in first_chapter and first_chapter['isFirst']:
            chapter_start = first_chapter['ct']

        prev_chapter_title = first_chapter['title']

        # now iterate, adding the chapters before the one we're at
        # TODO: do a while loop and manually call next()? already setting up the iterator
        for c in chapter_iter:
            chapter_end = c['ct'] - 1
            add_chapter_url(prev_chapter_title, chapter_start, chapter_end)
            chapter_start = c['ct']
            prev_chapter_title = c['title']

        # with the loop done, we've handled every chapter but the final one, so we'll now do it manually.
        chapter_end = 9999999999999998
        add_chapter_url(prev_chapter_title, chapter_start, chapter_end)

        for a in appendices: # add appendices at the end
            chapter_start = a['ct']
            chapter_title = "Appendix: " + a['title'][9:] # 'Appendix: ' rather than '#special' at beginning of name
            add_chapter_url(chapter_title, chapter_start, chapter_start + 1) # 1 msec range = this one chunk only

        for r in routes:  # add route at the end, after appendices
            route_id = r['id']  # to get route chapter content, the route id is needed, not the timestamp
            chapter_title = "Route: " + r['title']  # 'Route: ' at beginning of name, since it's a multiroute chapter
            add_route_chapter_url(chapter_title, route_id)

    def getChapterText(self, url):

        chunk_handler = {
            "choice"     : self.format_choice,
            "readerPost" : self.format_readerposts,
            "chapter"    : self.format_chapter
        }

        response = self._fetchUrl(url)
        data = json.loads(response)

        if data == []:
            return ""
        # and *now* we can assume there's at least one chunk in the data -- chapters can be totally empty.

        # are we trying to read an appendix? check the first chunk to find out.
        getting_appendix = 't' in data[0] and data[0]['t'].startswith("#special")

        text = ""

        for count, chunk  in enumerate(data):
            #logger.debug("chunk #{i}".format(i=count)) # helps to locate problem chunks in long chapters

            text += "<div>" # chapter chunks aren't always well-delimited in their contents

            # so appendix chunks just turn up wherever
            if not getting_appendix and 't' in chunk and chunk['t'].startswith("#special"): # t = title = bookmark
                continue

            handler = chunk_handler.get(chunk['nt'], self.format_unknown) # nt = node type
            text += handler(chunk)

            show_timestamps = self.getConfig('show_timestamps')
            if show_timestamps and 'ct' in chunk:
                #logger.debug("Adding timestamp for chunk...")
                timestamp = six.ensure_text(self.parse_timestamp(chunk['ct']).strftime("%x -- %X"))
                text += '<div class="ut">' + timestamp + '</div>'

            text += "</div><br />\n"

        return text

    ### everything from here out is chunk data handling.

    def format_chapter(self, chunk):
        """Handles any formatting in the chapter body text for text chapters.
        In the 'default case' where we're getting boring chapter-chunk body text, just calls utf8fromSoup
        and returns the text as is on the website."""

        soup = self.make_soup(chunk['b'] if 'b' in chunk else "")

        if self.getConfig('legend_spoilers'):
            soup = self.add_spoiler_legends(soup)

        if self.achievements:
            soup = self.append_achievments(soup)

        # utf8FromSoup does important processing e.g. sanitization and imageurl extraction
        return self.utf8FromSoup(self.url, soup)

    def add_spoiler_legends(self, soup):
        # find spoiler links and change link-anchor block to legend block
        spoilers = soup.find_all('a', class_="tydai-spoiler")
        for link_tag in spoilers:
            link_tag.name = 'fieldset'
            legend = soup.new_tag('legend')
            legend.string = "Spoiler"
            link_tag.insert(0, legend)
        return soup

    def append_achievments(self, soup):
        # achivements are present in the text as a kind of link, and you get the shiny popup by clicking them.
        achievement_links = soup.find_all('a', class_="tydai-achievement")

        achieved_ids = []
        for link_tag in achievement_links:
            # these are not only prepended by a unicode lightning-bolt, but also format clearly as a link
            # should use .u css selector -- part of output_css defaults? or just let replace_tags_with_spans do it?
            new_u = soup.new_tag('u')
            new_u.string = link_tag.text # copy out the link text into a new element
            # html entities for improved compatability with AZW3 conversion
            link_tag.string = "&#x26A1;" # then overwrite
            link_tag.insert(1, new_u)

            ## while we've got the achievment links, get the ids from the link
            a_id = link_tag['data-id']
            # BUG: these are all replaced, but I *don't* know that the list is complete.
            # should be rare, thankfully. *most* authors don't use any funny characters in the achievment's *ID*
            special_chars = "\"\\,.!?+=/[](){}<>_'@#$%^&*~`;:|" # not the hyphen, which is used to represent spaces
            a_id = a_id.lower().replace(" ", "-").translate({ord(x) : None for x in special_chars})
            achieved_ids.append(a_id)

        if achieved_ids:
            logger.debug("achievements (this chunk): " + ", ".join(achieved_ids))

        # can't replicate the animated shiny announcement popup, so have an end-of-chunk announcement instead
        # TODO: achievement images -- does anyone use them?
        a_source = "<br />\n<fieldset><legend>&#x26A1; Achievement obtained!</legend>\n<h4>{}</h4>\n{}</fieldset>\n"

        for a_id in achieved_ids:
            if a_id in self.achievements:
                a_title = self.achievements[a_id]['t']  if 't' in self.achievements[a_id] else a_id.title()
                a_text = self.achievements[a_id]['d'] if 'd' in self.achievements[a_id] else ""
                soup.append(self.make_soup(a_source.format(a_title, a_text)))
            else:
                a_title = a_id.title()
                error = "<br />\n<fieldset><legend>Error: Achievement not found.</legend>Couldn't find '{}'. Ask the story author to check if the achievment exists."
                soup.append(self.make_soup(error.format(a_title)))

        return soup

    def count_votes(self, chunk):
        """So, fiction.live's api doesn't return the counted votes you see on the website.
        After all, it needs to allow for things like revoking a vote,
        with the count live and updated in realtime on your client.
        So instead we get the raw vote-data, but have to count it ourselves."""

        # optional.
        choices = chunk['choices'] if 'choices' in chunk else []

        def counter(votes):
            output = [0] * len(choices)
            for vote in votes.values():
                ## votes are either a single option-index or a list of option-indicies, depending on the choice type
                if 'multiple' in chunk and chunk['multiple'] == False:
                    vote = [vote] # normalize to list
                for v in vote:
                    if 0 <= v <= len(choices):
                        output[v] += 1
            return output

        # I believe that verified is always a subset of all votes, but that's not enforced here
        total_votes = counter(chunk['votes'] if 'votes' in chunk else {})
        verified_votes = counter(chunk['userVotes'] if 'userVotes' in chunk else {})

        # Choices can link to route chapters, where the index of the choice in list 'choices' is a key in the
        #   'routes' dict and the dict value is the route id.
        # That route id is needed for the url to create the internal link from the choice to the route chapter.
        routes = chunk['routes'] if 'routes' in chunk else {}
        if choices and len(routes) > 0:
            altered_choices = []
            for i, choice in enumerate(choices):
                choice_index = str(i)
                if choice_index in routes.keys():
                    route_chunkrange_url = "https://fiction.live/api/anonkun/route/{c_id}/chapters"
                    route_url = route_chunkrange_url.format(c_id=routes[choice_index])
                    choice_link = "<a data-orighref='" + route_url + "' >" + choice + "</a>"
                    altered_choices.append(choice_link)
                else:
                    altered_choices.append(choice)
            choices = altered_choices

        return zip(choices, verified_votes, total_votes)

    def format_choice(self, chunk):

        options = self.count_votes(chunk)

        # crossed-out writeins. authors can censor user-written choices, and (optionally) offer a reason.
        x_outs = [int(x) for x in chunk['xOut']] if 'xOut' in chunk else []
        x_reasons = chunk['xOutReasons'] if 'xOutReasons' in chunk else {}

        closed = "closed" if 'closed' in chunk else "open" # BUG: check on reopened votes

        num_voters = len(chunk['votes']) if 'votes' in chunk else 0

        output = ""
        # start with the header
        output += u"<h4><span>Choices — <small>Voting " + closed
        output += u" — " + str(num_voters) + " voters</small></span></h4>\n"

        # we've got everything needed to build the html for our vote table.
        output += "<table class=\"voteblock\">\n"

        # filter out the crossed-out options, which display last
        crossed = []
        for index, (choice_text, verified_votes, total_votes) in enumerate(options):
            if index in x_outs:
                crossed.append((index, choice_text, verified_votes, total_votes))
            else:
                output += "<tr class=\"choiceitem\"><td>" + choice_text + "</td><td class=\"votecount\">"
                if verified_votes > 0:
                    output += "★" + str(verified_votes) + "/"
                output += str(total_votes)+ " </td></tr>\n"

        # crossed out options are: displayed last, struckthrough, smaller, with the reason below, and no vote count.
        # also greyed out, but that's a bit much.
        for index, choice_text, _, _ in crossed:
            if choice_text == "permanentlyRemoved":
                continue
            else:
                x_reason = x_reasons[str(index)] if str(index) in x_reasons else ""
                output += "<tr class=\"choiceitem\"><td colspan=\"2\"><small><strike>" \
                                      + choice_text + "</strike><br>" + x_reason + "</small></td></tr>"

        output += "</table>\n"

        return output

    def format_readerposts(self, chunk):

        closed = "Closed" if 'closed' in chunk else "Open"

        posts = chunk['votes'] if 'votes' in chunk else {}
        dice = chunk['dice'] if 'dice' in chunk else {}

        # now matches the site and does *not* include dicerolls as posts!
        num_votes = str(len(posts)) + "posts" if len(posts) != 0 else "be the first to post."

        output = ""
        output += u"<h4><span>Reader Posts — <small> Posting " + closed
        output += u" — " + num_votes + "</small></span></h4>\n"

        ## so. a voter can roll with their post. these rolls are in a seperate dict, but have the **same uid**.
        ## they're then formatted with the roll above the writein for that user.
        ## I *think* that formatting roll-only before writein-only posts is correct, but tbh, it's hard to tell.
        ## writeins are usually opened by the author for posts or rolls, not both at once.
        ## people tend to only mix the two by accident.
        if dice != {}:
            for uid, roll in dice.items():
                output += '<div class="choiceitem">'
                if roll: # optional. just because there's a list entry for it doesn't mean it has a value!
                    output += '<div class="dice">' + roll + '</div>\n'
                if uid in posts:
                    post = posts[uid]
                    if post:
                        output += post
                    del posts[uid] # it's handled here with the roll instead of later
                output += '</div>'

        for post in posts.values():
            if post:
                output += '<div class="choiceitem">' + post + '</div>\n'

        return output

    def format_unknown(self, chunk):
        raise NotImplementedError("Unknown chunk type ({}) in fiction.live story.".format(chunk))

# in future, I'd like to handle audio embeds somehow. but they're not availble to add to stories right now.
# pretty sure they'll just format as a link (with a special tydai-audio class) and should be easier than achievements

# TODO:
# set fanficfare plugin to use "overwrite if newer" ? or 'update epub always' ?
# a lot of times, chunks will be added even when chapters/bookmarks don't change
# if bookmarks do change, it may not be as simple as adding new ones to the end

# TODO: verify that show_timestamps is working, check times!

# TODO: find a story that uses achievement images and implement them

# TODO: sort out updates, somehow. 'update epub if new chapters' is an awful match for fiction.live
# where chunks get just dropped at the end of chapters, and chapter-bookmarking happens later.
# updating in 'overwrite always' or 'overwrite if newer' does the right thing, but.

# TODO: pagecache. In particular, if there's any way to update stories and *not* redownload images, that'd be great.
