import numpy as np


def to_float_array(values):
    return np.asarray(values, dtype=np.float64)


def clean(values):
    arr = to_float_array(values)
    arr[arr < 0] = np.nan
    return arr


def safe_mean(values):
    return float(np.nanmean(clean(values)))


def geometric_mean(values):
    arr = to_float_array(values)
    return float(np.prod(arr) ** (1.0 / len(arr)))


def all_positive(values):
    return bool(np.all(to_float_array(values) > 0))
