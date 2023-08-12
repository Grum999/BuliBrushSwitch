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
# The resutils module provides class to manage Krita's resources
#
# Note: access to Krita's SQLite resourcescache.sqlite file is realised in
#       READ ONLY mode
#       the module doesn't provides any method to update/modify Krita's database
#       content
#
# Main class from this module
#
# - ManagedResourceTypes:
#       Enumerate resources currently managed
#
# - ManagedResource:
#       A managed resource
#       Provides miscellaneous additional properties for krita's resource
#
# - DBManagedResources:
#       Krita's API doesn't return tags for resources
#       This class retrieve resources directly from database
#
# - ManagedResourcesModel
#       A model for resources; use DBManagedResources to return data
#
#
# -----------------------------------------------------------------------------

from enum import Enum
import os.path
import sys

from krita import Resource

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtSql import (QSqlDatabase, QSqlQuery)

from .imgutils import checkerBoardImage
from .iconsizes import IconSizes
from ..pktk import *


class ManagedResourceTypes(Enum):
    """Define identifier of available resources queries"""
    RES_GRADIENTS = "gradient"
    RES_PRESETS = "preset"
    RES_PALETTES = "palette"
    RES_PATTERNS = "pattern"

    def label(self,  **param):
        match self:
            case ManagedResourceTypes.RES_GRADIENTS:
                return i18n('Gradients')
            case ManagedResourceTypes.RES_PRESETS:
                return i18n('Presets')
            case ManagedResourceTypes.RES_PALETTES:
                return i18n('Palettes')
            case ManagedResourceTypes.RES_PATTERNS:
                return i18n('Patterns')
        return self.value


