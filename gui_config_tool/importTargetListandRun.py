
from inputTargets import TargetList
from targetListWidget import TargetDisplayWidget
from PyQt6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QPushButton
)

class ImportTargetListandRun(QWidget):
    def __init__(self):
        super().__init__()
        self.import_target_list_button = QPushButton(text = "Import Target List")
        self.import_target_list_button.setFixedSize(150,40)

        self.import_target_list_button.clicked.connect(self.starlist_file_button_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.import_target_list_button)
        self.setLayout(layout)
        

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
            TargetDisplayWidget(target_list.send_list())

            

            