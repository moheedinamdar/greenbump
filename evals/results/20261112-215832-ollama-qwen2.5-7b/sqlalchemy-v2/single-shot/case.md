## Upgrade
- sqlalchemy 1.4.54 -> 2.1.8

## Test run after the upgrade: 0 passed, 3 failed, 0 errors
```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
_____________________________ test_empty_database ______________________________
../../../../../../.greenbump-cache/venvs/sqlalchemy-v2-409c0198c38b/lib/python3.13/site-packages/sqlalchemy/engine/base.py:1490: in execute
    meth = statement._execute_on_connection
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'str' object has no attribute '_execute_on_connection'

The above exception was the direct cause of the following exception:
tests/test_repo.py:12: in test_empty_database
    assert count_users(engine) == 0
           ^^^^^^^^^^^^^^^^^^^
userdb/repo.py:32: in count_users
    return conn.execute("SELECT COUNT(*) FROM users").scalar()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
../../../../../../.greenbump-cache/venvs/sqlalchemy-v2-409c0198c38b/lib/python3.13/site-packages/sqlalchemy/engine/base.py:1492: in execute
    raise exc.ObjectNotExecutableError(statement) from err
E   sqlalchemy.exc.ObjectNotExecutableError: Not an executable object: 'SELECT COUNT(*) FROM users'
___________________________ test_add_and_list_users ____________________________
tests/test_repo.py:17: in test_add_and_list_users
    add_user(engine, "bob", "bob@example.com")
userdb/repo.py:21: in add_user
    engine.execute(users.insert().values(name=name, email=email))
    ^^^^^^^^^^^^^^
E   AttributeError: 'Engine' object has no attribute 'execute'
_______________________________ test_count_users _______________________________
tests/test_repo.py:23: in test_count_users
    add_user(engine, "carol", "carol@example.com")
userdb/repo.py:21: in add_user
    engine.execute(users.insert().values(name=name, email=email))
    ^^^^^^^^^^^^^^
E   AttributeError: 'Engine' object has no attribute 'execute'
=========================== short test summary info ============================
FAILED tests/test_repo.py::test_empty_database - sqlalchemy.exc.ObjectNotExec...
FAILED tests/test_repo.py::test_add_and_list_users - AttributeError: 'Engine'...
FAILED tests/test_repo.py::test_count_users - AttributeError: 'Engine' object...
3 failed in 0.34s
```

## Files that import the upgraded package(s), with line numbers
### userdb/repo.py
```python
    1 | from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
    2 | 
    3 | metadata = MetaData()
    4 | 
    5 | users = Table(
    6 |     "users",
    7 |     metadata,
    8 |     Column("id", Integer, primary_key=True),
    9 |     Column("name", String(50), nullable=False),
   10 |     Column("email", String(100), nullable=False),
   11 | )
   12 | 
   13 | 
   14 | def make_engine(url="sqlite://"):
   15 |     engine = create_engine(url)
   16 |     metadata.create_all(engine)
   17 |     return engine
   18 | 
   19 | 
   20 | def add_user(engine, name, email):
   21 |     engine.execute(users.insert().values(name=name, email=email))
   22 | 
   23 | 
   24 | def user_names(engine):
   25 |     with engine.connect() as conn:
   26 |         rows = conn.execute(select([users.c.name]).order_by(users.c.name))
   27 |         return [row[0] for row in rows]
   28 | 
   29 | 
   30 | def count_users(engine):
   31 |     with engine.connect() as conn:
   32 |         return conn.execute("SELECT COUNT(*) FROM users").scalar()
```

## Upstream notes that may be relevant
Search queries used: _execute_on_connection, execute, ObjectNotExecutableError, AttributeError: 'str' object has no attribute '_execute_on_connection', sqlalchemy.exc.ObjectNotExecutableError: Not an executable object: 'SELECT COUNT(*) FROM users', AttributeError: 'Engine' object has no attribute 'execute'

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L328">
        # for warnings related to execute() / scalar(), raise
        for msg in [
            r"The (?:Executable|Engine)\.(?:execute|scalar)\(\) function",
            r"The current statement is being autocommitted using implicit autocommit,",
            r"The connection.execute\(\) method in SQLAlchemy 2.0 will accept "
            "parameters as a single dictionary or a single sequence of "
            "dictionaries only.",
            r"The Connection.connect\(\) function/method is considered legacy",
            r".*DefaultGenerator.execute\(\)",
        ]:
            warnings.filterwarnings(
                "error",
                message=msg,
                category=exc.RemovedIn20Warning,
            )
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L1493">
          session.query(User).\
            filter(User.name == "foo").\
            update(
              {"fullname": "Foo Bar"},
              synchronize_session="evaluate"
            )
      - ::
          session.execute(
            update(User)
            .where(User.name == "foo")
            .values(fullname="Foo Bar")
            .execution_options(
              synchronize_session="evaluate"
            )
          )
      - :ref:`orm_expression_update_delete`
    *
      - ::
          session.query(User).count()
      - ::
          session.scalar(
            select(func.count()).
            select_from(User)
          )
          # or
          session.scalar(
            select(func.count(User.id))
          )
      - :meth:`_orm.Session.scalar`
