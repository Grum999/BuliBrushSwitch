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

from bulibrushswitch.pktk.modules.edialog import EDialog
from bulibrushswitch.pktk.modules.uitheme import UITheme
from bulibrushswitch.pktk.modules.iconsizes import IconSizes
from bulibrushswitch.pktk.modules.strutils import stripHtml
from bulibrushswitch.pktk.modules.imgutils import (warningAreaBrush, qImageToPngQByteArray, bullet, buildIcon)
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

    KEY_UUID = 'uuid'
    KEY_POSITION = 'position'
    KEY_SHORTCUT = 'shortcut'

    def __init__(self, parent=None):
        super(BBSBaseNode, self).__init__(None)
        self.__uuid = QUuid.createUuid().toString().strip("{}")
        self.__emitUpdated = 0
        self.__position = -1
        self.__shortcut = QKeySequence()

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

    def actionId(self):
        """Return id to use for an action for this brush"""
        return BBSSettings.brushActionId(self.id())

    def action(self):
        """Return Krita's action for this brush or none if not found"""
        return BBSSettings.brushAction(self.id())

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

    INFO_COMPACT =                  0b00000001
    INFO_WITH_BRUSH_ICON =          0b00000010
    INFO_WITH_BRUSH_DETAILS =       0b00000100
    INFO_WITH_BRUSH_OPTIONS =       0b00001000

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
        return f"<BBSBrush({self.id()}, '{self.__name}')>"

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
                self.__brushNfoImg = f'<img src="data:image/png;base64,{bytes(qImageToPngQByteArray(self.__image).toBase64(QByteArray.Base64Encoding)).decode()}">'
            else:
                self.__brushNfoImg = ''

            shortcut = self.shortcut()
            if not shortcut.isEmpty():
                shortcutText = f' <tr><td align="left"><b>{i18n("Shortcut")}</b></td><td align="right">{shortcut.toString()}</td><td></td></tr>'
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
                                                 r"<\1div", re.sub("<!doctype[^>]>|<meta[^>]+>|</?html>|</?head>", "", self.__brushNfoComments, flags=re.I),
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
                BBSBrush.KEY_SHORTCUT: self.shortcut().toString(),
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
        if displayOption & BBSBrush.INFO_WITH_BRUSH_OPTIONS:
            returned = self.__brushNfoOptions

            if not(displayOption & BBSBrush.INFO_COMPACT) and self.__brushNfoComments != '':
                hr = ''
                if returned != '':
                    hr = "<tr><td colspan=3><hr></td></tr>"
                returned = f"<tr><td colspan=3>{self.__brushNfoComments}</td></tr>{hr}{returned}"

        if displayOption & BBSBrush.INFO_WITH_BRUSH_DETAILS:
            hr = ''
            if returned != '':
                hr = "<tr><td colspan=3><hr></td></tr>"

            if displayOption & BBSBrush.INFO_COMPACT:
                returned = f'<small><i><table>{self.__brushNfoShort}{hr}{returned}</table></i></small>'
            else:
                returned = f'<small><i><table>{self.__brushNfoFull}{hr}{returned}</table></i></small>'

            returned = f'<b>{self.__name.replace("_", " ")}</b>{returned}'
        else:
            returned = f'<small><i><table>{returned}</table></i></small>'

        if displayOption & BBSBrush.INFO_WITH_BRUSH_ICON and self.__brushNfoImg != '':
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


