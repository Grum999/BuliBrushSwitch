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

*Toolbar button + popup brushes list*

![Main interface](./screenshots/ui-list.jpeg)


## Functionalities

Main functionality for this plugin is to let possibility for user to quickly switch to preset brush through shortcuts.

Plugin allows:
- To manage and organize an infinite number of brushes
- To access to brushes from popup list and/or through defined shortcuts
- To define properties (size, opacity, ...) per brush
- To put comment on brushes
- To manage different setups

Shortcuts for brushes can be managed directly from plugin or from default Krita's user interface for shorcuts; in this case, actions are named taking in account brushes name & comments.

> Read [short documentation](./DOC.md) for more detailed informations

## Download, Install & Execute

### Download
+ **[ZIP ARCHIVE - v0.2.2b](https://github.com/Grum999/BuliBrushSwitch/releases/download/0.2.2b/bulibrushswitch.zip)**
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

Plugin requires at least Krita 5.2.0-alpha (Linux appimage)

---


## Plugin's life

### What's new?

_[2022-xx-xx] Version 1.0.0_ *[Show detailed release content](./releases-notes/RELEASE-1.0.0.md)*
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

Known bug on shortcut widget, all keystrokes are not recognized (at least on my Debian)
And probably some other I didn't saw.

Please consider the plugin is still in beta version!

### What’s next?

Some ideas to implement:
- Replace option "Ignore eraser mode" at brush level to let the possibility to define a specific brush to use for "eraser mode"
- Some cosmetics improvements (brush list, toolbar button)


## License

### *Buli Brush Switch* is released under the GNU General Public License (version 3 or any later version).

*Buli Brush Switch* is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

*Buli Brush Switch* is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should receive a copy of the GNU General Public License along with *Buli Brush Switch*. If not, see <https://www.gnu.org/licenses/>.


Long story short: you're free to download, modify as well as redistribute *Buli Brush Switch* as long as this ability is preserved and you give contributors proper credit. This is the same license under which Krita is released, ensuring compatibility between the two.