class ManagedResource(object):
    """A managed resource item"""

    def __init__(self, value=None):
        """Given `value` can be a resource or a dict"""
        # internal Krita's resource Id
        self.__id = None

        # resource name
        self.__name = ''

        # resource file name
        self.__fileName = ''

        # resource tooltip
        self.__tooltip = ''

        # normalized resource thumbnail (384x384 pixel square)
        self.__thumbnail = None

        # resource native PNG data size
        self.__originalImgSize = QSize()

        # tags are defined by a list of tuples (tagId, tagName)
        self.__tags = []

        # tagsId a list of tagId
        self.__tagsId = []

        # Krita Resource
        self.__resource = None

        # resource type
        self.__type = None

        # resource storage location
        self.__location = ''

        # resource storage type
        self.__storageTypeId = 0

        # resource storage active
        self.__active = False

        if isinstance(value, ManagedResource):
            self.__id = value.id()
            self.__name = value.name()
            self.__fileName = value.fileName()
            self.__tooltip = value.tooltip()
            self.__thumbnail = value.thumbnail()
            self.__originalImgSize = value.originalImgSize()
            self.__tags = value.tags()
            self.__tagsId = value.tagsId()
            self.__resource = value.resource()
            self.__type = value.type()
            self.__storageLocation = value.storageLocation()
            self.__storageTypeId = value.storageTypeId()
            self.__storageActive = value.storageActive()
        elif isinstance(value, dict):
            if 'id' in value and isinstance(value['id'], int) and value['id'] >= 0:
                self.__id = value['id']
            else:
                raise EInvalidType("Given `id` must be provided as a positive <int>")

            if 'fileName' in value and isinstance(value['fileName'], str) and value['fileName'] != '':
                self.__fileName = value['fileName']
            else:
                raise EInvalidType("Given `fileName` must be provided as a non empty <str>")

            if 'name' in value and isinstance(value['name'], str) and value['name'] != '':
                self.__name = value['name']
            else:
                raise EInvalidType("Given `name` must be provided as a non empty <str>")

            if 'tooltip' in value and isinstance(value['tooltip'], str):
                self.__tooltip = value['tooltip']
            else:
                self.__tooltip = self.__name

            if 'thumbnail' in value and (isinstance(value['thumbnail'], QPixmap) or value['thumbnail'] is None):
                self.__thumbnail = value['thumbnail']
            else:
                raise EInvalidType("Given `thumbnail` must be provided as a <QPixmap>")

            if 'originalImgSize' in value and isinstance(value['originalImgSize'], QSize):
                self.__originalImgSize = value['originalImgSize']
            else:
                raise EInvalidType("Given `originalImgSize` must be provided as a <QSize>")

            if 'tags' in value and isinstance(value['tags'], list):
                self.__tags = value['tags']
                self.__tagsId = []
                for tag in self.__tags:
                    if isinstance(tag, tuple) and len(tag) == 2 and isinstance(tag[0], int) and isinstance(tag[1], str):
                        self.__tagsId.append(tag[0])
                    else:
                        raise EInvalidType("Given `tags` must be provided as a <list> of <tuple(int, str)>")
            else:
                raise EInvalidType("Given `tags` must be provided as a <list> of <tuple(int, str)>")

            if 'type' in value and isinstance(value['type'], ManagedResourceTypes):
                self.__type = value['type']
            else:
                raise EInvalidType("Given `type` must be provided as a <ManagedResourceTypes>")

            if 'resource' in value and isinstance(value['resource'], Resource):
                self.__resource = value['resource']
            else:
                raise EInvalidType("Given `resource` must be provided as a <Resource>")

            if 'storageLocation' in value and isinstance(value['storageLocation'], str):
                self.__storageLocation = value['storageLocation']
            else:
                raise EInvalidType("Given `storageLocation` must be provided as a <str>")

            if 'storageTypeId' in value and isinstance(value['storageTypeId'], int):
                self.__storageTypeId = value['storageTypeId']
            else:
                raise EInvalidType("Given `storageTypeId` must be provided as a <int>")

            if 'storageActive' in value and isinstance(value['storageActive'], bool):
                self.__storageActive = value['storageActive']
            else:
                raise EInvalidType("Given `storageActive` must be provided as a <bool>")

    def __repr__(self):
        if self.__type is None:
            return f"<ManagedResource({self.__id}, '{self.__name}', '{self.__fileName}', 'None')>"
        else:
            return f"<ManagedResource({self.__id}, '{self.__name}', '{self.__fileName}', '{self.__type.value}')>"

    def __eq__(self, other):
        return other is not None and self.__type == other.__type and self.__id == other.__id

    def id(self):
        """return internal Krita's resource Id"""
        return self.__id

    def name(self):
        """return resource name"""
        return self.__name

    def fileName(self):
        """return resource file name"""
        return self.__fileName

    def tooltip(self):
        """return resource tooltip"""
        return self.__tooltip

    def thumbnail(self):
        """return resource thumbnail as a QPixmap
        (or None if is empty resource)
        """
        return self.__thumbnail

    def originalImgSize(self):
        """return native PNG data size"""
        return self.__originalImgSize

    def tags(self):
        """return tags list as a list of tuples (tagId, tagName)"""
        return self.__tags

    def tagsId(self):
        """return tags list as a list of tagId"""
        return self.__tagsId

    def resource(self):
        """return Krita Resource"""
        return self.__resource

    def type(self):
        """return resource type"""
        return self.__type

    def storageLocation(self):
        """return resource storage location"""
        return self.__storageLocation

    def storageTypeId(self):
        """return resource storage type id"""
        return self.__storageTypeId

    def storageActive(self):
        """return resource storage active or not"""
        return self.__storageActive


