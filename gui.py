import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QVBoxLayout,
    QWidget, QHBoxLayout, QPushButton, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, QThread
import qtawesome as qta
from scanInvoice import InvoiceScanner  # make sure this file exists and exports the class
from PySide6.QtWidgets import QProgressBar
from pathlib import Path

downloads_path = Path.home() / "Downloads"
output_folder = downloads_path / "separated_invoices"
output_path = Path.home() / "Downloads" / "separated_invoices"


class GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
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
                padding: 5px;
            }
            QLineEdit {
                background: White;
                color: black;
                font-weight: bold;
                font-size: 15px;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QPushButton {
                background: White;
                color: black;
                font-weight: bold;
                font-size: 15px;
                border: 1px solid #2c3e50;
                border-radius: 10px;
                padding: 7px 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c598b;
            }
        """)

        self.setWindowTitle("Invoice Scanner")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignTop)

        self.horizontal_layout = QHBoxLayout()
        layout.addLayout(self.horizontal_layout)

        folder_path_label = QLabel("Choose PDF File:")
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

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.loading_label = QLabel("Processing...")
        self.loading_label.setStyleSheet("color: yellow; font-size: 16px;")
        layout.addWidget(self.loading_label)
        self.loading_label.hide()

        self.saved_location = QLabel(f"Files saved in your Downloads folder: {output_path}")
        self.saved_location.hide()
        layout.addWidget(self.saved_location)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", "", "PDF Files (*.pdf)")
        if files:
            self.file_path_input.setText("; ".join(files))

    def open_output_folder(self):
        output_path.mkdir(parents=True, exist_ok=True)

        # Open the folder in the default file manager
        if sys.platform.startswith('win'):
            os.startfile(str(output_path))
        elif sys.platform == 'darwin':
            os.system(f"open '{output_path}'")
        else:
            os.system(f"xdg-open '{output_path}'")

    def handle_submit(self):
        try:
            pdf_path = self.file_path_input.text().strip()
            if os.path.isfile(pdf_path):
                self.loading_label.show()
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)


                self.thread = QThread()
                self.worker = InvoiceScanner(pdf_path)
                self.worker.moveToThread(self.thread)

                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.thread.deleteLater)


                self.worker.progress.connect(self.progress_bar.setValue)

                # Hide loading after done
                self.thread.finished.connect(self.loading_label.hide)
                self.thread.finished.connect(lambda: self.progress_bar.setVisible(False))
                self.thread.finished.connect(lambda: print("Scan completed!"))
                self.thread.finished.connect(self.saved_location.show)
                self.thread.finished.connect(self.open_output_folder)  # Opens folder after scan

                self.thread.start()
            else:
                print("File does not exist or is not a valid path.")
        except Exception as e:
            print(f"Error in handle_submit: {e}")



    def run(self):
        self.show()


