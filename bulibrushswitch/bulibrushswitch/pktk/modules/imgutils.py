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
# The imgutils module provides miscellaneous image functions
#
# -----------------------------------------------------------------------------

from PyQt5.Qt import *
from PyQt5.QtGui import (
        QBrush,
        QPainter,
        QPixmap,
        QColor,
        QPolygon,
        QPen,
        QIcon,
        QImage
    )

from math import ceil
import re
import pickle

from ..pktk import *


def warningAreaBrush(size=32):
    """Return a checker board brush"""
    tmpPixmap = QPixmap(size, size)
    tmpPixmap.fill(QColor(255, 255, 255, 32))
    brush = QBrush(QColor(0, 0, 0, 32))

    canvas = QPainter()
    canvas.begin(tmpPixmap)
    canvas.setPen(Qt.NoPen)
    canvas.setBrush(brush)

    s1 = size >> 1
    s2 = size - s1

    canvas.setRenderHint(QPainter.Antialiasing, True)
    canvas.drawPolygon(QPolygon([QPoint(s1, 0), QPoint(size, 0), QPoint(0, size), QPoint(0, s1)]))
    canvas.drawPolygon(QPolygon([QPoint(size, s1), QPoint(size, size), QPoint(s1, size)]))
    canvas.end()

    return QBrush(tmpPixmap)


def checkerBoardBrush(size=32, color1=QColor(255, 255, 255), color2=QColor(220, 220, 220), strictSize=True):
    """Return a checker board brush"""
    s1 = size >> 1
    if strictSize:
        s2 = size - s1
    else:
        s2 = s1

    size = s1+s2

    tmpPixmap = QPixmap(size, size)
    tmpPixmap.fill(color1)
    brush = QBrush(color2)

    canvas = QPainter()
    canvas.begin(tmpPixmap)
    canvas.setPen(Qt.NoPen)

    canvas.setRenderHint(QPainter.Antialiasing, False)
    canvas.fillRect(QRect(0, 0, s1, s1), brush)
    canvas.fillRect(QRect(s1, s1, s2, s2), brush)
    canvas.end()

    return QBrush(tmpPixmap)


def checkerBoardImage(size, checkerSize=32):
    """Return a checker board image"""
    if isinstance(size, int):
        size = QSize(size, size)

    if not isinstance(size, QSize):
        return None

    pixmap = QPixmap(size)
    painter = QPainter()
    painter.begin(pixmap)
    painter.fillRect(pixmap.rect(), checkerBoardBrush(checkerSize))
    painter.end()

    return pixmap