class BBSGroup(BBSBaseNode):
    """A group definition"""
    KEY_NAME = 'name'
    KEY_COMMENTS = 'comments'
    KEY_COLOR = 'color'
    KEY_SHORTCUT = 'shortcut'
    KEY_EXPANDED = 'expanded'

    def __init__(self, group=None):
        super(BBSGroup, self).__init__(None)

        self.__name = ''
        self.__comments = ''
        self.__color = WStandardColorSelector.COLOR_NONE
        self.__expanded = True

        if isinstance(group, BBSGroup):
            # clone group
            self.importData(group.exportData())
        elif isinstance(group, dict):
            self.importData(group)

    def __repr__(self):
        return f"<BBSGroup({self.id()}, '{self.__name}')>"

    def applyUpdate(self, property):
        """Emit updated signal when a property has been changed"""
        if not self.inUpdate():
            pass

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
                BBSGroup.KEY_SHORTCUT: self.shortcut().toString(),
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

            action = self.action()
            if action and action.shortcut():
                self.setShortcut(action.shortcut())
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
            self.applyUpdate('color')

    def expanded(self):
        """Return if group is expanded or not"""
        return self.__expanded

    def setExpanded(self, expanded):
        """Set if if group is expanded or not"""
        if isinstance(expanded, bool) and expanded != self.__expanded:
            self.__expanded = expanded
            self.applyUpdate('expanded')


class BBSModelNode:
    """A node for BBSModel"""

    def __init__(self, data, parent=None):
        if parent is not None and not isinstance(parent, BBSModelNode):
            raise EInvalidType("Given `parent` must be a <BBSModelNode>")
        elif not isinstance(data, BBSBaseNode):
            raise EInvalidType("Given `data` must be a <BBSBaseNode>")

        self.__parent = parent
        self.__data = data

        self.__inUpdate = 0

        # Initialise node childs
        self.__childs = []

    def __repr__(self):
        if self.__parent:
            parent = f"{self.__parent.data().id()}"
        else:
            parent = "None"

        if self.__data:
            data = f"{self.__data}"
        else:
            data = "None"

        return f"<BBSModelNode(parent:{parent}, data:{data}, childs:{len(self.__childs)})>"

    def __beginUpdate(self):
        self.__inUpdate += 1

    def __endUpdate(self):
        self.__inUpdate -= 1
        if self.__inUpdate < 0:
            self.__inUpdate = 0
        elif self.__inUpdate == 0:
            self.sort()

    def childs(self):
        """Return list of childs"""
        return self.__childs

    def child(self, row):
        """Return child at given position"""
        if row < 0 or row >= len(self.__childs):
            return None
        return self.__childs[row]

    def addChild(self, childNode):
        """Add a new child """
        if isinstance(childNode, list):
            self.__beginUpdate()
            for childNodeToAdd in childNode:
                self.addChild(childNodeToAdd)
            self.__endUpdate()
        elif not isinstance(childNode, BBSModelNode):
            raise EInvalidType("Given `childNode` must be a <BBSModelNode>")
        elif isinstance(childNode.data(), self.__data.acceptedChild()):
            self.__beginUpdate()
            childNode.setParent(self)
            self.__childs.append(childNode)
            self.__endUpdate()

    def removeChild(self, childNode):
        """Remove a child
        Removed child is returned
        Or None if child is not found
        """
        if isinstance(childNode, list):
            returned = []
            self.__beginUpdate()
            for childNodeToRemove in childNode:
                returned.append(self.removeChild(childNodeToRemove))
            self.__endUpdate()
            return returned
        elif not isinstance(childNode, BBSModelNode):
            raise EInvalidType("Given `childNode` must be a <BBSModelNode>")
        else:
            self.__beginUpdate()
            try:
                returned = self.__childs.pop(self.__childs.index(childNode))
            except Exception:
                returned = None

            self.__endUpdate()
            return returned

    def clear(self):
        """Remove all childs"""
        self.__beginUpdate()
        self.__childs = []
        self.__endUpdate()

    def childCount(self):
        """Return number of children the current node have"""
        return len(self.__childs)

    def row(self):
        """Return position in parent's children list"""
        returned = 0
        if self.__parent:
            returned = self.__parent.childRow(self)
            if returned < 0:
                # need to check if -1 can be used
                returned = -1
        return returned

    def childRow(self, node):
        """Return row number for given node

        If node is not found, return -1
        """
        try:
            return self.__childs.index(node)
        except Exception:
            return -1

    def columnCount(self):
        """Return number of column for item"""
        return 1

    def data(self):
        """Return data for node

        Content is managed from model
        """
        return self.__data

    def parent(self):
        """Return current parent"""
        return self.__parent

    def setParent(self, parent):
        """Set current parent"""
        if parent is None or isinstance(parent, BBSModelNode):
            self.__parent = parent

    def setData(self, data):
        """Set node data"""
        if not isinstance(data, BBSBaseNode):
            raise EInvalidType("Given `data` must be a <BBSBaseNode>")
        self.__data = data

    def sort(self):
        """Sort children from their position"""
        #self.__childs.sort(key=lambda item: item.data().position())
        pass


