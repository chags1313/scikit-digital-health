"""
!{{ short_description }}

!{{ author }}
!{{ year }}, Pfizer DMTI
"""
from warnings import warn

from numpy import zeros

from PfyMU.base import _BaseProcess
"""
Add other imports here. Per python stardards, imports should follow the above pattern:
top - python standard libraries
empty line
middle - 3rd party libraries (eg numpy, scipy, etc)
empty line
bottom - this library/module imports. ideally, all imports should be ABSOLUTE, not relative
"""


class !{{ module_name }}(_BaseProcess):
    def __repr__(self):
        ret = "!{{ module_name }}("
        ret += f"attr1={self.attr1!r}, "  # TODO update these to be parameters passed to __init__
        ret += f"attr2={self.attr2!r})"
        return ret

    def __init__(self, attr1=None, attr2=None):
        """
        Process description here

        Parameters
        ----------
        attr1
        attr2
        """
        super().__init__("!{{ module_name }}", True)  # TODO update this if desired!

        self.attr1 = attr1
        self.attr2 = attr2

    def predict(self, *args, **kwargs):
        """
        Docstring for predict, with call/attributes from _predict

        Parameters
        ----------


        Returns
        -------

        """
        super().predict(*args, **kwargs)

    def _predict(self, time=None, accel=None, *, gyro=None, **kwargs):
        # TODO add functionality
        result = {}
        # TODO add any results needed to result

        kwargs.update({self._time: time, self._acc: accel, self._gyro: gyro})
        return kwargs, result

