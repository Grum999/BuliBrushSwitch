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
# The bbsmainvindow module provides classes used to manage main user interface
# (the main window)
# --> this module is a core module for plugin
#
# Main classes from this module
#
# - BBSMainWindow:
#       The main use interface window :)
#       Mostly used to manage main window menu entries & toolbars
#
# -----------------------------------------------------------------------------

import os
import os.path
import re
import shutil
from krita import (
                Scratchpad,
                View,
                ManagedColor,
                Resource,
                Krita
            )
import PyQt5.uic

from PyQt5.QtCore import QDir
from PyQt5.Qt import *
from PyQt5.QtWidgets import (
        QDialog,
        QWidget
    )

from .bbswbrushes import (
        BBSBrush,
        BBSGroup,
        BBSModel,
        BBSBrushesEditor,
        BBSGroupEditor
    )
from .bbssettings import (
        BBSSettings,
        BBSSettingsKey,
        BBSSettingsValues
    )

from bulibrushswitch.pktk.modules.edialog import EDialog

from bulibrushswitch.pktk.widgets.wstandardcolorselector import WStandardColorSelector
from bulibrushswitch.pktk.widgets.wmenuitem import (WMenuBrushesPresetSelector, WMenuColorPicker)
from bulibrushswitch.pktk.widgets.wcolorselector import WColorPicker
from bulibrushswitch.pktk.widgets.wiodialog import (WDialogBooleanInput, WDialogMessage)

from bulibrushswitch.pktk.modules.ekrita import EKritaBrushPreset
from bulibrushswitch.pktk.modules.ekrita_tools import EKritaTools


