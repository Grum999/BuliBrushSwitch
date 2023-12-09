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
# The uitheme module provides a generic class to use to manage current theme
#
# Main class from this module
#
# - UITheme:
#       Main class to manage themes
#       Provide init ans static methods to load theme (icons, colors) according
#       to current Krita theme
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Build resources files:
#   cd .../.../resources
#   /usr/lib/qt5/bin/rcc --binary -o ./lighttheme_icons.rcc light_icons.qrc
#   /usr/lib/qt5/bin/rcc --binary -o ./darktheme_icons.rcc dark_icons.qrc
# -----------------------------------------------------------------------------

import os
import re

from PyQt5.QtCore import (
        QResource
    )
from PyQt5.QtGui import (
        QPalette,
        QPixmapCache,
        QColor
    )
from PyQt5.QtWidgets import (
        QApplication
    )


from ..pktk import *


# -----------------------------------------------------------------------------

class UITheme(object):
    """Manage theme

    By default, DARK and LIGHT themes are managed
    """

    DARK_THEME = 'dark'
    LIGHT_THEME = 'light'

    STYLES_SHEET = {
        'dark': {
                'warning-label': 'background-color: rgba(255, 255, 200, 75%); color:#C33700; border: 1px solid rgba(255, 255, 200, 25%); border-radius: 3px; font-weight: bold;',
                'warning-box': 'background-color: rgba(255, 255, 200, 100%); color:#C33700; border: 1px solid rgba(255, 255, 200, 100%); border-radius: 3px;',
                'error-bg': 'background-color: #882222; color: #ffffff; }',
                'warning-bg': 'background-color: #FFDD00; color: #DA490F; }'
            },
        'light': {
                'warning-label': 'background-color: rgba(255, 255, 200, 75%); color:#C33700; border: 1px solid rgba(255, 255, 200, 25%); border-radius: 3px; font-weight: bold;',
                'warning-box': 'background-color: rgba(255, 255, 200, 100%); color:#C33700; border: 1px solid rgba(255, 255, 200, 100%); border-radius: 3px;',
                'error-bg': 'background-color: #E47B78; color: #ffffff; }',
                'warning-bg': 'background-color: #ffffaa; color: #E77935; }'
            }
    }

    __themes = {}
    __kraActiveWindow = None

    @staticmethod
    def load(rccPath=None, autoReload=True):
        """Initialise theme"""
        import krita

        def initThemeChanged():
            # initialise theme when main window is created
            if UITheme.__kraActiveWindow is None:
                UITheme.__kraActiveWindow = Krita.instance().activeWindow()
                if UITheme.__kraActiveWindow is not None:
                    UITheme.__kraActiveWindow.themeChanged.connect(UITheme.reloadResources)

        if rccPath is None:
            # by default if no path is provided, load default PkTk theme
            rccPath = PkTk.PATH_RESOURCES

        if rccPath not in UITheme.__themes:
            UITheme.__themes[rccPath] = UITheme(rccPath, autoReload)

        # Initialise connector on theme changed
        initThemeChanged()

        # If not initialised (main window not yet created), initialise it when main window is created
        if UITheme.__kraActiveWindow is None:
            Krita.instance().notifier().windowCreated.connect(initThemeChanged)

    @staticmethod
    def reloadResources(clearPixmapCache=None):
        """Reload resources"""
        if clearPixmapCache is None:
            clearPixmapCache = True
        for theme in UITheme.__themes:
            if UITheme.__themes[theme].getAutoReload():
                # reload
                UITheme.__themes[theme].loadResources(clearPixmapCache)
                if clearPixmapCache:
                    clearPixmapCache = False

    @staticmethod
    def style(name):
        """Return style according to current theme"""
        for theme in UITheme.__themes:
            # return style from first theme (should be the same for all themes)
            return UITheme.__themes[theme].getStyle(name)

    @staticmethod
    def theme():
        """Return style according to current theme"""
        for theme in UITheme.__themes:
            # return style from first theme (should be the same for all themes)
            return UITheme.__themes[theme].getTheme()

    def __init__(self, rccPath, autoReload=True):
        """The given `rccPath` is full path to directory where .rcc files can be found
        If None, default resources from PkTk will be loaded

        The .rcc file names must match the following pattern:
        - darktheme_icons.rcc
        - lighttheme_icons.rcc


        If `autoReload` is True, theme is reloaded automatically when theme is changed
        Otherwise it have to be implemented explicitely in plugin
        """
        self.__theme = UITheme.DARK_THEME
        self.__registeredResource = None
        self.__rccPath = rccPath
        self.__autoReload = autoReload
        self.__kraActiveWindow = None

        self.loadResources(False)

    def loadResources(self, clearPixmapCache=True):
        """Load resources for current theme"""
        # Need to clear pixmap cache otherwise some icons are not reloaded from new resource file
        if clearPixmapCache:
            QPixmapCache.clear()

        if self.__registeredResource is not None:
            QResource.unregisterResource(self.__registeredResource)

        palette = QApplication.palette()

        if palette.color(QPalette.Window).value() <= 128:
            self.__theme = UITheme.DARK_THEME
        else:
            self.__theme = UITheme.LIGHT_THEME

        if re.search(r"\.rcc$", self.__rccPath):
            self.__registeredResource = self.__rccPath
        else:
            self.__registeredResource = os.path.join(self.__rccPath, f'{self.__theme}theme_icons.rcc')

        if not QResource.registerResource(self.__registeredResource):
            self.__registeredResource = None

    def getTheme(self):
        """Return current theme"""
        return self.__theme

    def getStyle(self, name):
        """Return style according to current theme"""
        if name in UITheme.STYLES_SHEET[self.__theme]:
            return UITheme.STYLES_SHEET[self.__theme][name]
        elif self.__theme != UITheme.DARK_THEME and name in UITheme.STYLES_SHEET[UITheme.DARK_THEME]:
            return UITheme.STYLES_SHEET[UITheme.DARK_THEME][name]
        return ''

    def getAutoReload(self):
        """Return if autoreload is activated for theme"""
        return self.__autoReload


