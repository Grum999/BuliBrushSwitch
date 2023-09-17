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

import ctypes
import json
import re
import os.path
import sys
import datetime
from pathlib import Path

from PyQt5.Qt import *
from PyQt5.QtGui import (
        QPainter,
        QPen,
        QPalette,
        QBrush,
        QTextDocument,
        QIcon,
        QStandardItem
    )
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )

from ..modules.utils import (loadXmlUi, replaceLineEditClearButton, JsonQObjectEncoder, JsonQObjectDecoder)
from ..modules.strutils import (stripHtml, wildcardToRegEx)
from ..modules.iconsizes import IconSizes
from ..modules.imgutils import (buildIcon, QUriIcon, QIconPickable)
from ..pktk import *
from .wedialog import WEDialog
from .wiconselector import (WIconSelector, WIconSelectorDialog)
from .wlineedit import WLineEdit
from .wtextedit import (WTextEdit, WTextEditDialog, WTextEditBtBarOption)
from .wiodialog import (WDialogBooleanInput, WDialogFile)


class SetupManagerBase(QObject):
    """Common base for groups & setups"""
    updated = Signal(QObject, str)

    IMG_SIZE = 256
    IMG_QSIZE = QSize(256, 256)

    KEY_UUID = 'uuid'
    KEY_POSITION = 'position'
    KEY_NAME = 'name'
    KEY_COMMENTS = 'comments'
    KEY_ICON_URI = 'iconUri'
    KEY_ICON = 'icon'
    KEY_DATE_CREATED = 'dateCreated'
    KEY_DATE_MODIFIED = 'dateModified'

    def __init__(self, parent=None):
        super(SetupManagerBase, self).__init__(None)
        self.__uuid = QUuid.createUuid().toString().strip("{}")
        self.__emitUpdated = 0
        self.__position = 999999
        self.__node = None
        self.__iconUri = 'pktk:brush_tune'
        self.__icon = buildIcon(self.__iconUri)
        self.__name = ''
        self.__comments = ''
        self.__dateCreated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.__dateModified = self.__dateCreated

    def _setId(self, id):
        """Set unique id """
        if id is None:
            self.__uuid = QUuid.createUuid().toString().strip("{}")
        else:
            self.__uuid = id.strip("{}")

    def id(self):
        """Return unique id"""
        return self.__uuid

    def position(self):
        """Return item position in list"""
        return self.__position

    def setPosition(self, position):
        """Set item position"""
        if isinstance(position, int) and self.__position != position:
            self.__position = position
            self.applyUpdate('position')

    def name(self):
        """Return item name"""
        return self.__name

    def setName(self, value):
        """Set name"""
        if value != self.__name:
            self.__name = value
            self.applyUpdate('name')

    def comments(self):
        """Return current comment for item"""
        return self.__comments

    def setComments(self, value):
        """Set current comment for item"""
        if value != self.__comments:
            if stripHtml(value).strip() != '':
                self.__comments = value
            else:
                self.__comments = ''
            self.applyUpdate('comments')

    def iconUri(self):
        """Return icon uri"""
        return self.__iconUri

    def setIconUri(self, uri, icon=None):
        """Set item image uri"""
        if isinstance(uri, QUriIcon) and self.__iconUri != uri.uri():
            self.__iconUri = uri.uri()
            self.__icon = uri.icon()
            self.applyUpdate('iconUri')
        elif isinstance(uri, str) and self.__iconUri != uri:
            self.__iconUri = uri
            if icon is None:
                try:
                    icon = buildIcon(uri)
                    self.__icon = icon
                except Exception as e:
                    # not able to create icon?
                    # ignore case
                    pass
            self.applyUpdate('iconUri')

    def icon(self):
        return self.__icon

    def dateCreated(self):
        """Return creation date"""
        return self.__dateCreated

    def setDateCreated(self, date):
        """Set creation date"""
        if isinstance(date, str) and self.__dateCreated != date:
            self.__dateCreated = date
            self.applyUpdate('dateCreated')

    def dateModified(self):
        """Return last modification date"""
        return self.__dateModified

    def setDateModified(self, date=None):
        """Set modification date"""
        if isinstance(date, str) and self.__dateModified != date:
            self.__dateModified = date
            self.applyUpdate('dateModified')
        elif date is None:
            self.__dateModified = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.applyUpdate('dateModified')

    def acceptedChild(self):
        """Return a list of allowed children types

        Return empty list if node don't accept childs
        """
        return tuple()

    def applyUpdate(self, property):
        if self.__emitUpdated == 0:
            self.updated.emit(self, property)

    def beginUpdateCreated(self):
        """Start updating massivelly and then do not emit update"""
        self.__emitUpdated += 1

    def endUpdateCreated(self):
        """Stop updating massivelly and then emit update"""
        self.__emitUpdated -= 1
        if self.__emitUpdated < 0:
            self.__emitUpdated = 0
        elif self.__emitUpdated == 0:
            self.applyUpdate('*')

    def inUpdateCreated(self):
        """Return if currently in a massive update"""
        return (self.__emitUpdated != 0)

    def node(self):
        """return node owner"""
        return self.__node

    def setNode(self, node):
        """set node owner"""
        self.__node = node


class SetupManagerSetup(SetupManagerBase):
    """Class to manage setup definition"""

    KEY_DATA = 'data'

    def __init__(self, initFrom=None):
        super(SetupManagerSetup, self).__init__(None)

        self.__data = None

        if isinstance(initFrom, SetupManagerSetup):
            # clone setup definition
            self.importData(initFrom.exportData())
        elif isinstance(initFrom, dict):
            self.importData(initFrom)

    def __repr__(self):
        return f"<SetupManagerSetup({self.id()}, {self.name()})>"

    def exportData(self):
        """Export setup definition as dictionary"""
        icon = ''
        uriIcon = self.iconUri()
        if re.search("^(pktk|krita):", uriIcon) is None:
            # an external file; serialize ICON in a base64 format
            icon = QIconPickable(self.icon()).toB64()

        returned = {
                SetupManagerBase.KEY_UUID: self.id(),
                SetupManagerBase.KEY_NAME: self.name(),
                SetupManagerBase.KEY_COMMENTS: self.comments(),
                SetupManagerBase.KEY_POSITION: self.position(),
                SetupManagerBase.KEY_ICON_URI: uriIcon,
                SetupManagerBase.KEY_ICON: icon,
                SetupManagerBase.KEY_DATE_CREATED: self.dateCreated(),
                SetupManagerBase.KEY_DATE_MODIFIED: self.dateModified(),
                SetupManagerSetup.KEY_DATA: self.data()
            }

        return returned

    def importData(self, value):
        """Import definition from dictionary"""
        if not isinstance(value, dict):
            return False

        self.beginUpdateCreated()
        try:
            if SetupManagerBase.KEY_UUID in value:
                self._setId(value[SetupManagerBase.KEY_UUID])
            if SetupManagerBase.KEY_POSITION in value:
                self.setPosition(value[SetupManagerBase.KEY_POSITION])
            if SetupManagerBase.KEY_NAME in value:
                self.setName(value[SetupManagerBase.KEY_NAME])
            if SetupManagerBase.KEY_COMMENTS in value:
                self.setComments(value[SetupManagerBase.KEY_COMMENTS])
            if SetupManagerBase.KEY_DATE_CREATED in value:
                self.setDateCreated(value[SetupManagerBase.KEY_DATE_CREATED])
            if SetupManagerBase.KEY_DATE_MODIFIED in value:
                self.setDateModified(value[SetupManagerBase.KEY_DATE_MODIFIED])
            if SetupManagerSetup.KEY_DATA in value:
                self.setData(value[SetupManagerSetup.KEY_DATA])

            if SetupManagerBase.KEY_ICON_URI in value:
                iconB64 = ''

                if SetupManagerBase.KEY_ICON in value:
                    iconB64 = value[SetupManagerBase.KEY_ICON]

                if iconB64 != '':
                    # if a b64 icon is provided, use it (uri is then provided as an information)
                    icon = QIconPickable()
                    self.setIconUri(QUriIcon(value[SetupManagerBase.KEY_ICON_URI], icon.fromB64(iconB64)))
                else:
                    self.setIconUri(value[SetupManagerBase.KEY_ICON_URI])

            isValid = True
        except Exception as e:
            print("Unable to import setup definition:", e)
            isValid = False

        self.endUpdateCreated()
        return isValid

    def data(self):
        """Return setup data

        Format is not known, can be anything
        """
        return self.__data

    def setData(self, data):
        """Return setup data

        Format is not known, can be anything
        """
        if data != self.__data:
            self.__data = data
            self.applyUpdate('data')


class SetupManagerGroup(SetupManagerBase):
    """Class to manage group definition"""

    KEY_EXPANDED = 'expanded'

    def __init__(self, initFrom=None):
        super(SetupManagerGroup, self).__init__(None)

        self.__expanded = True

        self.__iconUriOpen = 'pktk:folder_open'
        self.__iconUriClose = 'pktk:folder_close'

        self.__iconOpen = buildIcon(self.__iconUriOpen)
        self.__iconClose = buildIcon(self.__iconUriClose)

        if isinstance(initFrom, SetupManagerGroup):
            # clone group
            self.importData(initFrom.exportData())
        elif isinstance(initFrom, dict):
            self.importData(initFrom)

    def __repr__(self):
        return f"<SetupManagerGroup({self.id()}, {self.name()})>"

    def expanded(self):
        """Return if group is expanded or not"""
        return self.__expanded

    def setExpanded(self, expanded):
        """Set if if group is expanded or not"""
        if isinstance(expanded, bool) and expanded != self.__expanded:
            self.__expanded = expanded
            self.applyUpdate('expanded')

    def acceptedChild(self):
        """Return a list of allowed children types

        Return empty list if node don't accept childs
        """
        return (SetupManagerSetup, SetupManagerGroup)

    def exportData(self):
        """Export group definition as dictionary"""
        returned = {
                SetupManagerBase.KEY_UUID: self.id(),
                SetupManagerBase.KEY_NAME: self.name(),
                SetupManagerBase.KEY_COMMENTS: self.comments(),
                SetupManagerBase.KEY_POSITION: self.position(),
                SetupManagerBase.KEY_ICON_URI: '',
                SetupManagerBase.KEY_ICON: '',
                SetupManagerBase.KEY_DATE_CREATED: self.dateCreated(),
                SetupManagerBase.KEY_DATE_MODIFIED: self.dateModified(),
                SetupManagerGroup.KEY_EXPANDED: self.__expanded
            }

        return returned

    def importData(self, value):
        """Import group definition from dictionary"""
        if not isinstance(value, dict):
            return False

        self.beginUpdateCreated()

        try:
            if SetupManagerBase.KEY_UUID in value:
                self._setId(value[SetupManagerBase.KEY_UUID])
            if SetupManagerBase.KEY_POSITION in value:
                self.setPosition(value[SetupManagerBase.KEY_POSITION])
            if SetupManagerBase.KEY_NAME in value:
                self.setName(value[SetupManagerBase.KEY_NAME])
            if SetupManagerBase.KEY_COMMENTS in value:
                self.setComments(value[SetupManagerBase.KEY_COMMENTS])
            if SetupManagerBase.KEY_DATE_CREATED in value:
                self.setDateCreated(value[SetupManagerBase.KEY_DATE_CREATED])
            if SetupManagerBase.KEY_DATE_MODIFIED in value:
                self.setDateModified(value[SetupManagerBase.KEY_DATE_MODIFIED])
            if SetupManagerGroup.KEY_EXPANDED in value:
                self.setExpanded(value[SetupManagerGroup.KEY_EXPANDED])

            isValid = True
        except Exception as e:
            print("Unable to import group definition:", e)
            isValid = False

        self.endUpdateCreated()
        return isValid

    def icon(self, expandedStatus=None):
        """Return icon for group

        if expandedStatus is none, return image according to expanded/collapsed status
        if expandedStatus is True, return image for exapanded status, otherwise return image for collapsed status
        """
        if expandedStatus is None:
            expandedStatus = self.expanded()

        if expandedStatus:
            return self.__iconOpen
        else:
            return self.__iconClose

    def setIconUri(self, open, close):
        """Set alternative icons for open and close folder

        Given `open` and `close` must be icon uri; if None is given, default icon are set
        """
        if isinstance(open, str) and self.__iconUriOpen != open:
            icon = buildIcon(open)
            if icon:
                self.__iconOpen = icon
                self.__iconUriOpen = open
        elif open is None:
            self.__iconUriOpen = 'pktk:folder_open'
            self.__iconOpen = buildIcon(self.__iconUriOpen)

        if isinstance(close, str) and self.__iconUriClose != close:
            icon = buildIcon(close)
            if icon:
                self.__iconClose = icon
                self.__iconUriClose = close
        elif close is None:
            self.__iconUriClose = 'pktk:folder_close'
            self.__iconClose = buildIcon(self.__iconUriClose)

        self.applyUpdate('icon')


