"""CSV Plotter

@author: Mario Garcia
"""

import os
import sys
import numpy as np
from PyQt5 import QtGui, uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot

# Using module 'rigidbody' from repository 'Robotics' to compute Orientations
sys.path.insert(0, '../Robotics/Motion')
import rigidbody as rb

base_path = "./data"
test_file = "./data/TStick_Test02_Trial1.csv"

labels = {"Accelerometers":['IMU Acceleration_X', 'IMU Acceleration_Y', 'IMU Acceleration_Z'],
          "Gyroscopes":['IMU Gyroscope_X', 'IMU Gyroscope_Y', 'IMU Gyroscope_Z'],
          "Magnetometers":['IMU Magnetometer_X', 'IMU Magnetometer_Y', 'IMU Magnetometer_Z'],
          "Quaternions":['Vicon Orientation_W', 'Vicon Orientation_X', 'Vicon Orientation_Y', 'Vicon Orientation_Z']}

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
        self.file2use = ""
        self.update_tableWidget()


    """ ========================== SIGNALED FUNCTIONS ==========================
    """
    @pyqtSlot()
    def on_tableWidget_itemSelectionChanged(self):
        row = self.tableWidget.currentRow()
        if row>-1:
            self.file2use = self.tableWidget.item(row,0).text()
            path2file = os.path.normpath(os.path.join(base_path, self.file2use))
            all_data, all_headers = self.getData(path2file)
            labels2find = list(labels.keys())
            indices = []
            [ indices.append(self.getIndices(all_headers, labels[labels2find[idx]])) for idx in range(len(labels2find)) ]
            acc = all_data[:,indices[0]]
            gyr = all_data[:,indices[1]]
            mag = all_data[:,indices[2]]
            qts = all_data[:,indices[3]]
            self.plotData(self.graphicsView, acc)
            self.plotData(self.graphicsView_2, gyr)
            self.plotData(self.graphicsView_3, mag)
            self.plotData(self.graphicsView_4, qts)
            # Compute and Plot Quaternions
            beta = 0.0029
            q = self.estimatePose(acc, gyr, mag, "MadgwickMARG", [beta, 100.0])
            self.plotData(self.graphicsView_5, q)
            mse_errors = self.getMSE(qts, q)
            self.plotData(self.graphicsView_6, mse_errors)
            mse_sum = np.mean(np.mean(mse_errors))
            print("MSE_error(%f) = %e" % (beta,mse_sum))


    def estimatePose(self, acc, gyr, mag, algo='MadgwickMARG', params=[]):
        """estimatePose computes the Orientation of the frame, given the IMU data
        """
        num_samples = np.shape(acc)[0]
        q = []
        if num_samples<1:
            return np.array(q)
        if algo=="MadgwickMARG":
            beta, freq = 0.01, 100.0
            if len(params)>1:
                freq = params[1]
            if len(params)>0:
                beta = params[0]
            # Initial Pose is estimated with Accelerometer
            q = [ np.array(rb.am2q(acc[0])) ]
            for i in range(1,num_samples):
                q.append( rb.Madgwick.updateMARG(acc[i,:], gyr[i,:], mag[i,:], q[-1], beta, freq) )
        elif algo=="Gravity":
            for i in range(num_samples):
                q.append( rb.am2q(acc[i,:]) )
        elif algo=="IMU":
            for i in range(num_samples):
                q.append( rb.am2q(acc[i,:], mag[i,:]) )
        return np.array(q)


    def getMSE(self, ref_values, values):
        num_samples = np.shape(values)[0]
        num_labels = np.shape(values)[1]
        mse = []
        for j in range(num_labels):
            line_errors = []
            for i in range(num_samples):
                line_errors.append( (values[i,j]-ref_values[i,j])**2 )
            mse.append(line_errors)
        mse_errors = np.array(mse) / num_samples
        return np.transpose(mse_errors)


    def setupWidgets(self):
        self.plot_settings = dict.fromkeys(plotting_options, True)
        self.setupPlotWidgets()


    def setupPlotWidgets(self):
        # self.graphicsView.setBackground(background=None)
        self.graphicsView.setAntialiasing(True)
        # self.graphicsView_2.setBackground(background=None)
        self.graphicsView_2.setAntialiasing(True)
        # self.graphicsView_3.setBackground(background=None)
        self.graphicsView_3.setAntialiasing(True)
        # self.graphicsView_4.setBackground(background=None)
        self.graphicsView_4.setAntialiasing(True)


    def update_tableWidget(self):
        found_files = os.listdir(base_path)
        num_files = len(found_files)
        self.tableWidget.setRowCount(num_files)
        for row in range(num_files):
            self.tableWidget.setItem(row, 0, QtGui.QTableWidgetItem(found_files[row]))


    ## ============ DATA HANDLING FUNCTIONS ============

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


    def mergeHeaders(self, header_lines):
        all_headers = []
        for line in header_lines:
            split_line = line.strip().split(';')
            temp_header = split_line
            for index in range(len(split_line)):
                if len(temp_header[index])<1:
                    temp_header[index] = temp_header[index-1]
            all_headers.append(temp_header)
        new_headers = []
        for h in list(map(list, zip(*all_headers))):
            new_label = '_'.join(h).strip('_')
            if new_label not in new_headers:
                new_headers.append(new_label)
        return new_headers


    def getIndices(self, all_headers, requested_headers):
        found_headers = []
        for header in requested_headers:
            if header in all_headers:
                found_headers.append(all_headers.index(header))
        return found_headers


    def getData(self, fileName, data_type='float'):
        """getData reads the data stored in a CSV file, returns a numPy array of
        its contents and a list of its headers.

        fileName    is a string of the name of the requested file.

        Returns:

        data        is an array of the size M-by-N, where M is the number of
                    samples and N is the number of observed elements (headers or
                    columns.)
        headers     is a list of strings with the headers in the file. It is
                    also of size N.
        """
        data, headers = [], []
        try:
            with open(fileName, 'r') as f:
                read_data = f.readlines()
            # Read and store Headers in a list of strings
            header_rows = self.countHeaders(read_data)
            if header_rows > 1:
                headers = self.mergeHeaders(read_data[:header_rows])
            else:
                [headers.append(header.lstrip()) for header in read_data[0].strip().split(';')]
            # Read and store the data in a NumPy array
            [data.append( line.strip().split(';') ) for line in read_data[header_rows:]]    # Skip the first N lines
            data = np.array(data, dtype=data_type)
        except:
            data = np.array([], dtype=data_type)
        return data, headers


    def countHeaders(self, data_lines=[]):
        row_count = 0
        for line in data_lines:
            elements_array = []
            for element in line.strip().split(';'):
                elements_array.append(self.isfloat(element))
            if not all(elements_array):
                row_count += 1
            else:
                break
        return row_count


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


    def plotData(self, plotWidget, data, data2plot=[], clearPlot=True):
        """This function takes a numPy array of size M x 3, and plots its
        contents in the main PlotWidget using pyQtGraph.
        """
        lineStyle = "Line"
        current_settings = self.plot_settings.copy()
        if len(data2plot)<1:
            data2plot = list(range(np.shape(data)[1]))
        if clearPlot:
            plotWidget.clear()
        try:
            used_colors = colors[:len(data2plot)]
            if len(data2plot)==4:
                used_colors = [colors[6]] + colors[:len(data2plot)]
            for index in range(len(data2plot)):
                line_data = data[:,data2plot[index]]
                self.plotDataLine(plotWidget, line_data, lineStyle, used_colors[index])
            plotWidget.getViewBox().setAspectLocked(lock=False)
            plotWidget.autoRange()
            # Add Grid
            plotWidget.showGrid(x=current_settings["Grid-X"], y=current_settings["Grid-Y"])
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