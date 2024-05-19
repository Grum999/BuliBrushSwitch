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
# The colorutils module provides miscellaneous color functions
#
# Main class from this module
#
# - QEColor
#       Extend the QColor to support the None value
#       (no color defined != transparent color)
#
# -----------------------------------------------------------------------------


from PyQt5.Qt import *
from PyQt5.QtGui import (
        QColor
    )


def colorSpaceNfo(colorSpace):
    """Return informations for a given color Space

    Example:
        "RGBA" will return dictionary:
            {
                'channelSize': 1,
                'channels': ('Red', 'Green', 'Blue', 'Alpha'),
                'text': 'RGB with Alpha, 8-bit integer/channel'
            }

    If color space is not known, return None
    """
    # Color model id comparison through the ages (from kis_kra_loader.cpp)
    #
    #   2.4        2.5          2.6         ideal
    #
    #   ALPHA      ALPHA        ALPHA       ALPHAU8
    #
    #   CMYK       CMYK         CMYK        CMYKAU8
    #              CMYKAF32     CMYKAF32
    #   CMYKA16    CMYKAU16     CMYKAU16
    #
    #   GRAYA      GRAYA        GRAYA       GRAYAU8
    #   GrayF32    GRAYAF32     GRAYAF32
    #   GRAYA16    GRAYAU16     GRAYAU16
    #
    #   LABA       LABA         LABA        LABAU16
    #              LABAF32      LABAF32
    #              LABAU8       LABAU8
    #
    #   RGBA       RGBA         RGBA        RGBAU8
    #   RGBA16     RGBA16       RGBA16      RGBAU16
    #   RgbAF32    RGBAF32      RGBAF32
    #   RgbAF16    RgbAF16      RGBAF16
    #
    #   XYZA16     XYZA16       XYZA16      XYZAU16
    #              XYZA8        XYZA8       XYZAU8
    #   XyzAF16    XyzAF16      XYZAF16
    #   XyzAF32    XYZAF32      XYZAF32
    #
    #   YCbCrA     YCBCRA8      YCBCRA8     YCBCRAU8
    #   YCbCrAU16  YCBCRAU16    YCBCRAU16
    #              YCBCRF32     YCBCRF32
    channelSize = None
    channels = None
    text = None

    # RGB
    if colorSpace in ['RGBA', 'RGBAU8']:
        cspace = ('RGBA', 'U8')
        channelSize = 1
        channels = ('Red', 'Green', 'Blue', 'Alpha')
        text = 'RGB with Alpha, 8-bit integer/channel'
    elif colorSpace in ['RGBA16', 'RGBAU16']:
        cspace = ('RGBA', 'U16')
        channelSize = 2
        channels = ('Red', 'Green', 'Blue', 'Alpha')
        text = 'RGB with Alpha, 16-bit integer/channel'
    elif colorSpace in ['RgbAF16', 'RGBAF16']:
        cspace = ('RGBA', 'F16')
        channelSize = 2
        channels = ('Red', 'Green', 'Blue', 'Alpha')
        text = 'RGB with Alpha, 16-bit float/channel'
    elif colorSpace in ['RgbAF32', 'RGBAF32']:
        cspace = ('RGBA', 'F32')
        channelSize = 4
        channels = ('Red', 'Green', 'Blue', 'Alpha')
        text = 'RGB with Alpha, 32-bit float/channel'
    # CYMK
    elif colorSpace in ['CMYK', 'CMYKAU8']:
        cspace = ('CMYKA', 'U8')
        channelSize = 1
        channels = ('Cyan', 'Magenta', 'Yellow', 'Black', 'Alpha')
        text = 'CMYK with Alpha, 8-bit integer/channel'
    elif colorSpace in ['CMYKA16', 'CMYKAU16']:
        cspace = ('CMYKA', 'U16')
        channelSize = 2
        channels = ('Cyan', 'Magenta', 'Yellow', 'Black', 'Alpha')
        text = 'CMYK with Alpha, 16-bit integer/channel'
    elif colorSpace in ['CMYKAF32', 'CMYKAF32']:
        cspace = ('CMYKA', 'F32')
        channelSize = 4
        channels = ('Cyan', 'Magenta', 'Yellow', 'Black', 'Alpha')
        text = 'CMYK with Alpha, 32-bit float/channel'
    # GRAYSCALE
    elif colorSpace in ['A', 'G']:
        cspace = ('A', 'U8')
        channelSize = 1
        channels = ('Level',)
        text = 'Grayscale, 8-bit integer/channel'
    elif colorSpace in ['GRAYA', 'GRAYAU8']:
        cspace = ('GRAYA', 'U8')
        channelSize = 1
        channels = ('Gray', 'Alpha')
        text = 'Grayscale with Alpha, 8-bit integer/channel'
    elif colorSpace in ['GRAYA16', 'GRAYAU16']:
        cspace = ('GRAYA', 'U16')
        channelSize = 2
        channels = ('Gray', 'Alpha')
        text = 'Grayscale with Alpha, 16-bit integer/channel'
    elif colorSpace == 'GRAYAF16':
        cspace = ('GRAYA', 'F16')
        channelSize = 2
        channels = ('Gray', 'Alpha')
        text = 'Grayscale with Alpha, 16-bit float/channel'
    elif colorSpace in ['GrayF32', 'GRAYAF32']:
        cspace = ('GRAYA', 'F32')
        channelSize = 4
        channels = ('Gray', 'Alpha')
        text = 'Grayscale with Alpha, 32-bit float/channel'
    # L*A*B*
    elif colorSpace == 'LABAU8':
        cspace = ('LABA', 'U8')
        channelSize = 1
        channels = ('L*', 'a*', 'b*', 'Alpha')
        text = 'L*a*b* with Alpha, 8-bit integer/channel'
    elif colorSpace in ['LABA', 'LABAU16']:
        cspace = ('LABA', 'U16')
        channelSize = 2
        channels = ('L*', 'a*', 'b*', 'Alpha')
        text = 'L*a*b* with Alpha, 16-bit integer/channel'
    elif colorSpace == 'LABAF32':
        cspace = ('LABA', 'F32')
        channelSize = 4
        channels = ('L*', 'a*', 'b*', 'Alpha')
        text = 'L*a*b* with Alpha, 32-bit float/channel'
    # XYZ
    elif colorSpace in ['XYZAU8', 'XYZA8']:
        cspace = ('XYZA', 'U8')
        channelSize = 1
        channels = ('X', 'Y', 'Z', 'Alpha')
        text = 'XYZ with Alpha, 8-bit integer/channel'
    elif colorSpace in ['XYZA16', 'XYZAU16']:
        cspace = ('XYZA', 'U16')
        channelSize = 2
        channels = ('X', 'Y', 'Z', 'Alpha')
        text = 'XYZ with Alpha, 16-bit integer/channel'
    elif colorSpace in ['XyzAF16', 'XYZAF16']:
        cspace = ('XYZA', 'F16')
        channelSize = 2
        channels = ('X', 'Y', 'Z', 'Alpha')
        text = 'XYZ with Alpha, 16-bit float/channel'
    elif colorSpace in ['XyzAF32', 'XYZAF32']:
        cspace = ('XYZA', 'F32')
        channelSize = 4
        channels = ('X', 'Y', 'Z', 'Alpha')
        text = 'XYZ with Alpha, 32-bit float/channel'
    # YCbCr
    elif colorSpace in ['YCbCrA', 'YCBCRA8', 'YCBCRAU8']:
        cspace = ('YCbCrA', 'U8')
        channelSize = 1
        channels = ('Y', 'Cb', 'Cr', 'Alpha')
        text = 'YCbCr with Alpha, 8-bit integer/channel'
    elif colorSpace in ['YCbCrAU16', 'YCBCRAU16']:
        cspace = ('YCbCrA', 'U16')
        channelSize = 2
        channels = ('Y', 'Cb', 'Cr', 'Alpha')
        text = 'YCbCr with Alpha, 16-bit integer/channel'
    elif colorSpace == 'YCBCRF32':
        cspace = ('YCbCrA', 'F32')
        channelSize = 4
        channels = ('Y', 'Cb', 'Cr', 'Alpha')
        text = 'YCbCr with Alpha, 32-bit float/channel'

    if channelSize is None:
        return None

    return {
            'cspace': cspace,
            'channelSize': channelSize,
            'channels': channels,
            'text': text
        }


class QEColor(QColor):
    def __init__(self, value=None):
        if isinstance(value, (QColor, QEColor)):
            super(QEColor, self).__init__(value)
        elif isinstance(value, str):
            super(QEColor, self).__init__(QColor(value))
        else:
            super(QEColor, self).__init__(QColor(Qt.transparent))

        self.__isNone = (value is None)

    def __deepcopy__(self, memo):
        """Used by pickle from copy.deepcopy()"""
        returned = QEColor()
        returned.setNamedColor(self.name())
        returned.setNone(self.__isNone)
        return returned

    def isNone(self):
        return self.__isNone

    def setNone(self, value):
        if isinstance(value, bool):
            self.__isNone = value