class SetupManagerNode(QStandardItem):
    """A node for SetupManagerModel"""

    def __init__(self, data, parent=None):
        if parent is not None and not isinstance(parent, SetupManagerNode):
            raise EInvalidType("Given `parent` must be a <SetupManagerNode>")
        elif not isinstance(data, SetupManagerBase):
            raise EInvalidType("Given `data` must be a <SetupManagerBase>")

        self.__parentNode = None
        self.__dataNode = None

        self.__inUpdate = 0
        self.__dndOver = False

        # Initialise node childs
        self.__childNodes = []

        self.setData(data)
        self.setParentNode(parent)

    def __repr__(self):
        if self.__parentNode:
            parent = f"{self.__parentNode.data().id()}"
        else:
            parent = "None"

        if self.__dataNode:
            data = f"{self.__dataNode}"
        else:
            data = "None"

        return f"<SetupManagerNode(parent:{parent}, data:{data}, childs({len(self.__childNodes)}):{self.__childNodes})>"

    def beginUpdateCreated(self):
        self.__inUpdate += 1

    def endUpdateCreated(self):
        self.__inUpdate -= 1
        if self.__inUpdate < 0:
            self.__inUpdate = 0
        elif self.__inUpdate == 0:
            self.__childNodes.sort(key=lambda item: item.data().position())
            # need to recalculate position properly;
            for index, child in enumerate(self.__childNodes):
                child.data().setPosition((index + 1) * 100)

    def childs(self):
        """Return list of childs"""
        return self.__childNodes

    def child(self, row):
        """Return child at given position"""
        if row < 0 or row >= len(self.__childNodes):
            return None
        return self.__childNodes[row]

    def appendChild(self, childNode):
        """Add a new child at the end of child list"""
        if isinstance(childNode, list):
            self.beginUpdateCreated()
            for childNodeToAdd in childNode:
                self.appendChild(childNodeToAdd)
            self.endUpdateCreated()
        elif not isinstance(childNode, SetupManagerNode):
            raise EInvalidType("Given `childNode` must be a <SetupManagerNode>")
        elif isinstance(childNode.data(), self.__dataNode.acceptedChild()):
            self.__childNodes.append(childNode)
            self.beginUpdateCreated()
            childNode.beginUpdateCreated()
            childNode.setParentNode(self)
            childNode.endUpdateCreated()
            self.endUpdateCreated()

    def removeChild(self, childNode):
        """Remove a child
        Removed child is returned
        Or None if child is not found
        """
        if isinstance(childNode, list):
            returned = []
            self.beginUpdateCreated()
            for childNodeToRemove in childNode:
                returned.append(self.removeChild(childNodeToRemove))
            self.__endUpdate()
            return returned
        elif not isinstance(childNode, (int, SetupManagerNode)):
            raise EInvalidType("Given `childNode` must be a <SetupManagerNode> or <int>")
        else:
            self.beginUpdateCreated()
            try:
                if isinstance(childNode, SetupManagerNode):
                    returned = self.__childNodes.pop(self.__childNodes.index(childNode))
                else:
                    # row number provided
                    returned = self.__childNodes.pop(childNode)
            except Exception:
                returned = None

            self.endUpdateCreated()
            return returned

    def insertChild(self, position, childNode):
        self.beginUpdateCreated()
        row = 0
        for i, child in enumerate(self.__childNodes):
            if child.data().position() >= position:
                row = i - 1
                break
        self.__childNodes.insert(row, childNode)
        childNode.beginUpdateCreated()
        childNode.data().setPosition(position)
        childNode.setParentNode(self)
        childNode.endUpdateCreated()
        self.endUpdateCreated()

    def remove(self):
        """Remove item from parent"""
        if self.__parentNode:
            self.__parentNode.removeChild(self)

    def clear(self):
        """Remove all childs"""
        self.beginUpdateCreated()
        self.__childNodes = []
        self.endUpdateCreated()

    def childCount(self):
        """Return number of children the current node have"""
        return len(self.__childNodes)

    def row(self):
        """Return position in parent's children list"""
        returned = 0
        if self.__parentNode:
            returned = self.__parentNode.childRow(self)
        return returned

    def childRow(self, node):
        """Return row number for given node

        If node is not found, return -1
        """
        try:
            return self.__childNodes.index(node)
        except Exception:
            return -1

    def columnCount(self):
        """Return number of column for item"""
        return 1

    def data(self):
        """Return data for node

        Content is managed from model
        """
        return self.__dataNode

    def setData(self, data):
        """Set node data"""
        if not isinstance(data, SetupManagerBase):
            raise EInvalidType("Given `data` must be a <SetupManagerBase>")
        self.__dataNode = data
        self.__dataNode.setNode(self)

    def dndOver(self):
        """memorize drag'n'drop over status"""
        return self.__dndOver

    def setDndOver(self, value):
        """memorize drag'n'drop over status"""
        self.__dndOver = value

    def parentNode(self):
        """Return current parent"""
        return self.__parentNode

    def setParentNode(self, parent):
        """Set current parent"""
        if parent is None or isinstance(parent, SetupManagerNode):
            self.__parentNode = parent

    def level(self):
        if self.__parentNode:
            return 1 + self.__parentNode.level()
        return 0

    def childStats(self):
        """return child statistics:
            - number of groups/sub-groups
            - number of setups/sub-setups
        """
        returned = {
                'groups': 0,
                'setups': 0,
                'sub-groups': 0,
                'sub-setups': 0,
                'total-groups': 0,
                'total-setups': 0
            }

        if len(self.__childNodes):
            for child in self.__childNodes:
                data = child.data()

                if isinstance(data, SetupManagerSetup):
                    returned['setups'] += 1
                    returned['total-setups'] += 1
                else:
                    returned['groups'] += 1
                    returned['total-groups'] += 1

                    stats = child.childStats()

                    returned['sub-setups'] += stats['total-setups']
                    returned['total-setups'] += stats['total-setups']

                    returned['sub-groups'] += stats['total-groups']
                    returned['total-groups'] += stats['total-groups']

            # sub don't count childs from groups
            returned['sub-setups'] -= returned['setups']
            returned['sub-groups'] -= returned['groups']
        return returned


