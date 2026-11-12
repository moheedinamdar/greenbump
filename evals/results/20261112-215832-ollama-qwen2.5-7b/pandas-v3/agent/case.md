## Upgrade
- pandas 1.5.3 -> 3.1.1

## Test run after the upgrade: 0 passed, 3 failed, 0 errors
```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
_________________________________ test_add_row _________________________________
tests/test_report.py:17: in test_add_row
    df = add_row(sample(), {"category": "fuel", "kind": "sale", "amount": 30.0})
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ledger/report.py:5: in add_row
    return df.append(row, ignore_index=True)
           ^^^^^^^^^
../../../../../../.greenbump-cache/venvs/pandas-v3-44c302854c3f/lib/python3.13/site-packages/pandas/core/generic.py:6434: in __getattr__
    return object.__getattribute__(self, name)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'DataFrame' object has no attribute 'append'
____________________________ test_total_by_category ____________________________
tests/test_report.py:24: in test_total_by_category
    assert total_by_category(sample()) == {"food": 14.0, "rent": 500.0}
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
ledger/report.py:10: in total_by_category
    for category, amount in df.groupby("category")["amount"].sum().iteritems():
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
../../../../../../.greenbump-cache/venvs/pandas-v3-44c302854c3f/lib/python3.13/site-packages/pandas/core/generic.py:6434: in __getattr__
    return object.__getattribute__(self, name)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'Series' object has no attribute 'iteritems'
____________________________ test_zero_out_refunds _____________________________
tests/test_report.py:29: in test_zero_out_refunds
    assert df["amount"].tolist() == [10.0, 500.0, 0.0]
E   assert [10.0, 500.0, 4.0] == [10.0, 500.0, 0.0]
E     
E     At index 2 diff: 4.0 != 0.0
E     Use -v to get more diff
=============================== warnings summary ===============================
tests/test_report.py::test_zero_out_refunds
  <repo>/ledger/report.py:16: ChainedAssignmentError: A value is being set on a copy of a DataFrame or Series through chained assignment.
  Such chained assignment never works to update the original DataFrame or Series, because the intermediate object on which we are setting values always behaves as a copy (due to Copy-on-Write).
  
  Try using '.loc[row_indexer, col_indexer] = value' instead, to perform the assignment in a single step.
  
  See the documentation for a more detailed explanation: https://pandas.pydata.org/docs/dev/user_guide/migration.html#chained-assignment
    df["amount"][df["kind"] == "refund"] = 0

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_report.py::test_add_row - AttributeError: 'DataFrame' objec...
FAILED tests/test_report.py::test_total_by_category - AttributeError: 'Series...
FAILED tests/test_report.py::test_zero_out_refunds - assert [10.0, 500.0, 4.0...
3 failed, 1 warning in 0.63s
```

## Files that import the upgraded package(s), with line numbers
### ledger/report.py
```python
    1 | import pandas as pd
    2 | 
    3 | 
    4 | def add_row(df, row):
    5 |     return df.append(row, ignore_index=True)
    6 | 
    7 | 
    8 | def total_by_category(df):
    9 |     totals = {}
   10 |     for category, amount in df.groupby("category")["amount"].sum().iteritems():
   11 |         totals[category] = float(amount)
   12 |     return totals
   13 | 
   14 | 
   15 | def zero_out_refunds(df):
   16 |     df["amount"][df["kind"] == "refund"] = 0
   17 |     return df
```

### tests/test_report.py
```python
    1 | import pandas as pd
    2 | 
    3 | from ledger.report import add_row, total_by_category, zero_out_refunds
    4 | 
    5 | 
    6 | def sample():
    7 |     return pd.DataFrame(
    8 |         {
    9 |             "category": ["food", "rent", "food"],
   10 |             "kind": ["sale", "sale", "refund"],
   11 |             "amount": [10.0, 500.0, 4.0],
   12 |         }
   13 |     )
   14 | 
   15 | 
   16 | def test_add_row():
   17 |     df = add_row(sample(), {"category": "fuel", "kind": "sale", "amount": 30.0})
   18 |     assert len(df) == 4
   19 |     assert df.iloc[-1]["category"] == "fuel"
   20 |     assert list(df.index) == [0, 1, 2, 3]
   21 | 
   22 | 
   23 | def test_total_by_category():
   24 |     assert total_by_category(sample()) == {"food": 14.0, "rent": 500.0}
   25 | 
   26 | 
   27 | def test_zero_out_refunds():
   28 |     df = zero_out_refunds(sample())
   29 |     assert df["amount"].tolist() == [10.0, 500.0, 0.0]
```

