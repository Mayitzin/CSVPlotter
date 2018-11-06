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
from PyQt5.QtCore import pyqtSlot
import pyqtgraph as pg

paths = ["./data/"]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow_test.ui', self)
        self.splitter.setStretchFactor(1, 5)
        self.update_tableWidget(self.tableWidget, paths)
        self.tableWidget.setDragEnabled(True)
        max_elems = 9
        self.all_data = random_samples(max_elems, 10)
        gv = self.graphicsView
        # print(type(gv))
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
            # plot_item.dropEvent = dropEvent
            plot_item.dropEvent = self.dropEvent
            # plot_item_title = plot_item.titleLabel.text
            # print("  {} at position {}".format(plot_item_title, all_plot_items[plot_item]))
            new_plot_data_item = pg.PlotDataItem(np.random.random(10))
            plot_item.addItem(new_plot_data_item)
        # print("Items:", gv_layout.items)
        # print("Rows:", gv_layout.rows)
        # self.tableWidget.viewport().setAcceptDrops(True)

    def widget_layout_dims(self, widget_layout):
        # gv_layout = plot_widget.ci
        num_rows = widget_layout.currentRow + 1
        num_cols = widget_layout.currentCol
        # print(" {} x {}".format(num_rows, num_cols))
        return (num_rows, num_cols)

    @pyqtSlot(bool)
    def on_pushButton_clicked(self):
        """
        Add Column in Graphics View
        """
        self.add_subplot_array(self.graphicsView, axis=1)

    @pyqtSlot(bool)
    def on_pushButton_2_clicked(self):
        """
        Add Row in Graphics View
        """
        self.add_subplot_array(self.graphicsView, axis=0)

    def add_subplot_array(self, plot_widget, axis):
        gv_layout = plot_widget.ci
        num_rows = gv_layout.currentRow + 1
        num_cols = gv_layout.currentCol
        if axis == 0:
            gv_layout.nextRow()
            for col in range(num_cols):
                plot_widget.addPlot(row=num_rows, col=col, title="Extra Row")
        else:
            for row in range(num_rows):
                plot_widget.addPlot(row=row, col=num_cols, title="Extra Column")
            gv_layout.currentCol = num_cols + 1
        all_plot_items = gv_layout.items
        for plot_item in all_plot_items:
            plot_item.setAcceptDrops(True)
            plot_item.dropEvent = self.dropEvent

    def copy_plot_widget(self, plot_widget, scope=None):
        plot_widget_layout = plot_widget.ci
        print(type(plot_widget_layout))
        num_rows, num_cols = self.widget_layout_dims(plot_widget_layout)
        print("{} x {}".format(num_rows, num_cols))
        # Show elements
        # plot_items_list = list(plot_widget_layout.items.keys())
        # for item in plot_items_list:
        #     print(item, plot_widget_layout.items[item][0])
        # for item in plot_rows_list:
        #     print(item, plot_widget_layout.items[item][0])
        # New Graphics Layout
        new_gv = pg.widgets.GraphicsLayoutWidget.GraphicsLayoutWidget()
        # if scope is None:
        #     scope = [num_rows, num_cols]
        # for row in range(scope[0]):
        #     new_gv.addItem
        plot_rows_list = list(plot_widget_layout.rows.keys())
        for row in plot_rows_list:
            print("Row: {}".format(row))
            for col in range(num_cols):
                print("   Column: {}".format(plot_widget_layout.rows[row]))
        return new_gv

    @pyqtSlot(bool)
    def on_pushButton_3_clicked(self):
        """
        Remove Column from Graphics View
        """
        new_graphics_view = self.copy_plot_widget(self.graphicsView)
        new_gv_layout = new_graphics_view.ci
        print(type(new_gv_layout))
        num_rows, num_cols = self.widget_layout_dims(new_gv_layout)
        print("{} x {}".format(num_rows, num_cols))

    @pyqtSlot(bool)
    def on_pushButton_4_clicked(self):
        """
        Remove Row from Graphics View
        """
        print("Push button 4 was clicked.")

    def dropEvent(self, event):
        event_mimeData = event.mimeData()
        # Handle event data
        byte_array = event_mimeData.data('application/x-qabstractitemmodeldatalist')
        dcd_data = decode_data(byte_array)[0]
        dragged_items = []
        if type(dcd_data) == dict:
            for k in list(dcd_data.keys()):
                if type(dcd_data[k].value()) == str:
                    dragged_items.append(dcd_data[k].value())
        # Handle drop event position in Graphics View
        ev_pos = event.scenePos()
        all_plot_items = self.graphicsView.ci.items
        for item in all_plot_items:
            coords = item.mapRectToParent(item.rect()).getCoords()
            in_subplot = (coords[0] <= ev_pos.x() <= coords[2]) and (coords[1] <= ev_pos.y() <= coords[3])
            if in_subplot:
                item_cells = all_plot_items[item]
                item_title = item.titleLabel.text
                print("Dropped {} in {} {}.".format(dragged_items[-1], item_title, item_cells[0]))


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


def dragEnterEvent(event):
    """
    See Also
    --------
    - https://wiki.python.org/moin/PyQt/Handling%20Qt%27s%20internal%20item%20MIME%20type

    """
    event_mimeData = event.mimeData()
    if event_mimeData.hasFormat('application/x-qabstractitemmodeldatalist'):
        event.accept()
    else:
        event.ignore()


def decode_data(bytearray):
    data = []
    item = {}
    ds = QtCore.QDataStream(bytearray)
    while not ds.atEnd():
        row = ds.readInt32()
        column = ds.readInt32()
        map_items = ds.readInt32()
        for i in range(map_items):
            key = ds.readInt32()
            value = QtCore.QVariant()
            ds >> value
            item[QtCore.Qt.ItemDataRole(key)] = value
        data.append(item)
    return data

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
