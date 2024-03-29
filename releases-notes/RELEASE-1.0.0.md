# Buli Brush Switch :: Release 1.0.0 [2023-08-12]

# Krita Interface

## Improve toolbar button
[Feature request #5](https://github.com/Grum999/BuliBrushSwitch/issues/5)

Review button in Krita toolbar to let it being rendered exactly like the *Brush Preset Chooser* button is.

![Krita toolbar buttons](./../screenshots/r1-0-0_kritatoolbar-button-render.png)
- Left button: Krita *Brush Preset Chooser*
- Right button: Buli Brush Switch button

*(Top: Linux / Bottom: Windows)*


# Main Interface

## List & Icon views
List and icon views from main popup interface have been reviewed to take in account groups management

### List view
Basic improvement: as groups are now available, double-click to expand/collapse them

![List view mode](./../screenshots/r1-0-0_mainui-list_viewmode.png)

### Icon view
The icon view provide 2 views:
- Flat view: all brushes in single view
- User view: groups tree on left, brushes from selected group on right

![Icon view mode](./../screenshots/r1-0-0_mainui-icon_viewmode.png)


# Main settings

## Redesign
With new Setups manager, user interface has been redesigned in pages:
- General settings
- Brushes
- Setups manager

![Main settings redesign](./../screenshots/r1-0-0_mainui-redesign.png)


## Brushes - Improve layout for brushes informations
[Feature request #15](https://github.com/Grum999/BuliBrushSwitch/issues/15)

Layout and informations provided are now more readable:
- Only display active options
- Reduce text and use icons

![New brushes information layout](./../screenshots/r1-0-0_mainsettings-new_brushnfo_layout.png)

## Brushes - Organize brushes within groups
[Feature request #9](https://github.com/Grum999/BuliBrushSwitch/issues/9)

Brushes can now be organized withins groups.

Group editor provides:
- Group color
- Shorcuts to activate previous/next brush in group
- Rich text editor to write an optional description

![Group editor](./../screenshots/r1-0-0_mainsettings-groups_editor.png)

## Brushes - Re-organize brushes & and groups with Drag'n'Drop
[Feature request #3](https://github.com/Grum999/BuliBrushSwitch/issues/3)

Brushes and groups can be re-organized with Drag'n'Drop

![Drag'n'Drop](./../screenshots/r1-0-0_mainsettings-dnd.png)


## Brushes - Let user choose scratchpad background color
[Feature request #4](https://github.com/Grum999/BuliBrushSwitch/issues/4)

An additional color button menu has been added to define background color for scratchpad
There's now:
- One button to choose brush color in scratchpad
- One button to choose background color for scratchpad

![scratchpad with background color](./../screenshots/r1-0-0_mainsettings-scratchpad_bg_color.png)


## Setups manager
[Feature request #16](https://github.com/Grum999/BuliBrushSwitch/issues/16)

The Setups manager allows to create and organize differents *BuliBrushSwitch* configuration.

Instead of having a unique big configuration with a lot of brushes, it's possible create different configuration for different use cases.

Also, configurations in Setups manager can be exported/imported:
- Useful for backup
- Easily allows to copy setups from a computer to another one

*Setups manager*

![Setup manager - main window](./../screenshots/r1-0-0_mainsettings-sm-main_window.png)

*Properties for a setup - Main properties*

![Setup manager - setup properties](./../screenshots/r1-0-0_mainsettings-sm-setup_properties-prop.png)

*Properties for a setup - Preview of saved brushes configuration*

![Setup manager - setup properties-preview](./../screenshots/r1-0-0_mainsettings-sm-setup_properties-preview.png)


# Brushes settings

## Redesign
With new options, user interface has been redesigned to be less messy.

## Color button when *No color*
[Feature request #6](https://github.com/Grum999/BuliBrushSwitch/issues/6)

Represent the **No color** choice for background color with hatched pattern

![Color button - hatched when no color set](./../screenshots/r1-0-0_mainsettings-bg_color_button.png)


## Additional brushes options

### Gradient color
[Feature request #8](https://github.com/Grum999/BuliBrushSwitch/issues/8)

Some brushes can use a gradient as source color.
A new button -like for foreround/background- is added to let possibility to define a specific gradient with a brush.

Button popups a list of available gradient in Krita.

![Gradient button with gradient list](./../screenshots/r1-0-0_mainsettings-gradient_color_button.png)


### Take in account the preserve Alpha option
[Feature request #7](https://github.com/Grum999/BuliBrushSwitch/issues/7)

Allows brush to force use of *preserve Alpha* option

![Preserve alpha option](./../screenshots/r1-0-0_mainsettings-preservealpha.png)

### Ignore tool opacity
[Feature request #14](https://github.com/Grum999/BuliBrushSwitch/issues/14)

Krita memorize opacity per tool (brush tool, line tool, rectangle tool, ...) rather than per brush.
This means, when changing a tool, current defined opacity can be modified by new selected tool.

This option allows to ignore tool opacity and force use of defined brush opacity whatever the tool is.
![Ignore tool opacity option](./../screenshots/r1-0-0_mainsettings-ignoretoolopacity.png)


# Fix bugs

## Brush Settings - *Ignore eraser mode option*
[Bug #10](https://github.com/Grum999/BuliBrushSwitch/issues/10)

Option *Ignore eraser mode* was not taken in account (always checked)

Now problem is fixed.

## Brush Settings - **Keep user modifications*
[Bug #11](https://github.com/Grum999/BuliBrushSwitch/issues/11)

Option *Keep user modifications* was not taken properly in account when brush was deactivated

Now problem is fixed.


## Main Interface - *Crash when brushes from disabled bundles are referenced*
[Bug #1](https://github.com/Grum999/BuliBrushSwitch/issues/1)

When a brush is linked to a deactivated bundle, brush thumbnail can't be returned and then generate python exception

To avoid this, now display a warning icon:
![Popup brushes list](./../screenshots/r1-0-0_mainui-missing_brush.png)


## Main Interface - *Lag/Freeze when changing brush*
[Bug #2](https://github.com/Grum999/BuliBrushSwitch/issues/2)

There was a lag (from ~0.28s to ~1.00s) when changing brush from Buli brush switch
Switch time was different according to tool.

Now problem is fixed (~0.01s to switch)
