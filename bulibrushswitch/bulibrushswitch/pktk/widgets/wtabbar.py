# -----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2023 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin framework
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# The wtabbar module provides a WTabBar widget, extending QTabBar:
# . Highlight on mouse over
# . Active tab visible
# . Visual modified status/Close button
#
# Main class from this module
#
# - WTabBar:
#       Widget
#       The main tab bar widget
#
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtGui import (
        QPainter,
        QFontMetrics,
        QPen,
        QBrush,
        QPixmap,
        QColor,
        QPalette
    )
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )


class WTabBar(QTabBar):
    """Implement a tabbar that let possibility in code editor to made distinction
    between saved and unsaved document (ie: customized tab content)

    Also, close button is not visible by default and displayed only when mouse is
    over tab

    Implementation made from solution found here: https://stackoverflow.com/a/64346097


    To use it:

        Assuming:
            tabWidget = QTabWidget(self)

        Then:
            tabBar = WTabBar(tabWidget)
            tabWidget.setTabBar(tabBar)
    """
    __ROLE_RAW = Qt.UserRole + 10000
    __ROLE_MODIFIED = Qt.UserRole + 10001
    __ROLE_COLOR = Qt.UserRole + 10002

    class MovingTab(QWidget):
        """A private QWidget that paints the current moving tab"""
        def setPixmap(self, pixmap):
            self.pixmap = pixmap
            self.update()

        def paintEvent(self, event):
            qp = QPainter(self)
            qp.drawPixmap(0, 0, self.pixmap)

    def __init__(self, parent, fromTabBar=None):
        super(WTabBar, self).__init__(parent)
        self.__movingTab = None
        self.__isMoving = False
        self.__pressedIndex = -1
        self.__overIndex = -1

        self.setStyleSheet("""
            WTabBar {
                background: palette(Base);
                padding: 0px;
                border: 0px none;
                margin: 0px;
                qproperty-drawBase: 0;
            }

            WTabBar::tab {
                height: 3ex;
                padding: 0px 1ex;
                border-left: 0px none;
                border-right: 0px none;
                border-bottom: 1px solid palette(Base);
                border-top: 3px solid palette(Base);
                background: palette(Base);
                color:palette(Text);
                margin: 0px;
            }
            WTabBar::tab:selected {
                border-top: 3px solid palette(Highlight);
                background: palette(Window);
                border-bottom: 1px solid palette(Window);
            }
            WTabBar::tab:selected:last {
                border-right: 1px solid palette(Base);
                border-bottom: 1px solid palette(Window);
            }

            WTabBar::tab:hover {
                border-right: 0px none;
                background: palette(Highlight);
                border-top: 3px solid palette(Highlight);
                color: palette(HighlightedText);
            }
            WTabBar::close-button {
                height: 8px;
                width: 8px;
            }
            WTabBar::scroller {
                width: 4ex;
            }
        """)

        # track mouse to highlight tab when over
        self.setMouseTracking(True)

        if isinstance(fromTabBar, QTabBar):
            for tabIndex in range(fromTabBar.count()):
                addedTabIndex = self.addTab(fromTabBar.tabIcon(tabIndex), fromTabBar.tabText(tabIndex))
                self.setTabData(addedTabIndex, fromTabBar.tabData(tabIndex))
                self.setTabToolTip(addedTabIndex, fromTabBar.tabToolTip(tabIndex))
                self.setTabVisible(addedTabIndex, fromTabBar.isTabVisible(tabIndex))

    def __drawTab(self, painter, index, tabOption, forPixmap=False):
        """Draw tab according to current state"""
        tabModified = self.tabModified(index)
        if tabModified:
            # set font bold as bold for unsaved tab
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            tabOption.fontMetrics = QFontMetrics(font)

        painter.drawControl(QStyle.CE_TabBarTab, tabOption)

        if tabModified:
            # draw bullet
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.tabRect(index)
            text = self.tabText(index)

            bRadius = rect.height()/8

            closeButton = self.tabButton(index, QTabBar.RightSide)
            if closeButton:
                if closeButton.isVisible():
                    return

                oX = rect.x()
                rect = closeButton.rect()
                pos = closeButton.pos()

                pX = pos.x() + rect.width()/2
                pY = pos.y() + rect.height()/2

                if forPixmap:
                    pX -= oX
            else:
                # should not occurs, but as a workaround solution if occurs ^_^''
                pX = rect.x() + painter.fontMetrics().boundingRect(text).width()
                pY = rect.y() + rect.height()/2

            painter.setPen(QPen(Qt.transparent))
            painter.setBrush(QBrush(self.tabData(index, WTabBar.__ROLE_COLOR)))

            painter.drawEllipse(QPointF(pX, pY), bRadius, bRadius)

    def minimumTabSizeHint(self, index):
        """Return minimum tab size hint"""
        return self.tabSizeHint(index)

    def tabSizeHint(self, index):
        """return size hint for tab

        If tab is flagged as 'modified', size hint take in account font weight as bold
        """
        returned = super(WTabBar, self).tabSizeHint(index)

        if self.tabModified(index):
            # set font bold as bold for unsaved tab; need to recalculate size hint
            tabText = self.tabText(index)

            # weird method...
            # 1) get current text (normal font) width
            # 2) calculate delta betseen text width and current tab width
            # 3) calculate new tab with  as text width (bold) + delta
            font = self.font()
            fontMetrics = QFontMetrics(font)
            delta = returned.width() - fontMetrics.size(Qt.TextShowMnemonic, tabText).width()

            font.setBold(True)
            fontMetrics = QFontMetrics(font)
            returned.setWidth(fontMetrics.size(Qt.TextShowMnemonic, tabText).width() + delta)

        return returned

    def tabInserted(self, index):
        """When a new tab is inserted, hide close button"""
        closeButton = self.tabButton(index, QTabBar.RightSide)
        if closeButton:
            closeButton.hide()

    def isVertical(self):
        """Return if tabs are in vertical mode"""
        return self.shape() in (
            self.RoundedWest,
            self.RoundedEast,
            self.TriangularWest,
            self.TriangularEast)

    def layoutTab(self, overIndex):
        oldIndex = self.__pressedIndex
        self.__pressedIndex = overIndex
        self.moveTab(oldIndex, overIndex)

    def finishedMovingTab(self):
        """Once tab is moved, reset references on tab"""
        self.__movingTab.hide()
        self.__movingTab.deleteLater()
        self.__movingTab = None
        self.__pressedIndex = -1
        self.update()

    def mousePressEvent(self, event):
        """Start to move, get current tab under mouse cursor"""
        super(WTabBar, self).mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            # left button, start "drag"
            self.__pressedIndex = self.tabAt(event.pos())
            if self.__pressedIndex < 0:
                return
            self.startPos = event.pos()

    def mouseMoveEvent(self, event):
        """Mouse move => is moving a tab?"""
        if not event.buttons() & Qt.LeftButton or self.__pressedIndex < 0:
            # not moving a tab
            super(WTabBar, self).mouseMoveEvent(event)

            overIndex = self.tabAt(event.pos())

            if overIndex != self.__overIndex:
                # over another tab
                if self.__overIndex != -1:
                    # hide button for previous tab, if any
                    closeButton = self.tabButton(self.__overIndex, QTabBar.RightSide)
                    if closeButton:
                        closeButton.hide()

                if overIndex != -1:
                    # show button for current tab, if any
                    closeButton = self.tabButton(overIndex, QTabBar.RightSide)
                    if closeButton:
                        closeButton.show()

                self.__overIndex = overIndex
        else:
            if not self.__isMoving:
                closeButton = self.tabButton(self.__pressedIndex, QTabBar.RightSide)
                if closeButton:
                    closeButton.hide()

            delta = event.pos() - self.startPos
            if not self.__isMoving and delta.manhattanLength() < QApplication.startDragDistance():
                # ignore the movement as it's too small to be considered a drag
                return

            if not self.__movingTab:
                # create a private widget that appears as the current (moving) tab
                tabRect = self.tabRect(self.__pressedIndex)
                overlap = self.style().pixelMetric(QStyle.PM_TabBarTabOverlap, None, self)

                tabRect.adjust(-overlap, 0, overlap, 0)

                # create pixmap used while moving
                pm = QPixmap(tabRect.size())
                pm.fill(Qt.transparent)

                qp = QStylePainter(pm, self)
                opt = QStyleOptionTab()
                self.initStyleOption(opt, self.__pressedIndex)
                if self.isVertical():
                    opt.rect.moveTopLeft(QPoint(0, overlap))
                else:
                    opt.rect.moveTopLeft(QPoint(overlap, 0))
                opt.position = opt.OnlyOneTab

                self.__drawTab(qp, self.__pressedIndex, opt, True)
                qp.end()

                self.__movingTab = self.MovingTab(self)
                self.__movingTab.setPixmap(pm)
                self.__movingTab.setGeometry(tabRect)
                self.__movingTab.show()

            self.__isMoving = True

            self.startPos = event.pos()
            isVertical = self.isVertical()
            startRect = self.tabRect(self.__pressedIndex)
            if isVertical:
                delta = delta.y()
                translate = QPoint(0, delta)
                startRect.moveTop(startRect.y() + delta)
            else:
                delta = delta.x()
                translate = QPoint(delta, 0)
                startRect.moveLeft(startRect.x() + delta)

            movingRect = self.__movingTab.geometry()
            movingRect.translate(translate)
            self.__movingTab.setGeometry(movingRect)

            if delta < 0:
                overIndex = self.tabAt(startRect.topLeft())
            else:
                if isVertical:
                    overIndex = self.tabAt(startRect.bottomLeft())
                else:
                    overIndex = self.tabAt(startRect.topRight())
            if overIndex < 0:
                return

            # if the target tab is valid, move the current whenever its position
            # is over the half of its size
            overRect = self.tabRect(overIndex)
            if isVertical:
                if (((overIndex < self.__pressedIndex and movingRect.top() < overRect.center().y()) or
                     (overIndex > self.__pressedIndex and movingRect.bottom() > overRect.center().y()))):
                    self.layoutTab(overIndex)
            elif ((overIndex < self.__pressedIndex and movingRect.left() < overRect.center().x()) or
                  (overIndex > self.__pressedIndex and movingRect.right() > overRect.center().x())):
                self.layoutTab(overIndex)

    def mouseReleaseEvent(self, event):
        """Release mouse button => manage moving tab"""
        super(WTabBar, self).mouseReleaseEvent(event)
        if self.__movingTab:
            self.finishedMovingTab()
        else:
            self.__pressedIndex = -1
        self.__isMoving = False
        self.update()

    def leaveEvent(self, event):
        if self.__overIndex != -1:
            closeButton = self.tabButton(self.__overIndex, QTabBar.RightSide)
            if closeButton:
                closeButton.hide()
            self.__overIndex = -1

    def paintEvent(self, event):
        """paint tabs with own designed style"""
        painter = QStylePainter(self)
        tabOption = QStyleOptionTab()
        for index in range(self.count()):

            if index == self.__pressedIndex and self.__isMoving:
                continue
            self.initStyleOption(tabOption, index)

            painter.save()
            self.__drawTab(painter, index, tabOption)
            painter.restore()

    def tabModified(self, index):
        """return tab flag modified"""
        return self.tabData(index, WTabBar.__ROLE_MODIFIED)

    def setTabModified(self, index, value, color=None):
        """Set tab flag as modified"""
        if isinstance(value, bool):
            tabText = self.tabText(index)

            self.setTabData(index, value, WTabBar.__ROLE_MODIFIED)

            if not isinstance(color, QColor):
                color = self.palette().color(QPalette.Active, QPalette.Highlight)
            self.setTabData(index, color, WTabBar.__ROLE_COLOR)

            # weird method...
            # not able to find how to force widget to recalculate and apply tabs sizes then, force it by renaming tab...
            # (call the method self.updateGeometry() doesn't change anything)
            self.setTabText(index, tabText+' - ')
            self.setTabText(index, tabText)
            self.update()

    def tabData(self, index, role=Qt.UserRole):
        """Override tabData() to be able to manage more than one data value per tab"""
        # get original value
        rawData = super(WTabBar, self).tabData(index)

        if not isinstance(rawData, dict):
            rawData = {Qt.UserRole: QVariant(),
                       WTabBar.__ROLE_MODIFIED: False,
                       WTabBar.__ROLE_COLOR: self.palette().color(QPalette.Active, QPalette.Highlight)
                       }
        if role in (Qt.UserRole, WTabBar.__ROLE_MODIFIED, WTabBar.__ROLE_COLOR):
            return rawData[role]
        elif role == WTabBar.__ROLE_RAW:
            return rawData

        return None

    def setTabData(self, index, value, role=Qt.UserRole):
        """Override setTabData() to be able to manage more than one data value per tab"""
        if index >= 0 and index < self.count():
            # valid index
            currentData = self.tabData(index, WTabBar.__ROLE_RAW)

            if role in (Qt.UserRole, WTabBar.__ROLE_MODIFIED, WTabBar.__ROLE_COLOR):
                currentData[role] = value

            super(WTabBar, self).setTabData(index, currentData)
