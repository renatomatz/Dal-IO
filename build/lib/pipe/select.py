"""Defines various ways of getting a subset of data based on some condition"""

from itertools import product

import numpy as np
import pandas as pd

from dalio.pipe import Pipe

from dalio.validator import IS_PD_DF, IS_PD_TS, HAS_COLS

from dalio.util import (
    process_cols,
    process_date,
    filter_levels,
    extract_level_names_dict,
    extract_cols,
)


class ColRename(Pipe):
    """A pipeline stage that renames a column or columns.

    Attributes:
        rename_map (dict): Maps old column names to new ones.

    Example
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[8,'a'],[5,'b']], [1,2], ['num', 'char'])
        >>> pdp.ColRename({'num': 'len', 'char': 'initial'}).apply(df)
           len initial
        1    8       a
        2    5       b
    """

    def __init__(self, map_dict):
        super().__init__()
        self._map_dict = map_dict

    def transform(self, data, **kwargs):

        return data.rename(
            self._map_dict, 
            axis=1,
        )

    def copy(self, *args, **kwargs):
        return super().copy(
            *args,
            map_dict=self._map_dict,
            **kwargs,
        )


class _ColSelection(Pipe):

    def __init__(self, columns):
        super().__init__()

        if isinstance(columns, dict):
            for level, col in columns.items():
                self._source\
                    .add_desc(HAS_COLS(col, level=level))
        elif isinstance(columns, (list, str)):
            self._source\
                .add_desc(HAS_COLS(columns))
        else:
            self._source\
                .add_desc(IS_PD_DF())

        self._columns = process_cols(columns)

    def copy(self, *args, **kwargs):
        return super().copy(
            *args,
            columns=self._columns,
            **kwargs
        )


class _ColValSelection(_ColSelection):

    def __init__(self, values, columns=None):
        super().__init__(columns)

        self._values = values

    def copy(self, *args, **kwargs):
        return super().copy(
            *args,
            values=self._values,
            **kwargs,
        )


class ColSelect(_ColSelection):
    """Select columns"""

    def transform(self, data, **kwargs):
        """Selects the specified columns or returns data as is if no column
        was specified.

        Returns:
            Data of the same format as before but only only containing the
            specified columns.
        """
        cols = filter_levels(
            extract_level_names_dict(data),
            self._columns
        )

        return extract_cols(data, cols)


class ColDrop(_ColSelection):
    """A pipeline stage that drops columns by name.

    Parameters
    ----------
    columns : str, iterable or callable
        The label, or an iterable of labels, of columns to drop. Alternatively,
        columns can be assigned a callable returning bool values for
        pandas.Series objects; if this is the case, every column for which it
        return True will be dropped.

    Example
    -------
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[8,'a'],[5,'b']], [1,2], ['num', 'char'])
        >>> pdp.ColDrop('num').apply(df)
          char
        1    a
        2    b
    """

    def transform(self, data, **kwargs):

        all_cols = extract_level_names_dict(data)

        drop_cols = filter_levels(
            all_cols,
            self._columns
        )

        if not isinstance(drop_cols, dict):
            drop_cols = {0: drop_cols}

        cols = {level: list(set(ac).difference(dc))
                for (level, ac), (level, dc)
                in zip(all_cols.items(), drop_cols.items())}

        return extract_cols(data, cols)


class DateSelect(Pipe):
    """Select a date range.

    This is commonly left as a local variable to control date range being
    used at a piece of a graph.

    Attributes:
        _start (pd.Timestamp): start date.
        _end (pd.Timestamp): end date.
    """

    _start: pd.Timestamp
    _end: pd.Timestamp

    def __init__(self, start=None, end=None):
        """Initialize instance, processes and sets dates.

        Defines source data as a pandas time series.
        """
        super().__init__()

        self._source\
            .add_desc(IS_PD_TS())

        self._start = process_date(start)
        self._end = process_date(end)

    def transform(self, data, **kwargs):
        """Slices time series into selected date range.

        Returns:
            Time series of the same format as input containing a subset of
            the original dates.
        """
        return data.loc[self._start:self._end]

    def copy(self, *args, **kwargs):
        return super().copy(
            *args,
            start=self._start,
            end=self._end,
            **kwargs
        )

    def set_start(self, start):
        """Set the _start attribute"""
        self._start = process_date(start)
        return self

    def set_end(self, end):
        """Set the _end attribute"""
        self._end = process_date(end)
        return self


