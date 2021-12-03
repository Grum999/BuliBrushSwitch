#-----------------------------------------------------------------------------
# BuliBrushSwitch
# Copyright (C) 2021 - Grum999
# -----------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see https://www.gnu.org/licenses/
# -----------------------------------------------------------------------------
# A Krita plugin designed to manage notes
# -----------------------------------------------------------------------------
import re

from bulibrushswitch.pktk import *

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from krita import (
        View,
        ManagedColor
    )

from .bbssettings import (
        BBSSettings,
        BBSSettingsKey,
        BBSSettingsValues
    )

from bulibrushswitch.pktk.modules.uitheme import UITheme
from bulibrushswitch.pktk.modules.iconsizes import IconSizes
from bulibrushswitch.pktk.modules.strutils import stripHtml
from bulibrushswitch.pktk.modules.imgutils import (warningAreaBrush, qImageToPngQByteArray, bullet, buildIcon)
from bulibrushswitch.pktk.modules.ekrita import (EKritaBrushPreset, EKritaShortcuts)
from bulibrushswitch.pktk.widgets.wtextedit import (WTextEdit, WTextEditDialog, WTextEditBtBarOption)
from bulibrushswitch.pktk.widgets.wcolorbutton import WColorButton
from bulibrushswitch.pktk.widgets.wkeysequenceinput import WKeySequenceInput


