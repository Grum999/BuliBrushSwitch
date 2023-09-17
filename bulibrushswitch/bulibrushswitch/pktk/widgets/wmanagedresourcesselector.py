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

import PyQt5.uic

import os.path
import sys

from krita import Resource

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )

from ..modules.utils import loadXmlUi
from ..modules.resutils import (
        ManagedResourceTypes,
        ManagedResource,
        DBManagedResources,
        ManagedResourcesModel
    )
from ..modules.iconsizes import IconSizes
from ..modules.imgutils import buildIcon
from ..pktk import *
from .wlineedit import WLineEdit
from .wtaginput import WTagInput


class ManagedResourcesProxyModel(QSortFilterProxyModel):
    """A proxy model to manage filtering"""

    FILTER_TAG_COMBINATION_AND = 0
    FILTER_TAG_COMBINATION_OR = 1

    def __init__(self, parent=None):
        super(ManagedResourcesProxyModel, self).__init__(parent)

        self.__tagIdList = []
        self.__tagCombination = ManagedResourcesProxyModel.FILTER_TAG_COMBINATION_AND

        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setRecursiveFilteringEnabled(False)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        defaultRule = super(ManagedResourcesProxyModel, self).filterAcceptsRow(sourceRow, sourceParent)
        if not defaultRule:
            # default rule exclude row, no need to continue
            return False

        sourceModel = self.sourceModel()
        modelIndex = sourceModel.index(sourceRow, 0, sourceParent)

        if len(self.__tagIdList) == 0:
            # we have no search based on tags, then validate it
            return True

        tagList = modelIndex.data(ManagedResourcesModel.ROLE_TAGSID)
        if len(tagList) == 0:
            # no tag for item
            # we have a search based on tags, then exclude it
            return False

        for tag in self.__tagIdList:
            if self.__tagCombination == ManagedResourcesProxyModel.FILTER_TAG_COMBINATION_AND:
                if tag not in tagList:
                    # expected tag not in resource tags
                    # exclude item
                    return False
            else:
                if tag in tagList:
                    # expected tag in resource tags
                    # validate item
                    return True

        if self.__tagCombination == ManagedResourcesProxyModel.FILTER_TAG_COMBINATION_AND:
            # for AND combination, being here means that all tags were found in resource tags
            return True
        else:
            # for OR combination, being here means that no tags were found in resource tags
            return False

    def filterTags(self):
        """Return list of tag id used for filter"""
        return self.__tagIdList

    def setFilterTag(self, tagIdList):
        """Set list of tag id used for filter"""
        # tag id are stored as string, need an integer
        self.__tagIdList = [int(tagId) for tagId in tagIdList]
        self.invalidateFilter()

    def filterTagCombination(self):
        """Return filter tag combination rule"""
        return self.__tagCombination

    def setFilterTagCombination(self, value):
        """Set filter tag combination rule"""
        self.__tagCombination = value
        self.invalidateFilter()