.. format: on
.. _migration_20_unify_select:
ORM Query Unified with Core Select
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L1540">
**Synopsis**
The :class:`_orm.Query` object (as well as the :class:`_baked.BakedQuery` and
:class:`_horizontal.ShardedQuery` extensions) become long term legacy objects,
replaced by the direct usage of the :func:`_sql.select` construct in conjunction
with the :meth:`_orm.Session.execute` method.  Results
that are returned from :class:`_orm.Query` in the form of lists of objects
or tuples, or as scalar ORM objects are returned from :meth:`_orm.Session.execute`
uniformly as :class:`_engine.Result` objects, which feature an interface
consistent with that of Core execution.
Legacy code examples are illustrated below::
    session = Session(engine)
    # becomes legacy use case
    user = session.query(User).filter_by(name="some user").one()
    # becomes legacy use case
    user = session.query(User).filter_by(name="some user").first()
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L613">
    with engine.connect() as conn:
        conn.execute(some_table.insert().values(foo="bar"))
        conn.execute(some_other_table.insert().values(bat="hoho"))
        conn.commit()
When :ref:`2.0 deprecations mode <migration_20_deprecations_mode>` is enabled,
a warning will emit when the deprecated "autocommit" feature takes place,
indicating those places where an explicit transaction should be noted.
**Discussion**
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L564">
In SQLAlchemy 1.x, the following statements will automatically commit
the underlying DBAPI transaction, but in SQLAlchemy
2.0 this will not occur::
    conn = engine.connect()
    # won't autocommit in 2.0
    conn.execute(some_table.insert().values(foo="bar"))
Nor will this autocommit::
    conn = engine.connect()
    # won't autocommit in 2.0
    conn.execute(text("INSERT INTO table (foo) VALUES ('bar')"))
The common workaround for custom DML that requires commit, the "autocommit"
execution option, will be removed::
    conn = engine.connect()
    # won't autocommit in 2.0
    conn.execute(text("EXEC my_procedural_thing()").execution_options(autocommit=True))
**Migration to 2.0**
The method that is cross-compatible with :term:`1.x style` and :term:`2.0
style` execution is to make use of the :meth:`_engine.Connection.begin` method,
or the :meth:`_engine.Engine.begin` context manager::
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L652">
    with engine.begin() as conn:
        conn.execute(some_table.insert().values(foo="bar"))
For "commit as you go, or rollback instead" usage, which resembles how the
:class:`_orm.Session` is normally used today, the "future" version of
:class:`_engine.Connection`, which is the one that is returned from an
:class:`_engine.Engine` that was created using the
:paramref:`_sa.create_engine.future` flag, includes new
:meth:`_engine.Connection.commit` and :meth:`_engine.Connection.rollback`
methods, which act upon a transaction that is now begun automatically when
a statement is first invoked::
    # 1.4 / 2.0 code
    from sqlalchemy import create_engine
    engine = create_engine(..., future=True)
    with engine.connect() as conn:
        conn.execute(some_table.insert().values(foo="bar"))
        conn.commit()
        conn.execute(text("some other SQL"))
        conn.rollback()
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L1781">
The string calling form is ambiguous and requires that the internals do extra
work to determine the appropriate path and retrieve the correct mapped
property. By passing the ORM mapped attribute directly, not only is the
necessary information passed up front, the attribute is also typed and is
more potentially compatible with IDEs and pep-484 integrations.
ORM Query - Chaining using lists of attributes, rather than individual calls, removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Synopsis**
"Chained" forms of joining and loader options which accept multiple mapped
attributes in a list will be removed::
    # chaining removed
    q = session.query(User).join("orders", "items", "keywords")
**Migration to 2.0**
Use individual calls to :meth:`_orm.Query.join` for 1.x /2.0 cross compatible
use::
</untrusted>

<untrusted source="https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/doc/build/changelog/migration_20.rst#L1012">
This :class:`.Row` behaves like a named tuple, in that it acts as a sequence
but also supports attribute name access, e.g. ``row.some_column``.  However,
it also provides the previous "mapping" behavior via the special attribute
``row._mapping``, which produces a Python mapping such that keyed access
such as ``row["some_column"]`` can be used.
In order to receive results as mappings up front, the ``mappings()`` modifier
on the result can be used::
    from sqlalchemy.future.orm import Session
    session = Session(some_engine)
    result = session.execute(stmt)
    for row in result.mappings():
        print("the user is: %s" % row["User"])
The :class:`.Row` class as used by the ORM also supports access via entity
or attribute::
    from sqlalchemy.future import select
    stmt = select(User, Address).join(User.addresses)
</untrusted>