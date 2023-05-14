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

# -----------------------------------------------------------------------------
# The bbssettings module provides classes used to manage plugin settings
# --> this module is a core module for plugin
#
# Main classes from this module
#
# - BBSSettings:
#       Allows to easily manage settings
#       (read, write, default values, allowed values, ...)
#
# -----------------------------------------------------------------------------


from enum import Enum

import PyQt5.uic
from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal,
        QSettings,
        QStandardPaths
    )

import os.path
import json
import os
import re
import sys
import shutil

from krita import (
                Resource,
                Krita
            )

from bulibrushswitch.pktk.modules.strutils import stripHtml
from bulibrushswitch.pktk.modules.utils import (
        checkKritaVersion,
        Debug
    )
from bulibrushswitch.pktk.modules.settings import (
        Settings,
        SettingsFmt,
        SettingsKey,
        SettingsRule
    )
from bulibrushswitch.pktk.modules.ekrita import EKritaBrushPreset

from bulibrushswitch.pktk.widgets.wcolorselector import WColorPicker

from bulibrushswitch.pktk.pktk import (
        EInvalidType,
        EInvalidValue
    )

# -----------------------------------------------------------------------------


class BBSSettingsValues(object):
    DEFAULT_SELECTIONMODE_FIRST_FROM_LIST = 'firstFromList'
    DEFAULT_SELECTIONMODE_LAST_SELECTED = 'lastSelected'

    DEFAULT_MODIFICATIONMODE_IGNORE = 'ignoreModification'
    DEFAULT_MODIFICATIONMODE_KEEP = 'keepModification'

    POPUP_BRUSHES_VIEWMODE_LIST = 0
    POPUP_BRUSHES_VIEWMODE_ICON = 1


