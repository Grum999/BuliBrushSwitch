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
# - BBSWBrushSwitcher:
#       A widget displayed in toolbar and used to visualize/switch to BBS
#
# - BBSWBrushSwitcherUi:
#       Pop-out user interface for brush switcher
#
# -----------------------------------------------------------------------------
import re
from krita import (
        Krita,
        Window,
        View,
        ManagedColor
    )
from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )

from .bbssettings import (
        BBSSettings,
        BBSSettingsKey,
        BBSSettingsValues
    )

from .bbswbrushes import (
        BBSGroup,
        BBSBrush,
        BBSWBrushesTv,
        BBSWBrushesLv,
        BBSWGroupsTv,
        BBSModel,
        BBSBrushesProxyModel,
        BBSGroupsProxyModel
    )

from .bbsmainwindow import BBSMainWindow

from bulibrushswitch.pktk.modules.imgutils import buildIcon
from bulibrushswitch.pktk.modules.edialog import EDialog
from bulibrushswitch.pktk.modules.about import AboutWindow
from bulibrushswitch.pktk.modules.ekrita import EKritaBrushPreset
from bulibrushswitch.pktk.modules.ekrita_tools import EKritaTools
from bulibrushswitch.pktk.widgets.wseparator import WVLine
from bulibrushswitch.pktk.widgets.wtoolbarbutton import WToolbarButton

from bulibrushswitch.pktk.pktk import *


