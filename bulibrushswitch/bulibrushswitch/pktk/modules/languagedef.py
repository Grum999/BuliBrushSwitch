# -----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2022 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin framework
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# The languagedef module provides base class used to defined a language
# (that can be tokenized and parsed --> tokenizer + parser modules)
#
# Main class from this module
#
# - LanguageDef:
#       Base class to use to define language
#
# - LanguageDefXML
#       Basic XML language definition
#
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtGui import QColor

import re

from .tokenizer import (
            Token,
            TokenType,
            TokenStyle,
            Tokenizer,
            TokenizerRule
        )
from .uitheme import UITheme

from ..pktk import *


class LanguageDef:

    SEP_PRIMARY_VALUE = '\x01'              # define bounds for <value> and cursor position
    SEP_SECONDARY_VALUE = '\x02'            # define bounds for other values

    def __init__(self, rules=[], tokenType=None):
        """Initialise language & styles"""
        if tokenType is not None:
            self.__tokenType = tokenType
            self.__tokenTypeVars = [tt for tt in [getattr(self.__tokenType, tt) for tt in dir(self.__tokenType)] if isinstance(tt, self.__tokenType) and not callable(tt.value)]
        else:
            self.__tokenType = None
            self.__tokenTypeVars = []
        self.__tokenizer = Tokenizer(rules)
        self.__tokenStyle = TokenStyle()

    def __repr__(self):
        return f"<{self.__class__.name}({self.name()}, {self.extensions()})>"

    def name(self):
        """Return language name"""
        return "None"

    def extensions(self):
        """Return language file extension as list

        For example:
            ['.htm', '.html']

        """
        return []

    def tokenizer(self):
        """Return tokenizer for language"""
        return self.__tokenizer

    def setStyles(self, theme, styles):
        """Set styles for a given theme

        Given `styles` can be:
        - a list of tuples
            (tokenType, fgColor, bold, italic, bgColor=None)
        - a dict, for which
                key = tokentype (as strinf)
                value = dict {
                        'fg': <str>,
                        'bg': <str>,
                        'bold': <boolean>,
                        'italic': <boolean>
                    }
        """
        if isinstance(styles, list):
            # set token styles
            for style in styles:
                self.__tokenStyle.setStyle(theme, *style)
        elif isinstance(styles, dict) and len(self.__tokenTypeVars):
            # need to parse dict content
            computedStyles = []
            for tokenId in styles.keys():
                # loop on dictionary keys, assuming they are token type id
                for tokenType in self.__tokenTypeVars:
                    # lookup available token types for language definition
                    if tokenType.value[0] == tokenId:
                        # current entry in dictionnary match a token type, process it
                        computedStyle = [tokenType]

                        if 'fg' in styles[tokenId] and isinstance(styles[tokenId]['fg'], str) and re.search('^#[a-f0-9]{6}$', styles[tokenId]['fg'], re.I):
                            computedStyle.append(QColor(styles[tokenId]['fg']))
                        else:
                            computedStyle.append(None)

                        if 'bold' in styles[tokenId] and isinstance(styles[tokenId]['bold'], bool):
                            computedStyle.append(styles[tokenId]['bold'])
                        else:
                            computedStyle.append(False)

                        if 'italic' in styles[tokenId] and isinstance(styles[tokenId]['italic'], bool):
                            computedStyle.append(styles[tokenId]['italic'])
                        else:
                            computedStyle.append(False)

                        if 'bg' in styles[tokenId] and isinstance(styles[tokenId]['bg'], str) and re.search('^#[a-f0-9]{6}$', styles[tokenId]['fg'], re.I):
                            computedStyle.append(QColor(styles[tokenId]['bg']))
                        else:
                            computedStyle.append(None)

                        computedStyles.append(computedStyle)
                        break

            # now we have all style ready to be set
            self.setStyles(theme, computedStyles)

    def style(self, item):
        """Return style (from current theme) for given token and/or rule"""
        if isinstance(item, TokenType):
            return self.__tokenStyle.style(item)
        return self.__tokenStyle.style(item.type())

    def styles(self):
        """Return list of available styles for languagedef"""
        return self.__tokenStyle.styles()

    def clearStyles(self):
        """Remove ALL style, from all themes"""
        self.__tokenStyle.reset()

    def themes(self):
        """Return list of available theme for language"""
        return self.__tokenStyle.themes()

    def currentTheme(self):
        """Return current theme for language definition"""
        return self.__tokenStyle.theme()

    def setCurrentTheme(self, theme):
        """Set current theme for language definition"""
        self.__tokenStyle.setTheme(theme)

    def getTextProposal(self, text, full=False):
        """Return a list of possible values for given text

        return list of tuple (str, str, rule)
            str: autoCompletion value
            str: description
            rule: current rule
        """
        if not isinstance(text, str):
            raise EInvalidType('Given `text` must be str')

        rePattern = re.compile(re.escape(re.sub(r'\s+', '\x02', text)).replace('\x02', r'\s+')+'.*')
        returned = []
        for rule in self.__tokenizer.rules():
            values = rule.matchText(rePattern, full)
            if len(values) > 0:
                returned += values
        # return list without any duplicate values
        return list(set(returned))


