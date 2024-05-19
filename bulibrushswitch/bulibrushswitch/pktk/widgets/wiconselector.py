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

# Widget provide an UI to select pktk and/or Krita internal icon

import re

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )

from ..modules.utils import (regExIsValid, loadXmlUi, replaceLineEditClearButton)
from ..modules.iconsizes import IconSizes
from ..modules.imgutils import (buildIcon, getIconList, QUriIcon)
from ..pktk import *
from .wlineedit import WLineEdit


class WIconSelector(QWidget):
    """A widget to select icons

        +------------------------------------------------------------------------------ search text entry
        |
        |
        |   +----------------------------------+---+
        |   |                                  | V | <--------------------------------- icon sourcecombobox
        |   +----------------------------------+---+
        |   +-------------------------------+  +---+
        +-> | xxxx                          |  |   | <--------------------------------- search text entry 'regular expression mode' option
            +-------------------------------+  +---+
            +--------------------------------------+
            |                                      |
            |                                      | <--------------------------------- Resources listwidget
            |                                      |
            |                                      |
            |                                      |
            |                                      |
            |                                      |
            |                                      |
            |                                      |
            |                                      |
            +--------------------------------------+
                                      +------+ +---+
            Found: XXX                |..*...| |   | <--------------------------------- listview popup menu (icon mode/list mode | square icon|rect icon)
                        ^                 +------+ +---+
                        |                    ^
                        |                    |
                        |                    +--------------------------------------------- Slider to define icon size
         selectionChanged               |
                        +------------------------------------------------------------------ Number of found items

    """

    OPTIONS_SHOW_SOURCE_PKTK =          0b1000000000000000
    OPTIONS_SHOW_SOURCE_KRITA =         0b0100000000000000

    OPTIONS_SHOW_STATUSBAR =            0b0000000000100000

    OPTIONS_DEFAULT_MODE_VIEW_ICON =    0b0000000000000000
    OPTIONS_DEFAULT_MODE_VIEW_LIST =    0b0000000001000000

    OPTIONS_DEFAULT_ICON_SIZE =         0b0000000000010000  # provide icon size as (OPTIONS_DEFAULT_ICON_SIZE | 3) for example

    # selected item changed, provide a list of string uri if there's selected item, or empty list if nothing is selected
    iconSelectionChanged = Signal(list)

    # A double-click on an icon
    doubleClicked = Signal(str)

    # Triggered when filter is applied (value >= 0 provide number of found items)
    # Triggered when filter is removed (value == -1)
    filterChanged = Signal(int)

    # Icon size has been changed (index, size)
    iconSizeIndexChanged = Signal(int, QSize)

    # View mode (icon/list) size has been changed
    viewModeChanged = Signal(int)

    def __init__(self, options=None, parent=None):
        super(WIconSelector, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), '..', 'resources', 'wiconselector.ui')

        loadXmlUi(uiFileName, self)

        self.__iconSize = IconSizes([32, 64, 96, 128, 192, 256, 384])
        self.__iconSize.setIndex(3)  # default value

        if options is None:
            # set default options
            options = (WIconSelector.OPTIONS_SHOW_SOURCE_PKTK |
                       WIconSelector.OPTIONS_SHOW_SOURCE_KRITA |
                       WIconSelector.OPTIONS_SHOW_STATUSBAR |
                       WIconSelector.OPTIONS_DEFAULT_MODE_VIEW_ICON)

        if options & (WIconSelector.OPTIONS_SHOW_SOURCE_PKTK |
                      WIconSelector.OPTIONS_SHOW_SOURCE_KRITA) == 0:
            # an icon source is mandatory, set the default one
            options |= (WIconSelector.OPTIONS_SHOW_SOURCE_PKTK |
                        WIconSelector.OPTIONS_SHOW_SOURCE_KRITA)

        if options & (WIconSelector.OPTIONS_SHOW_SOURCE_PKTK |
                      WIconSelector.OPTIONS_SHOW_SOURCE_KRITA) != (WIconSelector.OPTIONS_SHOW_SOURCE_PKTK |
                                                                   WIconSelector.OPTIONS_SHOW_SOURCE_KRITA):
            # only one source provided: no need to show icon source selector
            self.cbIconsSource.hide()
        else:
            self.cbIconsSource.currentIndexChanged.connect(self.__updateFilter)

        if options & WIconSelector.OPTIONS_SHOW_STATUSBAR != WIconSelector.OPTIONS_SHOW_STATUSBAR:
            # status bar not required, hide it
            self.wStatusBar.hide()
        else:
            self.hsIconsIconSize.valueChanged.connect(self.setIconSizeIndex)

        self.__options = options

        # init UI
        self.leFilterName.textEdited.connect(self.__updateFilter)
        self.tbFilterNameRegEx.toggled.connect(self.__updateFilter)
        self.lvIcons.selectionModel().selectionChanged.connect(self.__selectionChanged)
        self.lvIcons.itemDoubleClicked.connect(self.__doubleClick)
        # because I'm too lazy to create a widget for this...
        self.__lvIconsOriginalWheelEvent = self.lvIcons.wheelEvent
        self.lvIcons.wheelEvent = self.__lvIconsWheelEvent

        self.__initSources()
        self.__loadIcons()
        self.__initPopupMenu()
        self.__updateFilter()

        if options & WIconSelector.OPTIONS_DEFAULT_MODE_VIEW_LIST == WIconSelector.OPTIONS_DEFAULT_MODE_VIEW_LIST:
            self.setViewMode(QListView.ListMode)
        else:
            self.setViewMode(QListView.IconMode)

        if options & WIconSelector.OPTIONS_DEFAULT_ICON_SIZE == WIconSelector.OPTIONS_DEFAULT_ICON_SIZE:
            self.setIconSizeIndex(options & 0b0000000000000111)
        else:
            self.setIconSizeIndex(3)

    def __initSources(self):
        """Initialise icon sources list

        Normally called only if there's ate least 2 sources
        """
        self.cbIconsSource.addItem(i18n('All icons'), 0)

        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_PKTK == WIconSelector.OPTIONS_SHOW_SOURCE_PKTK:
            self.cbIconsSource.addItem(i18n('PkTk icons'), WIconSelector.OPTIONS_SHOW_SOURCE_PKTK)

        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_KRITA == WIconSelector.OPTIONS_SHOW_SOURCE_KRITA:
            self.cbIconsSource.addItem(i18n('Krita icons'), WIconSelector.OPTIONS_SHOW_SOURCE_KRITA)

        self.cbIconsSource.setCurrentIndex(0)

    def __loadIcons(self):
        """Load all availables icons according to settings"""
        source = []
        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_PKTK == WIconSelector.OPTIONS_SHOW_SOURCE_PKTK:
            source.append('pktk')

        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_KRITA == WIconSelector.OPTIONS_SHOW_SOURCE_KRITA:
            source.append('krita')

        for name in getIconList(source):
            fileName = re.sub('^(pktk|krita):', '', name)
            item = QListWidgetItem(buildIcon(name), fileName.replace('_', ' ').capitalize())
            item.setData(Qt.UserRole, name)
            self.lvIcons.addItem(item)

    def __initPopupMenu(self):
        """Initialise popup menu for toolbuttons"""
        self.__actionViewModeGroup = QActionGroup(self)
        self.__actionViewModeList = QAction(buildIcon('pktk:list_view_details'), i18n("List view"))
        self.__actionViewModeList.setCheckable(True)
        self.__actionViewModeList.setChecked(False)
        self.__actionViewModeList.setActionGroup(self.__actionViewModeGroup)
        self.__actionViewModeList.toggled.connect(self.__viewModeChanged)
        self.__actionViewModeIcon = QAction(buildIcon('pktk:list_view_icon'), i18n("Icon view"))
        self.__actionViewModeIcon.setCheckable(True)
        self.__actionViewModeIcon.setChecked(True)
        self.__actionViewModeIcon.setActionGroup(self.__actionViewModeGroup)
        self.__actionViewModeIcon.toggled.connect(self.__viewModeChanged)

        self.__menuViewMode = QMenu(self.tbIconsViewMode)
        self.__menuViewMode.addAction(self.__actionViewModeList)
        self.__menuViewMode.addAction(self.__actionViewModeIcon)
        self.tbIconsViewMode.setMenu(self.__menuViewMode)

        self.__viewModeChanged()

    def __updateFilter(self):
        """Show/Hide items according to current filter

        Filter takes in account:
        - selected source
        - text filter
        """
        checkSource = 0
        if self.cbIconsSource.isVisible():
            checkSource = self.cbIconsSource.currentData(Qt.UserRole)

        searchFilter = self.leFilterName.text()
        checkSearchFilter = (searchFilter != '')

        checkSearchFilterRegEx = self.tbFilterNameRegEx.isChecked()
        if checkSearchFilter and not checkSearchFilterRegEx:
            # Convert it as regular expression
            searchFilter = searchFilter.replace(" ", r"\s").replace("*", ".*").replace("?", ".")

        self.lvIcons.setUpdatesEnabled(False)

        if not regExIsValid(searchFilter):
            return

        nbVisible = 0
        for index in range(self.lvIcons.count()):
            item = self.lvIcons.item(index)
            itemIconUri = item.data(Qt.UserRole)
            isVisible = True
            if checkSource == WIconSelector.OPTIONS_SHOW_SOURCE_PKTK:
                if not itemIconUri.startswith('pktk:'):
                    isVisible = False
            elif checkSource == WIconSelector.OPTIONS_SHOW_SOURCE_KRITA:
                if not itemIconUri.startswith('krita:'):
                    isVisible = False

            if isVisible and checkSearchFilter:
                if not re.search(searchFilter, item.text(), re.I):
                    isVisible = False

            if isVisible:
                nbVisible += 1
                item.setHidden(False)
            else:
                item.setHidden(True)

        self.lvIcons.setUpdatesEnabled(True)
        self.lblIconsFoundItems.setText(f'{nbVisible}')

    def __selectionChanged(self):
        """Selected item as been changed, emit signal"""
        index = self.lvIcons.selectionModel().currentIndex()
        if index.isValid():
            emitted = [index.data(Qt.UserRole)]
        else:
            emitted = []

        self.iconSelectionChanged.emit(emitted)

    def __viewModeChanged(self):
        """Update view mode list/icon"""
        if self.__actionViewModeList.isChecked():
            self.lvIcons.setViewMode(QListView.ListMode)
        else:
            self.lvIcons.setViewMode(QListView.IconMode)
        self.viewModeChanged.emit(self.lvIcons.viewMode())

    def __lvIconsWheelEvent(self, event):
        """Manage zoom level through mouse wheel"""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                # Zoom in
                sizeChanged = self.__iconSize.next()
            else:
                # zoom out
                sizeChanged = self.__iconSize.prev()

            if sizeChanged:
                self.setIconSizeIndex()
        else:
            self.__lvIconsOriginalWheelEvent(event)

    def __doubleClick(self, item):
        """An item has been double-clicked"""
        self.doubleClicked.emit(item.data(Qt.UserRole))

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            iconSizeValue = self.__iconSize.value()

            iconSize = QSize(iconSizeValue, iconSizeValue)

            self.lvIcons.setIconSize(iconSize)
            self.hsIconsIconSize.setValue(self.__iconSize.index())
            self.iconSizeIndexChanged.emit(self.__iconSize.index(), iconSize)

    def viewMode(self):
        """Return currentview mode (icon/list)"""
        return self.lvIcons.viewMode()

    def setViewMode(self, mode):
        """Set view mode (icon/list)"""
        if mode == QListView.IconMode:
            self.__actionViewModeIcon.setChecked(True)
        else:
            self.__actionViewModeList.setChecked(True)

    def icon(self):
        """Return selected item uri"""
        index = self.lvIcons.selectionModel().currentIndex()
        if index.isValid():
            return index.data(Qt.UserRole)
        return ''

    def setIcon(self, iconId):
        """Select given `iconId`; must be 'krita:xxx' or 'pktk:xxx' reference

        If not found, return False
        """
        if not isinstance(iconId, str):
            raise EInvalidType("Given `iconId` must be a <str>")

        if iconId == '' or not re.search('^(krita|pktk):', iconId):
            # avoid to search if we know we won't found it'
            return False

        for itemIndex in range(self.lvIcons.count()):
            if self.lvIcons.item(itemIndex).data(Qt.UserRole) == iconId:
                if self.cbIconsSource.isVisible():
                    # need to switch current icon list?
                    if re.search('^krita:', iconId):
                        # krita icon
                        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_KRITA == WIconSelector.OPTIONS_SHOW_SOURCE_KRITA:
                            # available in source list
                            checkSource = self.cbIconsSource.currentData(Qt.UserRole)
                            if not (checkSource == 0 or checkSource == WIconSelector.OPTIONS_SHOW_SOURCE_KRITA):
                                self.cbIconsSource.setCurrentIndex(2)  # WIconSelector.OPTIONS_SHOW_SOURCE_KRITA
                    else:
                        # pktk icon
                        if self.__options & WIconSelector.OPTIONS_SHOW_SOURCE_PKTK == WIconSelector.OPTIONS_SHOW_SOURCE_PKTK:
                            # available in source list
                            checkSource = self.cbIconsSource.currentData(Qt.UserRole)
                            if not (checkSource == 0 or checkSource == WIconSelector.OPTIONS_SHOW_SOURCE_PKTK):
                                self.cbIconsSource.setCurrentIndex(1)  # WIconSelector.OPTIONS_SHOW_SOURCE_PKTK

                self.lvIcons.setCurrentRow(itemIndex)
                return True
        return False