class BBSWBrushSwitcher(QWidget):
    """A widget displayed in toolbar and used to visualize/switch to BBS"""
    brushSelected = Signal(QVariant)

    @staticmethod
    def installToWindow(window, pluginName, pluginVersion):
        """Install an instance of BBSWBrushSwitcher to given window

        If instance already exists for window, does nothing
        """
        if not isinstance(window, Window):
            raise EInvalidType("Given `window` must be a <Window>")

        if not BBSWBrushSwitcher.isInstalledOnWindow(window):
            # not yet created

            # search for 'paintopbox' widget
            # ==> the switcher will be added in 'paintopbox' layout
            #     after 'Edit Brush Settings' and 'Choose Brush Preset'
            paintOpBox = window.qwindow().findChild(QWidget, 'paintopbox', Qt.FindChildrenRecursively)

            if paintOpBox is None:
                # not able to find it?? a normal case, cancel...
                return None

            containerWidget = paintOpBox.children()[1]

            # create BBSWBrushSwitcher instance
            returnedBbs = BBSWBrushSwitcher(pluginName, pluginVersion)

            # keep a reference at window level (easier to)
            window.setProperty('BBSWBrushSwitcher', returnedBbs)

            # add widget to Krita's UI
            containerWidget.layout().addWidget(returnedBbs)
            returnedBbs.update()
            return returnedBbs

    @staticmethod
    def isInstalledOnWindow(window):
        """return True if instance of BBSWBrushSwitcher is installed on given window"""
        if not isinstance(window, Window):
            raise EInvalidType("Given `window` must be a <Window>")

        return not(window.property('BBSWBrushSwitcher') is None)

    @staticmethod
    def fromWindow(window):
        """return instance of BBSWBrushSwitcher is installed on given window, otherwise None"""
        if not isinstance(window, Window):
            raise EInvalidType("Given `window` must be a <Window>")

        return window.property('BBSWBrushSwitcher')

    def __init__(self, pluginName, pluginVersion, parent=None):
        """Initialise tool button"""
        super(BBSWBrushSwitcher, self).__init__(parent)

        self.__bbsName = pluginName
        self.__bbsVersion = pluginVersion

        # define oibject name (easier to find widget in window children, if needed)
        self.setObjectName('bbs')

        # when tool is changed, need to fix opacity
        EKritaTools.notifier.toolChanged.connect(self.__kritaToolChanged)

        # need it...
        self.__dlgParentWidget = QWidget()

        # don't use a QToolButton with MenuButtonPopup because when checkable,
        # right button is checked and it start to be difficult to manage popup
        # events...
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.__tbBrush = WToolbarButton()
        self.__tbBrush.setAutoRaise(True)
        self.__tbBrush.setMinimumSize(32, 32)
        self.__tbBrush.setObjectName("btIcon")
        self.__tbBrush.clicked.connect(self.setActiveBrush)

        self.__tbPopup = QToolButton()
        self.__tbPopup.setArrowType(Qt.DownArrow)
        self.__tbPopup.setAutoRaise(True)
        self.__tbPopup.setMaximumWidth(16)
        self.__tbPopup.setObjectName("btArrow")
        self.__tbPopup.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.MinimumExpanding)
        self.__tbPopup.clicked.connect(self.__displayPopupUi)

        layout.addWidget(self.__tbBrush)
        layout.addWidget(self.__tbPopup)

        # list of available brushes
        self.__bbsModel = BBSModel()
        self.__actionPopupUi = BBSWBrushSwitcherUi(self, self.__bbsName, self.__bbsVersion)

        # current selected brush (used when direct click on __tbBrush button)
        self.__selectedBrushId = None

        # which icon is displayed in button __tbBrush
        self.__selectedBrushMode = BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST

        # For brush with specific color/paint tool, when color/paint tool is modified, how
        # switch back to initial brush is managed
        self.__selectedBrushModificationMode = BBSSettingsValues.DEFAULT_MODIFICATIONMODE_KEEP

        # memorized brush from Krita
        self.__kritaBrush = None

        # current applied brush (if None, then plugin is not "active")
        self.__selectedBrush = None

        # flag to determinate if brush shortcut have to be updated when shorcut
        # for related action has been modified
        self.__disableUpdatingShortcutFromAction = False

        # keep a reference to action "set eraser mode"
        self.__actionEraserMode = Krita.instance().action('erase_action')
        self.__actionEraserMode.triggered.connect(self.__eraserModeActivated)

        # current opacity value
        # used as a 'cache' value when tool is changed and brush require to ignore tool opacity
        self.__currentOpacity = 1.0

        # flag to indicate a brush selection is already ongoing
        self.__brushSelectionOnGoing = False

        # indicate which group is currently looping to next/prev brush
        # None is none :-)
        self.__loopingGroup = None

        # keep reference for all actions
        action = Krita.instance().action('bulibrushswitch_settings')
        action.triggered.connect(self.openSettings)

        action = Krita.instance().action('bulibrushswitch_activate_default')
        action.triggered.connect(self.setActiveBrush)

        action = Krita.instance().action('bulibrushswitch_deactivate')
        action.triggered.connect(lambda: self.setActiveBrush(None))

        action = Krita.instance().action('bulibrushswitch_show_brushes_list')
        action.triggered.connect(self.__displayPopupUi)

        self.setLayout(layout)
        self.__reloadBrushes()

    def __getFirstBrush(self):
        """Return first brush in tree, according to position sort"""
        def searchFromNode(node):
            items = self.__bbsModel.getGroupItems(node, False)
            brushes = [item for item in items if isinstance(item, BBSBrush)]
            if len(brushes) > 0:
                return brushes[0]
            for group in [item for item in items if isinstance(item, BBSGroup)]:
                found = searchFromNode(group.id())
                if found:
                    return found
            return None

        return searchFromNode(None)

    def __setSelectedBrushId(self, brushId=None):
        """Set `brushName` as new selected brush

        If given `brushName` is None (or not found in list of brush), first brush
        in list will be defined as current selected brush name
        """
        updated = False
        brushIdList = self.__bbsModel.idIndexes({'groups': False})

        if self.__selectedBrushMode == BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST:
            selectedBrush = self.__getFirstBrush()
            # always use the first item from brush list
            if selectedBrush is not None and self.__selectedBrushId != selectedBrush.id():
                self.__selectedBrushId = selectedBrush.id()
                updated = True
        elif brushId in brushIdList:
            # in list
            if self.__selectedBrushId != brushId:
                # and not the current selected brush, use it
                self.__selectedBrushId = brushId
                selectedBrush = self.__bbsModel.getFromId(self.__selectedBrushId, False)
                updated = True
        else:
            selectedBrush = self.__getFirstBrush()
            if selectedBrush is not None and self.__selectedBrushId != selectedBrush.id():
                # not in list, use the first one
                self.__selectedBrushId = selectedBrush.id()
                updated = True

        BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_LAST_SELECTED, self.__selectedBrushId)

        if updated:
            # update icon...
            self.__tbBrush.setIcon(QIcon(QPixmap.fromImage(selectedBrush.image())))
            self.__tbBrush.setToolTip(selectedBrush.information(BBSBrush.INFO_WITH_DETAILS | BBSBrush.INFO_WITH_OPTIONS))

    @pyqtSlot(bool)
    def __setSelectedBrushFromAction(self, checked):
        """An action has been triggered to select a brush"""
        if self.__loopingGroup:
            # currently looping on a group; need to indicate group we stop to loop
            self.__loopingGroup.resetBrushIfNeeded()
            self.__loopingGroup = None

        action = self.sender()
        brush = self.__bbsModel.getFromId(action.data(), False)
        self.setActiveBrush(brush)

    @pyqtSlot(bool)
    def __setSelectedGroupNextFromAction(self, checked):
        """An action has been triggered to select a brush from a group"""
        action = self.sender()
        group = self.__bbsModel.getFromId(action.data().removesuffix("-N"), False)
        if group:
            if self.__loopingGroup and self.__loopingGroup != group:
                # currently looping on a group; need to indicate group we stop to loop
                self.__loopingGroup.resetBrushIfNeeded()

            self.__loopingGroup = group

            brush = group.getNextBrush()
            self.setActiveBrush(brush)

    @pyqtSlot(bool)
    def __setSelectedGroupPreviousFromAction(self, checked):
        """An action has been triggered to select a brush"""
        action = self.sender()
        group = self.__bbsModel.getFromId(action.data().removesuffix("-P"), False)
        if group:
            if self.__loopingGroup and self.__loopingGroup != group:
                # currently looping on a group; need to indicate group we stop to loop
                self.__loopingGroup.resetBrushIfNeeded()

            self.__loopingGroup = group

            brush = group.getPrevBrush()
            self.setActiveBrush(brush)

    @pyqtSlot()
    def __setShortcutFromAction(self):
        """An action has been changed

        Many change made on action can trigger this method
        Also, it seems that when changing current tool, action are changed and
        shortcut is "reset"

        Then we have to:
        - Ensure that we're not already in a call of this method
        - Determinate if we are from Krita's settings window (KisShortcutsDialog widget exists)
            > If yes, accept change
            > If no, reject change (reapply shortcut from brush)
        """
        if self.__disableUpdatingShortcutFromAction:
            # already in the method, or plugin settings dialog is opened
            return
        self.__disableUpdatingShortcutFromAction = True

        action = self.sender()
        item = self.__bbsModel.getFromId(action.data(), False)
        if isinstance(item, BBSBrush):
            # a brush is defined for action
            obj = Krita.instance().activeWindow().qwindow().findChild(QWidget, 'KisShortcutsDialog')
            if obj:
                # shortcut has been modified from settings dialog
                # update brush
                item.setShortcut(action.shortcut())
            else:
                # shortcut has been molified from???
                # force shortcut from brush
                item.setShortcut(item.shortcut())
            # reapply shortcut to action
            BBSSettings.setBrushShortcut(item, item.shortcut())
        elif isinstance(item, BBSGroup):
            # a group is defined for action
            obj = Krita.instance().activeWindow().qwindow().findChild(QWidget, 'KisShortcutsDialog')
            if re.search("-N$", action.data()):
                if obj:
                    # shortcut has been modified from settings dialog
                    # update group
                    item.setShortcutNext(action.shortcut())
                else:
                    # shortcut has been molified from???
                    # force shortcut from brush
                    item.setShortcutNext(item.shortcutNext())
            else:
                if obj:
                    # shortcut has been modified from settings dialog
                    # update group
                    item.setShortcutPrevious(action.shortcut())
                else:
                    # shortcut has been molified from???
                    # force shortcut from brush
                    item.setShortcutPrevious(item.shortcutPrevious())

            # reapply shortcut to action
            BBSSettings.setGroupShortcut(item, item.shortcutNext(), item.shortcutPrevious())

        self.__disableUpdatingShortcutFromAction = False

    def __reloadBrushes(self):
        """Brushes configurations has been modified; reload"""
        self.__selectedBrushMode = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE)
        self.__selectedBrushModificationMode = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE)

        # cleanup all current action shortcuts
        # not made from model to let possibility to work on removed items if needed
        for id in self.__bbsModel.idIndexes():
            item = self.__bbsModel.getFromId(id, False)
            if isinstance(item, BBSBrush):
                action = item.action()
                if action:
                    try:
                        action.triggered.disconnect(self.__setSelectedBrushFromAction)
                    except Exception:
                        pass
                    try:
                        action.changed.disconnect(self.__setSelectedBrushFromAction)
                    except Exception:
                        pass
            else:
                actionNext = item.actionNext()
                if actionNext:
                    try:
                        actionNext.triggered.disconnect(self.__setSelectedGroupNextFromAction)
                    except Exception:
                        pass
                    try:
                        actionNext.changed.disconnect(self.__setSelectedGroupNextFromAction)
                    except Exception:
                        pass

                actionPrevious = item.actionPrevious()
                if actionPrevious:
                    try:
                        actionPrevious.triggered.disconnect(self.__setSelectedGroupPreviousFromAction)
                    except Exception:
                        pass
                    try:
                        actionPrevious.changed.disconnect(self.__setSelectedGroupPreviousFromAction)
                    except Exception:
                        pass

        brushesAndGroups = []

        # create BBSBrush object + link action shortcuts
        brushesDictList = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
        for brushNfo in brushesDictList:
            brush = BBSBrush()
            if brush.importData(brushNfo):
                action = brush.action()
                if action:
                    try:
                        action.triggered.disconnect(self.__setSelectedBrushFromAction)
                    except Exception:
                        pass

                    try:
                        action.changed.disconnect(self.__setSelectedBrushFromAction)
                    except Exception:
                        pass

                    action.triggered.connect(self.__setSelectedBrushFromAction)
                    action.changed.connect(self.__setShortcutFromAction)
                brushesAndGroups.append(brush)

        groupsDictList = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_GROUPS)
        for groupNfo in groupsDictList:
            group = BBSGroup()
            if group.importData(groupNfo):
                actionNext = group.actionNext()
                if actionNext:
                    try:
                        actionNext.triggered.disconnect(self.__setSelectedGroupNextFromAction)
                    except Exception:
                        pass

                    try:
                        actionNext.changed.disconnect(self.__setSelectedGroupNextFromAction)
                    except Exception:
                        pass

                    actionNext.triggered.connect(self.__setSelectedGroupNextFromAction)
                    actionNext.changed.connect(self.__setShortcutFromAction)

                actionPrevious = group.actionPrevious()
                if actionPrevious:
                    try:
                        actionPrevious.triggered.disconnect(self.__setSelectedGroupPreviousFromAction)
                    except Exception:
                        pass

                    try:
                        actionPrevious.changed.disconnect(self.__setSelectedGroupPreviousFromAction)
                    except Exception:
                        pass

                    actionPrevious.triggered.connect(self.__setSelectedGroupPreviousFromAction)
                    actionPrevious.changed.connect(self.__setShortcutFromAction)

                brushesAndGroups.append(group)

        self.__bbsModel.importData(brushesAndGroups, BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_NODES))
        self.__setSelectedBrushId(self.__selectedBrushId)

    def __displayPopupUi(self):
        """Display popup user interface"""
        self.__keepUserModif()
        action = Krita.instance().action('view_show_canvas_only')
        if action and action.isChecked():
            self.__actionPopupUi.showRelativeTo(QCursor.pos())
        else:
            self.__actionPopupUi.showRelativeTo(self)

    def __disconnectResourceSignal(self):
        """Disconnect resource signal to __presetChanged() method"""
        try:
            EKritaBrushPreset.presetChooserWidget().currentResourceChanged.disconnect(self.__presetChanged)
        except Exception:
            pass

    def __connectResourceSignal(self):
        """Connect resource signal to __presetChanged() method"""
        # need to be sure there's no connection:
        self.__disconnectResourceSignal()
        EKritaBrushPreset.presetChooserWidget().currentResourceChanged.connect(self.__presetChanged)

    def __eraserModeActivated(self, dummy=None):
        """Eraser mode has been activated/deactivated"""
        if self.__selectedBrush is not None and self.__selectedBrush.ignoreEraserMode() and self.__actionEraserMode.isChecked() != self.__selectedBrush.eraserMode():
            # if we have a brush for which we have to ignore eraser mode, force eraser status to the one defined in brush
            self.__actionEraserMode.setChecked(self.__selectedBrush.eraserMode())

    def __presetChanged(self, dummy=None):
        """Called when preset has been changed in Krita"""
        # normally, it shouldn't occurs when preset is modified by plugin
        # only if preset is changed outside plugin
        #
        # new brush is already active Krita
        if self.__selectedBrush is not None and self.__selectedBrush.keepUserModifications():
            # we need to keep settings for plugin's brush...
            #
            # need to disconnect to avoid recursives call...
            self.__disconnectResourceSignal()

            # get current view
            view = Krita.instance().activeWindow().activeView()

            # temporary memorize brush that have been selected
            tmpKritaBrush = view.currentBrushPreset()

            # restore plugin's brush, without settings (just use brush)
            view.setCurrentBrushPreset(EKritaBrushPreset.getPreset(self.__selectedBrush.name()))
            # now, Krita has "restored" brush settings, save them
            self.__keepUserModif()

            # switch back to selected preset
            view.setCurrentBrushPreset(tmpKritaBrush)

        # deactivate current brush
        self.setActiveBrush(None, False)

    def __keepUserModif(self):
        """Update (or not) user modification to current brush, according to brush settings"""
        if self.__selectedBrush is not None and self.__selectedBrush.keepUserModifications():
            # a brush for which modidications have to be kept
            if self.__selectedBrush.ignoreEraserMode():
                pass

            saveOptions = 0
            if self.__selectedBrush.colorFg():
                saveOptions |= BBSBrush.KRITA_BRUSH_FGCOLOR

            if self.__selectedBrush.colorBg():
                saveOptions |= BBSBrush.KRITA_BRUSH_BGCOLOR

            if self.__selectedBrush.colorGradient():
                saveOptions |= BBSBrush.KRITA_BRUSH_GRADIENT

            if self.__selectedBrush.defaultPaintTool():
                saveOptions |= BBSBrush.KRITA_BRUSH_TOOLOPT

            self.__selectedBrush.fromCurrentKritaBrush(saveOptions=saveOptions)

            BBSSettings.setBrushes([self.__bbsModel.data(index, BBSModel.ROLE_DATA) for index in self.__bbsModel.idIndexes({'groups': False}).values()])
            if BBSSettings.modified():
                # autosave modification settings all the time!
                # no full save (False): save settings only, no need to save actions files too here
                BBSSettings.save(False)

    def __kritaToolChanged(self, toolId, activated):
        if not activated:
            view = Krita.instance().activeWindow().activeView()
            if view:
                self.__currentOpacity = view.paintingOpacity()
        elif self.__selectedBrush and self.__selectedBrush.ignoreToolOpacity():
            view = Krita.instance().activeWindow().activeView()
            if view:
                view.setPaintingOpacity(self.__currentOpacity)

    def openSettings(self):
        """Open settings dialog box"""
        self.__disableUpdatingShortcutFromAction = True
        if BBSMainWindow.open(self.__bbsName, self.__bbsVersion, self.__dlgParentWidget):
            # settings has been saved; reload brushes
            self.__reloadBrushes()
        self.__disableUpdatingShortcutFromAction = False

    def openAbout(self):
        """Open settings dialog box"""
        AboutWindow(self.__bbsName, self.__bbsVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':BuliBrushSwitch')

    def brushesModel(self):
        """Return brush list model"""
        return self.__bbsModel

    def setActiveBrush(self, value, restoreKritaBrush=True):
        """Activate/deactivate current selected brush

        If `restoreKritaBrush` is True,
        """
        def finalize():
            self.brushSelected.emit(self.__selectedBrush)
            self.__brushSelectionOnGoing = False

        if self.__brushSelectionOnGoing:
            return

        self.__brushSelectionOnGoing = True

        if isinstance(value, BBSBrush):
            # brush is provided
            selectedBrush = value
            selectedBrushId = value.id()
        elif isinstance(value, bool):
            # toggle status from __tbBrush button
            # -- need to keep current
            if self.__selectedBrush is None:
                # activate current "selectedBrushId"
                selectedBrush = self.__bbsModel.getFromId(self.__selectedBrushId, False)
                selectedBrushId = self.__selectedBrushId
            else:
                # deactivate current "selectedBrushId"
                selectedBrush = None
                selectedBrushId = None
        elif value is None:
            # want to deactivate current brush
            selectedBrush = None
            selectedBrushId = None
        else:
            raise EInvalidType("Given `value` must be <str> or <BBSBrush> or <bool>")

        if selectedBrush is None:
            if self.__loopingGroup:
                # currently looping on a group; need to indicate group we stop to loop
                self.__loopingGroup.resetBrushIfNeeded()
                self.__loopingGroup = None


        if selectedBrush == self.__selectedBrush:
            selectedBrush = None
            selectedBrushId = None

        view = Krita.instance().activeWindow().activeView()

        # keep current plugin brush color
        applyBrushColor = True
        applyBrushTool = True

        if selectedBrush is None:
            # "deactivate" current brush
            self.__disconnectResourceSignal()

            # keep user modification made on current brush, if needed
            self.__keepUserModif()

        if self.__selectedBrush:
            # restore original Krita's brush properties if available
            if self.__selectedBrush.colorFg() is None:
                # brush don't have a specific color
                # do not keep current color (restore initial Krita's brush color)
                applyBrushColor = False

            if self.__selectedBrush.defaultPaintTool() is None:
                # brush don't have a specific paint tool
                # do not keep current paint tool (restore initial Krita's paint tool)
                applyBrushTool = False

            if applyBrushColor:
                if self.__selectedBrushModificationMode == BBSSettingsValues.DEFAULT_MODIFICATIONMODE_KEEP:
                    currentFg = view.foregroundColor().colorForCanvas(view.canvas())
                    currentBg = view.backgroundColor().colorForCanvas(view.canvas())

                    if self.__selectedBrush.colorFg() != currentFg or (not self.__selectedBrush.colorBg() is None and self.__selectedBrush.colorBg() != currentBg):
                        applyBrushColor = False

            if applyBrushTool:
                if self.__selectedBrushModificationMode == BBSSettingsValues.DEFAULT_MODIFICATIONMODE_KEEP:
                    currentPaintTool = EKritaTools.current()

                    if currentPaintTool and self.__selectedBrush.defaultPaintTool() != currentPaintTool:
                        applyBrushTool = False

            self.__selectedBrush.restoreKritaBrush(applyBrushColor, applyBrushTool)

        if selectedBrush is None:
            # "deactivate" current brush
            # no need anymore to be aware for brushes change
            self.__disconnectResourceSignal()

            if restoreKritaBrush and self.__kritaBrush:
                # restore Krita's brush, if asked (default...)
                #
                # case when not asked: brush as been changed outside plugin
                # in this case don't need to restore brush, and no need to
                # keep user modification as already processed in __keepUserModif()

                # restore Krita's brush, if asked
                self.__kritaBrush.toCurrentKritaBrush(None, applyBrushColor, applyBrushTool)
            elif self.__kritaBrush and restoreKritaBrush is False:
                # do not restore Krita's brush, but a krita's brush exist
                #
                # case when not asked: brush as been changed outside plugin
                # in this case don't need to restore brush, but we want to restore
                # initial colors

                if applyBrushColor:
                    colorFg = self.__kritaBrush.colorFg()
                    colorBg = self.__kritaBrush.colorBg()

                    if colorFg and view:
                        view.setForeGroundColor(ManagedColor.fromQColor(colorFg, view.canvas()))
                    if colorBg and view:
                        view.setBackGroundColor(ManagedColor.fromQColor(colorBg, view.canvas()))

                if applyBrushTool:
                    paintTool = self.__kritaBrush.defaultPaintTool()

                    if paintTool:
                        action = Krita.instance().action(paintTool)
                        if action:
                            action.trigger()

            self.__kritaBrush = None
            self.__selectedBrush = None
            self.setStyleSheet("")
        else:
            if self.__kritaBrush is None:
                # memorize current Krita brush to finally restore when plugin brush is "deactivated"
                self.__kritaBrush = BBSBrush()
                self.__kritaBrush.setIgnoreEraserMode(False)
                if not self.__kritaBrush.fromCurrentKritaBrush(None,
                                                               BBSBrush.KRITA_BRUSH_FGCOLOR |
                                                               BBSBrush.KRITA_BRUSH_BGCOLOR |
                                                               BBSBrush.KRITA_BRUSH_GRADIENT |
                                                               BBSBrush.KRITA_BRUSH_TOOLOPT):
                    self.__kritaBrush = None
                    self.__brushSelectionOnGoing = False
                    finalize()
                    return
            else:
                # already using brush activated from plugin
                # temporary disable signal management
                self.__disconnectResourceSignal()

            # apply current asked brush
            self.__setSelectedBrushId(selectedBrushId)
            self.__selectedBrush = selectedBrush
            self.__selectedBrush.toCurrentKritaBrush()

            # Highlight widget to indicate it's active
            self.setStyleSheet("""
                QToolButton#btIcon {
                    background: palette(Highlight);
                    border-top-left-radius: 2px;
                    border-bottom-left-radius: 2px;
                }
                QToolButton#btArrow{
                    background: palette(Highlight);
                    border-top-right-radius: 2px;
                    border-bottom-right-radius: 2px;
                }
                """)
            # need to be aware for brushes change (should occurs when change is made outside plugin)
            self.__connectResourceSignal()
        finalize()

    def activeBrush(self):
        """Return current active brush, or None if BBSBrush is not active"""
        return self.__selectedBrush


