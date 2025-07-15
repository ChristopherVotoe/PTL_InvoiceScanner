import sys
from PyQt5.QtWidgets import QApplication
from gui import GUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = GUI()
    main_window.run()
    sys.exit(app.exec_())
