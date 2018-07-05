"""CSV Plotter

@author: Mario Garcia
"""

import sys
import numpy as np
from PyQt5 import QtGui, uic, QtWidgets, QtCore
# from PyQt5.QtCore import pyqtSlot

test_file = "./data/TStick_Test02_Trial1.csv"

plotting_options = ["Grid-X","Label-X","Values-X","Grid-Y","Label-Y","Values-Y","ShowTitle"]
# Set default List of Colors
colors = [(255,0,0,255),(0,255,0,255),(60,60,255,255),          # Red, Green, Blue
          (120,0,0,255),(0,100,0,255),(0,0,150,255),            # Dark Red, Dark Green, Dark Blue
          (215,215,0,255),(150,150,0,255),(125,125,125,255)  ]  # Yellow, Dark Yellow, Gray

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        # Remove QBasicTimer error by ensuring Application quits at right time.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupWidgets()

        all_data, headers = self.getData(test_file, 2)
        self.plotData(all_data, headers, [1, 2, 3])


    def setupWidgets(self):
        self.plot_settings = dict.fromkeys(plotting_options, True)
        self.setupPlotWidget()


    def setupPlotWidget(self):
        self.graphicsView.setBackground(background=None)
        self.graphicsView.setAntialiasing(True)


    def getHeaders(self, fileName):
        """This function reads the headers stored in the first line of a CSV
        file. It splits the first line at the separator ';' and returns the
        resulting strings.

        fileName    is a string of the name of the requested file.
        """
        with open(fileName, 'r') as f:
            read_data = f.readline()
        header_string = read_data.strip().split(';')
        headers = []
        [ headers.append(header.lstrip()) for header in header_string ]
        return headers


    def getData(self, fileName, skip_N=1, data_type='float'):
        """getData reads the data stored in a CSV file, returns a numPy array of
        its contents and a list of its headers.

        fileName    is a string of the name of the requested file.

        Returns:

        data        is an array of the size M-by-N, where M is the number of
                    observations and N is the number of observed elements
                    (headers, or columns).
        headers     is a list of strings with the headers in the file. It is
                    also of size N.
        """
        data, headers = [], []
        try:
            with open(fileName, 'r') as f:
                read_data = f.readlines()
            # Read Headers (remove leading white spaces) and Store data in an array
            [headers.append(header.lstrip()) for header in read_data[0].strip().split(';')]
            [data.append( line.strip().split(';') ) for line in read_data[skip_N:]]    # Skip the first N lines
            data = np.array(data, dtype=data_type)
        except:
            data = np.array([], dtype=data_type)
        return data, headers


    def isfloat(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False


    def selectColor(self, num_headers, all_colors):
        used_colors = all_colors
        if num_headers == 4: used_colors = [all_colors[6]] + all_colors[:3]
        if num_headers == 6: used_colors = all_colors[:6]
        if num_headers == 8: used_colors = [all_colors[7]] + all_colors[3:6] + [all_colors[6]] + all_colors[:3]
        return used_colors


    def plotDataLine(self, plot_widget, data=[], style="", color=(125,125,125,255)):
        pen_style = None
        symbol_style = None
        if "Line" in style:
            pen_style = color
        if "Scatter" in style:
            symbol_style = 'o'
        plot_widget.plot(data, pen=pen_style, symbol=symbol_style, symbolPen=None, symbolSize=4, symbolBrush=color, name="Curve")


    def plotData(self, data, file_headers, data2plot=[0], mask="", plot_options="0111111", clearPlot=True):
        """This function takes a numPy array of size M x 3, and plots its
        contents in the main PlotWidget using pyQtGraph.
        """
        lineStyle = "Line"
        current_settings = self.plot_settings.copy()
        num_headers = len(file_headers)
        if clearPlot:
            # Set and start Plotting Widget
            self.graphicsView.clear()
        try:
            for elem in data2plot:
                # used_colors = self.selectColor(num_headers, colors[elem])
                line_data = data[:,elem]
                self.plotDataLine(self.graphicsView, line_data, lineStyle, colors[elem])
            # Allow resizing stretching axes
            self.graphicsView.getViewBox().setAspectLocked(lock=False)
            self.graphicsView.autoRange()
            # Add Grid
            self.graphicsView.showGrid(x=current_settings["Grid-X"], y=current_settings["Grid-Y"])
        except:
            QtGui.QMessageBox.warning(self, "Invalid File", "The selected file does not have valid data.")
        self.plot_settings = current_settings.copy()


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()