class WManagedResourcesLv(QListView):

    iconSizeIndexChanged = Signal(int, QSize)

    def __init__(self, parent=None):
        super(WManagedResourcesLv, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setAutoScroll(True)
        self.setSpacing(0)

        self.__sourceModel = ManagedResourcesModel()

        self.__managedResourcesProxyModel = ManagedResourcesProxyModel(self)
        self.__managedResourcesProxyModel.setSourceModel(self.__sourceModel)
        self.__managedResourcesProxyModel.setFilterRole(ManagedResourcesModel.ROLE_NAME)

        self.setModel(self.__managedResourcesProxyModel)

        self.__iconSize = IconSizes([32, 64, 96, 128, 192, 256, 384])
        self.setIconSizeIndex(3)
        self.setViewMode(QListView.IconMode)

    def __setSelectedItem(self, resource):
        """Select item if found in model, otherwise do nothing"""
        index = self.__sourceModel.getResource(resource, True)
        if index is not None:
            self.selectionModel().select(index, QItemSelectionModel.Select)

    def wheelEvent(self, event):
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
            super(WManagedResourcesLv, self).wheelEvent(event)

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            iconSizeValue = self.__iconSize.value()
            if self.__sourceModel.resourceType() == ManagedResourceTypes.RES_GRADIENTS:
                iconSize = QSize(iconSizeValue << 1, iconSizeValue)
            else:
                iconSize = QSize(iconSizeValue, iconSizeValue)

            self.setGridSize(iconSize)
            self.setIconSize(iconSize)
            self.iconSizeIndexChanged.emit(self.__iconSize.index(), iconSize)

    def selectedItems(self):
        """Return a list of selected brushes items"""
        returned = []
        if self.selectionModel():
            for item in self.selectionModel().selectedIndexes():
                resource = item.data(ManagedResourcesModel.ROLE_MANAGEDRESOURCE)
                if resource is not None:
                    returned.append(resource)
        return returned

    def setSelectedItems(self, resources):
        """Set selected resources

        given `resources` can be:
        - None (clear selection)
        - A list
        - An integer (then, represent an Id)
        - A tuple (name, fileName)
        - A ManagedResource
        - A Resource
        """
        if not (isinstance(resources, (list, ManagedResource, int, tuple, Resource)) or resources is None):
            raise EInvalidType("Given `resources` is not valid")

        if not self.selectionModel():
            return

        if isinstance(resources, list):
            self.selectionModel().clearSelection()
            for resource in resources:
                self.__setSelectedItem(resource)
        elif resources is None or isinstance(resources, ManagedResource) and resources.id() is None:
            self.selectionModel().clearSelection()
        else:
            self.__setSelectedItem(resources)

    def nbSelectedItems(self):
        """Return number of selected items"""
        return len(self.selectedItems())

    def setViewMode(self, value):
        """Set if if view is icon mode"""
        super(WManagedResourcesLv, self).setViewMode(value)
        if self.viewMode() == QListView.IconMode:
            self.__sourceModel.setDisplayName(False)
        else:
            self.__sourceModel.setDisplayName(True)

    def resourceType(self):
        """return current managed resource type"""
        return self.__sourceModel.__resourceType()

    def setResourceType(self, value):
        """set current managed resource type"""
        self.__sourceModel.updateResources(value)
        # force icon size to be recalculated
        self.setIconSizeIndex()


class WManagedResourcesSelector(QWidget):
    """A widget to browse resources

        +---------------------------------------------------------------------------------- tags entry
        |
        |
        |   +------------------------------------------------------------------------------ search text entry
        |   |
        |   |
        |   |   +----------------------------------+---+
        |   |   |                                  | V | <--------------------------------- resource type combobox
        |   |   +----------------------------------+---+
        |   |   +-------------------------------+  +---+
        |   +-> | xxxx                          |  |   | <--------------------------------- search text entry 'regular expression mode' option
        |       +-------------------------------+  +---+
        |       +-------------------------------+  +---+
        +-----> | xxxx                          |  |   | <--------------------------------- tag popup menu 'Match all tags (AND)' or 'Match on of tags (OR)'
                +-------------------------------+  +---+
                +--------------------------------------+
                |                                      |
                |                                      | <--------------------------------- Resources listview
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
                        |
                        +------------------------------------------------------------------ Number of found items

    """
    # selected item changed, provide a list of ManagedResource
    selectionChanged = Signal(list)

    # Trigerred when filter is applied (value >= 0 provide number of found items)
    # Trigerred when filter is removed (value == -1)
    filterChanged = Signal(int)

    # Trigerred when resources are loaded
    resourcesLoaded = Signal(ManagedResourceTypes, int)

    def __init__(self, parent=None):
        super(WManagedResourcesSelector, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), '..', 'resources', 'wmanagedresourcesselector.ui')

        loadXmlUi(uiFileName, self)

        self.__model = self.lvManagedResources.model()
        self.__resourceType = ManagedResourceTypes.RES_GRADIENTS
        self.__resourceTypes = [ManagedResourceTypes.RES_GRADIENTS]

        self.__loadResources()
        self.cbResourceType.setVisible(False)
        self.leFilterName.textEdited.connect(self.__updateFilter)
        self.wtiFilterTag.tagSelection.connect(self.__updateFilter)
        self.tbFilterNameRegEx.toggled.connect(self.__updateFilter)
        self.hsManagedResourcesIconSize.valueChanged.connect(self.__iconSizeIndexSliderChanged)
        self.lvManagedResources.iconSizeIndexChanged.connect(self.__iconSizeIndexChanged)
        self.lvManagedResources.selectionModel().selectionChanged.connect(self.__selectionChanged)
        self.cbResourceType.currentIndexChanged.connect(self.__updateResourceType)

        self.__initPopupMenu()

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

        self.__menuViewMode = QMenu(self.tbManagedResourcesViewMode)
        self.__menuViewMode.addAction(self.__actionViewModeList)
        self.__menuViewMode.addAction(self.__actionViewModeIcon)
        self.tbManagedResourcesViewMode.setMenu(self.__menuViewMode)

        self.__viewModeChanged()

        self.__actionFilterTagModeGroup = QActionGroup(self)
        self.__actionFilterTagModeAnd = QAction(buildIcon('pktk:sign_logical_and'), i18n("Match all tags (AND)"))
        self.__actionFilterTagModeAnd.setCheckable(True)
        self.__actionFilterTagModeAnd.setChecked(False)
        self.__actionFilterTagModeAnd.setActionGroup(self.__actionFilterTagModeGroup)
        self.__actionFilterTagModeAnd.toggled.connect(self.__FilterTagModeChanged)
        self.__actionFilterTagModeOr = QAction(buildIcon('pktk:sign_logical_or'), i18n("Match any tag (OR)"))
        self.__actionFilterTagModeOr.setCheckable(True)
        self.__actionFilterTagModeOr.setChecked(True)
        self.__actionFilterTagModeOr.setActionGroup(self.__actionFilterTagModeGroup)
        self.__actionFilterTagModeOr.toggled.connect(self.__FilterTagModeChanged)

        self.__menuFilterTagMode = QMenu(self.tbManagedResourcesViewMode)
        self.__menuFilterTagMode.addAction(self.__actionFilterTagModeAnd)
        self.__menuFilterTagMode.addAction(self.__actionFilterTagModeOr)
        self.tbFilterTagRules.setMenu(self.__menuFilterTagMode)

        self.__FilterTagModeChanged()

    def __loadResources(self):
        """Initialise resource listview"""
        self.lvManagedResources.setResourceType(self.__resourceType)
        sourceModel = self.__model.sourceModel()

        # build tag list from ALL resource (even filtered one, so use source model)
        allTags = []
        for rowNumber in range(sourceModel.rowCount()):
            modelIndex = sourceModel.index(rowNumber, 0)
            tagsList = sourceModel.data(modelIndex, ManagedResourcesModel.ROLE_TAGS)

            for tag in tagsList:
                if tag not in allTags:
                    # tag id must be <str>
                    allTags.append((f"{tag[0]}", tag[1]))

        self.wtiFilterTag.setAvailableTags(allTags)
        self.wFilterTag.setVisible(len(allTags) > 0)
        self.__updateFilter()
        self.resourcesLoaded.emit(self.__resourceType, sourceModel.rowCount())

    def __updateFilter(self):
        """Filter definition has been modified, need to apply it"""
        if self.tbFilterNameRegEx.isChecked():
            regEx = QRegularExpression(self.leFilterName.text(), QRegularExpression.CaseInsensitiveOption)
            self.__model.setFilterRegularExpression(regEx)
        else:
            self.__model.setFilterFixedString(self.leFilterName.text())

        self.__model.setFilterTag(self.wtiFilterTag.selectedTags())

        nbFound = self.lvManagedResources.model().rowCount()
        self.lblManagedResourcesFoundItems.setText(f"{nbFound}")

        if self.leFilterName.text() != '' or len(self.wtiFilterTag.selectedTags()) > 0:
            self.filterChanged.emit(nbFound)
        else:
            self.filterChanged.emit(-1)

    def __iconSizeIndexSliderChanged(self, newSize):
        """Icon size has been changed from slider"""
        self.lvManagedResources.setIconSizeIndex(newSize)

    def __iconSizeIndexChanged(self, newSize, newQSize):
        """Icon size has been changed from listview"""
        self.hsManagedResourcesIconSize.setValue(newSize)

    def __viewModeChanged(self):
        """View mode Icon/List has changed"""
        if self.__actionViewModeList.isChecked():
            self.tbManagedResourcesViewMode.setIcon(self.__actionViewModeList.icon())
            self.lvManagedResources.setViewMode(QListView.ListMode)
        else:
            self.tbManagedResourcesViewMode.setIcon(self.__actionViewModeIcon.icon())
            self.lvManagedResources.setViewMode(QListView.IconMode)

    def __FilterTagModeChanged(self):
        """Filter tag mode AND/OR has changed"""
        if self.__actionFilterTagModeAnd.isChecked():
            self.tbFilterTagRules.setIcon(self.__actionFilterTagModeAnd.icon())
            self.lvManagedResources.model().setFilterTagCombination(ManagedResourcesProxyModel.FILTER_TAG_COMBINATION_AND)
        else:
            self.tbFilterTagRules.setIcon(self.__actionFilterTagModeOr.icon())
            self.lvManagedResources.model().setFilterTagCombination(ManagedResourcesProxyModel.FILTER_TAG_COMBINATION_OR)

    def __updateResourceType(self, index):
        """Update resource type from cbResourceType"""
        self.setResourceType(self.cbResourceType.currentData())

    def __selectionChanged(self, selected=None, deselected=None):
        """Selected item has changed"""
        self.selectionChanged.emit(self.lvManagedResources.selectedItems())

    def resourceType(self):
        """Return current managed resource type"""
        return self.__resourceType

    def setResourceType(self, value):
        """Set current managed resource type"""
        if isinstance(value, ManagedResourceTypes) and value != self.__resourceType and value in self.__resourceTypes:
            self.__resourceType = value
            self.__loadResources()

    def resourceTypes(self):
        """Return list of managed resource types """
        return self.__resourceTypes

    def setResourceTypes(self, values):
        """Set list of managed resource types

        Given `value` is a <ManagedResources> or a list of <ManagedResources>
        If more than one <ManagedResources> is provided, widget will display a combobox to let user chose resource type
        """
        if isinstance(values, ManagedResourceTypes):
            values = [values]
        elif not isinstance(values, (list, tuple)):
            raise EInvalidType("Given `values` must be a <ManagedResourceTypes> or a list of <ManagedResourceTypes>")

        self.__resourceTypes = []

        for value in values:
            if isinstance(value, ManagedResourceTypes) and value not in self.__resourceTypes:
                self.__resourceTypes.append(value)
            else:
                raise EInvalidType("Given `values` items must be <ManagedResourceTypes>")

        if len(self.__resourceTypes) == 0:
            raise EInvalidValue("At least one resource type must be provided")

        if len(self.__resourceTypes) > 1:
            self.cbResourceType.clear()
            for resource in sorted(self.__resourceTypes, key=lambda value: value.value):
                self.cbResourceType.addItem(resource.label(), resource)
            self.cbResourceType.setVisible(True)
        else:
            self.cbResourceType.setVisible(False)

        if self.__resourceType not in self.__resourceTypes:
            self.setResourceType(self.__resourceTypes[0])

    def selectionMode(self):
        """Return current selection mode"""
        return self.lvManagedResources.selectionMode()

    def setSelectionMode(self, value):
        """Set current selection mode"""
        self.lvManagedResources.setSelectionMode(value)

    def viewMode(self):
        """Return current view mode"""
        return self.lvManagedResources.viewMode()

    def setViewMode(self, value):
        """Set current selection mode"""
        if value == QListView.ListMode:
            self.__actionViewModeList.setChecked(True)
        else:
            self.__actionViewModeIcon.setChecked(True)

    def iconSizeIndex(self):
        """Return current view mode"""
        return self.lvManagedResources.iconSizeIndex()

    def setIconSizeIndex(self, value):
        """Set current selection mode"""
        self.lvManagedResources.setIconSizeIndex(value)

    def setSelectedResources(self, resources):
        """Set selected resources

        given `resources` can be:
        - None
        - A list
        - An integer (then, represent an Id)
        - A tuple (name, fileName)
        - A ManagedResource
        - A Resource
        """
        self.lvManagedResources.setSelectedItems(resources)

    def selectedResources(self):
        """Return a list of selected resources"""
        return self.lvManagedResources.selectedItems()

    def selectedResourcesCount(self):
        """Return number of selected resources"""
        return self.lvManagedResources.selectedItems()

    def resources(self, filtered=False):
        """Return list of current resources

        If filtered is True, return only resources available through current filter, if any active/applied
        """
        returned = []
        model = self.lvManagedResources.model()
        if not filtered:
            model = model.sourceModel()

        for row in range(model.rowCount()):
            index = model.index(row, 0)
            returned.append(model.data(index, ManagedResourcesModel.ROLE_MANAGEDRESOURCE))

        return returned
