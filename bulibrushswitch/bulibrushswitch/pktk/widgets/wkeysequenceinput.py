#-----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2021 - Grum999
#
# A toolkit to make pykrita plugin coding easier :-)
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


# -----------------------------------------------------------------------------
from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QKeySequenceEdit

from ..modules.utils import replaceLineEditClearButton

class WKeySequenceInput(QKeySequenceEdit):
    """An improved version of QKeySequenceEdit"""
    keySequenceCleared=Signal()

    def __init__(self, parent=None):
        super(WKeySequenceInput, self).__init__(parent)

        self.__lineEdit=self.findChild(QLineEdit)
        self.__lineEdit.textChanged.connect(self.__textChanged)

    def __textChanged(self, value):
        """Text has been changed"""
        if value=='':
            self.clear()
            self.keySequenceCleared.emit()

    def isClearButtonEnabled(self, value):
        """Return if clear button is displayed or not"""
        self.__lineEdit.isClearButtonEnabled()

    def setClearButtonEnabled(self, value):
        """Display or not clear button"""
        self.__lineEdit.setClearButtonEnabled(value)
        if value:
            replaceLineEditClearButton(self.__lineEdit)

    #def event(self, event):
    #    print("event", event, event.type())
    #    return super(WKeySequenceInput, self).event(event)

    #def keyPressEvent(self, event):
    #    print("keyPressEvent", event, event.text(), event.key(), event.modifiers())
    #    super(WKeySequenceInput, self).keyPressEvent(event)

    #def keyReleaseEvent(self, event):
    #    print("keyReleaseEvent", event, event.text(), event.key(), event.modifiers())
    #    super(WKeySequenceInput, self).keyReleaseEvent(event)

    #def timerEvent(self, event):
    #    print("timerEvent", event)
    #    super(WKeySequenceInput, self).timerEvent(event)
