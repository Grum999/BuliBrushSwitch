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

from krita import (
        Krita,
        Window
    )
from PyQt5.Qt import *

from .bbssettings import (
        BBSSettings,
        BBSSettingsKey,
        BBSSettingsValues
    )

from .bbswbrushes import (
        BBSBrush,
        BBSBrushes,
        BBSWBrushesTv,
        BBSWBrushesLv
    )

from .bbsmainwindow import BBSMainWindow

from bulibrushswitch.pktk.modules.imgutils import buildIcon
from bulibrushswitch.pktk.modules.edialog import EDialog
from bulibrushswitch.pktk.modules.about import AboutWindow
from bulibrushswitch.pktk.modules.ekrita import EKritaBrushPreset
from bulibrushswitch.pktk.widgets.wseparator import WVLine


from bulibrushswitch.pktk.pktk import *



class BBSWBrushSwitcher(QWidget):
    """A widget displayed in toolbar and used to visualize/switch to BBS"""


    @staticmethod
    def installToWindow(window, pluginName, pluginVersion):
        """Install an instance of BBSWBrushSwitcher to given window

        If instance already exists for window, does nothing
        """
        if not isinstance(window, Window):
            raise EInvalidType("Given `window` must be a <Window>")

        if not BBSWBrushSwitcher.isInstalledOnWindow(window):
            # not yet created

            # search for 'paintopbox' widget
            # ==> the switcher will be added in 'paintopbox' layout
            #     after 'Edit Brush Settings' and 'Choose Brush Preset'
            paintOpBox=window.qwindow().findChild(QWidget, 'paintopbox', Qt.FindChildrenRecursively)

            if paintOpBox is None:
                # not able to find it?? a normal case, cancel...
                return None

            containerWidget=paintOpBox.children()[1]

            # create BBSWBrushSwitcher instance
            returnedBbs=BBSWBrushSwitcher(pluginName, pluginVersion)

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

        self.__bbsName=pluginName
        self.__bbsVersion=pluginVersion

        # define oibject name (easier to find widget in window children, if needed)
        self.setObjectName('bbs')

        # when settings are saved, need to reload brushes
        BBSSettings.settingsSaved().connect(lambda: self.__reloadBrushes())

        # need it...
        self.__dlgParentWidget=QWidget()

        # don't use a QToolButton with MenuButtonPopup because when checkable,
        # right button is checked and it start to be difficult to manage popup
        # events...
        layout=QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        self.__tbBrush=QToolButton()
        self.__tbBrush.setAutoRaise(True)
        self.__tbBrush.setMinimumSize(32,32)
        self.__tbBrush.setObjectName("btIcon")
        self.__tbBrush.clicked.connect(self.setBrushActivated)

        self.__tbPopup=QToolButton()
        self.__tbPopup.setArrowType(Qt.DownArrow)
        self.__tbPopup.setAutoRaise(True)
        self.__tbPopup.setMaximumWidth(16)
        self.__tbPopup.setObjectName("btArrow")
        self.__tbPopup.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.MinimumExpanding)
        self.__tbPopup.clicked.connect(self.__displayPopupUi)

        layout.addWidget(self.__tbBrush)
        layout.addWidget(self.__tbPopup)

        # list of available brushes
        self.__brushes=BBSBrushes()
        self.__actionPopupUi=BBSWBrushSwitcherUi(self, self.__bbsName, self.__bbsVersion)

        # current selected brush (used when direct click on __tbBrush button)
        self.__selectedBrushName=None

        # wich icon is displayed in button __tbBrush
        self.__selectedBrushMode=BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST

        # memorized brush from Krita
        self.__kritaBrush=None

        # current applied brush (if None, then plugin is not "active")
        self.__selectedBrush=None

        # flag to determinate if brush shortcut have to be updated when shorcut
        # for related action has been modified
        self.__disableUpdatingShortcutFromAction=False

        # keep a reference to action "set eraser mode"
        self.__actionEraserMode=Krita.instance().action('erase_action')
        self.__actionEraserMode.triggered.connect(self.__eraserModeActivated)

        # keep reference for all actions
        action=Krita.instance().action('bulibrushswitch_settings')
        action.triggered.connect(self.openSettings)

        action=Krita.instance().action('bulibrushswitch_activate_default')
        action.triggered.connect(self.setBrushActivated)

        action=Krita.instance().action('bulibrushswitch_deactivate')
        action.triggered.connect(lambda: self.setBrushActivated(None))

        action=Krita.instance().action('bulibrushswitch_show_brushes_list')
        action.triggered.connect(self.__displayPopupUi)

        self.setLayout(layout)
        self.__reloadBrushes()

    def __setSelectedBrushName(self, brushName=None):
        """Set `brushName` as new selected brush

        If given `brushName` is None (or not found in list of brush), first brush
        in list will be defined as current selected brush name
        """
        updated=False
        brushNames=self.__brushes.namesList()

        if self.__selectedBrushMode==BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST:
            # always use the first item from brush list
            if self.__selectedBrushName!=brushNames[0]:
                self.__selectedBrushName=brushNames[0]
                updated=True
        elif brushName in brushNames:
            if self.__selectedBrushName!=brushName:
                self.__selectedBrushName=brushName
                updated=True
        elif self.__selectedBrushName!=brushNames[0]:
            self.__selectedBrushName=brushNames[0]
            updated=True

        BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_LAST_SELECTED, self.__selectedBrushName)

        if updated:
            # update icon...
            brush=self.__brushes.getFromName(self.__selectedBrushName)
            self.__tbBrush.setIcon(QIcon(QPixmap.fromImage(brush.image())))

    @pyqtSlot(bool)
    def __setSelectedBrushFromAction(self, checked):
        """An action has been triggered to select a brush"""
        action=self.sender()
        brush=self.__brushes.get(action.data())
        self.setBrushActivated(brush)

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
        self.__disableUpdatingShortcutFromAction=True

        action=self.sender()
        brush=self.__brushes.get(action.data())
        if brush:
            # a brush is defined for action
            obj=Krita.instance().activeWindow().qwindow().findChild(QWidget,'KisShortcutsDialog')
            if obj:
                # shortcut has been modified from settings dialog
                # update brush
                brush.setShortcut(action.shortcut())
            else:
                # shortcut has been molified from???
                # force shortcut from brush
                brush.setShortcut(brush.shortcut())
            # reapply shortcut to action
            BBSSettings.setShortcut(brush, brush.shortcut())
        self.__disableUpdatingShortcutFromAction=False

    def __reloadBrushes(self):
        """Brushes configurations has been modified; reload"""
        self.__selectedBrushMode=BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE)

        # cleanup current action shortcuts
        for brushId in self.__brushes.idList():
            action=self.__brushes.get(brushId).action()
            if action:
                try:
                    action.triggered.disconnect(self.__setSelectedBrushFromAction)
                except:
                    pass
                try:
                    action.changed.disconnect(self.__setSelectedBrushFromAction)
                except:
                    pass

        # appky action shortcuts
        brushes=BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
        self.__brushes.beginUpdate()
        self.__brushes.clear()
        for brushNfo in brushes:
            brush=BBSBrush()
            if brush.importData(brushNfo):
                action=brush.action()
                if action:
                    try:
                        action.triggered.disconnect(self.__setSelectedBrushFromAction)
                    except:
                        pass

                    try:
                        action.changed.disconnect(self.__setSelectedBrushFromAction)
                    except:
                        pass

                    action.triggered.connect(self.__setSelectedBrushFromAction)
                    action.changed.connect(self.__setShortcutFromAction)
                self.__brushes.add(brush)
        self.__brushes.endUpdate()
        self.__setSelectedBrushName(self.__selectedBrushName)

    def __displayPopupUi(self):
        """Display popup user interface"""
        action=Krita.instance().action('view_show_canvas_only')
        if action and action.isChecked():
            self.__actionPopupUi.showRelativeTo(QCursor.pos())
        else:
            self.__actionPopupUi.showRelativeTo(self)

    def __disconnectResourceSignal(self):
        """Disconnect resource signal to __presetChanged() method"""
        try:
            EKritaBrushPreset.presetChooserWidget().currentResourceChanged.disconnect(self.__presetChanged)
        except:
            pass

    def __connectResourceSignal(self):
        """Connect resource signal to __presetChanged() method"""
        # need to be sure there's no connection:
        self.__disconnectResourceSignal()
        EKritaBrushPreset.presetChooserWidget().currentResourceChanged.connect(self.__presetChanged)

    def __eraserModeActivated(self, dummy=None):
        """Eraser mode has been activated/deactivated"""
        if not self.__selectedBrush is None and self.__selectedBrush.ignoreEraserMode() and self.__actionEraserMode.isChecked()!=self.__selectedBrush.eraserMode():
            # if we have a brush for which we have to ignore eraser mode, force eraser status to the one defined in brush
            self.__actionEraserMode.setChecked(self.__selectedBrush.eraserMode())

    def __presetChanged(self, dummy=None):
        """Called when preset has been changed in Krita"""
        # normally, it shouldn't occurs when preset is modified by plugin
        # only if preset is changed outside plugin
        #
        # new brush is already active Krita
        if not self.__selectedBrush is None and self.__selectedBrush.keepUserModifications():
            # we need to keep settings for brush...
            #
            # need to disconnect to avoid recursives call...
            self.__disconnectResourceSignal()

            # get current view
            view = Krita.instance().activeWindow().activeView()

            # temporary memorize brush that have been selected
            tmpKritaBrush=view.currentBrushPreset()

            # restore plugin's brush, without settings (just use brush)
            view.setCurrentBrushPreset(EKritaBrushPreset.getPreset(self.__selectedBrush.name()))
            # now, Krita has "restored" brush settings, save them
            self.__keepUserModif()

            # switch back to selected preset
            view.setCurrentBrushPreset(tmpKritaBrush)

        # deactivate current brush
        self.setBrushActivated(None, False)

    def __keepUserModif(self):
        """Update (or not) user modification to current brush, according to brush settings"""
        if not self.__selectedBrush is None and self.__selectedBrush.keepUserModifications():
            # a brush fo which modidications has to be kept
            if self.__selectedBrush.ignoreEraserMode():
                pass

            if self.__selectedBrush.color():
                saveColor=True
            else:
                saveColor=False

            if self.__selectedBrush.defaultPaintTool():
                saveTool=True
            else:
                saveTool=False

            self.__selectedBrush.fromCurrentKritaBrush(saveColor=saveColor, saveTool=saveTool)

            BBSSettings.setBrushes(self.__brushes)

    def openSettings(self):
        """Open settings dialog box"""
        self.__disableUpdatingShortcutFromAction=True
        BBSMainWindow(self.__bbsName, self.__bbsVersion, self.__dlgParentWidget)
        self.__disableUpdatingShortcutFromAction=False

    def openAbout(self):
        """Open settings dialog box"""
        AboutWindow(self.__bbsName, self.__bbsVersion, os.path.join(os.path.dirname(__file__), 'resources', 'png', 'buli-powered-big.png'), None, ':BuliBrushSwitch')

    def brushes(self):
        """Return brush list"""
        return self.__brushes

    def setBrushActivated(self, value, restoreKritaBrush=True):
        """Activate/deactivate current selected brush

        If `restoreKritaBrush` is True,
        """
        if isinstance(value, BBSBrush):
            # brush is provided
            selectedBrush=value
            selectedBrushName=value.name()
        elif isinstance(value, bool):
            # toggle status from __tbBrush button
            # -- need to keep current
            if self.__selectedBrush is None:
                # activate current "selectedBrushName"
                selectedBrush=self.__brushes.getFromName(self.__selectedBrushName)
                selectedBrushName=self.__selectedBrushName
            else:
                # deactivate current "selectedBrushName"
                selectedBrush=None
                selectedBrushName=None
        elif value is None:
            # want to deactivate current brush
            selectedBrush=None
            selectedBrushName=None
        else:
            raise EInvalidType("Given `value` must be <str> or <BBSBrush> or <bool>")

        if selectedBrush==self.__selectedBrush:
            selectedBrush=None
            selectedBrushName=None

        if selectedBrush is None:
            # "deactivate" current brush
            # no need anymore to be aware for brushes change
            self.__disconnectResourceSignal()

            if restoreKritaBrush and self.__kritaBrush:
                # restore Krita's brush, if asked (default...)
                #
                # case when not asked: brush as been changed outside plugin
                # in this case don't need to restore brush, and no need to
                # keep user modificatin as already processed in __keepUserModif()

                # keep user modification made on current brush, if needed
                self.__keepUserModif()

                # restore Krita's brush, if asked
                self.__kritaBrush.toCurrentKritaBrush()

            self.__kritaBrush=None
            self.__selectedBrush=None
            self.setStyleSheet("")
        else:
            if self.__kritaBrush is None:
                # memorize current Krita brush to finally restore when plugin brush is "deactivated"
                self.__kritaBrush=BBSBrush()
                self.__kritaBrush.setIgnoreEraserMode(False)
                if not self.__kritaBrush.fromCurrentKritaBrush(saveColor=True, saveTool=True):
                    self.__kritaBrush=None
                    return
            else:
                # already using brush activated from plugin
                # temporary disable signal management
                self.__disconnectResourceSignal()

            # keep user modification made on current brush, if needed
            self.__keepUserModif()

            # apply current asked brush
            self.__setSelectedBrushName(selectedBrushName)
            self.__selectedBrush=selectedBrush
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



