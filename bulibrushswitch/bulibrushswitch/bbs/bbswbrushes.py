# -----------------------------------------------------------------------------
# Buli Brush Switch
# Copyright (C) 2011-2022 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin designed to manage brushes switch easy
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# The bnbrushes module provides classes used to manage brushes
#
# Main classes from this module
#
# - BNBrushes:
#       Collection of brushes
#
# - BNBrushPreset:
#       Static methods to access to brushes 'securely' (shouldn't fail to get
#       a brush)
#
# - BNBrush:
#       A brush definition (managed by BNBrushes collection)
#
# -----------------------------------------------------------------------------
import ctypes
import json
import re
import os.path

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

from bulibrushswitch.pktk.modules.edialog import EDialog
from bulibrushswitch.pktk.modules.uitheme import UITheme
from bulibrushswitch.pktk.modules.iconsizes import IconSizes
from bulibrushswitch.pktk.modules.utils import replaceLineEditClearButton
from bulibrushswitch.pktk.modules.strutils import stripHtml
from bulibrushswitch.pktk.modules.imgutils import (warningAreaBrush, qImageToPngQByteArray, bullet, buildIcon, roundedPixmap)
from bulibrushswitch.pktk.modules.resutils import (ManagedResourceTypes, ManagedResource, ManagedResourcesModel)
from bulibrushswitch.pktk.modules.ekrita import (EKritaBrushPreset, EKritaShortcuts, EKritaBlendingModes)
from bulibrushswitch.pktk.modules.ekrita_tools import (EKritaToolsCategory, EKritaTools)
from bulibrushswitch.pktk.widgets.wtextedit import (WTextEdit, WTextEditDialog, WTextEditBtBarOption)
from bulibrushswitch.pktk.widgets.wcolorbutton import WColorButton
from bulibrushswitch.pktk.widgets.wcolorselector import WColorPicker
from bulibrushswitch.pktk.widgets.wkeysequenceinput import WKeySequenceInput
from bulibrushswitch.pktk.widgets.wstandardcolorselector import WStandardColorSelector

# module instance of ManagedResourcesModel, dedicated for gradients
_bbsManagedResourcesGradients = ManagedResourcesModel()
_bbsManagedResourcesGradients.setResourceType(ManagedResourceTypes.RES_GRADIENTS)


class BBSBaseNode(QObject):
    """Base class for brushes and groups"""
    updated = Signal(QObject, str)

    INFO_COMPACT =            0b00000001
    INFO_WITH_ICON =          0b00000010
    INFO_WITH_DETAILS =       0b00000100
    INFO_WITH_OPTIONS =       0b00001000

    KEY_UUID = 'uuid'
    KEY_POSITION = 'position'

    def __init__(self, parent=None):
        super(BBSBaseNode, self).__init__(None)
        self.__uuid = QUuid.createUuid().toString().strip("{}")
        self.__emitUpdated = 0
        self.__position = 999999
        self.__node = None

    def _setId(self, id):
        """Set unique id """
        self.__uuid = id.strip("{}")

    def id(self):
        """Return unique id"""
        return self.__uuid

    def position(self):
        """Return brush position in list"""
        return self.__position

    def setPosition(self, position):
        """Set brush position"""
        if isinstance(position, int) and self.__position != position:
            self.__position = position
            self.applyUpdate('position')

    def acceptedChild(self):
        """Return a list of allowed children types

        Return empty list if node don't accept childs
        """
        return tuple()

    def applyUpdate(self, property):
        if self.__emitUpdated == 0:
            self.updated.emit(self, property)

    def beginUpdate(self):
        """Start updating massivelly and then do not emit update"""
        self.__emitUpdated += 1

    def endUpdate(self):
        """Stop updating massivelly and then emit update"""
        self.__emitUpdated -= 1
        if self.__emitUpdated < 0:
            self.__emitUpdated = 0
        elif self.__emitUpdated == 0:
            self.applyUpdate('*')

    def inUpdate(self):
        """Return if currently in a massive update"""
        return (self.__emitUpdated != 0)

    def information(self, displayOption=0):
        """Return synthetised information (HTML)"""
        return ''

    def node(self):
        """return node owner"""
        return self.__node

    def setNode(self, node):
        """set node owner"""
        self.__node = node


