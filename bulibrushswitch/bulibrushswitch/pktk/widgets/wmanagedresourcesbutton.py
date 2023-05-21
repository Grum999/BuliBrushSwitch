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
# The wmanagedresourcesbutton module provides a resource button choser
#
# Main class from this module
#
# - WManagedResourcesButton:
#       Widget
#       The resource button
#
# -----------------------------------------------------------------------------

from math import ceil

from krita import Resource

import PyQt5.uic

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QPushButton,
    )

from ..modules.imgutils import checkerBoardBrush
from ..modules.resutils import (ManagedResource, ManagedResourceTypes)
from .wmenuitem import WMenuManagedResourcesSelector


class WManagedResourcesButton(QToolButton):
    """A button to choose color"""
    resourceChanged = Signal(ManagedResource)

    def __init__(self, label=None, parent=None):
        super(WManagedResourcesButton, self).__init__(parent)

        def newSetText(value):
            # don't let external code trying to set button text: there's no text :)
            pass

        self.__pen = QPen(QColor("#88888888"))
        self.__pen.setWidth(1)

        self.__havePopupMenu = True
        self.__noneResource = ManagedResource()
        self.__managedResource = self.__noneResource

        self.__manageNoneResource = True

        self.__cbBrushDiagPat = QBrush(QColor("#88888888"), Qt.BDiagPattern)

        self.__noResourceTooltip = ''
        self.__resourceTooltip = ''

        self.__actionNoResource = QAction(i18n('None'), self)
        self.__actionNoResource.triggered.connect(self.__setManagedResourceNone)

        self.__actionFromManagedResourcesSelector = WMenuManagedResourcesSelector()
        self.__actionFromManagedResourcesSelector.managedResourcesSelector().selectionChanged.connect(self.__setManagedResource)

        self.__menu = QMenu(self)
        self.__menu.addAction(self.__actionNoResource)
        self.__menu.addAction(self.__actionFromManagedResourcesSelector)

        self.setText("")
        self.setText = newSetText

        self.__setPopupMenu()
        self.setManageNoneResource(True)
        self.setManagedResourceType(ManagedResourceTypes.RES_GRADIENTS)

    def __setPopupMenu(self):
        """Define popup menu according to options"""
        self.__actionNoResource.setVisible(self.__manageNoneResource)

        if self.__havePopupMenu:
            self.setPopupMode(QToolButton.InstantPopup)
            self.setArrowType(Qt.NoArrow)
            self.setMenu(self.__menu)
            self.setStyleSheet("""WManagedResourcesButton::menu-indicator { width: 0; } """)
        else:
            self.setPopupMode(QToolButton.DelayedPopup)
            self.setMenu(None)

    def __setManagedResourceNone(self):
        """Set current resource to None"""
        self.setResource(self.__noneResource)
        self.resourceChanged.emit(self.__managedResource)

    def __setManagedResource(self, managedResources):
        """Set cresrouce from managed resource selector"""
        if len(managedResources) > 0:
            self.setResource(managedResources[0])
        else:
            self.setResource(self.__noneResource)
        self.resourceChanged.emit(self.__managedResource)

    def __updateTooltip(self):
        """update button tooltip"""
        if self.__managedResource.id() is None:
            self.setToolTip(self.__noResourceTooltip)
        else:
            self.setToolTip(f"{self.__resourceTooltip}<br>{self.__managedResource.tooltip()}")

    def sizeHint(self):
        """calculate size hint"""
        returned = super(WManagedResourcesButton, self).sizeHint()
        if self.__actionFromManagedResourcesSelector.managedResourcesSelector().resourceTypes()[0] == ManagedResourceTypes.RES_GRADIENTS:
            returned.setWidth(returned.width() << 1)
        return returned

    def paintEvent(self, event):
        super(WManagedResourcesButton, self).paintEvent(event)

        margin = 5  # ceil(self.height()/2)//3
        margin2 = margin << 1
        if not self.icon().isNull():
            rect = QRect(margin, self.height() - margin//2 - 4, self.width() - margin2, margin//2)
        else:
            rect = QRect(margin, margin, self.width() - margin2,  self.height() - margin2)

        painter = QPainter(self)
        painter.setPen(self.__pen)
        if self.__managedResource.id() is None:
            painter.fillRect(rect, self.__cbBrushDiagPat)
        else:
            painter.drawPixmap(rect.topLeft(), self.__managedResource.thumbnail().scaled(rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        painter.drawRect(rect)

    def resource(self):
        """Return current button color"""
        return self.__managedResource

    def setResource(self, managedResource):
        """Set current button resource"""
        if managedResource is None:
            managedResource = self.__noneResource

        self.__managedResource = managedResource
        self.__actionFromManagedResourcesSelector.managedResourcesSelector().setSelectedResources(self.__managedResource)
        self.__updateTooltip()
        self.update()

    def manageNoneResource(self):
        """Return if no color value is managed or not"""
        return self.__manageNoneResource

    def setManageNoneResource(self, value):
        """Set if no resource is managed or not

        If true, button is delayed popup with a menu:
        - "None"
        - From resource
        """
        if isinstance(value, bool):
            self.__manageNoneResource = value
            self.__setPopupMenu()

    def popupMenu(self):
        """Return if button have popup menu (ie: manage colors through menu)"""
        return self.__havePopupMenu

    def setPopupMenu(self, value):
        """Set if button have popup menu

        If true, button is delayed popup with a menu
        Otherwise resource selection method have to be implemented
        """
        if isinstance(value, bool):
            self.__havePopupMenu = value
            self.__setPopupMenu()

    def managedResourceType(self):
        """Return which type of resource is managed by button"""
        return self.__actionFromManagedResourcesSelector.managedResourcesSelector().resourceTypes()[0]

    def setManagedResourceType(self, resourceType):
        """Set which type of resource is managed by button"""
        if not isinstance(resourceType, ManagedResourceTypes):
            raise EInvalidType("Given `resourceType` must be a resource type")

        match resourceType:
            case ManagedResourceTypes.RES_GRADIENTS:
                self.__noResourceTooltip = i18n('No gradient')
                self.__resourceTooltip = i18n('Gradient')
            case ManagedResourceTypes.RES_PALETTES:
                self.__noResourceTooltip = i18n('No palette')
                self.__resourceTooltip = i18n('Palette')
            case ManagedResourceTypes.RES_PATTERNS:
                self.__noResourceTooltip = i18n('No pattern')
                self.__resourceTooltip = i18n('Pattern')
            case ManagedResourceTypes.RES_PRESETS:
                self.__noResourceTooltip = i18n('No preset')
                self.__resourceTooltip = i18n('Preset')

        self.__actionNoResource.setText(self.__noResourceTooltip)
        self.__actionFromManagedResourcesSelector.managedResourcesSelector().setResourceTypes(resourceType)
        self.__updateTooltip()

    def managedResourcesSelector(self):
        """Return color picker instance, allowing to define options for it"""
        return self.__actionFromManagedResourcesSelector.managedResourcesSelector()
