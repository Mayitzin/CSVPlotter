"""CSV Plotter

@author: Mario Garcia
"""

import os
import sys
import numpy as np
import datetime
import json
from PyQt5 import QtGui, uic, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot
import pyqtgraph as pg
import pyqtgraph.opengl as gl

# Using module 'rigidbody' from repository 'Robotics' to compute Orientations
sys.path.insert(0, '../Robotics/Motion')
import rigidbody as rb

base_path = "./data"
workspace = [base_path]

# all_labels = {"repoIMU": {"Accelerometers":['IMU Acceleration_X', 'IMU Acceleration_Y', 'IMU Acceleration_Z'],
#                          "Gyroscopes":['IMU Gyroscope_X', 'IMU Gyroscope_Y', 'IMU Gyroscope_Z'],
#                          "Magnetometers":['IMU Magnetometer_X', 'IMU Magnetometer_Y', 'IMU Magnetometer_Z'],
#                          "Quaternions":['Vicon Orientation_W', 'Vicon Orientation_X', 'Vicon Orientation_Y', 'Vicon Orientation_Z']
#                         },
#               "fcs_xsens": {"Accelerometers":['Acc_X', 'Acc_Y', 'Acc_Z'],
#                             "Gyroscopes":['Gyr_X', 'Gyr_Y', 'Gyr_Z'],
#                             "Quaternions":['Quat_q0', 'Quat_q1', 'Quat_q2', 'Quat_q3']
#                            }
#              }

all_labels = {"repoIMU": {"Accelerometers":['IMU Acceleration_X', 'IMU Acceleration_Y', 'IMU Acceleration_Z'],
                         "Gyroscopes":['IMU Gyroscope_X', 'IMU Gyroscope_Y', 'IMU Gyroscope_Z'],
                         "Magnetometers":['IMU Magnetometer_X', 'IMU Magnetometer_Y', 'IMU Magnetometer_Z'],
                         "Quaternions":['Vicon Orientation_W', 'Vicon Orientation_X', 'Vicon Orientation_Y', 'Vicon Orientation_Z']
                        }
             }

plotting_options = ["Grid-X","Label-X","Values-X","Grid-Y","Label-Y","Values-Y","ShowTitle"]
# Set default List of Colors
colors = [(255,0,0,255),(0,255,0,255),(60,60,255,255),          # Red, Green, Blue
          (120,0,0,255),(0,100,0,255),(0,0,150,255),            # Dark Red, Dark Green, Dark Blue
          (215,215,0,255),(150,150,0,255),(125,125,125,255)  ]  # Yellow, Dark Yellow, Gray

with open('data_options.dat', 'r') as f:
    read_lines = f.readlines()