class BBSBrush(BBSBaseNode):
    """A brush definition"""
    KEY_NAME = 'name'
    KEY_SIZE = 'size'
    KEY_FLOW = 'flow'
    KEY_OPACITY = 'opacity'
    KEY_BLENDINGMODE = 'blendingMode'
    KEY_PRESERVEALPHA = 'preserveAlpha'
    KEY_IGNORETOOLOPACITY = 'ignoreToolOpacity'
    KEY_COMMENTS = 'comments'
    KEY_IMAGE = 'image'
    KEY_ERASERMODE = 'eraserMode'
    KEY_KEEPUSERMODIFICATIONS = 'keepUserModifications'
    KEY_IGNOREERASERMODE = 'ignoreEraserMode'
    KEY_COLOR_FG = 'color'
    KEY_COLOR_BG = 'colorBg'
    KEY_COLOR_GRADIENT = 'colorGradient'
    KEY_DEFAULTPAINTTOOL = 'defaultPaintTool'
    KEY_SHORTCUT = 'shortcut'

    KRITA_BRUSH_FGCOLOR =  0b00000001
    KRITA_BRUSH_BGCOLOR =  0b00000010
    KRITA_BRUSH_GRADIENT = 0b00000100
    KRITA_BRUSH_TOOLOPT =  0b00001000

    def __init__(self, brush=None):
        super(BBSBrush, self).__init__(None)
        self.__name = ''
        self.__size = 0
        self.__flow = 0
        self.__opacity = 0
        self.__blendingMode = ''
        self.__preserveAlpha = False
        self.__comments = ''
        self.__image = None
        self.__keepUserModifications = True
        self.__eraserMode = False
        self.__ignoreEraserMode = True
        self.__ignoreToolOpacity = False
        self.__colorFg = None
        self.__colorBg = None
        self.__colorGradient = None
        self.__defaultPaintTool = None
        self.__shortcut = QKeySequence()

        self.__fingerPrint = ''

        self.__brushNfoImg = ''
        self.__brushNfoFull = ''
        self.__brushNfoShort = ''
        self.__brushNfoOptions = ''
        self.__brushNfoComments = ''

        # this allows to keep current Krita's brush value
        # if None => nothing memorized
        #            otherwise it's a BBSBrush
        self.__kritaBrush = None
        # a flag to determinate if Krita brush is currently in restoring state
        self.__kritaBrushIsRestoring = False

        if isinstance(brush, BBSBrush):
            # clone brush
            self.importData(brush.exportData())
        elif isinstance(brush, dict):
            self.importData(brush)

    def __repr__(self):
        return f"<BBSBrush({self.id()}, '{self.__name}', '{self.position()}')>"

    def applyUpdate(self, property):
        """Emit updated signal when a property has been changed"""
        def yesno(value):
            if value:
                return i18n('Yes')
            else:
                return i18n('No')

        if not self.inUpdate():
            self.__brushNfoFull = (f' <tr><td align="left"><b>{i18n("Blending mode")}:</b></td><td align="right">{self.__blendingMode}</td><td></td></tr>'
                                   f' <tr><td align="left"><b>{i18n("Size")}:</b></td>         <td align="right">{self.__size:0.2f}px</td><td></td></tr>'
                                   f' <tr><td align="left"><b>{i18n("Opacity")}:</b></td>      <td align="right">{100*self.__opacity:0.2f}%</td><td></td></tr>'
                                   f' <tr><td align="left"><b>{i18n("Flow")}:</b></td>         <td align="right">{100*self.__flow:0.2f}%</td><td></td></tr>'
                                   )

            self.__brushNfoShort = f' <tr><td align="left">{self.__size:0.2f}px - {self.__blendingMode}</td><td></td><td></td></tr>'

            if self.__image:
                self.__brushNfoImg = f'<img src="data:image/png;base64,{bytes(qImageToPngQByteArray(roundedPixmap(QPixmap.fromImage(self.__image), 8).toImage()).toBase64(QByteArray.Base64Encoding)).decode()}">'
            else:
                self.__brushNfoImg = ''

            if not self.__shortcut.isEmpty():
                shortcutText = f' <tr><td align="left"><b>{i18n("Shortcut")}</b></td><td align="right">{self.__shortcut.toString()}</td><td></td></tr>'
            else:
                shortcutText = ''

            if self.__defaultPaintTool is not None:
                defaultPaintTool = f' <tr><td align="left"><b>{i18n("Default paint tool")}</b></td>'\
                                   f'<td align="right">{EKritaTools.name(self.__defaultPaintTool)}</td><td></td></tr>'
            else:
                defaultPaintTool = ''

            if self.__blendingMode == 'erase':
                self.__brushNfoOptions = (f' {defaultPaintTool}'
                                          f' <tr><td align="left"><b>{i18n("Keep user modifications")}</b></td><td align="right">{yesno(self.__blendingMode)}</td><td></td></tr>'
                                          f' {shortcutText}'
                                          )
            else:
                if self.__colorFg is None:
                    useSpecificColor = yesno(False)
                    imageNfo = ''
                else:
                    imageNfo = f'&nbsp;<img src="data:image/png;base64,'\
                               f'{bytes(qImageToPngQByteArray(bullet(16, self.__colorFg,"roundSquare").toImage()).toBase64(QByteArray.Base64Encoding)).decode()}">'
                    if self.__colorBg is not None:
                        imageNfo += f'&nbsp;<img src="data:image/png;base64,'\
                                    f'{bytes(qImageToPngQByteArray(bullet(16, self.__colorBg,"roundSquare").toImage()).toBase64(QByteArray.Base64Encoding)).decode()}">'
                    if self.__colorGradient is not None and self.__colorGradient.id() is not None:
                        pngQByteArray = qImageToPngQByteArray(self.__colorGradient.thumbnail().scaledToHeight(16, Qt.SmoothTransformation).toImage())
                        imageNfo += f'&nbsp;<img src="data:image/png;base64,'\
                                    f'{bytes(pngQByteArray.toBase64(QByteArray.Base64Encoding)).decode()}">'
                    useSpecificColor = yesno(True)

                self.__brushNfoOptions = (f' {defaultPaintTool}'

                                          f' <tr><td align="left"><b>{i18n("Use specific color")}:</b></td>'
                                          f'     <td align="right">{useSpecificColor}</td><td>{imageNfo}</td></tr>'

                                          f' <tr><td align="left"><b>{i18n("Preserve Alpha")}:</b></td>'
                                          f'     <td align="right">{yesno(self.__preserveAlpha)}</td><td></td></tr>'

                                          f' <tr><td align="left"><b>{i18n("Ignore tool opacity")}:</b></td>'
                                          f'     <td align="right">{yesno(self.__ignoreToolOpacity)}</td><td></td></tr>'

                                          f' <tr><td align="left"><b>{i18n("Keep user modifications")}</b></td>'
                                          f'     <td align="right">{yesno(self.__keepUserModifications)}</td><td></td></tr>'

                                          f' <tr><td align="left"><b>{i18n("Ignore eraser mode")}:</b></td>'
                                          f'     <td align="right">{yesno(self.__ignoreEraserMode)}</td><td></td></tr>'

                                          f' {shortcutText}'
                                          )

            self.__brushNfoComments = self.__comments
            if self.__brushNfoComments != '':
                self.__brushNfoComments = re.sub("<(/)?body",
                                                 r"<\1div", re.sub("<!doctype[^>]+>|<meta[^>]+>|</?html>|</?head>", "", self.__brushNfoComments, flags=re.I),
                                                 flags=re.I)

        super(BBSBrush, self).applyUpdate(property)

    def fromCurrentKritaBrush(self, view=None, saveOptions=0):
        """Set brush properties from given view

        If no view is provided, use current active view
        """
        global _bbsManagedResourcesGradients

        if view is None:
            view = Krita.instance().activeWindow().activeView()
            if view is None:
                return False
        elif not isinstance(view, View):
            return False

        if (view.visible() is False
           or view.document() is None):
            return False

        self.beginUpdate()

        brush = view.currentBrushPreset()

        self.__name = brush.name()
        self.__size = view.brushSize()
        self.__flow = view.paintingFlow()
        self.__opacity = view.paintingOpacity()
        self.__blendingMode = view.currentBlendingMode()
        self.__preserveAlpha = Krita.instance().action('preserve_alpha').isChecked()
        self.__image = brush.image()

        if saveOptions & BBSBrush.KRITA_BRUSH_FGCOLOR == BBSBrush.KRITA_BRUSH_FGCOLOR:
            self.__colorFg = view.foregroundColor().colorForCanvas(view.canvas())
        else:
            self.__colorFg = None

        if saveOptions & BBSBrush.KRITA_BRUSH_BGCOLOR == BBSBrush.KRITA_BRUSH_BGCOLOR:
            self.__colorBg = view.backgroundColor().colorForCanvas(view.canvas())
        else:
            self.__colorBg = None

        if saveOptions & BBSBrush.KRITA_BRUSH_GRADIENT == BBSBrush.KRITA_BRUSH_GRADIENT:
            self.__colorGradient = _bbsManagedResourcesGradients.getResource(view.currentGradient())
        else:
            self.__colorGradient = None

        if saveOptions & BBSBrush.KRITA_BRUSH_TOOLOPT == BBSBrush.KRITA_BRUSH_TOOLOPT:
            current = EKritaTools.current()
            if current:
                self.__defaultPaintTool = current
        else:
            self.__defaultPaintTool = None

        if self.__ignoreEraserMode:
            self.__eraserMode = (self.__blendingMode == 'erase')
        else:
            action = Krita.instance().action('erase_action')
            self.__eraserMode = action.isChecked()

        self.endUpdate()
        return True

    def toCurrentKritaBrush(self, view=None, loadColor=True, loadTool=True):
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

        if self.__kritaBrush is None and self.__kritaBrushIsRestoring is False:
            # currently nothing has been memorized
            # memorize current brush
            self.__kritaBrush = BBSBrush()
            self.__kritaBrush.fromCurrentKritaBrush(view)

        if self.__defaultPaintTool is not None and loadTool:
            # as tool already keep is own properties, restore tool before brush properties to ensure that memorized brush properties
            # are properly applied after
            EKritaTools.setCurrent(self.__defaultPaintTool)

        view.setBrushSize(self.__size)
        view.setPaintingFlow(self.__flow)
        view.setPaintingOpacity(self.__opacity)
        view.setCurrentBlendingMode(self.__blendingMode)
        Krita.instance().action('preserve_alpha').setChecked(self.__preserveAlpha)

        if self.__colorFg is not None and loadColor:
            # use specific color
            view.setForeGroundColor(ManagedColor.fromQColor(self.__colorFg, view.canvas()))

            # use bg specific color (available only if fg specific color is defined)
            if self.__colorBg is not None:
                view.setBackGroundColor(ManagedColor.fromQColor(self.__colorBg, view.canvas()))

        if self.__colorGradient is not None and loadColor:
            # use specific gradient
            view.setCurrentGradient(self.__colorGradient.resource())

        # in all case restore eraser mode
        # - if __ignoreEraserMode is True, then force __eraserMode value because
        #   it's already set to the right value for given brush (True for eraser brush, False otherwise)
        # - if __ignoreEraserMode is False, then use __eraserMode value
        #   it contains the last value set for given brush
        Krita.instance().action('erase_action').setChecked(self.__eraserMode)

        return True

    def exportData(self):
        """Export brush definition as dictionary"""
        if self.__colorFg is None:
            colorFg = ''
        else:
            colorFg = self.__colorFg.name(QColor.HexRgb)

        if self.__colorBg is None:
            colorBg = ''
        else:
            colorBg = self.__colorBg.name(QColor.HexRgb)

        if self.__colorGradient is None:
            colorGradient = 0
        else:
            colorGradient = self.__colorGradient.id()

        returned = {
                BBSBrush.KEY_NAME: self.__name,
                BBSBrush.KEY_SIZE: self.__size,
                BBSBrush.KEY_FLOW: self.__flow,
                BBSBrush.KEY_OPACITY: self.__opacity,
                BBSBrush.KEY_BLENDINGMODE: self.__blendingMode,
                BBSBrush.KEY_PRESERVEALPHA: self.__preserveAlpha,
                BBSBrush.KEY_ERASERMODE: self.__eraserMode,
                BBSBrush.KEY_COMMENTS: self.__comments,
                BBSBrush.KEY_KEEPUSERMODIFICATIONS: self.__keepUserModifications,
                BBSBrush.KEY_IGNOREERASERMODE: self.__ignoreEraserMode,
                BBSBrush.KEY_POSITION: self.position(),
                BBSBrush.KEY_COLOR_FG: colorFg,
                BBSBrush.KEY_COLOR_BG: colorBg,
                BBSBrush.KEY_COLOR_GRADIENT: colorGradient,
                BBSBrush.KEY_UUID: self.id(),
                BBSBrush.KEY_SHORTCUT: self.__shortcut.toString(),
                BBSBrush.KEY_DEFAULTPAINTTOOL: self.__defaultPaintTool,
                BBSBrush.KEY_IGNORETOOLOPACITY: self.__ignoreToolOpacity
            }

        return returned

    def importData(self, value):
        """Import definition from dictionary"""
        if not isinstance(value, dict):
            return False

        self.beginUpdate()

        try:
            if BBSBrush.KEY_UUID in value:
                self._setId(value[BBSBrush.KEY_UUID])
            if BBSBrush.KEY_POSITION in value:
                self.setPosition(value[BBSBrush.KEY_POSITION])
            if BBSBrush.KEY_NAME in value:
                self.setName(value[BBSBrush.KEY_NAME])
            if BBSBrush.KEY_SIZE in value:
                self.setSize(value[BBSBrush.KEY_SIZE])
            if BBSBrush.KEY_FLOW in value:
                self.setFlow(value[BBSBrush.KEY_FLOW])
            if BBSBrush.KEY_OPACITY in value:
                self.setOpacity(value[BBSBrush.KEY_OPACITY])
            if BBSBrush.KEY_BLENDINGMODE in value:
                self.setBlendingMode(value[BBSBrush.KEY_BLENDINGMODE])
            if BBSBrush.KEY_PRESERVEALPHA in value:
                self.setPreserveAlpha(value[BBSBrush.KEY_PRESERVEALPHA])
            if BBSBrush.KEY_IGNORETOOLOPACITY in value:
                self.setIgnoreToolOpacity(value[BBSBrush.KEY_IGNORETOOLOPACITY])
            if BBSBrush.KEY_COMMENTS in value:
                self.setComments(value[BBSBrush.KEY_COMMENTS])
            if BBSBrush.KEY_KEEPUSERMODIFICATIONS in value:
                self.setKeepUserModifications(value[BBSBrush.KEY_KEEPUSERMODIFICATIONS])
            if BBSBrush.KEY_IGNOREERASERMODE in value:
                self.setIgnoreEraserMode(value[BBSBrush.KEY_IGNOREERASERMODE])
            if BBSBrush.KEY_COLOR_FG in value:
                self.setColorFg(value[BBSBrush.KEY_COLOR_FG])
            if BBSBrush.KEY_COLOR_BG in value:
                self.setColorBg(value[BBSBrush.KEY_COLOR_BG])
            if BBSBrush.KEY_COLOR_GRADIENT in value:
                self.setColorGradient(value[BBSBrush.KEY_COLOR_GRADIENT])
            if BBSBrush.KEY_ERASERMODE in value:
                self.setEraserMode(value[BBSBrush.KEY_ERASERMODE])

            if BBSBrush.KEY_DEFAULTPAINTTOOL in value:
                self.setDefaultPaintTool(value[BBSBrush.KEY_DEFAULTPAINTTOOL])

            if EKritaBrushPreset.found(self.__name):
                brushPreset = EKritaBrushPreset.getPreset(self.__name)
                if brushPreset:
                    self.__image = brushPreset.image()

            action = self.action()
            if action and action.shortcut():
                self.setShortcut(action.shortcut())
            isValid = True
        except Exception as e:
            print("Unable to import brush definition:", e)
            isValid = False

        self.endUpdate()
        return isValid

    def name(self):
        """Return brush name"""
        return self.__name

    def setName(self, value):
        """Set name"""
        if value != self.__name:
            self.__name = value
            self.__fingerPrint = ''
            self.applyUpdate('name')

    def size(self):
        """Return brush size"""
        return self.__size

    def setSize(self, value):
        """Set size"""
        if isinstance(value, (int, float)) and value > 0 and self.__size != value:
            self.__size = value
            self.__fingerPrint = ''
            self.applyUpdate('size')

    def flow(self):
        """Return brush flow"""
        return self.__flow

    def setFlow(self, value):
        """Set flow"""
        if isinstance(value, (int, float)) and value >= 0 and value <= 1.0 and self.__flow != value:
            self.__flow = value
            self.__fingerPrint = ''
            self.applyUpdate('flow')

    def opacity(self):
        """Return brush opacity"""
        return self.__opacity

    def setOpacity(self, value):
        """Set opacity"""
        if isinstance(value, (int, float)) and value >= 0 and value <= 1.0 and self.__opacity != value:
            self.__opacity = value
            self.__fingerPrint = ''
            self.applyUpdate('opacity')

    def blendingMode(self):
        """Return blending mode"""
        return self.__blendingMode

    def setBlendingMode(self, value):
        """Set blending mode"""
        if value != self.__blendingMode:
            self.__blendingMode = value
            self.__fingerPrint = ''
            self.applyUpdate('blendingMode')

    def preserveAlpha(self):
        """Preserve alpha mode"""
        return self.__preserveAlpha

    def setPreserveAlpha(self, value):
        """Set preserve alpha mode"""
        if value != self.__preserveAlpha and isinstance(value, bool):
            self.__preserveAlpha = value
            self.applyUpdate('preserveAlpha')

    def comments(self):
        """Return current comment for brush"""
        return self.__comments

    def setComments(self, value):
        """Set current comment for brush"""
        if value != self.__comments:
            if stripHtml(value).strip() != '':
                self.__comments = value
            else:
                self.__comments = ''
            self.applyUpdate('comments')

    def keepUserModifications(self):
        """Return current keep user value for brush"""
        return self.__keepUserModifications

    def setKeepUserModifications(self, value):
        """Set current keep user value for brush"""
        if value != self.__keepUserModifications and isinstance(value, bool):
            self.__keepUserModifications = value
            self.applyUpdate('keepUserModifications')

    def ignoreEraserMode(self):
        """Return current eraser mode behavior for brush"""
        return self.__ignoreEraserMode

    def setIgnoreEraserMode(self, value):
        """Set current eraser mode behavior for brush"""
        if value != self.__ignoreEraserMode and isinstance(value, bool):
            self.__ignoreEraserMode = value
            self.applyUpdate('ignoreEraserMode')

    def ignoreToolOpacity(self):
        """Return current tool opacity behavior for brush"""
        return self.__ignoreToolOpacity

    def setIgnoreToolOpacity(self, value):
        """Set current tool opacity behavior for brush"""
        if value != self.__ignoreToolOpacity and isinstance(value, bool):
            self.__ignoreToolOpacity = value
            self.applyUpdate('ignoreToolOpacity')

    def image(self):
        """Return brush image"""
        return self.__image

    def setImage(self, image):
        """Set brush image"""
        if isinstance(image, QImage) and self.__image != image:
            self.__image = image
            self.applyUpdate('image')

    def colorFg(self):
        """Return foreground color"""
        return self.__colorFg

    def setColorFg(self, color):
        """Set brush foreground color"""
        if color == '':
            color = None
        elif isinstance(color, str):
            try:
                color = QColor(color)
            except Exception:
                return

        if color is None or isinstance(color, QColor) and self.__colorFg != color:
            self.__colorFg = color
            self.applyUpdate('colorFg')

    def colorBg(self):
        """Return background color"""
        return self.__colorBg

    def setColorBg(self, color):
        """Set brush background color"""
        if color == '':
            color = None
        elif isinstance(color, str):
            try:
                color = QColor(color)
            except Exception:
                return

        if color is None or isinstance(color, QColor) and self.__colorBg != color:
            self.__colorBg = color
            self.applyUpdate('colorBg')

    def colorGradient(self):
        """Return gradient color"""
        return self.__colorGradient

    def setColorGradient(self, managedResource):
        """Set gradient color"""
        global _bbsManagedResourcesGradients

        managedResource = _bbsManagedResourcesGradients.getResource(managedResource)

        if managedResource is None or isinstance(managedResource, ManagedResource):
            if self.__colorGradient is None and managedResource is not None or self.__colorGradient != managedResource:
                self.__colorGradient = managedResource
                self.applyUpdate('colorGradient')

    def eraserMode(self):
        """Return eraser mode"""
        return self.__eraserMode

    def setEraserMode(self, eraserMode):
        """Set eraser mode"""
        if isinstance(eraserMode, bool) and self.__eraserMode != eraserMode and not self.__ignoreEraserMode:
            self.__eraserMode = eraserMode
            self.applyUpdate('eraserMode')

    def defaultPaintTool(self):
        """Return brush default Paint Tool"""
        return self.__defaultPaintTool

    def setDefaultPaintTool(self, defaultPaintTool):
        """Set brush default Paint Tool

        Default Paint Tool is activated when brush is selected
        """
        if defaultPaintTool is None or (defaultPaintTool in EKritaTools.list(EKritaToolsCategory.PAINT) and defaultPaintTool != self.__defaultPaintTool):
            self.__defaultPaintTool = defaultPaintTool
            self.applyUpdate('defaultPaintTool')

    def fingerPrint(self):
        """Return finger print for brush"""
        if self.__fingerPrint == '':
            hash = blake2b()

            hash.update(self.__name.encode())
            hash.update(struct.pack('!d', self.__size))
            hash.update(struct.pack('!d', self.__flow))
            hash.update(struct.pack('!d', self.__opacity))
            hash.update(self.__blendingMode.encode())
            self.__fingerPrint = hash.hexdigest()

        return self.__fingerPrint

    def information(self, displayOption=0):
        """Return synthetised brush information (HTML)"""
        returned = ''
        if displayOption & BBSBrush.INFO_WITH_OPTIONS:
            returned = self.__brushNfoOptions

            if not(displayOption & BBSBrush.INFO_COMPACT) and self.__brushNfoComments != '':
                hr = ''
                if returned != '':
                    hr = "<tr><td colspan=3><hr></td></tr>"
                returned = f"<tr><td colspan=3>{self.__brushNfoComments}</td></tr>{hr}{returned}"

        if displayOption & BBSBrush.INFO_WITH_DETAILS:
            hr = ''
            if returned != '':
                hr = "<tr><td colspan=3><hr></td></tr>"

            if displayOption & BBSBrush.INFO_COMPACT:
                returned = f'<small><i><table>{self.__brushNfoShort}{hr}{returned}</table></i></small>'
            else:
                returned = f'<small><i><table>{self.__brushNfoFull}{hr}{returned}</table></i></small>'

            returned = f'<b>{self.__name.replace("_", " ")}</b>{returned}'
        else:
            returned = f'<b>{self.__name.replace("_", " ")}</b><small><i><table>{returned}</table></i></small>'

        if displayOption & BBSBrush.INFO_WITH_ICON and self.__brushNfoImg != '':
            returned = f'<table><tr><td>{self.__brushNfoImg}</td><td>{returned}</td></tr></table>'

        return returned

    def found(self):
        """Return True if brush preset exists in krita otherwise False"""
        return EKritaBrushPreset.found(self.__name)

    def kritaBrush(self):
        """Return Krita's brush if any, otherwise None"""
        return self.__kritaBrush

    def restoreKritaBrush(self, restoreColor=True, restorePaintTool=True):
        """Restore Return Krita's brush if any, otherwise does nothing"""
        if self.__kritaBrush:
            self.__kritaBrushIsRestoring = True
            self.__kritaBrush.toCurrentKritaBrush(None, restoreColor, restorePaintTool)
            self.__kritaBrushIsRestoring = False

    def shortcut(self):
        """Return brush shortcut"""
        return self.__shortcut

    def setShortcut(self, shortcut):
        """Set brush shortcut

        Shortcut is used as an information only to simplify management
        """
        if isinstance(shortcut, QKeySequence) and shortcut != self.__shortcut:
            self.__shortcut = shortcut
            self.applyUpdate('shortcut')

    def actionId(self):
        """Return id to use for an action for this brush"""
        return BBSSettings.brushActionId(self.id())

    def action(self):
        """Return Krita's action for this brush or none if not found"""
        return BBSSettings.brushAction(self.id())


