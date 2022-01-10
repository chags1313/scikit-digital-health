from pathlib import Path

from pytest import fixture
from numpy import load

from skdh import BaseProcess
from skdh.read.base import check_input_file


@fixture
def dummy_reader_class():
    class Rdr(BaseProcess):
        extn = ".abc"
        extn_message = "File extension is not expected '{}'"
        _in_pipeline = False

        def __init__(self, ext_error='warn'):
            super().__init__(
                ext_error=ext_error,
            )

            if ext_error.lower() in ['warn', 'raise', 'skip']:
                self.ext_error = ext_error.lower()
            else:
                raise ValueError("`ext_error` must be one of 'raise', 'warn', 'skip'.")

        @check_input_file
        def predict(self, file=None, **kwargs):
            super().predict(expect_wear=False, expect_days=False, file=file, **kwargs)

            kwargs.update({'file': file, 'in_predict': True})
            return (kwargs, None) if self._in_pipeline else kwargs

    return Rdr


@fixture
def gnactv_file():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        return Path("data/gnactv_sample.bin")
    elif cwd[-1] == "test":
        return Path("read/data/gnactv_sample.bin")
    elif cwd[-1] == "scikit-digital-health":
        return Path("test/read/data/gnactv_sample.bin")


@fixture
def gnactv_truth():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        path = "data/gnactv_data.npz"
    elif cwd[-1] == "test":
        path = "read/data/gnactv_data.npz"
    elif cwd[-1] == "scikit-digital-health":
        path = "test/read/data/gnactv_data.npz"

    dat = load(path, allow_pickle=False)

    data = {i: dat[i] for i in ["accel", "time", "temperature", "light"]}
    data["day_ends"] = {(8, 12): dat["day_ends_8_12"]}

    return data


@fixture
def ax3_file():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        return Path("data/ax3_sample.cwa")
    elif cwd[-1] == "test":
        return Path("read/data/ax3_sample.cwa")
    elif cwd[-1] == "scikit-digital-health":
        return Path("test/read/data/ax3_sample.cwa")


@fixture
def ax3_truth():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        path = "data/ax3_data.npz"
    elif cwd[-1] == "test":
        path = "read/data/ax3_data.npz"
    elif cwd[-1] == "scikit-digital-health":
        path = "test/read/data/ax3_data.npz"

    dat = load(path, allow_pickle=False)

    data = {i: dat[i] for i in ["accel", "time", "temperature", "fs"]}
    data["day_ends"] = {(8, 12): dat["day_ends_8_12"]}

    return data


@fixture
def ax6_file():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        return Path("data/ax6_sample.cwa")
    elif cwd[-1] == "test":
        return Path("read/data/ax6_sample.cwa")
    elif cwd[-1] == "scikit-digital-health":
        return Path("test/read/data/ax6_sample.cwa")


@fixture
def ax6_truth():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        path = "data/ax6_data.npz"
    elif cwd[-1] == "test":
        path = "read/data/ax6_data.npz"
    elif cwd[-1] == "scikit-digital-health":
        path = "test/read/data/ax6_data.npz"

    dat = load(path, allow_pickle=False)

    data = {i: dat[i] for i in ["accel", "time", "gyro", "temperature", "fs"]}
    data["day_ends"] = {(8, 12): dat["day_ends_8_12"]}

    return data


@fixture
def gt3x_file():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        return Path("data/gt3x_sample.gt3x")
    elif cwd[-1] == "test":
        return Path("read/data/gt3x_sample.gt3x")
    elif cwd[-1] == "scikit-digital-health":
        return Path("test/read/data/gt3x_sample.gt3x")


@fixture
def gt3x_truth():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        path = "data/gt3x_data.npz"
    elif cwd[-1] == "test":
        path = "read/data/gt3x_data.npz"
    elif cwd[-1] == "scikit-digital-health":
        path = "test/read/data/gt3x_data.npz"

    dat = load(path, allow_pickle=False)

    data = {i: dat[i] for i in ["accel", "time"]}
    data["day_ends"] = {(9, 2): dat["day_ends_9_2"]}

    return data


@fixture
def apdm_file():
    cwd = Path.cwd().parts

    if cwd[-1] == "read":
        return Path("data/apdm_sample.h5")
    elif cwd[-1] == "test":
        return Path("read/data/apdm_sample.h5")
    elif cwd[-1] == "scikit-digital-health":
        return Path("test/read/data/apdm_sample.h5")
