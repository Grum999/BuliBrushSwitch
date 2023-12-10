# Buli Brush Switch

A plugin for [Krita](https://krita.org).


## What is Buli Brush Switch?
*Buli Brush Switch* is a Python plugin made for [Krita](https://krita.org) (free professional and open-source painting program).


This plugin allows to define shortcuts to activate brushes, but also provides some additional features.


## Screenshots

*Settings brushes list*

![Main interface](./screenshots/settings-brush-list.jpeg)

*Setting a brush*

![Main interface](./screenshots/settings-brush.jpeg)

*Toolbar button + popup brushes (list mode)*

![Main interface](./screenshots/ui-list.jpeg)


## Functionalities

Main functionality for this plugin is to let possibility for user to quickly switch to preset brush through shortcuts.

Plugin allows:
- To manage and organize an infinite number of brushes
- To access to brushes from popup list and/or through defined shortcuts
- To define properties (size, opacity, ...) and ccomments per brush
- To manage different setups

Shortcuts for brushes can be managed directly from plugin or from default Krita's user interface for shorcuts.

> Read [short documentation](./DOC.md) for more detailed informations

## Download, Install & Execute

### Download
+ **[ZIP ARCHIVE - v1.1.0](https://github.com/Grum999/BuliBrushSwitch/releases/download/1.1.0/bulibrushswitch.zip)**
+ **[SOURCE](https://github.com/Grum999/BuliBrushSwitch)**


### Installation

Plugin installation in [Krita](https://krita.org) is not intuitive and needs some manipulation:

1. Open [Krita](https://krita.org) and go to **Tools** -> **Scripts** -> **Import Python Plugins...** and select the **bulibrushswitch.zip** archive and let the software handle it.
2. Restart [Krita](https://krita.org)
3. To enable *Buli Brush Switch* go to **Settings** -> **Configure Krita...** -> **Python Plugin Manager** and click the checkbox to the left of the field that says **Buli Brush Switch**.
4. Restart [Krita](https://krita.org)


### Execute

Once installed, you should have a new button in toolbar, near the Krita's *Choose brush preset* button:
![Main interface](./screenshots/ui-toolbar.jpeg)


### Tested platforms

Plugin requires at least Krita 5.2.2
Has been tested:
- Linux AppImage
- Windows 10

---


## Plugin's life

### What's new?
_[2023-12-10] Version 1.1.0_ *[Show detailed release content](./releases-notes/RELEASE-1.1.0.md)*
- Implement - Brush Settings - *Brush rotation*

_[2023-12-09] Version 1.0.2_ *[Show detailed release content](./releases-notes/RELEASE-1.0.2.md)*
- Fix bug - Regression on brush editor

_[2023-12-08] Version 1.0.1_ *[Show detailed release content](./releases-notes/RELEASE-1.0.1.md)*
- Fix bug - Windows compatibility

_[2023-08-12] Version 1.0.0_ *[Show detailed release content](./releases-notes/RELEASE-1.0.0.md)*
- Implement - Krita Interface - *Improve toolbar button*
- Implement - Main Interface - *Icon view*
- Implement - Main Settings - *Redesign*
- Implement - Main Settings - *Brushes - Improve layout for brushes informations*
- Implement - Main Settings - *Brushes - Organize brushes within groups*
- Implement - Main Settings - *Brushes - Re-organize brushes & and groups with Drag'n'Drop*
- Implement - Main Settings - *Brushes - Let user choose scratchpad background color*
- Implement - Main Settings - *Setups manager*
- Implement - Brush Settings - *Color button when **No color***
- Implement - Brush Settings - *Take in account the preserve Alpha option*
- Implement - Brush Settings - *Gradient color*
- Implement - Brush Settings - *Ignore tool opacity*
- Fix bug - Brush Settings - *Keep user modifications*
- Fix bug - Brush Settings - *Ignore eraser mode option*
- Fix bug - Main Interface - *Crash when brushes from disabled bundles are referenced*
- Fix bug - Main Interface - *Lag/Freeze when changing brush*

_[2023-05-09] Version 0.2.2b_ *[Show detailed release content](./releases-notes/RELEASE-0.2.2b.md)*
- Fix bug *Krita 5.2.0 Compatibility*

_[2021-12-11] Version 0.2.1b_ *[Show detailed release content](./releases-notes/RELEASE-0.2.1b.md)*
- Fix bug *Invalid plugin initialisation*

_[2021-12-11] Version 0.2.0b_ *[Show detailed release content](./releases-notes/RELEASE-0.2.0b.md)*
- Improve *Popup brushes list*
- Implement *Default behaviour option for brushes with specific values*
- Implement *Modification of brush properties from brush settings*
- Implement *Specific paint tool for brush*
- Implement *Specific background color for brush*
- Fix bug *Selecting brush from Popup brushes list*
- Fix bug *Error on Krita's exit*
- Fix bug *Shortcut lost on tool selection*
- Fix bug *Non modal settings window*
- Fix bug *Krita's brush properties lost*
- Fix bug *Invalid selected brush*
- Fix bug *Difference according to method used to exit selected plugin brush*
- Fix bug *Missing icon on Brushes list settings*


_[2021-12-02] Version 0.1.1b_ *[Show detailed release content](./releases-notes/RELEASE-0.1.1b.md)*
- Add missing `.action` file on installation
- Fix invalid default brush definition from settings when no configuration files exists
- On Windows, fix main Brushes list window staying over Brush setting window

_[2021-12-01] Version 0.1.0b_ *[Show detailed release content](./releases-notes/RELEASE-0.1.0b.md)*
- First implemented/released version!



### Bugs

There's a known bug on shortcut widget, all keystrokes are not recognized (at least on my Debian)
> If you can't define a shortcut from plugin's interface, then do it from Krita's shortcuts interface

The plugin use Krita's API `Krita.instance().resources()`: on my DEV computer, with ~1000 presets, first call to this API function need ~4.0s for execution
- With plugin installed, Krita's startup will need a little bit more time than usual
- Should be faster with less presets
> A [bug](https://bugs.kde.org/show_bug.cgi?id=473311) has been opened on Krita side for this case, not sure if it can be fixed or not...

**Question? Bugs? Feature request?**
> Please use the dedicated [Issues](https://github.com/Grum999/BuliBrushSwitch/issues) page




### What’s next?

Who knows? 😅


## License

### *Buli Brush Switch* is released under the GNU General Public License (version 3 or any later version).

*Buli Brush Switch* is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

*Buli Brush Switch* is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should receive a copy of the GNU General Public License along with *Buli Brush Switch*. If not, see <https://www.gnu.org/licenses/>.


Long story short: you're free to download, modify as well as redistribute *Buli Brush Switch* as long as this ability is preserved and you give contributors proper credit. This is the same license under which Krita is released, ensuring compatibility between the two.