class DBManagedResources(QObject):
    """A class dedicated to access to resources directly through SQlite database

    The current class does READ ACCESS ONLY on database
    There's no risk to interfere and/or corrupt resource database

    According to SQLite documentation:
        Can multiple applications or multiple instances of the same application access a single database file at the same time?
        (https://www.sqlite.org/faq.html#q5)read access to database is Ok


    Linux/OSX: it should be totally OK
    Windows:   it seems more delicate in the case of database is hosted on a NFS file system, but it's probably not a
               big problem as there's few risk to get krita's resourcescache.sqlite file hosted on a NFS drive :-)
    """
    __DBINSTANCEID = "PKTK_DBManagedResources"

    def __init__(self, fileName, parent=None):
        super(DBManagedResources, self).__init__(parent)

        self.__dbInstanceId = f"{DBManagedResources.__DBINSTANCEID}_{QUuid.createUuid().toString()}"
        self.__dbFileName = ""
        self.__databaseInstance = None
        self.__includeStorageInactive = False
        self.__includeDuplicateResources = False
        self.setDatabaseFile(fileName)

    def __del__(self):
        """Ensure to close database before instance being destroyed"""
        self.close()

    def __initializeQueries(self):
        """Initialise default queries"""
        if self.__databaseInstance is None:
            return

        # The query is "large"
        # - return duplicates resources if self.__includeDuplicateResources is True
        # - return from deactived storages if self.__includeStorageInactive is True
        # Resources are filtered in second time, if needed
        modelQuery = """
            WITH filteredResources AS (
                -- select resources according to option __includeDuplicateResources and __includeStorageInactive
                SELECT {},
                       r.name,
                       r.filename as "fileName",
                       r.tooltip,
                       rtrim(replace(group_concat(DISTINCT cast(t.id as text) || '\v' || t.name || '\t'), '\t,', '\t'), '\t') as "tagsId"
                FROM resources r
                    -- need to reduce resources from ACTIVE storages only
                    JOIN storages s
                      ON s.id = r.storage_id
                     {}
                    -- reduce resources list to expected resource type
                    JOIN resource_types rty
                      ON r.resource_type_id = rty.id
                     AND rty.name = '{}'
                    -- get tags
                    LEFT OUTER JOIN resource_tags rta
                      ON rta.active = 1
                     AND rta.resource_id = r.id
                    LEFT JOIN tags t
                      ON t.resource_type_id = r.resource_type_id
                     AND t.id = rta.tag_id
                     AND t.active = 1
                GROUP BY r.md5sum,
                         {}
                         r.name,
                         r.fileName,
                         r.tooltip
                ORDER BY r.name,
                         r.id
            )
            -- return resources properties, using filtered resource view
            SELECT fr.id,
                   fr.name,
                   fr.fileName,
                   fr.tooltip,
                   fr.tagsId,
                   s.location AS "storageLocation",
                   s.storage_type_id AS "storageTypeId",
                   s.active AS "storageActive"
            FROM filteredResources AS fr
                 JOIN resources r
                   ON r.id = fr.id
                 JOIN storages AS s
                   ON s.id = r.storage_id
            ORDER BY r.name,
                     r.id
            """

        if self.__includeDuplicateResources:
            includeDuplicateResources = 'r.id'
            includeDuplicateResourcesGB = 'r.id,'
        else:
            includeDuplicateResources = 'min(r.id) as "id"'
            includeDuplicateResourcesGB = ''

        if self.__includeStorageInactive:
            includeStorageInactive = ''
        else:
            includeStorageInactive = 'AND s.active = 1'

        self.__dbQueries[ManagedResourceTypes.RES_GRADIENTS] = QSqlQuery(self.__databaseInstance)
        self.__dbQueries[ManagedResourceTypes.RES_GRADIENTS].prepare(modelQuery.format(includeDuplicateResources,
                                                                                       includeStorageInactive,
                                                                                       'gradients',
                                                                                       includeDuplicateResourcesGB))

        self.__dbQueries[ManagedResourceTypes.RES_PRESETS] = QSqlQuery(self.__databaseInstance)
        self.__dbQueries[ManagedResourceTypes.RES_PRESETS].prepare(modelQuery.format(includeDuplicateResources,
                                                                                     includeStorageInactive,
                                                                                     'paintoppresets',
                                                                                     includeDuplicateResourcesGB))

        self.__dbQueries[ManagedResourceTypes.RES_PALETTES] = QSqlQuery(self.__databaseInstance)
        self.__dbQueries[ManagedResourceTypes.RES_PALETTES].prepare(modelQuery.format(includeDuplicateResources,
                                                                                      includeStorageInactive,
                                                                                      'palettes',
                                                                                      includeDuplicateResourcesGB))

        self.__dbQueries[ManagedResourceTypes.RES_PATTERNS] = QSqlQuery(self.__databaseInstance)
        self.__dbQueries[ManagedResourceTypes.RES_PATTERNS].prepare(modelQuery.format(includeDuplicateResources,
                                                                                      includeStorageInactive,
                                                                                      'patterns',
                                                                                      includeDuplicateResourcesGB))

    def databaseFile(self):
        """Return current database file name

        Return empty string if not database is set
        """
        return self.__dbFileName

    def setDatabaseFile(self, fileName):
        """Set database file to use

        If a database file is already open, it will be closed before

        Return True if file is valid and database opened, otherwise return False
        """
        if os.path.isfile(fileName):
            self.close()

            self.__dbFileName = fileName

            self.__databaseInstance = QSqlDatabase.addDatabase("QSQLITE", self.__dbInstanceId)
            self.__databaseInstance.setDatabaseName(self.__dbFileName)

            # Define connection options
            self.__databaseInstance.setConnectOptions("QSQLITE_BUSY_TIMEOUT=25;QSQLITE_OPEN_READONLY=1")

            # reset precompiled queries
            self.__dbQueries = {}

            if self.__databaseInstance.open():
                self.__initializeQueries()
                return True
            else:
                self.close()
        return False

    def close(self):
        """Close database, and free all resources

        Does nothing if database is not open
        """
        if self.__databaseInstance:
            if self.__databaseInstance.isOpen():
                self.__databaseInstance.close()
            self.__databaseInstance = None
            QSqlDatabase.removeDatabase(self.__dbInstanceId)

    def executeQuery(self, queryId, bindValues={}):
        """Execute query by Id

        If query accept binding parameters, just provide `bindValues` parameter as dict

        Return a tuple:
            If execution is OK: (True, QSqlQuery)
            If execution is KO: (False, QSqlQuery)
            If query id is not valid or database is not opened: (None, None)
        """
        if self.__databaseInstance is not None and isinstance(queryId, ManagedResourceTypes):
            # get prepared query
            query = self.__dbQueries[queryId]

            # bind values if any
            for bindKey in bindValues.keys():
                query.bindValue(bindKey, bindValues[bindKey])

            # execute query
            return (query.exec(), query)

        return (None, None)

    def includeStorageInactive(self):
        """Return if resources from inactive storage are returned"""
        return self.__includeStorageInactive

    def setIncludeStorageInactive(self, value):
        """Set if resources from inactive storage are returned"""
        if isinstance(value, bool) and value != self.__includeStorageInactive:
            self.__includeStorageInactive = value
            self.__initializeQueries()
            return value
        return None

    def includeDuplicateResources(self):
        """Return if duplicates resources are returned"""
        return self.__includeDuplicateResources

    def setIncludeDuplicateResources(self, value):
        """Set if duplicates resources are returned

        Are considered duplicates resources, resource for which NAME and FILENAME are the same across different storages

        Currently, Krita doesn't really manage this with a precise rule
        ==> cf. https://bugs.kde.org/show_bug.cgi?id=470017

        Ideally, the rule would be:
        1) prioritize resource from active storage
        2) prioritize resource with lowest Id (the oldest one)

        But the rule that will be applied will try to be the same than Krita, assuming it's to return the resource with
        the lowest Id, whatever the storage is active or not
        ==> In this situation (cf. reported bug) some resource could not be returned; it's not really satisfying but the
            class must try to return a consistent result with what Krita is returning
        """
        if isinstance(value, bool) and value != self.__includeDuplicateResources:
            self.__includeDuplicateResources = value
            self.__initializeQueries()
            return value
        return None