class BBSWBrushSwitcherUi(QFrame):
    """User interface for brush switcher"""

    def __init__(self, brushSwitcher, pluginName, pluginVersion, parent=None):
        super(BBSWBrushSwitcherUi, self).__init__(parent)

        self.__bbsName = pluginName
        self.__bbsVersion = pluginVersion

        # brushSwitcher instance
        self.__brushSwitcher = brushSwitcher

        # list of brushes
        self.__bbsModel = brushSwitcher.brushesModel()
        self.__bbsModel.modelReset.connect(self.__updateCtBrushes)
        self.__bbsBrushesModel = BBSBrushesProxyModel()
        self.__bbsBrushesModel.setSourceModel(self.__bbsModel)
        self.__bbsGroupsModel = BBSGroupsProxyModel()
        self.__bbsGroupsModel.setSourceModel(self.__bbsModel)

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setLineWidth(1)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        # widget content
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)

        # tree view mode
        self.__tvBrushes = BBSWBrushesTv()
        self.__tvBrushes.setModel(self.__bbsModel)
        self.__tvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL))
        self.__tvBrushes.setIndentation(0)
        self.__tvBrushes.setCompactIconSizeIndex(2)
        self.__tvBrushes.iconSizeIndexChanged.connect(self.__brushesSizeIndexChanged)
        self.__tvBrushes.collapsed.connect(self.__groupExpandCollapse)
        self.__tvBrushes.expanded.connect(self.__groupExpandCollapse)
        self.__tvBrushes.header().sectionResized.connect(self.__brushesColumnResized)
        self.__tvBrushes.setDragEnabled(False)
        self.__tvBrushes.setSelectionMode(QAbstractItemView.SingleSelection)
        self.__tvBrushesInitialised = False

        # list view mode
        self.__tvGroups = BBSWGroupsTv()
        self.__tvGroups.setModel(self.__bbsGroupsModel)
        self.__tvGroups.collapsed.connect(self.__groupExpandCollapse)
        self.__tvGroups.expanded.connect(self.__groupExpandCollapse)

        self.__lvBrushes = BBSWBrushesLv()
        self.__lvBrushes.setModel(self.__bbsBrushesModel)
        self.__lvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL))
        self.__lvBrushes.iconSizeIndexChanged.connect(self.__brushesSizeIndexChanged)
        self.__lvBrushes.setDragEnabled(False)
        self.__lvBrushes.setSelectionMode(QAbstractItemView.SingleSelection)


        self.__splBrushes = QSplitter()
        self.__splBrushes.setOrientation(Qt.Horizontal)
        self.__splBrushes.addWidget(self.__tvGroups)
        self.__splBrushes.addWidget(self.__lvBrushes)
        self.__splBrushes.splitterMoved.connect(self.__splitterViewIconMoved)

        # layout
        self.__viewLayout = QStackedLayout()
        self.__viewLayout.addWidget(self.__tvBrushes)
        self.__viewLayout.addWidget(self.__splBrushes)

        self.__statusBar = QStatusBar()
        self.__statusBar.setSizeGripEnabled(True)

        currentViewIsListMode = (BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE) == BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST)
        self.__actionModeGroup = QActionGroup(self)
        self.__actionListMode = QAction(buildIcon('pktk:list_view_details'), i18n("List view"))
        self.__actionListMode.setCheckable(True)
        self.__actionListMode.setChecked(currentViewIsListMode)
        self.__actionListMode.setActionGroup(self.__actionModeGroup)
        self.__actionListMode.setData(BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST)
        self.__actionListMode.toggled.connect(self.__brushesViewModeChanged)
        self.__actionIconMode = QAction(buildIcon('pktk:list_view_icon'), i18n("Icon view"))
        self.__actionIconMode.setCheckable(True)
        self.__actionIconMode.setChecked(not currentViewIsListMode)
        self.__actionIconMode.setActionGroup(self.__actionModeGroup)
        self.__actionIconMode.setData(BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_ICON)
        self.__actionIconMode.toggled.connect(self.__brushesViewModeChanged)

        self.__tbViewMode = QToolButton(self)
        self.__tbViewMode.setAutoRaise(True)
        self.__tbViewMode.setPopupMode(QToolButton.InstantPopup)
        self.__tbViewMode.setToolTip(i18n("Select brushes view mode"))
        if currentViewIsListMode:
            self.__tbViewMode.setIcon(self.__actionListMode.icon())
        else:
            self.__tbViewMode.setIcon(self.__actionIconMode.icon())
        self.__menuViewMode = QMenu(self.__tbViewMode)
        self.__menuViewMode.addAction(self.__actionListMode)
        self.__menuViewMode.addAction(self.__actionIconMode)
        self.__tbViewMode.setMenu(self.__menuViewMode)

        self.__hsBrushesThumbSize = QSlider()
        self.__hsBrushesThumbSize.setOrientation(Qt.Horizontal)
        self.__hsBrushesThumbSize.setMinimum(0)
        self.__hsBrushesThumbSize.setMaximum(4)
        self.__hsBrushesThumbSize.setSingleStep(1)
        self.__hsBrushesThumbSize.setPageStep(1)
        self.__hsBrushesThumbSize.setTracking(True)
        self.__hsBrushesThumbSize.setMaximumWidth(150)
        self.__hsBrushesThumbSize.setValue(self.__tvBrushes.iconSizeIndex())
        self.__hsBrushesThumbSize.setToolTip(i18n("Icon size"))
        self.__hsBrushesThumbSize.valueChanged.connect(self.__brushesSizeIndexSliderChanged)

        self.__tbSettings = QToolButton()
        self.__tbSettings.setIcon(buildIcon("pktk:tune"))
        self.__tbSettings.setAutoRaise(True)
        self.__tbSettings.setToolTip(i18n("Settings"))
        self.__tbSettings.clicked.connect(self.__brushSwitcher.openSettings)

        self.__tbAbout = QToolButton()
        self.__tbAbout.setIcon(buildIcon("pktk:info"))
        self.__tbAbout.setAutoRaise(True)
        self.__tbAbout.setToolTip(i18n("About <i>Buli Brush Switch</i>"))
        self.__tbAbout.clicked.connect(self.__brushSwitcher.openAbout)

        self.__statusBar.addPermanentWidget(self.__tbViewMode)
        self.__statusBar.addPermanentWidget(self.__hsBrushesThumbSize)
        self.__statusBar.addPermanentWidget(WVLine())
        self.__statusBar.addPermanentWidget(self.__tbSettings)
        self.__statusBar.addWidget(self.__tbAbout)

        layout.addLayout(self.__viewLayout)
        layout.addWidget(self.__statusBar)

        self.__viewLayout.setCurrentIndex(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE))

        width = BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_WIDTH)
        height = BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_HEIGHT)
        if height <= 0:
            height = 550
        if width <= 0:
            width = 950

        self.__inSelectionUpdate = False

        self.setLayout(layout)
        self.resize(width, height)
        self.setVisible(False)

        self.__splBrushes.setSizes(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE_ICON_SPLITTER_POSITION))

        self.__brushSwitcher.brushSelected.connect(self.selectBrush)

    def __splitterViewIconMoved(self, pos, index):
        """Splitter position has been modified"""
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE_ICON_SPLITTER_POSITION, self.__splBrushes.sizes())

    def __brushesViewModeChanged(self, dummy=None):
        """View mode has been changed"""
        self.__viewLayout.setCurrentIndex(self.sender().data())
        self.__tbViewMode.setIcon(self.sender().icon())
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE, self.sender().data())

    def __updateCtBrushes(self):
        """Model has been reset; need to expand/collapse groups"""
        groupIndex = self.__bbsGroupsModel.getIndexFromId(BBSGroupsProxyModel.UUID_USERVIEW)
        self.__tvGroups.scrollTo(groupIndex, QAbstractItemView.EnsureVisible)
        self.__tvGroups.expand(groupIndex)

    def __updateTvGroupsSelectionChanged(self, index):
        """From list view mode, a group has been selected"""
        data = self.__tvGroups.selectedItems()
        if data is not None:
            self.__inSelectionUpdate = True
            if data.id() ==  BBSGroupsProxyModel.UUID_FLATVIEW:
                self.__bbsBrushesModel.setParentId(None)
            elif data.id() ==  BBSGroupsProxyModel.UUID_USERVIEW:
                self.__bbsBrushesModel.setParentId(BBSGroupsProxyModel.UUID_ROOTNODE)
            else:
                self.__bbsBrushesModel.setParentId(data.id())

            self.__lvBrushes.selectItem(self.__brushSwitcher.activeBrush())
            self.__inSelectionUpdate = False

    def __selectAndScrollToBrush(self, brush, widgetView):
        """Scroll to given brush for given widgetView"""
        if widgetView == self.__lvBrushes:
            # need to check/update __tvGroups before
            selectedgroup = self.__tvGroups.selectedItems()
            if selectedgroup is None or selectedgroup.id() != BBSGroupsProxyModel.UUID_FLATVIEW:
                # if in flat view, stay in flat view
                # otherwise need to find in which group the item is, and select (+expand) the group
                groupId = brush.node().parentNode().data().id()
                if groupId == BBSGroupsProxyModel.UUID_ROOTNODE:
                    groupId = BBSGroupsProxyModel.UUID_USERVIEW

                groupIndex = self.__bbsGroupsModel.getIndexFromId(groupId)
                self.__tvGroups.scrollTo(groupIndex, QAbstractItemView.EnsureVisible)
                self.__tvGroups.selectItem(groupIndex.data(BBSModel.ROLE_DATA))

                if groupId == BBSGroupsProxyModel.UUID_USERVIEW:
                    groupId = BBSGroupsProxyModel.UUID_ROOTNODE
                self.__bbsBrushesModel.setParentId(groupId)
            inViewIndex = self.__bbsBrushesModel.getIndexFromId(brush.id())
        else:
            inViewIndex = self.__bbsModel.getFromId(brush.id(), True)

        widgetView.scrollTo(inViewIndex, QAbstractItemView.EnsureVisible)
        widgetView.selectItem(brush)

    def __brushesSelectionChanged(self, selected=None, deselected=None):
        """Selection in treeview has changed, update UI"""
        if self.__inSelectionUpdate:
            return

        self.__inSelectionUpdate = True

        if BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE) == BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST:
            selectedBrushes = self.__tvBrushes.selectedItems()
            selectInView = self.__lvBrushes
        else:
            selectedBrushes = self.__lvBrushes.selectedItems()
            selectInView = self.__tvBrushes

        if len(selectedBrushes) == 1:
            if isinstance(selectedBrushes[0], BBSBrush):
                if selectedBrushes[0].found():
                    self.__selectAndScrollToBrush(selectedBrushes[0], selectInView)
                    self.__brushSwitcher.setActiveBrush(selectedBrushes[0])
                    self.hide()
        self.__inSelectionUpdate = False

    def __brushesSizeIndexChanged(self, newSize, newQSize):
        """Thumbnail size has been changed from brushes treeview/lisview"""
        # update slider
        self.__hsBrushesThumbSize.setValue(newSize)
        # update settings
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL, newSize)

    def __brushesSizeIndexSliderChanged(self, newSize):
        """Thumbnail size has been changed from brushes slider"""
        # update treeview
        self.__tvBrushes.setIconSizeIndex(newSize)
        self.__lvBrushes.setIconSizeIndex(newSize)

    def __groupExpandCollapse(self, index):
        """Group is expanded or collapsed; save state in configuration file"""
        exportedData = self.__bbsModel.exportData()
        BBSSettings.setGroups(exportedData['groups'])
        if BBSSettings.modified():
            BBSSettings.save()

    def __brushesColumnResized(self, logicalIndex, oldSize, newSize):
        """Brushes column resized, keep it in settings"""
        if logicalIndex == BBSModel.COLNUM_BRUSH:
            BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_COLWIDTH, newSize)
            if BBSSettings.modified():
                BBSSettings.save()

    def selectBrush(self, brush):
        """Select given brush (BBSBrush)
        Both __tvBrushes and __lvBrushes+__tvGroups are updated
        """
        if isinstance(brush, BBSBrush) and brush.found():
            self.__selectAndScrollToBrush(brush, self.__lvBrushes)
            self.__selectAndScrollToBrush(brush, self.__tvBrushes)
        elif brush is None:
            # case there's no active brush
            self.__lvBrushes.selectItem(None)
            self.__tvBrushes.selectItem(None)

    def keyPressEvent(self, event):
        """Check if need to close window"""
        if event.type() == QEvent.KeyPress:
            action = Krita.instance().action('bulibrushswitch_show_brushes_list')

            if action and action.shortcut().toString() != '':
                # a shortcut has been defined to popup list
                key = event.key()

                if key in (Qt.Key_unknown, Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
                    newKeySequence = QKeySequence(key)
                else:
                    # combination of keys
                    modifiers = event.modifiers()
                    # if the keyText is empty than it's a special key like F1, F5, ...
                    keyText = event.text()

                    if modifiers & Qt.ShiftModifier:
                        key += Qt.SHIFT
                    if modifiers & Qt.ControlModifier:
                        key += Qt.CTRL
                    if modifiers & Qt.AltModifier:
                        key += Qt.ALT
                    if modifiers & Qt.MetaModifier:
                        key += Qt.META

                    newKeySequence = QKeySequence(key)

                if newKeySequence.matches(action.shortcut()) == QKeySequence.ExactMatch:
                    event.accept()
                    self.close()
                    return

        super(BBSWBrushSwitcherUi, self).keyPressEvent(event)

    def showEvent(self, event):
        """Widget is visible"""
        if not self.__tvBrushesInitialised:
            # if user click on an already selected item, selectionChanged signal is not emitted
            #
            # if user click on an item that is not selected, selectionChanged signal is emitted
            # but clicked signal is not
            #
            # add signal for both case, to ensure that when a item is clicked or selected, the
            # brush selection method is executed
            self.__tvBrushes.selectionModel().selectionChanged.connect(self.__brushesSelectionChanged)
            self.__lvBrushes.selectionModel().selectionChanged.connect(self.__brushesSelectionChanged)
            self.__tvGroups.selectionModel().selectionChanged.connect(self.__updateTvGroupsSelectionChanged)

            self.__tvBrushes.clicked.connect(self.__brushesSelectionChanged)
            self.__lvBrushes.clicked.connect(self.__brushesSelectionChanged)
            self.__tvGroups.clicked.connect(self.__updateTvGroupsSelectionChanged)

            self.__updateCtBrushes()

            self.__tvGroups.selectItem(self.__bbsGroupsModel.getIndexFromId(BBSGroupsProxyModel.UUID_FLATVIEW).data(BBSModel.ROLE_DATA))

            self.__tvBrushesInitialised = True

        colSize = BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_COLWIDTH)
        if colSize > 0:
            self.__tvBrushes.header().resizeSection(BBSModel.COLNUM_BRUSH, colSize)
        else:
            self.__tvBrushes.resizeColumns()
        self.selectBrush(self.__brushSwitcher.activeBrush())

    def resizeEvent(self, event):
        """Widget has been resized"""
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_WIDTH, event.size().width())
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_HEIGHT, event.size().height())

    def focusOutEvent(self, event):
        """Widget lost focus

        If focus is not on a child, hide widget
        """
        if (self.__tbSettings.hasFocus()
           or self.__hsBrushesThumbSize.hasFocus()
           or self.__tbAbout.hasFocus()):
            return
        elif self.__tvBrushes.hasFocus() or self.__lvBrushes.hasFocus() or self.__tvGroups.hasFocus():
            # let "selectionChanged" and/or "clicked" signal manage this case
            return

        self.hide()

    def showRelativeTo(self, origin):
        """Show ui using given `widget` as reference for position"""
        if isinstance(origin, QWidget):
            # display under button
            screenPosition = origin.mapToGlobal(QPoint(0, origin.height()))
            checkPosition = QPoint(screenPosition)
        else:
            # display under cursor
            screenPosition = origin
            checkPosition = QPoint(origin)
            screenPosition.setX(screenPosition.x() - self.width()//2)
            screenPosition.setY(screenPosition.y() - self.height()//2)

        # need to ensure popup is not "outside" visible screen
        for screen in QGuiApplication.screens():
            screenRect = screen.availableGeometry()
            if screenRect.contains(checkPosition):
                # we're on the right screen
                # need to check if window if displayed properly in screen
                relativePosition = screenPosition - screenRect.topLeft()

                if screenPosition.x() < screenRect.left():
                    screenPosition.setX(screenRect.left())
                elif screenPosition.x() + self.width() > screenRect.right():
                    screenPosition.setX(screenRect.right() - self.width())

                if screenPosition.y() < screenRect.top():
                    screenPosition.setY(screenRect.top())
                elif screenPosition.y() + self.height() > screenRect.bottom():
                    screenPosition.setY(screenRect.bottom() - self.height())

        self.move(screenPosition)
        self.setVisible(True)
        self.setFocus(True)