class SetupManagerModel(QAbstractItemModel):
    """A model to access setup and groups in an hierarchical tree"""
    updateWidth = Signal()

    HEADERS = [i18n('Setup'), i18n('Modified'), i18n('Description')]

    COLNUM_SETUP = 0
    COLNUM_DATE = 1
    COLNUM_COMMENT = 2

    COLNUM_LAST = 2

    ROLE_ID = Qt.UserRole + 1
    ROLE_DATA = Qt.UserRole + 2
    ROLE_NODE = Qt.UserRole + 3
    ROLE_DND = Qt.UserRole + 4

    TYPE_SETUP = 0b01
    TYPE_GROUP = 0b10

    MIME_DATA = 'x-application/pykrita-pktk-smm-dnd-modelindex'

    def __init__(self, parent=None):
        """Initialise data model"""
        super(SetupManagerModel, self).__init__(parent)

        self.__rootNode = SetupManagerNode(SetupManagerGroup({SetupManagerGroup.KEY_UUID: "00000000-0000-0000-0000-000000000000",
                                                              SetupManagerGroup.KEY_NAME: "root node"
                                                              }))

        # maintain an index for Id
        self.__idIndexes = {}

        # massive updates
        self.__inMassiveUpdate = 0

    def __getIdIndex(self, id):
        def getIdIndexes(id, parent, modelIndexParent):
            for childRow in range(parent.childCount()):
                child = parent.child(childRow)
                data = child.data()

                currentIndex = self.index(childRow, 0, modelIndexParent)

                if data.id() == id:
                    return currentIndex

                returned = getIdIndexes(id, child, currentIndex)
                if returned.isValid():
                    return returned
            return QModelIndex()
        returned = getIdIndexes(id, self.__rootNode, QModelIndex())
        return returned

    def __updateIdIndex(self):
        """Build internal dictionnary of all setups/groups id

        key = id
        value = index
        """
        def getIdIndexes(parent):
            for childRow in range(parent.childCount()):
                child = parent.child(childRow)
                data = child.data()

                if isinstance(data, SetupManagerSetup):
                    self.__idIndexes[data.id()] = SetupManagerModel.TYPE_SETUP
                else:
                    self.__idIndexes[data.id()] = SetupManagerModel.TYPE_GROUP

                getIdIndexes(child)

        self.__idIndexes = {}
        getIdIndexes(self.__rootNode)

    def __beginUpdate(self):
        """Start a massive update"""
        self.__inMassiveUpdate += 1

    def __endUpdate(self):
        """Start a massive update"""
        self.__inMassiveUpdate -= 1
        if self.__inMassiveUpdate == 0:
            self.__updateIdIndex()
            self.updateWidth.emit()

    def flags(self, index):
        """Model accept drap'n'drop"""
        if not index.isValid():
            return Qt.NoItemFlags
        return super(SetupManagerModel, self).flags(index) | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        """Model accept move of items only"""
        return Qt.MoveAction

    def supportedDragActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        """return mime type managed by treeview"""
        return [SetupManagerModel.MIME_DATA]

    def mimeData(self, indexes):
        """Encode current node memory address to mime data"""
        nodes = [id(self.nodeForIndex(index)) for index in indexes if index.column() == 0]

        mimeData = QMimeData()
        mimeData.setData(SetupManagerModel.MIME_DATA, json.dumps(nodes).encode())
        return mimeData

    def dropMimeData(self, mimeData, action, row, column, newParent):
        """User drop a group/setup on view

        Need to process it: move item(s) from source to target
        """
        if action != Qt.MoveAction:
            return False

        if not mimeData.hasFormat(SetupManagerModel.MIME_DATA):
            return False

        idList = json.loads(bytes(mimeData.data(SetupManagerModel.MIME_DATA)).decode())

        newParentNode = self.nodeForIndex(newParent)
        if not newParentNode:
            return False

        # take current target position to determinate new position for items
        targetPosition = newParentNode.data().position()
        if newParentNode.dndOver() == QAbstractItemView.AboveItem:
            positionUpdate = -1
            # above a SetupManagerGroup ==> need to get group parent
            # above a SetupManagerSetup ==> need to get setup parent
            targetParentNode = newParentNode.parentNode()
            targetParentIndex = self.parent(newParent)
            row = newParentNode.row()
        else:
            positionUpdate = 1
            # below a SetupManagerGroup ==> SetupManagerGroup is the parent
            # below a SetupManagerSetup ==> need to get setup parent
            if isinstance(newParentNode.data(), SetupManagerSetup):
                targetParentNode = newParentNode.parentNode()
                targetParentIndex = self.parent(newParent)
                row = newParentNode.row() + 1
            else:
                targetParentIndex = newParent
                targetParentNode = newParentNode
                # when moved directly into a group, ensure the item is moved to the last position
                targetPosition = 999999
                row = newParentNode.row() + 1

        if positionUpdate < 0:
            # above, need to process in inverted order to keep position
            idList.reverse()

        self.__beginUpdate()
        targetParentNode.beginUpdateCreated()
        for numDataId, nodeDataId in enumerate(idList):
            itemNode = ctypes.cast(nodeDataId, ctypes.py_object).value

            newPosition = targetPosition + positionUpdate * (numDataId+1)

            # remove from old position
            self.removeNode(itemNode)

            self.beginInsertRows(targetParentIndex, row, row)
            targetParentNode.insertChild(newPosition, itemNode)
            self.endInsertRows()

            row += positionUpdate

        targetParentNode.endUpdateCreated()
        self.__endUpdate()

        return True

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column for index"""
        return SetupManagerModel.COLNUM_LAST+1

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows for index"""
        if parent.column() > 0:
            return 0

        parentNode = self.nodeForIndex(parent)

        return parentNode.childCount()

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        if not index.isValid():
            return None

        item = index.internalPointer()
        if item is None:
            # not sure when/why it could occurs...
            return None

        if role == SetupManagerModel.ROLE_NODE:
            return item

        data = item.data()  # get SetupManagerSetup or SetupManagerGroup

        column = index.column()
        row = index.row()

        if role == SetupManagerModel.ROLE_ID:
            return data.id()
        elif role == SetupManagerModel.ROLE_DATA:
            return data
        elif role == Qt.DisplayRole:
            column = index.column()
            if column == SetupManagerModel.COLNUM_SETUP:
                return data.name()
            elif column == SetupManagerModel.COLNUM_COMMENT:
                return data.comments()
            elif column == SetupManagerModel.COLNUM_DATE:
                return data.dateModified()

        if isinstance(data, SetupManagerSetup):
            if role == Qt.DecorationRole and column == SetupManagerModel.COLNUM_SETUP:
                icon = data.icon()
                if icon:
                    # QIcon
                    return icon
                else:
                    return buildIcon('pktk:warning')
        elif isinstance(data, SetupManagerGroup):
            if role == Qt.DecorationRole and column == SetupManagerModel.COLNUM_SETUP:
                icon = data.icon()
                if icon:
                    # QIcon
                    return icon
                else:
                    return buildIcon('pktk:folder_open')

        return None

    def index(self, row, column, parent=None):
        """Provide indexes for views and delegates to use when accessing data

        If an invalid model index is specified as the parent, it is up to the model to return an index that corresponds to a top-level item in the model.
        """
        if not isinstance(parent, QModelIndex) or not self.hasIndex(row, column, parent):
            return QModelIndex()

        parentNode = self.nodeForIndex(parent)
        childNode = parentNode.child(row)

        if childNode:
            return self.createIndex(row, column, childNode)
        else:
            return QModelIndex()

    def parent(self, index):
        """return parent (QModelIndex) for given index"""
        if not isinstance(index, QModelIndex) or not index.isValid():
            return QModelIndex()

        childNode = self.nodeForIndex(index)
        if not childNode or childNode == self.__rootNode:
            return QModelIndex()

        parentNode = childNode.parentNode()
        if parentNode == self.__rootNode:
            return QModelIndex()

        return self.createIndex(parentNode.row(), 0, parentNode)

    def nodeForIndex(self, index):
        """Return node for given index

        If index is not valid, return a toot node
        """
        if not index.isValid():
            return self.__rootNode
        else:
            return index.internalPointer()

    def removeNode(self, node):
        """Delete a SetupManagerNode from model, update model properly to update view according to MVC principle"""
        if isinstance(node, SetupManagerNode):
            row = node.row()
            index = self.createIndex(row, 0, node)
            self.beginRemoveRows(self.parent(index), row, row)
            node.parentNode().removeChild(row)
            self.endRemoveRows()

    def insertNode(self, node, parentNode):
        """Insert a SetupManagerNode in model, update model properly to update view according to MVC principle"""
        if isinstance(node, SetupManagerNode) and isinstance(parentNode, SetupManagerNode):
            row = parentNode.childCount()
            parentIndex = self.__getIdIndex(parentNode.data().id())

            self.beginInsertRows(parentIndex, row, row)
            parentNode.appendChild(node)
            self.endInsertRows()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return label for given data section"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return SetupManagerModel.HEADERS[section]
        return None

    def itemSelection(self, item):
        """Return QItemSelection for given item"""
        returned = QItemSelection()

        if isinstance(item, SetupManagerBase):
            index = self.__getIdIndex(item.id())
            if index.isValid():
                indexS = self.createIndex(index.row(), 0, item.node())
                indexE = self.createIndex(index.row(), SetupManagerModel.COLNUM_LAST, item.node())
                returned = QItemSelection(indexS, indexE)

        return returned

    def idIndexes(self, options={}):
        """Return a dictionnary of all setups/groups id

        key = id
        value = index

        Given `options` is a dict that can contains
            'setups': True         # if True (default), result contains setups Id
            'groups': True          # if True (default), result contains groups Id
        """
        if 'setups' not in options:
            options['setups'] = True
        if 'groups' not in options:
            options['groups'] = True
        if 'asIndex' not in options:
            options['asIndex'] = True

        if not isinstance(options['setups'], bool):
            raise EInvalidType("Given `option['setups'] must be a <bool>")
        if not isinstance(options['groups'], bool):
            raise EInvalidType("Given `option['groups'] must be a <bool>")
        if not isinstance(options['asIndex'], bool):
            raise EInvalidType("Given `option['asIndex'] must be a <bool>")

        self.__updateIdIndex()

        if not (options['setups'] or options['groups']):
            # nonsense but...
            return {}
        elif options['setups'] and options['groups']:
            # return everything
            returned = [id for id in self.__idIndexes]
        elif options['setups']:
            # return setups
            returned = [id for id in self.__idIndexes if self.__idIndexes[id] == SetupManagerModel.TYPE_SETUP]
        elif options['groups']:
            # return groups
            returned = [id for id in self.__idIndexes if self.__idIndexes[id] == SetupManagerModel.TYPE_GROUP]
        else:
            # should not occurs
            return {}

        if options['asIndex']:
            return {id: self.__getIdIndex(id) for id in returned}
        else:
            return {id: self.__idIndexes[id] for id in returned}

    def getFromId(self, id, asIndex=True):
        """Return setup/group from given Id

        Return None if not found
        """
        index = self.__getIdIndex(id)
        if index.isValid():
            if asIndex:
                return index
            else:
                return self.data(index, SetupManagerModel.ROLE_DATA)
        else:
            return None

    def getGroupItems(self, groupId=None, asIndex=True):
        """Return items from given `groupId`

        If `groupId` is None, return items from root
        If `groupId` is not found, return empty list

        If `asIndex` is True, return items as QModelIndex otherwise return SetupManagerGroup/SetupManagerSetup
        """
        returned = []
        node = None
        self.__updateIdIndex()

        if groupId is None:
            node = self.__rootNode
        elif isinstance(groupId, str):
            index = self.__getIdIndex(groupId)
            if index.isValid():
                data = self.data(index, SetupManagerModel.ROLE_DATA)
                if isinstance(data, SetupManagerGroup) and data.id() == groupId:
                    node = self.data(index, SetupManagerModel.ROLE_NODE)
        elif isinstance(groupId, SetupManagerGroup):
            return self.getGroupItems(groupId.id(), asIndex)

        if node is not None:
            # get all data, maybe not ordered
            returned = [childNode.data() for childNode in node.childs()]
            returned.sort(key=lambda item: item.position())

            if asIndex:
                returned = [self.__getIdIndex(item.id()) for item in returned]
        return returned

    def clear(self):
        """Clear all setups & groups"""
        if self.__inMassiveUpdate == 0:
            self.beginResetModel()

        self.__beginUpdate()
        self.__rootNode.clear()
        self.__endUpdate()

        if self.__inMassiveUpdate == 0:
            self.endResetModel()

    def remove(self, itemToRemove):
        """Remove item from list

        Given `itemToRemove` can:
        - a list
        - an id
        - an item
        - a node
        """
        if isinstance(itemToRemove, list) and len(itemToRemove) > 0:
            # a list of item to remove
            self.__beginUpdate()
            for item in list(itemToRemove):
                self.remove(item)
            self.__endUpdate()
        elif isinstance(itemToRemove, SetupManagerNode):
            # a node
            self.__beginUpdate()
            self.removeNode(itemToRemove)
            self.__endUpdate()
        elif isinstance(itemToRemove, str):
            # a string --> assume it's an Id
            index = self.getFromId(itemToRemove)
            if index is not None:
                self.remove(self.data(index, SetupManagerModel.ROLE_NODE))
        elif isinstance(itemToRemove, SetupManagerBase):
            self.remove(itemToRemove.id())

    def add(self, itemToAdd, parent=None):
        """Add item to parent

        If parent is None, item is added to rootNode
        """
        if parent is None:
            parent = self.__rootNode

        if isinstance(parent, SetupManagerNode):
            if isinstance(itemToAdd, list):
                # a list of item to add
                self.__beginUpdate()
                for item in itemToAdd:
                    self.add(item, parent)
                self.__endUpdate()
            elif isinstance(itemToAdd, SetupManagerBase):
                if isinstance(itemToAdd, parent.data().acceptedChild()):
                    self.__beginUpdate()
                    self.insertNode(SetupManagerNode(itemToAdd, parent), parent)
                    self.__endUpdate()
        elif isinstance(parent, str):
            # a string --> assume it's an Id
            index = self.getFromId(parent)
            if index is not None:
                self.add(itemToAdd, self.data(index, SetupManagerModel.ROLE_NODE))
        elif isinstance(parent, SetupManagerBase):
            self.add(itemToAdd, parent.id())

    def updateItem(self, itemToUpdate):
        """The given item has been updated"""
        if isinstance(itemToUpdate, list):
            # a list of item to add
            self.__beginUpdate()
            for item in itemToUpdate:
                self.updateItem(item)
            self.__endUpdate()
        elif isinstance(itemToUpdate, SetupManagerBase):
            self.updatedData(self.getFromId(itemToUpdate.id(), True))

    def updatedData(self, index):
        """Data has been updated for index, emit signal"""
        if index.isValid():
            self.dataChanged.emit(index, index, [SetupManagerModel.ROLE_DATA])

    def importData(self, data, mergeWithExistingData=False):
        """Load model from given `data` provided as a <dict>
            - 'setups' (list of SetupManagerSetup)
            - 'groups' (list of SetupManagerGroup)
            - 'nodes' (list defined hierarchy)
                [id, id, (id, [id, id, (id, [id])])]
        """
        def addNodes(idList, parent):
            toAdd = []
            for id in idList:
                if isinstance(id, str):
                    if id in tmpIdIndex:
                        node = SetupManagerNode(tmpIdIndex[id], parent)
                        toAdd.append(node)
                    else:
                        raise EInvalidValue(f"Given `id` ({id}) can't be added, index not exist")
                elif isinstance(id, (tuple, list)):
                    # a group
                    groupNode = SetupManagerNode(tmpIdIndex[id[0]], parent)
                    addNodes(id[1], groupNode)
                    toAdd.append(groupNode)
                else:
                    raise EInvalidValue(f"Given `id` must be a valid <str>")
            parent.appendChild(toAdd)

        if not isinstance(data, dict):
            raise EInvalidType("Given `data` must be a <dict>")
        elif ('setups' not in data or 'groups' not in data or 'nodes' not in data):
            raise EInvalidValue("Given `data` must contains following keys: 'setups', 'groups', 'nodes'")

        self.beginResetModel()
        self.__beginUpdate()

        for index, setup in enumerate(data['setups']):
            if isinstance(data['setups'][index], dict):
                data['setups'][index] = SetupManagerSetup(data['setups'][index])

        for index, group in enumerate(data['groups']):
            if isinstance(data['groups'][index], dict):
                data['groups'][index] = SetupManagerGroup(data['groups'][index])

        if mergeWithExistingData:
            # a dictionary id => SetupManagerNode

            # when merging, we must ensure there's no duplicate ID for items
            # then for imported item, generate new ID

            # id map table old->new
            mapTable = {}

            # manage setups & groups + reaffect new Id to item
            for item in (data['setups'] + data['groups']):
                oldId = item.id()
                item._setId(None)
                mapTable[oldId] = item.id()

            # manage nodes
            # nodes are list that can includes list; easy method to manage it:
            # - convert to json string
            # - replace id
            # - convert to list
            nodesAsList = json.dumps(data['nodes'])

            for oldId, newId in mapTable.items():
                nodesAsList = nodesAsList.replace(oldId, newId)

            nodes = json.loads(nodesAsList)
        else:
            self.clear()
            nodes = data['nodes']

        # a dictionary id => SetupManagerNode
        tmpIdIndex = {setup.id(): setup for setup in data['setups']} | {group.id(): group for group in data['groups']}

        if len(nodes) == 0:
            # in this case create everything at root level
            nodes = list(tmpIdIndex.keys())

        addNodes(nodes, self.__rootNode)
        self.__endUpdate()
        self.endResetModel()

    def exportData(self, itemId=[]):
        """export model as dict
            {
                'setups': list of SetupManagerSetup
                'groups':  list of SetupManagerGroup
                'nodes':   list defined hierarchy
                               [id, id, (id, [id, id, (id, [id])])]
            }

        If given `itemId` list is provided, only items for which id is provided are exported
        """
        def export(parent, itemId, returned):
            nodes = []
            for childRow in range(parent.childCount()):
                child = parent.child(childRow)
                data = child.data()

                if itemId is None or data.id() in itemId:
                    # item can be exported
                    if isinstance(data, SetupManagerSetup):
                        returned['setups'].append(data)
                        nodes.append(data.id())
                    else:
                        returned['groups'].append(data)
                        # exporting a group means to export all children too, then provide None as itemId
                        nodes.append((data.id(), export(child, None, returned)))
                elif isinstance(data, SetupManagerGroup):
                    # item can't be exported, but if it's a group, need to check inside if there's an item to export
                    subNodes = export(child, itemId, returned)
                    if len(subNodes) > 0:
                        nodes += subNodes
            return nodes

        returned = {
                'setups': [],
                'groups': [],
                'nodes': []
            }

        if not isinstance(itemId, list) or len(itemId) == 0:
            itemId = None

        returned['nodes'] = export(self.__rootNode, itemId, returned)

        return returned

    def rootNode(self):
        """Return root node"""
        return self.__rootNode


