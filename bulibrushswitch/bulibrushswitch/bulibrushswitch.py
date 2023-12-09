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

import os
import re
import sys
import time

import PyQt5.uic

from krita import (
        Extension,
        Krita
    )

from PyQt5.Qt import *
from PyQt5 import QtCore
from PyQt5.QtCore import (
        pyqtSlot
    )

if __name__ != '__main__':
    # script is executed from Krita, loaded as a module
    __PLUGIN_EXEC_FROM__ = 'KRITA'

    from .pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )
    from bulibrushswitch.pktk.modules.utils import checkKritaVersion
    from bulibrushswitch.pktk.modules.uitheme import UITheme
    from bulibrushswitch.bbs.bbswbrushes import (BBSBrush, BBSGroup)
    from bulibrushswitch.bbs.bbssettings import (BBSSettings, BBSSettingsKey)
    from bulibrushswitch.bbs.bbsmainwindow import BBSMainWindow
    from bulibrushswitch.bbs.bbswbrushswitcher import BBSWBrushSwitcher
else:
    # Execution from 'Scripter' plugin?
    __PLUGIN_EXEC_FROM__ = 'SCRIPTER_PLUGIN'

    from importlib import reload

    print("======================================")
    print(f'Execution from {__PLUGIN_EXEC_FROM__}')

    for module in list(sys.modules.keys()):
        if not re.search(r'^bulibrushswitch\.', module) is None:
            print('Reload module {0}: {1}', module, sys.modules[module])
            reload(sys.modules[module])

    from bulibrushswitch.pktk.pktk import (
            EInvalidStatus,
            EInvalidType,
            EInvalidValue,
            PkTk
        )
    from bulibrushswitch.pktk.modules.utils import checkKritaVersion
    from bulibrushswitch.pktk.modules.uitheme import UITheme
    from bulibrushswitch.bbs.bbswbrushes import (BBSBrush, BBSGroup)
    from bulibrushswitch.bbs.bbssettings import (BBSSettings, BBSSettingsKey)
    from bulibrushswitch.bbs.bbsmainwindow import BBSMainWindow
    from bulibrushswitch.bbs.bbswbrushswitcher import BBSWBrushSwitcher

    print("======================================")


EXTENSION_ID = 'pykrita_bulibrushswitch'
PLUGIN_VERSION = '1.0.3'
PLUGIN_MENU_ENTRY = 'Buli Brush Switch'

REQUIRED_KRITA_VERSION = (5, 2, 0)

PkTk.setPackageName('bulibrushswitch')


class BuliBrushSwitch(Extension):

    def __init__(self, parent):
        # Default options

        # Always initialise the superclass.
        # This is necessary to create the underlying C++ object
        super(BuliBrushSwitch, self).__init__(parent)
        self.parent = parent
        self.__uiController = None
        self.__isKritaVersionOk = checkKritaVersion(*REQUIRED_KRITA_VERSION)
        self.__action = None
        self.__notifier = Krita.instance().notifier()

    @pyqtSlot()
    def __windowCreated(self):
        """Main window has been created"""
        # consider that newly created window is active window (because no more information
        # is provided by signal)
        window = Krita.instance().activeWindow()
        installedWindow = BBSWBrushSwitcher.installToWindow(window, PLUGIN_MENU_ENTRY, PLUGIN_VERSION)

    @pyqtSlot()
    def __kritaIsClosing(self):
        """Save configuration before closing"""
        if BBSSettings.modified():
            BBSSettings.save()

    def setup(self):
        """Is executed at Krita's startup"""
        if not self.__isKritaVersionOk:
            return

        UITheme.load()

        self.__notifier.setActive(True)
        self.__notifier.windowCreated.connect(self.__windowCreated)

        # self.__notifier.applicationClosing.connect(self.__kritaIsClosing)
        # doesn't work, use QApplication signal instead
        QApplication.instance().aboutToQuit.connect(self.__kritaIsClosing)

    def createActions(self, window):
        """Create default actions for plugin"""
        if self.__isKritaVersionOk:
            BBSSettings.load()

            for actionId in BBSSettings.DEFAULT_ACTIONS:
                action = window.createAction(actionId, '', None)

            brushes = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
            for brushNfo in brushes:
                if BBSBrush.KEY_UUID in brushNfo and BBSBrush.KEY_NAME in brushNfo and BBSBrush.KEY_COMMENTS in brushNfo:
                    action = BBSSettings.brushAction(brushNfo[BBSBrush.KEY_UUID], brushNfo[BBSBrush.KEY_NAME], brushNfo[BBSBrush.KEY_COMMENTS], True, window)

                    if BBSBrush.KEY_SHORTCUT in brushNfo and brushNfo[BBSBrush.KEY_SHORTCUT]:
                        # action will be loaded with defaul shortcut
                        # force "dedicated" shortcut to be the same than default one to
                        # avoid problems with Krita's user defined shortcut definition
                        action.setShortcut(QKeySequence(brushNfo[BBSBrush.KEY_SHORTCUT]))

            groups = BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_GROUPS)
            for groupNfo in groups:
                if BBSGroup.KEY_UUID in groupNfo and BBSGroup.KEY_NAME in groupNfo and BBSGroup.KEY_COMMENTS in groupNfo:
                    actionNext = BBSSettings.groupAction(groupNfo[BBSBrush.KEY_UUID], 'N', groupNfo[BBSGroup.KEY_NAME], groupNfo[BBSGroup.KEY_COMMENTS], True, window)
                    if BBSGroup.KEY_SHORTCUT_NEXT in groupNfo and groupNfo[BBSGroup.KEY_SHORTCUT_NEXT]:
                        # action will be loaded with defaul shortcut
                        # force "dedicated" shortcut to be the same than default one to
                        # avoid problems with Krita's user defined shortcut definition
                        actionNext.setShortcut(QKeySequence(groupNfo[BBSGroup.KEY_SHORTCUT_NEXT]))

                    actionPrevious = BBSSettings.groupAction(groupNfo[BBSBrush.KEY_UUID], 'P', groupNfo[BBSGroup.KEY_NAME], groupNfo[BBSGroup.KEY_COMMENTS], True, window)
                    if BBSGroup.KEY_SHORTCUT_PREV in groupNfo and groupNfo[BBSGroup.KEY_SHORTCUT_PREV]:
                        # action will be loaded with defaul shortcut
                        # force "dedicated" shortcut to be the same than default one to
                        # avoid problems with Krita's user defined shortcut definition
                        actionPrevious.setShortcut(QKeySequence(groupNfo[BBSGroup.KEY_SHORTCUT_PREV]))