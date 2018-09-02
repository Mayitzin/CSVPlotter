"""CSV Plotter

@author: Mario Garcia
"""

import os
import sys
import numpy as np
import datetime
from PyQt5 import QtGui, uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot
import pyqtgraph as pg

# Using module 'rigidbody' from repository 'Robotics' to compute Orientations
sys.path.insert(0, '../Robotics/Motion')
import rigidbody as rb

base_path = "./data"
workspace = [base_path]

all_labels = {"repoIMU": {"Accelerometers":['IMU Acceleration_X', 'IMU Acceleration_Y', 'IMU Acceleration_Z'],
                         "Gyroscopes":['IMU Gyroscope_X', 'IMU Gyroscope_Y', 'IMU Gyroscope_Z'],
                         "Magnetometers":['IMU Magnetometer_X', 'IMU Magnetometer_Y', 'IMU Magnetometer_Z'],
                         "Quaternions":['Vicon Orientation_W', 'Vicon Orientation_X', 'Vicon Orientation_Y', 'Vicon Orientation_Z']
                        },
              "fcs_xsens": {"Accelerometers":['Acc_X', 'Acc_Y', 'Acc_Z'],
                            "Gyroscopes":['Gyr_X', 'Gyr_Y', 'Gyr_Z'],
                            "Quaternions":['Quat_q0', 'Quat_q1', 'Quat_q2', 'Quat_q3']
                           }
             }

plotting_options = ["Grid-X","Label-X","Values-X","Grid-Y","Label-Y","Values-Y","ShowTitle"]
# Set default List of Colors
colors = [(255,0,0,255),(0,255,0,255),(60,60,255,255),          # Red, Green, Blue
          (120,0,0,255),(0,100,0,255),(0,0,150,255),            # Dark Red, Dark Green, Dark Blue
          (215,215,0,255),(150,150,0,255),(125,125,125,255)  ]  # Yellow, Dark Yellow, Gray