class WSetupManagerTv(QTreeView):
    focused = Signal()
    keyPressed = Signal(int)
    iconSizeIndexChanged = Signal(int, QSize)

    def __init__(self, parent=None):
        super(WSetupManagerTv, self).__init__(parent)
        self.setAutoScroll(True)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(False)
        self.setAllColumnsShowFocus(True)
        self.setExpandsOnDoubleClick(False)
        self.setDropIndicatorShown(False)

        self.__parent = parent
        self.__model = None
        self.__selectedBeforeReset = []
        self.__dndOverIndex = None

        self.__fontSize = self.font().pointSizeF()
        if self.__fontSize == -1:
            self.__fontSize = -self.font().pixelSize()

        # value at which treeview apply compacted view (-1: never)
        self.__compactIconSizeIndex = -1

        self.__delegate = SetupManagerModelDelegateTv(self)
        self.setItemDelegate(self.__delegate)

        self.__iconSize = IconSizes([32, 64, 96, 128, 192])
        self.setIconSizeIndex(3)

        self.__contextMenu = QMenu()
        self.__initMenu()

        header = self.header()
        header.sectionResized.connect(self.__sectionResized)

    def __initMenu(self):
        """Initialise context menu"""
        pass

    def __modelAboutToBeReset(self):
        """model is about to be reset"""
        self.__selectedBeforeReset = self.selectedItems()

    def __modelReset(self):
        """model has been reset"""
        for selectedItem in self.__selectedBeforeReset:
            self.selectItem(selectedItem)

        for index in self.__model.idIndexes({'setups': False, 'asIndex': True}).values():
            self.setExpanded(index, index.data(SetupManagerModel.ROLE_DATA).expanded())

        self.__selectedBeforeReset = []
        self.resizeColumns()

    def __modelDataChanged(self, topLeft, bottomRight, roles):
        """Data has been changed"""
        if SetupManagerModel.ROLE_DATA in roles:
            data = topLeft.data(SetupManagerModel.ROLE_DATA)
            if isinstance(data, SetupManagerGroup):
                self.setExpanded(topLeft, data.expanded())

    def __sectionResized(self, index, oldSize, newSize):
        """When section is resized, update rows height"""
        if index == SetupManagerModel.COLNUM_COMMENT and not self.isColumnHidden(SetupManagerModel.COLNUM_COMMENT):
            # update height only if comment section is resized
            self.__delegate.setCSize(newSize)
            for rowNumber in range(self.__model.rowCount()):
                # need to recalculate height for all rows
                self.__delegate.sizeHintChanged.emit(self.__model.createIndex(rowNumber, index))

    def __setDndOverIndex(self, index, position=None):
        """Set given index as current d'n'd index"""
        if self.__dndOverIndex is not None and self.__dndOverIndex != index:
            # remove indicator on index
            node = self.model().data(self.__dndOverIndex, SetupManagerModel.ROLE_NODE)
            if node:
                node.setDndOver(None)

        if isinstance(index, QModelIndex):
            # set indicator on index
            rect = self.visualRect(index)
            indicatorPosition = QAbstractItemView.OnViewport

            if isinstance(position, QPoint):
                half = rect.height()//2
                if position.y() < rect.top() + half:
                    indicatorPosition = QAbstractItemView.AboveItem
                else:
                    indicatorPosition = QAbstractItemView.BelowItem

            node = self.model().data(index, SetupManagerModel.ROLE_NODE)
            if node:
                node.setDndOver(indicatorPosition)

        self.__dndOverIndex = index

        # needed to erase previous d'n'd over indicator
        self.viewport().update()

    def mouseDoubleClickEvent(self, event):
        """Manage double-click on Groups to expand/collapse and keep state in model"""
        index = self.indexAt(event.pos())
        data = index.data(SetupManagerModel.ROLE_DATA)
        if isinstance(data, SetupManagerGroup) and index.column() == SetupManagerModel.COLNUM_SETUP:
            newExpandedState = not self.isExpanded(index)
            data.setExpanded(newExpandedState)
            self.setExpanded(index, newExpandedState)
            self.__model.updatedData(index)
        super(WSetupManagerTv, self).mouseDoubleClickEvent(event)

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
            super(WSetupManagerTv, self).wheelEvent(event)

    def dropEvent(self, event):
        """needed?"""
        super(WSetupManagerTv, self).dropEvent(event)
        self.__setDndOverIndex(None)

    def dragMoveEvent(self, event):
        """Mouse move over items during drag'n'drop

        need to determinate next drop position:
        - above item
        - below item
        - on item (group, or rootnode)
        """
        overIndex = self.indexAt(event.pos())

        self.__setDndOverIndex(overIndex, event.pos())

    def dragLeaveEvent(self, event):
        """leaving viewport, cleanup treeview render"""
        self.__setDndOverIndex(None)

    def paintEvent(self, event):
        """paint treeview

        Override default method, just calling drawTree() method
        This is tricky method to avoid to draw the ugly default "drag over" rectangle
        (then delegated to SetupManagerModelDelegateTv)

        Note: when calling setDropIndicatorShown(False), it seems drag'n'drop is disabled
              so can't use this just to remove ugly dnd rectangle
        """
        painter = QPainter(self.viewport())
        self.drawTree(painter, event.region())

    def resizeColumns(self):
        """Resize columns"""
        minColSize = self.sizeHintForColumn(SetupManagerModel.COLNUM_SETUP)
        if self.columnWidth(SetupManagerModel.COLNUM_SETUP) < minColSize:
            self.setColumnWidth(SetupManagerModel.COLNUM_SETUP, minColSize)
        self.resizeColumnToContents(SetupManagerModel.COLNUM_DATE)

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            self.setIconSize(self.__iconSize.value(True))
            self.__delegate.setIconSize(self.__iconSize.value(False))
            self.__delegate.setCompactSize(self.__iconSize.index() <= self.__compactIconSizeIndex)

            header = self.header()
            self.resizeColumns()
            self.iconSizeIndexChanged.emit(self.__iconSize.index(), self.__iconSize.value(True))

    def setModel(self, model):
        """Initialise treeview header & model"""
        self.__model = model
        super(WSetupManagerTv, self).setModel(self.__model)

        # set colums size rules
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(SetupManagerModel.COLNUM_SETUP, QHeaderView.Interactive)
        header.setSectionResizeMode(SetupManagerModel.COLNUM_DATE, QHeaderView.Interactive)
        header.setSectionResizeMode(SetupManagerModel.COLNUM_COMMENT, QHeaderView.Stretch)

        self.__model.updateWidth.connect(self.resizeColumns)
        self.__model.modelAboutToBeReset.connect(self.__modelAboutToBeReset)
        self.__model.modelReset.connect(self.__modelReset)
        self.__model.dataChanged.connect(self.__modelDataChanged)

        # when model is set, consider there's a reset
        self.__modelReset()

    def selectItem(self, item):
        """Select given item"""
        if isinstance(item, SetupManagerBase):
            itemSelection = self.__model.itemSelection(item)
            self.selectionModel().select(itemSelection, QItemSelectionModel.ClearAndSelect)
        else:
            self.selectionModel().clear()

    def selectedItems(self):
        """Return a list of selected groups/setups items"""
        returned = []
        if self.selectionModel():
            for selectedItem in self.selectionModel().selectedRows(SetupManagerModel.COLNUM_SETUP):
                item = selectedItem.data(SetupManagerModel.ROLE_DATA)
                if item is not None:
                    returned.append(item)
        return returned

    def nbSelectedItems(self):
        """Return number of selected items"""
        return len(self.selectedItems())

    def compactIconSizeIndex(self):
        """Return current defined icon index under which treeview willdisplay compact view for items

        From -1 to 4
        """
        return self.__compactIconSizeIndex

    def setCompactIconSizeIndex(self, value):
        """Set current defined icon index under which treeview willdisplay compact view for items"""
        if not isinstance(value, int):
            raise EInvalidType("Given `index` must be <int>")

        value = max(-1, min(value, 4))
        if self.__compactIconSizeIndex != value:
            self.__compactIconSizeIndex = value
            self.__delegate.setCompactSize(self.__iconSize.index() <= self.__compactIconSizeIndex)
            self.resizeColumns()
            self.update()


