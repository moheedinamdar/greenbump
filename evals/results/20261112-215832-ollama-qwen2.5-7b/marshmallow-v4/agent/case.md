## Upgrade
- marshmallow 3.26.2 -> 4.4.0

## Test run after the upgrade: 0 passed, 0 failed, 1 errors
```text
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_schemas.py ____________________
tests/test_schemas.py:4: in <module>
    from accounts.schemas import dump_user, load_user
accounts/schemas.py:4: in <module>
    class UserSchema(Schema):
accounts/schemas.py:7: in UserSchema
    role = fields.Str(missing="viewer")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Field.__init__() got an unexpected keyword argument 'missing'
=========================== short test summary info ============================
ERROR tests/test_schemas.py - TypeError: Field.__init__() got an unexpected k...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.06s
```

## Files that import the upgraded package(s), with line numbers
### accounts/schemas.py
```python
    1 | from marshmallow import Schema, ValidationError, fields, validates
    2 | 
    3 | 
    4 | class UserSchema(Schema):
    5 |     name = fields.Str(required=True)
    6 |     email = fields.Email(required=True)
    7 |     role = fields.Str(missing="viewer")
    8 |     active = fields.Bool(default=True)
    9 |     display = fields.Method("get_display", dump_only=True)
   10 | 
   11 |     def get_display(self, obj):
   12 |         prefix = self.context.get("prefix", "")
   13 |         return f"{prefix}{obj['name']}"
   14 | 
   15 |     @validates("name")
   16 |     def validate_name(self, value):
   17 |         if len(value.strip()) < 2:
   18 |             raise ValidationError("Name is too short.")
   19 | 
   20 | 
   21 | def load_user(data):
   22 |     return UserSchema().load(data)
   23 | 
   24 | 
   25 | def dump_user(user, prefix=""):
   26 |     return UserSchema(context={"prefix": prefix}).dump(user)
```

### tests/test_schemas.py
```python
    1 | import pytest
    2 | from marshmallow import ValidationError
    3 | 
    4 | from accounts.schemas import dump_user, load_user
    5 | 
    6 | 
    7 | def test_load_applies_default_role():
    8 |     user = load_user({"name": "Ada", "email": "ada@example.com"})
    9 |     assert user == {"name": "Ada", "email": "ada@example.com", "role": "viewer"}
   10 | 
   11 | 
   12 | def test_load_rejects_short_name():
   13 |     with pytest.raises(ValidationError) as info:
   14 |         load_user({"name": "A", "email": "a@example.com"})
   15 |     assert info.value.messages == {"name": ["Name is too short."]}
   16 | 
   17 | 
   18 | def test_dump_fills_active_and_display():
   19 |     out = dump_user({"name": "Ada", "email": "ada@example.com", "role": "admin"}, prefix="Dr. ")
   20 |     assert out == {
   21 |         "name": "Ada",
   22 |         "email": "ada@example.com",
   23 |         "role": "admin",
   24 |         "active": True,
   25 |         "display": "Dr. Ada",
   26 |     }
   27 | 
   28 | 
   29 | def test_dump_without_prefix():
   30 |     out = dump_user({"name": "Ada", "email": "ada@example.com", "role": "admin", "active": False})
   31 |     assert out["display"] == "Ada"
   32 |     assert out["active"] is False
```

## Upstream notes that may be relevant
Search queries used: missing, TypeError: Field.__init__() got an unexpected keyword argument 'missing'

<untrusted source="https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/docs/upgrading.rst#L563">
    # 3.x
    schema = UserSchema()
    # There is only one right way
    try:
        data = schema.load({"name": "Monty", "email": "monty@python.org"})
    except ValidationError as err:
        errors = err.messages
        valid_data = err.valid_data
`Schema.validate <marshmallow.Schema.validate>` always returns a dictionary of validation errors (same as 2.x with ``strict=False``).
.. code-block:: python
    schema.validate({"email": "invalid"})
    # {'email': ['Not a valid email address.']}