class BBSGroup(BBSBaseNode):
    """A group definition"""
    KEY_NAME = 'name'
    KEY_COMMENTS = 'comments'
    KEY_COLOR = 'color'
    KEY_SHORTCUT_NEXT = 'shortcutNext'
    KEY_SHORTCUT_PREV = 'shortcutPrevious'
    KEY_EXPANDED = 'expanded'

    IMG_SIZE = 256

    def __init__(self, group=None):
        super(BBSGroup, self).__init__(None)

        self.__name = ''
        self.__comments = ''
        self.__color = WStandardColorSelector.COLOR_NONE
        self.__expanded = True
        self.__shortcutNext = QKeySequence()
        self.__shortcutPrevious = QKeySequence()

        self.__groupNfoFull = ''
        self.__groupNfoShort = ''
        self.__groupNfoOptions = ''
        self.__groupNfoComments = ''

        self.__imageOpen = None
        self.__imageClose = None

        self.__node = None

        if isinstance(group, BBSGroup):
            # clone group
            self.importData(group.exportData())
        elif isinstance(group, dict):
            self.importData(group)

    def __repr__(self):
        return f"<BBSGroup({self.id()}, '{self.__name}', '{self.position()}')>"

    def applyUpdate(self, property):
        """Emit updated signal when a property has been changed"""
        def yesno(value):
            if value:
                return i18n('Yes')
            else:
                return i18n('No')

        if not self.inUpdate():
            shortcutText = ''
            if not self.__shortcutNext.isEmpty():
                shortcutText += f' <tr><td align="left"><b>{i18n("Shortcut next")}</b></td><td align="right">{self.__shortcutNext.toString()}</td><td></td></tr>'

            if not self.__shortcutPrevious.isEmpty():
                shortcutText += f' <tr><td align="left"><b>{i18n("Shortcut previous")}</b></td><td align="right">{self.__shortcutPrevious.toString()}</td><td></td></tr>'

            self.__groupNfoOptions = shortcutText

            self.__groupNfoComments = self.__comments
            if self.__groupNfoComments != '':
                self.__groupNfoComments = re.sub("<(/)?body",
                                                 r"<\1div", re.sub("<!doctype[^>]+>|<meta[^>]+>|</?html>|</?head>", "", self.__groupNfoComments, flags=re.I),
                                                 flags=re.I)

            self.__groupNfoFull = ""
            self.__groupNfoShort = ""

        super(BBSGroup, self).applyUpdate(property)

    def acceptedChild(self):
        """Return a list of allowed children types

        Return empty list if node don't accept childs
        """
        return (BBSBrush, BBSGroup)

    def exportData(self):
        """Export group definition as dictionary"""
        returned = {
                BBSGroup.KEY_NAME: self.__name,
                BBSBrush.KEY_POSITION: self.position(),
                BBSGroup.KEY_COMMENTS: self.__comments,
                BBSGroup.KEY_COLOR: self.__color,
                BBSGroup.KEY_UUID: self.id(),
                BBSGroup.KEY_SHORTCUT_NEXT: self.__shortcutNext.toString(),
                BBSGroup.KEY_SHORTCUT_PREV: self.__shortcutPrevious.toString(),
                BBSGroup.KEY_EXPANDED: self.__expanded
            }

        return returned

    def importData(self, value):
        """Import group definition from dictionary"""
        if not isinstance(value, dict):
            return False

        self.beginUpdate()

        try:
            if BBSGroup.KEY_UUID in value:
                self._setId(value[BBSGroup.KEY_UUID])
            if BBSGroup.KEY_POSITION in value:
                self.setPosition(value[BBSGroup.KEY_POSITION])
            if BBSGroup.KEY_NAME in value:
                self.setName(value[BBSGroup.KEY_NAME])
            if BBSGroup.KEY_COMMENTS in value:
                self.setComments(value[BBSGroup.KEY_COMMENTS])
            if BBSGroup.KEY_COLOR in value:
                self.setColor(value[BBSGroup.KEY_COLOR])
            if BBSGroup.KEY_EXPANDED in value:
                self.setExpanded(value[BBSGroup.KEY_EXPANDED])

            actionNext = self.actionNext()
            if actionNext and actionNext.shortcut():
                self.setShortcutNext(actionNext.shortcut())

            actionPrevious = self.actionPrevious()
            if actionPrevious and actionPrevious.shortcut():
                self.setShortcutPrevious(actionPrevious.shortcut())

            isValid = True
        except Exception as e:
            print("Unable to import group definition:", e)
            isValid = False

        self.endUpdate()
        return isValid

    def name(self):
        """Return group name"""
        return self.__name

    def setName(self, value):
        """Set name"""
        if value != self.__name:
            self.__name = value
            self.__fingerPrint = ''
            self.applyUpdate('name')

    def comments(self):
        """Return current comment for group"""
        return self.__comments

    def setComments(self, value):
        """Set current comment for group"""
        if value != self.__comments:
            if stripHtml(value).strip() != '':
                self.__comments = value
            else:
                self.__comments = ''
            self.applyUpdate('comments')

    def color(self):
        """Return color"""
        return self.__color

    def setColor(self, color):
        """Set group color"""
        if WStandardColorSelector.isValidColorIndex(color) and self.__color != color:
            self.__color = color

            # need to build images according to colors
            pixmapOpen = buildIcon('pktk:folder__filled_open').pixmap(QSize(BBSGroup.IMG_SIZE, BBSGroup.IMG_SIZE))
            painterOpen = QPainter()
            painterOpen.begin(pixmapOpen)
            if self.__color != WStandardColorSelector.COLOR_NONE:
                painterOpen.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                painterOpen.fillRect(0, 0, BBSGroup.IMG_SIZE, BBSGroup.IMG_SIZE, WStandardColorSelector.getColor(self.__color))
            painterOpen.end()
            self.__imageOpen = pixmapOpen.toImage()

            pixmapClose = buildIcon('pktk:folder__filled_close').pixmap(QSize(BBSGroup.IMG_SIZE, BBSGroup.IMG_SIZE))
            painterClose = QPainter()
            painterClose.begin(pixmapClose)
            if self.__color != WStandardColorSelector.COLOR_NONE:
                painterClose.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                painterClose.fillRect(0, 0, BBSGroup.IMG_SIZE, BBSGroup.IMG_SIZE, WStandardColorSelector.getColor(self.__color))
            painterClose.end()
            self.__imageClose = pixmapClose.toImage()

            self.applyUpdate('color')

    def expanded(self):
        """Return if group is expanded or not"""
        return self.__expanded

    def setExpanded(self, expanded):
        """Set if if group is expanded or not"""
        if isinstance(expanded, bool) and expanded != self.__expanded:
            self.__expanded = expanded
            self.applyUpdate('expanded')

    def shortcutNext(self):
        """Return group shortcut"""
        return self.__shortcutNext

    def setShortcutNext(self, shortcut):
        """Set group shortcut

        Shortcut is used as an information only to simplify management
        """
        if isinstance(shortcut, QKeySequence) and shortcut != self.__shortcutNext:
            self.__shortcutNext = shortcut
            self.applyUpdate('shortcutNext')

    def shortcutPrevious(self):
        """Return group shortcut"""
        return self.__shortcutPrevious

    def setShortcutPrevious(self, shortcut):
        """Set group shortcut

        Shortcut is used as an information only to simplify management
        """
        if isinstance(shortcut, QKeySequence) and shortcut != self.__shortcutPrevious:
            self.__shortcutPrevious = shortcut
            self.applyUpdate('shortcutPrevious')

    def actionNextId(self):
        """Return id to use for an action for this group"""
        return BBSSettings.groupActionId(self.id(), 'N')

    def actionNext(self):
        """Return Krita's action for this group or none if not found"""
        return BBSSettings.groupAction(self.id(), 'N')

    def actionPreviousId(self):
        """Return id to use for an action for this group"""
        return BBSSettings.groupActionId(self.id(), 'P')

    def actionPrevious(self):
        """Return Krita's action for this group or none if not found"""
        return BBSSettings.groupAction(self.id(), 'P')

    def information(self, displayOption=0):
        """Return synthetised brush information (HTML)"""
        returned = ''
        if displayOption & BBSGroup.INFO_WITH_OPTIONS:
            returned = self.__groupNfoOptions

            if not(displayOption & BBSBrush.INFO_COMPACT) and self.__groupNfoComments != '':
                hr = ''
                if returned != '':
                    hr = "<tr><td colspan=3><hr></td></tr>"
                returned = f"<tr><td colspan=3>{self.__groupNfoComments}</td></tr>{hr}{returned}"

        if displayOption & BBSGroup.INFO_WITH_DETAILS and returned != '':
            returned = f'<small><i><table>{returned}</table></i></small>'

        returned = f'<b>{self.__name}</b>{returned}'

        return returned

    def image(self, expandedStatus=None):
        """Return image for group

        if expandedStatus is none, return image according to expanded/collapsed status
        if expandedStatus is True, return image for exapanded status, otherwise return image for collapsed status
        """
        if expandedStatus is None:
            expandedStatus = self.expanded()

        if expandedStatus:
            return self.__imageOpen
        else:
            return self.__imageClose


