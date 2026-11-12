## Upgrade
- numpy 1.26.4 -> 2.5.4

## Test run after the upgrade: 0 passed, 5 failed, 0 errors
```text
FFFFF                                                                    [100%]
=================================== FAILURES ===================================
__________________________ test_to_float_array_dtype ___________________________
tests/test_metrics.py:9: in test_to_float_array_dtype
    assert to_float_array([1, 2, 3]).dtype == np.dtype("float64")
           ^^^^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:5: in to_float_array
    return np.asarray(values, dtype=np.float_)
                                    ^^^^^^^^^
../../../../../../.greenbump-cache/venvs/numpy-v2-92d47f97614a/lib/python3.13/site-packages/numpy/__init__.py:763: in __getattr__
    raise AttributeError(
E   AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
______________________ test_clean_marks_negatives_missing ______________________
tests/test_metrics.py:13: in test_clean_marks_negatives_missing
    cleaned = clean([1.0, -2.0, 3.0])
              ^^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:9: in clean
    arr = to_float_array(values)
          ^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:5: in to_float_array
    return np.asarray(values, dtype=np.float_)
                                    ^^^^^^^^^
../../../../../../.greenbump-cache/venvs/numpy-v2-92d47f97614a/lib/python3.13/site-packages/numpy/__init__.py:763: in __getattr__
    raise AttributeError(
E   AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
_______________________ test_safe_mean_ignores_negatives _______________________
tests/test_metrics.py:19: in test_safe_mean_ignores_negatives
    assert safe_mean([2.0, -5.0, 4.0]) == 3.0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:15: in safe_mean
    return float(np.nanmean(clean(values)))
                            ^^^^^^^^^^^^^
stats/metrics.py:9: in clean
    arr = to_float_array(values)
          ^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:5: in to_float_array
    return np.asarray(values, dtype=np.float_)
                                    ^^^^^^^^^
../../../../../../.greenbump-cache/venvs/numpy-v2-92d47f97614a/lib/python3.13/site-packages/numpy/__init__.py:763: in __getattr__
    raise AttributeError(
E   AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
_____________________________ test_geometric_mean ______________________________
tests/test_metrics.py:23: in test_geometric_mean
    assert math.isclose(geometric_mean([1, 4, 16]), 4.0)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:19: in geometric_mean
    arr = to_float_array(values)
          ^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:5: in to_float_array
    return np.asarray(values, dtype=np.float_)
                                    ^^^^^^^^^
../../../../../../.greenbump-cache/venvs/numpy-v2-92d47f97614a/lib/python3.13/site-packages/numpy/__init__.py:763: in __getattr__
    raise AttributeError(
E   AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
______________________________ test_all_positive _______________________________
tests/test_metrics.py:27: in test_all_positive
    assert all_positive([1, 2, 3])
           ^^^^^^^^^^^^^^^^^^^^^^^
stats/metrics.py:24: in all_positive
    return bool(np.alltrue(to_float_array(values) > 0))
                ^^^^^^^^^^
../../../../../../.greenbump-cache/venvs/numpy-v2-92d47f97614a/lib/python3.13/site-packages/numpy/__init__.py:763: in __getattr__
    raise AttributeError(
E   AttributeError: `np.alltrue` was removed in the NumPy 2.0 release. Use `np.all` instead.
=========================== short test summary info ============================
FAILED tests/test_metrics.py::test_to_float_array_dtype - AttributeError: `np...
FAILED tests/test_metrics.py::test_clean_marks_negatives_missing - AttributeE...
FAILED tests/test_metrics.py::test_safe_mean_ignores_negatives - AttributeErr...
FAILED tests/test_metrics.py::test_geometric_mean - AttributeError: `np.float...
FAILED tests/test_metrics.py::test_all_positive - AttributeError: `np.alltrue...
5 failed in 0.09s
```

## Files that import the upgraded package(s), with line numbers
### stats/metrics.py
```python
    1 | import numpy as np
    2 | 
    3 | 
    4 | def to_float_array(values):
    5 |     return np.asarray(values, dtype=np.float_)
    6 | 
    7 | 
    8 | def clean(values):
    9 |     arr = to_float_array(values)
   10 |     arr[arr < 0] = np.NaN
   11 |     return arr
   12 | 
   13 | 
   14 | def safe_mean(values):
   15 |     return float(np.nanmean(clean(values)))
   16 | 
   17 | 
   18 | def geometric_mean(values):
   19 |     arr = to_float_array(values)
   20 |     return float(np.product(arr) ** (1.0 / len(arr)))
   21 | 
   22 | 
   23 | def all_positive(values):
   24 |     return bool(np.alltrue(to_float_array(values) > 0))