class BBSSettingsKey(SettingsKey):
    CONFIG_EDITOR_WINDOW_POSITION_X =                                           'config.editor.window.position.x'
    CONFIG_EDITOR_WINDOW_POSITION_Y =                                           'config.editor.window.position.y'
    CONFIG_EDITOR_WINDOW_SIZE_WIDTH =                                           'config.editor.window.size.width'
    CONFIG_EDITOR_WINDOW_SIZE_HEIGHT =                                          'config.editor.window.size.height'

    CONFIG_EDITOR_BRUSHES_ZOOMLEVEL =                                           'config.editor.brushes.list.zoomLevel'
    CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION =                                   'config.editor.brushes.list.splitterPosition'

    CONFIG_EDITOR_TEXT_COLORPICKER_COMPACT =                                    'config.editor.text.colorPicker.compact'
    CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_VISIBLE =                            'config.editor.text.colorPicker.palette.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_DEFAULT =                            'config.editor.text.colorPicker.palette.default'
    CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_VISIBLE =                             'config.editor.text.colorPicker.colorWheel.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_CPREVIEW =                            'config.editor.text.colorPicker.colorWheel.colorPreview'
    CONFIG_EDITOR_TEXT_COLORPICKER_CCOMBINATION =                               'config.editor.text.colorPicker.colorCombination'
    CONFIG_EDITOR_TEXT_COLORPICKER_CCSS =                                       'config.editor.text.colorPicker.colorCss.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_VISIBLE =                        'config.editor.text.colorPicker.colorSlider.rgb.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_ASPCT =                          'config.editor.text.colorPicker.colorSlider.rgb.asPct'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_VISIBLE =                       'config.editor.text.colorPicker.colorSlider.cmyk.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_ASPCT =                         'config.editor.text.colorPicker.colorSlider.cmyk.asPct'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_VISIBLE =                        'config.editor.text.colorPicker.colorSlider.hsl.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_ASPCT =                          'config.editor.text.colorPicker.colorSlider.hsl.asPct'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_VISIBLE =                        'config.editor.text.colorPicker.colorSlider.hsv.visible'
    CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_ASPCT =                          'config.editor.text.colorPicker.colorSlider.hsv.asPct'

    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT =                           'config.editor.scratchpad.colorPicker.compact'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE =                   'config.editor.scratchpad.colorPicker.palette.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT =                   'config.editor.scratchpad.colorPicker.palette.default'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE =                    'config.editor.scratchpad.colorPicker.colorWheel.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW =                   'config.editor.scratchpad.colorPicker.colorWheel.colorPreview'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION =                      'config.editor.scratchpad.colorPicker.colorCombination'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS =                              'config.editor.scratchpad.colorPicker.colorCss.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE =               'config.editor.scratchpad.colorPicker.colorSlider.rgb.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT =                 'config.editor.scratchpad.colorPicker.colorSlider.rgb.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE =              'config.editor.scratchpad.colorPicker.colorSlider.cmyk.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT =                'config.editor.scratchpad.colorPicker.colorSlider.cmyk.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE =               'config.editor.scratchpad.colorPicker.colorSlider.hsl.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT =                 'config.editor.scratchpad.colorPicker.colorSlider.hsl.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE =               'config.editor.scratchpad.colorPicker.colorSlider.hsv.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT =                 'config.editor.scratchpad.colorPicker.colorSlider.hsv.asPct'

    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT =                           'config.editor.scratchpad.colorPickerBg.compact'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE =                   'config.editor.scratchpad.colorPickerBg.palette.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT =                   'config.editor.scratchpad.colorPickerBg.palette.default'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE =                    'config.editor.scratchpad.colorPickerBg.colorWheel.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW =                   'config.editor.scratchpad.colorPickerBg.colorWheel.colorPreview'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION =                      'config.editor.scratchpad.colorPickerBg.colorCombination'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS =                              'config.editor.scratchpad.colorPickerBg.colorCss.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE =               'config.editor.scratchpad.colorPickerBg.colorSlider.rgb.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT =                 'config.editor.scratchpad.colorPickerBg.colorSlider.rgb.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE =              'config.editor.scratchpad.colorPickerBg.colorSlider.cmyk.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT =                'config.editor.scratchpad.colorPickerBg.colorSlider.cmyk.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE =               'config.editor.scratchpad.colorPickerBg.colorSlider.hsl.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT =                 'config.editor.scratchpad.colorPickerBg.colorSlider.hsl.asPct'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE =               'config.editor.scratchpad.colorPickerBg.colorSlider.hsv.visible'
    CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT =                 'config.editor.scratchpad.colorPickerBg.colorSlider.hsv.asPct'

    CONFIG_EDITOR_SCRATCHPAD_COLOR_BG =                                         'config.editor.scratchpad.colorBg'

    CONFIG_UI_POPUP_WIDTH =                                                     'config.ui.popup.width'
    CONFIG_UI_POPUP_HEIGHT =                                                    'config.ui.popup.height'
    CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL =                                         'config.ui.popup.brushes.list.zoomLevel'
    CONFIG_UI_POPUP_BRUSHES_VIEWMODE =                                          'config.ui.popup.brushes.list.viewMode'

    CONFIG_BRUSHES_LIST_COUNT =                                                 'config.brushes.list.count'
    CONFIG_BRUSHES_LIST_BRUSHES =                                               'config.brushes.list.brushes'

    CONFIG_BRUSHES_DEFAULT_SELECTIONMODE =                                      'config.brushes.default.selectionMode'
    CONFIG_BRUSHES_LAST_SELECTED =                                              'config.brushes.default.lastSelected'
    CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE =                                   'config.brushes.default.modificationMode'