class ManagedResourcesModel(QAbstractTableModel):
    """A model provided for resources"""
    ROLE_ID = Qt.UserRole + 1
    ROLE_NAME = Qt.UserRole + 2
    ROLE_TAGS = Qt.UserRole + 3
    ROLE_TAGSID = Qt.UserRole + 4
    ROLE_MANAGEDRESOURCE = Qt.UserRole + 5

    HEADERS = ['Icon', 'Name']
    COLNUM_ICON = 0
    COLNUM_NAME = 1
    COLNUM_LAST = 1

    ICON_MAX_SIZE = 384

    def __init__(self, parent=None):
        """Initialise list"""
        super(ManagedResourcesModel, self).__init__(parent)
        self.__items = []
        self.__dbResources = DBManagedResources(os.path.join(QStandardPaths.standardLocations(QStandardPaths.DataLocation)[0], 'resourcecache.sqlite'))
        self.__resourceType = None
        self.__displayName = True

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column"""
        return ManagedResourcesModel.COLNUM_LAST+1

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows"""
        return len(self.__items)

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        column = index.column()
        row = index.row()

        if role == Qt.DecorationRole:
            if column == ManagedResourcesModel.COLNUM_ICON and self.__items[row].thumbnail() is not None:
                return QIcon(self.__items[row].thumbnail())
        elif role == Qt.ToolTipRole:
            txtTag = ''
            txtImg = ''
            if len(self.__items[row].tags()) > 0:
                if len(self.__items[row].tags()) == 1:
                    tag = i18n('Tag')
                    tags = self.__items[row].tags()[0][1]
                else:
                    tag = i18n('Tags')
                    tags = "</li><li>".join([tagProperty[1] for tagProperty in self.__items[row].tags()])
                txtTag = f"<hr><b>{tag} ({len(self.__items[row].tags())})</b><ul><li>{tags}</li></ul>"

            if self.__resourceType == ManagedResourceTypes.RES_PATTERNS:
                size = self.__items[row].originalImgSize()
                txtImg = f"<hr><b>{i18n('Pattern size')}</b> {size.width()}x{size.height()}"

            return f"{self.__items[row].tooltip()}{txtImg}{txtTag}"
        elif role == Qt.DisplayRole:
            if self.__displayName:
                return self.__items[row].name()
        elif role == ManagedResourcesModel.ROLE_ID:
            return self.__items[row].id()
        elif role == ManagedResourcesModel.ROLE_TAGS:
            return self.__items[row].tags()
        elif role == ManagedResourcesModel.ROLE_TAGSID:
            return self.__items[row].tagsId()
        elif role == ManagedResourcesModel.ROLE_MANAGEDRESOURCE:
            return self.__items[row]
        elif role == ManagedResourcesModel.ROLE_NAME:
            return self.__items[row].name()
        return None

    def updateResources(self, resourceType=None):
        """Update resources from database"""
        def resourceToQPixmap(resourceImg):
            originalImgSize = None
            pixmap = None
            if not isinstance(resourceImg, QImage):
                return pixmap

            if self.__resourceType == ManagedResourceTypes.RES_GRADIENTS:
                # Gradient resources returns a 2048x1 image size
                # need to:
                #   - return a 384x192 thumbnail
                #   - generate a checked background in case gradient has transparent value
                pixmap = QPixmap(ManagedResourcesModel.ICON_MAX_SIZE << 1, ManagedResourcesModel.ICON_MAX_SIZE)

                imgData = QPixmap.fromImage(resourceImg)
                originalImgSize = imgData.size()
                checkerBoard = checkerBoardImage(pixmap.size())

                painter = QPainter(pixmap)
                painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
                painter.drawPixmap(0, 0, checkerBoard)
                painter.drawPixmap(QRect(0, 0, pixmap.width(), pixmap.height()), imgData)
                painter.end()
            else:
                # for PATTERNS, PRESET, PALETTE
                #   - Always return a square pixmap for which dimension is at least 384x384
                #   - For PATTERNS & PALETTE, if size if less than expected, upscale using nearest neighbor method
                #   - For PRESET, if size if less than expected, upscale using bilinear method
                #   - For PATTERNS, set a checkerboard background
                #   - If thumbnail is not a square, center it
                imgData = QPixmap.fromImage(resourceImg)
                originalImgSize = imgData.size()

                minDim = min(originalImgSize.width(), originalImgSize.height())
                maxDim = max(originalImgSize.width(), originalImgSize.height(), ManagedResourcesModel.ICON_MAX_SIZE)

                pixmap = QPixmap(maxDim, maxDim)

                # ensure pixmap is transparent before starting to paint on it
                pixmap.fill(Qt.transparent)

                if self.__resourceType == ManagedResourceTypes.RES_PRESETS:
                    imgData = imgData.scaled(pixmap.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    checkerBoard = None
                else:
                    # need a checkerboard as background
                    imgData = imgData.scaled(pixmap.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
                    checkerBoard = checkerBoardImage(imgData.size())

                pX = (pixmap.width() - imgData.width())//2
                pY = (pixmap.height() - imgData.height())//2

                painter = QPainter(pixmap)
                if checkerBoard:
                    painter.drawPixmap(pX, pY, checkerBoard)
                painter.drawPixmap(pX, pY, imgData)
                painter.end()

            return (pixmap, originalImgSize)

        if isinstance(resourceType, ManagedResourceTypes):
            self.__resourceType = resourceType
        elif resourceType is not None:
            raise EInvalidType("Given `resourceType` must be None or a <ManagedResourceTypes>")

        if self.__resourceType is None:
            return

        self.beginResetModel()
        # query will return resources with their tags
        query = self.__dbResources.executeQuery(self.__resourceType)
        # get krita resource objects
        kritaResources = Krita.instance().resources(self.__resourceType.value)

        self.__items = []
        if query[0]:
            while query[1].next():
                if query[1].value('name') in kritaResources and kritaResources[query[1].value('name')].filename() == query[1].value('fileName'):
                    # by default, no tags
                    tags = []
                    if query[1].value('tagsId') != '':
                        tagsId =  query[1].value('tagsId').split('\t')
                        for index in range(len(tagsId)):
                            tag = tuple(tagsId[index].split('\v'))
                            tags.append((int(tag[0]), tag[1]))

                        # sort tags by name
                        tags.sort(key=lambda value: value[1])

                    thumbnail, originalImgSize = resourceToQPixmap(kritaResources[query[1].value('name')].image())
                    self.__items.append(ManagedResource({
                            'id': query[1].value('id'),
                            'name': query[1].value('name'),
                            'fileName': query[1].value('fileName'),
                            'tooltip': query[1].value('tooltip'),
                            'thumbnail': thumbnail,
                            'originalImgSize': originalImgSize,
                            'tags': tags,
                            'resource': kritaResources[query[1].value('name')],
                            'type': self.__resourceType,
                            'storageLocation': query[1].value('storageLocation'),
                            'storageTypeId': query[1].value('storageTypeId'),
                            'storageActive': (query[1].value('storageActive') == 1)
                        }))
        else:
            err = query[1].lastError()
            print(err.databaseText())
            print(err.driverText())
            print(err.nativeErrorCode())
        self.endResetModel()

    def displayName(self):
        """Return if name is returned for display"""
        return self.__displayName

    def setDisplayName(self, value):
        """Set if name is returned for display"""
        if isinstance(value, bool):
            self.__displayName = value

    def resourceType(self):
        """return current managed resource type"""
        return self.__resourceType

    def setResourceType(self, value):
        """set current managed resource type
        Alias for updateResources()
        """
        self.updateResources(value)

    def getResource(self, resource, asIndex=False):
        """return ManagedResource for resource, or None is not found

        given `resources` can be:
        - An integer (then, represent an Id)
        - A tuple (name, fileName)
        - A ManagedResource
        - A Krita Resource

        If `asIndex` is True, return QModelIndex() in model instead of ManagedResource
        """
        if resource is None:
            return None

        if not isinstance(resource, (ManagedResource, int, tuple, Resource)):
            raise EInvalidType("Given `resources` is not valid")

        for row in range(self.rowCount()):
            index = self.index(row, 0)
            data = self.data(index, ManagedResourcesModel.ROLE_MANAGEDRESOURCE)

            if isinstance(resource, int) and resource == data.id() or\
               isinstance(resource, ManagedResource) and resource == data or\
               isinstance(resource, Resource) and resource == data.resource() or\
               isinstance(resource, tuple) and resource[0] == data.name() and resource[1] == data.fileName():
                if asIndex:
                    return index
                return data
        return None

    def includeStorageInactive(self):
        """Return if resources from inactive storage are returned"""
        return self.__includeStorageInactive

    def setIncludeStorageInactive(self, value):
        """Set if resources from inactive storage are returned"""
        if self.__dbResources.setIncludeStorageInactive(value) is not None:
            self.updateResources()

    def includeDuplicateResources(self):
        """Return if duplicates resources are returned"""
        return self.__includeDuplicateResources

    def setIncludeDuplicateResources(self, value):
        """Set if duplicates resources are returned

        Are considered duplicates resources, resource for which NAME and FILENAME are the same across different storages

        Currently, Krita doesn't really manage this with a precise rule
        ==> cf. https://bugs.kde.org/show_bug.cgi?id=470017

        Ideally, the rule would be:
        1) prioritize resource from active storage
        2) prioritize resource with lowest Id (the oldest one)

        But the rule that will be applied will try to be the same than Krita, assuming it's to return the resource with
        the lowest Id, whatever the storage is active or not
        ==> In this situation (cf. reported bug) some resource could not be returned; it's not really satisfying but the
            class must try to return a consistent result with what Krita is returning
        """
        if self.__dbResources.setIncludeDuplicateResources(value) is not None:
            self.updateResources()
