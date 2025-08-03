import sys
from PySide6.QtWidgets import QApplication
from gui import GUI

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = GUI()
    window.run()
    sys.exit(app.exec())
