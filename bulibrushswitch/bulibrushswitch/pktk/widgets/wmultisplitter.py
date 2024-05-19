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
# The wmultispliiter module provides an advanced splitter widget
# - can automatically split horizontally or vertically the content
#
# Main class from this module
#
# - WMultiSpliiter:
#       The main widget
#
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from ..pktk import *


class WMultiSplitter(QWidget):
    """A splitter widget"""

    def __init__(self, parent=None):
        super(WMultiSplitter, self).__init__(parent)

        self.__splitter = QSplitter(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__splitter)

        self.setLayout(layout)

    def __addWidget(self, widget, split=None, index=None):
        if not isinstance(widget, QWidget):
            raise EInvalidType("Given widget `widget` must be a <QWidget>")

        if split is None or split == self.__splitter.orientation():
            self.__splitter.addWidget(widget)
            self.__splitter.setSizes([1000] * self.__splitter.count())
        elif split is not None and split != self.__splitter.orientation():
            if index is None or index == -1:
                index = self.__splitter.count() - 1

            newContainer = WMultiSplitter(self)
            newContainer.setOrientation(split)

            replacedWidget = self.__splitter.replaceWidget(index, newContainer)

            if split == Qt.Vertical:
                newContainer.addWidgetVertically(replacedWidget)
                newContainer.addWidgetVertically(widget)
            else:
                newContainer.addWidgetHorizontally(replacedWidget)
                newContainer.addWidgetHorizontally(widget)

    def orientation(self):
        """Return current orientation of splitter"""
        return self.__splitter.orientation()

    def setOrientation(self, orientation):
        """Define current orientation of splitter"""
        self.__splitter.setOrientation(orientation)

    def indexOf(self, widget):
        """Return index for given widget

        if widget is not found, return -1
        """
        if not isinstance(widget, QWidget):
            raise EInvalidType("Given widget `widget` must be a <QWidget>")

        return self.__splitter.indexOf(widget)

    def searchWidget(self, widget):
        """Search for given widget in current WMultiSplitter and childs

        if widget is not found, return None
        otherwise return a tuple (parent widget<WMultiSplitter>, index from parent, index from current)
        """
        # search in current widget
        if not isinstance(widget, QWidget):
            raise EInvalidType("Given widget `widget` must be a <QWidget>")

        index = self.__splitter.indexOf(widget)
        if index > -1:
            return (self, index, index)

        # maybe in children?
        for index in range(self.__splitter.count()):
            childWidget = self.__splitter.widget(index)
            if isinstance(childWidget, WMultiSplitter):
                found = childWidget.searchWidget(widget)
                if found:
                    return (found[0], found[1], index)

        # nothing found...
        return None

    def addWidget(self, widget):
        """Add a widget:
           - Use current split orientation
           - Added at the end

        Current content
        +------+------+                 +--------------+
        |0     |1     |                 |0 A           |
        |A     |B     |                 +--------------+
        |      |      |                 |1 B           |
        |      |      |                 +--------------+
        |      |      |
        +------+------+

        Added widget
        +------+------+------+          +--------------+
        |0     |1     |2     |          |0 A           |
        |A     |B     |new   |          +--------------+
        |      |      |      |          |1 B           |
        |      |      |      |          +--------------+
        |      |      |      |          |2 new         |
        +------+------+------+          +--------------+
        """
        self.__addWidget(widget)

    def addWidgetVertically(self, widget):
        """Add a widget vertically:
           - Added at the end

        Current content
        +------+------+                 +----------------+
        |0     |1     |                 |0 A             |
        |A     |B     |                 +----------------+
        |      |      |                 |1 B             |
        |      |      |                 +----------------+
        |      |      |
        +------+------+

        Added widget
        +------+------+------+          +----------------+
        |0     |1     |2     |          |0 A             |
        |A     |B     |new   |          +-------+--------+
        |      |      |      |          |1,0 B  |1,1 new |
        |      |      |      |          +-------+--------+
        |      |      |      |
        +------+------+------+
        """
        self.__addWidget(widget, Qt.Vertical)

    def addWidgetHorizontally(self, widget):
        """Add a widget horizontally:
           - Added at the end

        Current content
        +------+------+                 +--------------+
        |0     |1     |                 |0 A           |
        |A     |B     |                 +--------------+
        |      |      |                 |1 B           |
        |      |      |                 +--------------+
        |      |      |
        +------+------+

        Added widget
        +------+------+                 +--------------+
        |0     |1,0   |                 |0 A           |
        |A     |B     |                 +--------------+
        |      +------+                 |1 B           |
        |      |1,1   |                 +--------------+
        |      |new   |                 |2 new         |
        +------+------+                 +--------------+
        """
        self.__addWidget(widget, Qt.Horizontal)

    def insertWidget(self, widget, position):
        """Add a widget:
           - Use current split orientation
           - Added at given position

        Current content
        +------+------+------+          +--------------+
        |0     |1     |2     |          |0 A           |
        |A     |B     |C     |          +--------------+
        |      |      |      |          |1 B           |
        |      |      |      |          +--------------+
        |      |      |      |          |2 C           |
        +------+------+------+          +--------------+

        Insert widget at position 1
        +------+------+------+------+   +--------------+
        |0     |1     |2     |3     |   |0 A           |
        |A     |new   |B     |C     |   +--------------+
        |      |      |      |      |   |1 new         |
        |      |      |      |      |   +--------------+
        |      |      |      |      |   |2 B           |
        |      |      |      |      |   +--------------+
        |      |      |      |      |   |3 C           |
        +------+------+------+------+   +--------------+
        """
        self.__addWidget(widget)

    def insertWidgetVertically(self, widget, position):
        """Add a widget vertically:
           - Added at given position

        Current content
        +------+------+------+          +--------------+
        |0     |1     |2     |          |0 A           |
        |A     |B     |C     |          +--------------+
        |      |      |      |          |1 B           |
        |      |      |      |          +--------------+
        |      |      |      |          |2 C           |
        +------+------+------+          +--------------+

        Insert widget at position 1
        +------+------+------+------+   +---------------+
        |0     |1     |2     |3     |   |0 A            |
        |A     |new   |B     |C     |   +------+--------+
        |      |      |      |      |   |1,0 B |1,1 new |
        |      |      |      |      |   +------+--------+
        |      |      |      |      |   |2 C            |
        |      |      |      |      |   +---------------+
        |      |      |      |      |
        +------+------+------+------+
        """
        self.__addWidget(widget, Qt.Vertical, position)

    def insertWidgetHorizontally(self, widget, position):
        """Add a widget horizontally:
           - Added at given position

        Current content
        +------+------+------+          +--------------+
        |0     |1     |2     |          |0 A           |
        |A     |B     |C     |          +--------------+
        |      |      |      |          |1 B           |
        |      |      |      |          +--------------+
        |      |      |      |          |2 C           |
        +------+------+------+          +--------------+

        Insert widget at position 1
        +------+------+------+          +--------------+
        |0     |1,0   |2     |          |0 A           |
        |A     |B     |C     |          +--------------+
        |      |      |      |          |1 new         |
        |      +------+      |          +--------------+
        |      |1,1   |      |          |2 B           |
        |      |new   |      |          +--------------+
        |      |      |      |          |3 C           |
        +------+------+------+          +--------------+
        """
        self.__addWidget(widget, Qt.Horizontal, position)

    def replaceWidgetAt(self, index, replacedBy):
        """Replace widget at given index with given widget `replacedBy`

        If giben `index` is not valid, return None
        Otherwise return widget that has been replaced
        """
        if not isinstance(replacedBy, QWidget):
            raise EInvalidType("Given widget `replacedBy` must be a <QWidget>")

        returned = self.__splitter.replaceWidget(index, replacedBy)

    def replaceWidget(self, toReplace, replacedBy):
        """Replace given widget `toReplace` with given widget `replacedBy`

        Widget `toReplace` is search in all children
        If not found, does nothing and return False, otherwise return True
        """
        if not isinstance(toReplace, QWidget):
            raise EInvalidType("Given widget `toReplace` must be a <QWidget>")
        elif not isinstance(replacedBy, QWidget):
            raise EInvalidType("Given widget `replacedBy` must be a <QWidget>")
        elif toReplace != replacedBy:
            found = self.searchWidget(toReplace)
            if found:
                if found[0].replaceWidgetAt(found[1], replacedBy):
                    return True

        return False

    def switchWidgets(self, widgetA, widgetB):
        """Switch given `widgetA` and `widgetB`

        If one of given widget is not found, does nothing and return False
        Otherwise return True
        """
        if not isinstance(widgetA, QWidget):
            raise EInvalidType("Given widget `widgetA` must be a <QWidget>")
        elif not isinstance(widgetB, QWidget):
            raise EInvalidType("Given widget `widgetB` must be a <QWidget>")

        foundA = self.searchWidget(widgetA)
        if foundA:
            foundB = self.searchWidget(widgetB)
            if foundB:
                # boths widget found...
                tmpWidget = QWidget()

                foundA[0].replaceWidget(widgetA, tmpWidget)
                foundB[0].replaceWidget(widgetB, widgetA)
                foundA[0].replaceWidget(tmpWidget, widgetB)

                return True

        return False

    def removeWidget(self, widget):
        """Remove `widget`

        Return True if found and removed, otherwise return False

        Widget is not destroyed!
        """
        found = self.searchWidget(widget)
        if found:
            if found[0] != self:
                return found[0].removeWidget(widget)
            else:
                widget.setParent(None)
                if self.__splitter.count() == 1:
                    # only one widget left
                    # remove WMultiSplitter
                    self.parentWidget().parentWidget().replaceWidget(self, self.__splitter.widget(0))
                    self.deleteLater()
                return True

        return False

    def sizes(self):
        """Return sizes for widgets"""
        self.__splitter.sizes()

    def setSizes(self, sizes):
        """Define sizes for widgets"""
        self.__splitter.setSizes(sizes)

    def exportLayout(self):
        """Export current layout sizes

        If widget have method .id(),
        """
        nbTotal = 0
        returned = {
                'orientation': self.__splitter.orientation(),
                'sizes': self.__splitter.sizes(),
                'items': []
            }

        for index in range(self.__splitter.count()):
            childWidget = self.__splitter.widget(index)

            if isinstance(childWidget, WMultiSplitter):
                subLayout, subNbTotal = childWidget.exportLayout()
                nbTotal += subNbTotal
                returned['items'].append(subLayout)
            elif hasattr(childWidget, 'refWidget') and callable(childWidget.refWidget):
                returned['items'].append(f"@{childWidget.refWidget()}")
                nbTotal += 1
            else:
                returned['items'].append(f"#{childWidget.__class__.__name__}")
                nbTotal += 1

        if isinstance(self.parentWidget(), QSplitter) and isinstance(self.parentWidget().parentWidget(), WMultiSplitter):
            return (returned, nbTotal)

        returned['nbTotal'] = nbTotal
        return returned

    def importLayout(self):
        pass