class WIconSelectorDialog(QDialog):
    """A simple dialog box to display and select icons"""

    @staticmethod
    def show(options=None):
        """Open a dialog box to edit group"""
        widget = QWidget()
        dlgBox = WIconSelectorDialog(options, widget)

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            return {
                    'uri': dlgBox.selectedUri(),
                    'optionViewMode': dlgBox.viewMode(),
                    'optionIconSizeIndex': dlgBox.iconSizeIndex()
                    }
        else:
            return None

    def __init__(self, options, parent=None):
        super(WIconSelectorDialog, self).__init__(parent)

        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setSizeGripEnabled(True)
        self.setModal(True)
        self.resize(800, 600)

        self.__selectedURI = QUriIcon()

        self.__isIcons = WIconSelector(options)
        self.__isIcons.iconSelectionChanged.connect(self.__selectionChanged)

        self.__dbbxOkCancel = QDialogButtonBox(self)
        self.__dbbxOkCancel.setOrientation(Qt.Horizontal)
        self.__dbbxOkCancel.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.__dbbxOkCancel.accepted.connect(self.accept)
        self.__dbbxOkCancel.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.__isIcons)
        layout.addWidget(self.__dbbxOkCancel)

        self.__dbbxOkCancel.button(QDialogButtonBox.Ok).setEnabled(False)

    def __selectionChanged(self, uriIcon):
        """Selected icon has been changed, update UI"""
        if len(uriIcon) > 0:
            self.__selectedURI = QUriIcon(uriIcon[0])
        else:
            self.__selectedURI = QUriIcon()

        if self.__selectedURI.uri() is None:
            self.__dbbxOkCancel.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.__dbbxOkCancel.button(QDialogButtonBox.Ok).setEnabled(True)

    def selectedUri(self):
        """Return selected node"""
        return self.__selectedURI

    def viewMode(self):
        """Return current view mode"""
        return self.__isIcons.viewMode()

    def setViewMode(self, viewMode):
        """set current view mode"""
        self.__isIcons.setViewMode(viewMode)

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__isIcons.iconSizeIndex()

    def setIconSizeIndex(self, index):
        """Set current icon size index"""
        self.__isIcons.setIconSizeIndex(index)
