"""
Test Script for developing features
===================================

Current Test: Panel Editing
---------------------------

@author: Mario Garcia
"""

import sys
import os
import datetime
import numpy as np
from PyQt5 import QtGui, uic, QtWidgets, QtCore
import pyqtgraph as pg

paths = ["./data/"]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow_test.ui', self)
        self.splitter.setStretchFactor(1, 5)
        max_elems = 9
        self.all_data = random_samples(max_elems, 10)
        gv = self.graphicsView
        gv_layout = gv.ci
        gv.dragEnterEvent = dragEnterEvent
        gv.addPlot(row=0, col=0, title="Data 1")
        gv.addPlot(row=0, col=1, title="Data 2")
        # print("Current Row:", gv_layout.currentRow)
        # print("Current Col:", gv_layout.currentCol)
        gv_layout.nextRow()
        gv.addPlot(row=1, col=0, title="Data 3")
        gv.addPlot(row=1, col=1, title="Data 4")
        # print("Current Row:", gv_layout.currentRow)
        # print("Current Col:", gv_layout.currentCol)
        all_plot_items = gv_layout.items
        # print("There are {} elements in the {} x {} Plot Widget array".format(len(all_plot_items), len(gv_layout.rows), gv_layout.currentCol))
        for plot_item in all_plot_items:
            plot_item.setAcceptDrops(True)
            plot_item.dropEvent = dropEvent
            # plot_item_title = plot_item.titleLabel.text
            # print("  {} at position {}".format(plot_item_title, all_plot_items[plot_item]))
            new_plot_data_item = pg.PlotDataItem(np.random.random(10))
            plot_item.addItem(new_plot_data_item)
        # print("Items:", gv_layout.items)
        # print("Rows:", gv_layout.rows)
        self.tableWidget.setDragEnabled(True)
        # self.tableWidget.dragLeaveEvent = dragLeaveEvent
        # self.tableWidget.viewport().setAcceptDrops(True)
        self.update_tableWidget(self.tableWidget, paths)


    def plot_data(self, plotWidget, data):
        plotWidget.clear()
        plotWidget.plot(data)
        plotWidget.autoRange()
        
    def update_tableWidget(self, table_widget, paths):
        found_files = getFiles(paths)
        num_files = len(found_files)
        table_widget.setRowCount(num_files)
        table_widget.setColumnCount(4)
        for row in range(num_files):
            file_name = found_files[row]
            item_file_name = QtGui.QTableWidgetItem( file_name )
            item_file_name.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            item_num_lines = QtGui.QTableWidgetItem( str(quickCountLines(file_name)) )
            item_num_lines.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item_num_cols = QtGui.QTableWidgetItem( str(quickCountColumns(file_name)) )
            item_num_cols.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            date_string = datetime.datetime.fromtimestamp(os.path.getctime(file_name)).strftime('%d.%m.%y %H:%M')
            item_date = QtGui.QTableWidgetItem( date_string )
            item_date.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            # Populate Row with information of file
            table_widget.setItem(row, 0, item_file_name)
            table_widget.setItem(row, 1, item_num_lines)
            table_widget.setItem(row, 2, item_num_cols)
            table_widget.setItem(row, 3, item_date)
        table_widget.resizeColumnToContents(0)

def dragEnterEvent(ev):
    event_mimeData = ev.mimeData()
    # print(dir(event_mimeData))
    print(event_mimeData.formats())
    ev.accept()
    # if ev.mimeData().hasFormat('text/plain'):
    #     ev.accept()
    # else:
    #     ev.ignore()

def dragLeaveEvent(ev):
    print(ev)

def dropEvent(event):
    # print(event.mimeData().text())
    print("Got drop!")

def quickCountLines(fileName):
    return sum(1 for line in open(fileName))

def quickCountColumns(fileName, separator=';'):
    with open(fileName, 'r') as f:
        read_line = f.readline()
    return len( read_line.strip().split(separator) )

def random_samples(num_items, samples_per_item):
    data = []
    for i in range(num_items):
        data.append(np.random.random(samples_per_item))
    return data

def getFiles(paths):
    found_files = []
    for folder in paths:
        files_in_folder = os.listdir(folder)
        complete_path_files = []
        for f in files_in_folder:
            complete_path_files.append(os.path.normpath(os.path.join(folder, f)))
        found_files += complete_path_files
    return found_files


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