class DropNa(Pipe):
    """A pipeline stage that drops null values.

    Supports all parameter supported by pandas.dropna function.

    Example:
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[1,4],[4,None],[1,11]], [1,2,3], ['a','b'])
        >>> pdp.DropNa().apply(df)
           a     b
        1  1   4.0
        3  1  11.0
    """

    def __init__(self, **kwargs):
        super().__init__()

        self._source\
            .add_desc(IS_PD_DF())

        self._drop_na_kwargs = kwargs

    def transform(self, data, **kwargs):
        return data.dropna(**self._drop_na_kwargs)


class RowDrop(_ColSelection):
    """A pipeline stage that drop rows by callable conditions.

    Parameters
    ----------
    conditions : list-like or dict
        The list of conditions that make a row eligible to be dropped. Each
        condition must be a callable that take a cell value and return a bool
        value. If a list of callables is given, the conditions are checked for
        each column value of each row. If a dict mapping column labels to
        callables is given, then each condition is only checked for the column
        values of the designated column.
    reduce : 'any', 'all' or 'xor', default 'any'
        Determines how row conditions are reduced. If set to 'all', a row must
        satisfy all given conditions to be dropped. If set to 'any', rows
        satisfying at least one of the conditions are dropped. If set to 'xor',
        rows satisfying exactly one of the conditions will be dropped. Set to
        'any' by default.
    columns : str or iterable, optional
        The label, or an iterable of labels, of columns. Optional. If given,
        input conditions will be applied to the sub-dataframe made up of
        these columns to determine which rows to drop.

    Example
    -------
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[1,4],[4,5],[5,11]], [1,2,3], ['a','b'])
        >>> pdp.RowDrop([lambda x: x < 2]).apply(df)
           a   b
        2  4   5
        3  5  11
        >>> pdp.RowDrop({'a': lambda x: x == 4}).apply(df)
           a   b
        1  1   4
        3  5  11
    """

    _REDUCERS = {
        'all': all,
        'any': any,
        'xor': lambda x: sum(x) == 1
    }

    def _row_condition_builder(self):
        if isinstance(self._conditions, dict):
            def _row_cond(row):
                res = [cond(row[lbl])
                       for lbl, cond in self._conditions.items()]
                return self._reducer(res)
        elif hasattr(self._conditions, "__iter__"):
            def _row_cond(row):
                res = [self._reducer(row.apply(cond))
                       for cond in self._conditions]
                return self._reducer(res)
        else:
            def _row_cond(row):
                return self._reducer(row.apply(self._conditions))

        return _row_cond

    def __init__(self, conditions, columns=None, reduce_strat=None):

        self._reducer = RowDrop._REDUCERS.get(reduce_strat, any)

        if isinstance(conditions, dict):
            valid = all([callable(cond) for cond in conditions.values()])
            if not valid:
                raise ValueError(
                    "Condition dicts given to RowDrop must map to callables!")
            columns = list(conditions.keys())
        elif hasattr(conditions, "__iter__"):
            valid = all([callable(cond) for cond in conditions])
            if not valid:
                raise ValueError(
                    "RowDrop condition lists can contain only callables!")
        elif not callable(conditions):
            raise ValueError("RowDrop condition must be callable!")

        self._conditions = conditions

        super().__init__(columns)

    def transform(self, data, **kwargs):

        inter_df = extract_cols(data,
                                filter_levels(
                                    extract_level_names_dict(data),
                                    self._columns
                                ))

        return data.copy()[
            ~inter_df.apply(
                self._row_condition_builder(),
                axis=1
            )
        ]


class ValDrop(_ColValSelection):
    """A pipeline stage that drops rows by value.

    Parameters
    ----------
    values : list-like
        A list of the values to drop.
    columns : str or list-like, default None
        The name, or an iterable of names, of columns to check for the given
        values. If set to None, all columns are checked.

    Example
    -------
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[1,4],[4,5],[18,11]], [1,2,3], ['a','b'])
        >>> pdp.ValDrop([4], 'a').apply(df)
            a   b
        1   1   4
        3  18  11
        >>> pdp.ValDrop([4]).apply(df)
            a   b
        3  18  11
    """

    def __init__(self, values, columns=None):
        if not isinstance(values, (dict, list)):
            values = [values]

        super().__init__(values, columns)

    def transform(self, data, **kwargs):

        levels = extract_level_names_dict(data)

        cols_to_check = filter_levels(
            levels,
            self._columns
        )

        # if data has a multiindex
        if data.columns.nlevels > 1 \
        and not isinstance(cols_to_check[0], tuple):

            if not isinstance(cols_to_check, dict):
                levels[0] = cols_to_check
                cols_to_check = levels

            # check the tuple combinations of selected levels
            cols_to_check = product(*cols_to_check.values())

        for col in cols_to_check:
            # keep those values that are not (~) in self._values
            data = data[~data[col].isin(self._values)]

        return data


