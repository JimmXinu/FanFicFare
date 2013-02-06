AUTHOR
  Pau Sanchez
  http://www.codigomanso.com/

VERSION:
  bbcodeutils v1.0
  
LICENSE
  This code is licensed under Creative Commons Attribution 3.0
  http://creativecommons.org/licenses/by/3.0/

  You can use this python module or any part of the code you want as long as you add
  my name as a contributor to your project.
  
DESCRIPTION
  This module can be used to produce HTML from BBCode, to generate BBCode or to fix invalid BBCode.

  The classes are:
    - bbcodeparser
    - bbcodebuilder
    - bbcode2html
  
  You can use bbcodeparser to parse BBCode and to produce output in any format you want.

  Open the python file to find more information and examples of use of each class. It can
  be a good idea to check the test.py for examples

  To run the unit tests:
    > python test.py
  
  To run the performance test:
    > python test.py BBCodeTests.performanceTest  


EXAMPLES OF BBCode:

  [b] -> bold
  [u] -> underline
  [i] -> italic

  [center] -> center the text inside
  [color=XXX] -> change color of text
  [size=XXX] -> change size of text

  Lists:
  [ul] -> unordered list
  [ol] -> ordered list
  [li] -> list item

  [list] -> start unordered list
  [*]    -> list item
  [list=1] -> start a list of numbers
  [list=a] -> start a list of alphabetic characters

  Advanced:
  [url] -> link to url
  [url=http://link/url/]text[/url]  
  [url link=http://link/url/ title="This is the title"]text[/url]  

  [img]http://to/image[/img]
  [img=230x330]http://to/image[/img]
  [img="Alt text here"]http://to/image[/img]
  [img="Alt text here" width=320 height=240]http://to/image[/img]

  [email]asdf@asdf.com[/email]
  [email=john@asdf.com]John Smith[/email]

  [google]search this[/google]
  [wikipedia]Tom Hanks[/wikipedia]
  [wikipedia lang=es]Tom Hanks[/wikipedia]

  Tables:
  [table]
  [tr]
  [th]
  [td]

  Advanced:
  [google]
  [wikipedia]

