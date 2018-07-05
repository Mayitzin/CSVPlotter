# CSV Plotter

Small application to read, parse and plot the data contained in a CSV file.

It is mainly intended to be a tool to represent the data of inertial sensors,
and their derived computations (position, velocity, orientation, etc.)

## Features

- [x] Implementation with [Qt5](https://www.qt.io/).
- [ ] Automatically identify columns, given the required header labels.
- [ ] 3D Visualization of movement and orientation.

**Python**

+ Implemented with [Python 3](https://www.python.org/).
+ Uses [NumPy](http://www.numpy.org/) for a fast sort of data.
+ [PyQtGraph](http://pyqtgraph.org/) is the main plotting library for better speed.
+ Inclusion of [matplotlib](https://matplotlib.org/) as alternative for pretty plots.
+ ToDo:
    - Identify headers of more than one line.
    - Select format of lines (color, shape, etc.)
    - Select files to plot.
    - Select elements of file to plot.  
    - Test with [vtk](https://www.vtk.org/features-language-agnostic/) wrapper.

**C++**

+ It will be implemented, once the prototype in Python is completed.
+ The most likely plotting library will be [VTK](https://www.vtk.org/).
+ For better performance, [OpenGL](https://www.opengl.org/) is considered.