class BBSWBrushSwitcherUi(QFrame):
    """User interface for brush switcher"""

    def __init__(self, brushSwitcher, pluginName, pluginVersion, parent=None):
        super(BBSWBrushSwitcherUi, self).__init__(parent)

        self.__bbsName=pluginName
        self.__bbsVersion=pluginVersion

        # brushSwitcher instance
        self.__brushSwitcher=brushSwitcher

        # list of brushes
        self.__brushes=brushSwitcher.brushes()

        self.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setLineWidth(1)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        # widget content
        layout=QVBoxLayout()
        layout.setContentsMargins(3,3,3,3)

        self.__tvBrushes=BBSWBrushesTv()
        self.__tvBrushes.setBrushes(self.__brushes)
        self.__tvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL))
        self.__tvBrushes.setIndentation(0)
        self.__tvBrushes.setRootIsDecorated(False)
        self.__tvBrushes.setAllColumnsShowFocus(True)
        self.__tvBrushes.setCompactIconSizeIndex(2)
        self.__tvBrushes.iconSizeIndexChanged.connect(self.__brushesSizeIndexChanged)
        self.__tvBrushesInitialised=False

        self.__lvBrushes=BBSWBrushesLv()
        self.__lvBrushes.setBrushes(self.__brushes)
        self.__lvBrushes.setIconSizeIndex(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL))
        self.__lvBrushes.iconSizeIndexChanged.connect(self.__brushesSizeIndexChanged)

        self.__viewLayout=QStackedLayout()
        self.__viewLayout.addWidget(self.__tvBrushes)
        self.__viewLayout.addWidget(self.__lvBrushes)

        self.__statusBar=QStatusBar()
        self.__statusBar.setSizeGripEnabled(True)

        currentViewIsListMode=(BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE)==BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST)
        self.__actionModeGroup=QActionGroup(self)
        self.__actionListMode=QAction(buildIcon('pktk:list_view_details'), i18n("List view"))
        self.__actionListMode.setCheckable(True)
        self.__actionListMode.setChecked(currentViewIsListMode)
        self.__actionListMode.setActionGroup(self.__actionModeGroup)
        self.__actionListMode.setData(BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST)
        self.__actionListMode.toggled.connect(self.__brushesViewModeChanged)
        self.__actionIconMode=QAction(buildIcon('pktk:list_view_icon'), i18n("Icon view"))
        self.__actionIconMode.setCheckable(True)
        self.__actionIconMode.setChecked(not currentViewIsListMode)
        self.__actionIconMode.setActionGroup(self.__actionModeGroup)
        self.__actionIconMode.setData(BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_ICON)
        self.__actionIconMode.toggled.connect(self.__brushesViewModeChanged)

        self.__tbViewMode=QToolButton(self)
        self.__tbViewMode.setAutoRaise(True)
        self.__tbViewMode.setPopupMode(QToolButton.InstantPopup)
        self.__tbViewMode.setToolTip(i18n("Select brushes view mode"))
        if currentViewIsListMode:
            self.__tbViewMode.setIcon(self.__actionListMode.icon())
        else:
            self.__tbViewMode.setIcon(self.__actionIconMode.icon())
        self.__menuViewMode=QMenu(self.__tbViewMode)
        self.__menuViewMode.addAction(self.__actionListMode)
        self.__menuViewMode.addAction(self.__actionIconMode)
        self.__tbViewMode.setMenu(self.__menuViewMode)

        self.__hsBrushesThumbSize=QSlider()
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

        self.__tbSettings=QToolButton()
        self.__tbSettings.setIcon(buildIcon("pktk:tune"))
        self.__tbSettings.setAutoRaise(True)
        self.__tbSettings.setToolTip(i18n("Settings"))
        self.__tbSettings.clicked.connect(self.__brushSwitcher.openSettings)

        self.__tbAbout=QToolButton()
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

        width=BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_WIDTH)
        height=BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_HEIGHT)
        if height<=0:
            height=550
        if width<=0:
            width=950

        self.__inSelectionUpdate=False

        self.setLayout(layout)
        self.resize(width, height)
        self.setVisible(False)

    def __brushesViewModeChanged(self, dummy=None):
        """View mode has been changed"""
        self.__viewLayout.setCurrentIndex(self.sender().data())
        self.__tbViewMode.setIcon(self.sender().icon())
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE, self.sender().data())

    def __brushesSelectionChanged(self, selected=None, deselected=None):
        """Selection in treeview has changed, update UI"""
        if self.__inSelectionUpdate:
            return
        self.__inSelectionUpdate=True
        if BBSSettings.get(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE)==BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST:
            selectedBrushes=self.__tvBrushes.selectedItems()
            selectInView=self.__lvBrushes
        else:
            selectedBrushes=self.__lvBrushes.selectedItems()
            selectInView=self.__tvBrushes

        if len(selectedBrushes)==1:
            if selectedBrushes[0].found():
                self.__brushSwitcher.setBrushActivated(selectedBrushes[0])
                selectInView.selectItem(selectedBrushes[0])
                self.hide()
        self.__inSelectionUpdate=False

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

    def keyPressEvent(self, event):
        """Check if need to close window"""
        if event.type() == QEvent.KeyPress:
            action=Krita.instance().action('bulibrushswitch_show_brushes_list')

            if action and action.shortcut().toString()!='':
                # a shortcut has been defined to popup list
                key = event.key()

                if key in (Qt.Key_unknown, Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
                    newKeySequence=self.setKeySequence(QKeySequence(key))
                else:
                    # combination of keys
                    modifiers = event.modifiers()
                    # if the keyText is empty than it's a special key like F1, F5, ...
                    keyText = event.text()

                    if modifiers & Qt.ShiftModifier:
                        key+=Qt.SHIFT
                    if modifiers & Qt.ControlModifier:
                        key+=Qt.CTRL
                    if modifiers & Qt.AltModifier:
                        key+=Qt.ALT
                    if modifiers & Qt.MetaModifier:
                        key+=Qt.META

                    newKeySequence=QKeySequence(key)


                if newKeySequence.matches(action.shortcut())==QKeySequence.ExactMatch:
                    event.accept()
                    self.close()
                    return

        super(BBSWBrushSwitcherUi, self).keyPressEvent(event)

    def showEvent(self, event):
        """Widget is visible"""
        if not self.__tvBrushesInitialised:
            self.__tvBrushes.selectionModel().selectionChanged.connect(self.__brushesSelectionChanged)
            self.__lvBrushes.selectionModel().selectionChanged.connect(self.__brushesSelectionChanged)
            self.__tvBrushesInitialised=True
        self.__tvBrushes.resizeColumns()

    def resizeEvent(self, event):
        """Widget has been resized"""
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_WIDTH, event.size().width())
        BBSSettings.set(BBSSettingsKey.CONFIG_UI_POPUP_HEIGHT, event.size().height())

    def focusOutEvent(self, event):
        """Widget lost focus

        If focus is not on a child, hide widget
        """
        if (self.__tbSettings.hasFocus() or
            self.__hsBrushesThumbSize.hasFocus() or
            self.__tbAbout.hasFocus()):
            return
        elif self.__tvBrushes.hasFocus() or self.__lvBrushes.hasFocus():
            self.__brushesSelectionChanged()
            return

        self.hide()

    def showRelativeTo(self, origin):
        """Show ui using given `widget` as reference for position"""
        if isinstance(origin, QWidget):
            # display under button
            screenPosition=origin.mapToGlobal(QPoint(0,origin.height()))
            checkPosition=QPoint(screenPosition)
        else:
            # display under cursor
            screenPosition=origin
            checkPosition=QPoint(origin)
            screenPosition.setX(screenPosition.x() - self.width()//2)
            screenPosition.setY(screenPosition.y() - self.height()//2)

        # need to ensure popup is not "outside" visible screen
        for screen in QGuiApplication.screens():
            screenRect=screen.availableGeometry()
            if screenRect.contains(checkPosition):
                # we're on the right screen
                # need to check if window if displayed properly in screen
                relativePosition=screenPosition - screenRect.topLeft()

                if screenPosition.x()<screenRect.left():
                    screenPosition.setX(screenRect.left())
                elif screenPosition.x() + self.width() > screenRect.right():
                    screenPosition.setX(screenRect.right() - self.width())

                if screenPosition.y()<screenRect.top():
                    screenPosition.setY(screenRect.top())
                elif screenPosition.y() + self.height() > screenRect.bottom():
                    screenPosition.setY(screenRect.bottom() - self.height())

        self.move(screenPosition)
        self.setVisible(True)
        self.setFocus(True)