```

### tests/test_metrics.py
```python
    1 | import math
    2 | 
    3 | import numpy as np
    4 | 
    5 | from stats.metrics import all_positive, clean, geometric_mean, safe_mean, to_float_array
    6 | 
    7 | 
    8 | def test_to_float_array_dtype():
    9 |     assert to_float_array([1, 2, 3]).dtype == np.dtype("float64")
   10 | 
   11 | 
   12 | def test_clean_marks_negatives_missing():
   13 |     cleaned = clean([1.0, -2.0, 3.0])
   14 |     assert math.isnan(cleaned[1])
   15 |     assert cleaned[0] == 1.0
   16 | 
   17 | 
   18 | def test_safe_mean_ignores_negatives():
   19 |     assert safe_mean([2.0, -5.0, 4.0]) == 3.0
   20 | 
   21 | 
   22 | def test_geometric_mean():
   23 |     assert math.isclose(geometric_mean([1, 4, 16]), 4.0)
   24 | 
   25 | 
   26 | def test_all_positive():
   27 |     assert all_positive([1, 2, 3])
   28 |     assert not all_positive([1, 0, 3])
```

## Upstream notes that may be relevant
Search queries used: float_, float64, alltrue, all, AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead., AttributeError: `np.alltrue` was removed in the NumPy 2.0 release. Use `np.all` instead.

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/release/2.0.0-notes.rst#L159">
* Replaced ``from ... import *`` in the ``numpy/__init__.py`` with explicit imports.
  As a result, these main namespace members got removed: ``np.FLOATING_POINT_SUPPORT``,
  ``np.FPE_*``, ``np.NINF``, ``np.PINF``, ``np.NZERO``, ``np.PZERO``, ``np.CLIP``,
  ``np.WRAP``, ``np.WRAP``, ``np.RAISE``, ``np.BUFSIZE``, ``np.UFUNC_BUFSIZE_DEFAULT``,
  ``np.UFUNC_PYVALS_NAME``, ``np.ALLOW_THREADS``, ``np.MAXDIMS``, ``np.MAY_SHARE_EXACT``,
  ``np.MAY_SHARE_BOUNDS``, ``add_newdoc``, ``np.add_docstring`` and
  ``np.add_newdoc_ufunc``.
  (`gh-24357 <https://github.com/numpy/numpy/pull/24357>`__)
* Alias ``np.float_`` has been removed. Use ``np.float64`` instead.
* Alias ``np.complex_`` has been removed. Use ``np.complex128`` instead.
* Alias ``np.longfloat`` has been removed. Use ``np.longdouble`` instead.
* Alias ``np.singlecomplex`` has been removed. Use ``np.complex64`` instead.
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/numpy_2_0_migration_guide.rst#L365">
- ``Arrayterator`` and ``NumpyVersion`` classes,
- ``add_docstring`` and ``add_newdoc`` functions,
- ``tracemalloc_domain`` constant.
If you get an ``AttributeError`` when accessing an attribute from ``np.lib`` you should
try accessing it from the main ``np`` namespace then. If an item is also missing from
the main namespace, then you're using a private member. You should either use the existing
API or, in case it's infeasible, reach out to us with a request to restore the removed entry.
numpy.core namespace
--------------------
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/numpy_2_0_migration_guide.rst#L32">
You can also apply the NumPy 2.0 rule directly from the command line::
    $ ruff check path/to/code/ --select NPY201
.. _migration_promotion_changes:
Changes to NumPy data type promotion
=====================================
NumPy 2.0 changes promotion (the result of combining dissimilar data types)
as per :ref:`NEP 50 <NEP50>`. Please see the NEP for details on this change.
It includes a table of example changes and a backwards compatibility section.
The largest backwards compatibility change is that the precision of scalars
is now preserved consistently.  Two examples are:
* ``np.float32(3) + 3.`` now returns a float32 when it previously returned
  a float64.