class BBSModelNode(QStandardItem):
    """A node for BBSModel"""

    def __init__(self, data, parent=None):
        if parent is not None and not isinstance(parent, BBSModelNode):
            raise EInvalidType("Given `parent` must be a <BBSModelNode>")
        elif not isinstance(data, BBSBaseNode):
            raise EInvalidType("Given `data` must be a <BBSBaseNode>")

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

        return f"<BBSModelNode(parent:{parent}, data:{data}, childs({len(self.__childNodes)}):{self.__childNodes})>"

    def beginUpdate(self):
        self.__inUpdate += 1

    def endUpdate(self):
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
        """Add a new child """
        if isinstance(childNode, list):
            self.beginUpdate()
            for childNodeToAdd in childNode:
                self.appendChild(childNodeToAdd)
            self.endUpdate()
        elif not isinstance(childNode, BBSModelNode):
            raise EInvalidType("Given `childNode` must be a <BBSModelNode>")
        elif isinstance(childNode.data(), self.__dataNode.acceptedChild()):
            self.beginUpdate()
            self.__childNodes.append(childNode)
            self.endUpdate()

    def removeChild(self, childNode):
        """Remove a child
        Removed child is returned
        Or None if child is not found
        """
        if isinstance(childNode, list):
            returned = []
            self.beginUpdate()
            for childNodeToRemove in childNode:
                returned.append(self.removeChild(childNodeToRemove))
            self.__endUpdate()
            return returned
        elif not isinstance(childNode, (int, BBSModelNode)):
            raise EInvalidType("Given `childNode` must be a <BBSModelNode> or <int>")
        else:
            self.beginUpdate()
            try:
                if isinstance(childNode, BBSModelNode):
                    returned = self.__childNodes.pop(self.__childNodes.index(childNode))
                else:
                    # row number provided
                    returned = self.__childNodes.pop(childNode)
            except Exception:
                returned = None

            self.endUpdate()
            return returned

    def insertChild(self, position, childNode):
        row = 0
        for i, child in enumerate(self.__childNodes):
            if child.data().position() >= position:
                row = i - 1
                break
        self.__childNodes.insert(row, childNode)
        childNode.beginUpdate()
        childNode.data().setPosition(position)
        childNode.setParentNode(self)
        childNode.endUpdate()

    def remove(self):
        """Remove item from parent"""
        if self.__parentNode:
            self.__parentNode.removeChild(self)

    def clear(self):
        """Remove all childs"""
        self.beginUpdate()
        self.__childNodes = []
        self.endUpdate()

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
        if not isinstance(data, BBSBaseNode):
            raise EInvalidType("Given `data` must be a <BBSBaseNode>")
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
        if parent is None or isinstance(parent, BBSModelNode):
            self.__parentNode = parent

    def level(self):
        if self.__parentNode:
            return 1 + self.__parentNode.level()
        return 0

    def childStats(self):
        """return child statistics:
            - number of groups/sub-groups
            - number of brushes/sub-brushes
        """
        returned = {
                'groups': 0,
                'brushes': 0
            }

        if len(self.__childNodes):
            for child in self.__childNodes:
                data = child.data()

                if isinstance(data, BBSBrush):
                    returned['brushes'] += 1
                else:
                    returned['groups'] += 1

                    stats = child.childStats()
                    returned['brushes'] += stats['brushes']
                    returned['groups'] += stats['groups']
        return returned


