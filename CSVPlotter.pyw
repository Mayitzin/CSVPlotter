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

plotting_options = ["Grid-X", "Label-X", "Values-X", "Grid-Y", "Label-Y", "Values-Y", "ShowTitle"]
# Set default List of Colors
colors = [(255, 0, 0, 255), (0, 255, 0, 255), (60, 60, 255, 255),          # Red, Green, Blue
          (120, 0, 0, 255), (0, 100, 0, 255), (0, 0, 150, 255),            # Dark Red, Dark Green, Dark Blue
          (215, 215, 0, 255), (150, 150, 0, 255), (125, 125, 125, 255) ]   # Yellow, Dark Yellow, Gray

def json2dict(fileName):
    """reads a json file and stores its contents orderly in a dictionary.
    
    Args:
        fileName (TYPE): the path and name of the file containing a json string.
    
    Returns:
        dictionary with the formatted contents of the json file.
    """
    with open(fileName, 'r') as f:
        read_lines = f.readlines()
    return json.loads( ''.join(read_lines) )

def quickCountLines(fileName):
    return sum(1 for line in open(fileName))

def quickCountColumns(fileName, separator=';'):
    with open(fileName, 'r') as f:
        read_line = f.readline()
    return len( read_line.strip().split(separator) )

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
        for element in line.strip().split(';'):
            elements_array.append(isfloat(element))
        if not all(elements_array):
            row_count += 1
        else:
            break
    return row_count

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