class BBSBrush(QObject):
    """A brush definition"""
    updated=Signal(QObject, str)

    KEY_NAME='name'
    KEY_SIZE='size'
    KEY_FLOW='flow'
    KEY_OPACITY='opacity'
    KEY_BLENDINGMODE='blendingMode'
    KEY_COMMENTS='comments'
    KEY_IMAGE='image'
    KEY_ERASERMODE='eraserMode'
    KEY_KEEPUSERMODIFICATIONS='keepUserModifications'
    KEY_IGNOREERASERMODE='ignoreEraserMode'
    KEY_POSITION='position'
    KEY_COLOR='color'
    KEY_UUID='uuid'
    KEY_SHORTCUT='shortcut'

    def __init__(self, brush=None):
        super(BBSBrush, self).__init__(None)
        self.__name=''
        self.__size=0
        self.__flow=0
        self.__opacity=0
        self.__blendingMode=''
        self.__comments=''
        self.__image=None
        self.__keepUserModifications=True
        self.__eraserMode=False
        self.__ignoreEraserMode=True
        self.__position=-1
        self.__color=None
        self.__shortcut=QKeySequence()

        self.__uuid=QUuid.createUuid().toString()
        self.__fingerPrint=''
        self.__emitUpdated=0

        self.__brushNfoFullImg=''
        self.__brushNfoFull=''
        self.__brushNfoShort=''

        if isinstance(brush, BBSBrush):
            # clone brush
            self.importData(brush.exportData())

    def __repr__(self):
        return f"<BBSBrush({self.__uuid}, {self.__name})>"

    def __updated(self, property):
        """Emit updated signal when a property has been changed"""
        if self.__emitUpdated==0:
            self.__brushNfoFull=(f'<b>{self.__name.replace("_", " ")}</b>'
                                 f'<small><i><table>'
                                 f' <tr><td align="left"><b>{i18n("Blending mode")}:</b></td><td align="right">{self.__blendingMode}</td></tr>'
                                 f' <tr><td align="left"><b>{i18n("Size")}:</b></td>         <td align="right">{self.__size:0.2f}px</td></tr>'
                                 f' <tr><td align="left"><b>{i18n("Opacity")}:</b></td>      <td align="right">{100*self.__opacity:0.2f}%</td></tr>'
                                 f' <tr><td align="left"><b>{i18n("Flow")}:</b></td>         <td align="right">{100*self.__flow:0.2f}%</td></tr>'
                                 f'</table></i></small>'
                            )

            self.__brushNfoShort=(f'<b>{self.__name.replace("_", " ")}</b>'
                                  f'<small><br><i>{self.__size:0.2f}px - {self.__blendingMode}</i></small>'
                                )

            if self.__image:
                imageNfo=f'<img src="data:image/png;base64,{bytes(qImageToPngQByteArray(self.__image).toBase64(QByteArray.Base64Encoding)).decode()}">'

                self.__brushNfoFullImg=(f'<table><tr><td>{imageNfo}</td><td><b>{self.__name.replace("_", " ")}</b>'
                                     f'<small><i><table>'
                                     f' <tr><td align="left"><b>{i18n("Blending mode")}:</b></td><td align="right">{self.__blendingMode}</td></tr>'
                                     f' <tr><td align="left"><b>{i18n("Size")}:</b></td>         <td align="right">{self.__size:0.2f}px</td></tr>'
                                     f' <tr><td align="left"><b>{i18n("Opacity")}:</b></td>      <td align="right">{100*self.__opacity:0.2f}%</td></tr>'
                                     f' <tr><td align="left"><b>{i18n("Flow")}:</b></td>         <td align="right">{100*self.__flow:0.2f}%</td></tr>'
                                     f'</table></i></small> </tr></table>'
                                )
            else:
                self.__brushNfoFullImg=self.__brushNfoFull

            self.updated.emit(self, property)

    def beginUpdate(self):
        """Start updating note massivelly and then do note emit update"""
        self.__emitUpdated+=1

    def endUpdate(self):
        """Start updating note massivelly and then do note emit update"""
        self.__emitUpdated-=1
        if self.__emitUpdated<0:
            self.__emitUpdated=0
        elif self.__emitUpdated==0:
            self.__updated('*')

    def fromCurrentKritaBrush(self, view=None, saveColor=False):
        """Set brush properties from given view

        If no view is provided, use current active view
        """
        if view is None:
            view = Krita.instance().activeWindow().activeView()
            if view is None:
                return False
        elif not isinstance(view, View):
            return False

        if (view.visible()==False
            or view.document() is None):
            return False


        self.beginUpdate()

        brush=view.currentBrushPreset()

        self.__name=brush.name()
        self.__size=view.brushSize()
        self.__flow=view.paintingFlow()
        self.__opacity=view.paintingOpacity()
        self.__blendingMode=view.currentBlendingMode()
        self.__image=brush.image()

        if saveColor:
            self.__color=view.foregroundColor().colorForCanvas(view.canvas())
        else:
            self.__color=None

        if self.__ignoreEraserMode:
            self.__eraserMode=(self.__blendingMode=='erase')
        else:
            action=Krita.instance().action('erase_action')
            self.__eraserMode=action.isChecked()

        self.endUpdate()
        return True

    def toCurrentKritaBrush(self, view=None):
        """Set brush properties to given view

        If no view is provided, use current active view
        """
        if view is None:
            view = Krita.instance().activeWindow().activeView()
            if view is None:
                return False
        elif not isinstance(view, View):
            return False

        if not self.__name or not EKritaBrushPreset.found(self.__name):
            return False

        view.setCurrentBrushPreset(EKritaBrushPreset.getPreset(self.__name))

        view.setBrushSize(self.__size)
        view.setPaintingFlow(self.__flow)
        view.setPaintingOpacity(self.__opacity)
        view.setCurrentBlendingMode(self.__blendingMode)

        if self.__color!=None:
            view.setForeGroundColor(ManagedColor.fromQColor(self.__color, view.canvas()))

        # in all case restore eraser mode
        # - if __ignoreEraserMode is True, then force __eraserMode value because
        #   it's already set to the right value for given brush (True for eraser brush, False otherwise)
        # - if __ignoreEraserMode is False, then use __eraserMode value
        #   it contains the last value set for given brush
        action=Krita.instance().action('erase_action')
        action.setChecked(self.__eraserMode)

        return True

    def exportData(self):
        """Export brush definition as dictionary"""
        if self.__color is None:
            color=''
        else:
            color=self.__color.name(QColor.HexRgb)

        returned={
                BBSBrush.KEY_NAME: self.__name,
                BBSBrush.KEY_SIZE: self.__size,
                BBSBrush.KEY_FLOW: self.__flow,
                BBSBrush.KEY_OPACITY: self.__opacity,
                BBSBrush.KEY_BLENDINGMODE: self.__blendingMode,
                BBSBrush.KEY_ERASERMODE: self.__eraserMode,
                BBSBrush.KEY_COMMENTS: self.__comments,
                BBSBrush.KEY_KEEPUSERMODIFICATIONS: self.__keepUserModifications,
                BBSBrush.KEY_IGNOREERASERMODE: self.__ignoreEraserMode,
                BBSBrush.KEY_POSITION: self.__position,
                BBSBrush.KEY_COLOR: color,
                BBSBrush.KEY_UUID: self.__uuid,
                BBSBrush.KEY_SHORTCUT: self.__shortcut.toString(),
            }

        return returned

    def importData(self, value):
        """Import definition from dictionary"""
        if not isinstance(value, dict):
            return False

        self.beginUpdate()

        try:
            if BBSBrush.KEY_UUID in value:
                self.__uuid=value[BBSBrush.KEY_UUID]
            self.setName(value[BBSBrush.KEY_NAME])
            self.setSize(value[BBSBrush.KEY_SIZE])
            self.setFlow(value[BBSBrush.KEY_FLOW])
            self.setOpacity(value[BBSBrush.KEY_OPACITY])
            self.setBlendingMode(value[BBSBrush.KEY_BLENDINGMODE])
            self.setComments(value[BBSBrush.KEY_COMMENTS])
            self.setKeepUserModifications(value[BBSBrush.KEY_KEEPUSERMODIFICATIONS])
            self.setIgnoreEraserMode(value[BBSBrush.KEY_IGNOREERASERMODE])
            self.setColor(value[BBSBrush.KEY_COLOR])
            self.setEraserMode(value[BBSBrush.KEY_ERASERMODE])
            if EKritaBrushPreset.found(self.__name):
                brushPreset=EKritaBrushPreset.getPreset(self.__name)
                if brushPreset:
                    self.__image=brushPreset.image()

            action=self.action()
            if action and action.shortcut():
                self.setShortcut(action.shortcut())
            isValid=True
        except Exception as e:
            print("Unable to import brush definition:", e)
            isValid=False

        self.endUpdate()
        return isValid

    def name(self):
        """Return brush name"""
        return self.__name

    def setName(self, value):
        """Set name"""
        if value!=self.__name:
            self.__name=value
            self.__fingerPrint=''
            self.__updated('name')

    def size(self):
        """Return brush size"""
        return self.__size

    def setSize(self, value):
        """Set size"""
        if isinstance(value, (int, float)) and value>0 and self.__size!=value:
            self.__size=value
            self.__fingerPrint=''
            self.__updated('size')

    def flow(self):
        """Return brush flow"""
        return self.__flow

    def setFlow(self, value):
        """Set flow"""
        if isinstance(value, (int, float)) and value>=0 and value<=1.0 and self.__flow!=value:
            self.__flow=value
            self.__fingerPrint=''
            self.__updated('flow')

    def opacity(self):
        """Return brush opacity"""
        return self.__opacity

    def setOpacity(self, value):
        """Set opacity"""
        if isinstance(value, (int, float)) and value>=0 and value<=1.0 and self.__opacity!=value:
            self.__opacity=value
            self.__fingerPrint=''
            self.__updated('opacity')

    def blendingMode(self):
        """Return blending mode"""
        return self.__blendingMode

    def setBlendingMode(self, value):
        """Set blending mode"""
        if value!=self.__blendingMode:
            self.__blendingMode=value
            self.__fingerPrint=''
            self.__updated('blendingMode')

    def comments(self):
        """Return current comment for brush"""
        return self.__comments

    def setComments(self, value):
        """Set current comment for brush"""
        if value!=self.__comments:
            if stripHtml(value).strip()!='':
                self.__comments=value
            else:
                self.__comments=''
            self.__updated('comments')

    def keepUserModifications(self):
        """Return current keep user value for brush"""
        return self.__keepUserModifications

    def setKeepUserModifications(self, value):
        """Set current keep user value for brush"""
        if value!=self.__keepUserModifications and isinstance(value, bool):
            self.__keepUserModifications=value
            self.__updated('keepUserModifications')

    def ignoreEraserMode(self):
        """Return current keep user value for brush"""
        return self.__ignoreEraserMode

    def setIgnoreEraserMode(self, value):
        """Set current keep user value for brush"""
        if value!=self.__ignoreEraserMode and isinstance(value, bool):
            self.__ignoreEraserMode=value
            self.__updated('ignoreEraserMode')

    def image(self):
        """Return brush image"""
        return self.__image

    def setImage(self, image):
        """Set brush image"""
        if isinstance(image, QImage) and self.__image!=image:
            self.__image=image
            self.__updated('image')

    def position(self):
        """Return brush position in list"""
        return self.__position

    def setPosition(self, position):
        """Set brush position"""
        if isinstance(position, int) and self.__position!=position:
            self.__position=position
            self.__updated('position')

    def color(self):
        """Return brush position in list"""
        return self.__color

    def setColor(self, color):
        """Set brush color"""
        if color=='':
            color=None
        elif isinstance(color, str):
            try:
                color=QColor(color)
            except:
                return

        if color is None or isinstance(color, QColor) and self.__color!=color:
            self.__color=color
            self.__updated('color')

    def eraserMode(self):
        """Return eraser mode"""
        return self.__eraserMode

    def setEraserMode(self, eraserMode):
        """Set eraser mode"""
        if isinstance(eraserMode, bool) and self.__eraserMode!=eraserMode and not self.__ignoreEraserMode:
            self.__eraserMode=eraserMode
            self.__updated('eraserMode')

    def shortcut(self):
        """Return brush shortcut"""
        return self.__shortcut

    def setShortcut(self, shortcut):
        """Set brush shortcut

        Shortcut is used as an information only to simplify management
        """
        if isinstance(shortcut, QKeySequence) and self.__shortcut!=shortcut:
            self.__shortcut=shortcut
            self.__updated('shortcut')

    def id(self):
        """Return unique id"""
        return self.__uuid

    def actionId(self):
        """Return id to use for an action for this brush"""
        return BBSSettings.brushActionId(self.__uuid)

    def action(self):
        """Return Krita's action for this brush or none if not found"""
        return BBSSettings.brushAction(self.id())

    def fingerPrint(self):
        """Return finger print for brush"""
        if self.__fingerPrint=='':
            hash = blake2b()

            hash.update(self.__name.encode())
            hash.update(struct.pack('!d', self.__size))
            hash.update(struct.pack('!d', self.__flow))
            hash.update(struct.pack('!d', self.__opacity))
            hash.update(self.__blendingMode.encode())
            self.__fingerPrint=hash.hexdigest()

        return self.__fingerPrint

    def information(self, full=True, withImage=False):
        """Return synthetised brush information (HTML)"""
        if full:
            if withImage:
                return self.__brushNfoFullImg
            else:
                return self.__brushNfoFull
        else:
            return self.__brushNfoShort

    def found(self):
        """Return True if brush preset exists in krita otherwise False"""
        return EKritaBrushPreset.found(self.__name)