class BBSModel(QAbstractItemModel):
    """A model to access brush and groups in an hierarchical tree"""
    updateWidth = Signal()

    HEADERS = ['Brush', 'Description']

    COLNUM_BRUSH = 0
    COLNUM_COMMENT = 1

    COLNUM_LAST = 1

    ROLE_ID = Qt.UserRole + 1
    ROLE_DATA = Qt.UserRole + 2
    ROLE_NODE = Qt.UserRole + 3
    ROLE_DND = Qt.UserRole + 4

    TYPE_BRUSH = 0b01
    TYPE_GROUP = 0b10

    MIME_DATA = 'x-application/pykrita-bbs-plugin-dnd-modelindex'

    def __init__(self, parent=None):
        """Initialise data model"""
        super(BBSModel, self).__init__(parent)

        self.__rootNode = BBSModelNode(BBSGroup({BBSGroup.KEY_UUID: "00000000-0000-0000-0000-000000000000",
                                                 BBSGroup.KEY_NAME: "root node"
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
        """Build internal dictionnary of all brushes/groups id

        key = id
        value = index
        """
        def getIdIndexes(parent):
            for childRow in range(parent.childCount()):
                child = parent.child(childRow)
                data = child.data()

                if isinstance(data, BBSBrush):
                    self.__idIndexes[data.id()] = BBSModel.TYPE_BRUSH
                else:
                    self.__idIndexes[data.id()] = BBSModel.TYPE_GROUP

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
        return super(BBSModel, self).flags(index) | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        """Model accept move of items only"""
        return Qt.MoveAction

    def supportedDragActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        """return mime type managed by treeview"""
        return [BBSModel.MIME_DATA]

    def mimeData(self, indexes):
        """Encode current node memory address to mime data"""
        nodes = [id(self.nodeForIndex(index)) for index in indexes if index.column() == 0]

        mimeData = QMimeData()
        mimeData.setData(BBSModel.MIME_DATA, json.dumps(nodes).encode())
        return mimeData

    def dropMimeData(self, mimeData, action, row, column, newParent):
        """User drop a group/brush on view

        Need to process it: move item(s) from source to target
        """
        if action != Qt.MoveAction:
            return False

        if not mimeData.hasFormat(BBSModel.MIME_DATA):
            return False

        idList = json.loads(bytes(mimeData.data(BBSModel.MIME_DATA)).decode())

        newParentNode = self.nodeForIndex(newParent)
        if not newParentNode:
            return False

        # take current target position to determinate new position for items
        targetPosition = newParentNode.data().position()
        if newParentNode.dndOver() == QAbstractItemView.AboveItem:
            positionUpdate = -1
            # above a BBSGroup ==> need to get group parent
            # above a BBSBrush ==> need to get brush parent
            targetParentNode = newParentNode.parentNode()
            targetParentIndex = self.parent(newParent)
            row = newParentNode.row()
        else:
            positionUpdate = 1
            # below a BBSGroup ==> BBSGroup is the parent
            # below a BBSBrush ==> need to get brush parent
            if isinstance(newParentNode.data(), BBSBrush):
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
        targetParentNode.beginUpdate()
        for numDataId, nodeDataId in enumerate(idList):
            itemNode = ctypes.cast(nodeDataId, ctypes.py_object).value

            newPosition = targetPosition + positionUpdate * (numDataId+1)

            # remove from old position
            self.removeNode(itemNode)

            self.beginInsertRows(targetParentIndex, row, row)
            targetParentNode.insertChild(newPosition, itemNode)
            self.endInsertRows()

            row += positionUpdate

        targetParentNode.endUpdate()
        self.__endUpdate()

        return True

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column for index"""
        return BBSModel.COLNUM_LAST+1

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

        if role == BBSModel.ROLE_NODE:
            return item

        data = item.data()  # get BBSBrush or BBSGroup

        if role == BBSModel.ROLE_ID:
            return data.id()
        elif role == BBSModel.ROLE_DATA:
            return data
        elif role == Qt.DisplayRole:
            column = index.column()
            if column == BBSModel.COLNUM_BRUSH:
                return data.name()
            elif column == BBSModel.COLNUM_COMMENT:
                return data.comments()

        column = index.column()
        row = index.row()

        if isinstance(data, BBSBrush):
            if role == Qt.DecorationRole:
                image = data.image()
                if image:
                    # QIcon
                    return QIcon(QPixmap.fromImage(image))
                else:
                    return BBSModel.buildIcon('pktk:warning')
            elif role == Qt.ToolTipRole:
                if not data.found():
                    return i18n(f"Brush <i><b>{data.name()}</b></i> is not installed and/or activated on this Krita installation")
                else:
                    return data.information(BBSBrush.INFO_WITH_DETAILS | BBSBrush.INFO_WITH_OPTIONS)
        elif isinstance(data, BBSGroup):
            if role == Qt.DecorationRole:
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
        if isinstance(node, BBSModelNode):
            row = node.row()
            index = self.createIndex(row, 0, node)
            self.beginRemoveRows(self.parent(index), row, row)
            node.parentNode().removeChild(row)
            self.endRemoveRows()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return label for given data section"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section > 0:
            return BBSModel.HEADERS[section]
        return None

    def itemSelection(self, item):
        """Return QItemSelection for given item"""
        returned = QItemSelection()

        if isinstance(item, BBSBaseNode):
            index = self.__getIdIndex(item.id())
            if index.isValid():
                indexS = self.createIndex(index.row(), 0)
                indexE = self.createIndex(index.row(), BBSModel.COLNUM_LAST)
                returned = QItemSelection(indexS, indexE)

        return returned

    def idIndexes(self, options={}):
        """Return a dictionnary of all brushes/groups id

        key = id
        value = index

        Given `options` is a dict that can contains
            'brushes': True         # if True (default), result contains brushes Id
            'groups': True          # if True (default), result contains groups Id
        """
        if 'brushes' not in options:
            options['brushes'] = True
        if 'groups' not in options:
            options['groups'] = True
        if 'asIndex' not in options:
            options['asIndex'] = True

        if not isinstance(options['brushes'], bool):
            raise EInvalidType("Given `option['brushes'] must be a <bool>")
        if not isinstance(options['groups'], bool):
            raise EInvalidType("Given `option['groups'] must be a <bool>")
        if not isinstance(options['asIndex'], bool):
            raise EInvalidType("Given `option['asIndex'] must be a <bool>")

        self.__updateIdIndex()

        if not (options['brushes'] or options['groups']):
            # nonsense but...
            return {}
        elif options['brushes'] and options['groups']:
            # return everything
            returned = [id for id in self.__idIndexes]
        elif options['brushes']:
            # return brushes
            returned = [id for id in self.__idIndexes if self.__idIndexes[id] == BBSModel.TYPE_BRUSH]
        elif options['groups']:
            # return groups
            returned = [id for id in self.__idIndexes if self.__idIndexes[id] == BBSModel.TYPE_GROUP]
        else:
            # should not occurs
            return {}

        if options['asIndex']:
            return {id: self.__getIdIndex(id) for id in returned}
        else:
            return {id: self.__idIndexes[id] for id in returned}

    def getFromId(self, id, asIndex=True):
        """Return brush/group from given Id

        Return None if not found
        """
        index = self.__getIdIndex(id)
        if index.isValid():
            if asIndex:
                return index
            else:
                return self.data(index, BBSModel.ROLE_DATA)
        else:
            return None

    def getGroupItems(self, groupId=None, asIndex=True):
        """Return items from given `groupId`

        If `groupId` is None, return items from root
        If `groupId` is not found, return empty list

        If `asIndex` is True, return items as QModelIndex otherwise return BBSGroup/BBSBrush
        """
        returned = []
        node = None
        self.__updateIdIndex()

        if groupId is None:
            node = self.__rootNode
        elif isinstance(groupId, str):
            index = self.__getIdIndex(groupId)
            if index.isValid():
                data = self.data(index, BBSModel.ROLE_DATA)
                if isinstance(data, BBSGroup) and data.id() == groupId:
                    node = self.data(index, BBSModel.ROLE_NODE)
        elif isinstance(groupId, BBSGroup):
            return self.getGroupItems(groupId.id(), asIndex)

        if node is not None:
            # get all data, maybe not ordered
            returned = [childNode.data() for childNode in node.childs()]
            returned.sort(key=lambda item: item.position())

            if asIndex:
                returned = [self.__getIdIndex(item.id()) for item in returned]
        return returned

    def clear(self):
        """Clear all brushes & groups"""
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
        elif isinstance(itemToRemove, BBSModelNode):
            # a node
            self.__beginUpdate()
            self.removeNode(itemToRemove)
            self.__endUpdate()
        elif isinstance(itemToRemove, str):
            # a string --> assume it's an Id
            index = self.getFromId(itemToRemove)
            if index is not None:
                self.remove(self.data(index, BBSModel.ROLE_NODE))
        elif isinstance(itemToRemove, BBSBaseNode):
            self.remove(itemToRemove.id())

    def add(self, itemToAdd, parent=None):
        """Add item to parent

        If parent is None, item is added to rootNode
        """
        if parent is None:
            parent = self.__rootNode

        if isinstance(parent, BBSModelNode):
            if isinstance(itemToAdd, list):
                # a list of item to add
                self.__beginUpdate()
                for item in itemToAdd:
                    self.add(item, parent)
                self.__endUpdate()
            elif isinstance(itemToAdd, BBSBaseNode):
                if isinstance(itemToAdd, parent.data().acceptedChild()):
                    self.__beginUpdate()
                    parent.appendChild(BBSModelNode(itemToAdd, parent))
                    self.__endUpdate()
        elif isinstance(parent, str):
            # a string --> assume it's an Id
            index = self.getFromId(parent)
            if index is not None:
                self.add(itemToAdd, self.data(index, BBSModel.ROLE_NODE))
        elif isinstance(parent, BBSBaseNode):
            self.add(itemToAdd, parent.id())

    def update(self, itemToUpdate):
        print("TODO: BBSModel.update()", itemToUpdate)

    def importData(self, brushesAndGroups, nodes):
        """Load model from:
        - brushes (list of BBSBrush)
        - groups (list of BBSGroup)
        - nodes (list defined hierarchy)
            [id, id, (id, [id, id, (id, [id])])]
        """
        def addNodes(idList, parent):
            toAdd = []
            for id in idList:
                if isinstance(id, str):
                    if id in tmpIdIndex:
                        node = BBSModelNode(tmpIdIndex[id], parent)
                        toAdd.append(node)
                    else:
                        raise EInvalidValue(f"Given `id` ({id}) can't be added, index not exist")
                elif isinstance(id, (tuple, list)):
                    # a group
                    groupNode = BBSModelNode(tmpIdIndex[id[0]], parent)
                    addNodes(id[1], groupNode)
                    toAdd.append(groupNode)
                else:
                    raise EInvalidValue(f"Given `id` must be a valid <str>")
            parent.appendChild(toAdd)

        self.beginResetModel()
        self.__beginUpdate()
        self.clear()
        # a dictionary id => BBSBaseNode
        tmpIdIndex = {brushOrGroup.id(): brushOrGroup for brushOrGroup in brushesAndGroups}

        if len(nodes) == 0:
            # in this case (probably from a previous version of BBS, create everything at root level
            nodes = list(tmpIdIndex.keys())

        addNodes(nodes, self.__rootNode)
        self.__endUpdate()
        self.endResetModel()

    def exportData(self):
        """export model as dict
            {
                'brushes': list of BBSBrush
                'groups':  list of BBSGroup
                'nodes':   list defined hierarchy
                               [id, id, (id, [id, id, (id, [id])])]
            }
        """
        def export(parent, returned):
            nodes = []
            for childRow in range(parent.childCount()):
                child = parent.child(childRow)
                data = child.data()

                if isinstance(data, BBSBrush):
                    returned['brushes'].append(data)
                    nodes.append(data.id())
                else:
                    returned['groups'].append(data)
                    nodes.append((data.id(), export(child, returned)))
            return nodes

        returned = {
                'brushes': [],
                'groups': [],
                'nodes': []
            }

        returned['nodes'] = export(self.__rootNode, returned)

        return returned


class BBSWBrushesTv(QTreeView):
    """Tree view groups&brushes"""
    focused = Signal()
    keyPressed = Signal(int)
    iconSizeIndexChanged = Signal(int, QSize)

    def __init__(self, parent=None):
        super(BBSWBrushesTv, self).__init__(parent)
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

        self.__delegate = BBSModelDelegateTv(self)
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

        for index in self.__model.idIndexes({'brushes': False, 'asIndex': True}).values():
            self.setExpanded(index, index.data(BBSModel.ROLE_DATA).expanded())

        self.__selectedBeforeReset = []

    def __sectionResized(self, index, oldSize, newSize):
        """When section is resized, update rows height"""
        if index == BBSModel.COLNUM_COMMENT and not self.isColumnHidden(BBSModel.COLNUM_COMMENT):
            # update height only if comment section is resized
            self.__delegate.setCSize(newSize)
            for rowNumber in range(self.__model.rowCount()):
                # need to recalculate height for all rows
                self.__delegate.sizeHintChanged.emit(self.__model.createIndex(rowNumber, index))

    def __setDndOverIndex(self, index, position=None):
        """Set given index as current d'n'd index"""
        if self.__dndOverIndex is not None and self.__dndOverIndex != index:
            # remove indicator on index
            node = self.model().data(self.__dndOverIndex, BBSModel.ROLE_NODE)
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

            node = self.model().data(index, BBSModel.ROLE_NODE)
            if node:
                node.setDndOver(indicatorPosition)

        self.__dndOverIndex = index

        # needed to erase previous d'n'd over indicator
        self.viewport().update()

    def mouseDoubleClickEvent(self, event):
        """Manage double-click on Groups to expand/collapse and keep state in model"""
        index = self.indexAt(event.pos())
        data = index.data(BBSModel.ROLE_DATA)
        if isinstance(data, BBSGroup) and index.column() == BBSModel.COLNUM_BRUSH:
            newExpandedState = not self.isExpanded(index)
            data.setExpanded(newExpandedState)
            self.setExpanded(index, newExpandedState)
        super(BBSWBrushesTv, self).mouseDoubleClickEvent(event)

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
            super(BBSWBrushesTv, self).wheelEvent(event)

    def dropEvent(self, event):
        """TODO: needed?"""
        super(BBSWBrushesTv, self).dropEvent(event)
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
        (then delegated to BBSModelDelegateTv)

        Note: when calling setDropIndicatorShown(False), it seems drag'n'drop is disabled
              so can't use this just to remove ugly dnd rectangle
        """
        painter = QPainter(self.viewport())
        self.drawTree(painter, event.region())

    def resizeColumns(self):
        """Resize columns"""
        minColSize = self.sizeHintForColumn(BBSModel.COLNUM_BRUSH)
        if self.columnWidth(BBSModel.COLNUM_BRUSH) < minColSize:
            self.setColumnWidth(BBSModel.COLNUM_BRUSH, minColSize)

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
        if isinstance(model, BBSModel):
            self.__model = model
        else:
            raise EInvalidType("Given `model` must be <BBSModel>")

        super(BBSWBrushesTv, self).setModel(self.__model)

        # set colums size rules
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(BBSModel.COLNUM_BRUSH, QHeaderView.Interactive)
        header.setSectionResizeMode(BBSModel.COLNUM_COMMENT, QHeaderView.Stretch)

        self.__model.updateWidth.connect(self.resizeColumns)
        self.__model.modelAboutToBeReset.connect(self.__modelAboutToBeReset)
        self.__model.modelReset.connect(self.__modelReset)

        # when model is set, consider there's a reset
        self.__modelReset()

    def selectItem(self, item):
        """Select given item"""
        if isinstance(item, BBSBaseNode):
            itemSelection = self.__model.itemSelection(item)
            self.selectionModel().select(itemSelection, QItemSelectionModel.ClearAndSelect)

    def selectedItems(self):
        """Return a list of selected groups/brushes items"""
        returned = []
        if self.selectionModel():
            for selectedItem in self.selectionModel().selectedRows(BBSModel.COLNUM_BRUSH):
                item = selectedItem.data(BBSModel.ROLE_DATA)
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
            self.update()



class BBSWBrushesLv(QListView):
    """List view groups&brushes"""
    focused = Signal()
    keyPressed = Signal(int)
    iconSizeIndexChanged = Signal(int, QSize)

    def __init__(self, parent=None):
        super(BBSWBrushesLv, self).__init__(parent)
        self.setAutoScroll(True)
        self.setViewMode(QListView.IconMode)

        self.__parent = parent
        self.__model = None
        self.__selectedBeforeReset = []
        self.__fontSize = self.font().pointSizeF()
        if self.__fontSize == -1:
            self.__fontSize = -self.font().pixelSize()

        self.__iconSize = IconSizes([32, 64, 96, 128, 192])
        self.setIconSizeIndex(3)

    def __modelAboutToBeReset(self):
        """model is about to be reset"""
        self.__selectedBeforeReset = self.selectedItems()

    def __modelReset(self):
        """model has been reset"""
        for selectedItem in self.__selectedBeforeReset:
            self.selectItem(selectedItem)

        self.__selectedBeforeReset = []

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
            super(BBSWBrushesLv, self).wheelEvent(event)

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            self.setIconSize(self.__iconSize.value(True))
            self.iconSizeIndexChanged.emit(self.__iconSize.index(), self.__iconSize.value(True))

    def setModel(self, model):
        """Initialise treeview header & model"""
        if isinstance(model, BBSModel):
            self.__model = model
        else:
            raise EInvalidType("Given `model` must be <BBSModel>")

        super(BBSWBrushesLv, self).setModel(self.__model)

        self.__model.modelAboutToBeReset.connect(self.__modelAboutToBeReset)
        self.__model.modelReset.connect(self.__modelReset)

    def selectItem(self, item):
        """Select given item"""
        if isinstance(item, BBSBrush):
            itemSelection = self.__model.itemSelection(item)
            self.selectionModel().select(itemSelection, QItemSelectionModel.ClearAndSelect)

    def selectedItems(self):
        """Return a list of selected brushes items"""
        returned = []
        if self.selectionModel():
            for item in self.selectionModel().selectedIndexes():
                brush = item.data(BBSModel.ROLE_DATA)
                if brush is not None:
                    returned.append(brush)
        return returned

    def nbSelectedItems(self):
        """Return number of selected items"""
        return len(self.selectedItems())


class BBSModelDelegateTv(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build improved rendering items for BBSWBrushesTv treeview"""
    MARGIN_TEXT = 8
    TEXT_WIDTH_FACTOR = 1.5
    DND_PENWIDTH = [2, 6, 10, 12, 12]

    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(BBSModelDelegateTv, self).__init__(parent)
        self.__csize = 0
        self.__compactSize = False

        self.__noPen = QPen(Qt.NoPen)
        self.__iconMargins = QMarginsF()
        self.__iconSize = 0
        self.__iconLevelOffset = 0
        self.__iconQSizeF = QSize()
        self.__iconAndMarginSize = 0

        colorBrush = QApplication.palette().color(QPalette.Highlight)
        colorBrush.setAlpha(127)
        self.__dndMarkerBrush = QBrush(colorBrush)
        self.__dndMarkerBrushSize = 4

    def __getInformation(self, item):
        """Return text for group/brush information"""
        compactSize = 0
        if self.__compactSize:
            compactSize = BBSBaseNode.INFO_COMPACT
        textDocument = QTextDocument()
        textDocument.setHtml(item.information(BBSBaseNode.INFO_WITH_DETAILS | compactSize))
        return textDocument

    def __getOptionsInformation(self, item):
        """Return text for group/brush options (comments + option)"""
        compactSize = 0
        if self.__compactSize:
            compactSize = BBSBaseNode.INFO_COMPACT

        textDocument = QTextDocument()
        textDocument.setHtml(item.information(BBSBaseNode.INFO_WITH_OPTIONS | compactSize))
        cursor = QTextCursor(textDocument)

        return textDocument

    def setCompactSize(self, value):
        """Activate/deactivate compact size"""
        self.__compactSize = value

    def setIconSize(self, value):
        """define icone size"""
        if self.__iconSize != value:
            self.__iconSize = value
            self.__iconLevelOffset = self.__iconSize//3
            self.__iconQSizeF = QSizeF(self.__iconSize, self.__iconSize)
            self.__iconAndMarginSize = QSize(self.__iconSize + BBSModelDelegateTv.MARGIN_TEXT, BBSModelDelegateTv.MARGIN_TEXT)

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
                    if isinstance(data, BBSGroup):
                        rect = dndRect
                    else:
                        rect = QRect(QPoint(dndRect.left(), dndRect.bottom() - self.__dndMarkerBrushSize), dndRect.bottomRight())
                    painter.fillRect(rect, self.__dndMarkerBrush)

        if option.state & QStyle.State_HasFocus == QStyle.State_HasFocus:
            # remove focus style if active
            option.state = option.state & ~QStyle.State_HasFocus

        if index.column() == BBSModel.COLNUM_BRUSH:
            # render group/brush information
            self.initStyleOption(option, index)

            # item: Node
            item = index.data(BBSModel.ROLE_NODE)
            # data: BBSBrush or BBSGroup
            data = item.data()

            # Initialise painter
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            # calculate sizes and positions
            iconOffset = int((item.level() - 1) * self.__iconLevelOffset)
            textOffset = iconOffset + self.__iconSize + BBSModelDelegateTv.MARGIN_TEXT
            bgRect = QRectF(option.rect.topLeft() + QPointF(iconOffset, 0), self.__iconQSizeF).marginsRemoved(self.__iconMargins)
            bgRect.setHeight(bgRect.width())
            bRadius = max(2, self.__iconSize * 0.050)
            rectTxt = QRectF(option.rect.left() + textOffset, option.rect.top()+4, option.rect.width()-4-textOffset, option.rect.height()-1)

            # Initialise pixmap (brush icon or folder icon)
            pixmap = None
            if isinstance(data, BBSBrush):
                if not data.found():
                    if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                        option.state &= ~QStyle.State_Selected
                    painter.fillRect(option.rect, warningAreaBrush())
                    # unable to get brush? return warning icon instead
                    pixmap = buildIcon('pktk:warning').pixmap(bgRect.size().toSize())
                else:
                    # brush icon is resized & border are rounded
                    pixmap = roundedPixmap(QPixmap.fromImage(data.image()), bRadius, bgRect.size().toSize())
            else:
                # group icon: folder
                pixmap = QPixmap.fromImage(data.image()).scaled(bgRect.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            if dndOver := item.dndOver():
                paintDndMarker(item.data(), dndOver, QRect(option.rect.topLeft() + QPoint(iconOffset, 0), option.rect.size() + QSize(-iconOffset, 0)))

            # draw icon
            painter.drawPixmap(bgRect.topLeft(), pixmap)

            # draw text
            textDocument = self.__getInformation(data)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(rectTxt.size())

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0, 0), rectTxt.size()))

            painter.restore()
            return
        elif index.column() == BBSModel.COLNUM_COMMENT:
            # render comment
            self.initStyleOption(option, index)

            # item: Node
            item = index.data(BBSModel.ROLE_NODE)
            # data: BBSBrush or BBSGroup
            data = item.data()
            rectTxt = QRect(option.rect.left(), option.rect.top(), option.rect.width(), option.rect.height())

            textDocument = self.__getOptionsInformation(data)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.save()

            if isinstance(data, BBSBrush):
                if not data.found():
                    if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                        option.state &= ~QStyle.State_Selected
                    painter.fillRect(option.rect, warningAreaBrush())

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

        QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """Calculate size for items"""
        size = QStyledItemDelegate.sizeHint(self, option, index)

        if index.column() == BBSModel.COLNUM_BRUSH:
            node = index.data(BBSModel.ROLE_NODE)
            textDocument = self.__getInformation(node.data())
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(4096, 1000))  # set 1000px size height arbitrary
            textDocument.setPageSize(QSizeF(textDocument.idealWidth() * BBSModelDelegateTv.TEXT_WIDTH_FACTOR, 1000))  # set 1000px size height arbitrary
            size = textDocument.size().toSize() + self.__iconAndMarginSize + QSize((node.level() - 1) * self.__iconLevelOffset, 0)
            if size.height() < self.__iconSize:
                # at least height must be icon size
                size.setHeight(self.__iconSize)
        elif index.column() == BBSModel.COLNUM_COMMENT:
            # size for comments cell (width is forced, calculate height of rich text)
            item = index.data(BBSModel.ROLE_DATA)
            textDocument = self.__getOptionsInformation(item)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(self.__csize, 1000))  # set 1000px size height arbitrary
            size = QSize(self.__csize, textDocument.size().toSize().height())

        return size


class BBSBrushesEditor(EDialog):
    """A simple dialog box to edit brush properties"""
    @staticmethod
    def edit(title, brush):
        """Open a dialog box to edit brush"""
        global _bbsManagedResourcesGradients

        _bbsManagedResourcesGradients.updateResources()

        widget = QWidget()
        dlgBox = BBSBrushesEditor(title, brush, widget)

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            BBSSettings.setTxtColorPickerLayout(dlgBox.colorPickerLayoutTxt())
            BBSSettings.setBrushColorPickerLayoutFg(dlgBox.colorPickerLayoutBrushFg())
            BBSSettings.setBrushColorPickerLayoutBg(dlgBox.colorPickerLayoutBrushBg())

            BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_GRADIENT_VIEWMODE, dlgBox.gradientBtnViewMode())
            BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_GRADIENT_ZOOMLEVEL, dlgBox.gradientBtnIconSizeIndex())

            return dlgBox.options()
        else:
            return None

    def __init__(self, title, brush, parent=None):
        super(BBSBrushesEditor, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'bbsbrushedit.ui'), parent)

        self.__brush = brush

        self.__inSliderSpinBoxEvent = False
        self.__inColorUiChangeEvent = False

        self.lblBrushTitle.setText(f"{i18n('Brush')} - <i>{brush.name()}</i>")

        self.wtComments.setHtml(self.__brush.comments())
        self.wtComments.setToolbarButtons(WTextEdit.DEFAULT_TOOLBAR | WTextEditBtBarOption.STYLE_STRIKETHROUGH | WTextEditBtBarOption.STYLE_COLOR_BG)
        self.wtComments.setColorPickerLayout(BBSSettings.getTxtColorPickerLayout())

        self.kseShortcut.setKeySequence(brush.shortcut())
        self.kseShortcut.setClearButtonEnabled(True)
        self.kseShortcut.keySequenceCleared.connect(self.__shortcutModified)
        self.kseShortcut.editingFinished.connect(self.__shortcutModified)
        self.kseShortcut.keySequenceChanged.connect(self.__shortcutModified)

        self.lblBrushIcon.setPixmap(QPixmap.fromImage(brush.image()).scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.cbKeepUserModifications.setChecked(brush.keepUserModifications())

        self.tbResetBrushValues.clicked.connect(self.__resetBrushValues)

        try:
            maxValue = int(Krita.instance().readSetting('', 'maximumBrushSize', '1000'))
        except Exception:
            maxValue = 1000
        self.hsBrushSize.setScale(1000)
        self.hsBrushSize.setNaturalMin(10)
        self.hsBrushSize.setNaturalMax(100*maxValue)
        self.dsbBrushSize.setMaximum(maxValue)
        self.hsBrushSize.naturalValueChanged.connect(lambda v: self.__brushSizeChanged(v, False))
        self.dsbBrushSize.valueChanged[float].connect(lambda v: self.__brushSizeChanged(v, True))
        self.dsbBrushSize.setValue(brush.size())

        self.hsBrushOpacity.valueChanged.connect(lambda v: self.__brushOpacityChanged(v, False))
        self.dsbBrushOpacity.valueChanged[float].connect(lambda v: self.__brushOpacityChanged(v, True))
        self.dsbBrushOpacity.setValue(100*brush.opacity())

        self.hsBrushFlow.valueChanged.connect(lambda v: self.__brushFlowChanged(v, False))
        self.dsbBrushFlow.valueChanged[float].connect(lambda v: self.__brushFlowChanged(v, True))
        self.dsbBrushFlow.setValue(100*brush.flow())

        index = 0
        for catId in EKritaBlendingModes.categoriesIdList():
            self.cbBrushBlendingMode.addItem(EKritaBlendingModes.categoryName(catId), None)
            index += 1

            for bModeId in EKritaBlendingModes.categoryBlendingMode(catId):
                self.cbBrushBlendingMode.addItem(EKritaBlendingModes.blendingModeName(bModeId), bModeId)
                if bModeId == brush.blendingMode():
                    self.cbBrushBlendingMode.setCurrentIndex(index)
                index += 1

        model = self.cbBrushBlendingMode.model()
        for row in range(model.rowCount()):
            if self.cbBrushBlendingMode.itemData(row) is None:
                item = model.item(row, 0)
                item.setFlags(item.flags() & ~(Qt.ItemIsSelectable | Qt.ItemIsEnabled))
                font = item.font()
                font.setBold(True)
                font.setItalic(True)
                item.setFont(font)

        cbBrushBlendingModeItemDelegate = QStyledItemDelegate(self)
        self.cbBrushBlendingMode.setItemDelegate(cbBrushBlendingModeItemDelegate)
        self.cbBrushBlendingMode.currentIndexChanged.connect(lambda index: self.cbIgnoreEraserMode.setEnabled(self.cbBrushBlendingMode.currentData() != 'erase'))

        self.cbPreserveAlpha.setChecked(brush.preserveAlpha())

        self.cbIgnoreToolOpacity.setChecked(brush.ignoreToolOpacity())

        toolIdList = EKritaTools.list(EKritaToolsCategory.PAINT)
        for index, toolId in enumerate(toolIdList):
            self.cbDefaultPaintTools.addItem(EKritaTools.icon(toolId), EKritaTools.name(toolId), toolId)
            if toolId == brush.defaultPaintTool():
                self.cbDefaultPaintTools.setCurrentIndex(index)
        self.cbDefaultPaintTool.toggled.connect(self.cbDefaultPaintTools.setEnabled)
        self.cbDefaultPaintTool.setChecked(brush.defaultPaintTool() in toolIdList)
        self.cbDefaultPaintTools.setEnabled(self.cbDefaultPaintTool.isChecked())

        self.btUseSpecificColorFg.colorPicker().setOptionLayout(BBSSettings.getBrushColorPickerLayoutFg())
        self.btUseSpecificColorBg.colorPicker().setOptionLayout(BBSSettings.getBrushColorPickerLayoutBg())
        self.btUseSpecificColorFg.colorPicker().setOptionMenu(WColorPicker.OPTION_MENU_RGB |
                                                              WColorPicker.OPTION_MENU_CMYK |
                                                              WColorPicker.OPTION_MENU_HSV |
                                                              WColorPicker.OPTION_MENU_HSL |
                                                              WColorPicker.OPTION_MENU_CSSRGB |
                                                              WColorPicker.OPTION_MENU_COLCOMP |
                                                              WColorPicker.OPTION_MENU_COLWHEEL |
                                                              WColorPicker.OPTION_MENU_PALETTE |
                                                              WColorPicker.OPTION_MENU_UICOMPACT |
                                                              WColorPicker.OPTION_MENU_COLPREVIEW)
        self.btUseSpecificColorBg.colorPicker().setOptionMenu(WColorPicker.OPTION_MENU_RGB |
                                                              WColorPicker.OPTION_MENU_CMYK |
                                                              WColorPicker.OPTION_MENU_HSV |
                                                              WColorPicker.OPTION_MENU_HSL |
                                                              WColorPicker.OPTION_MENU_CSSRGB |
                                                              WColorPicker.OPTION_MENU_COLCOMP |
                                                              WColorPicker.OPTION_MENU_COLWHEEL |
                                                              WColorPicker.OPTION_MENU_PALETTE |
                                                              WColorPicker.OPTION_MENU_UICOMPACT |
                                                              WColorPicker.OPTION_MENU_COLPREVIEW)
        self.btUseSpecificColorFg.colorPicker().uiChanged.connect(self.__brushColorPickerUiChanged)
        self.btUseSpecificColorBg.colorPicker().uiChanged.connect(self.__brushColorPickerUiChanged)
        self.btUseSpecificColorBg.setNoneColor(True)

        self.btUseSpecificColorGradient.setManageNoneResource(True)
        self.btUseSpecificColorGradient.setManagedResourceType(ManagedResourceTypes.RES_GRADIENTS)
        self.btUseSpecificColorGradient.managedResourcesSelector().setViewMode(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_GRADIENT_VIEWMODE))
        self.btUseSpecificColorGradient.managedResourcesSelector().setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_GRADIENT_ZOOMLEVEL))

        if brush.blendingMode() != 'erase':
            # for eraser, eraser mode is ignored
            self.cbIgnoreEraserMode.setEnabled(True)
            self.cbIgnoreEraserMode.setChecked(brush.ignoreEraserMode())

            # for eraser brush, option is not available
            colorFg = brush.colorFg()
            colorBg = brush.colorBg()
            colorGradient = brush.colorGradient()

            if colorFg is None:
                # foreground color define if a specific color is used
                self.cbUseSpecificColor.setChecked(False)
                self.btUseSpecificColorFg.setVisible(False)
                self.btUseSpecificColorBg.setVisible(False)
                self.btUseSpecificColorGradient.setVisible(False)
            else:
                self.cbUseSpecificColor.setChecked(True)
                self.btUseSpecificColorFg.setVisible(True)
                self.btUseSpecificColorBg.setVisible(True)
                self.btUseSpecificColorGradient.setVisible(True)

            self.btUseSpecificColorFg.setColor(colorFg)
            self.btUseSpecificColorBg.setColor(colorBg)
            self.btUseSpecificColorGradient.setResource(colorGradient)

            self.cbUseSpecificColor.toggled.connect(self.__useSpecificColorChanged)
        else:
            self.cbIgnoreEraserMode.setEnabled(False)
            self.cbUseSpecificColor.setVisible(False)
            self.btUseSpecificColorFg.setVisible(False)
            self.btUseSpecificColorBg.setVisible(False)
            self.btUseSpecificColorGradient.setVisible(False)

        self.pbOk.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.setModal(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

    def __resetBrushValues(self):
        """Reset brush properties to default values"""
        # memorize brush
        currentBrush = BBSBrush()
        currentBrush.fromCurrentKritaBrush()

        # reset brush
        Krita.instance().action('reload_preset_action').trigger()

        resetBrush = BBSBrush()
        resetBrush.fromCurrentKritaBrush()

        # update brush ui properties
        self.dsbBrushSize.setValue(resetBrush.size())
        self.dsbBrushFlow.setValue(100*resetBrush.flow())
        self.dsbBrushOpacity.setValue(100*resetBrush.opacity())
        for index in range(self.cbBrushBlendingMode.count()):
            if self.cbBrushBlendingMode.itemData(index) == resetBrush.blendingMode():
                self.cbBrushBlendingMode.setCurrentIndex(index)
                break

        # restore brush
        currentBrush.toCurrentKritaBrush()

    def __useSpecificColorChanged(self, isChecked):
        """Checkbox state for cbUseSpecificColor has changed"""
        self.btUseSpecificColorFg.setVisible(isChecked)
        self.btUseSpecificColorBg.setVisible(isChecked)
        self.btUseSpecificColorGradient.setVisible(isChecked)

    def __brushSizeChanged(self, value, fromSpinBox=True):
        """Size has been changed, update slider/spinbox according to value and source"""
        if self.__inSliderSpinBoxEvent:
            # avoid infinite call
            return
        self.__inSliderSpinBoxEvent = True
        if fromSpinBox:
            # update Slider
            self.hsBrushSize.setNaturalValue(round(value * 100))
        else:
            # update spinbox
            self.dsbBrushSize.setValue(round(value / 100, 2))
        self.__inSliderSpinBoxEvent = False

    def __brushOpacityChanged(self, value, fromSpinBox=True):
        """Size has been changed, update slider/spinbox according to value and source"""
        if self.__inSliderSpinBoxEvent:
            # avoid infinite call
            return
        self.__inSliderSpinBoxEvent = True
        if fromSpinBox:
            # update Slider
            self.hsBrushOpacity.setValue(round(value * 100))
        else:
            # update spinbox
            self.dsbBrushOpacity.setValue(round(value / 100, 2))
        self.__inSliderSpinBoxEvent = False

    def __brushFlowChanged(self, value, fromSpinBox=True):
        """Size has been changed, update slider/spinbox according to value and source"""
        if self.__inSliderSpinBoxEvent:
            # avoid infinite call
            return
        self.__inSliderSpinBoxEvent = True
        if fromSpinBox:
            # update Slider
            self.hsBrushFlow.setValue(round(value * 100))
        else:
            # update spinbox
            self.dsbBrushFlow.setValue(round(value / 100, 2))
        self.__inSliderSpinBoxEvent = False

    def __setOkEnabled(self, value):
        """Enable/Disable OK button"""
        if isinstance(value, bool):
            self.pbOk.setEnabled(value)

    def __shortcutModified(self):
        """Shortcut value has been modified

        Check if valid
        """
        keySequence = self.kseShortcut.keySequence()
        if keySequence.isEmpty():
            self.__setOkEnabled(True)
            self.lblShortcutAlreadyUsed.setText('')
            self.lblShortcutAlreadyUsed.setStyleSheet('')
        else:
            # need to check if shortcut already exists or not in Krita
            foundActions = EKritaShortcuts.checkIfExists(keySequence)
            if len(foundActions) == 0 or len(foundActions) == 1 and foundActions[0].data() == self.__brush.id():
                self.__setOkEnabled(True)
                self.lblShortcutAlreadyUsed.setText('')
                self.lblShortcutAlreadyUsed.setStyleSheet('')
            else:
                self.__setOkEnabled(False)
                text = [i18n("<b>Shortcut is already used</b>")]
                eChar = '\x01'
                for action in foundActions:
                    text.append(f"- <i>{action.text().replace('&&', eChar).replace('&', '').replace(eChar, '&')}</i>")
                self.lblShortcutAlreadyUsed.setText("<br>".join(text))
                self.lblShortcutAlreadyUsed.setStyleSheet(UITheme.style('warning-box'))

    def __brushColorPickerUiChanged(self):
        """UI has been changed for fg/bg color => apply same ui to other color bg/fg panel"""
        if self.__inColorUiChangeEvent:
            # avoid recursive calls
            return

        self.__inColorUiChangeEvent = True
        if self.sender() == self.btUseSpecificColorFg.colorPicker():
            self.btUseSpecificColorBg.colorPicker().setOptionLayout(self.btUseSpecificColorFg.colorPicker().optionLayout())
        else:
            self.btUseSpecificColorFg.colorPicker().setOptionLayout(self.btUseSpecificColorBg.colorPicker().optionLayout())
        self.__inColorUiChangeEvent = False

    def colorPickerLayoutTxt(self):
        """Return color picked layout for text editor"""
        return self.wtComments.colorPickerLayout()

    def colorPickerLayoutBrushFg(self):
        """Return color picked layout for brush"""
        return self.btUseSpecificColorFg.colorPicker().optionLayout()

    def colorPickerLayoutBrushBg(self):
        """Return color picked layout for background"""
        return self.btUseSpecificColorBg.colorPicker().optionLayout()

    def gradientBtnViewMode(self):
        """Return gradient button view mode"""
        return self.btUseSpecificColorGradient.managedResourcesSelector().viewMode()

    def gradientBtnIconSizeIndex(self):
        """Return gradient button zoom level"""
        return self.btUseSpecificColorGradient.managedResourcesSelector().iconSizeIndex()

    def options(self):
        """Return options from brush editor"""
        returned = {
                BBSBrush.KEY_SIZE: self.dsbBrushSize.value(),
                BBSBrush.KEY_OPACITY: self.dsbBrushOpacity.value()/100,
                BBSBrush.KEY_FLOW: self.dsbBrushFlow.value()/100,
                BBSBrush.KEY_BLENDINGMODE: self.cbBrushBlendingMode.currentData(),
                BBSBrush.KEY_PRESERVEALPHA: self.cbPreserveAlpha.isChecked(),
                BBSBrush.KEY_COMMENTS: self.wtComments.toHtml(),
                BBSBrush.KEY_KEEPUSERMODIFICATIONS: self.cbKeepUserModifications.isChecked(),
                BBSBrush.KEY_IGNOREERASERMODE: True,    # updated below
                BBSBrush.KEY_IGNORETOOLOPACITY: self.cbIgnoreToolOpacity.isChecked(),
                BBSBrush.KEY_SHORTCUT: self.kseShortcut.keySequence(),
                BBSBrush.KEY_COLOR_FG: None,
                BBSBrush.KEY_COLOR_BG: None,
                BBSBrush.KEY_COLOR_GRADIENT: None,
                BBSBrush.KEY_DEFAULTPAINTTOOL: None
            }

        if self.cbDefaultPaintTool.isChecked():
            returned[BBSBrush.KEY_DEFAULTPAINTTOOL] = self.cbDefaultPaintTools.currentData()

        if self.cbBrushBlendingMode.currentData() != 'erase':
            returned[BBSBrush.KEY_IGNOREERASERMODE] = self.cbIgnoreEraserMode.isChecked()

        if self.cbUseSpecificColor.isChecked():
            returned[BBSBrush.KEY_COLOR_FG] = self.btUseSpecificColorFg.color()
            if self.btUseSpecificColorBg.color().isNone():
                returned[BBSBrush.KEY_COLOR_BG] = None
            else:
                returned[BBSBrush.KEY_COLOR_BG] = self.btUseSpecificColorBg.color()

            returned[BBSBrush.KEY_COLOR_GRADIENT] = self.btUseSpecificColorGradient.resource().id()

        return returned


class BBSGroupEditor(EDialog):
    """A simple dialog box to edit group properties"""
    @staticmethod
    def edit(title, group):
        """Open a dialog box to edit group"""
        widget = QWidget()
        dlgBox = BBSGroupEditor(title, group, widget)

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            BBSSettings.setTxtColorPickerLayout(dlgBox.colorPickerLayoutTxt())

            return dlgBox.options()
        else:
            return None

    def __init__(self, title, group, parent=None):
        super(BBSGroupEditor, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'bbsgroupedit.ui'), parent)

        self.__group = group

        replaceLineEditClearButton(self.leName)
        self.leName.setText(self.__group.name())

        self.wColorIndex.setColorIndex(self.__group.color())

        self.wtComments.setHtml(self.__group.comments())
        self.wtComments.setToolbarButtons(WTextEdit.DEFAULT_TOOLBAR | WTextEditBtBarOption.STYLE_STRIKETHROUGH | WTextEditBtBarOption.STYLE_COLOR_BG)
        self.wtComments.setColorPickerLayout(BBSSettings.getTxtColorPickerLayout())

        self.kseShortcutNext.setKeySequence(self.__group.shortcutNext())
        self.kseShortcutNext.setClearButtonEnabled(True)
        self.kseShortcutNext.keySequenceCleared.connect(self.__shortcutModified)
        self.kseShortcutNext.editingFinished.connect(self.__shortcutModified)
        self.kseShortcutNext.keySequenceChanged.connect(self.__shortcutModified)

        self.kseShortcutPrevious.setKeySequence(self.__group.shortcutPrevious())
        self.kseShortcutPrevious.setClearButtonEnabled(True)
        self.kseShortcutPrevious.keySequenceCleared.connect(self.__shortcutModified)
        self.kseShortcutPrevious.editingFinished.connect(self.__shortcutModified)
        self.kseShortcutPrevious.keySequenceChanged.connect(self.__shortcutModified)

        self.pbOk.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.setModal(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

    def __setOkEnabled(self, value):
        """Enable/Disable OK button"""
        if isinstance(value, bool):
            self.pbOk.setEnabled(value)

    def __shortcutModified(self):
        """Shortcut value has been modified

        Check if valid
        """
        keySequenceNext = self.kseShortcutNext.keySequence()
        keySequencePrevious = self.kseShortcutPrevious.keySequence()

        isOk = True
        warningText = []
        warningStyle = ''
        if not keySequenceNext.isEmpty():
            # need to check if shortcut already exists or not in Krita
            foundActions = EKritaShortcuts.checkIfExists(keySequenceNext)
            if len(foundActions) > 0 and not (len(foundActions) == 1 and foundActions[0].data() == self.__group.id()+'-N'):
                isOk = False
                warningText.append(f'<b>{i18n("Shortcut is already used")} (<i>{keySequenceNext.toString()}</i>)')
                eChar = '\x01'
                for action in foundActions:
                    warningText.append(f"- <i>{action.text().replace('&&', eChar).replace('&', '').replace(eChar, '&')}</i>")
                warningStyle = UITheme.style('warning-box')

        if not keySequencePrevious.isEmpty():
            # need to check if shortcut already exists or not in Krita
            foundActions = EKritaShortcuts.checkIfExists(keySequencePrevious)
            if len(foundActions) > 0 and not (len(foundActions) == 1 and foundActions[0].data() == self.__group.id()+'-P'):
                isOk = False
                warningText.append(f'<b>{i18n("Shortcut is already used")} (<i>{keySequencePrevious.toString()}</i>)')
                eChar = '\x01'
                for action in foundActions:
                    warningText.append(f"- <i>{action.text().replace('&&', eChar).replace('&', '').replace(eChar, '&')}</i>")
                warningStyle = UITheme.style('warning-box')

        if not keySequencePrevious.isEmpty() and keySequenceNext == keySequencePrevious:
            isOk = False
            warningText.append(f"""<b>{i18n("Shortcut Next and Previous can't be the same")}""")
            warningStyle = UITheme.style('warning-box')

        self.__setOkEnabled(isOk)
        self.lblShortcutAlreadyUsed.setText("<br>".join(warningText))
        self.lblShortcutAlreadyUsed.setStyleSheet(warningStyle)

    def colorPickerLayoutTxt(self):
        """Return color picked layout for text editor"""
        return self.wtComments.colorPickerLayout()

    def options(self):
        """Return options from brush editor"""
        # --- ici ---
        returned = {
                BBSGroup.KEY_NAME: self.leName.text(),
                BBSGroup.KEY_COMMENTS: self.wtComments.toHtml(),
                BBSGroup.KEY_SHORTCUT_NEXT: self.kseShortcutNext.keySequence(),
                BBSGroup.KEY_SHORTCUT_PREV: self.kseShortcutPrevious.keySequence(),
                BBSGroup.KEY_COLOR: self.wColorIndex.colorIndex(),
                BBSGroup.KEY_EXPANDED: self.__group.expanded()
            }

        return returned