general_options = json.loads( ''.join(read_lines) )


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        # Remove QBasicTimer error by ensuring Application quits at right time.
        self.all_data, self.indices = [], []
        self.all_checkables = {}
        self.file2use = ""
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupWidgets()
        self.update_tableWidget(workspace)

    """ ========================== SIGNALED FUNCTIONS ==========================
    """
    @pyqtSlot()
    def on_tableWidget_itemSelectionChanged(self):
        self.statusBar.showMessage("Reading File")
        row = self.tableWidget.currentRow()
        if row>-1:
            self.file2use = self.tableWidget.item(row,0).text()
            data = Data(self.file2use)
            # Compute and Plot Quaternions
            if data.num_samples>0:
                # Update Plot Lines
                self.updatePlots(data)
                self.plotData(self.graphicsView_5, [])  # Estimated Quaternions
                self.plotData(self.graphicsView_6, [])  # Errors
                # Re-draw 3D
                # Reset GL Widget
                self.new_3d_widget.deleteLater()
                self.new_3d_widget = gl.GLViewWidget()
                self.setup3DWidget(self.new_3d_widget)
                self.showPlane(self.new_3d_widget)
                self.showFrames(self.new_3d_widget, data.qts)
                # Perform Computations with selected Algorithms
                if len(self.readSelectedVariables(self.treeWidget))>0:
                    tests = self.setTests()
                    mse_errors = self.runAllTests(tests, data)
        self.statusBar.showMessage("Ready")


    @pyqtSlot(QtGui.QKeyEvent)
    def on_graphicsView_keyPressEvent(self):
        print("graphicsView was clicked")

    @pyqtSlot(bool)
    def on_pushButton_clicked(self):
        if len(self.file2use)>0:
            data = Data(self.file2use)
            tests = self.setTests()
            mse_errors = self.runAllTests(tests, data)
        self.statusBar.showMessage("Ready")


    def runAllTests(self, tests, data, plotLast=True):
        tests_list = list(tests.keys())
        for test_name in tests_list:
            mse_mean = 0
            se_errors = self.runTest(data, {test_name:tests[test_name]})
            if len(se_errors)>0:
                mse_mean = np.mean(se_errors)
            input_vars = []
            [ input_vars.append(key+"="+str(tests[test_name][key])) for key in tests[test_name].keys() ]
            results_text = "{} ({} | {}) = {:1.4e}".format(test_name, data.file, ", ".join(input_vars), mse_mean)
            print("-", results_text)
        if plotLast and len(list(tests.keys()))>0:
            q = self.estimatePose(data, {test_name:tests[test_name]})
            self.plotData(self.graphicsView_5, q)
            self.plotData(self.graphicsView_6, se_errors)
            self.updateTextItem(self.graphicsView_6, results_text)
        return se_errors


    def runTest(self, data, test):
        se_errors = []
        q = self.estimatePose(data, test)
        if len(q)>0 or len(data.qts)>0:
            se_errors = self.squared_error(data.qts, q)
        return se_errors


    def setTests(self):
        test_names = ["Mahony IMU", "Mahony MARG", "Madgwick IMU", "Madgwick MARG"]
        tests = {}
        non_checkable_opts = self.readNonCheckableOptions(self.treeWidget)
        checked_options = self.readSelectedVariables(self.treeWidget)
        if len(checked_options)<1:
            return tests
        dict_keys = list(checked_options.keys())
        for test_name in dict_keys:
            if test_name in test_names:
                tests[test_name] = checked_options[test_name]
                for key in non_checkable_opts.keys():
                    tests[test_name][key] = non_checkable_opts[key]
        return tests


    def readSelectedVariables(self, tree):
        checked_options = {}
        variables_list = tree.findItems("", QtCore.Qt.MatchContains, 0)
        for var in variables_list:
            num_children = var.childCount()
            for child_idx in range(num_children):
                child = var.child(child_idx)
                child_name = child.text(0)
                if child.checkState(0):
                    checked_options[child_name] = {}
                    for i in range(child.childCount()):
                        grandchild = child.child(i)
                        checked_options[child_name][grandchild.text(0)] = tree.itemWidget(grandchild,1).value()
        return checked_options

    def readNonCheckableOptions(self, tree):
        non_checkable_options = ["Sampling Properties"]
        options = {}
        variables_list = tree.findItems("", QtCore.Qt.MatchContains, 0)
        for var in variables_list:
            var_text = var.text(0)
            if var_text in non_checkable_options:
                var_children_num = var.childCount()
                for child_idx in range(var_children_num):
                    child = var.child(child_idx)
                    child_name = child.text(0)
                    child_value = tree.itemWidget(var.child(child_idx),1).value()
                    options[child_name] = child_value
        return options


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
        self.setupOptionsTree(self.treeWidget, general_options)
        # Setup 3D Widget
        self.new_3d_widget = gl.GLViewWidget()
        self.setup3DWidget(self.new_3d_widget)
        self.showPlane(self.new_3d_widget)
        # self.showFrames(self.new_3d_widget)


    def setup3DWidget(self, new_widget):
        tab_layout = self.tabWidget.widget(2).layout()
        tab_layout.removeWidget(self.graphicsView_8)
        self.graphicsView_8.hide()
        tab_layout.addWidget(new_widget, 0, 0)
        # Set position of camera
        new_widget.opts['distance'] = 0.5
        
    def showPlane(self, plotWidget, plane="Z", shift=0.0):
        if plane in ["X", "Y", "Z"]:
            planeItem = gl.GLGridItem()
            if plane == "X":
                planeItem.rotate(90, 0, 1, 0)
                planeItem.translate(shift, 0, 0)
            if plane == "Y":
                planeItem.rotate(90, 1, 0, 0)
                planeItem.translate(0, shift, 0)
            if plane == "Z":
                planeItem.translate(0, 0, shift)
            plotWidget.addItem(planeItem)

    def showFrames(self, plotWidget, quaternions=[], locus=[], num_frames=5, ax_len=0.1):
        """plotFrames will show 3D frames describing the pose of the device
        along the reconstructed trajectory.

        plotWidget  is the given Axes element of the plotting canvas. It must be
                    a 3D plotting canvas.
        quaternions is an N-by-4 array with N sampled (or computed) Quaternions.
        num_frames  is the number of frames to be plot. Default is 5.
        ax_len      is the length of the axes in each frame. Default is 0.1.
        """
        colors = [(1.0,0.0,0.0,1.0), (0.0,1.0,0.0,1.0), (0.0,0.0,1.0,1.0)]
        num_samples = len(quaternions)
        if num_samples<1:
            quaternions = [[1., 0., 0., 0.]]
            locus = [[0., 0., 0.]]
            num_frames = 1
        if len(locus)<1:
            locus = np.zeros((num_samples, 3))
        # Plot frames
        for i in np.linspace(0, num_samples-1, num_frames, dtype='int'):
            R = rb.q2R(quaternions[i])
            t = np.array(locus[i])
            for j in range(len(colors)):
                axis_begin = np.array([t[0], t[1], t[2]])
                axis_end = np.array([R[j,0]*ax_len+t[0], R[j,1]*ax_len+t[1], R[j,2]*ax_len+t[2]])
                axis_array = np.vstack((axis_begin, axis_end))
                axis_item = gl.GLLinePlotItem(pos=axis_array, color=colors[j])
                plotWidget.addItem(axis_item)


    def fill_item(self, item, value):
        item.setExpanded(True)
        if type(value) is dict:
            for key, val in sorted(value.items()):
                child = QtWidgets.QTreeWidgetItem()
                child.setText(0, str(key))
                item.addChild(child)
                self.fill_item(child, val)
        # elif type(value) is list:
        #     for val in value:
        #         child = QtWidgets.QTreeWidgetItem()
        #         item.addChild(child)
        #         if type(val) is dict:      
        #             child.setText(0, '[dict]')
        #             self.fill_item(child, val, checkable=True)
        #         elif type(val) is list:
        #             child.setText(0, '[list]')
        #             self.fill_item(child, val, checkable=True)
        #         else:
        #             child.setText(0, str(val))              
        #         child.setExpanded(True)
        elif type(value) is float or int:
            child = self.createSpinBox(value)
            item.treeWidget().setItemWidget(item, 1, child)
            # Set immediate parent as checkable.
            item_parent = item.parent()
            item_parent_name =  item_parent.text(0)
            top_categories = list(general_options.keys())
            if item_parent_name not in top_categories:
                if item_parent_name not in list(self.all_checkables.keys()):
                    self.all_checkables[item_parent_name] = {}
                item_parent.setFlags(item_parent.flags() | QtCore.Qt.ItemIsUserCheckable)
                item_parent.setCheckState(0, QtCore.Qt.Unchecked)
                item_parent.setExpanded(False)
        else:
            child = QtWidgets.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)


    def setupOptionsTree(self, widget, value):
        headers = ["Options", "Values"]
        num_columns = len(headers)
        widget.clear()
        widget.setColumnCount(num_columns)
        widget.setHeaderLabels(headers)
        root_item = widget.invisibleRootItem()
        self.fill_item(root_item, value)
        widget.resizeColumnToContents(0)
        # Darken Top Level Rows
        c = [100,100,100,100]   # Color
        for index in range(widget.topLevelItemCount()):
            for column in range(num_columns):
                widget.topLevelItem(index).setBackground(column, QtGui.QColor(c[0], c[1], c[2], c[3]))


    def createSpinBox(self, value):
        widgetSpinBox = None
        if isinstance(value, int):
            widgetSpinBox = QtWidgets.QSpinBox()
        elif isinstance(value, float):
            widgetSpinBox = QtWidgets.QDoubleSpinBox()
            widgetSpinBox.setDecimals(4)
        else:
            print("  [ERROR] '"+str(value)+"' is not valid for SpinBoxes.")
        # Set default values
        if widgetSpinBox:
            widgetSpinBox.setMaximum(250)
            widgetSpinBox.setValue(value)
        return widgetSpinBox


    def setupPlotWidgets(self):
        # self.graphicsView.setBackground(background=None)
        self.graphicsView.setAntialiasing(True)
        # self.graphicsView.showAxis('bottom', False)
        self.graphicsView.enableAutoRange()
        self.graphicsView.setTitle("Acceleration")
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
        # region.sigRegionChanged.connect(lambda: self.updateCoords(region))
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
            item_file_name = QtGui.QTableWidgetItem( file_name )
            item_file_name.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            item_num_lines = QtGui.QTableWidgetItem( str(self.quickCountLines(file_name)) )
            item_num_lines.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item_num_cols = QtGui.QTableWidgetItem( str(self.quickCountColumns(file_name)) )
            item_num_cols.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            date_string = datetime.datetime.fromtimestamp(os.path.getctime(file_name)).strftime('%d.%m.%y %H:%M')
            item_date = QtGui.QTableWidgetItem( date_string )
            item_date.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            # Populate Row with information of file
            self.tableWidget.setItem(row, 0, item_file_name)
            self.tableWidget.setItem(row, 1, item_num_lines)
            self.tableWidget.setItem(row, 2, item_num_cols)
            self.tableWidget.setItem(row, 3, item_date)
        self.tableWidget.resizeColumnToContents(0)


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


    def estimatePose(self, data, estimation_info):
        """estimatePose computes the Orientation of the frame, given the IMU data
        """
        freq, beta = 100.0, 0.01
        Kp, Ki = 0.1, 0.5
        acc = data.acc
        gyr = data.gyr
        mag = data.mag
        num_samples = data.num_samples
        algo = list(estimation_info.keys())[0]
        q = []
        if num_samples<1:
            return np.array(q)
        if "Madgwick" in algo:
            freq = estimation_info[algo]['Frequency']
            beta = estimation_info[algo]['Beta']
            q = [ np.array(rb.am2q(acc[0])) ]   # Initial Pose estimation with Accelerometer
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
        if "Mahony" in algo:
            freq = estimation_info[algo]['Frequency']
            Kp = estimation_info[algo]['Kp']
            Ki = estimation_info[algo]['Ki']
            q = [ np.array(rb.am2q(acc[0])) ]   # Initial Pose estimation with Accelerometer
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


    def squared_error(self, ref_values, values):
        num_samples = np.shape(ref_values)[0]
        num_labels = np.shape(ref_values)[1]
        mse = []
        for j in range(num_labels):
            line_errors = []
            for i in range(num_samples):
                line_errors.append( (values[i,j]-ref_values[i,j])**2 )
            mse.append(line_errors)
        # mse_errors = np.array(mse) / num_samples
        return np.transpose(mse)


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
            plotWidget.showGrid(x=current_settings["Grid-X"], y=current_settings["Grid-Y"])
        except:
            QtGui.QMessageBox.warning(self, "Invalid File", "The selected file does not have valid data.")
        self.plot_settings = current_settings.copy()


    def updatePlots(self, data):
        # Get and Plot Shadow
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
            # print("Length:", len(data))
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
        # for dset_lbl in all_labels:
        #     all_group_labels = []
        #     group_indices = []
        #     headers_keys = list(all_labels[dset_lbl].keys())
        #     for i in range(len(headers_keys)):
        #         header_group = headers_keys[i]
        #         group_labels = all_labels[dset_lbl][header_group]
        #         group_indices.append(self.matchIndices(found_headers, group_labels))
        #         all_group_labels += group_labels
        #     if all(x in found_headers for x in all_group_labels):
        #         labels2use.append(dset_lbl)
        #         all_group_indices.append(group_indices)
        # if single_group and len(labels2use)>0:
        #     return all_labels[labels2use[0]].copy(), all_group_indices[0]
        # else:
        #     return labels2use, all_group_indices
        data_info = {}
        for dset_lbl in all_labels:
            all_group_labels = []
            group_indices = []
            headers_keys = list(all_labels[dset_lbl].keys())
            for i in range(len(headers_keys)):
                header_group = headers_keys[i]
                data_info[header_group] = {}
                group_labels = all_labels[dset_lbl][header_group]
                # print(header_group, ":", group_labels)
                group_indices.append(self.matchIndices(found_headers, group_labels))
                all_group_labels += group_labels
                data_info[header_group]["labels"] = group_labels
                data_info[header_group]["indices"] = group_indices[i]
            if all(x in found_headers for x in all_group_labels):
                labels2use.append(dset_lbl)
                all_group_indices.append(group_indices)
        # print(data_info)
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
            print("[WARN] File '{}' has no valid data to allocate.".format(self.file))

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