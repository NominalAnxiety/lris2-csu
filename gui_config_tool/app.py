"""
The GUI is in its very early stages. Its current features are the ability to take in a starlist file
and a menu that doesn't do anything. 7/9/25
"""


#just importing everything for now. When on the final stages I will not import what I don't need
from targetListWidget import TargetDisplayWidget
from importTargetListandRun import ImportTargetListandRun
from menuBar import MenuBar
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LRIS-2 Slit Configuration Tool")
        self.setGeometry(100,100,800,800)
        self.setMenuBar(MenuBar()) #sets the menu bar

        main_layout = QHBoxLayout()
        
        import_target_list_display = ImportTargetListandRun()
        target_display = TargetDisplayWidget([])

        main_layout.addWidget(target_display)
        main_layout.addWidget(import_target_list_display)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

app = QApplication([])
window = MainWindow()
window.show()
app.exec()