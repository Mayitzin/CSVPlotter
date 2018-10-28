"""
Test Script for Drag and Drop events in PyQt.

See Also
--------
- https://pythonspot.com/pyqt5-drag-and-drop/
- https://www.tutorialspoint.com/pyqt/pyqt_drag_and_drop.htm
- http://doc.qt.io/qt-5/qmimedata.html
- http://doc.qt.io/qt-5/dnd.html
"""

import sys
# import pyqtgraph as pg


# def dragEnterEvent(ev):
#     event_mimeData = ev.mimeData()
#     print(event_mimeData.text())
#     ev.accept()

# def dropEvent(event):
#     print("Got drop!")

# def main(application):
#     sys.exit(application.exec_())

# # Create Application
# app = pg.QtGui.QApplication([])

# # Create DRAG dialog with list
# l = pg.QtGui.QListWidget()
# l.addItem('Drag me')
# l.setDragEnabled(True)
# l.show()

# # Create DROP window
# win = pg.GraphicsWindow()
# win.dragEnterEvent = dragEnterEvent
# # Create Plot
# plot = pg.PlotItem()
# plot.setAcceptDrops(True)
# plot.dropEvent = dropEvent
# win.addItem(plot)
# # Show Window
# win.show()


# if __name__ == "__main__":
#     main(app)



from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QLabel
from PyQt5.QtCore import pyqtSlot

class App(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 drag and drop - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 320
        self.height = 60
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        editBox = QLineEdit('Drag this', self)
        editBox.setDragEnabled(True)
        editBox.move(10, 10)
        editBox.resize(100,32)

        button = CustomLabel('Drop here.', self)
        button.move(130,15)

        self.show()

    @pyqtSlot()
    def on_click(self):
        print('PyQt5 button click')

class CustomLabel(QLabel):

    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        self.setText(e.mimeData().text())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
