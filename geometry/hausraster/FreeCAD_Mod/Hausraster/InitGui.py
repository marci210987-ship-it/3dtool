class HausrasterWorkbench(Workbench):
    MenuText = "Hausraster"
    ToolTip = "Parametrisches Ordnungssystem (Gridfinity-kompatible Schnittstelle)"
    def Initialize(self):
        pass
    def GetClassName(self):
        return "Gui::PythonWorkbench"

# Die eigentliche Arbeit erledigen die Macros; Workbench nur als Erkennung.
try:
    Gui.addWorkbench(HausrasterWorkbench())
except Exception:
    pass
