
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

#for the list widgets I don't want them to be selectable so I will just do a list of label widgets in a layout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LRIS-2 Slit Configuration Tool")
        self.setGeometry(100,100,1000,1000)
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