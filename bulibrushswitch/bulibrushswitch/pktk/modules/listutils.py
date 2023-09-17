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
# The imgutils module provides miscellaneous list functions
#
# -----------------------------------------------------------------------------

from PyQt5.QtGui import QTextFormat

from ..pktk import *

EXTRASELECTION_FILTER_KEEP =    0x0001
EXTRASELECTION_FILTER_REMOVE =  0x0002
EXTRASELECTION_FILTER_FCTTRUE = 0x0003


def flatten(items):
    """Return a flatten list whatever the number of nested level the list have

    f=flatten([1,2,[3,4],[5,[6,7],[8,[9,10]]]])

    f: [1,2,3,4,5,6,7,8,9,10]
    """
    returned = []
    for item in items:
        if isinstance(item, (list, tuple)):
            returned.extend(flatten(item))
        else:
            returned.append(item)
    return returned


def rotate(items, shiftValue=1):
    """Rotate list

    - Positive `shiftValue` will rotate to right
    - Negative `shiftValue` will rotate to left


    l=[1,2,3,4]

    x=rotate(l, 1)
    x: [4,1,2,3]

    x=rotate(l, -1)
    x: [2,3,4,1]

    """
    shiftValue = shiftValue % len(items)
    if shiftValue == 0:
        # no rotation...
        return items
    # do rotation
    return items[-shiftValue:] + items[:-shiftValue]


def unique(items):
    """Return list of items with duplicate removed

    Initial order list is preserved
    Note: works with non-hashable object
    """
    # a faster method could be return list(set(items))
    # but it doesn't work with non-hashable object (like a QColor for example)
    returned = []
    for item in items:
        if item not in returned:
            returned.append(item)
    return returned


def sortExtraSelections(extraSelection):
    """Sort given `extraSelection` list from item's format.property

    1) items with format.property(QTextFormat.UserProperty)
       - sorted by extraSelection.format.property(QTextFormat.UserProperty) value
    2) items without format.property(QTextFormat.UserProperty)
       - no special order, just set 'after items with property QTextFormat.UserProperty'
    """
    def checkType(value):
        returned = value.format.property(QTextFormat.UserProperty)
        if returned:
            return returned
        return 0xFFFFFFFF
    if not isinstance(extraSelection, list):
        raise EInvalidType('Given `extraSelection` must be a <list>')
    extraSelection.sort(key=checkType)


def filterExtraSelections(extraSelection, filterValue, filterRule=EXTRASELECTION_FILTER_KEEP, filterProperty=QTextFormat.UserProperty, sortResult=False, stopOnFirst=False, removed=[]):
    """Sort given `extraSelection` list from item's property

    If `filterProperty` is given, define on which extraSelection.format.property(filterProperty) value is filtered

    Given `filterRule` define what to do:
    - EXTRASELECTION_FILTER_KEEP (default):
        only keep items for which extraSelection.format.property(filterProperty) equal `filterValue`
        (in this case, items without property are removed)
    - EXTRASELECTION_FILTER_REMOVE:
        only keep items for which extraSelection.format.property(filterProperty) do not equal `filterValue`
        (in this case, items without property are removed)
    - EXTRASELECTION_FILTER_FCTTRUE
        in this cas `filterValue` is a callable function for which:
        - extraSelection item is provided
        - returned result is a boolean:
            . True = keep item
            . False = remove item

    If `sortResult` is True, filtered list is sorted, otherwise returned list keep initial item orders

    If `stopOnFirst` is True (default is False), stop to filter on first occurence found
    This can be used when we know there's normally no more than one occurence of item to filter in list
    """
    if not isinstance(extraSelection, list):
        raise EInvalidType('Given `extraSelection` must be a <list>')

    removed.clear()
    if filterRule == EXTRASELECTION_FILTER_FCTTRUE:
        if not callable(filterValue):
            raise EInvalidType("Given `filterValue` must be a callable when `filterRule` is set to EXTRASELECTION_FILTER_FCTTRUE")

        index = len(extraSelection) - 1
        while index >= 0:
            if filterValue(extraSelection[index]) is False:
                removed.append(extraSelection.pop(index))
                if stopOnFirst:
                    return
            index -= 1
    elif filterRule == EXTRASELECTION_FILTER_KEEP:
        index = len(extraSelection) - 1
        while index >= 0:
            if extraSelection[index].format.property(filterProperty) != filterValue:
                removed.append(extraSelection.pop(index))
                if stopOnFirst:
                    return
            index -= 1
    elif filterRule == EXTRASELECTION_FILTER_REMOVE:
        index = len(extraSelection) - 1
        while index >= 0:
            if extraSelection[index].format.property(filterProperty) == filterValue:
                removed.append(extraSelection.pop(index))
                if stopOnFirst:
                    return
            index -= 1