Setting the ``strict`` option on `class Meta <marshmallow.Schema.Meta>` has no effect on `Schema <marshmallow.Schema>` behavior.
Passing ``strict=True`` or ``strict=False`` to the `Schema <marshmallow.Schema>` constructor
will raise a :exc:`TypeError`.
.. code-block:: python
    # 3.x
    UserSchema(strict=True)
    # TypeError: __init__() got an unexpected keyword argument 'strict'
.. seealso::
</untrusted>

<untrusted source="https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/docs/upgrading.rst#L179">
*****************************************************************************
Subclasses of `marshmallow.SchemaOpts` should remove the ``ordered`` argument from the constructor.
.. code-block:: python
    # 3.x
    class CustomOpts(SchemaOpts):
        def __init__(self, meta, ordered=False):
            super().__init__(meta, ordered=ordered)
            self.custom_option = getattr(meta, "custom_option", False)
    # 4.x
    class CustomOpts(SchemaOpts):
        def __init__(self, meta):
            super().__init__(meta)
            self.custom_option = getattr(meta, "custom_option", False)
``TimeDelta`` changes
*********************
The `TimeDelta <marshmallow.fields.TimeDelta>` field now preserves float values such that
microseconds are included in the resulting `datetime.timedelta` object.
.. code-block:: python
    from marshmallow import fields
</untrusted>

<untrusted source="https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/CHANGELOG.rst#L252">
- The ``ordered`` `class Meta <marshmallow.Schema.Meta>` option is removed  (:issue:`2146`) (deprecated in 3.26.0).
- *Backwards-incompatible*: `marshmallow.fields.Number` is no longer usable as a field in a schema (deprecated in 3.24.0).
  Use `marshmallow.fields.Integer`, `marshmallow.fields.Float`, or `marshmallow.fields.Decimal` instead.
- *Backwards-incompatible*: `marshmallow.fields.Mapping` is no longer usable as a field in a schema (deprecated in 3.24.0).
- *Backwards-incompatible*: Custom validators must raise a `ValidationError <marshmallow.exceptions.ValidationError>` for invalid values (deprecated in 3.24.0).
  Returning `False` is no longer supported (:issue:`1775`).
  Use `marshmallow.fields.Dict` instead.
- Remove ``__version__``, ``__parsed_version__``, and ``__version_info__`` attributes (deprecated in 3.21.0).
- `default` and `missing` parameters, which were replaced by `dump_default` and `load_default` in 3.13.0 (:pr:`1742`, :pr:`2700`).
- Passing field metadata via keyword arguments (deprecated in 3.10.0). Use the explicit ``metadata=...``
  argument instead (:issue:`1350`).
- `marshmallow.utils.pprint` (deprecated in 3.7.0). Use `pprint.pprint` instead.
- Passing `"self"` to `fields.Nested` (deprecated in 3.3.0). Use a callable instead.
- ``Field.fail``, which was replaced by ``Field.make_error`` in 3.0.0.
- `json_module` class Meta option (deprecated in 3.0.0b3). Use `render_module` instead.
</untrusted>

<untrusted source="https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/CHANGELOG.rst#L638">
3.13.0 (2021-07-21)
-------------------
Features:
- Replace ``missing``/``default`` field parameters with
  ``load_default``/``dump_default`` (:pr:`1742`).
  Thanks :user:`sirosen` for the PR.
Deprecations:
- The use of ``missing``/``default`` field parameters is deprecated and will be
  removed in marshmallow 4. ``load_default``/``dump_default`` should be used
  instead.
3.12.2 (2021-07-06)
-------------------
Bug fixes:
- Don't expose ``Field``\s as ``Schema`` attributes. This reverts a change
  introduced in 3.12.0 that causes issues when field names conflict with
  ``Schema`` attributes or methods. ``Fields``\s are still accessible on a
  ``Schema`` instance through the ``fields`` attribute. (:pr:`1843`)
3.12.1 (2021-05-10)
-------------------
Bug fixes:
</untrusted>