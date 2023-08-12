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

from .bulibrushswitch import BuliBrushSwitch

# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = BuliBrushSwitch(parent=app)
app.addExtension(extension)
