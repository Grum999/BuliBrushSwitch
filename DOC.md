> ***(Short) Documentation***

# Toolbar button

Button is splitted in 2 parts:

| Button | Description |
| --- | --- |
| *Icon button* | Direct access to activate the brush  |
| *Popup list button* | Show popup brushes list |

![Toolbar button](./screenshots/ui-toolbar-button.png)

# Popup brushes list

The popup brushes list is displayed when:
- Popup list button is clicked
- Shortcut "Show popup brushes list" is defined and used (can be useful in particular in "full canvas mode")

![Popup brushes list](./screenshots/ui-popup-brushes-list.png)


# Settings

Plugin allows to define from 1 to *N* brushes in a dedicated list, there's no limits to number of brushes in list.

![Settings - brushes list](./screenshots/ui-settings-brushes-list.png)

 Settings: Button selection mode

The option for *Button selection mode* in brush list settings window allows to define how the icon button is used.


| Checked option | Description |
| --- | --- |
| *First from list* | - The icon in toolbar will always be the first brush defined in list, whatever the last brush from list that has been selected<br/>- Clicking on icon button will then always activate the first brush in list |
| *Last selected* | - The icon in toolbar will always be the one from last selected brush in list<br/>- Clicking on icon button will then re-activate the last brush that has been selected in list |


 Settings: Behaviour for brushes with specific values

The option for *Behaviour for brushes with specific values* in brush list settings window allows to define default behaviour when paint tool/color is modified when using a brush with specific paint tool/color.


| Checked option | Description |
| --- | --- |
| *Ignore modified state* | For brushes with specific paint tool and/or color, exiting plugin’s brush will always restore initial paint tool and/or color |
| *Keep modified state* | For brushes with specific paint tool and/or color, exiting plugin’s brush will:<br/>- If paint tool and/or color has been modified, keep last selected paint tool and/or color<br/>- If paint tool and/or color has NOT been modified, restore initial paint tool and/or color |


 Settings: Brushes list

Brushes in list can be:
- Added
- Edited
- Removed
- Re-ordered

A scratchpad allows to tests brushes directly from brushes list settings window.


 Settings: Brush options

When created or updated,

Each brush can be configured with some options:

| Option | Description |
| --- | --- |
| *Blending mode*<br/>*Size*<br/>*Opacity*<br/>*Flow* | Allows to tune specific values for brush, different than default one |
| *Use specific paint tool* | When checked, paint tool selected in list is activated automatically when brush is selected |
| *Keep user modification* | When checked, modified brush properties are kept for next time:<br/>- Blending mode<br/>- Size<br/>- Opacity<br/>- Flow<br/>- Paint tool *(only if option "Use specific paint tool is checked")*<br/>- Color *(only if option "Use specific color is checked")*<br/>When unchecked, modifications made to properties are not kept in brush configuration |
| *Ignore eraser mode*<sup>*</sup> | When checked, Krita's *eraser mode* is deactivated for brush, you have to explicitly switch to an eraser |
| *Use specific color*<sup>*</sup> | When checked, defined color is automatically applied when brush is activated<br/>- Foreground color is mandatory<br/>- Background color is optional |
| *Shortcut* | Shortcut to activate/deactivate a brush can be defined from here (or from Krita's usual shortcuts settings window) |
| *Comments* | Free rich text comment can be added on a brush<br>First comment line is used to identify easily brushes in Krita's usual shortcuts settings window |

> <sup>*</sup>*Options not available for eraser brushes*


# Brush selection

Selecting a brush from plugin will "change" the default Krita's behavior about brushes.

| Case | Description |
| --- | --- |
| *A brush is selected from plugin list* | - Plugin take management of brushes (brush properties from plugin overrides Krita's brush rules)<br/>- Brush properties are reset with the one defined in plugin |
| *A brush is unselected from plugin list* | - Plugin leave management of brush (Krita's normal behaviour for brushes is applied)<br/> - Brush & properties that were defined before plugin took management are restored to their values |

> **Note:**
> When plugin takes management of brush, toolbar button is highlighted:
> ![The button in toolbar](./screenshots/ui-toolbar3-selected.jpeg)

To **select** a brush from plugin list, different possibilities:
- Open popup brush list, and click on desired brush to activate it
- If a shortcut has been defined for desired brush, use shortcut to activate it

To **unselect** a brush from plugin list:
- Open popup brush list, click on *the current active brush in list*
- If a shortcut has been defined for *the current active brush in list*, use shortcut to deactivate it
- If a shortcut has been defined for "*Deactivate current brush*" action, use shortcut to deactivate current brush (whatever the current brush is)
- Select any brush from Krita's brush preset selector


---