class SetupManagerModelDelegateTv(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build improved rendering items for BBSWBrushesTv treeview"""
    MARGIN_TEXT = 8
    TEXT_WIDTH_FACTOR = 1.5
    DND_PENWIDTH = [2, 6, 10, 12, 12]

    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(SetupManagerModelDelegateTv, self).__init__(parent)
        self.__csize = 0
        self.__compactSize = False

        self.__noPen = QPen(Qt.NoPen)
        self.__iconMargins = QMarginsF()
        self.__iconSize = 0
        self.__iconLevelOffset = 0
        self.__iconQSize = QSize()
        self.__iconQSizeF = QSizeF()
        self.__iconAndMarginSize = 0

        colorBrush = QApplication.palette().color(QPalette.Highlight)
        colorBrush.setAlpha(127)
        self.__dndMarkerBrush = QBrush(colorBrush)
        self.__dndMarkerBrushSize = 4

    def __getComments(self, item):
        """Return a text document for group/setup comments"""
        if self.__compactSize:
            # returne elided text on one row only
            return ""
        else:
            textDocument = QTextDocument()
            textDocument.setHtml(item.comments())
            return textDocument

    def setCompactSize(self, value):
        """Activate/deactivate compact size"""
        self.__compactSize = value

    def setIconSize(self, value):
        """define icone size"""
        if self.__iconSize != value:
            self.__iconSize = value
            self.__iconLevelOffset = self.__iconSize//3
            self.__iconQSize = QSize(self.__iconSize, self.__iconSize)
            self.__iconQSizeF = QSizeF(self.__iconSize, self.__iconSize)
            self.__iconAndMarginSize = QSize(self.__iconSize + SetupManagerModelDelegateTv.MARGIN_TEXT, SetupManagerModelDelegateTv.MARGIN_TEXT)

            margin = max(1, self.__iconSize * 0.025)
            self.__iconMargins = QMarginsF(margin, margin, margin, margin)

            match self.__iconSize:
                case 32:
                    self.__dndMarkerBrushSize = 5
                case 64:
                    self.__dndMarkerBrushSize = 10
                case 96:
                    self.__dndMarkerBrushSize = 15
                case _:
                    self.__dndMarkerBrushSize = 20

    def setCSize(self, value):
        """Force size for comments column"""
        self.__csize = value

    def paint(self, painter, option, index):
        """Paint list item"""
        def paintDndMarker(data, dndOver, dndRect):

            match dndOver:
                case QAbstractItemView.AboveItem:
                    rect = QRect(dndRect.topLeft(), QPoint(dndRect.right(), dndRect.top() + self.__dndMarkerBrushSize))
                    painter.fillRect(rect, self.__dndMarkerBrush)
                case QAbstractItemView.BelowItem:
                    if isinstance(data, SetupManagerGroup):
                        rect = dndRect
                    else:
                        rect = QRect(QPoint(dndRect.left(), dndRect.bottom() - self.__dndMarkerBrushSize), dndRect.bottomRight())
                    painter.fillRect(rect, self.__dndMarkerBrush)

        if option.state & QStyle.State_HasFocus == QStyle.State_HasFocus:
            # remove focus style if active
            option.state = option.state & ~QStyle.State_HasFocus

        if index.column() == SetupManagerModel.COLNUM_SETUP:
            # render group/setup information
            self.initStyleOption(option, index)

            # item: Node
            item = index.data(SetupManagerModel.ROLE_NODE)
            # data: SetupManagerSetup or SetupManagerGroup
            data = item.data()

            # Initialise painter
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            # calculate sizes and positions
            iconOffset = int((item.level() - 1) * self.__iconLevelOffset)
            textOffset = iconOffset + self.__iconSize + SetupManagerModelDelegateTv.MARGIN_TEXT
            bgRect = QRectF(option.rect.topLeft() + QPointF(iconOffset, 0), self.__iconQSizeF).marginsRemoved(self.__iconMargins)
            bgRect.setHeight(bgRect.width())
            bRadius = round(max(2, self.__iconSize * 0.050))
            rectTxt = QRectF(option.rect.left() + textOffset, option.rect.top()+4, option.rect.width()-4-textOffset, option.rect.height()-1)

            # Initialise pixmap
            pixmap = data.icon().pixmap(self.__iconQSize)

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            if dndOver := item.dndOver():
                paintDndMarker(item.data(), dndOver, QRect(option.rect.topLeft() + QPoint(iconOffset, 0), option.rect.size() + QSize(-iconOffset, 0)))

            # draw icon
            painter.drawPixmap(option.rect.topLeft(), pixmap)

            # draw text
            textDocument = QTextDocument()
            textDocument.setHtml(data.name())
            textDocument.setDocumentMargin(0)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(rectTxt.size())

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0, 0), rectTxt.size()))

            painter.restore()
            return
        elif index.column() == SetupManagerModel.COLNUM_COMMENT:
            # render comment
            self.initStyleOption(option, index)

            # item: Node
            item = index.data(SetupManagerModel.ROLE_NODE)
            # data: SetupManagerSetup or SetupManagerGroup
            data = item.data()
            textOffset = SetupManagerModelDelegateTv.MARGIN_TEXT
            rectTxt = QRectF(option.rect.left() + textOffset, option.rect.top()+4, option.rect.width()-4-textOffset, option.rect.height()-1)

            textDocument = self.__getComments(data)
            textDocument.setDocumentMargin(0)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.save()

            if dndOver := item.dndOver():
                paintDndMarker(item.data(), dndOver, option.rect)

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0, 0), QSizeF(rectTxt.size())))

            painter.restore()
            return
        elif index.column() == SetupManagerModel.COLNUM_DATE:
            # render date
            self.initStyleOption(option, index)

            # item: Node
            item = index.data(SetupManagerModel.ROLE_NODE)
            # data: SetupManagerSetup or SetupManagerGroup
            data = item.data()
            textOffset = SetupManagerModelDelegateTv.MARGIN_TEXT
            rectTxt = QRectF(option.rect.left() + textOffset, option.rect.top()+4, option.rect.width()-4-textOffset, option.rect.height()-1)

            painter.save()

            if dndOver := item.dndOver():
                paintDndMarker(item.data(), dndOver, option.rect)

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            painter.translate(QPointF(rectTxt.topLeft()))
            painter.drawText(QRectF(QPointF(0, 0), rectTxt.size()), data.dateModified())

            painter.restore()
            return

        QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """Calculate size for items"""
        size = QStyledItemDelegate.sizeHint(self, option, index)

        if index.column() == SetupManagerModel.COLNUM_SETUP:
            node = index.data(SetupManagerModel.ROLE_NODE)
            textDocument = QTextDocument()
            textDocument.setHtml(node.data().name())
            textDocument.setDocumentMargin(0)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(4096, 1000))  # set 1000px size height arbitrary
            textDocument.setPageSize(QSizeF(textDocument.idealWidth() * SetupManagerModelDelegateTv.TEXT_WIDTH_FACTOR, 1000))  # set 1000px size height arbitrary
            size = textDocument.size().toSize() + self.__iconAndMarginSize + QSize((node.level() - 1) * self.__iconLevelOffset, 0)
            if size.height() < self.__iconSize:
                # at least height must be icon size
                size.setHeight(self.__iconSize)
        elif index.column() == SetupManagerModel.COLNUM_COMMENT:
            # size for comments cell (width is forced, calculate height of rich text)
            item = index.data(SetupManagerModel.ROLE_DATA)
            textDocument = self.__getComments(item)
            textDocument.setDocumentMargin(0)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(self.__csize, 1000))  # set 1000px size height arbitrary
            size = QSize(self.__csize, textDocument.size().toSize().height())
        elif index.column() == SetupManagerModel.COLNUM_DATE:
            # size for comments cell (width is forced, calculate height of rich text)
            size.setWidth(size.width() + 2 * SetupManagerModelDelegateTv.MARGIN_TEXT)

        return size


class WSetupManagerOpenSavePreview(WDialogFile.WSubWidget):
    """Preview used in open/save dialog box"""

    def __init__(self, storedDataFormatIdentifier, parent=None):
        super(WSetupManagerOpenSavePreview, self).__init__(parent)

        if not isinstance(storedDataFormatIdentifier, str):
            raise EInvalidType("Given `storedDataFormatIdentifier` must be a string")

        self.__storedDataFormatIdentifier = storedDataFormatIdentifier

        self.__model = SetupManagerModel()
        self.__tvContent = WSetupManagerTv(self)
        self.__tvContent.setModel(self.__model)
        self.__tvContent.setIconSizeIndex(0)

        layout = QVBoxLayout()
        layout.addWidget(self.__tvContent)
        self.setLayout(layout)
        self.setMinimumWidth(800)

    def setFile(self, fileName):
        """When fileName is provided, update image preview content"""
        if fileName == '' or not os.path.isfile(fileName):
            self.__model.clear()
            return False
        else:
            try:
                with open(fileName, 'r') as fhandle:
                    jsonData = fhandle.read()
            except Exception as e:
                print("Unable to import setup manager definition:", e)
                self.__model.clear()
                return False

            data = json.loads(jsonData)

            isValid, message = WSetupManager.isValidPkTkSMContent(data, self.__storedDataFormatIdentifier)
            if isValid:
                self.__model.importData(data[WSetupManager.FILE_KEY_PKTKSM][WSetupManager.FILE_KEY_PKTKSM_DATA])
            else:
                self.__model.clear()
                return False

            return True


class WSetupManagerSaveSettings(WDialogFile.WSubWidget):
    """Settings used in save dialog box"""

    def __init__(self, storedDataFormatIdentifier, selectedActive, parent=None):
        super(WSetupManagerSaveSettings, self).__init__(parent)

        if not isinstance(storedDataFormatIdentifier, str):
            raise EInvalidType("Given `storedDataFormatIdentifier` must be a string")

        self.__storedDataFormatIdentifier = storedDataFormatIdentifier

        self.__lblNfoDescription = QLabel(i18n("Description:"), self)
        self.__teDescription = WTextEdit(self)

        self.__lblNfoSaveMode = QLabel(i18n("Save mode:"), self)
        self.__rbSaveModeAll = QRadioButton(i18n("All setups"), self)
        self.__rbSaveModeAll.setChecked(True)
        self.__rbSaveModeSelection = QRadioButton(i18n("Selected setups"), self)
        self.__rbSaveModeSelection.setEnabled(selectedActive)
        self.__btnGroup = QButtonGroup(self)
        self.__btnGroup.addButton(self.__rbSaveModeAll)
        self.__btnGroup.addButton(self.__rbSaveModeSelection)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__lblNfoDescription)
        layout.addWidget(self.__teDescription)
        layout.addWidget(self.__lblNfoSaveMode)
        layout.addWidget(self.__rbSaveModeAll)
        layout.addWidget(self.__rbSaveModeSelection)
        self.setLayout(layout)
        self.setMinimumHeight(270)

    def setFile(self, fileName):
        """When fileName is provided, update image preview content"""
        if os.path.isfile(fileName):
            try:
                with open(fileName, 'r') as fhandle:
                    jsonData = fhandle.read()
            except Exception as e:
                print("Unable to import setup manager definition:", e)
                self.__teDescription.setPlainText('')
                return True

            data = json.loads(jsonData)

            isValid, message = WSetupManager.isValidPkTkSMContent(data, self.__storedDataFormatIdentifier)
            if isValid:
                self.__teDescription.setHtml(data[WSetupManager.FILE_KEY_PKTKSM][WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION])
            else:
                self.__teDescription.setPlainText('')

        return True

    def information(self):
        """Return description"""
        # use a dict, maybe later some other information could be provided and then it will be easier to manage
        saveMode = 'all'
        if self.__rbSaveModeSelection.isChecked():
            saveMode = 'selection'
        return {WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION: self.__teDescription.toHtml(),
                'saveMode': saveMode}


class WSetupManagerOpenSettings(WDialogFile.WSubWidget):
    """Settings used in open dialog box"""

    def __init__(self, storedDataFormatIdentifier, parent=None):
        super(WSetupManagerOpenSettings, self).__init__(parent)

        if not isinstance(storedDataFormatIdentifier, str):
            raise EInvalidType("Given `storedDataFormatIdentifier` must be a string")

        self.__storedDataFormatIdentifier = ''

        self.__teDescription = QTextEdit(self)
        self.__teDescription.setReadOnly(True)

        self.__lblNfoOpenMode = QLabel(i18n("Open mode:"), self)
        self.__rbOpenModeReplace = QRadioButton(i18n("Replace current"), self)
        self.__rbOpenModeReplace.setChecked(True)
        self.__rbOpenModeMerge = QRadioButton(i18n("Merge current"), self)
        self.__btnGroup = QButtonGroup(self)
        self.__btnGroup.addButton(self.__rbOpenModeReplace)
        self.__btnGroup.addButton(self.__rbOpenModeMerge)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.__teDescription)
        layout.addWidget(self.__lblNfoOpenMode)
        layout.addWidget(self.__rbOpenModeReplace)
        layout.addWidget(self.__rbOpenModeMerge)
        self.setLayout(layout)
        self.setMinimumHeight(230)

    def setFile(self, fileName):
        """When fileName is provided, update description content"""
        if os.path.isfile(fileName):
            try:
                with open(fileName, 'r') as fhandle:
                    jsonData = fhandle.read()
            except Exception as e:
                print("Unable to import setup manager definition:", e)
                self.__teDescription.setPlainText('')
                return False

            data = json.loads(jsonData)

            isValid, message = WSetupManager.isValidPkTkSMContent(data, self.__storedDataFormatIdentifier)
            if isValid:
                self.__teDescription.setHtml(data[WSetupManager.FILE_KEY_PKTKSM][WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION])
            else:
                self.__teDescription.setPlainText(i18n("File is not a valid file!"))
                return False

        return True

    def information(self):
        """Return description"""
        # use a dict, maybe later some other information could be provided and then it will be easier to manage
        openMode = 'replace'
        if self.__rbOpenModeMerge.isChecked():
            openMode = 'merge'

        return {WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION: self.__teDescription.toHtml(),
                'openMode': openMode}


class WSetupManager(QWidget):
    """A widget to browse configuration setups"""

    __INTERNAL_FORMAT_VERSION = '1.00'

    FILE_KEY_PKTKSM = 'pktk-sm'
    FILE_KEY_PKTKSM_VERSION = 'version'
    FILE_KEY_PKTKSM_DESCRIPTION = 'description'
    FILE_KEY_PKTKSM_DATA = 'data'
    FILE_KEY_STOREDD_FMT = 'storedDataFormat'
    FILE_KEY_STOREDD_FMT_ID = 'identifier'
    FILE_KEY_STOREDD_FMT_VERSION = 'version'

    # selected setup is applied
    setupApplied = Signal(SetupManagerSetup)

    # selected item changed, provide a list of ManagedResource
    selectionChanged = Signal(list)

    # Triggered when filter is applied (value >= 0 provide number of found items)
    # Triggered when filter is removed (value == -1)
    filterChanged = Signal(int)

    # properties editor is opened
    setupPropertiesEditorOpen = Signal(SetupManagerBase)
    # properties editor is closed
    setupPropertiesEditorClose = Signal(SetupManagerBase, bool)

    # something has changed (group, setups, creation/deletion/update/move)
    setupsModified = Signal()

    # new setup intialized
    setupFileNew = Signal()
    # setup file opened
    setupFileOpened = Signal(str)
    # setup file saved
    setupFileSaved = Signal(str)

    @staticmethod
    def isValidPkTkSMContent(data, expectedStoredDataFormatIdentifier=''):
        """Return True if given data are valid, otherwise False"""
        if WSetupManager.FILE_KEY_PKTKSM in data:
            # at least, 'pktk-sm' should be available
            if WSetupManager.FILE_KEY_PKTKSM_DATA in data[WSetupManager.FILE_KEY_PKTKSM]:
                # data are present :-)
                if expectedStoredDataFormatIdentifier != '':
                    isFileFormatValid = False
                    # if provided, check if file format is expected one
                    if WSetupManager.FILE_KEY_STOREDD_FMT in data:
                        if WSetupManager.FILE_KEY_STOREDD_FMT_ID in data[WSetupManager.FILE_KEY_STOREDD_FMT]:
                            if data[WSetupManager.FILE_KEY_STOREDD_FMT][WSetupManager.FILE_KEY_STOREDD_FMT_ID] == expectedStoredDataFormatIdentifier:
                                isFileFormatValid = True
                else:
                    # consider it as valid as none has been provided
                    isFileFormatValid = True

                if isFileFormatValid:
                    return (True, '')

        return (False, f"Not a readable file")

    def __init__(self, parent=None):
        super(WSetupManager, self).__init__(parent)

        uiFileName = os.path.join(os.path.dirname(__file__), '..', 'resources', 'wsetupmanager.ui')

        loadXmlUi(uiFileName, self)

        # model to use to manipulate data
        self.__model = SetupManagerModel()

        # setup file name which contains the current setups file
        self.__setupFileName = ''

        # setup extension filter
        self.__extensionFilter = f"{i18n('Generic PkTk Setup Manager')} (*.pktksm)"

        # current setup data that will be applied to create a new setup
        self.__currentSetupData = None

        # Current widget class used to preview setup
        self.__widgetSetupClass = None

        # properties for data stored in WSetupManager
        # - stored data format identifier
        self.__storedDataFormatIdentifier = ''
        # - stored data format version
        self.__storedDataFormatVersion = ''

        # options for properties editor
        self.__propertiesEditorOptions = {SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT: ['colorPalette'],
                                          SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT: (WTextEdit.DEFAULT_TOOLBAR |
                                                                                                    WTextEditBtBarOption.STYLE_STRIKETHROUGH |
                                                                                                    WTextEditBtBarOption.STYLE_COLOR_BG),
                                          SetupManagerPropertyEditor.OPTION_TITLE: '',
                                          SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET: None,
                                          SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP: None,
                                          SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE: QListView.IconMode,
                                          SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE: 3
                                          }
        # last opened/saved setup file name
        self.__lastFileName = ''
        # last opened/saved setup file description
        self.__lastFileDescription = ''

        self.__hasModificationToSave = False

        # init UI
        self.tvSetups.setModel(self.__model)

        self.tbNewSetups.clicked.connect(self.__newSetupsUI)
        self.tbLoadSetups.clicked.connect(self.__loadSetupsUI)
        self.tbSaveSetups.clicked.connect(self.__saveSetupsUI)
        self.tbNewGroup.clicked.connect(self.__actionNewGroup)
        self.tbNewSetup.clicked.connect(self.__actionNewSetup)
        self.tbEdit.clicked.connect(self.__actionEditGroupSetup)
        self.tbDelete.clicked.connect(self.__actionDeleteGroupSetup)
        self.tbApplySetup.clicked.connect(self.__actionApplySetup)

        self.hsIconSize.valueChanged.connect(self.__iconSizeIndexSliderChanged)
        self.tvSetups.iconSizeIndexChanged.connect(self.__iconSizeIndexChanged)
        self.tvSetups.selectionModel().selectionChanged.connect(self.__selectionChanged)
        self.tvSetups.doubleClicked.connect(self.__actionItem)

        self.lblNfoSetupModified.setVisible(False)

        self.__updateUi()

    def __setSetupFile(self, fileName, description):
        """Define setup file"""
        self.__lastFileName = fileName
        self.__lastFileDescription = description

        if self.__lastFileName == '':
            self.lblNfoSetupFile.setText(i18n('<New setups>'))
            self.lblNfoSetupFile.setToolTip('')
        else:
            self.lblNfoSetupFile.setText(self.__lastFileName)
            self.lblNfoSetupFile.setToolTip(self.__lastFileDescription)

    def __setModified(self, value):
        """Define if there's some modification that need to be saved"""
        self.__hasModificationToSave = value
        self.lblNfoSetupModified.setVisible(self.__hasModificationToSave)

    def __newSetups(self):
        """initialise new setups"""
        self.__setSetupFile('', '')
        self.__model.clear()
        self.__updateUi()
        self.__setModified(False)
        self.setupFileNew.emit()
        return True

    def __loadSetupsFile(self, fileName, settingsNfo):
        """Load a setups file"""
        try:
            with open(fileName, 'r') as fHandle:
                jsonData = fHandle.read()
        except Exception as e:
            print(f"Unable to read file: {fileName}", e)
            return False

        try:
            data = json.loads(jsonData)
        except Exception as e:
            print(f"Unable to parse file: {fileName}", e)
            return False

        isValid, message = WSetupManager.isValidPkTkSMContent(data, self.__storedDataFormatIdentifier)
        if isValid:
            try:
                self.__model.importData(data[WSetupManager.FILE_KEY_PKTKSM][WSetupManager.FILE_KEY_PKTKSM_DATA], settingsNfo['openMode'] == 'merge')
                self.__setSetupFile(fileName, data[WSetupManager.FILE_KEY_PKTKSM][WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION])
                self.__setModified(False)
                self.setupsModified.emit()
                self.setupFileOpened.emit(fileName)
            except Exception as e:
                print(f"Unable to interpret file: {fileName}", e)
                return False

            self.__updateUi()
            return True
        return False

    def __saveSetupsFile(self, fileName, settingsNfo):
        """Save setups to a file"""
        if settingsNfo['saveMode'] == 'all':
            data = self.__model.exportData()
        else:
            data = self.__model.exportData([item.id() for item in self.tvSetups.selectedItems()])

        exportedData = {
                WSetupManager.FILE_KEY_PKTKSM: {
                    WSetupManager.FILE_KEY_PKTKSM_VERSION: WSetupManager.__INTERNAL_FORMAT_VERSION,
                    WSetupManager.FILE_KEY_PKTKSM_DESCRIPTION: settingsNfo['description'],
                    WSetupManager.FILE_KEY_PKTKSM_DATA: data
                },
                WSetupManager.FILE_KEY_STOREDD_FMT: {
                    WSetupManager.FILE_KEY_STOREDD_FMT_ID: self.__storedDataFormatIdentifier,
                    WSetupManager.FILE_KEY_STOREDD_FMT_VERSION: self.__storedDataFormatVersion
                }
            }

        jsonData = json.dumps(exportedData, cls=JsonQObjectEncoder)

        try:
            with open(fileName, 'w') as fHandle:
                fHandle.write(jsonData)
            self.__setSetupFile(fileName, settingsNfo['description'])
            self.__setModified(False)
            self.setupFileSaved.emit(fileName)
            return True
        except Exception as e:
            print("Unable to save file:", fileName, e)
            return False

    def __newSetupsUI(self):
        """Reinit a new setup"""
        if self.__hasModificationToSave:
            if WDialogBooleanInput.display(i18n("Create a new setup configuration"),
                                           f'{i18n("Current setups has been modified and will be erased")}<br><b>{i18n("Do you confirm action?")}</b>',
                                           minSize=QSize(950, 400)):
                return self.__newSetups()
            else:
                return False
        else:
            return self.__newSetups()

    def __loadSetupsUI(self):
        """Load a setups file"""
        wPreview = WSetupManagerOpenSavePreview(self.__storedDataFormatIdentifier)
        wSettings = WSetupManagerOpenSettings(self.__storedDataFormatIdentifier)
        result = WDialogFile.openFile(f'{i18n("Load Setup")}',
                                      directory=self.__lastFileName,
                                      filter=self.__extensionFilter,
                                      options={WDialogFile.OPTION_PREVIEW_WIDTH: 800,
                                               WDialogFile.OPTION_PREVIEW_WIDGET: wPreview,
                                               WDialogFile.OPTION_SETTINGS_WIDGET: wSettings})
        if result:
            return self.__loadSetupsFile(result['file'], result['settingsNfo'])
        return False

    def __saveSetupsUI(self):
        """Save setups to a file"""
        wPreview = WSetupManagerOpenSavePreview(self.__storedDataFormatIdentifier)
        wSettings = WSetupManagerSaveSettings(self.__storedDataFormatIdentifier, self.tvSetups.nbSelectedItems() > 0)
        result = WDialogFile.saveFile(f'{i18n("Save Setup")}',
                                      directory=self.__lastFileName,
                                      filter=self.__extensionFilter,
                                      options={WDialogFile.OPTION_PREVIEW_WIDTH: 800,
                                               WDialogFile.OPTION_PREVIEW_WIDGET: wPreview,
                                               WDialogFile.OPTION_SETTINGS_WIDGET: wSettings})
        if result:
            extensions = re.findall(r"(?:\*(\.[^\s\)]+))+", self.__extensionFilter)
            if Path(result['file']).suffix not in extensions:
                # if more than one extension, consider the first one as the expected one
                result['file'] += extensions[0]

            return self.__saveSetupsFile(result['file'], result['settingsNfo'])
        return False

    def __actionNewGroup(self):
        """Create a new group"""
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP] = None
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET] = self.__widgetSetup()
        newGroup = SetupManagerGroup()

        self.setupPropertiesEditorOpen.emit(newGroup)
        returned = SetupManagerPropertyEditor.edit(newGroup, self.__propertiesEditorOptions)

        if returned is not None:
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT] = returned[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT]
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE] = \
                returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE]
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE] = \
                returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE]

            newGroup.setName(returned[SetupManagerPropertyEditor.PROPERTY_NAME])
            newGroup.setComments(returned[SetupManagerPropertyEditor.PROPERTY_COMMENTS])

            self.__model.add(newGroup, self.__getCurrentGroupNode())

            index = self.__model.getFromId(newGroup.id())
            self.tvSetups.setExpanded(index, newGroup.expanded())
            self.__updateUi()
            self.__setModified(True)
            self.setupsModified.emit()
            self.setupPropertiesEditorClose.emit(newGroup, True)
        else:
            self.setupPropertiesEditorClose.emit(newGroup, False)

    def __actionNewSetup(self):
        """Create a new setup"""
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP] = None
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET] = self.__widgetSetup()
        newSetup = SetupManagerSetup()
        newSetup.setData(self.__currentSetupData)

        self.setupPropertiesEditorOpen.emit(newSetup)
        returned = SetupManagerPropertyEditor.edit(newSetup, self.__propertiesEditorOptions)

        if returned is not None:
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT] = returned[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT]
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE] = \
                returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE]
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE] = \
                returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE]

            newSetup.setName(returned[SetupManagerPropertyEditor.PROPERTY_NAME])
            newSetup.setComments(returned[SetupManagerPropertyEditor.PROPERTY_COMMENTS])
            newSetup.setIconUri(returned[SetupManagerPropertyEditor.PROPERTY_ICON])

            self.__model.add(newSetup, self.__getCurrentGroupNode())
            self.__updateUi()
            self.__setModified(True)
            self.setupsModified.emit()
            self.setupPropertiesEditorClose.emit(newSetup, True)
        else:
            self.setupPropertiesEditorClose.emit(newSetup, False)

    def __actionEditGroupSetup(self):
        """Edit selected group/setup"""
        if self.tvSetups.nbSelectedItems() != 1:
            return

        item = self.tvSetups.selectedItems()[0]
        if item:
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP] = self.__currentSetupData
            self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET] = self.__widgetSetup()

            self.setupPropertiesEditorOpen.emit(item)
            returned = SetupManagerPropertyEditor.edit(item, self.__propertiesEditorOptions)

            if returned is not None:
                self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT] = returned[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT]
                self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE] = \
                    returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE]
                self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE] = \
                    returned[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE]

                item.setName(returned[SetupManagerPropertyEditor.PROPERTY_NAME])
                item.setComments(returned[SetupManagerPropertyEditor.PROPERTY_COMMENTS])

                if isinstance(item, SetupManagerSetup):
                    item.setIconUri(returned[SetupManagerPropertyEditor.PROPERTY_ICON])

                self.__model.updateItem(item)
                self.__updateUi()
                self.__setModified(True)
                self.setupsModified.emit()
                self.setupPropertiesEditorClose.emit(item, True)
            else:
                self.setupPropertiesEditorClose.emit(item, False)

    def __actionDeleteGroupSetup(self):
        """Delete selected group/setup"""
        def groupNfo(group):
            returned = group.name()

            stats = group.node().childStats()
            includingGroups = ''
            groups = ''
            if stats['total-groups'] > 0:
                includingGroups = i18n(' (Including groups sub-items)')
                groups = f"<li>{i18n('Groups:')} {stats['total-groups']}</li>"

            if stats['total-setups'] > 0:
                returned += f"<hr><small><b><i>&gt; {i18n('Deletion of group will also delete')}{includingGroups}<ul>" \
                            f"<li>{i18n('Setups:')} {stats['setups']}</li>{groups}</ul></i></b></small>"

            return returned

        items = self.tvSetups.selectedItems()
        if len(items):
            # a setup is selected
            setups = [item for item in items if isinstance(item, SetupManagerSetup)]
            groups = [item for item in items if isinstance(item, SetupManagerGroup)]

            nbSetups = len(setups)
            nbGroups = len(groups)

            title = []
            txtSetups = []
            txtGroups = []

            if nbSetups > 0:
                if nbSetups == 1:
                    txtSetups.append(f'<h2>{i18n("Following setup will removed")}</h2>')
                    title.append(i18n("Remove setup"))
                elif nbSetups > 1:
                    txtSetups.append(f'<h2>{i18n("Following setups will removed")} ({nbSetups})</h2>')
                    title.append(i18n("Remove setups"))

                txtSetups.append("<ul><li>")
                txtSetups.append("<br></li><li>".join([setup.name() for setup in setups]))
                txtSetups.append("<br></li></ul>")

            if nbGroups > 0:
                if nbGroups == 1:
                    txtGroups.append(f'<h2>{i18n("Following group will removed")}</h2>')
                    title.append(i18n("Remove group"))
                elif nbGroups > 1:
                    txtGroups.append(f'<h2>{i18n("Following groups will removed")} ({nbGroups})</h2>')
                    title.append(i18n("Remove groups"))

                txtGroups.append("<ul><li>")
                txtGroups.append("<br></li><li>".join([groupNfo(group) for group in groups]))
                txtGroups.append("<br></li></ul>")

            if WDialogBooleanInput.display("/".join(title),
                                           "".join(txtSetups + txtGroups + [f'<br><b>{i18n("Do you confirm action?")}</b>']),
                                           minSize=QSize(950, 400)):
                self.__model.remove(setups)
                self.__model.remove(groups)
                self.__updateUi()
                self.__setModified(True)
                self.setupsModified.emit()

    def __actionApplySetup(self):
        """Apply selected setup"""
        if self.tvSetups.nbSelectedItems() == 1:
            item = self.tvSetups.selectedItems()[0]
            if isinstance(item, SetupManagerSetup):
                self.setupApplied.emit(item)
                self.__updateUi()

    def __actionItem(self, index):
        """Double click on item
        - setup: edit setup
        - group: expand/collapse
        """
        item = self.__model.data(index, SetupManagerModel.ROLE_DATA)
        if item:
            if isinstance(item, SetupManagerSetup) or index.column() != SetupManagerModel.COLNUM_SETUP:
                self.__actionEditGroupSetup()

    def __getCurrentGroupNode(self):
        """Return current group node

        If current selected item is a setup, return setup node's parent
        """
        for item in self.tvSetups.selectedItems():
            if isinstance(item, SetupManagerGroup):
                return item.node()
            elif isinstance(item, SetupManagerSetup):
                return item.node().parentNode()

        return self.__model.rootNode()

    def __updateUi(self):
        """Update user interface according to current status"""
        self.lblNbSetups.setText(f"{self.__model.rootNode().childStats()['total-setups']}")

        if self.__model.rowCount() > 0:
            self.tbSaveSetups.setEnabled(True)
        else:
            self.tbSaveSetups.setEnabled(False)

        if self.tvSetups.nbSelectedItems() == 1:
            if isinstance(self.tvSetups.selectedItems()[0], SetupManagerSetup):
                self.tbApplySetup.setEnabled(True)
            else:
                self.tbApplySetup.setEnabled(False)

            self.tbEdit.setEnabled(True)
        else:
            self.tbEdit.setEnabled(False)
            self.tbApplySetup.setEnabled(False)

        if self.tvSetups.nbSelectedItems() > 0:
            self.tbDelete.setEnabled(True)
        else:
            self.tbDelete.setEnabled(False)

    def __iconSizeIndexSliderChanged(self, newSize):
        """Icon size has been changed from slider"""
        self.tvSetups.setIconSizeIndex(newSize)

    def __iconSizeIndexChanged(self, newSize, newQSize):
        """Icon size has been changed from listview"""
        self.hsIconSize.setValue(newSize)

    def __selectionChanged(self, selected=None, deselected=None):
        """Selected item has changed"""
        self.__updateUi()
        self.selectionChanged.emit(self.tvSetups.selectedItems())

    def __widgetSetup(self):
        """Return an instancied widget setup class"""
        widget = self.__widgetSetupClass()
        layout = widget.layout()
        if layout:
            layout.setContentsMargins(0, 4, 0, 0)

        return widget

    def selectionMode(self):
        """Return current selection mode"""
        return self.tvSetups.selectionMode()

    def setSelectionMode(self, value):
        """Set current selection mode"""
        self.tvSetups.setSelectionMode(value)

    def iconSizeIndex(self):
        """Return current view mode"""
        return self.tvSetups.iconSizeIndex()

    def setIconSizeIndex(self, value):
        """Set current selection mode"""
        self.tvSetups.setIconSizeIndex(value)

    def columnSetupWidth(self):
        """Return column Setup width"""
        return self.tvSetups.columnWidth(SetupManagerModel.COLNUM_SETUP)

    def setColumnSetupWidth(self, value):
        """Set column Setup width"""
        self.tvSetups.setColumnWidth(SetupManagerModel.COLNUM_SETUP, value)

    def currentSetupData(self):
        """Return current setup data that will be applied to create a new setup"""
        return self.__currentSetupData

    def setCurrentSetupData(self, data):
        """Set current setup data that will be applied to create a new setup

        Can be of any type, widget doesn't interpret data
        """
        self.__currentSetupData = data

    def extensionFilter(self):
        """Return current extension filter"""
        return self.__extensionFilter

    def setExtensionFilter(self, extensionFilter):
        """Set current extension filter"""
        if not isinstance(extensionFilter, str):
            raise EInvalidType("Given `extensionFilter` must be a <str>")
        self.__extensionFilter = extensionFilter

    def storedDataFormat(self):
        """Return a tuple (dataFormatId, dataFormatVersion) for stored data"""
        return (self.__storedDataFormatIdentifier, self.__storedDataFormatVersion)

    def setStoredDataFormat(self, formatId, formatVersion):
        """Define stored data format Id and version"""
        self.__storedDataFormatIdentifier = formatId
        self.__storedDataFormatVersion = formatVersion

    def propertiesEditorSetupPreviewWidgetClass(self):
        """Return widget class used to preview setup data"""
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET]

    def setPropertiesEditorSetupPreviewWidgetClass(self, widgetClass):
        """Set widget Class used to preview setup data

        Widget MUST provide a method setData() that understand saved data format
        """
        if not (isinstance(widgetClass, type) and issubclass(widgetClass, QWidget)):
            raise EInvalidType("Given `widgetClass' must be a <QWidget> sub-class")
        elif not (hasattr(widgetClass, 'setData') and callable(widgetClass.setData)):
            raise EInvalidValue("Given `widget' must have a method 'setData()'")

        self.__widgetSetupClass = widgetClass

    def propertiesEditorTitle(self):
        """Return title for properties editor"""
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_TITLE]

    def setPropertiesEditorTitle(self, title):
        """Set title for properties editor"""
        if not isinstance(title, str):
            raise EInvalidType("Given `title' must be a <str>")

        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_TITLE] = title

    def propertiesEditorColorPickerLayout(self):
        """Return color picker layout applied for properties editor

        List of <str> --> check WColorPicker.setOptionLayout()
        """
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT]

    def setPropertiesEditorColorPickerLayout(self, layout):
        """Set color picker layout applied for properties editor

        List of <str> --> check WColorPicker.setOptionLayout()
        """
        if not isinstance(layout, list):
            raise EInvalidType("Given `layout` must be <list> of <str> (check WColorPicker.setOptionLayout())")
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT] = layout

    def propertiesEditorToolBarLayout(self):
        """Return toolbar layout applied for properties editor

        Combination of option from WTextEditBtBarOption
        """
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT]

    def setPropertiesEditorToolBarLayout(self, layout):
        """Set toolbar layout applied for properties editor

        Combination of option from WTextEditBtBarOption
        """
        if not isinstance(layout, int):
            raise EInvalidType("Given `layout` must be <int> (combination of options from <WTextEditBtBarOption>)")
        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT] = layout

    def propertiesEditorIconSelectorIconSizeIndex(self):
        """Return current icon size index for properties editor icon selector dialog box"""
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_TITLE]

    def setPropertiesEditorIconSelectorIconSizeIndex(self, title):
        """Set current icon size index for properties editor icon selector dialog box"""
        if not isinstance(title, str):
            raise EInvalidType("Given `title' must be a <str>")

        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_TITLE] = title

    def propertiesEditorIconSelectorIconSizeIndex(self):
        """Return current icon size index for properties editor icon selector dialog box"""
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE]

    def setPropertiesEditorIconSelectorIconSizeIndex(self, indexSize):
        """Set current icon size index for properties editor icon selector dialog box"""
        if not isinstance(indexSize, int):
            raise EInvalidType("Given `indexSize' must be an <int>")

        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE] = indexSize

    def propertiesEditorIconSelectorViewMode(self):
        """Return current view mode for properties editor icon selector dialog box"""
        return self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE]

    def setPropertiesEditorIconSelectorViewMode(self, viewMode):
        """Set current view mode for properties editor icon selector dialog box"""
        if viewMode not in (QListView.IconMode, QListView.ListMode):
            raise EInvalidValue("Given `viewMode' must be QListView.IconMode or QListView.ListMode")

        self.__propertiesEditorOptions[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE] = viewMode

    def lastFileName(self):
        """Return file name of last opened/saved setup file"""
        return self.__lastFileName

    def lastFileDescription(self):
        """Return file deszcription of last opened/saved setup file"""
        return self.__lastFileDescription

    def newSetups(self, force=False):
        """Initialise a new setup

        If `force` is True, don't ask confirmation to user to confirm action
        """
        if force:
            return self.__newSetups()
        else:
            return self.__newSetupsUI()

    def openSetup(self, fileName=None, merge=False):
        """open setup file

        If None is provided, display open dialog box
        """
        if fileName is None:
            return self.__loadSetupsUI()
        elif isinstance(fileName, str) and fileName != '':
            settingsNfo = {'openMode': 'replace'}
            if merge:
                settingsNfo['openMode'] = 'merge'
            return self.__loadSetupsFile(fileName, settingsNfo)
        return False

    def saveSetup(self, fileName=None, description=None):
        """Save setup file

        If None is provided, display open dialog box
        """
        if fileName is None:
            return self.__saveSetupsUI()
        else:
            settingsNfo = {'description': self.__lastFileDescription,
                           'saveMode': 'all'
                           }
            if isinstance(description, str):
                settingsNfo['description'] = description

            return self.__saveSetupsFile(fileName, settingsNfo)

    def saveSetupAs(self):
        """Save setup file as

        Always display open dialog box
        """
        return self.saveSetup(None, None)

    def hasModificationToSave(self):
        """Return if current setups has been modified without being saved"""
        return self.__hasModificationToSave