## Upstream notes that may be relevant
Search queries used: append, iteritems, ChainedAssignmentError, AttributeError: 'DataFrame' object has no attribute 'append', AttributeError: 'Series' object has no attribute 'iteritems', assert [10.0, 500.0, 4.0] == [10.0, 500.0, 0.0], At index 2 diff: 4.0 != 0.0, Use -v to get more diff

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L499">
    Many users will now get "datetime64[us]" dtype data in cases when they used
    to get "datetime64[ns]".
    For most use cases they should not notice a difference. One big exception is
    converting to integers, which will give integers 1000x smaller.
    When converting datetime-like data to integers, it is recommended to avoid
    ``astype("int64")`` to make your code agnostic to the exact unit, or ensure
    the desired unit with :meth:`~Series.dt.as_unit` before casting.
    See :ref:`timeseries.converting.epoch_inverse` for more details.
.. _whatsnew_300.api_breaking.pytz:
Time zones are now represented by standard library ``zoneinfo`` instead of ``pytz`` by default
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L1369">
^^^^^^^
- Bug in :meth:`Series.str.match` failing to raise when given a compiled ``re.Pattern`` object and conflicting ``case`` or ``flags`` arguments (:issue:`62240`)
- Bug in :meth:`Series.str.replace` raising an error on valid group references (``\1``, ``\2``, etc.) on series converted to PyArrow backend dtype (:issue:`62653`)
- Bug in :meth:`Series.str.zfill` raising ``AttributeError`` for :class:`ArrowDtype` (:issue:`61485`)
- Bug in :meth:`Series.value_counts` would not respect ``sort=False`` for series having ``string`` dtype (:issue:`55224`)
- Bug in :ref:`Series.str methods <api.series.str>` would fail when using regex with lookaheads or lookbehinds, backreferences, or ``\Z`` on data backed by PyArrow (:issue:`60833`, :issue:`63683`)
- Bug in multiplication with a :class:`StringDtype` incorrectly allowing multiplying by bools; explicitly cast to integers instead (:issue:`62595`)
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L119">
Some of the behaviour changes described above are breaking changes in pandas
3.0. When upgrading to pandas 3.0, it is recommended to first upgrade to pandas
2.3 to get deprecation warnings for a subset of those changes. The
:ref:`migration guide <copy_on_write.migration_guide>` explains the upgrade
process in more detail.
.. seealso::
    `PDEP-7: Consistent copy/view semantics in pandas with Copy-on-Write <https://pandas.pydata.org/pdeps/0007-copy-on-write.html>`__
