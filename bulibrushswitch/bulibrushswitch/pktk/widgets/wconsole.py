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
# The wconsole module provides a console like output widget
# Note: it's not a TTY console!
#
# Main class from this module
#
# - WConsole:
#       Widget
#       The main console widget
#
# - WConsoleType:
#       Information type for console output line
#
# - WConsoleUserData:
#       User data associated with an output line
#
# - WConsoleGutterArea:
#       Widget to render console gutter
#
# -----------------------------------------------------------------------------

from enum import Enum
import re
import html

from PyQt5.Qt import *
from PyQt5.QtGui import (
        QColor,
        QFont,
        QFontMetrics,
        QFontMetricsF,
        QTextCharFormat,
        QTextCursor,
        QTextBlockUserData,
        QPainter,
        QPen,
        QBrush
    )
from PyQt5.QtCore import (
        pyqtSignal as Signal
    )
from PyQt5.QtWidgets import (
        QWidget
    )

from .wsearchinput import SearchFromPlainTextEdit


class WConsoleType(Enum):
    """Define type of new line append in console

    By default, NORMAL type is applied, and standard rendering is applied to
    console line content

    If type is not NORMAL:
    - A colored bullet is drawn in gutter
      NORMAL:   none
      VALID:    green
      INFO:     cyan
      WARNING:  yellow
      ERROR:    red
    - Background style is colored

    Style (bullet, background, text) can be defined on console
    """
    NORMAL = 0
    VALID = 1
    INFO = 2
    WARNING = 3
    ERROR = 4

    @staticmethod
    def toStr(value):
        values = {
                WConsoleType.VALID: 'valid',
                WConsoleType.INFO: 'info',
                WConsoleType.WARNING: 'warning',
                WConsoleType.ERROR: 'error'
            }
        if value in values:
            return values[value]
        return 'normal'

    @staticmethod
    def fromStr(value):
        values = {
                'valid': WConsoleType.VALID,
                'info': WConsoleType.INFO,
                'warning': WConsoleType.WARNING,
                'error': WConsoleType.ERROR
            }
        if value in values:
            return values[value]
        return WConsoleType.NORMAL


