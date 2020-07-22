"""Define classes for image pieces

Images, be it a plot, picture or video are considered external outputs as the
figure itself is not contained in the python session, and must be shown in a
screen or server.
"""
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pypfopt import CLA

from dalio.external import External

from dalio.util import plot_efficient_frontier, \
    plot_covariance, plot_weights


class _Figure(External):
    """Base Figure class

    These serve to implement the basic logic of a figure, and are not limited
    to any specific python package. Python packages should be standardazied
    in these classes to take in these broad commands.

    Attributes:
        _connection: figure object dealt with by this class
        _figsize (tuple): figure size ratio
    """

    _connection: Any
    _figsize: tuple

    def __init__(self, figsize=None):
        """Initializes instance and set empty figure"""
        super().__init__()
        self._figsize = figsize
        self.reset()

    def request(self, **kwargs):
        """Processes a request based on the figure.

        Args:
            **kwargs: additional request options.
        """
        query = kwargs.get("query", None)
        if query == "GET":
            return self._connection
        else:
            return self._connection

    def check(self):
        """Check if there is a figure to return"""
        return self._connection is not None

    def plot(self, data, kind=None, **graph_opts):
        """Plots data on the figure.

        Args:
            data: data to be used in the plot.
            kind: kind of plot to be plotted. None by default.
            **graph_opts: optional graphing options
        """
        raise NotImplementedError()

    def reset(self):
        """Resets figure to default, empty state"""
        self._connection = None


class _MultiFigure(_Figure):
    """Base MultiFigure class

    These serve to implement the basic logic of a plotting multiple figures.
    Python packages should be standardazied in these classes to take in
    these broad commands.

    Attributes:
        _connection: figure object dealt with by this class
        _loc: way of localizing any of the multiple figures
    """

    _connection: Any
    _loc: Any

    def plot(self, data, coords=None, kind=None, **graph_opts):
        """Plots data on the figure.

        Args:
            data: data to be used in the plot.
            coords: coordinates or location of a target graph
            kind: kind of plot to be plotted. None by default.
            **graph_opts: optional graphing options
        """
        raise NotImplementedError()


class PyPlotGraph(_Figure):
    """Figure from the matplotlib.pyplot package.

    Attributes:
        _connection (matplotlib.pyplot.Figure): graph figure
        _axes (matplotlib.axes._subplots.AxesSubplot): figure axis
    """

    _connection: plt.Figure
    _axis: object

    def request(self, **kwargs):
        """Processed request for data.

        This adds the SHOW request to the base class implementation
        """
        query = kwargs.get("query", None)
        if query == "SHOW":
            self._connection.show()
            return None
        else:
            return super().request(**kwargs)

    def plot(self, data, kind=None, **graph_opts):
        """Plot x onto the x-axis and y onto the y-axis, if applicable.

        Args:
            data (matrix or array like): either data to be plotted on the x
                axis or a tuple of x and y data to be plotted or the x and y
                axis.
            kind (str): kind of graph.
            **graph_opts: plt plotting arguments for this kind of graph.
        """
        x, y = data if len(data) == 2 else (data, None)

        if kind in ["hist", "histogram"]:
            self._axis.hist(x, **graph_opts)
        elif kind == "line":
            self._axis.plot(x, y, **graph_opts)
        elif kind == "scatter":
            self._axis.scatter(x, y, **graph_opts)
        else:
            self._axis.plot(x, y, **graph_opts)

        if graph_opts.get("legend", None) is not None:
            self._axis.legend()

    def reset(self):
        """Set connection and axes to a single figure and axis"""
        self._connection, self._axis = plt.subplots(1, 1,
                                                    figsize=self._figsize)


class PySubplotGraph(_MultiFigure):
    """A matplotlib.pyplot.Figure containing multiple subplots.

    This has a set number of axes, rows and columns which can be accessed
    individually to have data plotted on. These will often be used inside of
    applications that require more than one subplot all contained in the
    same instance.

    Attributes:
        _rows (int): number of rows in the subplot
        _cols (int): number of columns in the subplot
        _loc (np.array): array of the figure's axes
    """

    _rows = int
    _cols = int
    _loc: np.ndarray

    def __init__(self, rows, cols, figsize=None):
        """Initialize instance, check and set rows and columns

        Args:
            rows (int): number of subplot rows
            cols (int): number of subplot columns
        """
        self._rows = rows
        self._cols = cols
        super().__init__(figsize=figsize)

    def plot(self, data, coords=None, kind=None, **graph_opts):
        """Plot on a specified subplot axis

        Args:
            coords (tuple): tuple of subplot coordinates to plot data

        Raises:
            ValueError: if coordinates are out of range.
        """

        if coords[0] < self._rows and coords[1] < self._cols:
            if len(data) == 3:
                self.get_loc(coords).plot(data[0], data[1], data[2],
                                          **graph_opts)
            if len(data) == 2:
                if kind == "line":
                    self.get_loc(coords).plot(data[0], data[1], **graph_opts)
                elif kind == "scatter":
                    self.get_loc(coords).scatter(data[0], data[1],
                                                 **graph_opts)
            if len(data) == 1:
                if kind in ["hist", "histogram"]:
                    self.get_loc(coords).hist(data[0].to_numpy(), **graph_opts)
            else:
                ValueError("No data was provided")
        else:
            raise ValueError(f"Invalid indexes, this figure has {self._rows} \
                rows and {self._cols} columns")

    def reset(self):
        """Resets figure and all axes"""
        self._connection, self._loc = plt.subplots(self._rows, self._cols,
                                                   figsize=self._figsize)

    def get_loc(self, coords):
        """Gets a specific axis from the _loc attribute at given
        coordinates
        """
        i, j = coords
        return self._loc[i, j]

    def make_manager(self, coords):
        """Create a SubPlotManager to manage this instance's subplots"""
        return SubplotManager(self, coords)


class SubplotManager(PyPlotGraph):
    """A manager object for treating a subplot axis like a single plot.

    Applications will often take in single plots and have their functionality
    catered to such. Subplots, while useful, will often be used for specific
    applications. A subplot manager allows you to create multiple subplots
    and pass each one individually onto applications that take a single
    subplot axis and still have access to the underlying figure.
    """

    def __init__(self, subplot, coords):
        """Initialize instance, check and assimilate managed subplot.

        Args:
            subplot (PySubplotGraph): subplot instance containing axis to be
                managed.
            coords (tuple): tuple containing row and column of the subplot
                to manage

        Raises:
            TypeError: if specified subplot is not a PySubplotGraph.
        """
        if not isinstance(subplot, PySubplotGraph):
            TypeError("Subplot managers take in PySubplotGraph instances")

        self._figure = subplot.request(query="GET")
        self._axis = subplot.get_axis(coords)
        super().__init__()

    def reset(self):
        self._axis.cla()


class PyPfOptGraph(PyPlotGraph):
    """Graphs data from the PyPfOpt package"""

    def plot(self, data, coords=None, kind=None, **kwargs):
        """Graph data from pypfopt

        Args:
            data: plottable data from pypfopt package

        Raises:
            TypeError: if data is not of a plottable class from pypfopt
        """
        if isinstance(data, CLA):
            plot_efficient_frontier(data, ax=self._axis, **kwargs)
        elif isinstance(data, (np.ndarray, pd.DataFrame)):
            plot_covariance(data, ax=self._axis, **kwargs)
        elif isinstance(data, dict):
            plot_weights(data, ax=self._axis, **kwargs)
        else:
            raise TypeError("Input data cannot be plotted in pypfopt")
