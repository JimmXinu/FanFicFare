# -*- coding: utf-8 -*-

import datetime

import fanficdownloader.BeautifulSoup as bs
import fanficdownloader.exceptions as exceptions

from base_adapter import BaseSiteAdapter, utf8FromSoup

class TestSiteAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)
        self.story.setMetadata('siteabbrev','tst1')
        self.crazystring = u" crazy tests:[bare amp(&) quote(&#39;) amp(&amp;) gt(&gt;) lt(&lt;) ATnT(AT&T) pound(&pound;)]"
        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId',self.parsedUrl.query.split('=',)[1])
        self.username=''

    @staticmethod
    def getSiteDomain():
        return 'test1.com'

    def getSiteExampleURLs(self):
        return "http://"+self.getSiteDomain()+"?sid=1234"

    def getSiteURLPattern(self):
        return BaseSiteAdapter.getSiteURLPattern(self)+'\?sid=\d+$'

    def extractChapterUrlsAndMetadata(self):

        if self.story.getMetadata('storyId') == '666':
            raise exceptions.StoryDoesNotExist(self.url)

        if self.getConfig("username"):
            self.username = self.getConfig("username")
        
        if self.story.getMetadata('storyId') == '668' and self.username != "Me" :
            raise exceptions.FailedToLogin(self.url,self.username)
        
        self.story.setMetadata(u'title',"Test Story Title "+self.crazystring)
        self.story.setMetadata('storyUrl',self.url)
        self.story.setMetadata('description',u'Description '+self.crazystring+u''' Done

Some more longer description.  "I suck at summaries!"  "Better than it sounds!"  "My first fic"
''')
        self.story.setMetadata('datePublished',datetime.date(1972, 01, 31))
        self.story.setMetadata('dateCreated',datetime.datetime.now())
        self.story.setMetadata('dateUpdated',datetime.date(1975, 01, 31))
        self.story.setMetadata('numChapters','5')
        self.story.setMetadata('numWords','123456')
        self.story.setMetadata('status','In-Completed')
        self.story.setMetadata('rating','Tweenie')
        
        self.story.setMetadata('author','Test Author aa')
        self.story.setMetadata('authorId','98765')
        self.story.setMetadata('authorUrl','http://author/url')

        self.story.addToList('warnings','Swearing')
        self.story.addToList('warnings','Violence')

        self.story.addToList('category','Harry Potter')
        self.story.addToList('category','Furbie')
        self.story.addToList('category','Crossover')
        
        self.story.addToList('genre','Fantasy')
        self.story.addToList('genre','SF')
        self.story.addToList('genre','Noir')
        
        self.chapterUrls = [(u'Prologue '+self.crazystring,self.url+"&chapter=1"),
                            ('Chapter 1, Xenos on Cinnabar',self.url+"&chapter=2"),
                            ('Chapter 2, Sinmay on Kintikin',self.url+"&chapter=3"),
                            ('Chapter 3, Over Cinnabar',self.url+"&chapter=4"),
                            ('Epilogue',self.url+"&chapter=5")]
                            

    def getChapterText(self, url):
