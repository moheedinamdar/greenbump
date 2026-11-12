import math

import numpy as np

from stats.metrics import all_positive, clean, geometric_mean, safe_mean, to_float_array


def test_to_float_array_dtype():
    assert to_float_array([1, 2, 3]).dtype == np.dtype("float64")


def test_clean_marks_negatives_missing():
    cleaned = clean([1.0, -2.0, 3.0])
    assert math.isnan(cleaned[1])
    assert cleaned[0] == 1.0


def test_safe_mean_ignores_negatives():
    assert safe_mean([2.0, -5.0, 4.0]) == 3.0


def test_geometric_mean():
    assert math.isclose(geometric_mean([1, 4, 16]), 4.0)


def test_all_positive():
    assert all_positive([1, 2, 3])
    assert not all_positive([1, 0, 3])