data_options = { "Mahony IMU":{"Frequency":100.0, "Kp":0.1, "Ki":0.5}, # freq, Kp, Ki = 100.0, 0.1, 0.5
            "Mahony MARG":{"Frequency":100.0, "Kp":0.1, "Ki":0.5},
            "Madgwick IMU":{"Beta":0.01, "Frequency":100.0},
            "Madgwick MARG":{"Beta":0.01, "Frequency":100.0}
          }

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        # Remove QBasicTimer error by ensuring Application quits at right time.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupWidgets()
        self.file2use = ""
        self.update_tableWidget(workspace)
        self.all_data, self.indices = [], []

    """ ========================== SIGNALED FUNCTIONS ==========================
    """
    @pyqtSlot()
    def on_tableWidget_itemSelectionChanged(self):
        self.statusBar.showMessage("Reading File")
        row = self.tableWidget.currentRow()
        if row>-1:
            print(" ")
            self.file2use = self.tableWidget.item(row,0).text()
            # path2file = os.path.normpath(os.path.join(base_path, self.file2use))
            data = Data(self.file2use)
            # data.printDatasetInfo()
            # Compute and Plot Quaternions
            beta = 0.0029
            if len(data.acc)>0:
                # q = self.estimatePose(data, "MahonyIMU", [0.1, 0.5, 100])
                # q = self.estimatePose(data, "MahonyMARG", [0.1, 0.5, 100])
                q = self.estimatePose(data, "MadgwickIMU", [beta, 100.0])
                # q = self.estimatePose(data, "MadgwickMARG", [beta, 100.0])
                if len(q)>0:
                    mse_errors = self.getMSE(data.qts, q)
                    mse_sum = np.mean(np.mean(mse_errors))
                    mse_text = "MSE({:4.4f}) = {:1.4e}".format(beta,mse_sum)
                    print("   ", mse_text)
                    # Update Plot Lines
                    self.updatePlots(data)
                    self.plotData(self.graphicsView_5, q)
                    # self.plotData(self.graphicsView_6, mse_errors, clearPlot=True)
                    self.plotData(self.graphicsView_6, mse_errors)
                    self.updateTextItem(self.graphicsView_6, mse_text)
        self.statusBar.showMessage("Ready")


    @pyqtSlot(QtGui.QKeyEvent)
    def on_graphicsView_keyPressEvent(self):
        print("graphicsView was clicked")


    def quickCountLines(self, fileName):
        return sum(1 for line in open(fileName))


    def quickCountColumns(self, fileName, separator=';'):
        with open(fileName, 'r') as f:
            read_line = f.readline()
        num_columns = len( read_line.strip().split(separator) )
        return num_columns


    def setupWidgets(self):
        self.tableWidget.setHorizontalHeaderLabels(["File", "Lines", "Columns", "Created", "Notes"])
        self.plot_settings = dict.fromkeys(plotting_options, True)
        self.setupPlotWidgets()
        self.setupOptionsTree(self.treeWidget, data_options)


    def setupOptionsTree(self, treeWidget, data_options={}):
        """
        The default value for flags is:
        Qt::ItemIsSelectable | Qt::ItemIsUserCheckable | Qt::ItemIsEnabled | Qt::ItemIsDragEnabled | Qt::ItemIsDropEnabled

        See:
        - http://doc.qt.io/qt-5/qtreewidgetitem.html#flags
        """
        tree = treeWidget
        tree.setHeaderHidden(False)
        tree.setHeaderLabels(["Options", "Values"])
        filters_list = list(data_options.keys())
        for filter_name in filters_list:
            # Build each Filter parent branch
            parent = QtWidgets.QTreeWidgetItem(tree)
            parent.setText(0, filter_name)
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsUserCheckable)
            parent.setCheckState(0, QtCore.Qt.Unchecked)
            parameter_list = data_options[filter_name].keys()
            for parameter_label in parameter_list:
                # Read each customizable value
                value = data_options[filter_name][parameter_label]
                if isinstance(value, int):
                    wid = QtWidgets.QSpinBox()
                elif isinstance(value, float):
                    wid = QtWidgets.QDoubleSpinBox()
                    wid.setDecimals(4)
                else:
                    print("'"+str(value)+"' is not a valid value of '"+parameter_label+"' for a "+filter_name+" filter")
                    break
                # Build valid Spinboxes with corresponding labels and values
                child = QtWidgets.QTreeWidgetItem(parent)
                child.setText(0, parameter_label)
                tree.addTopLevelItem(child) # Or parent? <---- Further test this
                wid.setMaximum(250)
                wid.setValue(value)
                tree.setItemWidget(child, 1, wid)


    def setupPlotWidgets(self):
        # self.graphicsView.setBackground(background=None)
        self.graphicsView.setAntialiasing(True)
        self.graphicsView.showAxis('bottom', False)
        self.graphicsView.enableAutoRange()
        self.graphicsView.setTitle("Acceleration")
        # self.graphicsView.setTitle("<span style='font-size: 8pt'>Acceleration</span>")
        # print(self.graphicsView.layout.count() )
        # "<span style='font-size: 2pt'>"
        # self.graphicsView_2.setBackground(background=None)
        self.graphicsView_2.setAntialiasing(True)
        self.graphicsView_2.showAxis('bottom', False)
        self.graphicsView_2.enableAutoRange()
        self.graphicsView_2.setTitle("Angular Velocity")
        # self.graphicsView_3.setBackground(background=None)
        self.graphicsView_3.setAntialiasing(True)
        self.graphicsView_3.showAxis('bottom', False)
        self.graphicsView_3.enableAutoRange()
        self.graphicsView_3.setTitle("Magnetic Field")
        # self.graphicsView_4.setBackground(background=None)
        self.graphicsView_4.setAntialiasing(True)
        self.graphicsView_4.showAxis('bottom', False)
        self.graphicsView_4.enableAutoRange()
        self.graphicsView_4.setTitle("Reference Quaternions")
        # self.graphicsView_5.setBackground(background=None)
        self.graphicsView_5.setAntialiasing(True)
        self.graphicsView_5.showAxis('bottom', False)
        self.graphicsView_5.enableAutoRange()
        self.graphicsView_5.setTitle("Computed Quaternions")
        # self.graphicsView_6.setBackground(background=None)
        self.graphicsView_6.setAntialiasing(True)
        self.graphicsView_6.showAxis('bottom', True)
        self.graphicsView_6.setTitle("Error")
        # self.graphicsView_6.enableAutoRange()
        self.setupLookupGraph()


    def setupLookupGraph(self):
        self.graphicsView_7.setAntialiasing(True)
        self.graphicsView_7.showLabel('bottom', False)
        self.graphicsView_7.showLabel('left', False)
        self.graphicsView_7.showAxis('bottom', True)
        self.graphicsView_7.showAxis('left', False)
        self.graphicsView_7.setTitle(None)
        self.graphicsView_7.setMouseEnabled(x=False, y=False)
        # Add region
        region = pg.LinearRegionItem()
        region.setZValue(10)
        region.sigRegionChanged.connect(lambda: self.updateCoords(region))
        # Add ROI to Plot Widget
        self.graphicsView_7.addItem(region, ignoreBounds=True)


    def updateLookupGraph(self, data):
        # Get and Plot Shadow
        self.graphicsView_7.clear()
        shadow = self.getDataShadow(data)
        x_axis = range(np.shape(shadow)[0])
        upper_line = pg.PlotDataItem(x_axis, shadow[:,0])
        lower_line = pg.PlotDataItem(x_axis, shadow[:,1])
        filled_plot = pg.FillBetweenItem(upper_line, lower_line, brush=(100,100,100,200))
        self.graphicsView_7.addItem(filled_plot)


    def updateCoords(self, region):
        if len(self.all_data)>0:
            minX, maxX = region.getRegion()
            if minX<0:
                minX = 0
            ROI = [int(minX), int(maxX)]
            self.plotData(self.graphicsView, self.all_data[ROI[0]:ROI[1],self.indices[0]])
            self.plotData(self.graphicsView_2, self.all_data[ROI[0]:ROI[1],self.indices[1]])
            self.plotData(self.graphicsView_3, self.all_data[ROI[0]:ROI[1],self.indices[2]])
            self.plotData(self.graphicsView_4, self.all_data[ROI[0]:ROI[1],self.indices[3]])


    def update_tableWidget(self, workspace):
        found_files = self.getFiles(workspace)
        num_files = len(found_files)
        self.tableWidget.setRowCount(num_files)
        for row in range(num_files):
            file_name = found_files[row]
            item_num_lines = QtGui.QTableWidgetItem( str(self.quickCountLines(file_name)) )
            item_num_lines.setTextAlignment(QtCore.Qt.AlignRight)
            item_num_cols = QtGui.QTableWidgetItem( str(self.quickCountColumns(file_name)) )
            item_num_cols.setTextAlignment(QtCore.Qt.AlignRight)
            date_string = datetime.datetime.fromtimestamp(os.path.getctime(file_name)).strftime('%d.%m.%y %H:%M')
            item_date = QtGui.QTableWidgetItem( date_string )
            item_date.setTextAlignment(QtCore.Qt.AlignRight)
            # Populate Row with information of file
            self.tableWidget.setItem(row, 0, QtGui.QTableWidgetItem(file_name))
            self.tableWidget.setItem(row, 1, item_num_lines)
            self.tableWidget.setItem(row, 2, item_num_cols)
            self.tableWidget.setItem(row, 3, item_date)


    def getFiles(self, workspace):
        found_files = []
        for folder in workspace:
            files_in_folder = os.listdir(folder)
            complete_path_files = []
            for f in files_in_folder:
                complete_path_files.append(os.path.normpath(os.path.join(folder, f)))
            found_files += complete_path_files
        return found_files


    ## ============ DATA HANDLING FUNCTIONS ============
    def printDatasetInfo(self, data):
        print("\n- File:", data.file)
        print("- Headers:", data.headers)
        print("- Num Samples:", data.num_samples)
        print("- Labels:", data.labels)
        print("- Indices:", data.indices)
        print("- Magnetometers:", np.shape(data.mag))


    def getDataShadow(self, data):
        num_rows = np.shape(data)[0]
        shadow = np.linalg.norm(data, axis=1).reshape((num_rows,1))
        shadow = np.abs(shadow - np.mean(shadow[:10])) # Remove bias (mean of first lines)
        shadow = np.hstack((shadow, -shadow))
        return shadow


    def estimatePose(self, data, algo='MadgwickMARG', params=[]):
        """estimatePose computes the Orientation of the frame, given the IMU data
        """
        acc = data.acc
        gyr = data.gyr
        mag = data.mag
        num_samples = data.num_samples
        q = []
        if num_samples<1:
            return np.array(q)
        if algo.startswith("Madgwick"):
            beta, freq = 0.01, 100.0
            if len(params)>1:
                freq = params[1]
            if len(params)>0:
                beta = params[0]
            # Initial Pose is estimated with Accelerometer
            q = [ np.array(rb.am2q(acc[0])) ]
            # Choose INS architecture to use Madgwick's Algorithm with
            if "MARG" in algo:
                if len(mag)>0:
                    for i in range(1,num_samples):
                        q.append( rb.Madgwick.updateMARG(acc[i,:], gyr[i,:], mag[i,:], q[-1], beta, freq) )
                else:
                    print("[WARN] No Compass data found. Computing Orientation from Accelerometers and Gyroscopes ONLY.")
                    for i in range(1,num_samples):
                        q.append( rb.Madgwick.updateIMU(acc[i,:], gyr[i,:], q[-1], beta, freq) )
            elif "IMU" in algo:
                for i in range(1,num_samples):
                    q.append( rb.Madgwick.updateIMU(acc[i,:], gyr[i,:], q[-1], beta, freq) )
        elif algo.startswith("Mahony"):
            freq, Kp, Ki = 100.0, 0.1, 0.5
            if len(params)>2:
                freq = params[2]
            if len(params)>1:
                Kp = params[1]
            if len(params)>0:
                Ki = params[0]
            # Initial Pose is estimated with Accelerometer
            q = [ np.array(rb.am2q(acc[0])) ]   # Initial Pose is estimated with Accelerometer
            # Choose INS architecture to use Mahony's Algorithm with
            if "MARG" in algo:
                for i in range(1,num_samples):
                    q.append( rb.Mahony.updateMARG(acc[i,:], gyr[i,:], mag[i,:], q[-1], freq, Kp, Ki) )
            if "IMU" in algo:
                for i in range(1,num_samples):
                    q.append( rb.Mahony.updateIMU(acc[i,:], gyr[i,:], q[-1], freq, Kp, Ki) )
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


    def updateTextItem(self, plotWidget, text=""):
        # label = pg.LabelItem(justify='center')
        # label.setText(formatted_text)
        # plotWidget.addItem(label)
        # print("label._sizeHint", label._sizeHint)
        # print("label.opts", label.opts)
        # print("label.item", label.item)
        # print("label.itemRect()", label.itemRect())
        
        formatted_text = text
        # formatted_text = "<span style='font-size: 2pt'>" + text + "</span>"
        # scene_width = plotWidget.viewRect().top()
        scene_height = plotWidget.viewRect().height() * 0.7
        txtItem = pg.TextItem(formatted_text)
        # txtItem.setText(formatted_text)
        txtItem.setPos(0,scene_height)
        plotWidget.addItem(txtItem)


    def plotData(self, plotWidget, data, data2plot=[], clearPlot=True):
        """This function takes a numPy array of size M x 3, and plots its
        contents in the main PlotWidget using pyQtGraph.
        """
        lineStyle = "Line"
        current_settings = self.plot_settings.copy()
        if np.shape(data)[0] < 1:
            plotWidget.clear()
            return 
        if len(data2plot)<1:
            data2plot = list(range(np.shape(data)[1]))
        if clearPlot:
            plotWidget.clear()
        try:
            used_colors = colors[:len(data2plot)]
            if len(data2plot)==4:
                used_colors = [colors[6]] + colors[:len(data2plot)]
            for index in data2plot:
                line_data = data[:,index]
                self.plotDataLine(plotWidget, line_data, lineStyle, used_colors[index])
            plotWidget.getViewBox().setAspectLocked(lock=False)
            plotWidget.autoRange()
            # Add Grid
            plotWidget.showGrid(x=True, y=True)
            # plotWidget.showGrid(x=current_settings["Grid-X"], y=current_settings["Grid-Y"])
        except:
            QtGui.QMessageBox.warning(self, "Invalid File", "The selected file does not have valid data.")
        self.plot_settings = current_settings.copy()


    def updatePlots(self, data):
        # Get and Plot Shadow
        self.updateLookupGraph(data.acc)
        self.plotData(self.graphicsView, data.acc)
        self.plotData(self.graphicsView_2, data.gyr)
        self.plotData(self.graphicsView_3, data.mag)
        self.plotData(self.graphicsView_4, data.qts)