class BBSBrushes(QObject):
    """Collection of brushes"""
    updated = Signal(BBSBrush, str)
    updateReset = Signal()
    updateAdded = Signal(list)
    updateRemoved = Signal(list)

    def __init__(self, brushes=None):
        """Initialize object"""
        super(BBSBrushes, self).__init__(None)

        # store everything in a dictionary
        # key = id
        # value = BNNotes
        self.__brushes = {}

        self.__temporaryDisabled=True

        # list of added hash
        self.__updateAdd=[]
        self.__updateRemove=[]

        if isinstance(brushes, BBSBrushes):
            for brushId in brushes.idList():
                self.add(BBSBrush(brushes.get(brushId)))

        self.__temporaryDisabled=False

    def __itemUpdated(self, item, property):
        """A brush have been updated"""
        if not self.__temporaryDisabled:
            self.updated.emit(item, property)

    def __emitUpdateReset(self):
        """List have been cleared/loaded"""
        if not self.__temporaryDisabled:
            self.updateReset.emit()

    def __emitUpdateAdded(self):
        """Emit update signal with list of id to update

        An empty list mean a complete update
        """
        items=self.__updateAdd.copy()
        self.__updateAdd=[]
        if not self.__temporaryDisabled:
            self.updateAdded.emit(items)

    def __emitUpdateRemoved(self):
        """Emit update signal with list of id to update

        An empty list mean a complete update
        """
        items=self.__updateRemove.copy()
        self.__updateRemove=[]
        if not self.__temporaryDisabled:
            self.updateRemoved.emit(items)

    def __updatePositions(self, idList=None):
        """Recalculate and update positions of item in list"""
        self.__temporaryDisabled=True
        if idList is None:
            idList=self.idList()
        for index, brushId in enumerate(idList):
            self.__brushes[brushId].setPosition(index)
        self.__temporaryDisabled=False

    def length(self):
        """Return number of notes"""
        return len(self.__brushes)

    def idList(self, sortedList=True):
        """Return list of id"""
        returned=list(self.__brushes.keys())
        if sortedList:
            return sorted(returned, key=lambda brushId: self.__brushes[brushId].position())
        else:
            return returned

    def get(self, id):
        """Return brush from id, or None if nothing is found"""
        if id in self.__brushes:
            return self.__brushes[id]
        return None

    def getFromFingerPrint(self, fp):
        """Return brush from fingerPrint, or None if nothing is found"""
        for key in list(self.__brushes.keys()):
            if self.__brushes[key].fingerPrint()==fp:
                return self.__brushes[key]
        return None

    def getFromName(self, name):
        """Return brush from name, or None if nothing is found"""
        for key in list(self.__brushes.keys()):
            if self.__brushes[key].name()==name:
                return self.__brushes[key]
        return None

    def namesList(self, sortedList=True):
        """Return list of names"""
        returned=self.idList(sortedList)
        return [self.__brushes[key].name() for key in returned]


    def exists(self, item):
        """Return True if item is already in brushes, otherwise False"""
        if isinstance(item, str):
            return (item in self.__brushes)
        elif isinstance(item, BBSBrush):
            return (item.id() in self.__brushes)
        return False

    def clear(self):
        """Clear all brushes"""
        state=self.__temporaryDisabled

        self.__temporaryDisabled=True
        for key in list(self.__brushes.keys()):
            self.remove(self.__brushes[key])
        self.__temporaryDisabled=state
        if not self.__temporaryDisabled:
            self.__emitUpdateReset()

    def add(self, item):
        """Add Brush to list"""
        if isinstance(item, BBSBrush):
            item.setPosition(9999)
            item.updated.connect(self.__itemUpdated)
            self.__updateAdd.append(item.id())
            self.__brushes[item.id()]=item
            self.__updatePositions()
            self.__emitUpdateAdded()
            return True
        return False

    def remove(self, item):
        """Remove Brush from list"""
        removedBrush=None

        if isinstance(item, list) and len(item)>0:
            self.__temporaryDisabled=True
            for brush in item:
                self.remove(brush)
            self.__temporaryDisabled=False
            self.__updatePositions()
            self.__emitUpdateRemoved()
            return True

        if isinstance(item, str) and item in self.__brushes:
            removedBrush=self.__brushes.pop(item, None)
        elif isinstance(item, BBSBrush):
            removedBrush=self.__brushes.pop(item.id(), None)

        if not removedBrush is None:
            removedBrush.updated.disconnect(self.__itemUpdated)
            self.__updateRemove.append(removedBrush.id())
            self.__updatePositions()
            self.__emitUpdateRemoved()
            return True
        return False

    def update(self, item):
        """Update brush"""
        if isinstance(item, BBSBrush):
            if self.exists(item.id()):
                self.__itemUpdated(item, '*')
                self.__updatePositions()
            return True
        return False

    def copyFrom(self, brushes):
        """Copy brushes from another brushes"""
        if isinstance(brushes, BBSBrushes):
            self.__temporaryDisabled=True
            self.clear()
            for brushId in brushes.idList():
                self.add(BBSBrush(brushes.get(brushId)))
        self.__temporaryDisabled=False
        self.__emitUpdateReset()

    def moveItemAtFirst(self, item):
        """Move given `item` to first position in list"""
        return self.moveAtIndex(item, 0)

    def moveItemAtLast(self, item):
        """Move given `item` to last position in list"""
        return self.moveAtIndex(item, len(self.__brushes))

    def moveItemAtPrevious(self, item):
        """Move given `item` to previous position in list"""
        return self.moveAtIndex(item, 'p')

    def moveItemAtNext(self, item):
        """Move given `item` to next position in list"""
        return self.moveAtIndex(item, 'n')

    def moveAtIndex(self, item, indexTo):
        """Move given `item` to given `indexTo` position in list"""
        if isinstance(item, BBSBrush):
            if self.exists(item.id()):
                brushIdList=self.idList()

                indexFrom=brushIdList.index(item.id())

                if indexTo=='p' and indexFrom>0:
                    indexTo=indexFrom-1
                elif indexTo=='n' and indexFrom<len(brushIdList):
                    indexTo=indexFrom+1

                if indexFrom!=indexTo and isinstance(indexTo, int):
                    brushIdList.insert(indexTo, brushIdList.pop(indexFrom))
                    self.__updatePositions(brushIdList)
                    self.updateReset.emit()
            return True
        return False

    def beginUpdate(self):
        """Start to update list

        No signal will be emitted
        """
        self.__temporaryDisabled=True

    def endUpdate(self):
        """Update list finished

        Signal will be emitted
        """
        if len(self.__updateAdd):
            self.__emitUpdateAdded()
        if len(self.__updateRemove):
            self.__emitUpdateRemoved()
        self.__temporaryDisabled=False


