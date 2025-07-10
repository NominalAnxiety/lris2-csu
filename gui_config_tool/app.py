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
    QLabel,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LRIS-2 Slit Configuration Tool")
        self.setGeometry(100,100,1000,700)
        self.setMenuBar(MenuBar()) #sets the menu bar

        main_layout = QHBoxLayout()
        layoutH1 = QHBoxLayout()
        layoutV1 = QVBoxLayout() #left side
        layoutV2 = QVBoxLayout() #right side
        
        import_target_list_display = ImportTargetListandRun()
        sample_data = [[0,1,1,1],[1,0,1,1]]

        target_display = TargetDisplayWidget(sample_data)
        temp_widget1 = QLabel("hello")
        temp_widget2 = QLabel("hello")
        temp_widget3 = QLabel("hello")
        import_target_list_display.setStyleSheet("border: 2px solid black;")

        import_target_list_display.change_data.connect(target_display.change_data)

        layoutV2.addWidget(temp_widget1)
        layoutV2.addWidget(import_target_list_display)

        layoutH1.addWidget(temp_widget2)
        layoutH1.addWidget(temp_widget3)
        
        layoutV1.addLayout(layoutH1)
        layoutV1.addWidget(target_display)

        main_layout.addLayout(layoutV1)
        main_layout.addLayout(layoutV2)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def update_list_display(self,data):
        self.data = data
        self.target_display = TargetDisplayWidget(self.data)
        self.target_display.update()

app = QApplication([])
window = MainWindow()
window.show()
app.exec()