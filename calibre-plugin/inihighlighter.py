# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2020, Jim Miller'
__docformat__ = 'restructuredtext en'

import re

import logging
logger = logging.getLogger(__name__)

from PyQt5.Qt import (QApplication, Qt, QColor, QSyntaxHighlighter,
                      QTextCharFormat, QBrush, QFont)

try:
    # qt6 Calibre v6+
    QFontNormal = QFont.Weight.Normal
    QFontBold = QFont.Weight.Bold
except:
    # qt5 Calibre v2-5
    QFontNormal = QFont.Normal
    QFontBold = QFont.Bold

from fanficfare.six import string_types

class IniHighlighter(QSyntaxHighlighter):
    '''
    QSyntaxHighlighter class for use with QTextEdit for highlighting
    ini config files.
    '''

    def __init__( self, parent, sections=[], keywords=[], entries=[], entry_keywords=[] ):
        QSyntaxHighlighter.__init__( self, parent )
        self.parent = parent

        self.highlightingRules = []

        colors = {
            'knownentries':Qt.darkGreen,
            'errors':Qt.red,
            'allkeywords':Qt.darkMagenta,
            'knownkeywords':Qt.blue,
            'knownsections':Qt.darkBlue,
            'teststories':Qt.darkCyan,
            'storyUrls':Qt.darkMagenta,
            'comments':Qt.darkYellow
            }
        try:
            if( hasattr(QApplication.instance(),'is_dark_theme')
                and QApplication.instance().is_dark_theme ):
                colors = {
                    'knownentries':Qt.green,
                    'errors':Qt.red,
                    'allkeywords':Qt.magenta,
                    'knownkeywords':QColor(Qt.blue).lighter(150),
                    'knownsections':Qt.darkCyan,
                    'teststories':Qt.cyan,
                    'storyUrls':QColor(Qt.magenta).lighter(150),
                    'comments':Qt.yellow
                    }
        except Exception as e:
            logger.error("Failed to set dark theme highlight colors: %s"%e)

        if entries:
            # *known* entries
            reentries = r'('+(r'|'.join(entries))+r')'
            self.highlightingRules.append( HighlightingRule( r"\b"+reentries+r"\b", colors['knownentries'] ) )

        # true/false -- just to be nice.
        self.highlightingRules.append( HighlightingRule( r"\b(true|false)\b", colors['knownentries'] ) )

        # *all* keywords -- change known later.
        self.errorRule = HighlightingRule( r"^[^:=\s][^:=]*[:=]", colors['errors'] )
        self.highlightingRules.append( self.errorRule )

        # *all* entry keywords -- change known later.
        reentrykeywords = r'('+(r'|'.join([ e % r'[a-zA-Z0-9_]+' for e in entry_keywords ]))+r')'
        self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+reentrykeywords+r"(_filelist)?\s*[:=]", colors['allkeywords'] ) )

        if entries: # separate from known entries so entry named keyword won't be masked.
            # *known* entry keywords
            reentrykeywords = r'('+(r'|'.join([ e % reentries for e in entry_keywords ]))+r')'
            self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+reentrykeywords+r"(_filelist)?\s*[:=]", colors['knownkeywords'] ) )

        # *known* keywords
        rekeywords = r'('+(r'|'.join(keywords))+r')'
        self.highlightingRules.append( HighlightingRule( r"^(add_to_)?"+rekeywords+r"(_filelist)?\s*[:=]", colors['knownkeywords'] ) )

        # *all* sections -- change known later.
        self.highlightingRules.append( HighlightingRule( r"^\[[^\]]+\].*?$", colors['errors'], QFontBold, blocknum=1 ) )

        if sections:
            # *known* sections
            resections = r'('+(r'|'.join(sections))+r')'
            resections = resections.replace('.','\.') #escape dots.
            self.highlightingRules.append( HighlightingRule( r"^\["+resections+r"\]\s*$", colors['knownsections'], QFontBold, blocknum=2 ) )

        # test story sections
        self.teststoryRule = HighlightingRule( r"^\[teststory:([0-9]+|defaults)\]", colors['teststories'], blocknum=3 )
        self.highlightingRules.append( self.teststoryRule )

        # storyUrl sections
        self.storyUrlRule = HighlightingRule( r"^\[https?://.*\]", colors['storyUrls'], blocknum=4 )
        self.highlightingRules.append( self.storyUrlRule )

        # NOT comments -- but can be custom columns, so don't flag.
        #self.highlightingRules.append( HighlightingRule( r"(?<!^)#[^\n]*" , colors['errors'] ) )

        # comments -- comments must start from column 0.
        self.commentRule = HighlightingRule( r"^#[^\n]*" , colors['comments'] )
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
                  weight=QFontNormal,
                  style=Qt.SolidPattern,
                  blocknum=0):
        if isinstance(pattern, string_types):
            self.pattern = re.compile(pattern)
        else:
            self.pattern=pattern
        charfmt = QTextCharFormat()
        brush = QBrush(color, style)
        charfmt.setForeground(brush)
        charfmt.setFontWeight(weight)
        self.highlight = charfmt
        self.blocknum=blocknum
