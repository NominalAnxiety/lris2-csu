
from inputTargets import TargetList
from targetListWidget import TargetDisplayWidget
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QPushButton,
    
)



class ImportTargetListandRun(QWidget):
    change_data = pyqtSignal(list)
    def __init__(self):
        super().__init__()

        self.setStyleSheet("border: 2px solid black;")
        import_target_list_button = QPushButton(text = "Import Target List")
        import_target_list_button.setFixedSize(150,40)
        

        layout = QVBoxLayout()
        

        import_target_list_button.clicked.connect(self.starlist_file_button_clicked)

        layout.addWidget(import_target_list_button)
        


        self.setLayout(layout)
        #self.show()
        

    def starlist_file_button_clicked(self):
        text_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a File",
            "",
            "All files (*)" 
        )

        if text_file_path: 
            print(f"Selected file: {text_file_path}")
            target_list = TargetList(text_file_path)
            #self.new_data_list.emit(target_list.send_list())
            self.change_data.emit(target_list.send_list())
            
            #TargetDisplayWidget(target_list.send_list())


            

            