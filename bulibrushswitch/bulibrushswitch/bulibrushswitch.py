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
# A Krita plugin designed to export as JPEG with a preview of final result
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
    from bulibrushswitch.bbs.bbswbrushes import BBSBrush
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
    from bulibrushswitch.bbs.bbswbrushes import BBSBrush
    from bulibrushswitch.bbs.bbssettings import (BBSSettings, BBSSettingsKey)
    from bulibrushswitch.bbs.bbsmainwindow import BBSMainWindow
    from bulibrushswitch.bbs.bbswbrushswitcher import BBSWBrushSwitcher

    print("======================================")


EXTENSION_ID = 'pykrita_bulibrushswitch'
PLUGIN_VERSION = '0.1.0b'
PLUGIN_MENU_ENTRY = 'Buli Brush Switch'

REQUIRED_KRITA_VERSION = (5, 0, 0)

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
        self.__dlgParentWidget=QWidget()
        self.__action=None
        self.__notifier=Krita.instance().notifier()


    def __windowCreated(self):
        """Main window has been created"""
        # consider that newly created window is active window (because no more information
        # is provided by signal)
        window=Krita.instance().activeWindow()
        installedWindow=BBSWBrushSwitcher.installToWindow(window, PLUGIN_MENU_ENTRY, PLUGIN_VERSION)

    def __kritaIsClosing(self):
        """Save configuration before closing"""
        if BBSSettings.modified():
            BBSSettings.saveConfig()

    def setup(self):
        """Is executed at Krita's startup"""
        if not self.__isKritaVersionOk:
            return

        UITheme.load()

        self.__notifier.windowCreated.connect(self.__windowCreated)
        self.__notifier.applicationClosing.connect(self.__kritaIsClosing)

    def createActions(self, window):
        """Create default actions for plugin"""
        if self.__isKritaVersionOk:
            BBSSettings.load()

            for actionId in BBSSettings.DEFAULT_ACTIONS:
                action = window.createAction(actionId, '', None)

            brushes=BBSSettings.get(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
            for brushNfo in brushes:
                action=BBSSettings.brushAction(brushNfo[BBSBrush.KEY_UUID], brushNfo[BBSBrush.KEY_NAME], brushNfo[BBSBrush.KEY_COMMENTS], True, window)


    def start(self):
        """Execute BuliBrushSwitch"""
        # ----------------------------------------------------------------------
        # Create dialog box
        BBSMainWindow(PLUGIN_MENU_ENTRY, PLUGIN_VERSION, self.__dlgParentWidget)
