#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
# Author:        Pau Sanchez (contact@pausanchez.com)
# Version:       v1.0
# Last Modified: 2010/09/15
# 
# For the latest version check out:
#   http://www.codigomanso.com/en/projects
# 
# My blog:
#   http://www.codigomanso.com/en/  - English Version
#   http://www.codigomanso.com/es/  - Spanish Version
#

from bbcodeparser import bbcodeparser
from bbcodebuilder import bbcodebuilder

import random
import unittest

class BBCodeTests(unittest.TestCase):
  def setUp (self):
    self.bbcode = bbcodeparser()
    return

  def testConstructor (self):
    self.assertEqual (bbcodeparser ('whatever').html(), 'whatever')
    self.assertEqual (bbcodeparser ('[b]bold[/b]').html(), '<b>bold</b>')
    self.assertEqual (str (bbcodeparser ('[b]bold[/b]')), '[b]bold[/b]')
    return

  def testBold (self):
    self.assertEqual (self.bbcode.parse ('whatever').html(), 'whatever')
    self.assertEqual (self.bbcode.parse ('[b]bold[/b]').html(), '<b>bold</b>')
    self.assertEqual (self.bbcode.parse ('[B]bold[/b]').html(), '<b>bold</b>')
    self.assertEqual (self.bbcode.parse ('this is [B]bold[/B]').html(), 'this is <b>bold</b>')
    return

  def testItalic (self):
    self.assertEqual (self.bbcode.parse ('[i]italic[/i]').html(), '<i>italic</i>')
    return

  def testUnderline (self):
    self.assertEqual (self.bbcode.parse ('[u]italic[/u]').html(), '<u>italic</u>')
    return

  def testURLs (self):
    self.assertEqual (
      self.bbcode.parse ('[url]http://www.google.com[/url]').html(),
      '<a href="http://www.google.com">http://www.google.com</a>'
    )
    self.assertEqual (
      self.bbcode.parse ('[url=http://www.google.com]Google[/url]').html(),
      '<a href="http://www.google.com">Google</a>'
    )
    self.assertEqual (
      self.bbcode.parse ('[url="http://www.google.com"]Google[/url]').html(),
      '<a href="http://www.google.com">Google</a>'
    )
    self.assertEqual (
      self.bbcode.parse ('[url="http://www.google.com" title="Search Engine"]Google[/url]').html(),
      '<a href="http://www.google.com" title="Search Engine">Google</a>'
    )
    self.assertEqual (
      self.bbcode.parse ('[url link="http://www.google.com"]Google[/url]').html(),
      '<a href="http://www.google.com">Google</a>'
    )
    return

  def testPTag (self):
    self.assertEqual (
      self.bbcode.parse ('[p color=#0000ff]blue[/p]').html(),
      u'<p style="color: #0000ff;">blue</p>'
    )
    self.assertEqual (
      self.bbcode.parse ('[p size=12]12pt font[/p]').html(),
      u'<p style="font-size: 12pt;">12pt font</p>'
    )

    self.assertEqual (
      self.bbcode.parse ('[p font=arial]arial[/p]').html(),
      u'<p style="font-family: arial;">arial</p>'
    )

    self.assertEqual (
      self.bbcode.parse ('[p font=arial color=blue size=14]blue 14pt arial').html(),
      u'<p style="color: blue; font-size: 14pt; font-family: arial;">blue 14pt arial</p>' 
    )

    self.assertEqual (
      self.bbcode.parse ('[p class=whatever]text[/p]').html(),
      u'<p>text</p>' 
    )
    return

  def testColorTag (self):
    self.assertEqual (
      self.bbcode.parse ('[color=#0000ff]blue[/color]').html(),
      u'<span style="color: #0000ff;">blue</span>'
    )
    return

  def testSizeTag (self):
    self.assertEqual (
      self.bbcode.parse ('[size=12]12pt font[/size]').html(),
      u'<span style="font-size: 12pt;">12pt font</span>'
    )
    return

  def testEmail(self):
    self.assertEqual (
      self.bbcode.parse ('[email]asdf@asdf.com[/email]').html(),
      u'<a href="mailto:asdf@asdf.com">asdf@asdf.com</a>'
    )

    self.assertEqual (
      self.bbcode.parse ('[email=john@smith.com]John Smith[/email]').html(),
      u'<a href="mailto:john@smith.com">John Smith</a>'
    )
    return

  def testImgTag (self):
    self.assertEqual (
      self.bbcode.parse ('[img]http://www.codigomanso.com/image.jpg[/img]').html(),
      u'<img src="http://www.codigomanso.com/image.jpg" />'
    )

    self.assertEqual (
      self.bbcode.parse ('[img="This is the ALT of the image"]http://www.codigomanso.com/image.jpg[/img]').html(),
      u'<img alt="This is the ALT of the image" src="http://www.codigomanso.com/image.jpg" />'
    )

    self.assertEqual (
      self.bbcode.parse ('[img=320x200]http://www.codigomanso.com/image.jpg[/img]').html(),
      u'<img height="200" src="http://www.codigomanso.com/image.jpg" width="320" />'
    )

    self.assertEqual (
      self.bbcode.parse ('[img=320x200 title="Image Test"]http://www.codigomanso.com/image.jpg[/img]').html(),
      u'<img height="200" src="http://www.codigomanso.com/image.jpg" title="Image Test" width="320" />'
    )

    self.assertEqual (
      self.bbcode.parse ('[img="whatever" width=320 height="212" title="Image Test"]http://www.codigomanso.com/image.jpg[/img]').html(),
      u'<img alt="whatever" height="212" src="http://www.codigomanso.com/image.jpg" title="Image Test" width="320" />'
    )
    return

  def testGoogleURL (self):
    self.assertEqual (
      self.bbcode.parse ('[google]asdf[/google]').html(),
      u'<a href="http://www.google.com/search?q=asdf">asdf</a>'
    )
    self.assertEqual (
      self.bbcode.parse ('[google]Tom Hanks[/google]').html(),
      u'<a href="http://www.google.com/search?q=Tom+Hanks">Tom Hanks</a>'
    )
    return
    
  def testWikipediaURL (self):
    self.assertEqual (
      self.bbcode.parse ('[wikipedia]Tom Hanks[/wikipedia]').html(),
      u'<a href="http://www.wikipedia.org/wiki/Tom_Hanks">Tom Hanks</a>'
    )

    self.assertEqual (
      self.bbcode.parse ('[wikipedia language=en]Tom Hanks[/wikipedia]').html(),
      u'<a href="http://en.wikipedia.org/wiki/Tom_Hanks">Tom Hanks</a>'
    )
    
    self.assertEqual (
      self.bbcode.parse ('[wikipedia lang=es]Tom Hanks[/wikipedia]').html(),
      u'<a href="http://es.wikipedia.org/wiki/Tom_Hanks">Tom Hanks</a>'
    )
    
    self.assertEqual (
      self.bbcode.parse ('[wikipedia=es]Tom Hanks[/wikipedia]').html(),
      u'<a href="http://es.wikipedia.org/wiki/Tom_Hanks">Tom Hanks</a>'
    )
    return
    
  def testListTags (self):
    self.assertEqual (
      self.bbcode.parse ('[ul][li]item 1[/li][li]item 2[/li][/ul]').html(),
      u'<ul><li>item 1</li><li>item 2</li></ul>'
    )
    
    self.assertEqual (
      self.bbcode.parse ('[ol][li]item 1[/li][li]item 2[/li][/ol]').html(),
      u'<ol><li>item 1</li><li>item 2</li></ol>'
    )

    self.assertEqual (
      self.bbcode.parse ('[list][li]item 1[/li][li]item 2[/li][/list]').html(),
      u'<ul><li>item 1</li><li>item 2</li></ul>'
    )

    self.assertEqual (
      self.bbcode.parse ('[list][*]item 1[*]item 2[/list]').html(),
      u'<ul><li>item 1</li><li>item 2</li></ul>'
    )

    self.assertEqual (
      self.bbcode.parse ('[list=1][li]item 1[/li][li]item 2[/li][/list]').html(),
      u'<ol type="1"><li>item 1</li><li>item 2</li></ol>'
    )
    return

  def testInvalidCode (self):
    self.assertEqual (self.bbcode.parse ('[invalid]valid text[/invalid]').html(), 'valid text')
    self.assertEqual (
      self.bbcode.parse ('[b]bold and [i]italics[/b]').html(),
      '<b>bold and <i>italics</i></b>'
    )
    self.assertEqual (
      self.bbcode.parse ('[/b]invalid[/b][/p]').html(),
      'invalid'
    )
    self.assertEqual (
      self.bbcode.parse ('[p][b]bold').html(),
      '<p><b>bold</b></p>'
    )
    self.assertEqual (
      self.bbcode.parse ('[p][b]a <b>').html(),
      '<p><b>a &lt;b&gt;</b></p>'
    )

    self.assertEqual (
      self.bbcode.parse ('[ol][li]item 1[li]item 2[/li][/ol]').html(),
      u'<ol><li>item 1</li><li>item 2</li></ol>'
    )

    self.assertEqual (
      self.bbcode.parse ('[b]\[b\] stands for [b]bold[/b]').html(),
      u'<b>[b] stands for </b><b>bold</b>'
    )
    return

  def testEscapedBrackets (self):
    self.assertEqual (
      self.bbcode.parse ('\[b\]not bold\[/b\]').html(),
      u'[b]not bold[/b]'
    )

    self.assertEqual (
      self.bbcode.parse ('[b]\[b\] stands for bold[/b]').html(),
      u'<b>[b] stands for bold</b>'
    )

    self.assertEqual (
      self.bbcode.parse ('\[b\][b]stands for bold[/b]').html(),
      u'[b]<b>stands for bold</b>'
    )

    self.assertEqual (
      self.bbcode.parse ('\[b\][b]stands for bold[/b] just like <b> in HTML').html(),
      u'[b]<b>stands for bold</b> just like &lt;b&gt; in HTML'
    )

  def testBigExample (self):
    inputText = """check this out

    [h1 class=circle]heading[/h1]

    [p size=14 color=blue font="verdana, Times New Roman"]This is [b] bold [/b] and this [i]italic[/i] and this is [color=red]red[/color] and this is [color="red"]also red[/color].
    [/p]

    fix [b][i]bold [font=verdana][size=12]and[/size][/font] italic[/b]
    [img]http://www.codigomanso.com/b.jpg[/img]
    [url]http://www.codigomanso.com/[/url]
    [url=http://www.codigomanso.com/]Codigo Manso[/url]
    [uRl link=http://www.codigomanso.com title="Codigo Manso Blog"]Codigo Manso[/url]

    [ul]
     [Li]item 1[/Li]
     [li]item 2[/LI]
    [/UL]

    [list=1 ]
     [*]item 1
     [*]item 2
    [/list]

    [table class="big"]
      [tr]
        [th]big[/th]
      [/tr]
    [/table]
    [invalid class="extra"]whatever[/invalid]"""

    out = self.bbcode.parse (inputText).html(allowClassAttr = True)
    self.assertEquals (out, '''check this out

    <h1 class="circle">heading</h1>

    <p style="color: blue; font-size: 14pt; font-family: verdana, Times New Roman;">This is <b> bold </b> and this <i>italic</i> and this is <span style="color: red;">red</span> and this is <span style="color: red;">also red</span>.
    </p>

    fix <b><i>bold <span style="font-family: verdana;"><span style="font-size: 12pt;">and</span></span> italic</i></b>
    <img src="http://www.codigomanso.com/b.jpg" />
    <a href="http://www.codigomanso.com/">http://www.codigomanso.com/</a>
    <a href="http://www.codigomanso.com/">Codigo Manso</a>
    <a href="http://www.codigomanso.com" title="Codigo Manso Blog">Codigo Manso</a>

    <ul>
     <li>item 1</li>
     <li>item 2</li>
    </ul>

    <ol type="1">
     <li>item 1
     </li><li>item 2
    </li></ol>

    <table class="big">
      <tr>
        <th>big</th>
      </tr>
    </table>
    whatever''')


  def testBBCodeDumper (self):
    self.assertEquals (
      self.bbcode.parse ('[b]bold[/b]').bbcode(),
      '[b]bold[/b]'
    )

    self.assertEquals (
      self.bbcode.parse ('[color=red]text in red[/color]').bbcode(),
      '[color=red]text in red[/color]'
    )
    self.assertEquals (
      self.bbcode.parse ('[p][color=red]text in red').bbcode(),
      '[p][color=red]text in red[/color][/p]'
    )

    self.assertEquals (
      self.bbcode.parse ('This [b][i]code[/b] will be fixed[/invalid]').bbcode(),
      'This [b][i]code[/i][/b] will be fixed'
    )

    self.assertEquals (
      self.bbcode.parse ('\[[url]http://www.codigomanso.com/en[/url]\]').bbcode(),
      "\[[url]http://www.codigomanso.com/en[/url]\]"
    )

  def performanceTest(self):
    '''
    This test checks the performance of parse and html operations

    To run this test type:
      > python test.py BBCodeTests.performanceTest
    '''
    inputText = """check this out

    [h1 class=circle]heading[/h1]

    [p size=14 color=blue font="verdana, Times New Roman"]This is [b] bold [/b] and this [i]italic[/i] and this is [color=red]red[/color] and this is [color="red"]also red[/color].
    [/p]

    fix [b][i]bold [font=verdana][size=12]and[/size][/font] italic[/b]
    [img]http://www.codigomanso.com/b.jpg[/img]
    [url]http://www.codigomanso.com/[/url]
    [url=http://www.codigomanso.com/]Codigo Manso[/url]
    [uRl link=http://www.codigomanso.com title="Codigo Manso Blog"]Codigo Manso[/url]

    [ul]
     [Li]item 1[/Li]
     [li]item 2[/LI]
    [/UL]

    [list=1 ]
     [*]item 1
     [*]item 2
    [/list]

    [table class="big"]
      [tr]
        [th]big[/th]
      [/tr]
    [/table]
    [invalid class="extra"]whatever[/invalid]"""

    import time
    start = time.time()

    for i in range(0, 12):
      inputText += inputText

    print "len(inputText) = %.2f MB  (took %.2f seconds)" % (len(inputText)/(1024.0*1024.0), time.time() - start)
    
    bbcode = bbcodeparser()
    start = time.time()
    bbcode.parse (inputText)
    total = (time.time() - start)
    print "time (bbcode.parse()) = %f" % total
    print "  >> %.2f chars/second" % (len(inputText) / total)

    start = time.time()
    bbcode.html(doDeepCopy = False)
    total = (time.time() - start)
    print "time (bbcode.html()) = %f" % total
    print "  >> %.2f chars/second" % (len(inputText) / total)
    return
    
  def testCodeBuilder (self):
    bbcode = bbcodebuilder ()
    self.assertEquals (bbcode.b ('bold'), u'[b]bold[/b]')
    self.assertEquals (bbcode.color ('this goes in red', 'red'), u'[color=red]this goes in red[/color]')
    self.assertEquals (bbcode.url ('Google', 'http://www.google.com'), u'[url=http://www.google.com]Google[/url]')
    self.assertEquals (bbcode.alist('item 1', 'item 2'), u"[list=a]\n  [*]item 1\n  [*]item 2\n[/list]")
    return

if __name__ == '__main__':
    unittest.main()



