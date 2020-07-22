"""Define extra utility classes used throughout the package

These classes implement certain interfaces used in specific cases and are not
constrained an object's parent class.
"""

from typing import Dict, List, Union, Any

from collections import namedtuple


class _Builder:
    """Interface for setting and assembling pieces.

    Builder instances are meant, as the name suggests, to be set and built at
    command. This is necessary in the context of graphs as the vast majority
    of settings (pieces) should be specified before actually running the
    code, as these running parameters would get overwhelming as the graph is
    built to some arbitrary length. This is different from contexts where
    various running parameters can be set for predictable classes or
    functions. Builders are commonly used to choose from possible functions
    and set arguments for it to be ran with before actually running them

    Attributes:
        piece (type): nametuple singleton for piece generation
        _pieces (dict): dictionary containing a piece's name, positional
            arguments and keyword arguments.
    """

    piece = namedtuple("piece",
                       "name, args, kwargs",
                       module="_Builder",
                       defaults=[str(), list(), dict()])

    _pieces: Dict[str, Union[List[Any], Dict[str, Any]]]

    def build_model(self, data, **kwargs):
        """Assemble pieces into a model given some data

        The data will opten be optional, but several builder models will
        require it to be fitted on initialization. Which further shows why
        builders are necessary for context-agnostic graphs.

        Args:
            data: data that might be used to build the model.
            **kwargs: any additional argument used in building
        """
        raise NotImplementedError()

    def set_piece(self, param, name, *args, **kwargs):
        """Set a piece name, positional arguments and keyword arguments

        Names and parameters are checked before this is performed and might
        cause exceptions to be raised. See the .check_name() method for more
        information on this process.

        Args:
            param (str): piece name set as the piece dict key. Not to be
                confused with the name parameter, which is a selection from
                available options for a certain piece of name {param}.
            name (str): name of a piece option.
            *args: piece positional arguments.
            **kwargs: piece keyword arguments.
        """

        self.check_name(param, name)

        self._pieces[param] = self.piece(name, args, kwargs)

        return self

    def _init_piece(self, params):
        """Initialize piece dictionary given a list of piece names.

        This is done upon initialization of a builder instance and sets all
        of the piece dictionary names and default dictionary.

        Args:
            params (list): list of piece names to be initialized.
        """
        self._pieces = {p: self.piece() for p in params}

    def check_name(self, param, name):
        """Check if name and parameter combination is valid.

        This will always be called upon setting a new piece to ensure this
        piece is present dictionary and that the name is valid. Subclasses
        will often override this method to implement the name checks in
        accordance to their specific name parameter combination options.
        Notice that checks cannot be done on arguments before running the
        _Builder. This also can be called from outside of a _Builder instance
        to check for the validity of settings.

        Args:
            piece (str): name of the key in the piece dictionary.
            name (str): name option to be set to the piece.
        """
        if param not in self._pieces:
            raise KeyError(f"invalid parameter {param}, select one of \
                {self._pieces.keys()}")
        if name is None:
            raise ValueError("Please specify a valid name")
