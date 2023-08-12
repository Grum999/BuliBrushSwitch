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
# The wtoolbarbutton module provides a QToolButton that allows to display icon
# exactly as Krita does with "Choose Brush Preset" button
#
# To render button, use similar code than kis_iconwidget
#   https://invent.kde.org/graphics/krita/-/blob/master/libs/ui/widgets/kis_iconwidget.cc
#
# Main class from this module
#
# - WToolbarButton:
#       Widget
#       A toolbar button
#
# -----------------------------------------------------------------------------

from math import ceil

import PyQt5.uic

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QToolButton
    )
from PyQt5.QtGui import (
        QPixmap,
        QPainter,
        QIcon,
        QRegion
    )


class WToolbarButton(QToolButton):
    """A button for Krita toolbar"""

    BORDER = 3

    def __init__(self, label=None, parent=None):
        super(WToolbarButton, self).__init__(parent)
        self.__pixmapCache = None

    def __updatePixmapCache(self):
        """Regenerate pixmap cache"""
        self.__iconWidth = self.width() - (WToolbarButton.BORDER * 2)
        self.__iconHeight = self.height() - (WToolbarButton.BORDER * 2)

        self.__pixmapCache = QPixmap(round(self.__iconWidth * self.devicePixelRatioF()), round(self.__iconHeight * self.devicePixelRatioF()))
        self.__pixmapCache.setDevicePixelRatio(self.devicePixelRatioF())
        self.__pixmapCache.fill(Qt.transparent)

        # Round off the corners of the preview
        clipRegion = QRegion(0, 0, self.__iconWidth, self.__iconHeight)
        clipRegion -= QRegion(0, 0, 1, 1)
        clipRegion -= QRegion(self.__iconWidth - 1, 0, 1, 1)
        clipRegion -= QRegion(self.__iconWidth - 1, self.__iconHeight - 1, 1, 1)
        clipRegion -= QRegion(0, self.__iconHeight - 1, 1, 1)

        painter = QPainter(self.__pixmapCache)
        painter.setClipRegion(clipRegion)
        painter.setClipping(True)
        painter.drawPixmap(0, 0, self.icon().pixmap(self.__pixmapCache.width(), self.__pixmapCache.height()))
        painter.end()
        self.update()

    def resizeEvent(self, event):
        """Widget has been resized, need to refresh pixmap cache"""
        super(WToolbarButton, self).resizeEvent(event)
        self.__updatePixmapCache()

    def setIcon(self, icon):
        """Set button icon, need to refresh pixmap cache"""
        super(WToolbarButton, self).setIcon(icon)
        self.__updatePixmapCache()

    def paintEvent(self, event):
        """Paint button"""
        painter = QStylePainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)

        opt.iconSize = QSize(self.__iconWidth, self.__iconHeight)
        opt.icon = QIcon(self.__pixmapCache)
        opt.toolButtonStyle = Qt.ToolButtonIconOnly

        painter.drawComplexControl(QStyle.CC_ToolButton, opt)