class Data:
    def __init__(self, fileName):
        self.file = fileName
        self.data, self.headers = self.getData(self.file)
        self.num_samples = len(self.data)
        self.labels, self.indices = self.idLabelGroups(self.headers)
        self.acc, self.gyr, self.mag, self.qts = [], [], [], []
        self.allotData(self.data, self.labels, self.indices)

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

    def isfloat(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def idLabelGroups(self, found_headers, single_group=True):
        labels2use = []
        all_group_indices = []
        for dset_lbl in all_labels:
            all_group_labels = []
            group_indices = []
            headers_keys = list(all_labels[dset_lbl].keys())
            for i in range(len(headers_keys)):
                header_group = headers_keys[i]
                group_labels = all_labels[dset_lbl][header_group]
                group_indices.append(self.matchIndices(found_headers, group_labels))
                all_group_labels += group_labels
            if all(x in found_headers for x in all_group_labels):
                labels2use.append(dset_lbl)
                all_group_indices.append(group_indices)
        if single_group and len(labels2use)>0:
            return all_labels[labels2use[0]].copy(), all_group_indices[0]
        else:
            return labels2use, all_group_indices

    def matchIndices(self, all_headers, requested_headers):
        requested_indices = []
        for header in requested_headers:
            if header in all_headers:
                requested_indices.append(all_headers.index(header))
        return requested_indices

    def allotData(self, data, labels, indices):
        try:
            labels_list = list(labels.keys())
            for label in labels_list:
                if label == "Accelerometers":
                    self.acc = data[:,indices[labels_list.index("Accelerometers")]]
                if label == "Gyroscopes":
                    self.gyr = data[:,indices[labels_list.index("Gyroscopes")]]
                if label == "Magnetometers":
                    self.mag = data[:,indices[labels_list.index("Magnetometers")]]
                if label == "Quaternions":
                    self.qts = data[:,indices[labels_list.index("Quaternions")]]
                    # q = rb.Quaternion(self.qts[0])
        except:
            print("[WARN] No data to allocate.")

    def printDatasetInfo(self):
        print("\n- File:", self.file)
        print("- Headers:", self.headers)
        print("- Num Samples:", self.num_samples)
        print("- Labels:", self.labels)
        print("- Indices:", self.indices)
        print("- Magnetometers:", np.shape(self.mag))

def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()