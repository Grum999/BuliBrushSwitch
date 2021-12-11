# Buli Brush Switch :: Release 0.2.1b [2021-12-11]

# Fixed bugs

## Error due to *Invalid plugin initialisation*

First plugin execution was generating a script error message due to missing shortcut configuration.

Fixed: Set a default empty shortcut configuration + ensure configuration exists at startup before trying to use it
