# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2015, Jim Miller'
__docformat__ = 'restructuredtext en'

import re

from PyQt5.Qt import (Qt, QSyntaxHighlighter, QTextCharFormat, QBrush)

from fanficfare.six import string_types

class BasicIniHighlighter(QSyntaxHighlighter):
    '''
    QSyntaxHighlighter class for use with QTextEdit for highlighting
    ini config files.

    I looked high and low to find a high lighter for basic ini config
    format, so I'm leaving this in the project even though I'm not
    using.
    '''

    def __init__( self, parent, theme ):
        QSyntaxHighlighter.__init__( self, parent )
        self.parent = parent

        self.highlightingRules = []

        # keyword
        self.highlightingRules.append( HighlightingRule( r"^[^:=\s][^:=]*[:=]",
                                                         Qt.blue,
                                                         Qt.SolidPattern ) )

        # section
        self.highlightingRules.append( HighlightingRule( r"^\[[^\]]+\]",
                                                         Qt.darkBlue,
                                                         Qt.SolidPattern ) )

        # comment
        self.highlightingRules.append( HighlightingRule( r"#[^\n]*" ,
                                                         Qt.darkYellow,
                                                         Qt.SolidPattern ) )

    def highlightBlock( self, text ):
        for rule in self.highlightingRules:
            for match in rule.pattern.finditer(text):
                self.setFormat( match.start(), match.end()-match.start(), rule.highlight )
        self.setCurrentBlockState( 0 )

class HighlightingRule():
    def __init__( self, pattern, color, style ):
        if isinstance(pattern, string_types):
            self.pattern = re.compile(pattern)
        else:
            self.pattern=pattern
        charfmt = QTextCharFormat()
        brush = QBrush(color, style)
        charfmt.setForeground(brush)
        self.highlight = charfmt
