# greenbump: NOT FIXED

- Mode: `single-shot`, model: `ollama:qwen2.5:7b`
- Stopped because: `answered`
- Tests before: 0 passed, 0 failed, 1 errors
- Tests after: 0 passed, 0 failed, 1 errors (repository defines 4 test functions)
- Steps: 1, model calls: 1, tokens in/out: 2388/83, time: 74.2s
- Edits applied: 1, edits refused by guardrails: 0

## Why it does not count as a fix
- tests do not pass: 0 passed, 0 failed, 1 errors

## Model's summary

Updated the `missing` parameter to `default` in the `UserSchema` class to make it compatible with the new version of marshmallow.

## Patch

```diff
--- a/accounts/schemas.py
+++ b/accounts/schemas.py
@@ -4,7 +4,7 @@
 class UserSchema(Schema):
     name = fields.Str(required=True)
     email = fields.Email(required=True)
-    role = fields.Str(missing="viewer")
+    role = fields.Str(default="viewer")
     active = fields.Bool(default=True)
     display = fields.Method("get_display", dump_only=True)
```

## Changelog sources (untrusted)
- https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/docs/upgrading.rst
- https://raw.githubusercontent.com/marshmallow-code/marshmallow/dev/CHANGELOG.rst

## Final test output

```text
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_schemas.py ____________________
tests/test_schemas.py:4: in <module>
    from accounts.schemas import dump_user, load_user
accounts/schemas.py:4: in <module>
    class UserSchema(Schema):
accounts/schemas.py:7: in UserSchema
    role = fields.Str(default="viewer")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Field.__init__() got an unexpected keyword argument 'default'
=========================== short test summary info ============================
ERROR tests/test_schemas.py - TypeError: Field.__init__() got an unexpected k...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.15s
```