class BBSBrushesModel(QAbstractTableModel):
    """A model provided for brushes"""
    updateWidth = Signal()

    ROLE_ID = Qt.UserRole + 1
    ROLE_BRUSH = Qt.UserRole + 2
    ROLE_CSIZE = Qt.UserRole + 3

    HEADERS = ['Icon', 'Brush', 'Description']
    COLNUM_ICON = 0
    COLNUM_BRUSH = 1
    COLNUM_COMMENT = 2
    COLNUM_LAST = 2

    def __init__(self, brushes, parent=None):
        """Initialise list"""
        super(BBSBrushesModel, self).__init__(parent)
        self.__brushes=brushes
        self.__brushes.updated.connect(self.__dataUpdated)
        self.__brushes.updateReset.connect(self.__dataUpdateReset)
        self.__brushes.updateAdded.connect(self.__dataUpdatedAdd)
        self.__brushes.updateRemoved.connect(self.__dataUpdateRemove)
        self.__items=self.__brushes.idList()

    def __idRow(self, id):
        """Return row number for a given id; return -1 if not found"""
        try:
            return self.__items.index(id)
        except Exception as e:
            return -1

    def __dataUpdateReset(self):
        """Data has entirely been changed (reset/reload)"""
        self.beginResetModel()
        self.__items=self.__brushes.idList()
        self.endResetModel()
        self.updateWidth.emit()

    def __dataUpdatedAdd(self, items):
        """Add a new brush to model"""
        self.__items=self.__brushes.idList()
        self.modelReset.emit()
        self.updateWidth.emit()

    def __dataUpdateRemove(self, items):
        """Remove brush from model"""
        self.__items=self.__brushes.idList()
        self.modelReset.emit()

    def __dataUpdated(self, item, property):
        """Update brush in model"""
        indexS=self.createIndex(self.__idRow(item.id()), 0)
        indexE=self.createIndex(self.__idRow(item.id()), BBSBrushesModel.COLNUM_LAST)
        self.dataChanged.emit(indexS, indexE, [Qt.DisplayRole])

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column"""
        return BBSBrushesModel.COLNUM_LAST+1

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows"""
        return self.__brushes.length()

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        column = index.column()
        row=index.row()

        if role == Qt.DecorationRole:
            id=self.__items[row]
            item = self.__brushes.get(id)

            if item:
                if column==BBSBrushesModel.COLNUM_ICON:
                    # QIcon
                    return QIcon(QPixmap.fromImage(item.image()))
        elif role == Qt.ToolTipRole:
            id=self.__items[row]
            item = self.__brushes.get(id)

            if item:
                if not item.found():
                    return i18n(f"Brush <i><b>{item.name()}</b></i> is not installed and/or activated on this Krita installation")
        elif role == Qt.DisplayRole:
            id=self.__items[row]
            item = self.__brushes.get(id)

            if item:
                if column==BBSBrushesModel.COLNUM_BRUSH:
                    return item.name()
                elif column==BBSBrushesModel.COLNUM_COMMENT:
                    return item.comments()
        elif role == BBSBrushesModel.ROLE_ID:
            return self.__items[row]
        elif role == BBSBrushesModel.ROLE_BRUSH:
            id=self.__items[row]
            return self.__brushes.get(id)
        #elif role == Qt.SizeHintRole:
        #    if column==BBSBrushesModel.COLNUM_ICON:
        #        return
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section>0:
            return BBSBrushesModel.HEADERS[section]
        return None

    def brushes(self):
        """Expose BBSBrushes object"""
        return self.__brushes

    def itemSelection(self, item):
        """Return model index for given brush"""
        returned=QItemSelection()
        if isinstance(item, BBSBrush):
            index=self.__idRow(item.id())
            if index>-1:
                indexS=self.createIndex(index, 0)
                indexE=self.createIndex(index, BBSBrushesModel.COLNUM_LAST)
                returned=QItemSelection(indexS, indexE)
        return returned


