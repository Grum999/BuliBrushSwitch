#-----------------------------------------------------------------------------
# BuliBrushSwitch
# Copyright (C) 2020 - Grum999
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
# A Krita plugin designed to export as JPEG with a preview of final result
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
        BBSBrushes,
        BBSBrushesEditor
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



# -----------------------------------------------------------------------------
class BBSMainWindow(EDialog):
    """Main BuliBrushSwitch window"""

    def __init__(self, bbsName="BuliBrushSwitch", bbsVersion="testing", parent=None):
        super(BBSMainWindow, self).__init__(os.path.join(os.path.dirname(__file__), 'resources', 'bbsmainwindow.ui'), parent)

        # plugin name/version
        self.__bbsName = bbsName
        self.__bbsVersion = bbsVersion

        # not yet initialised
        self.__activeView=None

        if (Krita.instance().activeWindow() is None
            or Krita.instance().activeWindow().activeView() is None
            or Krita.instance().activeWindow().activeView().visible()==False
            or Krita.instance().activeWindow().activeView().document() is None):
            # why if no document is opened, there's an active view?
            # need to check if it's normal or not
            WDialogMessage.display(self.__bbsName+' - '+i18n(f'Ooops sorry!'),
                                   f'''<p>{i18n("There's no active document")}</p><p>{i18n("A document must be active to configure plugin...")}</p><p>
                                   <i>{i18n("It's sounds weird I know, even me I'm not happy with that but there's technical things with brushes and then I currently don't have choice in implementation...")}<br><br>Grum999</i></p>''',
                                   minSize=QSize(500,0))
            return

        BBSSettings.load()

        # current active view
        self.__activeView=Krita.instance().activeWindow().activeView()

        # keep in memory current view configuration to restore on dialog close
        self.__activeViewCurrentConfig={}

        # list of defined brushes
        self.__brushes=BBSBrushes()

        # keep a saved view of current brush shortcuts
        self.__savedShortcuts={}
        self.__createdShortcuts=[]

        self.setModal(True)
        self.setWindowTitle(i18n(f'{bbsName} v{bbsVersion}'))
        self.setWindowFlags(Qt.Dialog|Qt.WindowTitleHint)

        self.__saveViewConfig()
        self.__initialiseUi()
        self.__loadBrushes()
        self.__saveShortcutConfig()
        self.__updateBrushUi()

        self.__result=self.exec()

    def showEvent(self, event):
        """Dialog is visible"""
        self.tvBrushes.selectionModel().selectionChanged.connect(self.__brushesSelectionChanged)
        self.tvBrushes.resizeColumns()

    def __initialiseUi(self):
        """Initialise window interface"""
        self.__actionSelectBrushScratchpadColor=WMenuColorPicker()
        self.__actionSelectBrushScratchpadColor.colorPicker().colorUpdated.connect(self.__actionBrushScratchpadSetColor)
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_COMPACT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_PALETTE_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_PALETTE_DEFAULT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CWHEEL_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CWHEEL_CPREVIEW))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CCOMBINATION))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CCSS))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_RGB_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionDisplayAsPctColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_RGB_ASPCT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_CMYK_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionDisplayAsPctColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_CMYK_ASPCT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSL_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionDisplayAsPctColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSL_ASPCT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSV_VISIBLE))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionDisplayAsPctColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSV_ASPCT))
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionShowColorAlpha(False)
        self.__actionSelectBrushScratchpadColor.colorPicker().setOptionMenu(WColorPicker.OPTION_MENU_ALL&~WColorPicker.OPTION_MENU_ALPHA)

        menuBrushScratchpadColor = QMenu(self.tbBrushScratchpadColor)
        menuBrushScratchpadColor.addAction(self.__actionSelectBrushScratchpadColor)

        self.__actionSelectCurrentBrush=QAction(QIcon(QPixmap.fromImage(self.__activeViewCurrentConfig['brushPreset'].image())), i18n(f"Current painting brush ({self.__activeViewCurrentConfig['brushPreset'].name()})"), self)
        self.__actionSelectCurrentBrush.triggered.connect(self.__actionBrushAddCurrentBrushPreset)
        self.__actionSelectChoosenBrush=WMenuBrushesPresetSelector()
        self.__actionSelectChoosenBrush.presetChooser().presetClicked.connect(self.__actionBrushAddChoosenBrushPreset)

        self.__menuBrushAdd = QMenu(self.tbBrushAdd)
        self.__menuBrushAdd.addAction(self.__actionSelectCurrentBrush)
        self.__menuBrushAdd.addAction(self.__actionSelectChoosenBrush)

        # -- toolbar
        self.tbBrushAdd.setMenu(self.__menuBrushAdd)
        self.tbBrushEdit.clicked.connect(self.__actionBrushEdit)
        self.tbBrushDelete.clicked.connect(self.__actionBrushDelete)
        self.tbBrushMoveFirst.clicked.connect(self.__actionBrushMoveFirst)
        self.tbBrushMoveLast.clicked.connect(self.__actionBrushMoveLast)
        self.tbBrushMoveUp.clicked.connect(self.__actionBrushMoveUp)
        self.tbBrushMoveDown.clicked.connect(self.__actionBrushMoveDown)
        self.tbBrushScratchpadClear.clicked.connect(self.__actionBrushScratchpadClear)
        self.tbBrushScratchpadColor.setMenu(menuBrushScratchpadColor)

        self.hsBrushesThumbSize.setValue(self.tvBrushes.iconSizeIndex())
        self.hsBrushesThumbSize.valueChanged.connect(self.__brushesSizeIndexSliderChanged)

        # -- button mode
        if BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE)==BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST:
            self.rbFirstFromList.setChecked(True)
        else:
            self.rbLastSelected.setChecked(True)

        if BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE)==BBSSettingsValues.DEFAULT_MODIFICATIONMODE_IGNORE:
            self.rbModificationModeIgnore.setChecked(True)
        else:
            self.rbModificationModeKeep.setChecked(True)

        # -- brush list
        self.tvBrushes.doubleClicked.connect(self.__actionBrushEdit)
        self.tvBrushes.setBrushes(self.__brushes)
        self.tvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_ZOOMLEVEL))
        self.tvBrushes.iconSizeIndexChanged.connect(self.__brushesSizeIndexChanged)

        # -- scratchpad initialisation
        self.__scratchpadTestBrush=Scratchpad(self.__activeView, QColor(Qt.white), self)
        self.__scratchpadTestBrush.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.__scratchpadTestBrush.linkCanvasZoom(False)
        self.__scratchpadTestBrush.setModeManually(False)
        #self.__scratchpadTestBrush.setMode('painting') -- bug if set? (don't remember why commented ^_^')
        self.wBrushScratchpad.layout().addWidget(self.__scratchpadTestBrush)

        # -- dialog box bottom buttons
        self.pbOk.clicked.connect(self.__acceptChange)
        self.pbCancel.clicked.connect(self.__rejectChange)

        # -- dialog box geometry
        size=QSize(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_WIDTH), BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_HEIGHT))
        if size.width()<=0:
            size.setWidth(self.width())
        if size.height()<=0:
            size.setHeight(self.height())
        self.resize(size)

        position=QPoint(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_X), BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_Y))
        if position.x()!=-1 and position.y()!=1:
            self.move(position)

        self.splitterBrushes.setSizes(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION))

    def __loadBrushes(self):
        """Load brush configuration from settings"""
        nbBrushes=BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_COUNT)
        brushes=BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
        self.__brushes.beginUpdate()
        for brushNfo in brushes:
            brush=BBSBrush()
            if brush.importData(brushNfo):
                self.__brushes.add(brush)
        self.__brushes.endUpdate()

    def __saveShortcutConfig(self):
        """Save current action shortcuts

        During process, we need to udpate action shortcut directly (allows to take
        in account shortcut modification made on brush)
        """
        for brushId in self.__brushes.idList():
            action=Krita.instance().action(f'bulibrushswitch_brush_{brushId.strip("{}")}')
            if action:
                self.__savedShortcuts[brushId]=action.shortcut()

    def __restoreShortcutConfig(self):
        """Restore current shortcut configuration"""
        # for potential new action created, remove designed shortcut
        for brushId in self.__createdShortcuts:
            action=BBSSettings.brushAction(brushId)
            if action:
                action.setShortcut(QKeySequence())

        #??restore initial shortcuts
        for brushId in self.__savedShortcuts:
            action=BBSSettings.brushAction(brushId)
            if action:
                action.setShortcut(self.__savedShortcuts[brushId])

    def __saveViewConfig(self):
        """Save current Krita active view properties"""
        self.__activeViewCurrentConfig['brushSize']=self.__activeView.brushSize()
        self.__activeViewCurrentConfig['brushPreset']=EKritaBrushPreset.getPreset(self.__activeView.currentBrushPreset())

        self.__activeViewCurrentConfig['fgColor']=self.__activeView.foregroundColor()
        self.__activeViewCurrentConfig['bgColor']=self.__activeView.backgroundColor()

        self.__activeViewCurrentConfig['blendingMode']=self.__activeView.currentBlendingMode()
        #self.__activeViewCurrentConfig['gradient']=self.__activeView.currentGradient()
        #self.__activeViewCurrentConfig['pattern']=self.__activeView.currentPattern()

        self.__activeViewCurrentConfig['paintingOpacity']=self.__activeView.paintingOpacity()
        self.__activeViewCurrentConfig['paintingFlow']=self.__activeView.paintingFlow()

        # don't know why, but zoomLevel() and setZoomLevel() don't use same value
        # https://krita-artists.org/t/canvas-class-what-does-zoomlevel-returns-compared-to-setzoomlevel-manual-link-inside/15702/3?u=grum999
        # need to apply a factor to be sure to reapply the right zoom
        self.__activeViewCurrentConfig['zoom']=self.__activeView.canvas().zoomLevel()/(self.__activeView.document().resolution()*1/72)

    def __restoreViewConfig(self):
        """Restore view properties"""
        self.__activeView.setCurrentBrushPreset(self.__activeViewCurrentConfig['brushPreset'])
        self.__activeView.setBrushSize(self.__activeViewCurrentConfig['brushSize'])

        self.__activeView.setForeGroundColor(self.__activeViewCurrentConfig['fgColor'])
        self.__activeView.setBackGroundColor(self.__activeViewCurrentConfig['bgColor'])

        self.__activeView.setCurrentBlendingMode(self.__activeViewCurrentConfig['blendingMode'])
        # crash on gradient?
        #self.__activeView.setCurrentGradient(self.__activeViewCurrentConfig['gradient'])
        #self.__activeView.setCurrentPattern(self.__activeViewCurrentConfig['pattern'])

        self.__activeView.setPaintingOpacity(self.__activeViewCurrentConfig['paintingOpacity'])
        self.__activeView.setPaintingFlow(self.__activeViewCurrentConfig['paintingFlow'])

        self.__activeView.canvas().setZoomLevel(self.__activeViewCurrentConfig['zoom'])

    def __actionBrushScratchpadSetColor(self, color):
        """Set brush testing scratchpad color"""
        self.__activeView.setForeGroundColor(ManagedColor.fromQColor(color, self.__activeView.canvas()))

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
        self.__actionBrushAdd()

    def __actionBrushAddChoosenBrushPreset(self, resource):
        """Set current brush"""
        self.__menuBrushAdd.setVisible(False)
        self.__activeView.setCurrentBrushPreset(resource)
        self.__actionBrushAdd()

    def __applyBrushOptions(self, brush, options):
        """Apply options to brush"""
        brush.setComments(options[BBSBrush.KEY_COMMENTS])
        brush.setKeepUserModifications(options[BBSBrush.KEY_KEEPUSERMODIFICATIONS])
        brush.setIgnoreEraserMode(options[BBSBrush.KEY_IGNOREERASERMODE])
        brush.setColorFg(options[BBSBrush.KEY_COLOR_FG])
        brush.setColorBg(options[BBSBrush.KEY_COLOR_BG])
        brush.setDefaultPaintTool(options[BBSBrush.KEY_DEFAULTPAINTTOOL])
        brush.setBlendingMode(options[BBSBrush.KEY_BLENDINGMODE])
        brush.setSize(options[BBSBrush.KEY_SIZE])
        brush.setOpacity(options[BBSBrush.KEY_OPACITY])
        brush.setFlow(options[BBSBrush.KEY_FLOW])
        brush.setShortcut(options[BBSBrush.KEY_SHORTCUT])
        BBSSettings.setShortcut(brush, options[BBSBrush.KEY_SHORTCUT])

    def __actionBrushAdd(self):
        """Add a new brush in list (from current view brush)"""
        brush=BBSBrush()
        brush.fromCurrentKritaBrush(self.__activeView)
        options=BBSBrushesEditor.edit(self.__bbsName+' - '+i18n('Add brush'), brush)
        if not options is None:
            self.__applyBrushOptions(brush, options)
            self.__createdShortcuts.append(brush.id())
            self.__brushes.add(brush)
            self.__updateBrushUi()

    def __actionBrushEdit(self):
        """Edit brush from list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            brush=brushes[0]
            options=BBSBrushesEditor.edit(self.__bbsName+' - '+i18n(f'Edit brush'), brush)
            if not options is None:
                self.__applyBrushOptions(brush, options)
                self.__brushes.update(brush)
                self.__updateBrushUi()

    def __actionBrushDelete(self):
        """Remove brush from list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            brush=brushes[0]

            brushDescription="<br><br>"+brush.information(BBSBrush.INFO_WITH_BRUSH_DETAILS|BBSBrush.INFO_WITH_BRUSH_OPTIONS)+"<br><br>"

            if WDialogBooleanInput.display(self.__bbsName+' - '+i18n(f'Remove brush'),
                                           i18n(f"<b>Following brush will removed from user list</b>{brushDescription}<b>Do you confirm action?</b>"),
                                           minSize=QSize(950,400)):
                BBSSettings.setShortcut(brush, QKeySequence())
                self.__brushes.remove(brush)
                self.__updateBrushUi()

    def __actionBrushMoveFirst(self):
        """Move brush at first position in list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            self.__brushes.moveItemAtFirst(brushes[0])
            self.__updateBrushUi()

    def __actionBrushMoveLast(self):
        """Move brush at last position in list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            self.__brushes.moveItemAtLast(brushes[0])
            self.__updateBrushUi()

    def __actionBrushMoveUp(self):
        """Move brush at previous position in list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            self.__brushes.moveItemAtPrevious(brushes[0])
            self.__updateBrushUi()

    def __actionBrushMoveDown(self):
        """Move brush at next position in list"""
        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            self.__brushes.moveItemAtNext(brushes[0])
            self.__updateBrushUi()

    def __brushesSelectionChanged(self, selected, deselected):
        """Selection in treeview has changed, update UI"""
        self.__updateBrushUi()
        selectedBrushes=self.tvBrushes.selectedItems()
        if len(selectedBrushes)==1:
            if selectedBrushes[0].found():
                selectedBrushes[0].toCurrentKritaBrush()

    def __brushesSizeIndexSliderChanged(self, newSize):
        """Thumbnail size has been changed from brushes slider"""
        # update treeview
        self.tvBrushes.setIconSizeIndex(newSize)

    def __brushesSizeIndexChanged(self, newSize, newQSize):
        """Thumbnail size has been changed from brushes treeview"""
        # update slider
        self.hsBrushesThumbSize.setValue(newSize)

    def __updateBrushUi(self):
        """Update brushes UI (enable/disable buttons...)"""
        nbSelectedBrush=self.tvBrushes.nbSelectedItems()
        self.tbBrushEdit.setEnabled(nbSelectedBrush==1)
        self.tbBrushDelete.setEnabled(nbSelectedBrush==1)

        brushes=self.tvBrushes.selectedItems()
        if len(brushes):
            #??a brush is selected
            brush=brushes[0]
            self.tbBrushMoveFirst.setEnabled(brush.position()>0)
            self.tbBrushMoveLast.setEnabled(brush.position()<self.__brushes.length()-1)
            self.tbBrushMoveUp.setEnabled(brush.position()>0)
            self.tbBrushMoveDown.setEnabled(brush.position()<self.__brushes.length()-1)
        else:
            self.tbBrushMoveFirst.setEnabled(False)
            self.tbBrushMoveLast.setEnabled(False)
            self.tbBrushMoveUp.setEnabled(False)
            self.tbBrushMoveDown.setEnabled(False)

        if self.__brushes.length()>0:
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

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_COMPACT, self.__actionSelectBrushScratchpadColor.colorPicker().optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_PALETTE_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_PALETTE_DEFAULT, self.__actionSelectBrushScratchpadColor.colorPicker().optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CWHEEL_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CWHEEL_CPREVIEW, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CCOMBINATION, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CCSS, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_RGB_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_RGB_ASPCT, self.__actionSelectBrushScratchpadColor.colorPicker().optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_CMYK_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_CMYK_ASPCT, self.__actionSelectBrushScratchpadColor.colorPicker().optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSL_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSL_ASPCT, self.__actionSelectBrushScratchpadColor.colorPicker().optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSV_VISIBLE, self.__actionSelectBrushScratchpadColor.colorPicker().optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_CSLIDER_HSV_ASPCT, self.__actionSelectBrushScratchpadColor.colorPicker().optionDisplayAsPctColorHSV())

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION, self.splitterBrushes.sizes())

        BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_LIST_COUNT, self.__brushes.length())

        BBSSettings.setBrushes(self.__brushes)

        if BBSSettings.modified():
            BBSSettings.save()

    def __rejectChange(self):
        """User clicked on cancel button"""
        self.__restoreViewConfig()
        self.__restoreShortcutConfig()
        self.reject()

    def __acceptChange(self):
        """User clicked on OK button"""
        for brushId in self.__brushes.idList():
            # don't kwow why, it seems that from here, some actions shortcut  are lost??
            # need to reapply them...
            brush=self.__brushes.get(brushId)
            if brush:
                BBSSettings.setShortcut(brush, brush.shortcut())

        self.__restoreViewConfig()
        self.__saveSettings()
        self.accept()

    def closeEvent(self, event):
        """Window is closed"""
        self.__restoreViewConfig()
        self.accept()

    def result(self):
        """Result is accepted or rejected"""
        return self.__result