class WConsole(QPlainTextEdit):
    """A console output (no input...)"""

    __TYPE_COLOR_ALPHA = 30

    @staticmethod
    def escape(text):
        """Escape characters used to format data in console:
            '*'
            '#'

        """
        return re.sub(r'([\*\$#])', r'$\1', text)

    @staticmethod
    def unescape(text):
        """unescape characters used to format data in console:
            '*'
            '#'
        """
        return re.sub(r'(?:\$([\*\$#]))', r'\1', text)

    @staticmethod
    def unformat(text):
        """Unformat text passed to console"""
        # bold
        text = re.sub(r'(?<!\$)\*\*(([^*]|\$\*)+)(?<!\$)\*\*', r'\1', text)
        # italic
        text = re.sub(r'(?<!\$)\*(([^*]|\$\*)+)(?<!\$)\*', r'\1', text)
        # color
        text = re.sub(r'(?<!\$)#(l?[rgbcmykw]|[A-F0-9]{6})(?<!\$)#(([^#]|\$#)+)(?<!\$)#', r'\2', text)

        return text

    def __init__(self, parent=None):
        super(WConsole, self).__init__(parent)

        self.setReadOnly(True)

        self.__typeColors = {
                WConsoleType.VALID: QColor('#39b54a'),
                WConsoleType.INFO: QColor('#006fb8'),
                WConsoleType.WARNING: QColor('#ffc706'),
                WConsoleType.ERROR: QColor('#de382b')
            }

        self.__styleColors = {
                'r':  QColor("#de382b"),
                'g':  QColor("#39b54a"),
                'b':  QColor("#006fb8"),
                'c':  QColor("#2cb5e9"),
                'm':  QColor("#762671"),
                'y':  QColor("#ffc706"),
                'k':  QColor("#000000"),
                'w':  QColor("#cccccc"),
                'lr': QColor("#ff0000"),
                'lg': QColor("#00ff00"),
                'lb': QColor("#0000ff"),
                'lc': QColor("#00ffff"),
                'lm': QColor("#ff00ff"),
                'ly': QColor("#ffff00"),
                'lk': QColor("#808080"),
                'lw': QColor("#ffffff")
            }

        # Gutter colors
        # maybe font size/type/style can be modified
        self.__optionGutterText = QTextCharFormat()
        self.__optionGutterText.setBackground(QColor('#282c34'))

        # show gutter with Warning/Error/... message type
        self.__optionShowGutter = True

        # allows key bindings
        self.__optionWheelSetFontSize = True

        # filtered
        self.__optionFilteredTypes = []
        self.__optionFilterExtraSelection = False

        # search object
        self.__search = SearchFromPlainTextEdit(self)

        # ---- Set default font (monospace, 10pt)
        font = QFont()
        font.setStyleHint(QFont.Monospace)
        font.setFamily('DejaVu Sans Mono, Consolas, Courier New')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)

        # ---- instanciate gutter area
        self.__gutterArea = WConsoleGutterArea(self)

        # ---- initialise signals
        self.updateRequest.connect(self.__updateGutterArea)

        # default values
        self.__updateGutterAreaWidth()

        self.setStyleSheet(f"WConsole {{ background: {self.__styleColors['k'].name()}; color: {self.__styleColors['w'].name()};}}")

    def __updateGutterArea(self, rect, deltaY):
        """Called on signal updateRequest()

        Invoked when the editors viewport has been scrolled

        The given `rect` is the part of the editing area that need to be updated (redrawn)
        The given `dy` holds the number of pixels the view has been scrolled vertically
        """
        if self.__optionShowGutter:
            if deltaY > 0:
                self.__gutterArea.scroll(0, deltaY)
            else:
                self.__gutterArea.update(0, rect.y(), self.__gutterArea.width(), rect.height())

            if rect.contains(self.viewport().rect()):
                self.__updateGutterAreaWidth(0)

    def __updateGutterAreaWidth(self, dummy=None):
        """Update viewport margins, taking in account gutter visibility"""
        self.setViewportMargins(self.gutterAreaWidth(), 0, 0, 0)

    def __formatText(self, text):
        """Return a HTML formatted text from a markdown like text

        Allows use of some 'Markdown':
        **XXX**     => bold
        *XXX*       => italic

        #r#XXX#     => RED
        #g#XXX#     => GREEN
        #b#XXX#     => BLUE
        #c#XXX#     => CYAN
        #m#XXX#     => MAGENTA
        #y#XXX#     => YELLOW
        #k#XXX#     => BLACK
        #w#XXX#     => WHITE

        #lr#XXX#    => LIGHT RED
        #lg#XXX#    => LIGHT GREEN
        #lb#XXX#    => LIGHT BLUE
        #lc#XXX#    => LIGHT CYAN
        #lm#XXX#    => LIGHT MAGENTA
        #ly#XXX#    => LIGHT YELLOW
        #lk#XXX#    => LIGHT BLACK (GRAY)
        #lw#XXX#    => LIGHT WHITE

        #xxxxxx#XXX# => Color #xxxxxx

        [c:nn]XXX[/c] => color 'nn'
        """
        def formatText(text):
            regEx = (r"(?:(?<!\$)(#(?:l?[rgbcmykw]|[A-F0-9]{6})(?<!\$)#))|"
                     r"(?<!\$)(#)|"
                     r"(?<!\$)(\*\*)|"
                     r"(?<!\$)(\*)")
            tokens = [token for token in re.split(regEx, text,  flags=re.I | re.M) if token]

            hasColor = False
            returned = []
            bold = False
            italic = False
            color = False
            for token in tokens:
                if token == '**':
                    if bold:
                        returned.append("</b>")
                        bold = False
                    else:
                        returned.append("<b>")
                        bold = True
                elif token == '*':
                    if italic:
                        returned.append("</i>")
                        italic = False
                    else:
                        returned.append("<i>")
                        italic = True
                elif token == '#':
                    if color:
                        returned.append("</span>")
                        color = False
                    else:
                        returned.append(token)
                elif regResult := re.match("#(l?[rgbcmykw]|[A-F0-9]{6})#", token,  flags=re.I):
                    if color:
                        # already in a color block?
                        returned.append(f'</span>')

                    hasColor = True
                    color = True
                    colorCode = regResult.groups()[0]

                    if colorCode in self.__styleColors:
                        colorStyle = self.__styleColors[colorCode].name()
                    else:
                        try:
                            colorStyle = QColor(f'#{colorCode}').name()
                        except Exception as e:
                            colorStyle = None

                    if colorStyle:
                        returned.append(f'<span style="color: {colorStyle};">')
                    else:
                        returned.append(f'<span>')
                else:
                    returned.append(html.escape(WConsole.unescape(token)))

            if hasColor:
                returned.append(f'''<span style="color: {self.__styleColors['w'].name()};"> </span>''')

            return f"<span style='white-space: pre;'>{''.join(returned)}</span>"

        texts = text.split("\n")
        returned = []
        for text in texts:
            returned.append(formatText(text))

        return returned

    def __isTypeFiltered(self, type):
        """Return True if given `type` is filtered"""
        return (type in self.__optionFilteredTypes)

    def __updateFilteredTypes(self):
        """Update current filtered types"""
        self.setUpdatesEnabled(False)

        filterSearch = False
        if self.__optionFilterExtraSelection:
            blockNumbers = [es.cursor.blockNumber() for es in self.extraSelections()]
            filterSearch = len(blockNumbers) > 0

        block = self.document().firstBlock()

        while block.isValid():
            colorLevel = WConsoleType.NORMAL

            blockData = block.userData()
            if blockData:
                colorLevel = block.userData().type()

            if not self.__isTypeFiltered(colorLevel):
                # check if filtered by search only if visible to reduce time analysis
                if filterSearch:
                    block.setVisible(block.blockNumber() in blockNumbers)
                else:
                    block.setVisible(True)
            else:
                block.setVisible(False)
            block = block.next()

        self.setUpdatesEnabled(True)

    # region: event overload ---------------------------------------------------

    def resizeEvent(self, event):
        """Console is resized

        Need to resize the gutter area
        """
        super(WConsole, self).resizeEvent(event)

        if self.__optionShowGutter:
            contentRect = self.contentsRect()
            self.__gutterArea.setGeometry(QRect(contentRect.left(), contentRect.top(), self.gutterAreaWidth(), contentRect.height()))

    def gutterAreaPaintEvent(self, event):
        """Paint gutter content"""
        # initialise painter on WCELineNumberArea
        painter = QPainter(self.__gutterArea)
        painter.setRenderHint(QPainter.Antialiasing)

        # set background
        rect = event.rect()
        painter.fillRect(rect, self.__optionGutterText.background())

        painter.setPen(QPen(Qt.transparent))

        # Get the top and bottom y-coordinate of the first text block,
        # and adjust these values by the height of the current text block in each iteration in the loop
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()

        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        dx = self.__gutterArea.width()//2
        dy = self.fontMetrics().height()//2
        radius = (dy - 4)//2

        # Loop through all visible lines and paint the line numbers in the extra area for each line.
        # Note: in a plain text edit each line will consist of one QTextBlock
        #       if line wrapping is enabled, a line may span several rows in the text edit’s viewport
        while block.isValid() and top <= event.rect().bottom():
            # Check if the block is visible in addition to check if it is in the areas viewport
            #   a block can, for example, be hidden by a window placed over the text edit
            if block.isVisible() and bottom >= event.rect().top():
                colorLevel = WConsoleType.NORMAL

                blockData = block.userData()
                if blockData:
                    colorLevel = block.userData().type()

                if colorLevel != WConsoleType.NORMAL:
                    color = QColor(self.__typeColors[colorLevel])
                    center = QPointF(dx, top+dx)
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(center, radius, radius)

                    h = bottom - center.y() - dy
                    if h > dy:
                        painter.drawRoundedRect(QRectF(dx-2, center.y(), 4, h), 2, 2)

                    color.setAlpha(WConsole.__TYPE_COLOR_ALPHA)
                    painter.fillRect(QRectF(rect.left(), top, rect.width(), self.blockBoundingRect(block).height()), QBrush(color))

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def wheelEvent(self, event):
        """CTRL + wheel os used to zoom in/out font size"""
        if self.__optionWheelSetFontSize and event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta < 0:
                self.zoomOut()
            elif delta > 0:
                self.zoomIn()
        else:
            super(WConsole, self).wheelEvent(event)

    def paintEvent(self, event):
        """Customize painting for block types"""

        # initialise some metrics
        rect = event.rect()
        font = self.currentCharFormat().font()
        charWidth = QFontMetricsF(font).averageCharWidth()
        leftOffset = self.contentOffset().x() + self.document().documentMargin()

        # initialise painter to editor's viewport
        painter = QPainter(self.viewport())

        block = self.firstVisibleBlock()

        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            # Check if the block is visible in addition to check if it is in the areas viewport
            #   a block can, for example, be hidden by a window placed over the text edit
            if block.isVisible() and bottom >= event.rect().top():

                colorLevel = WConsoleType.NORMAL

                blockData = block.userData()
                if blockData:
                    colorLevel = block.userData().type()

                if colorLevel != WConsoleType.NORMAL:
                    color = QColor(self.__typeColors[colorLevel])
                    color.setAlpha(WConsole.__TYPE_COLOR_ALPHA)
                    painter.fillRect(QRectF(rect.left(), top, rect.width(), self.blockBoundingRect(block).height()), QBrush(color))

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

        super(WConsole, self).paintEvent(event)

    # endregion: event overload ------------------------------------------------

    def gutterAreaWidth(self):
        """Calculate width for gutter area

        Width is calculated according to gutter visibility
        """
        if self.__optionShowGutter:
            digits = 2
            # width = (witdh for digit '9') * (number of digits) + 3pixels
            return 3 + self.fontMetrics().width('9') * 2
        return 0

    def optionShowGutter(self):
        """Return if gutter is visible or not"""
        return self.__optionShowGutter

    def setOptionShowGutter(self, value):
        """Set if gutter is visible or not"""
        if isinstance(value, bool) and value != self.__optionShowGutter:
            self.__optionShowGutter = value
            if value:
                self.__gutterArea = WConsoleGutterArea(self)
            else:
                self.__gutterArea.disconnect()
                self.__gutterArea = None

            self.__updateGutterAreaWidth()
            self.update()

    def optionFontSize(self):
        """Return current console font size (in point)"""
        return self.font().pointSize()

    def setOptionFontSize(self, value):
        """Set current console font size (in point)"""
        font = self.font()
        font.setPointSize(value)
        self.setFont(font)

    def optionFontName(self):
        """Return current console font name"""
        return self.font().family()

    def setOptionFontName(self, value):
        """Set current console font name"""
        font = self.font()
        font.setFamily(value)
        self.setFont(font)

    def optionAllowWheelSetFontSize(self):
        """Return if CTRL+WHEEL allows to change font size"""
        return self.__optionWheelSetFontSize

    def setOptionAllowWheelSetFontSize(self, value):
        """Set if CTRL+WHEEL allows to change font size"""
        if isinstance(value, bool) and value != self.__optionWheelSetFontSize:
            self.__optionWheelSetFontSize = value

    def setHeight(self, numberOfRows=None):
        """Set height according to given number of rows"""

        if numberOfRows is None:
            self.setminimumHeight(0)
            self.setMaximumHeight(16777215)
        elif isinstance(numberOfRows, int) and numberOfRows > 0:
            doc = self.document()
            fontMetrics = QFontMetrics(doc.defaultFont())
            margins = self.contentsMargins()

            self.setFixedHeight(fontMetrics.lineSpacing() * numberOfRows + (doc.documentMargin() + self.frameWidth()) * 2 + margins.top() + margins.bottom())

    def optionBufferSize(self):
        """Return maximum buffer size for console"""
        return self.maximumBlockCount()

    def setOptionBufferSize(self, value):
        """Set maximum buffer size for console"""
        return self.setMaximumBlockCount(value)

    def optionFilteredExtraSelection(self):
        """Return list of filtered types"""
        return self.__optionFilterExtraSelection

    def setOptionFilteredExtraSelection(self, value):
        """Set filter on extra selection"""
        if isinstance(value, bool):
            self.__optionFilterExtraSelection = value
            self.__updateFilteredTypes()

    def optionFilteredTypes(self):
        """Return list of filtered types"""
        return self.__optionFilteredTypes

    def setOptionFilteredTypes(self, filteredTypes):
        """Set list of filtered types"""
        if isinstance(filteredTypes, list):
            self.__optionFilteredTypes = []
            self.setOptionAddFilteredTypes(filteredTypes)

    def setOptionAddFilteredTypes(self, filteredTypes):
        """Add filtered types

        Given `filteredTypes` can be a <WConsoleType> or a <list>
        """
        if isinstance(filteredTypes, WConsoleType):
            filteredTypes = [filteredTypes]

        if isinstance(filteredTypes, list):
            for filteredType in filteredTypes:
                if isinstance(filteredType, WConsoleType) and filteredType not in self.__optionFilteredTypes:
                    self.__optionFilteredTypes.append(filteredType)

            self.__updateFilteredTypes()

    def setOptionRemoveFilteredTypes(self, filteredTypes):
        """Remove filtered types

        Given `filteredTypes` can be a <WConsoleType> or a <list>
        """
        if isinstance(filteredTypes, WConsoleType):
            filteredTypes = [filteredTypes]

        if isinstance(filteredTypes, list):
            current = self.__optionFilteredTypes
            self.__optionFilteredTypes = []
            for filteredType in current:
                if filteredType not in filteredTypes:
                    self.__optionFilteredTypes.append(filteredType)

            self.__updateFilteredTypes()

    # ---

    def appendLine(self, text, type=WConsoleType.NORMAL, data=None, raw=False):
        """Append a new line to console

        Given `type` is a WConsoleType value
        """
        if raw:
            if isinstance(text, str):
                lines = [text]
            else:
                lines = ['\n'.join(text)]
        else:
            if isinstance(text, list):
                text = "\n".join(text)
            if text == '':
                lines = ['']
            else:
                lines = self.__formatText(text)

        filteredType = self.__isTypeFiltered(type)

        for line in lines:
            if raw:
                self.appendPlainText(line)
            else:
                self.appendHtml(line)

            lastBlock = self.document().lastBlock()
            if lastBlock:
                lastBlock.setUserData(WConsoleUserData(type, data))
                if filteredType:
                    lastBlock.setVisible(False)

    def append(self, text, raw=False):
        """Append to current line"""
        if isinstance(text, list):
            text = "\n".join(text)

        if raw:
            self.moveCursor(QTextCursor.End)
            self.textCursor().insertText(text)
        else:
            texts = self.__formatText(text)
            for text in texts:
                self.moveCursor(QTextCursor.End)
                self.textCursor().insertHtml(text)

    # ---

    def search(self):
        """Return search object"""
        return self.__search

    def updateFilter(self):
        """Update current applied filter"""
        self.__updateFilteredTypes()

    def scrollToLastRow(self):
        """Go to last row"""
        self.moveCursor(QTextCursor.End)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class WConsoleUserData(QTextBlockUserData):

    def __init__(self, type=None, data={}):
        QTextBlockUserData.__init__(self)
        self.__type = type
        self.__data = data

    def type(self):
        return self.__type

    def data(self, key=None):
        if key is None or not isinstance(self.__data, dict):
            return self.__data
        elif key in self.__data:
            return self.__data[key]
        else:
            return None


class WConsoleGutterArea(QWidget):
    """Gutter area for console

    # From example documentation
    We paint the line numbers on this widget, and place it over the WConsole's viewport() 's left margin area.

    We need to use protected functions in QPlainTextEdit while painting the area.
    So to keep things simple, we paint the area in the WConsole class.
    The area also asks the editor to calculate its size hint.

    Note that we could simply paint the gutter content directly on the code editor, and drop the WConsoleGutterArea class.
    However, the QWidget class helps us to scroll() its contents.
    Also, having a separate widget is the right choice if we wish to extend the console features.
    The widget would then help in the handling of mouse events.
    """

    def __init__(self, console):
        super(WConsoleGutterArea, self).__init__(console)
        self.__console = console

    def sizeHint(self):
        if self.__console:
            return QSize(self.__console.gutterAreaWidth(), 0)
        return QSize(0, 0)

    def paintEvent(self, event):
        """It Invokes the draw method(gutterAreaPaintEvent) in Console"""
        if self.__console:
            self.__console.gutterAreaPaintEvent(event)

    def disconnect(self):
        """Disconnect area from console"""
        self.__console = None