all_labels = json2dict('labels.dat')
general_options = json2dict('data_options.dat')

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('mainwindow.ui', self)
        # Remove QBasicTimer error by ensuring Application quits at right time.
        self.all_data, self.indices = [], []
        self.data = None
        self.all_checkables = {}
        self.file2use = ""
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupWidgets()
        self.update_tableWidget(workspace)
        self.tableWidget.setDragEnabled(True)
        gv = self.graphicsView
        gv.dragEnterEvent = dragEnterEvent
        gv_layout = gv.ci
        plot_items = gv_layout.items
        for item in plot_items:
            item.setAcceptDrops(True)
            item.dropEvent = dropEvent

    """ ========================== SIGNALED FUNCTIONS ==========================
    """
    @pyqtSlot()
    def on_tableWidget_itemSelectionChanged(self):
        self.statusBar.showMessage("Reading File")
        row = self.tableWidget.currentRow()
        if row>-1:
            self.file2use = self.tableWidget.item(row,0).text()
            data = Data(self.file2use)
            self.data = data
            # Compute and Plot Quaternions
            if data.num_samples>0:
                # Update Plot Lines
                self.updatePlots(data)
                self.plotData(self.graphicsView_5, [])  # Estimated Quaternions
                self.plotData(self.graphicsView_6, [])  # Errors
                # Re-draw 3D. Reset GL Widget
                self.new_3d_widget.deleteLater()
                self.new_3d_widget = gl.GLViewWidget()
                self.setup3DWidget(self.new_3d_widget)
                self.showPlane(self.new_3d_widget)
                self.showFrames(self.new_3d_widget, data.qts, data.pos, num_frames=10)
                # Perform Computations with selected Algorithms
                if len(self.readSelectedVariables(self.treeWidget))>0:
                    tests = self.setTests()
                    mse_errors = self.runAllTests(tests, data)
                # Update MiniMap
                self.updateLookupGraph(data)
        self.statusBar.showMessage("Ready")


    @pyqtSlot(QtGui.QKeyEvent)
    def on_graphicsView_keyPressEvent(self):
        print("graphicsView was clicked")

    @pyqtSlot(bool)
    def on_pushButton_clicked(self):
        if len(self.file2use)>0:
            tests = self.setTests()
            mse_errors = self.runAllTests(tests, self.data)
        self.statusBar.showMessage("Ready")


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


    def runAllTests(self, tests, data, plotLast=True):
        tests_list = list(tests.keys())
        se_errors = np.array([])
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
        errors = []
        q = self.estimatePose(data, test)
        if len(q)>0 or len(data.qts)>0:
            errors = self.squared_error(data.qts, q)
        return errors


    def setTests(self):
        test_names = list(general_options["Pose Estimation"].keys())
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
    #
    #
    # def quickCountLines(self, fileName):
    #     return sum(1 for line in open(fileName))
    #
    #
    # def quickCountColumns(self, fileName, separator=';'):
    #     with open(fileName, 'r') as f:
    #         read_line = f.readline()
    #     return len( read_line.strip().split(separator) )


    def setupWidgets(self):
        self.splitter.setStretchFactor(1,5)
        self.splitter_2.setStretchFactor(6,1)
        self.tableWidget.setHorizontalHeaderLabels(["File", "Lines", "Columns", "Created", "Notes"])
        self.plot_settings = dict.fromkeys(plotting_options, True)
        self.setupPlotWidgets()
        self.setupOptionsTree(self.treeWidget, general_options)
        # Setup 3D Widget
        self.new_3d_widget = gl.GLViewWidget()
        self.setup3DWidget(self.new_3d_widget)
        self.showPlane(self.new_3d_widget)


    def setup3DWidget(self, new_widget):
        tab_layout = self.tabWidget.widget(2).layout()
        tab_layout.removeWidget(self.graphicsView_8)
        self.graphicsView_8.hide()
        tab_layout.addWidget(new_widget, 0, 0)
        # Set position of camera
        new_widget.opts['distance'] = 3.0
        
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
        colors = [(1.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0)]
        num_samples = len(quaternions)
        if num_samples<1:
            quaternions = [[1., 0., 0., 0.]]
            locus = [[0., 0., 0.]]
            num_frames = 1
        else:
            if len(quaternions[0])<1:
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
        # Show body trace
        body_item = gl.GLLinePlotItem(pos=locus, color=(0.5,0.5,0.5,0.5))
        plotWidget.addItem(body_item)


    def fill_item(self, item, value):
        item.setExpanded(True)
        if type(value) is dict:
            for key, val in sorted(value.items()):
                child = QtWidgets.QTreeWidgetItem()
                child.setText(0, str(key))
                item.addChild(child)
                self.fill_item(child, val)
        elif type(value) is list:
            child = self.createComboBox(value)
            item.treeWidget().setItemWidget(item, 1, child)
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
        self.highlightRows(widget, [], [150,150,150,100])


    def highlightRows(self, tree_widget, rows=[], color=[170,170,170,100]):
        qt_color = QtGui.QColor(color[0], color[1], color[2], color[3])
        num_columns = tree_widget.columnCount()
        num_top_level_items = tree_widget.topLevelItemCount()
        if len(rows)<1:
            for index in range(num_top_level_items):
                for column in range(num_columns):
                    tree_widget.topLevelItem(index).setBackground(column, qt_color)


    def createComboBox(self, list_of_values):
        widgetComboBox = QtWidgets.QComboBox()
        widgetComboBox.addItems(list_of_values)
        return widgetComboBox


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
            widgetSpinBox.setMaximum(1000)
            widgetSpinBox.setValue(value)
        return widgetSpinBox


    def setupPlotWidgets(self):
        graphics_widgets = [self.graphicsView, self.graphicsView_2,
                            self.graphicsView_3, self.graphicsView_4,
                            self.graphicsView_5, self.graphicsView_6]
        graphics_titles = ["Acceleration", "Angular Velocity", "Magnetic Field",
                           "Reference Quaternions", "Computed Quaternions", "Error"]
        for index in range(len(graphics_widgets)):
            # Setup each Graphic Widget
            graphics_widgets[index].setAntialiasing(True)
            graphics_widgets[index].showAxis('bottom', False)
            graphics_widgets[index].enableAutoRange()
            graphics_widgets[index].setTitle(graphics_titles[index])

        self.setupLookupGraph()


    def setupLookupGraph(self):
        self.graphicsView_7.setAntialiasing(True)
        self.graphicsView_7.showLabel('bottom', False)
        self.graphicsView_7.showLabel('left', False)
        self.graphicsView_7.showAxis('bottom', True)
        self.graphicsView_7.showAxis('left', False)
        self.graphicsView_7.setTitle(None)
        self.graphicsView_7.setMouseEnabled(x=False, y=False)
        # # Add region
        # self.addRegion(self.graphicsView_7)


    def updateLookupGraph(self, data, ROI=[]):
        # Get and Plot Shadow
        self.graphicsView_7.clear()
        shadow = self.getDataShadow(data.gyr)
        x_axis = range(np.shape(shadow)[0])
        upper_line = pg.PlotDataItem(x_axis, shadow[:,0])
        lower_line = pg.PlotDataItem(x_axis, shadow[:,1])
        filled_plot = pg.FillBetweenItem(upper_line, lower_line, brush=(100,100,100,200))
        self.graphicsView_7.addItem(filled_plot)
        # Add Region
        if len(ROI)!=2:
            ROI = [0, data.num_samples]
        self.addRegion(self.graphicsView_7, data, ROI)


    def addRegion(self, widget, data=None, ROI=[]):
        if data!=None:
            region = pg.LinearRegionItem(brush=(90,90,90,70))
            if len(ROI)==2:
                region.setRegion(ROI)
            # region.sigRegionChanged.connect(lambda: self.updateCoords(data, region))
            region.sigRegionChangeFinished.connect(lambda: self.updateCoords(data, region))
            widget.addItem(region, ignoreBounds=True)


    def updateCoords(self, data, region):
        if data.num_samples>0:
            minX, maxX = region.getRegion()
            if minX<0:
                minX = 0
            ROI = [int(minX), int(maxX)]
            self.updatePlots(data, ROI)


    def update_tableWidget(self, workspace):
        found_files = self.getFiles(workspace)
        num_files = len(found_files)
        self.tableWidget.setRowCount(num_files)
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
        """Summary
        
        Args:
            data (TYPE): Description
        
        Returns:
            TYPE: Description
        """
        num_rows = np.shape(data)[0]
        shadow = np.linalg.norm(data, axis=1).reshape((num_rows,1))
        shadow = np.abs(shadow - np.mean(shadow[:10])) # Remove bias (mean of first lines)
        shadow = np.hstack((shadow, -shadow))
        return shadow


    def estimatePose(self, data, estimation_info):
        """estimatePose computes the Orientation of the frame, given the IMU data
        """
        freq, beta = 100.0, 0.01
        acc = data.acc
        gyr = data.gyr
        mag = data.mag
        num_samples = data.num_samples
        algo = list(estimation_info.keys())[0]
        q = []
        if num_samples<1:
            return np.array(q)
        q = [ np.array(rb.am2q(acc[0])) ]   # Initial Pose estimation with Accelerometer
        # q = [ np.array([1., 0., 0., 0.]) ]
        if "Madgwick" in algo:
            freq = estimation_info[algo]['Frequency']
            beta = estimation_info[algo]['Beta']
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
            kp = estimation_info[algo]['Kp']
            ki = estimation_info[algo]['Ki']
            if "MARG" in algo:
                for i in range(1,num_samples):
                    q.append( rb.Mahony.updateMARG(acc[i,:], gyr[i,:], mag[i,:], q[-1], freq, kp, ki) )
            if "IMU" in algo:
                for i in range(1,num_samples):
                    q.append( rb.Mahony.updateIMU(acc[i,:], gyr[i,:], q[-1], freq, kp, ki) )
        if algo=="Gravity":
            for i in range(num_samples):
                q.append( rb.am2q(acc[i,:]) )
        if "Geomagnetic" in algo:
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


    def plotData(self, plotWidget, data, ROI=[], clearPlot=True):
        """This function takes a numPy array of size M x 3, and plots its
        contents in the main PlotWidget using pyQtGraph.
        """
        lineStyle = "Line"
        current_settings = self.plot_settings.copy()
        if len(data)<1:
            plotWidget.clear()
            return
        num_rows, num_columns = np.shape(data)
        if num_columns < 1:
            plotWidget.clear()
            return
        if len(ROI)!=2:
            ROI = [0, num_rows]
        if clearPlot:
            plotWidget.clear()
        try:
            used_colors = colors[:num_columns]
            if num_columns==4:
                used_colors = [colors[6]] + colors[:num_columns]
            for index in range(num_columns):
                self.plotDataLine(plotWidget, data[ROI[0]:ROI[1],index], style="Line", color=used_colors[index])
            plotWidget.getViewBox().setAspectLocked(lock=False)
            plotWidget.autoRange()
            # Add Grid
            plotWidget.showGrid(x=current_settings["Grid-X"], y=current_settings["Grid-Y"])
        except:
            print(self, "Invalid File", "The selected file does not have valid data.")
        self.plot_settings = current_settings.copy()


    def updatePlots(self, data, ROI=[]):
        # Get and Plot Shadow
        self.plotData(self.graphicsView, data.acc, ROI)
        self.plotData(self.graphicsView_2, data.gyr, ROI)
        self.plotData(self.graphicsView_3, data.mag, ROI)
        self.plotData(self.graphicsView_4, data.qts, ROI)


