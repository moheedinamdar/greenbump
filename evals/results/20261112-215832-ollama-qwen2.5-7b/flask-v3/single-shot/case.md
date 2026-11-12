## Upgrade
- flask 2.3.3 -> 3.1.3
- werkzeug 2.3.8 -> 3.1.9

## Test run after the upgrade: 0 passed, 0 failed, 1 errors
```text
==================================== ERRORS ====================================
______________________ ERROR collecting tests/test_app.py ______________________
ImportError while importing test module '<repo>/tests/test_app.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
<python>/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_app.py:3: in <module>
    from webapp.app import create_app
webapp/app.py:1: in <module>
    from flask import Flask, Markup, escape, request
E   ImportError: cannot import name 'Markup' from 'flask' (<venv>/lib/python3.13/site-packages/flask/__init__.py)
=========================== short test summary info ============================
ERROR tests/test_app.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.15s
```

## Files that import the upgraded package(s), with line numbers
### webapp/app.py
```python
    1 | from flask import Flask, Markup, escape, request
    2 | from werkzeug.urls import url_quote
    3 | 
    4 | 
    5 | def create_app():
    6 |     app = Flask(__name__)
    7 | 
    8 |     @app.get("/hello")
    9 |     def hello():
   10 |         name = request.args.get("name", "world")
   11 |         return Markup("<h1>Hello, {}!</h1>").format(name)
   12 | 
   13 |     @app.get("/link")
   14 |     def link():
   15 |         query = request.args.get("q", "")
   16 |         return f'<a href="/search?q={url_quote(query)}">{escape(query)}</a>'
   17 | 
   18 |     return app
```

## Upstream notes that may be relevant
Search queries used: Markup, ImportError: cannot import name 'Markup' from 'flask'

<untrusted source="https://raw.githubusercontent.com/pallets/flask/main/CHANGES.rst#L433">
-   Drop support for Python 3.6. :pr:`4335`
-   Update Click dependency to >= 8.0. :pr:`4008`
-   Remove previously deprecated code. :pr:`4337`
    -   The CLI does not pass ``script_info`` to app factory functions.
    -   ``config.from_json`` is replaced by
        ``config.from_file(name, load=json.load)``.
    -   ``json`` functions no longer take an ``encoding`` parameter.
    -   ``safe_join`` is removed, use ``werkzeug.utils.safe_join``
        instead.
    -   ``total_seconds`` is removed, use ``timedelta.total_seconds``
        instead.
    -   The same blueprint cannot be registered with the same name. Use
        ``name=`` when registering to specify a unique name.
    -   The test client's ``as_tuple`` parameter is removed. Use
        ``response.request.environ`` instead. :pr:`4417`
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pallets/flask/main/CHANGES.rst#L156">
-   Python 3.12 compatibility.
-   Require Werkzeug >= 2.3.7.
-   Use ``flit_core`` instead of ``setuptools`` as build backend.
-   Refactor how an app's root and instance paths are determined. :issue:`5160`
Version 2.3.2
-------------
Released 2023-05-01
-   Set ``Vary: Cookie`` header when the session is accessed, modified, or refreshed.
-   Update Werkzeug requirement to >=2.3.3 to apply recent bug fixes.
    :ghsa:`m2qf-hxjv-5gpq`
Version 2.3.1
-------------
Released 2023-04-25
-   Restore deprecated ``from flask import Markup``. :issue:`5084`
Version 2.3.0
-------------
Released 2023-04-25
-   Drop support for Python 3.7. :pr:`5072`
-   Update minimum requirements to the latest versions: Werkzeug>=2.3.0, Jinja2>3.1.2,
    itsdangerous>=2.1.2, click>=8.1.3.
-   Remove previously deprecated code. :pr:`4995`
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pallets/flask/main/CHANGES.rst#L208">
-   Importing ``escape`` and ``Markup`` from ``flask`` is deprecated. Import them
    directly from ``markupsafe`` instead. :pr:`4996`
-   The ``app.got_first_request`` property is deprecated. :pr:`4997`
-   The ``locked_cached_property`` decorator is deprecated. Use a lock inside the
    decorated function if locking is needed. :issue:`4993`
-   Signals are always available. ``blinker>=1.6.2`` is a required dependency. The
    ``signals_available`` attribute is deprecated. :issue:`5056`
-   Signals support ``async`` subscriber functions. :pr:`5049`
-   Remove uses of locks that could cause requests to block each other very briefly.
    :issue:`4993`
-   Use modern packaging metadata with ``pyproject.toml`` instead of ``setup.cfg``.
    :pr:`4947`
-   Ensure subdomains are applied with nested blueprints. :issue:`4834`
-   ``config.from_file`` can use ``text=False`` to indicate that the parser wants a
    binary file instead. :issue:`4989`
-   If a blueprint is created with an empty name it raises a ``ValueError``.
    :issue:`5010`
-   ``SESSION_COOKIE_DOMAIN`` does not fall back to ``SERVER_NAME``. The default is not
    to set the domain, which modern browsers interpret as an exact match rather than
    a subdomain match. Warnings about ``localhost`` and IP addresses are also removed.
    :issue:`5051`
-   The ``routes`` command shows each rule's ``subdomain`` or ``host`` when domain
    matching is in use. :issue:`5004`
-   Use postponed evaluation of annotations. :pr:`5071`
</untrusted>