def roundedPixmap(pixmap, radius=0.25, size=None):
    """return `pixmap` to given `size`, with rounded `radius`

    If `size` is None, use pixmap size
    If `radius` is given as integer, radius size is absolute (given in pixels)
    If `radius` is given as float, radius size is relative (given in percent)
   """
    if not isinstance(pixmap, QPixmap):
        raise EInvalidType('Given `pixmap` must be a <QPixmap>')
    elif not isinstance(radius, (int, float)) or radius < 0:
        raise EInvalidType('Given `radius` must be a positive <int> or <float>')

    if size is None:
        size = pixmap.size()

    if isinstance(radius, float):
        # given as percent, then relative
        radius *= 100
        radiusSizeMode = Qt.RelativeSize
    else:
        radiusSizeMode = Qt.AbsoluteSize

    workPixmap = QPixmap(size)
    workPixmap.fill(Qt.transparent)

    painter = QPainter(workPixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(Qt.NoPen))
    painter.setBrush(QBrush(Qt.black))
    painter.drawRoundedRect(0, 0, size.width(), size.height(), radius, radius, radiusSizeMode)
    painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    if size != pixmap.size():
        painter.drawPixmap(0, 0, pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        painter.drawPixmap(0, 0, pixmap)

    painter.end()
    return workPixmap


def bullet(size=16, color=QColor(255, 255, 255), shape='square', scaleShape=1.0, radius=0.25):
    """Draw a bullet and return it as a QPixmap

    Given `size` define size of pixmap (width=height)
    Given `color` define color bullet
    Given `shape` define bullet shape ('circle' or 'square')
    Given `scaleShape` define size of bullet in pixmap (1.0 = 100% / 0.5=50% for example)

    If `radius` is given as integer, radius size is absolute (given in pixels)
    If `radius` is given as float, radius size is relative (given in percent)
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    canvas = QPainter()
    canvas.begin(pixmap)
    canvas.setPen(Qt.NoPen)

    shapeWidth = size*scaleShape
    offset = (size-shapeWidth)/2

    if shape == 'square':
        canvas.fillRect(QRectF(offset, offset, shapeWidth, shapeWidth), color)
    elif shape == 'roundSquare':
        if isinstance(radius, float):
            # given as percent, then relative
            radius *= 100
            radiusSizeMode = Qt.RelativeSize
        else:
            radiusSizeMode = Qt.AbsoluteSize

        canvas.setBrush(color)
        canvas.drawRoundedRect(QRectF(offset, offset, shapeWidth, shapeWidth), radius, radius, radiusSizeMode)
    elif shape == 'circle':
        canvas.setBrush(color)
        canvas.drawEllipse(QRectF(offset, offset, shapeWidth, shapeWidth))
    else:
        raise EInvalidValue("Given `shape` value is not valid")

    canvas.end()
    return pixmap


def paintOpaqueAsColor(pixmap, color):
    """From given pixmap, non transparent color are replaced with given color"""
    if isinstance(pixmap, QPixmap):
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(),  color)
    return pixmap


def buildIcon(icons, size=None):
    """Return a QIcon build from given icons


    Given `icons` can be:
    - A string "pktk:XXXX"
        Where XXXX is name of a PkTk icon
        Return QIcon() will provide normal/disable icons
    - A string "krita:XXXX"
        Where XXXX is name of a Krita icon
        Return QIcon() will provide normal/disable icons
    - A list of tuple
        Each tuple can be:
            (QPixmap, )
            (QPixmap, QIcon.Mode)
            (QPixmap, QIcon.Mode, QIcon.State)
            (str, )
            (str, QIcon.Mode)
            (str, QIcon.Mode, QIcon.State)

    If provided, given `size` can be an <int> or an <QSize>
    """
    if isinstance(icons, QIcon):
        return icons
    elif isinstance(icons, list) and len(icons) > 0:
        returned = QIcon()

        if isinstance(size, int):
            appliedSize = QSize(size, size)
        elif isinstance(size, QSize):
            appliedSize = size
        else:
            appliedSize = QSize()

        for icon in icons:
            addPixmap = False
            if isinstance(icon[0], QPixmap):
                addPixmap = True
                iconListItem = [icon[0]]
            elif isinstance(icon[0], str):
                iconListItem = [icon[0], appliedSize]
            else:
                continue

            for index in range(1, 3):
                if index == 1:
                    if len(icon) >= 2:
                        iconListItem.append(icon[index])
                    else:
                        iconListItem.append(QIcon.Normal)
                elif index == 2:
                    if len(icon) >= 3:
                        iconListItem.append(icon[index])
                    else:
                        iconListItem.append(QIcon.Off)

            if addPixmap:
                returned.addPixmap(*tuple(iconListItem))
            else:
                returned.addFile(*tuple(iconListItem))
        return returned
    elif isinstance(icons, str) and (rfind := re.match("pktk:(.*)", icons)):
        return buildIcon([(f':/pktk/images/normal/{rfind.groups()[0]}', QIcon.Normal),
                          (f':/pktk/images/disabled/{rfind.groups()[0]}', QIcon.Disabled)], size)
    elif isinstance(icons, str) and (rfind := re.match("krita:(.*)", icons)):
        return Krita.instance().icon(rfind.groups()[0])
    elif isinstance(icons, str) and (rfind := re.match("qicon:b64=(.*)", icons)):
        icon = QIconPickable()
        icon.fromB64(icons)
        return icon
    else:
        raise EInvalidType("Given `icons` must be a <str> or a <list> of <tuples>")


def getIconList(source=[]):
    """Return a list of icon uri for given `source"

    Given `source` van be:
    - icons from pktk library:  'pktk'
    - icons from Krita:         'krita'

    if source is not provided, return a list of uri from all sources
    """
    if not isinstance(source, list):
        raise EInvalidType("Given `source` must be a <list>")
    elif len(source) == 0:
        source = ('pktk', 'krita')

    addPkTk = ('pktk' in source)
    addKrita = ('krita' in source)

    if not (addPkTk | addKrita):
        raise EInvalidValue("Given `source` must be empty or contain at least 'pktk' or 'krita'")

    returned = []
    resIterator = QDirIterator(":", QDirIterator.Subdirectories)

    while resIterator.hasNext():
        resName = resIterator.filePath()

        if addPkTk:
            if name := re.search(r"^:/pktk/images/normal/(.+)$", resName):
                returned.append(f'pktk:{name.groups()[0]}')

        if addKrita:
            if name := re.match(r"^:/(?:16_dark|dark)_(.*)\.svg$", resName):
                returned.append(f'krita:{name.groups()[0]}')

        resIterator.next()

    returned.sort()

    return returned


def qImageToPngQByteArray(image):
    """Convert a QImage as PNG and return a QByteArray"""
    if isinstance(image, QImage):
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()
        return ba
    return QByteArray()


def imgBoxSize(imageSize, boxSize):
    """Return size of given `imageSize` to fit within `boxSize`"""
    if not isinstance(imageSize, QSize):
        raise EInvalidType("Given `imageSize` must be a <QSize>")

    if not isinstance(boxSize, QSize):
        raise EInvalidType("Given `boxSize` must be a <QSize>")

    imageRatio = imageSize.width()/imageSize.height()
    boxRatio = boxSize.width()/boxSize.height()

    if boxRatio > imageRatio:
        h = boxSize.height()
        w = round(h*imageRatio)
    else:
        w = boxSize.width()
        h = round(w/imageRatio)

    return QSize(w, h)


def combineChannels(bytesPerChannel, *channels):
    """Combine given channels

    Given `bytesPerChannel` define how many byte are used for one pixel in channels
    Given `channels` are bytes or bytesarray (or memory view on bytes/bytearray)

    Return a bytearray

    Example:
        bytes per channel = 1
        channels =  red=[0xff, 0x01, 0x02]
                    green=[0x03, 0xff, 0x04]
                    blue=[0x05, 0x06, 0xff]

        returned byte array will be
        (0xff, 0x03, 0x05,
         0x01, 0xff, 0x06,
         0x02, 0x06, 0xff)
    """
    # First, need to ensure that all channels have the same size
    channelSize = None
    for channel in channels:
        if channelSize is None:
            channelSize = len(channel)
        elif channelSize != len(channel):
            raise EInvalidValue("All `channels` must have the same size")

    channelCount = len(channels)
    offsetTargetInc = channelCount*bytesPerChannel
    targetSize = channelSize*offsetTargetInc
    target = bytearray(targetSize)

    channelNumber = 0
    for channel in channels:
        offsetTarget = channelNumber*bytesPerChannel
        offsetSource = 0
        for index in range(channelSize//bytesPerChannel):
            target[offsetTarget] = channel[offsetSource]
            offsetTarget += offsetTargetInc
            offsetSource += bytesPerChannel
        channelNumber += 1

    return target


def convertSize(value, fromUnit, toUnit, resolution, roundValue=None):
    """Return converted `value` from given `fromUnit` to `toUnit`, using given `resolution` (if unit conversion implies px)

    Given `fromUnit` and `toUnit` can be:
        px: pixels
        mm: millimeters
        cm: centimeters
        in: inchs

    Given `fromUnit` can also be provided as 'pt' (points)

    The `roundValue` allows to define number of decimals for conversion
    If None is provided, according to `toUnit`:
        px: 0
        mm: 0
        cm: 2
        in: 4
    """
    if roundValue is None:
        if toUnit == 'in':
            roundValue = 4
        elif toUnit == 'cm':
            roundValue = 2
        else:
            roundValue = 0

    if resolution == 0:
        # avoid division by zero
        resolution = 1.0

    if fromUnit == 'mm':
        if toUnit == 'cm':
            return round(value/10, roundValue)
        elif toUnit == 'in':
            return round(value/25.4, roundValue)
        elif toUnit == 'px':
            return round(convertSize(value, fromUnit, 'in', resolution) * resolution, roundValue)
    elif fromUnit == 'cm':
        if toUnit == 'mm':
            return round(value*10, roundValue)
        elif toUnit == 'in':
            return round(value/2.54, roundValue)
        elif toUnit == 'px':
            return round(convertSize(value, fromUnit, 'in', resolution) * resolution, roundValue)
    elif fromUnit == 'in':
        if toUnit == 'mm':
            return round(value*25.4, roundValue)
        elif toUnit == 'cm':
            return round(value*2.54, roundValue)
        elif toUnit == 'px':
            return round(value * resolution, roundValue)
    elif fromUnit == 'px':
        if toUnit == 'mm':
            return round(convertSize(value, fromUnit, 'in', resolution)*25.4, roundValue)
        elif toUnit == 'cm':
            return round(convertSize(value, fromUnit, 'in', resolution)*2.54, roundValue)
        elif toUnit == 'in':
            return round(value / resolution, roundValue)
    elif fromUnit == 'pt':
        if toUnit == 'mm':
            return round(value * 0.35277777777777775, roundValue)   # 25.4/72
        elif toUnit == 'cm':
            return round(value * 0.035277777777777775, roundValue)  # 2.54/72
        elif toUnit == 'in':
            return round(value / 72, roundValue)
        elif toUnit == 'px':
            return round(resolution * convertSize(value, fromUnit, 'in', resolution)/72, roundValue)
    # all other combination are not valid, return initial value
    return value


def megaPixels(value, roundDec=2):
    """return value (in pixels) as megapixels rounded to given number of decimal"""
    if value is None or value == 0:
        return ""
    if value < 100000:
        return f"{ceil(value/10000)/100:.0{roundDec}f}"
    return f"{ceil(value/100000)/10:.0{roundDec}f}"


def ratioOrientation(ratio):
    """return ratio text for a given ratio value"""
    if ratio is None:
        return ""
    elif ratio < 1:
        return i18n("Portrait")
    elif ratio > 1:
        return i18n("Landscape")
    else:
        return i18n("Square")


class QIconPickable(QIcon):
    """A QIcon class that is serializable from pickle"""
    def __reduce__(self):
        return type(self), (), self.__getstate__()

    def __getstate__(self):
        ba = QByteArray()
        stream = QDataStream(ba, QIODevice.WriteOnly)
        stream << self
        return ba

    def __setstate__(self, ba):
        stream = QDataStream(ba, QIODevice.ReadOnly)
        stream >> self

    def toB64(self, pktkFormat=True):
        """Return a base64 string from current object"""
        returned = bytes(self.__getstate__().toBase64()).decode()
        if pktkFormat:
            returned = f'qicon:b64={returned}'

        return returned

    def fromB64(self, value):
        """Set from a base64 string"""
        if b64 := re.search("^qicon:b64=(.*)", value):
            value = b64.groups()[0]

        self.__setstate__(QByteArray.fromBase64(value.encode()))


class QUriIcon(QObject):
    """Associate an uri with QIcon"""
    def __init__(self, uri=None, icon=None, maxSize=None):
        self.__icon = None
        self.__uri = ''
        self.__maxSize = None

        if isinstance(maxSize, QSize):
            self.__maxSize = maxSize

        self.setUri(uri, icon)

    def __repr__(self):
        """Return string reprensentation for object"""
        if self.__uri == '':
            return "<QUriIcon(None)>"
        else:
            return f"<QUriIcon({self.__uri})>"

    def uri(self):
        """Return uri for icon"""
        return self.__uri

    def setUri(self, uri, icon=None):
        """Set uri for icon

        Given `uri` can be:{argument
        - a QUriIcon
        - a string ('pktk:xxx', 'krita:xxx', or a filename)

        If `uri` is a string and `icon` a <QIcon>, given icon is used for given uri
        """
        loadIcon = None
        if uri is None:
            self.__uri = ''
        elif isinstance(uri, QUriIcon):
            self.setUri(uri.uri(), uri.icon())
            return
        elif not isinstance(uri, str):
            raise EInvalidType('Given `uri` must be a <str> or <QUriIcon>')
        elif re.match("^(pktk|krita):", uri):
            loadIcon = QIconPickable(buildIcon(uri))
        else:
            # a file?
            if self.__maxSize is None:
                loadIcon = QIconPickable(uri)
            else:
                pixmap = QPixmap(uri)
                if pixmap.width() > self.__maxSize.width() or pixmap.height() > self.__maxSize.height():
                    # scale only if given image is greater than expected size:
                    pixmap = pixmap.scaled(self.__maxSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                loadIcon = QIconPickable(pixmap)

        if isinstance(icon, QIcon) and isinstance(uri, str):
            # an icon is provided, use it
            loadIcon = icon

        if loadIcon is not None:
            # icon is valid
            self.__uri = uri
            self.__icon = loadIcon

    def icon(self):
        """Return QIconPickable icon or None"""
        return self.__icon
