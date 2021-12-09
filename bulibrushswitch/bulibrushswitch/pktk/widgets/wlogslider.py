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
from math import log10

import PyQt5.uic

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QSlider
    )


# adapted from solution found on Stack Overflow
# https://stackoverflow.com/a/68227820

class WLogSlider(QSlider):
    """A slider with logarithmic scale"""
    naturalValueChanged=Signal(float)

    def __init__(self, parent=None):
        super(WLogSlider, self).__init__(parent)

        self.__naturalMinimumValue=0.01
        self.__naturalMaximumValue=100.00

        self.__scale=1000
        self.__naturalValue=1
        self.valueChanged.connect(self.__onValueChanged)

    def __onValueChanged(self, value):
        """Value has been modified"""
        self.__naturalValue=pow(10, (value / self.__scale))
        self.naturalValueChanged.emit(self.__naturalValue)

    def setNaturalMin(self, value):
        """Set minimum value"""
        if value>0:
            self.__naturalMinimumValue=value
            self.setMinimum(int(log10(value) * self.__scale))

    def setNaturalMax(self, value):
        """Set maximum value"""
        if value > 0:
            self.__naturalMaximumValue=value
            self.setMaximum(int(log10(value) * self.__scale))

    def setNaturalValue(self, value):
        """Set value"""
        self.__naturalValue=value
        self.setValue(int(log10(value) * self.__scale))

    def naturalValue(self, value):
        """return value"""
        return self.__naturalValue

    def scale(self):
        """Return scale"""
        return self.__scale

    def setScale(self, value):
        """Define scale for slider"""
        if isinstance(value, (int, float)) and value>0 and value!=self.__scale:
            self.__scale=value
            # need to recalculate min/max according to new scale
            self.setNaturalMin(self.__naturalMinimumValue)
            self.setNaturalMax(self.__naturalMaximumValue)
            self.setNaturalValue(self.__naturalValue)