class LanguageDefXML(LanguageDef):
    """Extent language definition for XML markup language"""

    class ITokenType(TokenType):
        STRING =        ('str', 'A STRING value')
        MARKUP =        ('markup', 'A XML Markup')
        ATTRIBUTE =     ('attribute', 'A node attribute')
        SETATTR =       ('set_attribute', 'Set attribute')
        CDATA =         ('cdata', 'A CDATA value')
        VALUE =         ('value', 'A VALUE value')
        SPECIALCHAR =   ('special_character', 'A SPECIAL CHARACTER value')

    def __init__(self):
        super(LanguageDefXML, self).__init__([
            TokenizerRule(LanguageDefXML.ITokenType.COMMENT,
                          r'<!--(.*?)-->',
                          multiLineStart=r'<!--',
                          multiLineEnd=r'-->'),
            TokenizerRule(LanguageDefXML.ITokenType.CDATA,
                          r'<!\[CDATA\[.*\]\]>',
                          multiLineStart=r'<!\[CDATA\[',
                          multiLineEnd=r'\]\]>'),
            TokenizerRule(LanguageDefXML.ITokenType.STRING, r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            TokenizerRule(LanguageDefXML.ITokenType.STRING, r"'[^'\\]*(?:\\.[^'\\]*)*'"),
            TokenizerRule(LanguageDefXML.ITokenType.MARKUP, r'<(?:\?xml|!DOCTYPE|!ELEMENT|\w[\w:-]*\b)'),
            TokenizerRule(LanguageDefXML.ITokenType.MARKUP, r'</\w[\w:-]*>'),
            TokenizerRule(LanguageDefXML.ITokenType.MARKUP, r'/?>|\?>'),
            TokenizerRule(LanguageDefXML.ITokenType.ATTRIBUTE, r'(?<=<[^>]*)\b\w[\w:-]*'),
            TokenizerRule(LanguageDefXML.ITokenType.ATTRIBUTE, r'\b\w[\w:-]*(?=\s*=)'),
            TokenizerRule(LanguageDefXML.ITokenType.SPECIALCHAR, r'&(?:amp|gt|lt|quot|apos|#\d+|#x[a-fA-F0-9]+);'),
            TokenizerRule(LanguageDefXML.ITokenType.SETATTR, r'='),
            TokenizerRule(LanguageDefXML.ITokenType.SPACE, r'\s+'),
            TokenizerRule(LanguageDefXML.ITokenType.VALUE, r'''[^<>'"&]*'''),
            ],
            LanguageDefXML.ITokenType)

        self.setStyles(UITheme.DARK_THEME, [
            (LanguageDefXML.ITokenType.STRING, '#98c379', False, False),
            (LanguageDefXML.ITokenType.MARKUP, '#c678dd', True, False),
            (LanguageDefXML.ITokenType.ATTRIBUTE, '#80bfff', False, False),
            (LanguageDefXML.ITokenType.SETATTR, '#ff66d9', False, False),
            (LanguageDefXML.ITokenType.CDATA, '#ffe066', False, True),
            (LanguageDefXML.ITokenType.VALUE, '#cccccc', False, False),
            (LanguageDefXML.ITokenType.SPECIALCHAR, '#ddc066', False, False),
            (LanguageDefXML.ITokenType.COMMENT, '#5c6370', False, True)
        ])
        self.setStyles(UITheme.LIGHT_THEME, [
            (LanguageDefXML.ITokenType.STRING, '#238800', False, False),
            (LanguageDefXML.ITokenType.MARKUP, '#9B0F83', True, False),
            (LanguageDefXML.ITokenType.ATTRIBUTE, '#e18890', False, False),
            (LanguageDefXML.ITokenType.SETATTR, '#DF0BEA', False, False),
            (LanguageDefXML.ITokenType.CDATA, '#78dac2', False, False),
            (LanguageDefXML.ITokenType.VALUE, '#82dde5', False, False),
            (LanguageDefXML.ITokenType.SPECIALCHAR, '#ddc066', False, False),
            (LanguageDefXML.ITokenType.COMMENT, '#5c6370', False, True)
        ])

    def name(self):
        """Return language name"""
        return "XML"

    def extensions(self):
        """Return language file extension as list"""
        return ['.xml', '.svg']


class LanguageDefJSON(LanguageDef):
    """Extent language definition for XML markup language"""

    class ITokenType(TokenType):
        OBJECT_ID =         ('object_id', 'Object identifier')
        OBJECT_DEFINITION = ('object_definition', 'Separator')
        OBJECT_SEPARATOR =  ('object_separator', 'Separator')
        OBJECT_MARKER_S =   ('object_marker_start', 'Start of Object')
        OBJECT_MARKER_E =   ('object_marker_end', 'End of Object')
        ARRAY_MARKER_S =    ('array_marker_start', 'Start of Array')
        ARRAY_MARKER_E =    ('array_marker_end', 'End of Array')
        STRING =            ('value_string', 'A STRING value')
        NUMBER =            ('value_number', 'A NUMBER value')
        SPECIAL_VALUE =     ('value_special', 'A special value')

    def __init__(self):
        super(LanguageDefJSON, self).__init__([
            TokenizerRule(LanguageDefJSON.ITokenType.OBJECT_ID, r'"[^"\\]*(?:\\.[^"\\]*)*"(?=\s*:)'),
            TokenizerRule(LanguageDefJSON.ITokenType.STRING, r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            TokenizerRule(LanguageDefJSON.ITokenType.NUMBER,
                          # float
                          r"-?(?:0\.|[1-9](?:\d*)\.)\d+(?:e[+-]?\d+)?",
                          caseInsensitive=True),
            TokenizerRule(LanguageDefJSON.ITokenType.NUMBER,
                          # integer
                          r"-?(?:[1-9]\d*)(?:e[+-]?\d+)?",
                          caseInsensitive=True),
            TokenizerRule(LanguageDefJSON.ITokenType.OBJECT_DEFINITION, r':'),
            TokenizerRule(LanguageDefJSON.ITokenType.OBJECT_SEPARATOR, r','),
            TokenizerRule(LanguageDefJSON.ITokenType.SPECIAL_VALUE, r'(?:true|false|null)'),
            TokenizerRule(LanguageDefJSON.ITokenType.OBJECT_MARKER_S, r'\{'),
            TokenizerRule(LanguageDefJSON.ITokenType.OBJECT_MARKER_E, r'\}'),
            TokenizerRule(LanguageDefJSON.ITokenType.ARRAY_MARKER_S, r'(?:\[)'),
            TokenizerRule(LanguageDefJSON.ITokenType.ARRAY_MARKER_E, r'(?:\])'),
            TokenizerRule(LanguageDefJSON.ITokenType.SPACE, r'\s+')
            ],
            LanguageDefJSON.ITokenType)

        self.setStyles(UITheme.DARK_THEME, [
            (LanguageDefJSON.ITokenType.OBJECT_ID, '#79c3cc', True, False),
            (LanguageDefJSON.ITokenType.STRING, '#98c379', False, False),
            (LanguageDefJSON.ITokenType.NUMBER, '#ffe066', False, True),
            (LanguageDefJSON.ITokenType.OBJECT_DEFINITION, '#ff66d9', True, False),
            (LanguageDefJSON.ITokenType.OBJECT_SEPARATOR, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.OBJECT_MARKER_S, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.OBJECT_MARKER_E, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.ARRAY_MARKER_S, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.ARRAY_MARKER_E, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.SPECIAL_VALUE, '#c678dd', False, False),
            (LanguageDefJSON.ITokenType.SPACE, None, False, False)
        ])
        self.setStyles(UITheme.LIGHT_THEME, [
            (LanguageDefJSON.ITokenType.OBJECT_ID, '#00019C', True, False),
            (LanguageDefJSON.ITokenType.STRING, '#238800', False, False),
            (LanguageDefJSON.ITokenType.NUMBER, '#D97814', False, True),
            (LanguageDefJSON.ITokenType.OBJECT_DEFINITION, '#ff66d9', True, False),
            (LanguageDefJSON.ITokenType.OBJECT_SEPARATOR, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.OBJECT_MARKER_S, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.OBJECT_MARKER_E, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.ARRAY_MARKER_S, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.ARRAY_MARKER_E, '#ff66d9', False, False),
            (LanguageDefJSON.ITokenType.SPECIAL_VALUE, '#c678dd', False, False),
            (LanguageDefJSON.ITokenType.SPACE, None, False, False)
        ])

    def name(self):
        """Return language name"""
        return "JSON"

    def extensions(self):
        """Return language file extension as list"""
        return ['.json']