class SetupManagerPropertyEditor(WEDialog):
    """A simple dialog box to edit group/setup properties"""

    PROPERTY_NAME = 'name'
    PROPERTY_COMMENTS = 'comments'
    PROPERTY_ICON = 'icon'

    OPTION_COMMENT_COLORPICKERLAYOUT = 'commentColorPickerLayout'
    OPTION_COMMENT_TOOLBARLAYOUT = 'commentToolbarLayout'
    OPTION_ICON_DLGBOX_SELECTION_VIEWMODE = 'iconDlgBoxSelectionViewMode'
    OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE = 'iconDlgBoxSelectionIndexSize'

    OPTION_TITLE = 'dialogTitle'

    OPTION_SETUP_PREVIEW_WIDGET = 'setupPreviewWidget'
    OPTION_SETUP_ACTIVE_SETUP = 'setupActiveSetup'

    @staticmethod
    def edit(item, options={}):
        """Open a dialog box to edit group"""
        widget = QWidget()
        dlgBox = SetupManagerPropertyEditor(item, options, widget)

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            return dlgBox.properties()
        else:
            return None

    def __init__(self, item, options, parent=None):
        super(SetupManagerPropertyEditor, self).__init__(os.path.join(os.path.dirname(__file__), '..', 'resources', 'wsetupmanager_propertieseditor.ui'), parent)

        if not isinstance(options, dict):
            options = {}

        title = ''
        if SetupManagerPropertyEditor.OPTION_TITLE in options and isinstance(options[SetupManagerPropertyEditor.OPTION_TITLE], str):
            title = options[SetupManagerPropertyEditor.OPTION_TITLE]

        self.__iconDlgBoxSelectionViewMode = QListView.IconMode
        self.__iconDlgBoxSelectionIndexSize = 1

        if SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE in options and \
           options[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE] == QListView.ListMode:
            self.__iconDlgBoxSelectionViewMode = QListView.ListMode

        if SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE in options and \
           isinstance(options[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE], int):
            self.__iconDlgBoxSelectionIndexSize = options[SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE]

        self.__item = item
        self.__uriIcon = None

        # tab properties active by default
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget.setTabBarAutoHide(True)

        if isinstance(self.__item, SetupManagerSetup) and isinstance(self.__item.data(), dict):
            if SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET in options and isinstance(options[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET], QWidget):
                options[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET].setData(self.__item.data())
                self.tabWidget.addTab(options[SetupManagerPropertyEditor.OPTION_SETUP_PREVIEW_WIDGET], i18n('Setup preview'))

            hideRefreshSetup = True
            if SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP in options:
                if options[SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP] is not None:
                    # need to compare both setup, if are the same or not
                    # - convert both to json
                    # - compare
                    jsonStrActiveSetup = json.dumps(options[SetupManagerPropertyEditor.OPTION_SETUP_ACTIVE_SETUP], cls=JsonQObjectEncoder)
                    jsonStrSetup = json.dumps(self.__item.data(), cls=JsonQObjectEncoder)
                    hideRefreshSetup = (jsonStrActiveSetup == jsonStrSetup)

            if hideRefreshSetup:
                self.lblRefreshSetup1.hide()
                self.lblRefreshSetup2.hide()
                self.tbRefreshSetup.hide()
            else:
                self.tbRefreshSetup.clicked.connect(self.__updateSetup)

            self.__buildIconPopupMenu()
            self.lblTitle.setText(i18n('Setup'))
            if title is None or title == '':
                title = i18n('Setups Manager - Edit Setup')

            self.tbIcon.setIcon(self.__item.icon())
        else:
            self.lblIcon.hide()
            self.tbIcon.hide()
            self.lblRefreshSetup1.hide()
            self.lblRefreshSetup2.hide()
            self.tbRefreshSetup.hide()
            self.lblTitle.setText(i18n('Group'))
            if title is None or title == '':
                title = i18n('Setups Manager - Edit Group')

        replaceLineEditClearButton(self.leName)
        self.leName.setText(self.__item.name())
        self.leName.textChanged.connect(self.__setOkEnabled)

        self.wtComments.setHtml(self.__item.comments())

        if SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT in options and isinstance(options[SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT], int):
            self.wtComments.setToolbarButtons(options[SetupManagerPropertyEditor.OPTION_COMMENT_TOOLBARLAYOUT])
        else:
            self.wtComments.setToolbarButtons(WTextEdit.DEFAULT_TOOLBAR | WTextEditBtBarOption.STYLE_STRIKETHROUGH | WTextEditBtBarOption.STYLE_COLOR_BG)

        if SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT in options and isinstance(options[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT], list):
            self.wtComments.setColorPickerLayout(options[SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT])

        self.pbOk.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.__setOkEnabled()
        self.setModal(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

    def __buildIconPopupMenu(self):
        """Build popup menu for icon button"""
        self.__actionFromInternalResource = QAction(i18n('Set icon from internal resource'), self)
        self.__actionFromInternalResource.triggered.connect(self.__setIconFromInternalResource)

        self.__actionFromFile = QAction(i18n('Set icon from a file'), self)
        self.__actionFromFile.triggered.connect(self.__setIconFromFile)

        self.__menu = QMenu(self)
        self.__menu.addAction(self.__actionFromFile)
        self.__menu.addAction(self.__actionFromInternalResource)

        self.tbIcon.setMenu(self.__menu)

    def __setIconFromInternalResource(self, icon=None):
        """Open dialog box to choose an icon from internal resources"""
        if isinstance(icon, bool):
            # if trigerred by button signal...
            icon = None

        if not isinstance(icon, QUriIcon):
            options = WIconSelector.OPTIONS_SHOW_STATUSBAR | WIconSelector.OPTIONS_DEFAULT_ICON_SIZE | self.__iconDlgBoxSelectionIndexSize
            if self.__iconDlgBoxSelectionViewMode == QListView.IconMode:
                options |= WIconSelector.OPTIONS_DEFAULT_MODE_VIEW_ICON
            else:
                options |= WIconSelector.OPTIONS_DEFAULT_MODE_VIEW_LIST

            result = WIconSelectorDialog.show(options)
            if isinstance(result, dict):
                icon = result['uri']

                self.__iconDlgBoxSelectionViewMode = result['optionViewMode']
                self.__iconDlgBoxSelectionIndexSize = result['optionIconSizeIndex']

        if icon is not None:
            self.tbIcon.setIcon(icon.icon())
            self.__uriIcon = icon

    def __setIconFromFile(self):
        """Open dialog box to choose an icon from a file"""
        result = WDialogFile.openFile(f'{self.windowTitle()} - {i18n("Load icon")}',
                                      filter=i18n("Images (*.png *.jpg *.jpeg *.svg)"),
                                      options={WDialogFile.OPTION_PREVIEW_WIDGET: 'image'})
        if result:
            self.tbIcon.setIcon(QIcon(result['file']))
            self.__uriIcon = QUriIcon(result['file'], maxSize=QSize(192, 192))

    def __setOkEnabled(self):
        """Enable/Disable OK button according to UI state"""
        enabled = False
        if self.leName.text() != '':
            enabled = True

        self.pbOk.setEnabled(enabled)

    def __updateSetup(self):
        """Update setup with current active one"""
        self.setUpdatesEnabled(False)
        self.lblRefreshSetup1.hide()
        self.lblRefreshSetup2.hide()
        self.tbRefreshSetup.hide()
        self.setUpdatesEnabled(True)

    def properties(self):
        """Return options from setup editor"""
        returned = {
                    SetupManagerPropertyEditor.PROPERTY_NAME: self.leName.text(),
                    SetupManagerPropertyEditor.PROPERTY_COMMENTS: self.wtComments.toHtml(),
                    SetupManagerPropertyEditor.PROPERTY_ICON: self.__uriIcon,
                    SetupManagerPropertyEditor.OPTION_COMMENT_COLORPICKERLAYOUT: self.wtComments.colorPickerLayout(),
                    SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_VIEWMODE: self.__iconDlgBoxSelectionViewMode,
                    SetupManagerPropertyEditor.OPTION_ICON_DLGBOX_SELECTION_INDEXSIZE: self.__iconDlgBoxSelectionIndexSize
                    }

        return returned