class BBSWBrushes(QTreeView):
    """Tree view brushes (editing mode)"""
    focused = Signal()
    keyPressed = Signal(int)
    iconSizeIndexChanged = Signal(int, QSize)

    __COLNUM_FULLNFO_MINSIZE = 7

    def __init__(self, parent=None):
        super(BBSWBrushes, self).__init__(parent)
        self.setAutoScroll(False)
        self.setAlternatingRowColors(True)

        self.__parent=parent
        self.__model = None
        self.__proxyModel = None
        self.__selectedBeforeReset=[]
        self.__fontSize=self.font().pointSizeF()
        if self.__fontSize==-1:
            self.__fontSize=-self.font().pixelSize()

        # value at which treeview apply compacted view (-1: never)
        self.__compactIconSizeIndex=-1

        self.__delegate=BBSBrushesModelDelegate(self)
        self.setItemDelegate(self.__delegate)

        self.__iconSize = IconSizes([32, 64, 96, 128, 192])
        self.setIconSizeIndex(3)

        self.__contextMenu=QMenu()
        self.__initMenu()

        header=self.header()
        header.sectionResized.connect(self.__sectionResized)
        self.resizeColumns()

    def __initMenu(self):
        """Initialise context menu"""
        pass

    def __modelAboutToBeReset(self):
        """model is about to be reset"""
        self.__selectedBeforeReset=self.selectedItems()

    def __modelReset(self):
        """model has been reset"""
        for selectedItem in self.__selectedBeforeReset:
            self.selectItem(selectedItem)

        self.__selectedBeforeReset=[]
        self.resizeColumns()

    def resizeColumns(self):
        """Resize columns"""
        self.resizeColumnToContents(BBSBrushesModel.COLNUM_ICON)
        self.resizeColumnToContents(BBSBrushesModel.COLNUM_BRUSH)

        width=max(self.columnWidth(BBSBrushesModel.COLNUM_BRUSH), self.columnWidth(BBSBrushesModel.COLNUM_ICON))
        self.setColumnWidth(BBSBrushesModel.COLNUM_BRUSH, round(width*1.25))

    def __sectionResized(self, index, oldSize, newSize):
        """When section is resized, update rows height"""
        if index==BBSBrushesModel.COLNUM_COMMENT and not self.isColumnHidden(BBSBrushesModel.COLNUM_COMMENT):
            # update height only if comment section is resized
            self.__delegate.setCSize(newSize)
            for rowNumber in range(self.__model.rowCount()):
                # need to recalculate height for all rows
                self.__delegate.sizeHintChanged.emit(self.__model.createIndex(rowNumber, index))

    def setColumnHidden(self, column, hide):
        """Reimplement column hidden"""
        super(BBSWBrushes, self).setColumnHidden(column, hide)
        self.__delegate.setCSize(0)

    def wheelEvent(self, event):
        """Mange zoom level through mouse wheel"""
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
            super(BBSWBrushes, self).wheelEvent(event)

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            self.setIconSize(self.__iconSize.value(True))
            self.__delegate.setCompactSize(self.__iconSize.index()<=self.__compactIconSizeIndex)

            header = self.header()
            header.resizeSection(BBSBrushesModel.COLNUM_ICON, self.__iconSize.value())
            self.resizeColumns()
            self.iconSizeIndexChanged.emit(self.__iconSize.index(), self.__iconSize.value(True))

    def setBrushes(self, brushes):
        """Initialise treeview header & model"""
        self.__model = BBSBrushesModel(brushes)

        #self.__proxyModel = QSortFilterProxyModel(self)
        #self.__proxyModel.setSourceModel(self.__model)

        self.setModel(self.__model)

        # set colums size rules
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(BBSBrushesModel.COLNUM_ICON, QHeaderView.Fixed)
        header.setSectionResizeMode(BBSBrushesModel.COLNUM_BRUSH, QHeaderView.Fixed)
        header.setSectionResizeMode(BBSBrushesModel.COLNUM_COMMENT, QHeaderView.Stretch)

        self.resizeColumns()
        self.__model.updateWidth.connect(self.resizeColumns)
        self.__model.modelAboutToBeReset.connect(self.__modelAboutToBeReset)
        self.__model.modelReset.connect(self.__modelReset)

    def selectItem(self, item):
        """Select given item"""
        if isinstance(item, BBSBrush):
            itemSelection=self.__model.itemSelection(item)
            self.selectionModel().select(itemSelection, QItemSelectionModel.ClearAndSelect)

    def selectedItems(self):
        """Return a list of selected brushes items"""
        returned=[]
        if self.selectionModel():
            for item in self.selectionModel().selectedRows(BBSBrushesModel.COLNUM_BRUSH):
                brush=item.data(BBSBrushesModel.ROLE_BRUSH)
                if not brush is None:
                    returned.append(brush)
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

        value=max(-1, min(value, 4))
        if self.__compactIconSizeIndex!=value:
            self.__compactIconSizeIndex=value
            self.__delegate.setCompactSize(self.__iconSize.index()<=self.__compactIconSizeIndex)
            self.update()