# -----------------------------------------------------------------------------
class BBSMainWindow(EDialog):
    """Main BuliBrushSwitch window"""

    @staticmethod
    def open(bbsName="BuliBrushSwitch", bbsVersion="testing", parent=None):
        if (Krita.instance().activeWindow() is None
           or Krita.instance().activeWindow().activeView() is None
           or Krita.instance().activeWindow().activeView().visible() is False
           or Krita.instance().activeWindow().activeView().document() is None):
            # why if no document is opened, there's an active view?
            # need to check if it's normal or not
            WDialogMessage.display(bbsName+' - '+i18n(f'Ooops sorry!'),
                                   f'''<p>{i18n("There's no active document")}</p><p>{i18n("A document must be active to configure plugin...")}</p><p>
                                   <i>{i18n("It's sounds weird I know, even me I'm not happy with that but there's technical things with brushes and then "
                                            "I currently don't have choice in implementation...")}<br><br>Grum999</i></p>''',
                                   minSize=QSize(500, 0))
            return False

        dlgBox = BBSMainWindow(bbsName, bbsVersion, parent)

        returned = dlgBox.exec()

        if returned == QDialog.Accepted:
            return True
        else:
            return False

    def __init__(self, bbsName="BuliBrushSwitch", bbsVersion="testing", parent=None):
        super(BBSMainWindow, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'bbsmainwindow.ui'), parent)

        # plugin name/version
        self.__bbsName = bbsName
        self.__bbsVersion = bbsVersion

        # not yet initialised
        self.__activeView = None

        BBSSettings.load()

        # default bg color for scratchpad
        self.__scratchpadDefaultBgColor = QColor('#ffffff')

        # current active view
        self.__activeView = Krita.instance().activeWindow().activeView()

        # keep in memory current view configuration to restore on dialog close
        self.__activeViewCurrentConfig = {}

        self.__bbsModel = BBSModel()

        # create BBSBrush object + link action shortcuts
        brushesAndGroups = []
        brushesDictList = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
        for brushNfo in brushesDictList:
            brush = BBSBrush()
            if brush.importData(brushNfo):
                brushesAndGroups.append(brush)

        groupsDictList = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_GROUPS)
        for groupNfo in groupsDictList:
            group = BBSGroup()
            if group.importData(groupNfo):
                brushesAndGroups.append(group)

        self.__bbsModel.importData(brushesAndGroups, BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_NODES))

        # keep a saved view of current brush shortcuts
        self.__savedShortcuts = {}
        self.__createdShortcuts = []

        self.setModal(True)
        self.setWindowTitle(i18n(f'{bbsName} v{bbsVersion}'))
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

        self.__saveViewConfig()
        self.__initialiseUi()
        self.__saveShortcutConfig()
        self.__updateUi()

    def showEvent(self, event):
        """Dialog is visible"""
        self.tvBrushes.selectionModel().selectionChanged.connect(self.__itemsSelectionChanged)

    def __initialiseUi(self):
        """Initialise window interface"""
        self.__actionSelectBrushScratchpadColorFg = WMenuColorPicker()
        self.__actionSelectBrushScratchpadColorFg.colorPicker().colorUpdated.connect(self.__actionBrushScratchpadSetColorFg)
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionDisplayAsPctColorRGB(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionDisplayAsPctColorCMYK(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionDisplayAsPctColorHSV(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE))
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionDisplayAsPctColorHSL(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionShowColorAlpha(False)
        self.__actionSelectBrushScratchpadColorFg.colorPicker().setOptionMenu(WColorPicker.OPTION_MENU_ALL & ~WColorPicker.OPTION_MENU_ALPHA)

        menuBrushScratchpadColorFg = QMenu(self.tbBrushScratchpadColorFg)
        menuBrushScratchpadColorFg.addAction(self.__actionSelectBrushScratchpadColorFg)

        self.__actionSelectBrushScratchpadColorBg = WMenuColorPicker()
        self.__actionSelectBrushScratchpadColorBg.colorPicker().colorUpdated.connect(self.__actionBrushScratchpadSetColorBg)
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionDisplayAsPctColorRGB(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionDisplayAsPctColorCMYK(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionDisplayAsPctColorHSV(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE))
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionDisplayAsPctColorHSL(
                                                                                        BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT)
                                                                                        )
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionShowColorAlpha(False)
        self.__actionSelectBrushScratchpadColorBg.colorPicker().setOptionMenu(WColorPicker.OPTION_MENU_ALL & ~WColorPicker.OPTION_MENU_ALPHA)

        menuBrushScratchpadColorBg = QMenu(self.tbBrushScratchpadColorBg)
        menuBrushScratchpadColorBg.addAction(self.__actionSelectBrushScratchpadColorBg)

        self.__actionSelectCurrentBrush = QAction(QIcon(QPixmap.fromImage(self.__activeViewCurrentConfig['brushPreset'].image())),
                                                  i18n(f"Current painting brush ({self.__activeViewCurrentConfig['brushPreset'].name()})"),
                                                  self)
        self.__actionSelectCurrentBrush.triggered.connect(self.__actionBrushAddCurrentBrushPreset)
        self.__actionSelectChoosenBrush = WMenuBrushesPresetSelector()
        self.__actionSelectChoosenBrush.presetChooser().presetClicked.connect(self.__actionBrushAddChoosenBrushPreset)

        self.__menuBrushAdd = QMenu(self.tbBrushAdd)
        self.__menuBrushAdd.addAction(self.__actionSelectCurrentBrush)
        self.__menuBrushAdd.addAction(self.__actionSelectChoosenBrush)

        self.__scratchpadDefaultBgColor = QColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLOR_BG))

        # -- toolbar
        self.tbGroupAdd.clicked.connect(self.__actionGroupAdd)
        self.tbBrushAdd.setMenu(self.__menuBrushAdd)
        self.tbEdit.clicked.connect(self.__actionEdit)
        self.tbDelete.clicked.connect(self.__actionDelete)
        self.tbBrushScratchpadClear.clicked.connect(self.__actionBrushScratchpadClear)
        self.tbBrushScratchpadColorFg.setMenu(menuBrushScratchpadColorFg)
        self.tbBrushScratchpadColorBg.setMenu(menuBrushScratchpadColorBg)


        self.hsItemsThumbSize.setValue(self.tvBrushes.iconSizeIndex())
        self.hsItemsThumbSize.valueChanged.connect(self.__itemsSizeIndexSliderChanged)

        # -- button mode
        if BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE) == BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST:
            self.rbFirstFromList.setChecked(True)
        else:
            self.rbLastSelected.setChecked(True)

        if BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE) == BBSSettingsValues.DEFAULT_MODIFICATIONMODE_IGNORE:
            self.rbModificationModeIgnore.setChecked(True)
        else:
            self.rbModificationModeKeep.setChecked(True)

        # -- brush list
        self.tvBrushes.doubleClicked.connect(self.__actionItem)
        self.tvBrushes.setModel(self.__bbsModel)
        self.tvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_ZOOMLEVEL))
        self.tvBrushes.iconSizeIndexChanged.connect(self.__itemsSizeIndexChanged)

        # -- scratchpad initialisation
        self.__scratchpadTestBrush = Scratchpad(self.__activeView, self.__scratchpadDefaultBgColor, self)
        self.__scratchpadTestBrush.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__scratchpadTestBrush.linkCanvasZoom(False)
        self.__scratchpadTestBrush.setModeManually(False)
        # self.__scratchpadTestBrush.setMode('painting') -- bug if set? (don't remember why commented ^_^')
        self.wBrushScratchpad.layout().addWidget(self.__scratchpadTestBrush)

        # -- dialog box bottom buttons
        self.pbOk.clicked.connect(self.__acceptChange)
        self.pbCancel.clicked.connect(self.__rejectChange)

        # -- dialog box geometry
        size = QSize(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_WIDTH), BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_HEIGHT))
        if size.width() <= 0:
            size.setWidth(self.width())
        if size.height() <= 0:
            size.setHeight(self.height())
        self.resize(size)

        position = QPoint(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_X), BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_Y))
        if position.x() != -1 and position.y() != 1:
            self.move(position)

        self.splitterBrushes.setSizes(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION))
        colSize = BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_COLWIDTH)
        if colSize > 0:
            self.tvBrushes.header().resizeSection(BBSModel.COLNUM_BRUSH, colSize)
        else:
            self.tvBrushes.resizeColumnToContents(BBSModel.COLNUM_BRUSH)

    def __saveShortcutConfig(self):
        """Save current action shortcuts

        During process, we need to udpate action shortcut directly (allows to take
        in account shortcut modification made on brush)
        """
        for itemId, itemType in self.__bbsModel.idIndexes().items():
            if itemType == BBSModel.TYPE_BRUSH:
                action = Krita.instance().action(BBSSettings.brushActionId(itemId))
                if action:
                    self.__savedShortcuts[itemId] = action.shortcut()
                elif itemId in self.__savedShortcuts:
                    self.__savedShortcuts.pop(itemId)
            else:
                actionNext = Krita.instance().action(BBSSettings.groupActionId(itemId, 'N'))
                if actionNext:
                    self.__savedShortcuts[itemId+'-N'] = actionNext.shortcut()
                elif itemId in self.__savedShortcuts:
                    self.__savedShortcuts.pop(itemId+'-N')
                actionPrevious = Krita.instance().action(BBSSettings.groupActionId(itemId, 'P'))
                if actionPrevious:
                    self.__savedShortcuts[itemId+'-P'] = actionPrevious.shortcut()
                elif itemId in self.__savedShortcuts:
                    self.__savedShortcuts.pop(itemId+'-P')

    def __restoreShortcutConfig(self):
        """Restore current shortcut configuration"""
        # for potential new action created, remove designed shortcut
        for itemId in self.__createdShortcuts:
            if re.search('-N$', itemId):
                action = BBSSettings.groupAction(re.sub('-N$', itemId, ''), 'N')
            elif re.search('-P$', itemId):
                action = BBSSettings.brushAction(re.sub('-P$', itemId, ''), 'P')
            else:
                action = BBSSettings.brushAction(itemId)

            if action:
                action.setShortcut(QKeySequence())

        # restore initial shortcuts
        for itemId in self.__savedShortcuts:
            if re.search('-N$', itemId):
                action = BBSSettings.groupAction(re.sub('-N$', itemId, ''), 'N')
            elif re.search('-P$', itemId):
                action = BBSSettings.brushAction(re.sub('-P$', itemId, ''), 'P')
            else:
                action = BBSSettings.brushAction(itemId)

            if action:
                action.setShortcut(self.__savedShortcuts[itemId])

    def __saveViewConfig(self):
        """Save current Krita active view properties"""
        self.__activeViewCurrentConfig['brushSize'] = self.__activeView.brushSize()
        self.__activeViewCurrentConfig['brushPreset'] = EKritaBrushPreset.getPreset(self.__activeView.currentBrushPreset())

        self.__activeViewCurrentConfig['fgColor'] = self.__activeView.foregroundColor()
        self.__activeViewCurrentConfig['bgColor'] = self.__activeView.backgroundColor()

        self.__activeViewCurrentConfig['blendingMode'] = self.__activeView.currentBlendingMode()
        # self.__activeViewCurrentConfig['gradient'] = self.__activeView.currentGradient()
        # self.__activeViewCurrentConfig['pattern'] = self.__activeView.currentPattern()

        self.__activeViewCurrentConfig['paintingOpacity'] = self.__activeView.paintingOpacity()
        self.__activeViewCurrentConfig['paintingFlow'] = self.__activeView.paintingFlow()

        # don't know why, but zoomLevel() and setZoomLevel() don't use same value
        # https://krita-artists.org/t/canvas-class-what-does-zoomlevel-returns-compared-to-setzoomlevel-manual-link-inside/15702/3?u=grum999
        # need to apply a factor to be sure to reapply the right zoom
        self.__activeViewCurrentConfig['zoom'] = self.__activeView.canvas().zoomLevel()/(self.__activeView.document().resolution()*1/72)

        # not from view but... need to be saved/restored
        self.__activeViewCurrentConfig['preserveAlpha'] = Krita.instance().action('preserve_alpha').isChecked()

        # tool
        self.__activeViewCurrentConfig['currentTool'] = EKritaTools.current()

    def __restoreViewConfig(self):
        """Restore view properties"""
        self.__activeView.setCurrentBrushPreset(self.__activeViewCurrentConfig['brushPreset'])
        self.__activeView.setBrushSize(self.__activeViewCurrentConfig['brushSize'])

        self.__activeView.setForeGroundColor(self.__activeViewCurrentConfig['fgColor'])
        self.__activeView.setBackGroundColor(self.__activeViewCurrentConfig['bgColor'])

        self.__activeView.setCurrentBlendingMode(self.__activeViewCurrentConfig['blendingMode'])
        # crash on gradient?
        # self.__activeView.setCurrentGradient(self.__activeViewCurrentConfig['gradient'])
        # self.__activeView.setCurrentPattern(self.__activeViewCurrentConfig['pattern'])

        self.__activeView.setPaintingOpacity(self.__activeViewCurrentConfig['paintingOpacity'])
        self.__activeView.setPaintingFlow(self.__activeViewCurrentConfig['paintingFlow'])

        self.__activeView.canvas().setZoomLevel(self.__activeViewCurrentConfig['zoom'])

        # not from view but... need to be saved/restored
        Krita.instance().action('preserve_alpha').setChecked(self.__activeViewCurrentConfig['preserveAlpha'])

        # tool
        EKritaTools.setCurrent(self.__activeViewCurrentConfig['currentTool'])

    def __actionBrushScratchpadSetColorFg(self, color):
        """Set brush testing scratchpad color"""
        self.__activeView.setForeGroundColor(ManagedColor.fromQColor(color, self.__activeView.canvas()))

    def __actionBrushScratchpadSetColorBg(self, color):
        """Set background testing scratchpad color"""
        self.__scratchpadDefaultBgColor = color
        self.__scratchpadTestBrush.setFillColor(color)
        # need to clear scratchpad to apply color
        self.__scratchpadTestBrush.clear()

    def __actionBrushScratchpadClear(self):
        """Clear Scratchpad content"""
        self.__scratchpadTestBrush.clear()

    def __actionBrushAddCurrentBrushPreset(self):
        """Add a new brush in list"""
        self.__activeView.setCurrentBrushPreset(self.__activeViewCurrentConfig['brushPreset'])
        self.__activeView.setBrushSize(self.__activeViewCurrentConfig['brushSize'])
        self.__activeView.setCurrentBlendingMode(self.__activeViewCurrentConfig['blendingMode'])
        self.__activeView.setPaintingOpacity(self.__activeViewCurrentConfig['paintingOpacity'])
        self.__activeView.setPaintingFlow(self.__activeViewCurrentConfig['paintingFlow'])
        Krita.instance().action('preserve_alpha').setChecked(self.__activeViewCurrentConfig['preserveAlpha'])
        self.__actionBrushAdd()

    def __actionBrushAddChoosenBrushPreset(self, resource):
        """Set current brush"""
        self.__menuBrushAdd.setVisible(False)
        self.__activeView.setCurrentBrushPreset(resource)
        self.__actionBrushAdd()

    def __applyBrushOptions(self, brush, options):
        """Apply options to brush"""
        brush.beginUpdate()
        brush.setComments(options[BBSBrush.KEY_COMMENTS])
        brush.setKeepUserModifications(options[BBSBrush.KEY_KEEPUSERMODIFICATIONS])
        brush.setIgnoreEraserMode(options[BBSBrush.KEY_IGNOREERASERMODE])
        brush.setColorFg(options[BBSBrush.KEY_COLOR_FG])
        brush.setColorBg(options[BBSBrush.KEY_COLOR_BG])
        brush.setColorGradient(options[BBSBrush.KEY_COLOR_GRADIENT])
        brush.setDefaultPaintTool(options[BBSBrush.KEY_DEFAULTPAINTTOOL])
        brush.setBlendingMode(options[BBSBrush.KEY_BLENDINGMODE])
        brush.setPreserveAlpha(options[BBSBrush.KEY_PRESERVEALPHA])
        brush.setIgnoreToolOpacity(options[BBSBrush.KEY_IGNORETOOLOPACITY])
        brush.setSize(options[BBSBrush.KEY_SIZE])
        brush.setOpacity(options[BBSBrush.KEY_OPACITY])
        brush.setFlow(options[BBSBrush.KEY_FLOW])
        brush.setShortcut(options[BBSBrush.KEY_SHORTCUT])
        brush.endUpdate()
        BBSSettings.setBrushShortcut(brush, options[BBSBrush.KEY_SHORTCUT])

    def __applyGroupOptions(self, group, options):
        """Apply options to group"""
        group.beginUpdate()
        group.setName(options[BBSGroup.KEY_NAME])
        group.setComments(options[BBSGroup.KEY_COMMENTS])
        group.setColor(options[BBSGroup.KEY_COLOR])
        group.setExpanded(options[BBSGroup.KEY_EXPANDED])
        group.setShortcutNext(options[BBSGroup.KEY_SHORTCUT_NEXT])
        group.setShortcutPrevious(options[BBSGroup.KEY_SHORTCUT_PREV])
        group.setResetWhenExitGroupLoop(options[BBSGroup.KEY_RESET_EXIT_GROUP])
        group.endUpdate()
        BBSSettings.setGroupShortcut(group, options[BBSGroup.KEY_SHORTCUT_NEXT], options[BBSGroup.KEY_SHORTCUT_PREV])

    def __actionBrushAdd(self):
        """Add a new brush in list (from current view brush)"""
        parentGroup = None
        items = self.tvBrushes.selectedItems()
        if len(items):
            for item in items:
                if isinstance(item, BBSGroup):
                    parentGroup = item
                    break

        brush = BBSBrush()
        brush.fromCurrentKritaBrush(self.__activeView)
        options = BBSBrushesEditor.edit(self.__bbsName+' - '+i18n('Add brush'), brush)
        if options is not None:
            self.__applyBrushOptions(brush, options)
            self.__createdShortcuts.append(brush.id())
            self.__bbsModel.add(brush, parentGroup)
            self.__updateUi()

    def __actionEdit(self):
        """Edit selected group/brush"""
        items = self.tvBrushes.selectedItems()
        if len(items) == 1:
            # can edit only if one item is selected
            item = items[0]

            if isinstance(item, BBSBrush):
                # edit a brush
                options = BBSBrushesEditor.edit(self.__bbsName+' - ' + i18n(f'Edit brush'), item)
                if options is not None:
                    self.__applyBrushOptions(item, options)
                    self.__bbsModel.update(item)
                    self.__updateUi()
            else:
                # edit a group
                options = BBSGroupEditor.edit(self.__bbsName+' - ' + i18n(f'Edit group'), item)
                if options is not None:
                    self.__applyGroupOptions(item, options)
                    self.__bbsModel.update(item)
                    self.__updateUi()

    def __actionDelete(self):
        """Remove selected group/brush"""
        def groupNfo(group):
            returned = group.information(BBSGroup.INFO_WITH_DETAILS | BBSGroup.INFO_WITH_OPTIONS)

            stats = group.node().childStats()
            includingGroups = ''
            groups = ''
            if stats['total-groups'] > 0:
                includingGroups = i18n(' (Including groups sub-items)')
                groups = f"<li>{i18n('Groups:')} {stats['total-groups']}</li>"

            if stats['total-brushes'] > 0:
                returned += f"<hr><small><b><i>&gt; {i18n('Deletion of group will also delete')}{includingGroups}<ul><li>{i18n('Brushes:')} {stats['brushes']}</li>{groups}</ul></i></b></small>"

            return returned

        items = self.tvBrushes.selectedItems()
        if len(items):
            # a brush is selected
            brushes = [item for item in items if isinstance(item, BBSBrush)]
            groups = [item for item in items if isinstance(item, BBSGroup)]

            nbBrushes = len(brushes)
            nbGroups = len(groups)

            title = []
            txtBrushes = []
            txtGroups = []

            if nbBrushes > 0:
                if nbBrushes == 1:
                    txtBrushes.append(f'<h2>{i18n("Following brush will removed")}</h2>')
                    title.append(i18n("Remove brush"))
                elif nbBrushes > 1:
                    txtBrushes.append(f'<h2>{i18n("Following brushes will removed")} ({nbBrushes})</h2>')
                    title.append(i18n("Remove brushes"))

                txtBrushes.append("<ul><li>")
                txtBrushes.append("<br></li><li>".join([brush.information(BBSBrush.INFO_WITH_ICON | BBSBrush.INFO_WITH_DETAILS | BBSBrush.INFO_WITH_OPTIONS) for brush in brushes]))
                txtBrushes.append("<br></li></ul>")

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

            if WDialogBooleanInput.display(self.__bbsName+' - ' + "/".join(title),
                                           "".join(txtBrushes + txtGroups + [f'<br><h2>{i18n("Do you confirm action?")}</h2>']),
                                           minSize=QSize(950, 400)):
                for brush in brushes:
                    BBSSettings.setBrushShortcut(brush, QKeySequence())
                self.__bbsModel.remove(brushes)

                for group in groups:
                    BBSSettings.setGroupShortcut(group, QKeySequence(), QKeySequence())

                self.__bbsModel.remove(groups)
                self.__updateUi()

    def __actionGroupAdd(self):
        """Add a new group in list (from current view brush)"""
        parentGroup = None
        items = self.tvBrushes.selectedItems()
        if len(items):
            for item in items:
                if isinstance(item, BBSGroup):
                    parentGroup = item
                    break

        group = BBSGroup()
        options = BBSGroupEditor.edit(self.__bbsName+' - '+i18n('Add group'), group)
        if options is not None:
            self.__applyGroupOptions(group, options)
            self.__createdShortcuts.append(group.id())
            self.__bbsModel.add(group, parentGroup)
            self.__updateUi()

    def __actionItem(self, index):
        """Double click on item
        - brush: edit brush
        - group: expand/collapse
        """
        item = self.__bbsModel.data(index, BBSModel.ROLE_DATA)
        if item:
            if isinstance(item, BBSBrush) or index.column() != BBSModel.COLNUM_BRUSH:
                self.__actionEdit()

    def __itemsSelectionChanged(self, selected, deselected):
        """Selection in treeview has changed, update UI"""
        self.__updateUi()
        selectedBrushes = self.tvBrushes.selectedItems()
        if len(selectedBrushes) == 1 and isinstance(selectedBrushes[0], BBSBrush):
            if selectedBrushes[0].found():
                selectedBrushes[0].toCurrentKritaBrush()

    def __itemsSizeIndexSliderChanged(self, newSize):
        """Thumbnail size has been changed from brushes slider"""
        # update treeview
        self.tvBrushes.setIconSizeIndex(newSize)

    def __itemsSizeIndexChanged(self, newSize, newQSize):
        """Thumbnail size has been changed from brushes treeview"""
        # update slider
        self.hsItemsThumbSize.setValue(newSize)

    def __updateUi(self):
        """Update brushes UI (enable/disable buttons...)"""
        items = self.tvBrushes.selectedItems()

        nbSelectedItems = len(items)

        self.tbEdit.setEnabled(nbSelectedItems == 1)
        self.tbDelete.setEnabled(nbSelectedItems >= 1)

        if len(self.__bbsModel.idIndexes({'groups': False})) > 0:
            # need at elast one brush defined!
            self.pbOk.setEnabled(True)
            self.pbOk.setToolTip("")
        else:
            # at least one brush is mandatory
            self.pbOk.setEnabled(False)
            self.pbOk.setToolTip(i18n("At least, one brush is mandatory!"))

    def __saveSettings(self):
        """Save current settings"""
        if self.rbFirstFromList.isChecked():
            BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE, BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST)
        else:
            BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE, BBSSettingsValues.DEFAULT_SELECTIONMODE_LAST_SELECTED)

        if self.rbModificationModeIgnore.isChecked():
            BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE, BBSSettingsValues.DEFAULT_MODIFICATIONMODE_IGNORE)
        else:
            BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE, BBSSettingsValues.DEFAULT_MODIFICATIONMODE_KEEP)

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_X, self.x())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_Y, self.y())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_WIDTH, self.width())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_HEIGHT, self.height())

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_ZOOMLEVEL, self.tvBrushes.iconSizeIndex())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_COLWIDTH, self.tvBrushes.header().sectionSize(BBSModel.COLNUM_BRUSH))

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT,
                        self.__actionSelectBrushScratchpadColorFg.colorPicker().optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT,
                        self.__actionSelectBrushScratchpadColorFg.colorPicker().optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT,
                        self.__actionSelectBrushScratchpadColorFg.colorPicker().optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE, self.__actionSelectBrushScratchpadColorFg.colorPicker().optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT,
                        self.__actionSelectBrushScratchpadColorFg.colorPicker().optionDisplayAsPctColorHSV())

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT,
                        self.__actionSelectBrushScratchpadColorBg.colorPicker().optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT,
                        self.__actionSelectBrushScratchpadColorBg.colorPicker().optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT,
                        self.__actionSelectBrushScratchpadColorBg.colorPicker().optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE, self.__actionSelectBrushScratchpadColorBg.colorPicker().optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT,
                        self.__actionSelectBrushScratchpadColorBg.colorPicker().optionDisplayAsPctColorHSV())

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLOR_BG, self.__scratchpadDefaultBgColor.name())

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION, self.splitterBrushes.sizes())

        BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_LIST_COUNT, len(self.__bbsModel.idIndexes()))

        exportedData = self.__bbsModel.exportData()
        BBSSettings.setBrushes(exportedData['brushes'])
        BBSSettings.setGroups(exportedData['groups'])
        BBSSettings.setNodes(exportedData['nodes'])

        if BBSSettings.modified():
            BBSSettings.save()

    def __rejectChange(self):
        """User clicked on cancel button"""
        self.__restoreViewConfig()
        self.__restoreShortcutConfig()
        self.reject()

    def __acceptChange(self):
        """User clicked on OK button"""
        for item in [self.__bbsModel.data(index, BBSModel.ROLE_DATA) for index in self.__bbsModel.idIndexes().values()]:
            # don't kwow why, it seems that from here, some actions shortcut are lost??
            # need to reapply them...
            if isinstance(item, BBSBrush):
                BBSSettings.setBrushShortcut(item, item.shortcut())
            else:
                BBSSettings.setGroupShortcut(item, item.shortcutNext(), item.shortcutPrevious())

        self.__restoreViewConfig()
        self.__saveSettings()
        self.accept()

    def closeEvent(self, event):
        """Window is closed"""
        self.__restoreViewConfig()
        self.__restoreShortcutConfig()
        self.reject()
