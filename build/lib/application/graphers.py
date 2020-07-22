"""Applications based on graphing input data"""

from itertools import product

import numpy as np

from dalio.base.constants import RETURNS, MAX_EXEDENCE
from dalio.base import _Builder
from dalio.application import Application
from dalio.validator import IS_PD_DF, HAS_COLS, IS_PD_TS, HAS_ATTR
from dalio.util import process_cols


class Grapher(Application):
    """Base grapher class.

    Does basic graphing, assuming data does not require any processing before
    being passed onto an external grapher.

    This Application has one source: data_in. The data_in source gets
    internal data to be graphed.

    This Application has one output: data_out. The data_out output represents
    an external graph.
    """

    def __init__(self):
        """Initializes instance, sources and output."""
        super().__init__()

        self._init_source([
            "data_in",
        ])

        self._init_output([
            "data_out",
        ])

    def run(self, **kwargs):
        """Gets data input and plots it"""
        data = self._source_from("data_in", **kwargs)

        graph_opts = kwargs.get("graph_opts", {})

        self._get_output("data_out").plot(data, **graph_opts)
        return self._get_output("data_out").request()

    def reset_out(self):
        """Reset the output graph. Figure instances should implement the
        .reset() method.
        """
        self._get_output("data_out").reset()
        return self


class MultiGrapher(Application, _Builder):
    """Grapher for multiple inputs taking in the same keyword arguments.

    This is useful to greate subplots of the same data processed in
    different ways. Sources are the data inputs and pieces are their kinds,
    args and kwargs.

    This applicaiton can N sources and pieces, where N is the total number of
    graphs.
    """

    def __init__(self, rows, cols):
        """Initialize instance.

        This generates one source and piece per figure (product of rows and
        cols) and one output.

        Args:
            rows (int): number of rows (starting at one).
            cols (int): number of cols (starting at one).
        """

        super().__init__()

        self._init_source(
            product(
                range(rows),
                range(cols)
            ),
        )

        self._init_output([
            "data_out",
        ])

        self._init_piece(
            product(
                range(rows),
                range(cols)
            ),
        )

    def run(self, **kwargs):
        """Gets data input from each source and plots it using the set
        information in each piece
        """
        for coord in self._source:

            data = self._source_from(coord, **kwargs)

            if data is None:
                continue

            data, kind, f_kwargs = self.build_model(data, coord=coord)

            graph_opts = kwargs.get("graph_opts", {})
            graph_opts.update(f_kwargs)

            self._get_output("data_out")\
                .plot(data, coord, kind=kind, **graph_opts)

        return self._get_output("data_out").request()

    def build_model(self, data, **kwargs):
        """Return data unprocessed"""
        plot = self._pieces[kwargs.get("coord", None)]
        return data, plot.name, plot.kwargs


class PandasXYGrapher(Grapher):
    """Graph data from a pandas dataframe with option of selecting columns
    used as axis

    Attributes:
        _x (str): name of column to be used for x-axis.
        _y (str): name of column to be used for y-axis.
        _legend (str, None): legend position. None by default
    """

    _x: str
    _y: str
    _legend: str

    def __init__(self, x=None, y=None, legend=None):
        """Initialize instance.

        Defines data_in source as a pandas dataframe. If x is set, it must
        be a column in this dataframe; same applies to y.

        Args:
            _x (str): name of column to be used for x-axis. Optional. None by
                default. If None, index is used.
            _y (str): name of column to be used for y-axis. Optional. None by
                default. If None, all columns are used.
            _legend (str, None): legend position. Optional. None by default.

        Raises:
            TypeError: if specified x or legend is not a string or if
                specified y is not string or list of strings.
        """
        super().__init__()

        self._get_source("data_in")\
            .add_desc(IS_PD_DF())

        if isinstance(x, (str, tuple)):
            self._get_source("data_in")\
                .add_desc(HAS_COLS(x))
            self._x = process_cols(x)
        elif x is None:
            self._x = process_cols(x)
        else:
            raise TypeError(f"argument x must be None or of type {str} \
                    not {type(x)}")

        if isinstance(y, (str, tuple, list)):
            self._get_source("data_in")\
                .add_desc(HAS_COLS(y))

            self._y = process_cols(y)

        elif y is None:
            self._y = y

        else:
            raise TypeError(f"argument y must be None or of type \
                {str} or {list} not {type(y)}")

        if legend is None or isinstance(legend, str):
            self._legend = legend
        else:
            raise TypeError(f"argument legend must be None or of type \
                {str} not {type(legend)}")

    def run(self, **kwargs):
        """Get data, separate columns and feed it to data output graph"""
        data = self._source_from("data_in", **kwargs)

        x = data[self._x].to_numpy() if self._x is not None else data.index
        y = data[self._y] if self._y is not None else data

        graph_opts = kwargs.get("graph_opts", {})

        self._get_output("data_out").plot(data=(x, y), **graph_opts)

        fig = self._get_output("data_out").request()

        if self._legend is not None:
            fig.legend(labels=y.columns, loc=self._legend)

        fig.show()
        return fig


class PandasTSGrapher(PandasXYGrapher):
    """Graphs a pandas time series

    Same functionality as parent class with stricter inputs.
    """

    def __init__(self, y=None, legend=None):
        """Initialize instance.

        Initialization based on parent class, allowing x to be the time
        series index.

        Defines data_in source to be a pandas time series on top of parent
        class definitions.
        """
        super().__init__(y=y, legend=legend)

        self._get_source("data_in")\
            .add_desc(IS_PD_TS())


