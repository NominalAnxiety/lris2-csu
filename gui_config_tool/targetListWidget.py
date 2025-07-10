
#from inputTargets import TargetList
from menuBar import MenuBar
from PyQt6.QtCore import Qt, QAbstractTableModel, QObject, pyqtSignal,pyqtSlot
from PyQt6.QtWidgets import (
    QWidget,
    QTableView,
    QVBoxLayout,
    QTableWidget


)
class TableModel(QAbstractTableModel):
    def __init__(self, data=[]):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:

            return self._data[index.row()][index.column()]

    def rowCount(self, index):

        return len(self._data)

    def columnCount(self, index):

        return len(self._data[0])
class TargetDisplayWidget(QWidget):
    def __init__(self,data=[]):
        super().__init__()
        #self.setGeometry(600,600,100,500)
        self.setStyleSheet("border: 2px solid black;")
        self.data = data

        self.table = QTableView()
        
        self.model = TableModel(self.data)
        self.table.setModel(self.model)


        layout = QVBoxLayout()

        layout.addWidget(self.table)

        self.setLayout(layout)
        #self.table.setModel(self.table)
    @pyqtSlot(list)
    def change_data(self,data):
        self.data = data
        self.model = TableModel(self.data)
        self.table.setModel(self.model)