Setting the option ``mode.copy_on_write`` no longer has any impact. The option is deprecated
and will be removed in pandas 4.0.
.. _whatsnew_300.enhancements.col:
Initial support for ``pd.col()`` syntax to create expressions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This release introduces :func:`col` to refer to a DataFrame column by name
and build up expressions.
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v2.0.0.rst#L1353">
^^^^^^^^^^
- Bug in :meth:`MultiIndex.get_indexer` not matching ``NaN`` values (:issue:`29252`, :issue:`37222`, :issue:`38623`, :issue:`42883`, :issue:`43222`, :issue:`46173`, :issue:`48905`)
- Bug in :meth:`MultiIndex.argsort` raising ``TypeError`` when index contains :attr:`NA` (:issue:`48495`)
- Bug in :meth:`MultiIndex.difference` losing extension array dtype (:issue:`48606`)
- Bug in :class:`MultiIndex.set_levels` raising ``IndexError`` when setting empty level (:issue:`48636`)
- Bug in :meth:`MultiIndex.unique` losing extension array dtype (:issue:`48335`)
- Bug in :meth:`MultiIndex.intersection` losing extension array (:issue:`48604`)
- Bug in :meth:`MultiIndex.union` losing extension array (:issue:`48498`, :issue:`48505`, :issue:`48900`)
- Bug in :meth:`MultiIndex.union` not sorting when sort=None and index contains missing values (:issue:`49010`)
- Bug in :meth:`MultiIndex.append` not checking names for equality (:issue:`48288`)
- Bug in :meth:`MultiIndex.symmetric_difference` losing extension array (:issue:`48607`)
- Bug in :meth:`MultiIndex.join` losing dtypes when :class:`MultiIndex` has duplicates (:issue:`49830`)
- Bug in :meth:`MultiIndex.putmask` losing extension array (:issue:`49830`)
- Bug in :meth:`MultiIndex.value_counts` returning a :class:`Series` indexed by flat index of tuples instead of a :class:`MultiIndex` (:issue:`49558`)
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L1218">
~~~~~~~~~~~~~~~~~~~~~~~~
- Eliminated circular reference in to original pandas object in accessor attributes (e.g. :attr:`Series.str`). However, accessor instantiation is no longer cached (:issue:`47667`, :issue:`41357`)
- :attr:`Categorical.categories` returns a :class:`RangeIndex` columns instead of an :class:`Index` if the constructed ``values`` was a ``range``. (:issue:`57787`)
- :class:`DataFrame` returns a :class:`RangeIndex` columns when possible when ``data`` is a ``dict`` (:issue:`57943`)
- :class:`Series` returns a :class:`RangeIndex` index when possible when ``data`` is a ``dict`` (:issue:`58118`)
- :func:`concat` returns a :class:`RangeIndex` column when possible when ``objs`` contains :class:`Series` and :class:`DataFrame` and ``axis=0`` (:issue:`58119`)
- :func:`concat` returns a :class:`RangeIndex` level in the :class:`MultiIndex` result when ``keys`` is a ``range`` or :class:`RangeIndex` (:issue:`57542`)
- :meth:`RangeIndex.append` returns a :class:`RangeIndex` instead of a :class:`Index` when appending values that could continue the :class:`RangeIndex` (:issue:`57467`)
- :meth:`Series.nlargest` has improved performance when there are duplicate values in the index (:issue:`55767`)
- :meth:`Series.str.extract` returns a :class:`RangeIndex` columns instead of an :class:`Index` column when possible (:issue:`57542`)
- :meth:`Series.str.partition` with :class:`ArrowDtype` returns a :class:`RangeIndex` columns instead of an :class:`Index` column when possible (:issue:`57768`)
- Performance improvement in :class:`DataFrame` when ``data`` is a ``dict`` and ``columns`` is specified (:issue:`24368`)
- Performance improvement in :class:`MultiIndex` when setting :attr:`MultiIndex.names` doesn't invalidate all cached operations (:issue:`59578`)
- Performance improvem
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L842">
With ``"future.distinguish_nan_and_na"`` enabled, ``ser.to_numpy()`` (and
``frame.values`` and ``np.asarray(obj)``) will convert to ``object`` dtype if
:class:`NA` entries are present, where before they would coerce to
``NaN``.  To retain a float numpy dtype, explicitly pass ``na_value=np.nan``
to :meth:`Series.to_numpy`.
Note that the option is experimental and subject to change in future releases.
The ``__module__`` attribute now points to public modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``__module__`` attribute on functions and classes in the public API has been
updated to refer to the preferred public module from which to access the object,
rather than the module in which the object happens to be defined (:issue:`55178`).
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v3.0.0.rst#L330">
- :func:`set_option` now accepts a dictionary of options, simplifying configuration of multiple settings at once (:issue:`61093`)
- :meth:`DataFrame.apply` supports using third-party execution engines like the Bodo.ai JIT compiler (:issue:`60668`)
- :meth:`Series.map` now accepts an ``engine`` parameter to allow execution with a third-party execution engine (:issue:`61125`)
- Support passing a :class:`Series` input to :func:`json_normalize` that retains the :class:`Index` (:issue:`51452`)
- Users can globally disable any ``PerformanceWarning`` by setting the option ``mode.performance_warnings`` to ``False`` (:issue:`56920`)
Packaging:
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/whatsnew/v2.0.0.rst#L863">
.. note::
    A current PDEP proposes the deprecation and removal of the keywords ``inplace`` and ``copy``
    for all but a small subset of methods from the pandas API. The current discussion takes place
    at `here <https://github.com/pandas-dev/pandas/pull/51466>`_. The keywords won't be necessary
    anymore in the context of Copy-on-Write. If this proposal is accepted, both
    keywords would be deprecated in the next release of pandas and removed in pandas 3.0.
.. ---------------------------------------------------------------------------
.. _whatsnew_200.deprecations:
Deprecations
</untrusted>