class PandasMultiGrapher(MultiGrapher):
    """Multigrapher with column selection mechanisms

    In this MultiGrapher, you can select any x, y and z columns as piece
    kwargs and they will be interpreted during the run. Keep in mind that
    this allows for any combination of these layered one on top of each other
    regardless of name. If you specify an "x" and a "z", the "z" column will
    be treated like a "y" column.

    There are also no interpretations of what
    is to be graphed, and thus all wanted columns should be specified.

    There is one case for indexes, where the x_index, y_index or z_index
    keyword arguments can be set to True.
    """

    def build_model(self, data, **kwargs):
        """Process data columns"""

        data, kind, f_kwargs = super().build_model(data, **kwargs)
        cols = []

        for ax in "xyz":
            ax, ax_index = \
                f_kwargs.pop(ax, None), \
                f_kwargs.pop(ax+"_index", False)

            if ax is None:
                if ax_index:
                    cols.append(data.index)
            else:
                cols.append(data.loc(axis=1)[ax])

        return tuple(cols), kind, f_kwargs


class ForecastGrapher(Grapher):
    """Application to graph data and a forecast horizon

    This Application has two sources data_in and forecast_in. The data-in
    source is explained in Grapher. The forecast_in source gets a forecast
    data to be graphed.
    """

    def __init__(self):
        """Initialize instance.

        Both data_in and forecast_in are described as pandas time series
        data frames.
        """

        super().__init__()

        self._init_source([
            "forecast_in"
        ])

        self._get_source("data_in")\
            .add_desc(IS_PD_DF())\
            .add_desc(IS_PD_TS())

        self._get_source("forecast_in")\
            .add_desc(IS_PD_DF())\
            .add_desc(IS_PD_TS())

    def run(self, **kwargs):
        """Get data, its forecast and plot both"""
        # TODO: Parallelize
        data = self._source_from("data_in", **kwargs)
        forecast = self._source_from("forecast_in", **kwargs)

        y = data.join(forecast, how="outer", sort=True)

        labels = [kwargs.get("data_label", "Data"),
                  kwargs.get("forecast_label", "Forecast")]

        y.columns = labels

        graph_opts = kwargs.get("graph_opts", {})

        self._get_output("data_out").plot(x=y.index, y=y, **graph_opts)
        fig = self._get_output("data_out").request()
        return fig


class VaRGrapher(Grapher):
    """Application to visualize Value at Risk"""

    def __init__(self):
        """Initialize instance.

        Defines data_in as having columns named RETURNS and MAX_EXEDENCE.
        """
        super().__init__()

        self._get_source("data_in")\
            .add_desc(HAS_COLS([RETURNS, MAX_EXEDENCE]))

        # use regex to check for % sign in columns

    def run(self, **kwargs):
        """Get value at risk data, plot returns, value at risk lines and
        exceptions at their maximum exedence.

        Thank you for the creators of the arch package for the amazing
        visulaization idea!
        """
        VaR = self._source_from("data_in", **kwargs)

        returns = VaR[RETURNS]
        exedence = VaR[MAX_EXEDENCE]
        VaR.drop([RETURNS, MAX_EXEDENCE], axis=1, inplace=True)

        # x axis is shared for all points
        x = VaR.index

        graph_opts = kwargs.get("graph_opts", {})

        line_opts = graph_opts.copy()
        line_opts.update(
            linewidth=0.5,
            alpha=0.6
        )

        # plot value at risk lines
        self._get_output("data_out").plot((x, VaR), **graph_opts)

        # add exedence as color
        scatter_opts = graph_opts.copy()
        scatter_opts.update(
            c=exedence,
            alpha=0.5
        )

        self._get_output("data_out").plot(
            (x, -returns),
            kind="scatter",
            **scatter_opts)

        fig = self._get_output("data_out").request(query="GET")
        return fig


class LMGrapher(PandasXYGrapher):
    """Application to graph data and a linear model fitted to it.

    This Application has two sources data_in and linear_model. The data-in
    source is explained in Grapher. The linear_model source is a fitted
    linear model with intercept and coefficient data.

    Attributes:
        _legend (str, None): legend position on graph.
    """

    def __init__(self, x=None, y=None, legend=None):
        """Initialize instance.

        Defines data_in source as a pandas data frame.
        Defines linear_model source as having attributes 'coef_' and
        'intercept_'

        Args:
            x, y: columns used for the x and y axes
            legend (str, None): Legend position on graph. Optional. None by
                default. If None, legend will not be included.

        Raises:
            TypeError: if legend is neither none or string.
        """
        super().__init__(x=x, y=y, legend=legend)

        self._init_source([
            "linear_model"
        ])

        self._get_source("data_in")\
            .add_desc(IS_PD_DF())

        self._get_source("linear_model")\
            .add_desc(HAS_ATTR(["coef_", "intercept_"]))

    def run(self, **kwargs):
        """Get data, its fitted coefficients and intercepts and graph them."""

        data = self._source_from("data_in", **kwargs)
        lm = self._source_from("linear_model", **kwargs)

        graph_opts = kwargs.get("graph_opts", {})

        x = data[self._x].to_numpy() if self._x is not None else data.index
        linspace = x if self._x is not None else np.arange(data.shape[0]) + 1

        data = data[self._y] if self._y is not None else data

        for i, col in enumerate(data):

            # graph returns
            self._get_output("data_out").plot(
                (x, data[col]),
                kind="scatter",
                s=1.5,
                **graph_opts)

            # graph fitted lm
            self._get_output("data_out").plot(
                (x, linspace*lm.coef_[i] + lm.intercept_[i]),
                kind="line",
                **graph_opts)

        fig = self._get_output("data_out").request()

        if self._legend is not None:
            fig.legend(labels=data.columns, loc=self._legend)

        fig.show()
        return fig