class BBSBrushesModelDelegate(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build improved rendering items"""
    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(BBSBrushesModelDelegate, self).__init__(parent)
        self.__csize=0
        self.__compactSize=False

    def __getBrushInformation(self, brush):
        """Return text for brush information"""
        textDocument=QTextDocument()
        textDocument.setHtml(brush.information(not self.__compactSize))
        return textDocument

    def __getOptionsInformation(self, brush):
        """Return text for brush options (comments + option)"""
        def yesno(value):
            if value:
                return i18n('Yes')
            else:
                return i18n('No')
        textDocument=QTextDocument()

        if not brush.shortcut().isEmpty():
            shortcutText=f' <tr><td align="left"><b>{i18n("Shortcut")}</b></td><td align="right">{brush.shortcut().toString()}</td></tr>'
        else:
            shortcutText=''

        if brush.blendingMode()=='erase':
            htmlText=(f'<small><i><table>'
                      f' <tr><td align="left"><b>{i18n("Keep user modifications")}</b></td><td align="right">{yesno(brush.keepUserModifications())}</td></tr>'
                      f' {shortcutText}'
                      f'</table></i></small>')
        else:
            if brush.color() is None:
                useSpecificColor=yesno(False)
                imageNfo=''
            else:
                imageNfo=f'&nbsp;<img src="data:image/png;base64,{bytes(qImageToPngQByteArray(bullet(16,brush.color(),"roundSquare").toImage()).toBase64(QByteArray.Base64Encoding)).decode()}">'
                useSpecificColor=yesno(True)

            htmlText=(f'<small><i><table>'
                      f' <tr><td align="left"><b>{i18n("Keep user modifications")}</b></td><td align="right">{yesno(brush.keepUserModifications())}</td><td></td></tr>'
                      f' <tr><td align="left"><b>{i18n("Ignore eraser mode")}:</b></td>    <td align="right">{yesno(brush.ignoreEraserMode())}</td><td></td></tr>'
                      f' <tr><td align="left"><b>{i18n("Use specific color")}:</b></td>    <td align="right">{useSpecificColor}</td><td>{imageNfo}</td></tr>'
                      f' {shortcutText}'
                      f'</table></i></small>')

        # comment are empty string '' if empty (already stripped in BBSBrush class)
        if not self.__compactSize:
            comments=brush.comments()
            if comments!='':
                htmlText=f"{comments}<hr>{htmlText}"

        textDocument.setHtml(htmlText)
        cursor=QTextCursor(textDocument)

        return textDocument

    def setCompactSize(self, value):
        """Activate/deactivate compact size"""
        self.__compactSize=value

    def setCSize(self, value):
        """Force size for comments column"""
        self.__csize=value

    def paint(self, painter, option, index):
        """Paint list item"""
        if index.column() == BBSBrushesModel.COLNUM_BRUSH:
            # render brush information
            self.initStyleOption(option, index)

            brush=index.data(BBSBrushesModel.ROLE_BRUSH)
            rectTxt = QRect(option.rect.left() + 1, option.rect.top()+4, option.rect.width()-4, option.rect.height()-1)

            painter.save()

            if not brush.found():
                if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                    option.state&=~QStyle.State_Selected
                painter.fillRect(option.rect, warningAreaBrush())

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            textDocument=self.__getBrushInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }");
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0,0), QSizeF(rectTxt.size()) ))

            #painter.drawText(rectTxt, Qt.AlignLeft|Qt.AlignTop, brush.name())

            painter.restore()
            return
        elif index.column() == BBSBrushesModel.COLNUM_COMMENT:
            # render comment
            self.initStyleOption(option, index)

            brush=index.data(BBSBrushesModel.ROLE_BRUSH)
            rectTxt = QRect(option.rect.left(), option.rect.top(), option.rect.width(), option.rect.height())

            textDocument=self.__getOptionsInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }");
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.save()

            if not brush.found():
                if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                    option.state&=~QStyle.State_Selected
                painter.fillRect(option.rect, warningAreaBrush())

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0,0), QSizeF(rectTxt.size()) ))

            painter.restore()
            return
        elif index.column() == BBSBrushesModel.COLNUM_ICON:
            # render icon in top-left position of cell
            painter.save()
            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))

            painter.drawPixmap(option.rect.topLeft(), index.data(Qt.DecorationRole).pixmap(option.decorationSize))
            painter.restore()
            return

        QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """Calculate size for items"""
        size = QStyledItemDelegate.sizeHint(self, option, index)

        if index.column() == BBSBrushesModel.COLNUM_ICON:
            return option.decorationSize
        elif index.column() == BBSBrushesModel.COLNUM_BRUSH:
            brush=index.data(BBSBrushesModel.ROLE_BRUSH)
            textDocument=self.__getBrushInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }");
            textDocument.setPageSize(QSizeF(4096, 1000)) # set 1000px size height arbitrary
            textDocument.setPageSize(QSizeF(textDocument.idealWidth(), 1000)) # set 1000px size height arbitrary
            size=textDocument.size().toSize()+QSize(8, 8)
        elif index.column() == BBSBrushesModel.COLNUM_COMMENT:
            # size for comments cell (width is forced, calculate height of rich text)
            brush=index.data(BBSBrushesModel.ROLE_BRUSH)
            textDocument=self.__getOptionsInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }");
            textDocument.setPageSize(QSizeF(self.__csize, 1000)) # set 1000px size height arbitrary
            size=QSize(self.__csize, textDocument.size().toSize().height())

        return size


class BBSBrushesEditor(WTextEditDialog):
    """A simple dialog box to brushe comment

    The WTextEditDialog doesn't allows to manage color picker configuration then,
    create a dedicated dailog box
    """

    @staticmethod
    def edit(title, brush):
        """Open a dialog box to edit text"""
        cbKeepUserModifications=None
        cbIgnoreEraserMode=None
        cbUseSpecificColor=None
        btUseSpecificColor=None
        kseShortcut=None
        lblShortcutAlreadyUsed=None
        dlgBox=None

        def shorcutModification(keySequence):
            """Shortcut value is currently modified"""
            # disable OK button, waiting for editingFinished singal to determinate
            # if shortcut is valid or not
            nonlocal lblShortcutAlreadyUsed
            nonlocal dlgBox
            lblShortcutAlreadyUsed.setText('')
            dlgBox.setOkEnabled(False)

        def shortcutModified():
            """Shortcut value has been modified

            Check if valid
            """
            nonlocal kseShortcut
            nonlocal lblShortcutAlreadyUsed
            nonlocal dlgBox
            keySequence=kseShortcut.keySequence()
            if keySequence.isEmpty():
                dlgBox.setOkEnabled(True)
                lblShortcutAlreadyUsed.setText('')
                lblShortcutAlreadyUsed.setStyleSheet('')
            else:
                # need to check if shortcut already exists or not in Krita
                foundActions=EKritaShortcuts.checkIfExists(keySequence)
                if len(foundActions)==0:
                    dlgBox.setOkEnabled(True)
                    lblShortcutAlreadyUsed.setText('')
                    lblShortcutAlreadyUsed.setStyleSheet('')
                else:
                    dlgBox.setOkEnabled(False)
                    text=[i18n("<b>Shortcut is already used</b>")]
                    eChar='\x01'
                    for action in foundActions:
                        text.append(f"- <i>{action.text().replace('&&', eChar).replace('&', '').replace(eChar, '&')}</i>")
                    lblShortcutAlreadyUsed.setText("<br>".join(text))
                    lblShortcutAlreadyUsed.setStyleSheet(UITheme.style('warning-box'))

        def getTitleLabel(text):
            title=QLabel(text)
            titleFont=title.font()
            titleFont.setBold(True)
            titleFont.setPointSize(12)
            title.setFont(titleFont)
            title.setStyleSheet("background-color: palette(light);padding: 6;")
            title.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
            return title

        def getBrushLayout(brush):
            # return a QLayout with current information
            layout=QHBoxLayout()

            lblImage=QLabel()
            lblImage.setPixmap(QPixmap.fromImage(brush.image()).scaled(128,128,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            lblImage.setMaximumSize(128, 128)
            lblImage.setMinimumSize(128, 128)

            lblInfo=QLabel(brush.information(True))

            layout.addWidget(lblImage)
            layout.addWidget(lblInfo)

            return layout

        def getOptionsLayout(brush):
            # return a QLayout with current brush options
            nonlocal cbKeepUserModifications
            nonlocal cbIgnoreEraserMode
            nonlocal cbUseSpecificColor
            nonlocal btUseSpecificColor
            nonlocal kseShortcut
            nonlocal lblShortcutAlreadyUsed

            layout=QGridLayout()

            cbKeepUserModifications=QCheckBox(i18n('Keep user modifications'))
            cbKeepUserModifications.setToolTip(i18n("When checked, user modifications made on plugin selected brush (size, opacity, ...) are kept in memory and reapplied on next switch to plugin brush\nWhen unchecked user modifications made on plugin selected brush are not kept and default values are applied on next switch to plugin brush"))
            cbKeepUserModifications.setChecked(brush.keepUserModifications())

            if brush.blendingMode()!='erase':
                # for eraser, eraser mode is ignored
                cbIgnoreEraserMode=QCheckBox(i18n('Ignore eraser mode'))
                cbIgnoreEraserMode.setToolTip(i18n("When brush is selected, eraser mode is ignored"))
                cbIgnoreEraserMode.setChecked(brush.ignoreEraserMode())

                # for eraser brush, option is not available
                color=brush.color()

                lUseSpecificColor=QHBoxLayout()

                cbUseSpecificColor=QCheckBox(i18n('Use specific color'))
                cbUseSpecificColor.setToolTip(i18n("When checked, defined color is always used on next switch to plugin brush; brush color is restored when going back to Krita's brush\nWhen unchecked, current color used bu Krita's is used on next switch to plugin brush"))

                btUseSpecificColor=WColorButton()
                btUseSpecificColor.colorPicker().setOptionLayout(BBSSettings.getBrushColorPickerLayout())

                if color is None:
                    cbUseSpecificColor.setChecked(False)
                    btUseSpecificColor.setVisible(False)
                else:
                    cbUseSpecificColor.setChecked(True)
                    btUseSpecificColor.setVisible(True)
                btUseSpecificColor.setColor(color)
                cbUseSpecificColor.toggled.connect(lambda isChecked: btUseSpecificColor.setVisible(isChecked))

                lUseSpecificColor.addWidget(cbUseSpecificColor)
                lUseSpecificColor.addWidget(btUseSpecificColor)
                lUseSpecificColor.addStretch()


            # layout for shortcut options
            lblShortcutAlreadyUsed=QLabel()
            font=lblShortcutAlreadyUsed.font()
            font.setPointSize(8)
            lblShortcutAlreadyUsed.setFont(font)
            kseShortcut=WKeySequenceInput()
            kseShortcut.setKeySequence(brush.shortcut())
            kseShortcut.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
            kseShortcut.setClearButtonEnabled(True)
            kseShortcut.keySequenceCleared.connect(shortcutModified)
            kseShortcut.editingFinished.connect(shortcutModified)
            kseShortcut.keySequenceChanged.connect(shorcutModification)
            lShortcut=QHBoxLayout()
            lShortcut.addWidget(QLabel(i18n('Shortcut')))
            lShortcut.addWidget(kseShortcut)

            # define grid layout
            layout.setColumnStretch(0, 50)
            layout.setColumnStretch(1, 50)

            # add widget - row 1
            layout.addWidget(cbKeepUserModifications, 0, 0)
            layout.addLayout(lShortcut, 0, 1)
            # add widget - row2
            layout.addWidget(cbIgnoreEraserMode, 1, 0)
            layout.addWidget(lblShortcutAlreadyUsed, 1, 1, -1, 1)

            if not cbUseSpecificColor is None:
                layout.addLayout(lUseSpecificColor, 2, 0)

            return layout

        dlgBox = BBSBrushesEditor(None)
        dlgBox.setHtml(brush.comments())
        dlgBox.setWindowTitle(title)

        dlgBox.editor.setToolbarButtons(WTextEdit.DEFAULT_TOOLBAR|WTextEditBtBarOption.STYLE_STRIKETHROUGH|WTextEditBtBarOption.STYLE_COLOR_BG)
        dlgBox.editor.setColorPickerLayout(BBSSettings.getTxtColorPickerLayout())

        dlgBox.layout().insertWidget(0, getTitleLabel(i18n('Comments')))

        # add options
        dlgBox.layout().insertLayout(0, getOptionsLayout(brush))
        dlgBox.layout().insertWidget(0, getTitleLabel(i18n('Options')))

        # Add brush information
        dlgBox.layout().insertLayout(0, getBrushLayout(brush))
        dlgBox.layout().insertWidget(0, getTitleLabel(i18n('Brush')))

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            BBSSettings.setTxtColorPickerLayout(dlgBox.editor.colorPickerLayout())
            if not btUseSpecificColor is None:
                BBSSettings.setBrushColorPickerLayout(btUseSpecificColor.colorPicker().optionLayout())
            returned={
                    BBSBrush.KEY_COMMENTS: dlgBox.toHtml(),
                    BBSBrush.KEY_KEEPUSERMODIFICATIONS: cbKeepUserModifications.isChecked(),
                    BBSBrush.KEY_IGNOREERASERMODE: True,
                    BBSBrush.KEY_SHORTCUT: kseShortcut.keySequence(),
                    BBSBrush.KEY_COLOR: None
                }

            if not cbIgnoreEraserMode is None:
                returned[BBSBrush.KEY_IGNOREERASERMODE]=cbIgnoreEraserMode.isChecked()

            if not cbUseSpecificColor is None and cbUseSpecificColor.isChecked():
                returned[BBSBrush.KEY_COLOR]=btUseSpecificColor.color()

            return returned
        else:
            return None
