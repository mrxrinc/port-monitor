"""
Port Monitor - Serial port monitoring application with CRC generation.

This is the main entry point for the application.
"""

import sys
from PyQt5.QtWidgets import QApplication

from app import APP_NAME
from app.ui import MainWindow


def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