class BBSSettings(Settings):
    """Manage BuliBrushSwitch settings (keep in memory last preferences used brush quick access)

    Configuration is saved as JSON file
    """
    __fullSave = True

    DEFAULT_ACTIONS = [
            'bulibrushswitch_settings',
            'bulibrushswitch_activate_default',
            'bulibrushswitch_deactivate',
            'bulibrushswitch_show_brushes_list'
        ]

    @classmethod
    def save(cls, fullSave=True):
        """save configuration"""
        cls.__fullSave = fullSave
        return super().save()

    def __init__(self, pluginId=None):
        """Initialise settings"""
        if pluginId is None or pluginId == '':
            pluginId = 'bulibrushswitch'

        rules = [
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_COMPACT,                         True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_VISIBLE,                 True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_DEFAULT,                 "Default",     SettingsFmt(str)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_VISIBLE,                  False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_CPREVIEW,                 True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCOMBINATION,                    0,             SettingsFmt(int, [0, 1, 2, 3, 4, 5])),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCSS,                            False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_VISIBLE,             False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_ASPCT,               False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_VISIBLE,            False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_ASPCT,              False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_VISIBLE,             False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_ASPCT,               False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_VISIBLE,             False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_ASPCT,               False,         SettingsFmt(bool)),

            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT,                False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE,        False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT,        "Default",     SettingsFmt(str)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE,         True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW,        True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION,           0,             SettingsFmt(int, [0, 1, 2, 3, 4, 5])),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS,                   False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE,    False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT,      False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE,   False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT,     False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE,    True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT,      False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE,    False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT,      False,         SettingsFmt(bool)),

            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT,                False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE,        False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT,        "Default",     SettingsFmt(str)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE,         True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW,        True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION,           0,             SettingsFmt(int, [0, 1, 2, 3, 4, 5])),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS,                   False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE,    False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT,      False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE,   False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT,     False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE,    True,          SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT,      False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE,    False,         SettingsFmt(bool)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT,      False,         SettingsFmt(bool)),

            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLOR_BG,                              '#ffffff',     SettingsFmt(str)),

            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_ZOOMLEVEL,                                3,             SettingsFmt(int, [0, 1, 2, 3, 4])),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_BRUSHES_SPLITTER_POSITION,                        [1000, 500],   SettingsFmt(int), SettingsFmt(int)),

            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_X,                                -1,            SettingsFmt(int)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_WINDOW_POSITION_Y,                                -1,            SettingsFmt(int)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_WIDTH,                                -1,            SettingsFmt(int)),
            SettingsRule(BBSSettingsKey.CONFIG_EDITOR_WINDOW_SIZE_HEIGHT,                               -1,            SettingsFmt(int)),

            SettingsRule(BBSSettingsKey.CONFIG_UI_POPUP_WIDTH,                                          -1,            SettingsFmt(int)),
            SettingsRule(BBSSettingsKey.CONFIG_UI_POPUP_HEIGHT,                                         -1,            SettingsFmt(int)),
            SettingsRule(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_ZOOMLEVEL,                              3,             SettingsFmt(int, [0, 1, 2, 3, 4])),
            SettingsRule(BBSSettingsKey.CONFIG_UI_POPUP_BRUSHES_VIEWMODE,                               BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST,
                                                                                                                       SettingsFmt(int,
                                                                                                                                   [BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_LIST,
                                                                                                                                    BBSSettingsValues.POPUP_BRUSHES_VIEWMODE_ICON])),

            SettingsRule(BBSSettingsKey.CONFIG_BRUSHES_LIST_COUNT,                                      0,             SettingsFmt(int, (0, None))),
            SettingsRule(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES,                                    [],            SettingsFmt(list)),

            SettingsRule(BBSSettingsKey.CONFIG_BRUSHES_LAST_SELECTED,                                   '',            SettingsFmt(str)),
            SettingsRule(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_SELECTIONMODE,                           BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST,
                                                                                                                       SettingsFmt(
                                                                                                                           str,
                                                                                                                           [BBSSettingsValues.DEFAULT_SELECTIONMODE_FIRST_FROM_LIST,
                                                                                                                            BBSSettingsValues.DEFAULT_SELECTIONMODE_LAST_SELECTED])),
            SettingsRule(BBSSettingsKey.CONFIG_BRUSHES_DEFAULT_MODIFICATIONMODE,                        BBSSettingsValues.DEFAULT_MODIFICATIONMODE_IGNORE,
                                                                                                                       SettingsFmt(
                                                                                                                            str,
                                                                                                                            [BBSSettingsValues.DEFAULT_MODIFICATIONMODE_IGNORE,
                                                                                                                             BBSSettingsValues.DEFAULT_MODIFICATIONMODE_KEEP])),
        ]

        super(BBSSettings, self).__init__(pluginId, rules)

    def configurationLoadedEvent(self, fileLoaded):
        """Configuration has been loaded

        Do additional checks
        """
        def getFirstValidBrush():
            # if we're looking for an eraser, try to get the most basic one
            #   "a) Eraser Circle"
            #   "a) Eraser Small"
            #   "a) Eraser Soft"
            defaultEraserList = ["a) Eraser Circle", "a) Eraser Small", "a) Eraser Soft"]
            for eraserName in defaultEraserList:
                preset = EKritaBrushPreset.getPreset(eraserName)
                if preset and preset.name() == eraserName:
                    return preset

            # just return the first available brush
            return EKritaBrushPreset.getPreset()

        # need to check brushes
        # - At least we need one brush
        #       If none found, add a default one
        # - Check if at least brushes are valid
        #       If no valid brush found, add a default one
        #
        # Except when plugin is executed for first time, it shouldn't occurs...
        brushes = self.option(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES)
        if len(brushes) == 0:
            # note: we normaly here have a dictionary, not a BBSBrush
            brushName = getFirstValidBrush()

            # build default configurations
            if brushName.name() == 'a) Eraser Circle':
                brushDict = {
                        "blendingMode": "erase",
                        "color": "",
                        "colorBg": "",
                        "comments": "",
                        "flow": 1.0,
                        "ignoreEraserMode": True,
                        "keepUserModifications": True,
                        "name": "a) Eraser Circle",
                        "opacity": 1.0,
                        "position": 0,
                        "size": 50.0,
                        "eraserMode": True,
                        "defaultPaintTool": None,
                        "shortcut": '',
                        "uuid": '1367df61-b0e2-4304-9b51-ff04c102659e'
                    }
            elif brushName.name() == 'a) Eraser Small':
                brushDict = {
                        "blendingMode": "erase",
                        "color": "",
                        "colorBg": "",
                        "comments": "",
                        "flow": 1.0,
                        "ignoreEraserMode": True,
                        "keepUserModifications": True,
                        "name": "a) Eraser Small",
                        "opacity": 1.0,
                        "position": 0,
                        "size": 25.0,
                        "eraserMode": True,
                        "defaultPaintTool": None,
                        "shortcut": '',
                        "uuid": '1367df61-b0e2-4304-9b51-ff04c102659e'
                    }
            elif brushName.name() == 'a) Eraser Soft':
                brushDict = {
                        "blendingMode": "erase",
                        "color": "",
                        "colorBg": "",
                        "comments": "",
                        "flow": 1.0,
                        "ignoreEraserMode": True,
                        "keepUserModifications": True,
                        "name": "a) Eraser Soft",
                        "opacity": 1.0,
                        "position": 0,
                        "size": 60.0,
                        "eraserMode": True,
                        "defaultPaintTool": None,
                        "shortcut": '',
                        "uuid": '1367df61-b0e2-4304-9b51-ff04c102659e'
                    }
            else:
                # in this case, it's a little bit more difficult because we don't
                # really know brush properties (it could be possible to get brush
                # properties, but it needs some extra works:
                #  - get in memory current active brush
                #  - load brush
                #  - get brush properties
                #  - restore previous brush...
                # possible, but I think we're here in a really specific situation
                # (users for which default erasers brushes have been removed... X_X)
                #
                # just build "something"
                brushDict = {
                        "blendingMode": "normal",
                        "color": "#000000",
                        "colorBg": "",
                        "comments": "",
                        "flow": 1.0,
                        "ignoreEraserMode": True,
                        "keepUserModifications": True,
                        "name": brushName.name(),
                        "opacity": 1.0,
                        "position": 0,
                        "size": 60.0,
                        "eraserMode": False,
                        "defaultPaintTool": None,
                        "shortcut": '',
                        "uuid": '1367df61-b0e2-4304-9b51-ff04c102659e'
                    }

            brushes.append(brushDict)
            self.setOption(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES, brushes)

    def configurationSavedEvent(self, fileSaved):
        """When saving configuration, also save .action file for shortcuts"""
        if not BBSSettings.__fullSave:
            # no full save, no need to save actions
            return

        directory = Krita.instance().readSetting('', 'ResourceDirectory', QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        actionsDirectory = os.path.normpath(os.path.join(directory, "actions"))

        if not os.path.isdir(actionsDirectory):
            os.makedirs(actionsDirectory, exist_ok=True)

        try:
            with open(os.path.join(os.path.dirname(__file__), 'resources', 'bbs.action'), 'r') as fHandle:
                fileContent = fHandle.read()

        except Exception as e:
            print(e)
            return

        for actionId in BBSSettings.DEFAULT_ACTIONS:
            shortcut = ''
            action = Krita.instance().action(actionId)

            if action:
                shortcut = action.shortcut().toString()
                fileContent = fileContent.replace(f"{{shortcut_{actionId}}}", shortcut)

        actionsList = []

        fromMarker = "    <!--- (user brush definition:start) -->"
        toMarker = "    <!--- (user brush definition:end) -->"

        for brush in self.option(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES):
            actionId = f'bulibrushswitch_brush_{brush["uuid"].strip("{}")}'
            actionText = BBSSettings.brushActionText(brush['name'], brush['comments'])
            shortcut = ''
            if 'shortcut' in brush:
                shortcut = brush['shortcut']
            actionsList.append(f"""
    <Action name="{actionId}">
      <icon></icon>
      <text>{actionText}</text>
      <whatsThis></whatsThis>
      <toolTip></toolTip>
      <iconText></iconText>
      <activationFlags>0</activationFlags>
      <activationConditions>0</activationConditions>
      <shortcut>{shortcut}</shortcut>
      <isCheckable>false</isCheckable>
      <statusTip></statusTip>
    </Action>""")

        actionsList.append('')

        pStart = fileContent.index(fromMarker)
        pEnd = fileContent.index(toMarker)

        fileContent = fileContent[:pStart+len(fromMarker)]+"\n".join(actionsList)+fileContent[pEnd:]

        try:
            with open(os.path.join(actionsDirectory, 'bulibrushswitch.action'), 'w') as fHandle:
                fHandle.write(fileContent)
        except Exception as e:
            print(e)
            return

    @staticmethod
    def getTxtColorPickerLayout():
        """Convert text color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_COMPACT))
        tmpColorPicker.setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_VISIBLE))
        tmpColorPicker.setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_DEFAULT))
        tmpColorPicker.setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_VISIBLE))
        tmpColorPicker.setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_CPREVIEW))
        tmpColorPicker.setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCOMBINATION))
        tmpColorPicker.setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCSS))
        tmpColorPicker.setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_ASPCT))
        tmpColorPicker.setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_ASPCT))
        tmpColorPicker.setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_ASPCT))
        tmpColorPicker.setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_ASPCT))
        tmpColorPicker.setOptionShowColorAlpha(False)
        return tmpColorPicker.optionLayout()

    @staticmethod
    def setTxtColorPickerLayout(layout):
        """Convert text color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionLayout(layout)

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_COMPACT, tmpColorPicker.optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_VISIBLE, tmpColorPicker.optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_PALETTE_DEFAULT, tmpColorPicker.optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_VISIBLE, tmpColorPicker.optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CWHEEL_CPREVIEW, tmpColorPicker.optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCOMBINATION, tmpColorPicker.optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CCSS, tmpColorPicker.optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_VISIBLE, tmpColorPicker.optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_RGB_ASPCT, tmpColorPicker.optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_VISIBLE, tmpColorPicker.optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_CMYK_ASPCT, tmpColorPicker.optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_VISIBLE, tmpColorPicker.optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSL_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_VISIBLE, tmpColorPicker.optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_TEXT_COLORPICKER_CSLIDER_HSV_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSV())

    @staticmethod
    def getBrushColorPickerLayoutFg():
        """Convert brush color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT))
        tmpColorPicker.setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE))
        tmpColorPicker.setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT))
        tmpColorPicker.setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE))
        tmpColorPicker.setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW))
        tmpColorPicker.setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION))
        tmpColorPicker.setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS))
        tmpColorPicker.setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT))
        tmpColorPicker.setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT))
        tmpColorPicker.setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT))
        tmpColorPicker.setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT))
        tmpColorPicker.setOptionShowColorAlpha(False)
        return tmpColorPicker.optionLayout()

    @staticmethod
    def setBrushColorPickerLayoutFg(layout):
        """Convert brush color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionLayout(layout)

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_COMPACT, tmpColorPicker.optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_VISIBLE, tmpColorPicker.optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_PALETTE_DEFAULT, tmpColorPicker.optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_VISIBLE, tmpColorPicker.optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CWHEEL_CPREVIEW, tmpColorPicker.optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCOMBINATION, tmpColorPicker.optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CCSS, tmpColorPicker.optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_VISIBLE, tmpColorPicker.optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_RGB_ASPCT, tmpColorPicker.optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_VISIBLE, tmpColorPicker.optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_CMYK_ASPCT, tmpColorPicker.optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_VISIBLE, tmpColorPicker.optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSL_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_VISIBLE, tmpColorPicker.optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_FG_CSLIDER_HSV_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSV())

    @staticmethod
    def getBrushColorPickerLayoutBg():
        """Convert background color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionCompactUi(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT))
        tmpColorPicker.setOptionShowColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE))
        tmpColorPicker.setOptionColorPalette(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT))
        tmpColorPicker.setOptionShowColorWheel(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE))
        tmpColorPicker.setOptionShowPreviewColor(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW))
        tmpColorPicker.setOptionShowColorCombination(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION))
        tmpColorPicker.setOptionShowCssRgb(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS))
        tmpColorPicker.setOptionShowColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorRGB(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT))
        tmpColorPicker.setOptionShowColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorCMYK(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT))
        tmpColorPicker.setOptionShowColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSV(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT))
        tmpColorPicker.setOptionShowColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE))
        tmpColorPicker.setOptionDisplayAsPctColorHSL(BBSSettings.get(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT))
        tmpColorPicker.setOptionShowColorAlpha(False)
        return tmpColorPicker.optionLayout()

    @staticmethod
    def setBrushColorPickerLayoutBg(layout):
        """Convert background color picker layout from settings to layout"""
        # build a dummy color picker
        tmpColorPicker = WColorPicker()
        tmpColorPicker.setOptionLayout(layout)

        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_COMPACT, tmpColorPicker.optionCompactUi())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_VISIBLE, tmpColorPicker.optionShowColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_PALETTE_DEFAULT, tmpColorPicker.optionColorPalette())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_VISIBLE, tmpColorPicker.optionShowColorWheel())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CWHEEL_CPREVIEW, tmpColorPicker.optionShowPreviewColor())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCOMBINATION, tmpColorPicker.optionShowColorCombination())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CCSS, tmpColorPicker.optionShowColorCssRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_VISIBLE, tmpColorPicker.optionShowColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_RGB_ASPCT, tmpColorPicker.optionDisplayAsPctColorRGB())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_VISIBLE, tmpColorPicker.optionShowColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_CMYK_ASPCT, tmpColorPicker.optionDisplayAsPctColorCMYK())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_VISIBLE, tmpColorPicker.optionShowColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSL_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSL())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_VISIBLE, tmpColorPicker.optionShowColorHSV())
        BBSSettings.set(BBSSettingsKey.CONFIG_EDITOR_SCRATCHPAD_COLORPICKER_BG_CSLIDER_HSV_ASPCT, tmpColorPicker.optionDisplayAsPctColorHSV())

    @staticmethod
    def setBrushes(brushes):
        """A generic method to save brushes list definition

        Given `brushes` is a BBSBrushes
        """
        exportedBrushes = []
        for brushId in brushes.idList():
            brush = brushes.get(brushId)
            exportedBrushes.append(brush.exportData())
        BBSSettings.set(BBSSettingsKey.CONFIG_BRUSHES_LIST_BRUSHES, exportedBrushes)

    @staticmethod
    def brushAction(brushId, brushName='', brushComments='', create=False, window=None):
        """Return action brush properties

        If not found, create it
        """
        brushId = brushId.strip("{}")
        actionId = BBSSettings.brushActionId(brushId)
        action = Krita.instance().action(actionId)
        if action is None and create:
            if window is None:
                window = Krita.instance().activeWindow()
            if window:
                action = window.createAction(actionId, BBSSettings.brushActionText(brushName, brushComments), None)
                action.setData(brushId)

        return action

    @staticmethod
    def brushActionId(brushId):
        """Return actionid from a brush id"""
        return f'bulibrushswitch_brush_{brushId.strip("{}")}'

    @staticmethod
    def brushActionText(brushName, brushComment):
        """Return title for action for given brush name/comment"""
        title = f"{i18n('Activate brush:')} {brushName}"
        comments = stripHtml(brushComment).split('\n')
        if len(comments) == 1 and comments[0].strip() != '':
            title += ' - '+comments[0]
        elif len(comments) > 1:
            for comment in comments:
                if comment.strip() != '':
                    title += ' - '+comment+'[...]'
                    break
        return title

    @staticmethod
    def setShortcut(brush, shortcut):
        """Create and/or update action for given `brush` with given `shortcut`

        Method placed in settingsz as managing shortcut is part of settings :)
        """
        window = Krita.instance().activeWindow()
        if window:
            action = BBSSettings.brushAction(brush.id(), brush.name(), brush.comments(), shortcut is not None)
            if action:
                if shortcut:
                    # assign shortcut
                    action.setShortcut(QKeySequence(shortcut))
                else:
                    # remove shortcut
                    action.setShortcut(QKeySequence())