class Data:
    def __init__(self, fileName):
        self.file = fileName
        self.data, self.headers = self.getData(self.file)
        self.num_samples = len(self.data)
        self.header_info = self.idLabelGroups(self.headers)
        self.acc, self.gyr, self.mag, self.qts, self.pos = [], [], [], [], []
        self.timestamps, self.frequencies = [], []
        self.allotData(self.data, self.header_info)
        # Identify and append frequencies
        if len(self.timestamps)>0:
            num_timestamps = np.shape(self.timestamps)[1]
            for idx in range(num_timestamps):
                self.frequencies.append(self.idFrequency(self.timestamps, timer_index=idx, units='ns'))
            # self.frequencies.append(self.idFrequency(self.timestamps, timer_index=0, units='ns'))
            # self.frequencies.append(self.idFrequency(self.timestamps, timer_index=1, units='ns'))

    def getData(self, fileName, data_type='float'):
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
            with open(fileName, 'r') as f:
                read_data = f.readlines()
            # Read and store Headers in a list of strings
            header_rows = countHeaders(read_data)
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

    def idLabelGroups(self, found_headers, single_group=True):
        labels2use = []
        all_group_indices = []
        data_info = {}
        for dset_lbl in all_labels:
            all_group_labels = []
            group_indices = []
            headers_keys = list(all_labels[dset_lbl].keys())
            # print("headers_keys:", headers_keys)
            for i in range(len(headers_keys)):
                header_group = headers_keys[i]
                data_info[header_group] = {}
                group_labels = all_labels[dset_lbl][header_group]
                group_indices.append(self.matchIndices(found_headers, group_labels))
                all_group_labels += group_labels
                data_info[header_group]["labels"] = group_labels
                data_info[header_group]["indices"] = group_indices[i]
            if all(x in found_headers for x in all_group_labels):
                labels2use.append(dset_lbl)
                all_group_indices.append(group_indices)
                break
        return data_info

    def matchIndices(self, all_headers, requested_headers):
        requested_indices = []
        for header in requested_headers:
            if header in all_headers:
                requested_indices.append(all_headers.index(header))
        return requested_indices

    def allotData(self, data, header_info):
        try:
            labels_list = list(header_info.keys())
            for label in labels_list:
                if label == "Accelerometers":
                    self.acc = data[:,header_info[label]["indices"]]
                if label == "Gyroscopes":
                    self.gyr = data[:,header_info[label]["indices"]]
                if label == "Magnetometers":
                    self.mag = data[:,header_info[label]["indices"]]
                if label == "Quaternions":
                    self.qts = data[:,header_info[label]["indices"]]
                if label == "Position":
                    self.pos = data[:,header_info[label]["indices"]]
                if label == "Timestamps":
                    print("Updating the timestamps")
                    self.timestamps = data[:,header_info[label]["indices"]]
        except:
            print("[WARN] File '{}' has no valid data to allocate.".format(self.file))

    def idFrequency(self, data_array, timer_index=0, units='s'):
        timestamps = data_array[:,timer_index]
        diffs = np.diff(timestamps)
        mean = np.mean(diffs)
        if units=='ms':
            mean *= 1e-3
        if units=='us':
            mean *= 1e-6
        if units=='ns':
            mean *= 1e-9
        return 1.0 / mean


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