#        return "<p>Really short chapter</p>"
#         return u'''
# <div id=storytext class=storytext><p>&#8220;It might be all it takes.&#8221; He held out his hand and shook Wilfred&#8217;s, he glanced at the Vinvocci woman as she knelt there cradling the body of her partner, and he said not a word.<br /></p><p><b>Disclaimer: I don't own Harry Potter or the craziness of Romilda Vane.</b></p><p><b>*EDIT* Romilda is in her 4th year, like she always has.</b></p><p><b>Thanks xxSkitten for Beta reading this! :D<br></b></p><p><b>Full Summary: Harry and Ginny are together. Romilda Vane is not happy. She can't stand seeing the guy she </b><i><b>wants</b></i><b> to be with the person she </b><i><b>deserves</b></i><b> to be with, with another girl - especially a girl younger that is far less pretty than her. She orders 100 Love potions from Weasley's Wizard Wheezes, Wonder Witch line. Several get to undesired targets, such as Ron Weasley. What happens when Ginny takes matters into her own hands?</b></p><p><b><hr size=1 noshade></b></p><p><b><u>Romilda Vane (3rd Person)</u></b></p><p>"Th-Tha-That little skank!" snarled Romilda Vane as she watched Harry Potter and Ginny Weasley from the balcony overlooking the common room.</p><p>"Romilda," said Abigail Stones, one of her friends, "Lets go, you don't need to watch this."</p><p>Abigail stones had long, sleek black hair that was always in a high ponytail. She had pale skin that very few blemishes. She had a long, blocky nose and a small mouth. Her hazel eyes were behind think horned rimmed glasses, and her uniform was in order without a crease or wrinkle in sight.</p><p>"What does he <i>see</i> in her?" Romilda snarled in a whisper, her eyes upon the red-headed fifth year. "I mean, she's all freckle-y and gingery, she's a filthy fifth year-"</p><p>"And you're a fourth year!" Abigail interjected, but Romilda just kept on ranting.</p><p>"…and I heard they live in a dump!" Her nostrils flared.</p><p>"Well what are you going to do about it, just sit and watch them all the time?" Piped up Charlotte Henderson, the second of Romilda's present friends. She had curly shoulder length blonde hair and wore a thick layer of make up to cover up her various large red pimples. Her eyes were dark blue and were surrounded with large clumpy eyelashes. She had an eager expression, like she was witnessing two people on a Muggle drama who were about to kiss.</p><p>"Of course not!" She said, looking away as Ginny kissed Harry. "I've ordered one-hundred love potions from that Wonder Witch line from Weasley's Wizard Wheezes, so once I get him in my grasp I'll have him for the rest of the year!"</p><p>"You realize," Abigail said, rolling her eyes slightly. "That with your luck, you'll get every guy in the school but him."</p><p>"It will only be for around an hour, and I could always just make him jealous by making every guy close to him fall in love with me."</p><p>Abigail sighed, "One, he has a girlfriend. Two, you already got his best friend and he <i>wasn't</i> jealous, he was pissed, and three, you'll get expelled before you can get to him."</p><p>"Sometimes I wonder how we're friends!" Romilda snapped at Abigail.</p><p>"We're friends because you need a good influence around you, or you would be as crazy as Peeves." Abigail stated.</p><p>Romilda spun around to glare at her friend, knowing Abigail was right but did not daring to admit it.</p><p>The silence was broken by Charlotte. "So how are you going to slip him the potion?" She asked, honestly interested.</p><p>"Just wait 'till morning, and you'll see." Romilda said, looking back down at Harry, then suddenly realizing Ginny wasn't there.</p><p>Then, Ginny appeared next to them. She stalked through their group, not looking at any of them. She stopped at the girl's dorm door and turned her head slightly to see them from the corner of her eye.</p><p>"One-hundred? You're <i>that</i> desperate?" Ginny said with a mix of humor and anger. Then, the red-head turned to the door and left them all in a surprised state.</p><p>"You're screwed." Abigail said matter-of-factly. She went into the dorm without another word.</p><p>"She can be so insensitive." Charlotte said, looking where Abigail had left while shaking her head.</p><p>"You can say that again," mumbled Romilda, downcast.</p><p>"She can be-" Charlotte began again, but Romilda held her hand up.</p><p>"That was a figure of speech, pea-brain." She snapped. "Sometimes you can be as dumb as that Loony Lovegood." She then stalked up to her room with one last pleading look at Harry, whispering fiercely under her breath.</p><p>"You will be mine…"</p><hr size=1 noshade><p><b>Isn't Romilda Pleasant? ;] xD Oh she's crazy, insane, envious, has stalkerish and man stealing tendencies. and that's why she's everyone's FAVORITE character.</b></p><p><b>Also Romilda's in her fourth year. yeah. oh an NO FEMSLASH geez.<br></b></p><p><b>Also, Abigail Stones and Charlotte Henderson are to OC's that i made up on the spot because even crazies need friends. Ones the ignored good influence and ones a stereotypical dumb 'blonde' (NO OFFENSE TO BLONDES! I'm blonde and I don't take those things that personally unless their clearly mean that way. Also Charlotte's Muggle-Born so she watches all those Muggle TV's shows were all addicted too. ;] .. )</b></p><p><b>The rest of the story will be in Ginny's point of view whether its 1st or 3rd Person IDK yet but probably 1st person. The pairing in this are - Harry x Ginny / Romilda x Harry / Ron x Hermione (hints of) / Charolette x OC (Undetermined).</b></p><p><b>Reviews = Something... GOOD!</b></p><p><i><b>~ Sincerely MNM</b></i></p>

# </div>'''
        if self.story.getMetadata('storyId') == '667':
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!" % url)

        soup = bs.BeautifulStoneSoup(u'''
<div>
<h3>Chapter</h3>
<p><center>Centered text</center></p>
<p>Lorem '''+self.crazystring+''' <i>italics</i>, <b>bold</b>, <u>underline</u> consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
br breaks<br><br>
br breaks<br><br>
<hr>
horizontal rules
<hr>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
''',selfClosingTags=('br','hr')) # otherwise soup eats the br/hr tags.
        return utf8FromSoup(soup)

def getClass():
    return TestSiteAdapter

