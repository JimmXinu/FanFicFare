# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2017, Jim Miller'
__docformat__ = 'restructuredtext en'

import re

try:
    from PyQt5.Qt import (Qt, QSyntaxHighlighter, QTextCharFormat, QBrush, QFont)
except ImportError as e:
    from PyQt4.Qt import (Qt, QSyntaxHighlighter, QTextCharFormat, QBrush, QFont)

class IniHighlighter(QSyntaxHighlighter):
    '''
    QSyntaxHighlighter class for use with QTextEdit for highlighting
    ini config files.
    '''

    def __init__( self, parent, sections=[], keywords=[], entries=[], entry_keywords=[] ):
        QSyntaxHighlighter.__init__( self, parent )
        self.parent = parent

        self.highlightingRules = []

        if entries:
            # *known* entries
            reentries = r'('+(r'|'.join(entries))+r')'
            self.highlightingRules.append( HighlightingRule( r"\b"+reentries+r"\b", Qt.darkGreen ) )

        # true/false -- just to be nice.
        self.highlightingRules.append( HighlightingRule( r"\b(true|false)\b", Qt.darkGreen ) )

        # *all* keywords -- change known later.
        self.errorRule = HighlightingRule( r"^[^:=\s][^:=]*[:=]", Qt.red )
        self.highlightingRules.append( self.errorRule )

        # *all* entry keywords -- change known later.
        reentrykeywords = r'('+(r'|'.join([ e % r'[a-zA-Z0-9_]+' for e in entry_keywords ]))+r')'
        self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+reentrykeywords+r"(_filelist)?\s*[:=]", Qt.darkMagenta ) )

        if entries: # separate from known entries so entry named keyword won't be masked.
            # *known* entry keywords
            reentrykeywords = r'('+(r'|'.join([ e % reentries for e in entry_keywords ]))+r')'
            self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+reentrykeywords+r"(_filelist)?\s*[:=]", Qt.blue ) )

        # *known* keywords
        rekeywords = r'('+(r'|'.join(keywords))+r')'
        self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+rekeywords+r"(_filelist)?\s*[:=]", Qt.blue ) )

        # *all* sections -- change known later.
        self.highlightingRules.append( HighlightingRule( r"^\[[^\]]+\].*?$", Qt.red, QFont.Bold, blocknum=1 ) )

        if sections:
            # *known* sections
            resections = r'('+(r'|'.join(sections))+r')'
            resections = resections.replace('.','\.') #escape dots.
            self.highlightingRules.append( HighlightingRule( r"^\["+resections+r"\]\s*$", Qt.darkBlue, QFont.Bold, blocknum=2 ) )

        # test story sections
        self.teststoryRule = HighlightingRule( r"^\[teststory:([0-9]+|defaults)\]", Qt.darkCyan, blocknum=3 )
        self.highlightingRules.append( self.teststoryRule )

        # storyUrl sections
        self.storyUrlRule = HighlightingRule( r"^\[https?://.*\]", Qt.darkMagenta, blocknum=4 )
        self.highlightingRules.append( self.storyUrlRule )

        # NOT comments -- but can be custom columns, so don't flag.
        #self.highlightingRules.append( HighlightingRule( r"(?<!^)#[^\n]*" , Qt.red ) )

        # comments -- comments must start from column 0.
        self.commentRule = HighlightingRule( r"^#[^\n]*" , Qt.darkYellow )
        self.highlightingRules.append( self.commentRule )

    def highlightBlock( self, text ):

        is_comment = False
        blocknum = self.previousBlockState()
        for rule in self.highlightingRules:
            for match in rule.pattern.finditer(text):
                self.setFormat( match.start(), match.end()-match.start(), rule.highlight )
                if rule == self.commentRule:
                    is_comment = True
                if rule.blocknum > 0:
                    blocknum = rule.blocknum

        if not is_comment:
            # unknown section, error all:
            if blocknum == 1 and blocknum == self.previousBlockState():
                self.setFormat( 0, len(text), self.errorRule.highlight )

            # teststory section rules:
            if blocknum == 3:
                self.setFormat( 0, len(text), self.teststoryRule.highlight )

            # storyUrl section rules:
            if blocknum == 4:
                self.setFormat( 0, len(text), self.storyUrlRule.highlight )

        self.setCurrentBlockState( blocknum )

class HighlightingRule():
    def __init__( self, pattern, color,
                  weight=QFont.Normal,
                  style=Qt.SolidPattern,
                  blocknum=0):
        if isinstance(pattern,basestring):
            self.pattern = re.compile(pattern)
        else:
            self.pattern=pattern
        charfmt = QTextCharFormat()
        brush = QBrush(color, style)
        charfmt.setForeground(brush)
        charfmt.setFontWeight(weight)
        self.highlight = charfmt
        self.blocknum=blocknum
