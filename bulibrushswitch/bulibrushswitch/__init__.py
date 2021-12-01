from .bulibrushswitch import BuliBrushSwitch

# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = BuliBrushSwitch(parent=app)
app.addExtension(extension)