class BaseTheme(object):
    """Base to define themes (used with WCodeEditor for example)

    Theme define global theme (foreground, background, gutter text, ...)
    TokenStyle, set through LanguageDef define colors to apply for a specific thme/language
    """
    def __init__(self, id, name, colors=None, baseTheme=None, comments=[]):
        if not isinstance(id, str) or id == '':
            raise EInvalidType('Given `id` must be non empty <str>')
        if not isinstance(name, str) or name == '':
            raise EInvalidType('Given `name` must be non empty <str>')
        if not (baseTheme is None or baseTheme in (UITheme.DARK_THEME, UITheme.LIGHT_THEME)):
            raise EInvalidType('Given `baseTheme` must be None, UITheme.DARK_THEME or UITheme.LIGHT_THEME')
        if not isinstance(comments, list):
            raise EInvalidType('Given `comments` must be a <list> of <str>')
        self.__id = id
        self.__name = name
        self.__baseTheme = baseTheme
        self.__colors = {}
        self.__comments = comments
        while len(self.__comments) < 2:
            self.__comments.append('')

        if isinstance(colors, dict):
            for key, value in colors.items():
                if not isinstance(key, str) or not isinstance(value, (str, QColor)):
                    raise EInvalidValue("Given colors must have a <str> key and a color <str> value")

                try:
                    self.__colors[key] = QColor(value)
                except Exception as e:
                    raise EInvalidValue("Given colors must have a <str> key and a color <str> value")
        elif isinstance(colors, BaseTheme):
            self.fromTheme(colors)
            if self.__baseTheme is None:
                self.__baseTheme = colors.baseTheme()

    def __repr__(self):
        return f"<{self.__class__.__name__}('{self.__id}', '{self.__name}', {self.__baseTheme}, {self.__colors})>"

    def id(self):
        """Return theme identifier"""
        return self.__id

    def name(self):
        """Return theme name"""
        return self.__name

    def baseTheme(self):
        """Return UITheme 'dark' or 'light' associated with current theme"""
        return self.__baseTheme

    def comments(self):
        """Return theme's comments"""
        return self.__comments

    def color(self, colorId):
        if colorId in self.__colors:
            return self.__colors[colorId]

        raise EInvalidValue("Given `colorId` is not a value identifier")

    def toDict(self):
        """Export theme as dictionnary

        {
            'id': '',
            'name': '',
            'comments': [],
            'colors': {
                <key>: <value>      # value is a color as string '#aarrggbb'
            }
        }
        """
        return {
                'id': self.__id,
                'name': self.__name,
                'comments': self.__comments,
                'colors': {id: color.name(QColor.HexArgb) for id, color in self.__colors.items()}
            }

    def fromDict(self, source):
        """Import theme from a dictionnary"""
        if not isinstance(source, dict):
            raise EInvalidType("Given `source` must be a <dict>")
        elif 'id' not in source or not isinstance(source['id'], str) or source['id'] == '':
            raise EInvalidValue("Given `source` must contain 'id' key, with a non empty <string> value")
        elif 'name' not in source or not isinstance(source['name'], str) or source['name'] == '':
            raise EInvalidValue("Given `source` must contain 'name' key, with a non empty <str> value")
        elif 'comments' not in source or not isinstance(source['comments'], list):
            raise EInvalidValue("Given `source` must contain 'comments' key as <list> of <str>")
        elif 'colors' not in source:
            raise EInvalidValue("Given `source` must contain 'colors' key")

        self.__id = source['id']
        self.__name = source['name']
        self.__comments = source['comments']
        while len(self.__comments) < 2:
            self.__comments.append('')

        self.__colors = {}
        for key, value in source['colors'].items():
            if not isinstance(key, str) or not isinstance(value, (QColor, str)):
                raise EInvalidValue("Given colors must have a <str> key and a color <str> value")
            try:
                self.__colors[key] = QColor(value)
            except Exception as e:
                raise EInvalidValue("Given colors must have a <str> key and a color <str> value")

    def fromTheme(self, source):
        """Import theme from a BaseTheme"""
        if not isinstance(source, BaseTheme):
            raise EInvalidType("Given `source` must be a <BaseTheme>")
        self.fromDict(source.toDict())
