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

PATHS = ["./data/"]
COLORS = [(255, 0, 0, 255), (0, 255, 0, 255), (60, 60, 255, 255),          # Red, Green, Blue
          (120, 0, 0, 255), (0, 100, 0, 255), (0, 0, 150, 255),            # Dark Red, Dark Green, Dark Blue
          (215, 215, 0, 255), (150, 150, 0, 255), (125, 125, 125, 255) ]   # Yellow, Dark Yellow, Gray

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow_test.ui', self)
        self.splitter.setStretchFactor(1, 5)
        self.setup_treeView(self.treeView, rootPath=PATHS[0])
        self.update_tableWidget(self.tableWidget, PATHS)
        self.tableWidget.setDragEnabled(True)
        self.init_graph_widget(self.graphicsView)

    def init_graph_widget(self, graph):
        if graph is None:
            graph = self.graphicsView
        gv_layout = graph.ci
        gv_layout.clear()
        graph.dragEnterEvent = dragEnterEvent
        graph.addPlot()
        for plot_item in gv_layout.items:
            plot_item.setAcceptDrops(True)
            plot_item.dropEvent = self.dropEvent

    def setup_treeView(self, treeView, rootPath="./"):
        model = QtWidgets.QFileSystemModel()
        model.setRootPath(rootPath)
        model.setNameFilters(["*.csv"])
        model.setNameFilterDisables(False)
        treeView.setModel(model)

    @pyqtSlot(QtCore.QModelIndex)
    def on_treeView_clicked(self):
        indices = self.treeView.selectedIndexes()
        if len(indices) > 0:
            selected_file = QtWidgets.QFileSystemModel().filePath(indices[-1])
            if selected_file.endswith(".csv"):
                data, headers = getData(selected_file)
                print("File: {}".format(selected_file))
                print("  Lines: {}".format(len(data)))
                print("  Header labels: {}".format(len(headers)))

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
        graph_layout = plot_widget.ci
        num_rows = len(list(graph_layout.rows.keys()))
        num_cols = graph_layout.currentCol
        if axis == 0:
            graph_layout.nextRow()
            for col in range(num_cols):
                plot_widget.addPlot(row=num_rows, col=col, title=None) # Add Row
        else:
            for row in range(num_rows):
                plot_widget.addPlot(row=row, col=num_cols, title=None) # Add Column
            graph_layout.currentCol = num_cols + 1
        # Set Drop Events in each plot item
        for plot_item in graph_layout.items:
            plot_item.setAcceptDrops(True)
            plot_item.dropEvent = self.dropEvent
        # Print Layout Dimensions
        num_rows, num_cols = widget_layout_dims(graph_layout)
        print("{} x {}".format(num_rows, num_cols))

    @pyqtSlot(bool)
    def on_pushButton_3_clicked(self):
        """
        Remove Column from Graphics View
        """
        self.remove_subplot_array(self.graphicsView, axis=1)

    @pyqtSlot(bool)
    def on_pushButton_4_clicked(self):
        """
        Remove Row from Graphics View
        """
        self.remove_subplot_array(self.graphicsView, axis=0)

    def remove_subplot_array(self, plot_widget, axis, index=-1):
        graph_layout = plot_widget.ci
        list_of_rows = sorted(list(graph_layout.rows.keys()))
        graph_items = graph_layout.items
        if axis == 0:
            # Remove a row
            if list_of_rows:
                row_to_remove = list_of_rows[index]
                # Remove each elements of desired row
                for item in list(graph_items.keys()):
                    row, col = graph_items[item][0]
                    if row == row_to_remove:
                        graph_layout.removeItem(item)
                # Remove empty row from the dict 'rows'
                if len(graph_layout.rows[row_to_remove]) < 1:
                    del graph_layout.rows[row_to_remove]
        else:
            # Remove a column
            if list_of_rows:
                last_row = list_of_rows[-1]
                list_of_cols = sorted(list(graph_layout.rows[last_row].keys()))
                if list_of_cols:
                    col_to_remove = list_of_cols[index]
                    # Remove all items in column
                    for item in list(graph_items.keys()):
                        row, col = graph_items[item][0]
                        if col == col_to_remove:
                            graph_layout.removeItem(item)
                    # Decrease the position of the column
                    graph_layout.currentCol -= 1
            else:
                print("The Widget is empty")
        # Print Layout Dimensions
        num_rows, num_cols = widget_layout_dims(graph_layout)
        print("{} x {}".format(num_rows, num_cols))

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
        for plot_item in all_plot_items:
            coords = plot_item.mapRectToParent(plot_item.rect()).getCoords()
            in_subplot = (coords[0] <= ev_pos.x() <= coords[2]) and (coords[1] <= ev_pos.y() <= coords[3])
            if in_subplot:
                item_cells = all_plot_items[plot_item]
                item_title = plot_item.titleLabel.text
                dropped_file = dragged_items[-1]
                add_graph(plot_item, dropped_file)

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


