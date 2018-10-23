"""
Test Script for developing features
===================================

Current Test: Panel Editing
---------------------------

@author: Mario Garcia
"""

import sys
import numpy as np
from PyQt5 import QtGui, uic, QtWidgets, QtCore
import pyqtgraph as pg


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow_test.ui', self)
        self.splitter.setStretchFactor(1, 5)
        max_elems = 9
        self.all_data = []
        for i in range(max_elems):
            self.all_data.append(np.random.random(10))
        self.plot_data(self.graphicsView, self.all_data[0])
        # self.graphicsView.additem
        # win_ly = self.graphicsView.centralLayout
        # win_ly = self.graphicsView.items()
        # print(win_ly)
        # win_ly.addPlot(y=self.all_data[1])
        # print(self.graphicsView.items)
        p2 = pg.PlotDataItem(self.all_data[1])
        pw = pg.PlotItem()
        # self.graphicsView.addItem(p2)
        self.graphicsView.addItem(pw)
        g_layout = self.graphicsView.centralWidget.layout
        print(g_layout)
        # for element in g_layout:
        #     print(element)
        # print(self.graphicsView.items)
        # p1 = g_layout.addPlot(y=self.all_data[0])
        # print("Parent's children:\n", self.graphicsView.parent().children())
        # self.graphicsView.addPlot(y=self.all_data[1])
        # print("Graphics View items:")
        # widget_items = self.graphicsView.items()
        # for item in widget_items:
        #     print(type(item))

    def plot_data(self, plotWidget, data):
        plotWidget.clear()
        plotWidget.plot(data)
        plotWidget.autoRange()


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
