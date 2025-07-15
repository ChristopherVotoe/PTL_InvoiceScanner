from PyQt5.QtWidgets import QMainWindow, QLabel, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QPushButton,QFileDialog
import qtawesome as qta
from PyQt5.QtCore import Qt
#from scanInvoice import (sortingInvoice)


class GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #00416A, stop:1 #E4E5E6);
                font-family: "Roboto", sans-serif;
                font-size: 18px;
            }

            QLabel {
                color: White;
                font-size: 18px;
                font-weight: bold;
                font-family: "Roboto", sans-serif;
                padding: 5px;
            }
            QLineEdit {
            background: White;
            color: black; /*TEXT COLOR*/
            font-weight: bold;
            font-family: "Roboto", sans-serif;
            font-size : 15px;
            border: 1px solid #2c3e50;
            border-radius: 8px;
            padding: 5px;
            }
            QLineEdit:focus {
            border: 1px solid #3498db;  /* Focus color */
            }
            QPushButton {
            background: White;
            color: black;
            font-weight: bold;
            font-family: "Roboto", sans-serif;
            font-size : 15px;
            border: 1px solid #2c3e50;
            border-radius: 10px;
            padding: 7px 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;  /* Hover effect */
            }
            QPushButton:pressed {
                background-color: #1c598b;  /* Pressed effect */
            }
        """)

        self.setWindowTitle("Invoice Scanner")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignTop)

        # Horizontal layout 
        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        folder_path_label = QLabel("Choose Project Year Folder:")
        self.horizontal_layout.addWidget(folder_path_label)

        self.file_path_input = QLineEdit()
        self.horizontal_layout.addWidget(self.file_path_input)

        browse_button = QPushButton("Browse")
        browse_button.setIcon(qta.icon('fa5s.file-import'))
        browse_button.clicked.connect(self.browse_files)
        self.horizontal_layout.addWidget(browse_button)

        submit_button = QPushButton("Submit")
        submit_button.setIcon(qta.icon('fa5s.check'))
        submit_button.clicked.connect(self.handle_submit)
        self.horizontal_layout.addWidget(submit_button)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", "", "PDF Files (*.pdf)")
        if files:
            self.file_path_input.setText("; ".join(files))  


    def handle_submit(self):
        try:
            pdf_path = self.file_path_input.text().strip()
            print(f"{pdf_path}")
        except Exception as e:
            print(f"Error in handle_submit: {e}")



    def run(self):
        self.show()