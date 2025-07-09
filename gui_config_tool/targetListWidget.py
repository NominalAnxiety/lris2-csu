
#from inputTargets import TargetList
from menuBar import MenuBar
from PyQt6.QtWidgets import (
    QWidget,
    QTableView
)



class TargetDisplayWidget(QWidget):
    def __init__(self,data):
        super().__init__()
        self.setGeometry(600,600,100,500)

        self.table = QTableView()

        self.data = data
        #self.table.setModel(self.table)




        
        #won't be using QlistWidget because I don't want the targets to be selectable
        #format this string so it looks nice
        #initial_label = QLabel(f"{"Name":<16}{"RA":<16}{"Dec":<16}{"Equinox":<16}") #should include target name, RA, Dec, and Equinox
        #initial_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        #initial_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        #initial_label.setLineWidth(2)

        #layout = QVBoxLayout()
        #layout.addWidget(initial_label)
        #self.setLayout(layout)

        #self.show()

        