class BBSModel(QAbstractItemModel):
    """A model to access brush and groups in an hierarchical tree"""
    updateWidth = Signal()

    HEADERS = ['Icon', 'Brush', 'Description']

    COLNUM_ICON = 0
    COLNUM_BRUSH = 1
    COLNUM_COMMENT = 2

    COLNUM_LAST = 2

    ROLE_ID = Qt.UserRole + 1
    ROLE_DATA = Qt.UserRole + 2
    ROLE_NODE = Qt.UserRole + 3
    ROLE_CSIZE = Qt.UserRole + 4

    TYPE_BRUSH = 0b01
    TYPE_GROUP = 0b10

    def __init__(self, parent=None):
        """Initialise data model"""
        super(BBSModel, self).__init__(parent)

        self.__rootItem = BBSModelNode(BBSGroup({BBSGroup.KEY_UUID: "00000000-0000-0000-0000-000000000000",
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
        return getIdIndexes(id, self.__rootItem, QModelIndex())

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
        getIdIndexes(self.__rootItem)

    def __beginUpdate(self):
        """Start a massive update"""
        if self.__inMassiveUpdate == 0:
            self.beginResetModel()
        self.__inMassiveUpdate += 1

    def __endUpdate(self):
        """Start a massive update"""
        self.__inMassiveUpdate -= 1
        if self.__inMassiveUpdate == 0:
            self.__updateIdIndex()
            self.__updatePositions()
            self.endResetModel()
            self.updateWidth.emit()

    def __updatePositions(self):
        """update items positions"""
        print('todo: BBSModel.__updatePositions()')

    def columnCount(self, parent=QModelIndex()):
        """Return total number of column for index"""
        return BBSModel.COLNUM_LAST+1

    def rowCount(self, parent=QModelIndex()):
        """Return total number of rows for index"""
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.__rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def data(self, index, role=Qt.DisplayRole):
        """Return data for index+role"""
        if not index.isValid():
            print("data() invalid index: ", index)
            return None

        item = index.internalPointer()
        if item is None:
            print("data()--0: internal pointer None", index.row(), index.column())
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
                if column == BBSModel.COLNUM_ICON:
                    image = data.image()
                    if image:
                        # QIcon
                        return QIcon(QPixmap.fromImage(image))
                    else:
                        return buildIcon('pktk:warning')
            elif role == Qt.ToolTipRole:
                if not data.found():
                    return i18n(f"Brush <i><b>{data.name()}</b></i> is not installed and/or activated on this Krita installation")
                else:
                    return data.information(BBSBrush.INFO_WITH_BRUSH_DETAILS | BBSBrush.INFO_WITH_BRUSH_OPTIONS)

        return None

    def index(self, row, column, parent=None):
        """Provide indexes for views and delegates to use when accessing data

        If an invalid model index is specified as the parent, it is up to the model to return an index that corresponds to a top-level item in the model.
        """
        if not isinstance(parent, QModelIndex) or not self.hasIndex(row, column, parent):
            return QModelIndex()

        child = None
        if not parent.isValid():
            parentNode = self.__rootItem
        else:
            parentNode = parent.internalPointer()

        child = parentNode.child(row)

        if child:
            return self.createIndex(row, column, child)
        else:
            print(f"index()--2: invalid child; row: {row}, col: {column}, parent:", parent, "\n.          parentNode:", parentNode, "\n")
            return QModelIndex()

    def parent(self, index):
        """return parent (QModelIndex) for given index"""
        if not index or not index.isValid():
            returned = QModelIndex()
            return returned

        if index.internalPointer() is None:
            # not sure to understand why this case occurs... :-/
            # print("parent()--2a: ", index, index.internalPointer(), index.internalId())
            # print("parent()--2b: ", index.row(), index.column(), index.data(), index.isValid())
            return QModelIndex()
        childItem = index.internalPointer()
        childParent = childItem.parent()

        if childParent is None or childParent == self.__rootItem:
            return QModelIndex()

        return self.createIndex(childParent.row(), 0, childParent)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return label for given data section"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section > 0:
            return BBSModel.HEADERS[section]
        return None

    # TODO: to check ==> not used?
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

    # TODO: used in bbsmainwindow & bbswbrushswitcher
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

    # TODO: used bbswbrushswitcher
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

    # TODO: used bbswbrushswitcher
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
            node = self.__rootItem
        elif isinstance(groupId, str):
            index = self.__getIdIndex(groupId)
            if index.isValid():
                data = self.data(index, BBSModel.ROLE_DATA)
                if isinstance(data, BBSGroup) and data.id() == groupId:
                    node = self.data(index, BBSModel.ROLE_NODE)

        if node is not None:
            # get all data, maybe not ordered
            returned = [childNode.data() for childNode in node.childs()]
            returned.sort(key=lambda item: item.position())

            if asIndex:
                returned = [self.__getIdIndex(item.id()) for item in returned]
        return returned

    def clear(self):
        """Clear all brushes & groups"""
        self.remove(self.__rootItem.childs())

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
            returned = itemToRemove.parent().removeChild(itemToRemove)
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
            parent = self.__rootItem

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
                    parent.addChild(BBSModelNode(itemToAdd, parent))
                    self.__endUpdate()
        elif isinstance(parent, str):
            # a string --> assume it's an Id
            index = self.getFromId(parent)
            if index is not None:
                self.add(itemToAdd, self.data(index, BBSModel.ROLE_NODE))
        elif isinstance(parent, BBSBaseNode):
            self.add(itemToAdd, parent.id())

    def update(self, itemToUpdate):
        print("BBSModel.update() -- TODO", itemToUpdate)

    def load(self, brushesAndGroups, nodes):
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
                        toAdd.append(BBSModelNode(tmpIdIndex[id], parent))
                    else:
                        raise EInvalidValue(f"Given `id` ({id}) can't be added, index not exist")
                elif isinstance(id, tuple):
                    # a group
                    addNodes(id[1], BBSModelNode(tmpIdIndex[id[0]], parent))
                else:
                    raise EInvalidValue(f"Given `id` must be a valid <str>")
            parent.addChild(toAdd)

        self.__beginUpdate()
        self.clear()
        # a dictionary id => BBSBaseNode
        tmpIdIndex = {brushOrGroup.id(): brushOrGroup for brushOrGroup in brushesAndGroups}

        if len(nodes) == 0:
            # in this case (probably from a previous version of BBS, create everything at root level
            nodes = list(tmpIdIndex.keys())

        addNodes(nodes, self.__rootItem)
        self.__endUpdate()


class BBSWBrushesTv(QTreeView):
    """Tree view brushes"""
    focused = Signal()
    keyPressed = Signal(int)
    iconSizeIndexChanged = Signal(int, QSize)

    def __init__(self, parent=None):
        super(BBSWBrushesTv, self).__init__(parent)
        self.setAutoScroll(True)
        self.setAlternatingRowColors(True)

        self.__parent = parent
        self.__model = None
        self.__selectedBeforeReset = []
        self.__fontSize = self.font().pointSizeF()
        if self.__fontSize == -1:
            self.__fontSize = -self.font().pixelSize()

        # value at which treeview apply compacted view (-1: never)
        self.__compactIconSizeIndex = -1

        self.__delegate = BBSModelDelegate(self)
        self.setItemDelegate(self.__delegate)

        self.__iconSize = IconSizes([32, 64, 96, 128, 192])
        self.setIconSizeIndex(3)

        self.__contextMenu = QMenu()
        self.__initMenu()

        header = self.header()
        header.sectionResized.connect(self.__sectionResized)
        self.resizeColumns()

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

        self.__selectedBeforeReset = []
        self.resizeColumns()

    def resizeColumns(self):
        """Resize columns"""
        self.resizeColumnToContents(BBSModel.COLNUM_ICON)
        self.resizeColumnToContents(BBSModel.COLNUM_BRUSH)

        width = max(self.columnWidth(BBSModel.COLNUM_BRUSH), self.columnWidth(BBSModel.COLNUM_ICON))
        self.setColumnWidth(BBSModel.COLNUM_BRUSH, round(width*1.25))

    def __sectionResized(self, index, oldSize, newSize):
        """When section is resized, update rows height"""
        if index == BBSModel.COLNUM_COMMENT and not self.isColumnHidden(BBSModel.COLNUM_COMMENT):
            # update height only if comment section is resized
            self.__delegate.setCSize(newSize)
            for rowNumber in range(self.__model.rowCount()):
                # need to recalculate height for all rows
                self.__delegate.sizeHintChanged.emit(self.__model.createIndex(rowNumber, index))

    def setColumnHidden(self, column, hide):
        """Reimplement column hidden"""
        super(BBSWBrushesTv, self).setColumnHidden(column, hide)
        self.__delegate.setCSize(0)

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

    def iconSizeIndex(self):
        """Return current icon size index"""
        return self.__iconSize.index()

    def setIconSizeIndex(self, index=None):
        """Set icon size from index value"""
        if index is None or self.__iconSize.setIndex(index):
            # new size defined
            self.setIconSize(self.__iconSize.value(True))
            self.__delegate.setCompactSize(self.__iconSize.index() <= self.__compactIconSizeIndex)

            header = self.header()
            header.resizeSection(BBSModel.COLNUM_ICON, self.__iconSize.value())
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
        header.setSectionResizeMode(BBSModel.COLNUM_ICON, QHeaderView.Fixed)
        header.setSectionResizeMode(BBSModel.COLNUM_BRUSH, QHeaderView.Fixed)
        header.setSectionResizeMode(BBSModel.COLNUM_COMMENT, QHeaderView.Stretch)

        self.resizeColumns()
        self.__model.updateWidth.connect(self.resizeColumns)
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
            for item in self.selectionModel().selectedRows(BBSModel.COLNUM_BRUSH):
                brush = item.data(BBSModel.ROLE_DATA)
                if brush is not None:
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

        value = max(-1, min(value, 4))
        if self.__compactIconSizeIndex != value:
            self.__compactIconSizeIndex = value
            self.__delegate.setCompactSize(self.__iconSize.index() <= self.__compactIconSizeIndex)
            self.update()


class BBSWBrushesLv(QListView):
    """List view brushes"""
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


class BBSModelDelegate(QStyledItemDelegate):
    """Extend QStyledItemDelegate class to build improved rendering items"""
    def __init__(self, parent=None):
        """Constructor, nothingspecial"""
        super(BBSModelDelegate, self).__init__(parent)
        self.__csize = 0
        self.__compactSize = False

    def __getBrushInformation(self, brush):
        """Return text for brush information"""
        compactSize = 0
        if self.__compactSize:
            compactSize = BBSBrush.INFO_COMPACT
        textDocument = QTextDocument()
        textDocument.setHtml(brush.information(BBSBrush.INFO_WITH_BRUSH_DETAILS | compactSize))
        return textDocument

    def __getOptionsInformation(self, brush):
        """Return text for brush options (comments + option)"""
        compactSize = 0
        if self.__compactSize:
            compactSize = BBSBrush.INFO_COMPACT

        textDocument = QTextDocument()
        textDocument.setHtml(brush.information(BBSBrush.INFO_WITH_BRUSH_OPTIONS | compactSize))
        cursor = QTextCursor(textDocument)

        return textDocument

    def setCompactSize(self, value):
        """Activate/deactivate compact size"""
        self.__compactSize = value

    def setCSize(self, value):
        """Force size for comments column"""
        self.__csize = value

    def paint(self, painter, option, index):
        """Paint list item"""
        if index.column() == BBSModel.COLNUM_BRUSH:
            # render brush information
            self.initStyleOption(option, index)

            brush = index.data(BBSModel.ROLE_DATA)
            rectTxt = QRect(option.rect.left() + 1, option.rect.top()+4, option.rect.width()-4, option.rect.height()-1)

            painter.save()

            if not brush.found():
                if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                    option.state &= ~QStyle.State_Selected
                painter.fillRect(option.rect, warningAreaBrush())

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            textDocument = self.__getBrushInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0, 0), QSizeF(rectTxt.size())))

            # painter.drawText(rectTxt, Qt.AlignLeft|Qt.AlignTop, brush.name())

            painter.restore()
            return
        elif index.column() == BBSModel.COLNUM_COMMENT:
            # render comment
            self.initStyleOption(option, index)

            brush = index.data(BBSModel.ROLE_DATA)
            rectTxt = QRect(option.rect.left(), option.rect.top(), option.rect.width(), option.rect.height())

            textDocument = self.__getOptionsInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(rectTxt.size()))

            painter.save()

            if not brush.found():
                if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                    option.state &= ~QStyle.State_Selected
                painter.fillRect(option.rect, warningAreaBrush())

            if (option.state & QStyle.State_Selected) == QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.color(QPalette.Highlight))
                painter.setPen(QPen(option.palette.color(QPalette.HighlightedText)))
            else:
                painter.setPen(QPen(option.palette.color(QPalette.Text)))

            painter.translate(QPointF(rectTxt.topLeft()))
            textDocument.drawContents(painter, QRectF(QPointF(0, 0), QSizeF(rectTxt.size())))

            painter.restore()
            return
        elif index.column() == BBSModel.COLNUM_ICON:
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

        if index.column() == BBSModel.COLNUM_ICON:
            return option.decorationSize
        elif index.column() == BBSModel.COLNUM_BRUSH:
            brush = index.data(BBSModel.ROLE_DATA)
            textDocument = self.__getBrushInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(4096, 1000))  # set 1000px size height arbitrary
            textDocument.setPageSize(QSizeF(textDocument.idealWidth(), 1000))  # set 1000px size height arbitrary
            size = textDocument.size().toSize()+QSize(8, 8)
        elif index.column() == BBSModel.COLNUM_COMMENT:
            # size for comments cell (width is forced, calculate height of rich text)
            brush = index.data(BBSModel.ROLE_DATA)
            textDocument = self.__getOptionsInformation(brush)
            textDocument.setDocumentMargin(1)
            textDocument.setDefaultFont(option.font)
            textDocument.setDefaultStyleSheet("td { white-space: nowrap; }")
            textDocument.setPageSize(QSizeF(self.__csize, 1000))  # set 1000px size height arbitrary
            size = QSize(self.__csize, textDocument.size().toSize().height())

        return size


class BBSBrushesEditor(EDialog):
    """A simple dialog box to brushe comment

    The WTextEditDialog doesn't allows to manage color picker configuration then,
    create a dedicated dailog box
    """
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
            self.cbDefaultPaintTools.addItem(EKritaTools.name(toolId), toolId)
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
            if len(foundActions) == 0:
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