* ``np.array([3], dtype=np.float32) + np.float64(3)`` will now return a float64
  array.  (The higher precision of the scalar is not ignored.)
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/numpy_2_0_migration_guide.rst#L256">
======================  =================================================================
removed member          migration guideline
======================  =================================================================
add_docstring           It's still available as ``np.lib.add_docstring``.
add_newdoc              It's still available as ``np.lib.add_newdoc``.
add_newdoc_ufunc        It's an internal function and doesn't have a replacement.
alltrue                 Use ``np.all`` instead.
asfarray                Use ``np.asarray`` with a float dtype instead.
byte_bounds             Now it's available under ``np.lib.array_utils.byte_bounds``
cast                    Use ``np.asarray(arr, dtype=dtype)`` instead.
cfloat                  Use ``np.complex128`` instead.
charrarray              It's still available as ``np.char.chararray``.
clongfloat              Use ``np.clongdouble`` instead.
compare_chararrays      It's still available as ``np.char.compare_chararrays``.
compat                  There's no replacement, as Python 2 is no longer supported.
complex\_               Use ``np.complex128`` instead.
cumproduct              Use ``np.cumprod`` instead.
DataSource              It's still available as ``np.lib.npyio.DataSource``.
deprecate               Emit ``DeprecationWarning`` with ``warnings.warn`` directly,
                        or use ``typing.deprecated``.
deprecate_with_doc      Emit ``DeprecationWarning`` with ``warnings.warn`` directly,
                        or use ``typing.deprecated``.
disp                    Use your own printing function instead.
fastCopyAndTranspose    Use ``arr.T.copy()`` instead.
find_common_type        Use ``numpy.promote_types`` or ``numpy.result_type`` instead. 
                        To achieve semantics for the ``scalar_t
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/release/2.0.0-notes.rst#L93">
Furthermore there are many changes to NumPy internals, including continuing to
migrate code from C to C++, that will make it easier to improve and maintain
NumPy in the future.
The "no free lunch" theorem dictates that there is a price to pay for all these
API and behavior improvements and better future extensibility. This price is:
1. Backwards compatibility. There are a significant number of breaking changes
   to both the Python and C APIs. In the majority of cases, there are clear
   error messages that will inform the user how to adapt their code. However,
   there are also changes in behavior for which it was not possible to give
   such an error message - these cases are all covered in the Deprecation and
   Compatibility sections below, and in the :ref:`numpy-2-migration-guide`.
   Note that there is a ``ruff`` mode to auto-fix many things in Python code.
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/release/2.0.0-notes.rst#L523">
* The dtype flags on ``PyArray_Descr`` must now be accessed through the
  ``PyDataType_FLAGS`` inline function to be compatible with both 1.x and 2.x.
  This function is defined in ``npy_2_compat.h`` to allow backporting.
  Most or all users should use ``PyDataType_FLAGCHK`` which is available on
  1.x and does not require backporting.
  Cython users should use Cython 3.  Otherwise access will go through Python
  unless they use ``PyDataType_FLAGCHK`` instead.
  (`gh-25816 <https://github.com/numpy/numpy/pull/25816>`__)
Datetime functionality exposed in the C API and Cython bindings
</untrusted>

<untrusted source="https://raw.githubusercontent.com/numpy/numpy/main/doc/source/numpy_2_0_migration_guide.rst#L197">
Complex types - Underlying type changes
---------------------------------------
The underlying C types for all of the complex types have been changed to use
native C99 types. While the memory layout of those types remains identical
to the types used in NumPy 1.x, the API is slightly different, since direct
field access (like ``c.real`` or ``c.imag``) is no longer possible.
It is recommended to use the functions ``npy_creal`` and ``npy_cimag``
(and the corresponding float and long double variants) to retrieve
the real or imaginary part of a complex number, as these will work with both
NumPy 1.x and with NumPy 2.x. New functions ``npy_csetreal`` and
``npy_csetimag``, along with compatibility macros ``NPY_CSETREAL`` and
``NPY_CSETIMAG`` (and the corresponding float and long double variants),
have been added for setting the real or imaginary part.
</untrusted>