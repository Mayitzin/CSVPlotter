"""CSV Plotter

@author: Mario Garcia
"""

from PyQt5 import QtGui, uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        # Remove QBasicTimer error by ensuring Application quits at right time.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupPlotWidget()

    def setupPlotWidget(self):
        self.graphicsView.setBackground(background=None)
        self.graphicsView.setAntialiasing(True)


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()