def widget_layout_dims(widget_layout):
    num_rows = len(widget_layout.rows)
    num_cols = widget_layout.currentCol
    return (num_rows, num_cols)

def add_graph(item, dropped_file):
    """
    Add data line to plot item
    """
    num_items = len(item.listDataItems())
    color = COLORS[num_items]
    lines = []
    with open(dropped_file, 'r') as f:
        read_lines = f.readlines()
    [lines.append(line.strip().split(';')) for line in read_lines[3:]]
    data_array = np.array(lines, dtype='float')
    plot_data_item = pg.PlotDataItem(data_array[:,3], pen=color)
    item.addItem(plot_data_item)

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
    """
    See Also
    --------
    - https://wiki.python.org/moin/PyQt/Handling%20Qt%27s%20internal%20item%20MIME%20type

    """
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

def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def countHeaders(data_lines=[]):
    row_count = 0
    for line in data_lines:
        elements_array = []
        for element in line:
            elements_array.append(isfloat(element))
        if not all(elements_array):
            row_count += 1
        else:
            break
    return row_count

def mergeHeaders(header_lines):
    all_headers = []
    for line in header_lines:
        temp_header = line
        for index in range(len(line)):
            if len(temp_header[index]) < 1:
                temp_header[index] = temp_header[index-1]
        all_headers.append(temp_header)
    new_headers = []
    for h in list(map(list, zip(*all_headers))):
        new_label = '_'.join(h).strip('_')
        if new_label not in new_headers:
            new_headers.append(new_label)
    return new_headers

def load_csv(fileName):
    split_lines = []
    try:
        with open(fileName, 'r') as f:
            read_lines = f.readlines()
        [split_lines.append(line.strip().split(';')) for line in read_lines]
    except:
        print("[ERROR] Invalid file: {}".format(fileName))
    return split_lines

def getData(fileName, data_type='float'):
    """getData reads the data stored in a CSV file, returns a numPy array of
    its contents and a list of its headers.

    fileName    is a string of the name of the requested file.

    Returns:

    data        is an array of the size M-by-N, where M is the number of
                samples and N is the number of observed elements (headers or
                columns.)
    headers     is a list of N strings with the headers in the file.
    """
    data, headers = [], []
    try:
        read_lines = load_csv(fileName)
        # Read and store Headers in a list of strings
        header_rows = countHeaders(read_lines)
        if header_rows > 1:
            headers = mergeHeaders(read_lines[:header_rows])
        else:
            [headers.append(header.strip()) for header in read_lines[0]]
        # Read and store the data in a NumPy array
        [data.append( line ) for line in read_lines[header_rows:]]    # Skip the first N lines
        data = np.array(data, dtype=data_type)
    except:
        data = np.array([], dtype=data_type)
    return data, headers


class Data:
    def __init__(self, fileName):
        self.file = fileName
        self.data, self.headers = getData(self.file)
        self.num_samples = len(self.data)
        self.header_rows = countHeaders(self.lines)

def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