class ValKeep(_ColValSelection):
    """A pipeline stage that keeps rows by value.

    Parameters
    ----------
    values : list-like
        A list of the values to keep.
    columns : str or list-like, default None
        The name, or an iterable of names, of columns to check for the given
        values. If set to None, all columns are checked.

    Example
    -------
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[1,4],[4,5],[5,11]], [1,2,3], ['a','b'])
        >>> pdp.ValKeep([4, 5], 'a').apply(df)
           a   b
        2  4   5
        3  5  11
        >>> pdp.ValKeep([4, 5]).apply(df)
           a  b
        2  4  5
    """

    def __init__(self, values, columns=None):
        if not isinstance(values, (dict, list)):
            values = [values]

        super().__init__(values, columns)


    def transform(self, data, **kwargs):

        levels = extract_level_names_dict(data)

        cols_to_check = filter_levels(
            levels,
            self._columns
        )

        # if data has a multiindex
        if data.columns.nlevels > 1 \
        and not isinstance(cols_to_check[0], tuple):

            if not isinstance(cols_to_check, dict):
                levels[0] = cols_to_check
                cols_to_check = levels

            # check the tuple combinations of selected levels
            cols_to_check = product(*cols_to_check.values())

        for col in cols_to_check:
            data = data[data[col].isin(self._values)]

        return data


class FreqDrop(_ColValSelection):
    """A pipeline stage that drops rows by value frequency.

    Parameters
    ----------
    threshold : int
        The minimum frequency required for a value to be kept.
    column : str
        The name of the colums to check for the given value frequency.

    Example
    -------
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[1,4],[4,5],[1,11]], [1,2,3], ['a','b'])
        >>> pdp.FreqDrop(2, 'a').apply(df)
           a   b
        1  1   4
        3  1  11
    """

    def transform(self, data, **kwargs):

        # TODO: make this a function and remove copies
        levels = extract_level_names_dict(data)

        cols_to_check = filter_levels(
            levels,
            self._columns
        )

        # if data has a multiindex
        if data.columns.nlevels > 1 \
        and not isinstance(cols_to_check[0], tuple):

            if not isinstance(cols_to_check, dict):
                levels[0] = cols_to_check
                cols_to_check = levels

            # check the tuple combinations of selected levels
            cols_to_check = product(*cols_to_check.values())

        i_to_keep = set()
        n_index = np.arange(data.shape[0])
        for col in cols_to_check:
            valcount = data[col].value_counts()
            vals_to_keep = valcount[valcount >= self._values].index
            i_to_keep.update(n_index[data[col].isin(vals_to_keep)])

        return data.copy().iloc[[*i_to_keep]]


class ColReorder(_ColSelection):
    """A pipeline stage that reorders columns.

    Attributes:
        positions (dict): A mapping of column names to their desired positions
            after reordering Columns not included in the mapping will maintain
            their relative positions over the non-mapped colums.

    Example:
        >>> import pandas as pd; import pdpipe as pdp;
        >>> df = pd.DataFrame([[8,4,3,7]], columns=['a', 'b', 'c', 'd'])
        >>> pdp.ColReorder({'b': 0, 'c': 3}).apply(df)
           b  a  d  c
        0  4  8  7  3
    """

    def __init__(self, map_dict, level=0):
        # TODO: make col maps a thing again
        super().__init__({level: [*map_dict.keys()]})

        self._map_dict = map_dict
        self._level = level

    def transform(self, data, **kwargs):

        all_cols = extract_level_names_dict(data)

        for col, pos in self._map_dict.items():
            all_cols[self._level].remove(col)
            # this works for edge cases like last cols because of
            # the remove
            all_cols[self._level] = all_cols[self._level][:pos] \
                + [col] \
                + all_cols[self._level][pos:]

        if data.columns.nlevels > 0:
            all_cols = pd.MultiIndex.from_tuples(
                [*product(*all_cols.values())]
            )
        else:
            all_cols = pd.Index(all_cols[0])

        inter_df = data.copy()
        inter_df.columns = all_cols

        return inter_df

    def copy(self, *args, **kwargs):
        return super().copy(
            *args,
            map_dict=self._map_dict,
            level=self._level,
            **kwargs,
        )
