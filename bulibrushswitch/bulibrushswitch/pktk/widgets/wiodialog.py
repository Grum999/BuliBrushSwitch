# -----------------------------------------------------------------------------
# PyKritaToolKit
# Copyright (C) 2019-2022 - Grum999
# -----------------------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
#
# https://spdx.org/licenses/GPL-3.0-or-later.html
# -----------------------------------------------------------------------------
# A Krita plugin framework
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# The wiodialog module provides a set of dialog box
#
# Main class from this module
#
# - WDialogMessage:
#       Main class for all dialog box
#
# - WDialogBooleanInput:
#       A yes/no/cancel dialog box
#
# - WDialogStrInput:
#       An input string value dialog box
#
# - WDialogIntInput:
#       An input integer value dialog box
#
# - WDialogFloatInput:
#       An input float value dialog box
#
# - WDialogComboBoxChoiceInput:
#       An input combobox value dialog box
#
# - WDialogRadioButtonChoiceInput:
#       An input radiobox value dialog box
#
# - WDialogCheckBoxChoiceInput:
#       An input checkbox value dialog box
#
# - WDialogColorInput:
#       An input color value dialog box
#
# - WDialogFontInput:
#       An input font value dialog box
#
# - WDialogProgress:
#       A generic progress dialog box
#
# - WDialogFile:
#       A generic open/save file dialog, extending Qt QFileDialog and providing
#       ability to use user defined preview & settings widgets
#
# -----------------------------------------------------------------------------
import re
import os.path

import PyQt5.uic

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtGui import (
        QTextDocument,
        QFontDatabase,
        QPixmap,
        QGuiApplication,
        QImageReader,
        QStandardItem,
        QStandardItemModel,
        QColor
    )
from PyQt5.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QVBoxLayout,
        QWidget,
        QFileDialog
    )

from .wcolorselector import (
        WColorPicker,
        WColorComplementary
    )

from ..modules.utils import replaceLineEditClearButton
from ..modules.imgutils import buildIcon
from .wimageview import (WImageView, WImageFilePreview)
from ..pktk import *


