import numpy as np


def to_float_array(values):
    return np.asarray(values, dtype=np.float_)


def clean(values):
    arr = to_float_array(values)
    arr[arr < 0] = np.NaN
    return arr


def safe_mean(values):
    return float(np.nanmean(clean(values)))


def geometric_mean(values):
    arr = to_float_array(values)
    return float(np.product(arr) ** (1.0 / len(arr)))


def all_positive(values):
    return bool(np.alltrue(to_float_array(values) > 0))