class WDialogMessage(QDialog):
    """A simple dialog box to display a formatted message with a "OK" button"""
    def __init__(self, title, message, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogMessage, self).__init__(parent)

        self.setSizeGripEnabled(True)
        self.setModal(True)

        self.setWindowTitle(title)

        self.__minimumSize = QSize(0, 0)
        if isinstance(minSize, QSize):
            self.__minimumSize = minSize
            self.setMinimumSize(self.__minimumSize)

        self._dButtonBox = QDialogButtonBox(self)
        self._dButtonBox.setOrientation(Qt.Horizontal)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok)
        self._dButtonBox.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum))
        self._dButtonBox.accepted.connect(self.accept)
        self._dButtonBox.rejected.connect(self.reject)

        self._message = QTextEdit(self)
        self._message.setReadOnly(True)
        self._message.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding))
        self._message.setHtml(message)

        self._messageText = message

        self._optionalCheckboxMsg = None
        if isinstance(optionalCheckboxMsg, str) and optionalCheckboxMsg != '':
            self._optionalCheckboxMsg = QCheckBox(optionalCheckboxMsg)

        if self._messageText == '':
            self._message.hide()

        self._layoutbtn = QHBoxLayout()
        self._layoutbtn.setContentsMargins(0, 0, 0, 0)
        if self._optionalCheckboxMsg is not None:
            self._layoutbtn.addWidget(self._optionalCheckboxMsg)
        self._layoutbtn.addStretch()
        self._layoutbtn.addWidget(self._dButtonBox)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.addWidget(self._message)
        self._layout.addLayout(self._layoutbtn)

    def __applyMessageIdealSize(self, message):
        """Try to calculate and apply ideal size for dialog box"""
        # get primary screen (screen on which dialog is displayed) size
        rect = QGuiApplication.primaryScreen().size()
        # and determinate maximum size to apply to dialog box when displayed
        # => note, it's not the maximum window size (user can increase size with grip),
        #    but the maximum we allow to use to determinate window size at display
        # => factor are arbitrary :)
        maxW = rect.width() * 0.5 if rect.width() > 1920 else rect.width() * 0.7 if rect.width() > 1024 else rect.width() * 0.9
        maxH = rect.height() * 0.5 if rect.height() > 1080 else rect.height() * 0.7 if rect.height() > 1024 else rect.height() * 0.9
        # let's define some minimal dimension for dialog box...
        minW = max(320, self.__minimumSize.width())
        minH = max(200, self.__minimumSize.height())

        # an internal document used to calculate ideal width
        # (ie: using no-wrap for space allows to have an idea of maximum text width)
        document = QTextDocument()
        document.setDefaultStyleSheet("p { white-space: nowrap; }")
        document.setHtml(message)

        # then define our QTextEdit width taking in account ideal size, maximum and minimum allowed width on screen
        self._message.setMinimumWidth(round(max(minW, min(maxW, document.idealWidth()))))

        # now QTextEdit widget has a width defined, we can retrieve height of document
        # (ie: document's height = as if we don't have scrollbars)
        # add a security margin of +25 pixels
        height = round(max(minH, min(maxH, self._message.document().size().height()+25)))

        self._message.setMinimumHeight(height)

    def showEvent(self, event):
        """Event trigerred when dialog is shown"""
        super(WDialogMessage, self).showEvent(event)
        # Ideal size can't be applied until widgets are shown because document
        # size (especially height) can't be known unless QTextEdit widget is visible
        if self._messageText != '':
            self.__applyMessageIdealSize(self._messageText)

        # calculate QDialog size according to content
        self.adjustSize()
        # recenter it on screen
        self.move(QGuiApplication.primaryScreen().geometry().center()-QPoint(self.width()//2, self.height()//2))

        # and finally, remove constraint for QTextEdit size (let user resize dialog box if needed)
        self._message.setMinimumSize(0, 0)

    def optionalCheckboxMsgIsChecked(self):
        """Return if 'apply for all check box' is checked"""
        if self._optionalCheckboxMsg is None:
            return False
        return self._optionalCheckboxMsg.isChecked()

    @staticmethod
    def display(title, message, minSize=None):
        """Open a dialog box to display message

        title: dialog box title
        message: message to display

        return None
        """
        dlgBox = WDialogMessage(title, message, minSize, None)

        returned = dlgBox.exec()
        return None


class WDialogBooleanInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a choice "Yes" / "No" and optional "Cancel" buttons
    """
    def __init__(self, title, message, cancelButton=False, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogBooleanInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from yes/no/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)

        if cancelButton:
            self._dButtonBox.setStandardButtons(QDialogButtonBox.Yes | QDialogButtonBox.No | QDialogButtonBox.Cancel)
            self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        else:
            self._dButtonBox.setStandardButtons(QDialogButtonBox.Yes | QDialogButtonBox.No)

        self._dButtonBox.button(QDialogButtonBox.Yes).clicked.connect(self.__buttonYes)
        self._dButtonBox.button(QDialogButtonBox.No).clicked.connect(self.__buttonNo)

        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonYes(self):
        """Button 'yes' has been clicked, return True value"""
        self.__value = True
        self.close()

    def __buttonNo(self):
        """Button 'no' has been clicked, return False value"""
        self.__value = False
        self.close()

    def value(self):
        """Return value defined by clicked button

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message, cancelButton=False, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        message to display
        cancelButton:   add an optional "Cancel" button

        return True value if button "Yes"
        return False value if button "No"
        return None value if button "Cancel"
        """
        if not isinstance(cancelButton, bool):
            cancelButton = False

        dlgBox = WDialogBooleanInput(title, message, cancelButton, minSize, optionalCheckboxMsg)

        dlgBox.exec()

        return dlgBox.value()


class WDialogStrInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a string value input, with "Ok" / "Cancel" buttons
    """
    def __init__(self, title, message, inputLabel='', defaultValue='', regEx='', minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogStrInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)
        self.__btnOk = self._dButtonBox.button(QDialogButtonBox.Ok)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._leInput = QLineEdit(self)
        self._leInput.setText(defaultValue)
        self._leInput.setFocus()
        self._leInput.setClearButtonEnabled(True)
        replaceLineEditClearButton(self._leInput)
        self._layout.insertWidget(self._layout.count()-1, self._leInput)

        self.__regEx = regEx
        if self.__regEx != '':
            self._leInput.textChanged.connect(self.__checkValue)
            self.__checkValue(self._leInput.text())

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return True value"""
        self.__value = self._leInput.text()
        self.close()

    def __checkValue(self, value):
        """Check if value is valid according to regular expression and enable/disabled Ok button"""
        if re.search(self.__regEx, value):
            self.__btnOk.setEnabled(True)
        else:
            self.__btnOk.setEnabled(False)

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, defaultValue=None, regEx=None, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        defaultValue:   an optional default value set to input when dialog box is opened
        regEx:          an optional regular expression; when set, input value must match
                        regular expression to enable "OK" button

        return input value if button "OK"
        return None value if button "Cancel"
        """
        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if defaultValue is None:
            defaultValue = ''
        elif not isinstance(defaultValue, str):
            defaultValue = f"{defaultValue}"

        if regEx is None:
            regEx = ''

        dlgBox = WDialogStrInput(title, message, inputLabel, defaultValue, regEx, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogIntInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    an integer value input, with "Ok" / "Cancel" buttons
    """
    def __init__(self, title, message, inputLabel='', defaultValue=0, minValue=None, maxValue=None, prefix=None, suffix=None, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogIntInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._sbInput = QSpinBox(self)
        if isinstance(minValue, int):
            self._sbInput.setMinimum(minValue)
        else:
            self._sbInput.setMinimum(-2147483648)
        if isinstance(maxValue, int):
            self._sbInput.setMaximum(maxValue)
        else:
            self._sbInput.setMaximum(2147483647)
        if isinstance(prefix, str):
            self._sbInput.setPrefix(prefix)
        if isinstance(suffix, str):
            self._sbInput.setSuffix(suffix)
        self._sbInput.setValue(defaultValue)
        self._sbInput.setFocus()
        self._layout.insertWidget(self._layout.count()-1, self._sbInput)

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = self._sbInput.value()
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, defaultValue=None, minValue=None, maxValue=None, prefix=None, suffix=None, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        defaultValue:   an optional default value set to input when dialog box is opened
        minValue:       an optional minimum value (for technical reason, bounded in range [-2147483648;2147483647])
        maxValue:       an optional maximum value (for technical reason, bounded in range [-2147483648;2147483647])
        prefix:         an optional prefix text
        suffix:         an optional suffix text

        return input value if button "OK"
        return None value if button "Cancel"
        """
        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if isinstance(defaultValue, float):
            defaultValue = round(defaultValue)
        elif not isinstance(defaultValue, int):
            defaultValue = 0

        if isinstance(minValue, float):
            minValue = round(minValue)
        elif not isinstance(minValue, int):
            minValue = None

        if isinstance(maxValue, float):
            maxValue = round(maxValue)
        elif not isinstance(maxValue, int):
            maxValue = None

        if not isinstance(prefix, str):
            prefix = None
        if not isinstance(suffix, str):
            suffix = None

        dlgBox = WDialogIntInput(title, message, inputLabel, defaultValue, minValue, maxValue, prefix, suffix, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogFloatInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    an integer value input, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', defaultValue=0,
                 decValue=None, minValue=None, maxValue=None, prefix=None, suffix=None, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogFloatInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._sbInput = QDoubleSpinBox(self)
        if isinstance(decValue, int):
            self._sbInput.setDecimals(max(0, min(323, decValue)))
        else:
            self._sbInput.setDecimals(2)
        if isinstance(minValue, float):
            self._sbInput.setMinimum(minValue)
        else:
            self._sbInput.setMinimum(-9007199254740992.0)
        if isinstance(maxValue, float):
            self._sbInput.setMaximum(maxValue)
        else:
            self._sbInput.setMaximum(9007199254740992.0)
        if isinstance(prefix, str):
            self._sbInput.setPrefix(prefix)
        if isinstance(suffix, str):
            self._sbInput.setSuffix(suffix)
        self._sbInput.setValue(defaultValue)
        self._sbInput.setFocus()
        self._layout.insertWidget(self._layout.count()-1, self._sbInput)

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = self._sbInput.value()
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, defaultValue=None,
                decValue=None, minValue=None, maxValue=None, prefix=None, suffix=None, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        defaultValue:   an optional default value set to input when dialog box is opened
        decValue:       an optional decimals number value (0 to 323)
        minValue:       an optional minimum value (for technical reason, bounded in range [-9007199254740992.0;9007199254740992.0])
        maxValue:       an optional maximum value (for technical reason, bounded in range [-9007199254740992.0;9007199254740992.0])
        prefix:         an optional prefix text
        suffix:         an optional suffix text

        return input value if button "OK"
        return None value if button "Cancel"
        """
        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if not isinstance(defaultValue, (int, float)):
            defaultValue = 0.0

        if not isinstance(minValue, (int, float)):
            minValue = None

        if not isinstance(maxValue, (int, float)):
            maxValue = None

        if not isinstance(decValue, (int, float)):
            decValue = None

        if not isinstance(prefix, str):
            prefix = None
        if not isinstance(suffix, str):
            suffix = None

        dlgBox = WDialogFloatInput(title, message, inputLabel, defaultValue, decValue, minValue, maxValue, prefix, suffix, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogComboBoxChoiceInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a choice in a list, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', choicesValue=[], defaultIndex=0, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogComboBoxChoiceInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        if len(choicesValue) == 0:
            self.reject()

        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._cbInput = QComboBox(self)
        self._cbInput.addItems(choicesValue)
        self._cbInput.setCurrentIndex(min(len(choicesValue), max(0, defaultIndex)))
        self._cbInput.setFocus()
        self._layout.insertWidget(self._layout.count()-1, self._cbInput)

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = self._cbInput.currentIndex()
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, choicesValue=[], defaultIndex=0, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        choicesValue:   a list of <str> item proposed as choices in combobox list
        defaultIndex:   an optional index to select a default choice

        return selected index in choices list if button "OK"
        return None value if button "Cancel"
        """
        if not isinstance(choicesValue, (list, tuple)) or len(choicesValue) == 0:
            return None

        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if not isinstance(defaultIndex, int):
            defaultIndex = 0

        dlgBox = WDialogComboBoxChoiceInput(title, message, inputLabel, choicesValue, defaultIndex, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogRadioButtonChoiceInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a choice from radio box list, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', choicesValue=[], defaultIndex=0, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogRadioButtonChoiceInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        if len(choicesValue) == 0:
            self.reject()

        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._rbInput = []
        for item in choicesValue:
            rbInput = QRadioButton(self)
            rbInput.setText(item)
            self._rbInput.append(rbInput)
            self._layout.insertWidget(self._layout.count()-1, rbInput)

        self._rbInput[min(len(choicesValue), max(0, defaultIndex))].setChecked(True)

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = None
        for index, item in enumerate(self._rbInput):
            if item.isChecked():
                self.__value = index
                break
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, choicesValue=[], defaultIndex=0, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        choicesValue:   a list of <str> item proposed as choices in combobox list
        defaultIndex:   an optional index to select a default choice

        return selected index in choices list if button "OK"
        return None value if button "Cancel"
        """
        if not isinstance(choicesValue, (list, tuple)) or len(choicesValue) == 0:
            return None

        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if not isinstance(defaultIndex, int):
            defaultIndex = 0

        dlgBox = WDialogRadioButtonChoiceInput(title, message, inputLabel, choicesValue, defaultIndex, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogCheckBoxChoiceInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a choice from check box list, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', choicesValue=[], defaultChecked=[], minimumChecked=0, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogCheckBoxChoiceInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        if len(choicesValue) == 0:
            self.reject()

        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)
        self.__btnOk = self._dButtonBox.button(QDialogButtonBox.Ok)

        self.__minimumChecked = max(0, min(len(choicesValue), minimumChecked))

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        self._cbInput = []
        for index, item in enumerate(choicesValue):
            cbInput = QCheckBox(self)
            cbInput.setText(item)
            if self.__minimumChecked > 0:
                cbInput.toggled.connect(self.__checkValue)
            if index in defaultChecked:
                cbInput.setChecked(True)

            self._cbInput.append(cbInput)
            self._layout.insertWidget(self._layout.count()-1, cbInput)

        if self.__minimumChecked > 0:
            self.__checkValue()

        # default returned value
        self.__value = None

    def __checkValue(self):
        """Check if number of checked values is valid according to minimumChecked value and enable/disabled Ok button"""
        self.__btnOk.setEnabled(len(self.value()) >= self.__minimumChecked)

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = []
        for index, item in enumerate(self._cbInput):
            if item.isChecked():
                self.__value.append(index)
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, choicesValue=[], defaultChecked=[], minimumChecked=0, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        choicesValue:   a list of <str> item proposed as choices in combobox list
        defaultChecked: an optional list of index to define default cheked boxes
        minimumChecked: an optional value to define the minimal number of checked box to allow user to validate selection

        return a list of checked index if button "OK"
        return None value if button "Cancel"
        """
        if not isinstance(choicesValue, (list, tuple)) or len(choicesValue) == 0:
            return None

        if not isinstance(defaultChecked, (list, tuple)):
            return None

        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        if not isinstance(minimumChecked, int):
            defaultIndex = 0

        dlgBox = WDialogCheckBoxChoiceInput(title, message, inputLabel, choicesValue, defaultChecked, minimumChecked, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogColorInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a color value input, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', defaultValue=None, options=None, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogColorInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        if not isinstance(options, dict):
            options = {}

        if not ('menu' in options and isinstance(options['menu'], int)):
            options['menu'] = 0

        if not ('layout' in options and isinstance(options['layout'], list) and len(options['layout']) > 0):
            options['layout'] = ['colorRGB',
                                 'colorHSV',
                                 'colorWheel',
                                 'colorPreview',
                                 f'colorCombination:{WColorComplementary.COLOR_COMBINATION_TETRADIC}',
                                 f'layoutOrientation:{WColorPicker.OPTION_ORIENTATION_HORIZONTAL}'
                                 ]

        # check options
        minimalColorChooser = 0
        minimalLayout = 0
        for layoutOption in options['layout']:
            if re.search('^layoutOrientation:[12]$', layoutOption, re.IGNORECASE):
                minimalLayout += 1
            elif re.search('^color(Palette|RGB%?|CMYK%?|HSV%?|HSL%?|Wheel)$', layoutOption, re.IGNORECASE):
                minimalColorChooser += 1

            if minimalColorChooser > 0 and minimalLayout > 0:
                break

        if minimalColorChooser == 0:
            options['layout'] += ['colorRGB',
                                  'colorHSV',
                                  'colorWheel',
                                  'colorPreview',
                                  f'colorCombination:{WColorComplementary.COLOR_COMBINATION_TETRADIC}'
                                  ]
        if minimalLayout == 0:
            options['layout'].append(f'layoutOrientation:{WColorPicker.OPTION_ORIENTATION_HORIZONTAL}')

        self._cpInput = WColorPicker(self)
        self._cpInput.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))
        self._cpInput.setOptionMenu(options['menu'])
        self._cpInput.setOptionLayout(options['layout'])

        if isinstance(defaultValue, QColor) or isinstance(defaultValue, str) and re.search("^#[A-F0-9]{6}$", defaultValue, re.IGNORECASE):
            self._cpInput.setColor(QColor(defaultValue))

        self._layout.insertWidget(self._layout.count()-1, self._cpInput)

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = self._cpInput.color()
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, defaultValue=None, options=None, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:          dialog box title
        message:        an optional message to display
        inputLabel:     an optional label positionned above input
        defaultValue:   an optional default value set to input when dialog box is opened
        options:        an optional set of options to define color picker UI, provided as a dictionary
                            'menu' = <int>
                                        Given value define available entry in context menu
                                        By default, no context menu is available
                                        See WColorPicker.setOptionMenu() widget for more information about menu configuration

                            'layout' = <list>
                                        A list of options to define which color components are available in interface
                                        See WColorPicker.setOptionLayout() widget for more information about layout configuration

                                        Default layout is:
                                        - Horizontal orientation
                                        - Color Wheel + Color Preview + Tetradic complementary colors
                                        - RGB Sliders
                                        - HSV Sliders

                                        ['layoutOrientation:2',
                                         'colorWheel',
                                         'colorPreview',
                                         'colorCombination:5',
                                         'colorRGB',
                                         'colorHSV']

        return color value if button "OK"
        return None value if button "Cancel"
        """
        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        dlgBox = WDialogColorInput(title, message, inputLabel, defaultValue, options, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogFontInput(WDialogMessage):
    """A simple input dialog box to display a formatted message and ask user for
    a choice from a font list, with "Ok" / "Cancel" buttons
    """

    def __init__(self, title, message, inputLabel='', defaultValue='', optionFilter=False, optionWritingSytem=False, minSize=None, optionalCheckboxMsg=None, parent=None):
        super(WDialogFontInput, self).__init__(title, message, minSize, optionalCheckboxMsg, parent)
        # need to manage returned value from ok/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)
        self._dButtonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
        self._dButtonBox.button(QDialogButtonBox.Ok).clicked.connect(self.__buttonOk)
        self.__btnOk = self._dButtonBox.button(QDialogButtonBox.Ok)
        self.__btnOk.setEnabled(False)

        self.__init = True
        self.__selectedFont = defaultValue
        self.__invertFilter = False

        self.__database = QFontDatabase()
        self.__tvInput = QTreeView(self)
        self.__tvInput.setAllColumnsShowFocus(True)
        self.__tvInput.setRootIsDecorated(False)
        self.__tvInput.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.__tvInput.setSelectionMode(QAbstractItemView.SingleSelection)
        self.__tvInput.selectionChanged = self.__fontSelectionChanged
        self.__tvInput.setMinimumWidth(900)

        self.__lblCount = QLabel(self)
        font = self.__lblCount.font()
        font.setPointSize(8)
        self.__lblCount.setFont(font)

        self.__lblText = QLabel(self)
        font = self.__lblText.font()
        font.setPixelSize(64)
        self.__lblText.setFont(font)
        self.__lblText.setMinimumHeight(72)
        self.__lblText.setMaximumHeight(72)

        self.__fontTreeModel = QStandardItemModel(self.__tvInput)
        self.__fontTreeModel.setColumnCount(2)
        self.__proxyModel = QSortFilterProxyModel()
        self.__proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.__proxyModel.setSourceModel(self.__fontTreeModel)
        self.__proxyModel.setFilterKeyColumn(0)
        self.__originalFilterAcceptsRow = self.__proxyModel.filterAcceptsRow
        self.__proxyModel.filterAcceptsRow = self.__filterAcceptsRow
        self.__tvInput.setModel(self.__proxyModel)

        if inputLabel != '':
            self._lbInput = QLabel(self)
            self._lbInput.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))
            self._lbInput.setText(inputLabel)
            self._layout.insertWidget(self._layout.count()-1, self._lbInput)

        if optionWritingSytem or optionFilter:
            wContainer = QWidget(self)
            fLayout = QFormLayout(wContainer)
            fLayout.setContentsMargins(0, 0, 0, 0)
            wContainer.setLayout(fLayout)

            if optionWritingSytem:
                self._cbWritingSystem = QComboBox(wContainer)
                self._cbWritingSystem.addItem(self.__database.writingSystemName(QFontDatabase.Any), QFontDatabase.Any)
                for writingSystem in self.__database.writingSystems():
                    self._cbWritingSystem.addItem(self.__database.writingSystemName(writingSystem), writingSystem)
                self._cbWritingSystem.currentIndexChanged.connect(self.__updateList)
                fLayout.addRow(i18n("Writing system"), self._cbWritingSystem)

            if optionFilter:
                self._leFilterName = QLineEdit(wContainer)
                self._leFilterName.setClearButtonEnabled(True)
                replaceLineEditClearButton(self._leFilterName)
                self._leFilterName.setToolTip(i18n('Filter fonts\nStart filter with "re:" for regular expression filter or "re!:" for inverted regular expression filter'))
                self._leFilterName.textEdited.connect(self.__updateFilter)
                fLayout.addRow(i18n("Filter name"), self._leFilterName)

            self._layout.insertWidget(self._layout.count()-1, wContainer)

        self._layout.insertWidget(self._layout.count()-1, self.__tvInput)
        self._layout.insertWidget(self._layout.count()-1, self.__lblCount)
        self._layout.insertWidget(self._layout.count()-1, self.__lblText)
        self.__init = False
        self.__updateList(QFontDatabase.Any)

        # default returned value
        self.__value = None

    def __updateList(self, writingSystem):
        """Build font list according to designed writingSystem"""
        self.__init = True
        defaultSelected = None
        self.__fontTreeModel.clear()
        self.__fontTreeModel.setHorizontalHeaderLabels([i18n("Font name"), i18n("Example")])
        for family in self.__database.families(writingSystem):
            familyItem = QStandardItem(family)
            fntSize = familyItem.font().pointSize()

            font = self.__database.font(family, "", fntSize)
            fontItem = QStandardItem(family)
            fontItem.setFont(font)

            self.__fontTreeModel.appendRow([familyItem, fontItem])

            if defaultSelected is None and self.__selectedFont == family:
                defaultSelected = familyItem

        self.__tvInput.resizeColumnToContents(0)
        self.__updateCount()
        self.__init = False

        if defaultSelected:
            index = self.__proxyModel.mapFromSource(defaultSelected.index())
            self.__tvInput.setCurrentIndex(index)

    def __updateFilter(self, filter):
        """Filter value has been changed, apply to proxyfilter"""
        if reFilter := re.search('^re:(.*)', filter):
            self.__invertFilter = False
            self.__proxyModel.setFilterRegExp(reFilter.groups()[0])
        elif reFilter := re.search('^re!:(.*)', filter):
            self.__invertFilter = True
            self.__proxyModel.setFilterRegExp(reFilter.groups()[0])
        else:
            self.__invertFilter = False
            self.__proxyModel.setFilterWildcard(filter)
        self.__updateCount()

    def __updateCount(self):
        """Update number of font label"""
        self.__lblCount.setText(f'Font: <i>{self.__proxyModel.rowCount()}</i>')

    def __fontSelectionChanged(self, selected, unselected):
        """Selection has changed in treeview"""
        if self.__init:
            return
        if selected is not None and len(selected.indexes()) > 0:
            self.__selectedFont = selected.indexes()[0].data()
            self.__btnOk.setEnabled(True)

            font = self.__lblText.font()
            font.setFamily(self.__selectedFont)
            self.__lblText.setFont(font)
            self.__lblText.setText(self.__selectedFont)
        else:
            self.__btnOk.setEnabled(False)
            self.__selectedFont = None
            self.__lblText.setText('')

    def __filterAcceptsRow(self, sourceRow, sourceParent):
        """Provides a way to invert filter"""

        returned = self.__originalFilterAcceptsRow(sourceRow, sourceParent)
        if self.__invertFilter:
            return not returned
        return returned

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__value = None
        self.close()

    def __buttonOk(self):
        """Button 'Ok' has been clicked, return value"""
        self.__value = self.__selectedFont
        self.close()

    def value(self):
        """Return value

        If there's an optional checkbox, return a tuple (value, checkbox status) instead of value
        """
        if self._optionalCheckboxMsg is None:
            return self.__value
        return (self.__value, self.optionalCheckboxMsgIsChecked())

    @staticmethod
    def display(title, message=None, inputLabel=None, defaultValue='', optionFilter=False, optionWritingSytem=False, minSize=None, optionalCheckboxMsg=None):
        """Open dialog box

        title:              dialog box title
        message:            an optional message to display
        inputLabel:         an optional label positionned above input
        defaultValue:       default font name to select in list
        optionFilter:       add a filter in UI
        optionWritingSytem: add a combobox in UI (to select writing system perimeter)

        return a name
        return None value if button "Cancel"
        """
        if not isinstance(defaultValue, str):
            return None

        if message is None:
            message = ''

        if inputLabel is None:
            inputLabel = ''
        elif not isinstance(inputLabel, str):
            inputLabel = f"{inputLabel}"

        dlgBox = WDialogFontInput(title, message, inputLabel, defaultValue, optionFilter, optionWritingSytem, minSize, optionalCheckboxMsg)

        returned = dlgBox.exec()

        return dlgBox.value()


class WDialogProgress(WDialogMessage):
    """A simple dialog box to display a formatted message with a progress bar
    and an optional "Cancel" button
    """

    def __init__(self, title, message, cancelButton=False, minSize=None, minValue=0, maxValue=0, progressSignal=None, parent=None):
        super(WDialogProgress, self).__init__(title, message, minSize, None, parent)
        # need to manage returned value from yes/no/cancel buttons
        # then disconnect default signal
        self._dButtonBox.accepted.disconnect(self.accept)
        self._dButtonBox.rejected.disconnect(self.reject)

        self.__btnCancel = None
        if cancelButton:
            self._dButtonBox.setStandardButtons(QDialogButtonBox.Cancel)
            self._dButtonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.__buttonCancel)
            self.__btnCancel = self._dButtonBox.button(QDialogButtonBox.Cancel)

        self._progressBar = QProgressBar(self)
        self._progressBar.setMinimum(minValue)
        self._progressBar.setMaximum(maxValue)
        self._progressBar.setFormat("Frame %v of %m (%p%)")
        self._progressBar.setTextVisible(True)
        self._layout.insertWidget(self._layout.count()-1, self._progressBar)

        self.__cancelled = False

        # default returned value
        self.__value = None

    def __buttonCancel(self):
        """Button 'cancel' has been clicked, return None value"""
        self.__cancelled = True
        self.close()

    def value(self):
        """Return value defined by clicked button"""
        self.__value

    def setProgress(self, value):
        """Update progress bar value

        If return false, means the cancel button as been clicked
        """
        self._progressBar.setValue(value)
        self._progressBar.update()
        QApplication.processEvents()
        return self.__cancelled

    def isInfinite(self):
        """Return if current progress bar is in 'infinite mode'"""
        return self._progressBar.maximum() == 0

    def setInfinite(self):
        """Set progress bar as infinite value"""
        self._progressBar.setValue(0)
        self._progressBar.setMaximum(0)
        self._progressBar.update()
        QApplication.processEvents()

    def minValue(self):
        """Return current minimum value for progress bar"""
        return self.minimum()

    def setMinValue(self, value):
        """Change minimum value; current value reset to minimum"""
        self._progressBar.setMinimum(value)
        self._progressBar.setValue(value)
        self._progressBar.update()
        QApplication.processEvents()

    def maxValue(self):
        """Return current maximum value for progress bar"""
        return self.maximum()

    def setMaxValue(self, value):
        """Change maximum value; current value reset to minimum"""
        self._progressBar.setValue(self._progressBar.minimum())
        self._progressBar.setMaximum(value)
        self._progressBar.update()
        QApplication.processEvents()

    def textFormat(self):
        """Return current text format"""
        self._progressBar.format()

    def setTextFormat(self, value):
        """Change maximum value; current value reset to minimum"""
        self._progressBar.setFormat(value)

    def cancelButtonIsEnabled(self):
        """Return if cancel button is enabled

        If there's no cancel button, return None
        """
        if self.__btnCancel is None:
            return None
        return self.__btnCancel.isEnabled()

    def setCancelButtonEnabled(self, value):
        """Enabled/Disable cancel button"""
        if self.__btnCancel is None or not isinstance(value, bool):
            return
        self.__btnCancel.setEnabled(value)

    def message(self):
        """Return current message"""
        return self._messageText

    def updateMessage(self, message, replace=True):
        """Replace current message content with new text

        If `replace` is True, current message is replaced by new message
        Otherwise, new message is added to current message

        """
        if replace:
            self._messageText = message
        else:
            self._messageText += message
        self._message.setHtml(self._messageText)
        self._message.update()
        QApplication.processEvents()

    @staticmethod
    def display(title, message, cancelButton=False, minSize=None, minValue=0, maxValue=0):
        """Open dialog box

        title:          dialog box title
        message:        message to display
        cancelButton:   add an optional "Cancel" button
        minValue:       minimum value for progress bar
        maxValue:       maximum value for progress bar (if 0=infinite progress bar)

        return WDialogProgress.RESULT_FINISHED value if button "Yes"
        return False value if button "No"
        return None value if button "Cancel"
        """

        if not isinstance(cancelButton, bool):
            cancelButton = False

        dlgBox = WDialogProgress(title, message, cancelButton, minSize, minValue, maxValue)

        dlgBox.show()
        return dlgBox


class WDialogFile(QFileDialog):
    """A file dialog with options

    Extend Qt QFileDialog to provide a customisable dialog box

    Given `options` can be:

        OPTION_MESSAGE: <str>                       Message (html) to display, or None (default) to disable message
        OPTION_PREVIEW_WIDTH: <int>                 Width for preview area, or None for default value
        OPTION_PREVIEW_WIDGET: <str>, <qwidget>     Widget used to display preview
                                                    Provided value can be:
                                                    - <str> value 'image': default internal image preview with be used
                                                    - <qwidget>: must be a WDialogFile.WSubWidget()
        OPTION_SETTINGS_WIDGET: <qwidget>           A widget used to provide additional UI settings to file dialog
                                                    - <qwidget>: must be a WDialogFile.WSubWidget()

        Usual file dialog
        +------------------------------------------------------------------------------+
        | Title                                                                        |
        +------------------------------------------------------------------------------+
        |                                                                              |
        | Files area                                                                   |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        |                                                                              |
        +------------------------------------------------------------------------------+
        | [File name......................]                                [open|save] |
        | [Filter.........................]                                   [cancel] |
        +------------------------------------------------------------------------------+

        With possible options file dialog
        +------------------------------------------------------------------------------+
        | Title                                                                        |
        +-----------------------------------------------------------+------------------+
        | Message area                                              |                  |
        |                                                           |                  |
        |                                                           |                  |
        +-----------------------------------------------------------+                  |
        |                                                           |                  |
        | Files area                                                | Preview Area     |
        |                                                           |                  |
        |                                                           |                  |
        |                                                           |                  |
        |                                                           |                  |
        |                                                           |                  |
        |                                                           |                  |
        |                                                           |                  |
        +-----------------------------------------------------------+                  |
        |                                                           |                  |
        | Additional settings area                                  |                  |
        |                                                           |                  |
        +-----------------------------------------------------------+                  |
        | [File name......................]             [open|save] |                  |
        | [Filter.........................]             [cancel]    |                  |
        +-----------------------------------------------------------+------------------+

    """

    class WSubWidget(QWidget):
        """A default sub-widget that can be extended to create:
           - Preview widget
           - Settings widget
        """
        def __init__(self, parent=None):
            super(WDialogFile.WSubWidget, self).__init__(parent)

        def setFile(self, fileName):
            """Called when dialog box select a file

            Given `fileNames` is an list of <str>
            Method must return True (if file accepted), or False

            Method must manage common case:
            - no file
            - one file
            - unexisting file, unreadable file, ...
            """
            raise EInvalidStatus("Abstract widget method `setFile()` must be implemented")

        def information(self):
            """Called by dialog box to return informations from widget

            Example:
                - for a preview, return number of records, image size, ...
                - for a setting, return settings values from widget

            returned result can be of any type (None, str, list, dict, ...)
            """
            return None

    class WSubWidgetImgPreview(WSubWidget):
        """A default sub-widget that can be extended to create:
           - Preview widget
           - Settings widget
        """
        def __init__(self, parent=None):
            super(WDialogFile.WSubWidgetImgPreview, self).__init__(parent)

            self.__imageSize = QSize()

            self.__imageFilePreview = WImageFilePreview(self)
            self.__imageFilePreview.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
            self.__imageFilePreview.setBackgroundType(WImageView.BG_TRANSPARENT)

            self.__lblSize = QLabel(self)
            font = self.__lblSize.font()
            font.setPointSize(8)
            self.__lblSize.setFont(font)
            self.__lblSize.setAlignment(Qt.AlignLeft)
            self.__lblSize.setStyleSheet('font-style: italic')

            layout = QVBoxLayout()
            layout.addWidget(self.__imageFilePreview)
            layout.addWidget(self.__lblSize)
            self.setLayout(layout)

        def setFile(self, fileName):
            """When fileName is provided, update image preview content"""
            self.__imageSize = QSize()

            if fileName == '':
                self.__imageFilePreview.hidePreview(i18n("No file selected"))
                self.__lblSize.setText('')
            else:
                if os.path.isfile(fileName):
                    imgNfo = QImageReader(fileName)

                    if imgNfo.canRead():
                        pixmap = QPixmap(fileName)
                        self.__imageSize = pixmap.size()

                        self.__imageFilePreview.showPreview(pixmap)
                        self.__lblSize.setText(f'{pixmap.width()}x{pixmap.height()}')

                        if imgNfo.imageCount() > 1:
                            self.__imageFilePreview.showAnimatedFrames(fileName, imgNfo.imageCount())
                        else:
                            self.__imageFilePreview.hideAnimatedFrames()
                    else:
                        self.__imageFilePreview.hidePreview(i18n("Can't read file"))
                        self.__lblSize.setText('')
                else:
                    self.__imageFilePreview.setText(i18n("No preview available"))
                    self.__lblSize.setText('')

            # always return True; if dialog box can't read image, maybe krita will be able
            return True

        def information(self):
            """Return dimension of image"""
            return self.__imageSize

    PREVIEW_WIDTH = 250

    OPTION_MESSAGE =                0b00000001
    OPTION_PREVIEW_WIDTH =          0b00000010
    OPTION_PREVIEW_WIDGET =         0b00000011
    OPTION_SETTINGS_WIDGET =        0b00000100

    OPTION_ACCEPT_MODE =            0b01000000
    OPTION_FILE_SELECTION_MODE =    0b01000001

    @staticmethod
    def openFile(caption=None, directory=None, filter=None, options=None):
        """A predefined function to open ONE file

        If action is cancelled, return None
        Otherwise return a <dict> with following keys:
            - 'file':           selected file name (<str>)
            - 'previewNfo':     information from preview if there's preview, otherwise None
            - 'settingsNfo':    information from settings if there's settings, otherwise None
        """
        if options is None:
            options = {}

        options[WDialogFile.OPTION_ACCEPT_MODE] = WDialogFile.AcceptOpen
        if WDialogFile.OPTION_FILE_SELECTION_MODE in options and options[WDialogFile.OPTION_FILE_SELECTION_MODE] not in (WDialogFile.AnyFile, WDialogFile.ExistingFile):
            options[WDialogFile.OPTION_FILE_SELECTION_MODE] = WDialogFile.ExistingFile

        dlgBox = WDialogFile(caption, directory, filter, options)

        if dlgBox.exec() == WDialogFile.Accepted:
            return {
                    'file': dlgBox.file(),
                    'previewNfo': dlgBox.widgetPreviewInformation(),
                    'settingsNfo': dlgBox.widgetSettingsInformation()
                }
        else:
            return None

    @staticmethod
    def openFiles(caption=None, directory=None, filter=None, options=None):
        """A predefined function to open MULTIPLE files

        If action is cancelled, return None
        Otherwise return a <dict> with following keys:
            - 'files':          selected file names (<list> of <str>)
            - 'previewNfo':     information from preview if there's preview, otherwise None
            - 'settingsNfo':    information from settings if there's settings, otherwise None
        """
        if options is None:
            options = {}

        options[WDialogFile.OPTION_ACCEPT_MODE] = WDialogFile.AcceptOpen
        options[WDialogFile.OPTION_FILE_SELECTION_MODE] = WDialogFile.ExistingFiles

        dlgBox = WDialogFile(caption, directory, filter, options)
        if dlgBox.exec() == WDialogFile.Accepted:
            return {
                    'files': dlgBox.files(),
                    'previewNfo': dlgBox.widgetPreviewInformation(),
                    'settingsNfo': dlgBox.widgetSettingsInformation()
                }
        else:
            return None

    @staticmethod
    def openDirectory(caption=None, directory=None, filter=None, options=None):
        """A predefined function to open a DIERCTORY

        If action is cancelled, return None
        Otherwise return a <dict> with following keys:
            - 'directory':      selected directory (<str>)
            - 'previewNfo':     information from preview if there's preview, otherwise None
            - 'settingsNfo':    information from settings if there's settings, otherwise None
        """
        if options is None:
            options = {}

        options[WDialogFile.OPTION_ACCEPT_MODE] = WDialogFile.AcceptOpen
        options[WDialogFile.OPTION_FILE_SELECTION_MODE] = WDialogFile.Directory

        dlgBox = WDialogFile(caption, directory, filter, options)
        if dlgBox.exec() == WDialogFile.Accepted:
            return {
                    'directory': dlgBox.file(),
                    'previewNfo': dlgBox.widgetPreviewInformation(),
                    'settingsNfo': dlgBox.widgetSettingsInformation()
                }
        else:
            return None

    @staticmethod
    def saveFile(caption=None, directory=None, filter=None, options=None):
        """A predefined function to save a file

        If action is cancelled, return None
        Otherwise return a <dict> with following keys:
            - 'file':           selected file name (<str>)
            - 'previewNfo':     information from preview if there's preview, otherwise None
            - 'settingsNfo':    information from settings if there's settings, otherwise None
        """
        if options is None:
            options = {}

        options[WDialogFile.OPTION_ACCEPT_MODE] = WDialogFile.AcceptSave
        options[WDialogFile.OPTION_FILE_SELECTION_MODE] = WDialogFile.AnyFile

        dlgBox = WDialogFile(caption, directory, filter, options)
        if dlgBox.exec() == WDialogFile.Accepted:
            return {
                    'file': dlgBox.file(),
                    'previewNfo': dlgBox.widgetPreviewInformation(),
                    'settingsNfo': dlgBox.widgetSettingsInformation()
                }
        else:
            return None

    def __init__(self, caption=None, directory=None, filter=None, options=None):
        super(WDialogFile, self).__init__(None, caption, directory, filter)

        self.__originalDlgBoxLayout = self.layout()

        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setMaximumSize(0xffffff, 0xffffff)

        self.__selectedFile = ''
        self.__selectedFiles = []

        # default options
        self.__options = {WDialogFile.OPTION_MESSAGE: '',
                          WDialogFile.OPTION_PREVIEW_WIDTH: WDialogFile.PREVIEW_WIDTH,
                          WDialogFile.OPTION_PREVIEW_WIDGET: None,
                          WDialogFile.OPTION_SETTINGS_WIDGET: None,

                          WDialogFile.OPTION_ACCEPT_MODE: WDialogFile.AcceptOpen,
                          WDialogFile.OPTION_FILE_SELECTION_MODE: WDialogFile.ExistingFile
                          }

        # check and apply provided options
        if isinstance(options, dict):
            # checking validty of given given options and  initialise self.__options
            if WDialogFile.OPTION_PREVIEW_WIDGET in options:
                if options[WDialogFile.OPTION_PREVIEW_WIDGET] == 'image':
                    # if image preview is required, initialise internal image preview widget
                    self.__options[WDialogFile.OPTION_PREVIEW_WIDGET] = WDialogFile.WSubWidgetImgPreview(self)
                elif isinstance(options[WDialogFile.OPTION_PREVIEW_WIDGET], WDialogFile.WSubWidget):
                    self.__options[WDialogFile.OPTION_PREVIEW_WIDGET] = options[WDialogFile.OPTION_PREVIEW_WIDGET]
                    self.__options[WDialogFile.OPTION_PREVIEW_WIDGET].setParent(self)
                else:
                    raise EInvalidType("Given `options` key 'DialogFile.OPTION_PREVIEW_WIDGET' is not valid")

            if WDialogFile.OPTION_SETTINGS_WIDGET in options and isinstance(options[WDialogFile.OPTION_SETTINGS_WIDGET], QWidget) and \
               hasattr(options[WDialogFile.OPTION_SETTINGS_WIDGET], 'setFile') and callable(options[WDialogFile.OPTION_SETTINGS_WIDGET].setFile):
                self.__options[WDialogFile.OPTION_SETTINGS_WIDGET] = options[WDialogFile.OPTION_SETTINGS_WIDGET]
                self.__options[WDialogFile.OPTION_SETTINGS_WIDGET].setParent(self)

            if WDialogFile.OPTION_PREVIEW_WIDTH in options and \
               isinstance(options[WDialogFile.OPTION_PREVIEW_WIDTH], int) and \
               options[WDialogFile.OPTION_PREVIEW_WIDTH] > 0:
                self.__options[WDialogFile.OPTION_PREVIEW_WIDTH] = options[WDialogFile.OPTION_PREVIEW_WIDTH]

            if WDialogFile.OPTION_MESSAGE in options and isinstance(options[WDialogFile.OPTION_MESSAGE], str):
                self.__options[WDialogFile.OPTION_MESSAGE] = options[WDialogFile.OPTION_MESSAGE]

            if WDialogFile.OPTION_FILE_SELECTION_MODE in options and options[WDialogFile.OPTION_FILE_SELECTION_MODE] in (WDialogFile.AnyFile,
                                                                                                                         WDialogFile.ExistingFile,
                                                                                                                         WDialogFile.Directory,
                                                                                                                         WDialogFile.ExistingFiles):
                self.__options[WDialogFile.OPTION_FILE_SELECTION_MODE] = options[WDialogFile.OPTION_FILE_SELECTION_MODE]

            if WDialogFile.OPTION_ACCEPT_MODE in options and options[WDialogFile.OPTION_ACCEPT_MODE] in (WDialogFile.AcceptOpen, WDialogFile.AcceptSave):
                self.__options[WDialogFile.OPTION_ACCEPT_MODE] = options[WDialogFile.OPTION_ACCEPT_MODE]

        # --------------------------------------
        # start to reorganize file dialog layout
        # --------------------------------------

        # add preview if needed
        if self.__options[WDialogFile.OPTION_PREVIEW_WIDGET] is not None:
            self.__newDlgBoxWidget = QWidget()
            self.__newDlgBoxWidget.setLayout(self.__originalDlgBoxLayout)

            self.__newDlgBoxLayout = QVBoxLayout()
            self.__newDlgBoxLayout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.__newDlgBoxLayout)

            self.__splitter = QSplitter()
            self.__splitter.addWidget(self.__newDlgBoxWidget)
            self.__splitter.addWidget(self.__options[WDialogFile.OPTION_PREVIEW_WIDGET])
            self.__newDlgBoxLayout.addWidget(self.__splitter)

            self.__options[WDialogFile.OPTION_PREVIEW_WIDGET].setMinimumSize(self.__options[WDialogFile.OPTION_PREVIEW_WIDTH], 0)

        offsetRow = 0
        self.__teMessage = None
        self.__message = None

        # insert message if needed
        if not(self.__options[WDialogFile.OPTION_MESSAGE] is None or self.__options[WDialogFile.OPTION_MESSAGE] == ''):
            offsetRow = 1
            self.__message = self.__options[WDialogFile.OPTION_MESSAGE]

            self.__teMessage = QTextEdit(self)
            self.__teMessage.setReadOnly(True)
            self.__teMessage.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding))
            self.__teMessage.setHtml(self.__message)

            # Insert message in dialog box layout
            #   insertAtRow=0
            #   rowSpan=1 (only one row)
            #   columnSpan=-1 (extend to the right edge of layout)
            self.__insertRowGridLayout(self.__teMessage, self.__originalDlgBoxLayout, 0, 1, -1)

        # insert settings widget if needed
        if self.__options[WDialogFile.OPTION_SETTINGS_WIDGET]:
            offsetRow += 2
            self.__insertRowGridLayout(self.__options[WDialogFile.OPTION_SETTINGS_WIDGET], self.__originalDlgBoxLayout, offsetRow, 1, 3)

        # custom widgets on dialog box, need to take care of returned value for setFile() method
        if self.__options[WDialogFile.OPTION_PREVIEW_WIDGET] or self.__options[WDialogFile.OPTION_SETTINGS_WIDGET]:
            self.currentChanged.connect(self.__changed)

        self.fileSelected.connect(self.__fileSelected)
        self.filesSelected.connect(self.__filesSelected)

        # apply accept mode and selection mode according to option
        self.setAcceptMode(self.__options[WDialogFile.OPTION_ACCEPT_MODE])
        self.setFileMode(self.__options[WDialogFile.OPTION_FILE_SELECTION_MODE])

    def __insertRowGridLayout(self, insertWidget, gridLayout, insertAtRow=0, rowSpan=1, columnSpan=1):
        """Insert a row in a grid layout"""
        # the dirty way to reorganize layout...
        # in synthesis: QGridLayout doesn't allows to INSERT rows
        # solution: 1) take all items from layout (until there's no item in layout)
        #           2) append message
        #           3) append taken item in initial order, with row offset + 1
        rows = {}
        while gridLayout.count():
            # take all items
            # returned position is an array:
            #   0: row
            #   1: column
            #   2: rowSpan
            #   3: columnSpan
            position = gridLayout.getItemPosition(0)

            if not position[0] in rows:
                # row not yet processed
                # initialise dictionary for row
                rows[position[0]] = []

            rows[position[0]].append((position, gridLayout.takeAt(0)))

        # appends taken items
        rowOffset = 0
        for row in list(rows.keys()):
            if insertAtRow == row:
                # insert expected widget at expected row
                rowOffset += 1
                gridLayout.addWidget(insertWidget, insertAtRow, 0, rowSpan, columnSpan)

            # append original items
            for itemNfo in rows[row]:
                # 0: position
                #       0: row
                #       1: column
                #       2: rowSpan
                #       3: columnSpan
                # 1: item
                gridLayout.addItem(itemNfo[1], itemNfo[0][0]+rowOffset, itemNfo[0][1], itemNfo[0][2], itemNfo[0][3])

    def showEvent(self, event):
        """Dialog box become visible, can recalculate size"""
        if self.__teMessage is not None:
            # Ideal size can't be applied until widgets are shown because document
            # size (especially height) can't be known unless QTextEdit widget is visible
            self.__applyMessageIdealSize(self.__message)
            # calculate QDialog size according to content
            self.adjustSize()
            # and finally, remove constraint for QTextEdit size (let user resize dialog box if needed)
            self.__teMessage.setMinimumSize(0, 0)

        if self.__options[WDialogFile.OPTION_SETTINGS_WIDGET] is not None:
            # calculate QDialog size according to content
            self.adjustSize()

        self.resize(self.width() + self.__options[WDialogFile.OPTION_PREVIEW_WIDTH], self.height())

    def __applyMessageIdealSize(self, message):
        """Try to calculate and apply ideal size for dialog box"""
        # get primary screen (screen on which dialog is displayed) size
        rect = QGuiApplication.primaryScreen().size()
        # and determinate maximum size to apply to dialog box when displayed
        # => note, it's not the maximum window size (user can increase size with grip),
        #    but the maximum we allow to use to determinate window size at display
        # => factor are arbitrary :)
        maxW = round(rect.width() * 0.5 if rect.width() > 1920 else rect.width() * 0.7 if rect.width() > 1024 else rect.width() * 0.9)
        maxH = round(rect.height() * 0.5 if rect.height() > 1080 else rect.height() * 0.7 if rect.height() > 1024 else rect.height() * 0.9)
        # let's define some minimal dimension for message box...
        minW = 320
        minH = 140

        # an internal document used to calculate ideal width
        # (ie: using no-wrap for space allows to have an idea of maximum text width)
        document = QTextDocument()
        document.setDefaultStyleSheet("p { white-space: nowrap; }")
        document.setHtml(message)

        # then define our QTextEdit width taking in account ideal size, maximum and minimum allowed width on screen
        self.__teMessage.setMinimumWidth(max(minW, min(maxW, document.idealWidth())))

        docHeight = round(self.__teMessage.document().size().height()+25)
        # now QTextEdit widget has a width defined, we can retrieve height of document
        # (ie: document's height = as if we don't have scrollbars)
        # add a security margin of +25 pixels
        minHeight = max(minH, min(maxH, docHeight))
        maxHeight = min(maxH, max(minH, docHeight))

        self.__teMessage.setMinimumHeight(minHeight)
        self.__teMessage.setMaximumHeight(maxHeight)

    def __changed(self, path):
        """File has been changed"""
        def updateOpenBtn(isValid, enabledUpdate):
            button = None
            if buttonBox := self.findChild(QDialogButtonBox):
                if self.acceptMode() == QFileDialog.AcceptOpen:
                    button = buttonBox.button(QDialogButtonBox.Open)

            if button:
                button.setUpdatesEnabled(enabledUpdate)
                # if button is disabled by QFileDialog, keep it disabled
                isValid &= button.isEnabled()
                button.setEnabled(isValid)

        isValid = True
        if self.__options[WDialogFile.OPTION_PREVIEW_WIDGET]:
            isValid &= self.__options[WDialogFile.OPTION_PREVIEW_WIDGET].setFile(path)

        if self.__options[WDialogFile.OPTION_SETTINGS_WIDGET]:
            isValid &= self.__options[WDialogFile.OPTION_SETTINGS_WIDGET].setFile(path)

        # if widget indicate file is not valid, disable Open button
        # -- a dirty trick to update open button: update it after a short time
        #    because native QFileDialog enabled/disable button after currentChanged signal, according to selected file(s)
        #    5ms should be enough
        updateOpenBtn(isValid, False)
        QTimer.singleShot(5, lambda: updateOpenBtn(isValid, True))

    def __fileSelected(self, file):
        """A file has been selected
        Set when:
            WDialogFile.AnyFile
            WDialogFile.ExistingFile
            WDialogFile.Directory
        """
        self.__selectedFile = file

    def __filesSelected(self, files):
        """One or files file have been selected
        Set when:
            WDialogFile.ExistingFiles
        """
        self.__selectedFiles = files

    def file(self):
        """return selected file name"""
        return self.__selectedFile

    def files(self):
        """return list of selected files"""
        return self.__selectedFiles

    def widgetPreviewInformation(self):
        """Return eventual information from preview widget, or None"""
        if self.__options[WDialogFile.OPTION_PREVIEW_WIDGET] is None:
            return None
        return self.__options[WDialogFile.OPTION_PREVIEW_WIDGET].information()

    def widgetSettingsInformation(self):
        """Return eventual information from settings widget, or None"""
        if self.__options[WDialogFile.OPTION_SETTINGS_WIDGET] is None:
            return None
        return self.__options[WDialogFile.OPTION_SETTINGS_WIDGET].information()
