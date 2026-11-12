## Upgrade
- pydantic 1.10.27 -> 2.14.3

## Test run after the upgrade: 0 passed, 0 failed, 1 errors
```text
==================================== ERRORS ====================================
____________________ ERROR collecting tests/test_models.py _____________________
tests/test_models.py:6: in <module>
    from inventory.models import Item, Order
inventory/models.py:6: in <module>
    class Item(BaseModel):
inventory/models.py:7: in Item
    sku: str = Field(..., regex=r"^[A-Z]{3}-\d{4}$")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
../../../../../../.greenbump-cache/venvs/pydantic-v2-33e1efc1febe/lib/python3.13/site-packages/pydantic/fields.py:1481: in Field
    raise PydanticUserError('`regex` is removed. use `pattern` instead', code='removed-kwargs')
E   pydantic.errors.PydanticUserError: `regex` is removed. use `pattern` instead
E   
E   For further information visit https://errors.pydantic.dev/2.14/u/removed-kwargs
=========================== short test summary info ============================
ERROR tests/test_models.py - pydantic.errors.PydanticUserError: `regex` is re...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.12s
```

## Files that import the upgraded package(s), with line numbers
### inventory/models.py
```python
    1 | from typing import List, Optional
    2 | 
    3 | from pydantic import BaseModel, Field, root_validator, validator
    4 | 
    5 | 
    6 | class Item(BaseModel):
    7 |     sku: str = Field(..., regex=r"^[A-Z]{3}-\d{4}$")
    8 |     name: str
    9 |     price: float
   10 |     quantity: int = 0
   11 |     tags: List[str] = []
   12 | 
   13 |     @validator("name")
   14 |     def name_not_blank(cls, value):
   15 |         if not value.strip():
   16 |             raise ValueError("name must not be blank")
   17 |         return value.strip()
   18 | 
   19 |     @root_validator
   20 |     def price_not_negative(cls, values):
   21 |         if values.get("price", 0) < 0:
   22 |             raise ValueError("price must not be negative")
   23 |         return values
   24 | 
   25 | 
   26 | class Order(BaseModel):
   27 |     order_id: int
   28 |     items: List[Item]
   29 |     note: Optional[str]
   30 | 
   31 |     def total(self) -> float:
   32 |         return sum(item.price * item.quantity for item in self.items)
   33 | 
   34 |     def to_json(self) -> str:
   35 |         return self.json(indent=2, sort_keys=True)
```

### tests/test_models.py
```python
    1 | import json
    2 | 
    3 | import pytest
    4 | from pydantic import ValidationError
    5 | 
    6 | from inventory.models import Item, Order
    7 | 
    8 | 
    9 | def make_item(**overrides):
   10 |     data = {"sku": "ABC-1234", "name": " Widget ", "price": 2.5, "quantity": 4}
   11 |     data.update(overrides)
   12 |     return Item(**data)
   13 | 
   14 | 
   15 | def test_item_name_is_stripped():
   16 |     assert make_item().name == "Widget"
   17 | 
   18 | 
   19 | def test_sku_pattern_is_enforced():
   20 |     with pytest.raises(ValidationError):
   21 |         make_item(sku="bad-sku")
   22 | 
   23 | 
   24 | def test_blank_name_is_rejected():
   25 |     with pytest.raises(ValidationError):
   26 |         make_item(name="   ")
   27 | 
   28 | 
   29 | def test_negative_price_is_rejected():
   30 |     with pytest.raises(ValidationError):
   31 |         make_item(price=-1)
   32 | 
   33 | 
   34 | def test_order_note_is_optional():
   35 |     order = Order(order_id=1, items=[make_item()])
   36 |     assert order.note is None
   37 | 
   38 | 
   39 | def test_order_total():
   40 |     order = Order(order_id=1, items=[make_item(), make_item(quantity=2)], note=None)
   41 |     assert order.total() == 15.0
   42 | 
   43 | 
   44 | def test_order_json_is_pretty_and_sorted():
   45 |     order = Order(order_id=7, items=[make_item()], note="rush")
   46 |     text = order.to_json()
   47 |     assert text.startswith("{\n  ")
   48 |     data = json.loads(text)
   49 |     assert list(data) == sorted(data)
   50 |     assert list(data["items"][0]) == sorted(data["items"][0])
   51 |     assert data["items"][0]["sku"] == "ABC-1234"
```

## Upstream notes that may be relevant
Search queries used: regex, pattern, PydanticUserError, pydantic.errors.PydanticUserError: `regex` is removed. use `pattern` instead, For further information visit https://errors.pydantic.dev/2.14/u/removed-kwargs

<untrusted source="https://raw.githubusercontent.com/pydantic/pydantic/main/docs/migration.md#L58">
Pydantic V1 is still available when you need it, though we recommend migrating to
Pydantic V2 for its improvements and new features.
If you need to use latest Pydantic V1, you can install it with:
```bash
pip install "pydantic==1.*"
```
The Pydantic V2 package also continues to provide access to the Pydantic V1 API
by importing through `pydantic.v1`.
For example, you can use the `BaseModel` class from Pydantic V1 instead of the
Pydantic V2 `pydantic.BaseModel` class:
```python {test="skip" lint="skip" upgrade="skip"}
from pydantic.v1 import BaseModel
```
You can also import functions that have been removed from Pydantic V2, such as `lenient_isinstance`:
```python {test="skip" lint="skip" upgrade="skip"}
from pydantic.v1.utils import lenient_isinstance
```
See the [Pydantic V1 documentation](https://pydantic.dev/docs/validation/1.10/overview/).
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pydantic/pydantic/main/docs/migration.md#L865">
assert str(AnyUrl(url='https://google.com')) == 'https://google.com/'
assert str(AnyUrl(url='https://google.com/')) == 'https://google.com/'
assert str(AnyUrl(url='https://google.com/api')) == 'https://google.com/api'
assert str(AnyUrl(url='https://google.com/api/')) == 'https://google.com/api/'
```
If you still want to use the old behavior without the appended slash, take a look at this [solution](https://github.com/pydantic/pydantic/issues/7186#issuecomment-1690235887).
### Constrained types
The `Constrained*` classes were *removed*, and you should replace them by `Annotated[<type>, Field(...)]`, for example:
```python {test="skip"}
from pydantic import BaseModel, ConstrainedInt
class MyInt(ConstrainedInt):
    ge = 0
class Model(BaseModel):
    x: MyInt
```
...becomes:
```python
from typing import Annotated
from pydantic import BaseModel, Field
MyInt = Annotated[int, Field(ge=0)]
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pydantic/pydantic/main/docs/migration.md#L298">
Field constraints are no longer automatically pushed down to the parameters of generics.  For example, you can no longer validate every element of a list matches a regex by providing `my_list: list[str] = Field(pattern=".*")`.  Instead, use [`typing.Annotated`][] to provide an annotation on the `str` itself: `my_list: list[Annotated[str, Field(pattern=".*")]]`
### Changes to dataclasses
Pydantic [dataclasses](concepts/dataclasses.md) continue to be useful for enabling the data validation on standard
dataclasses without having to subclass `BaseModel`. Pydantic V2 introduces the following changes to this dataclass behavior:
</untrusted>

<untrusted source="https://raw.githubusercontent.com/pydantic/pydantic/main/docs/migration.md#L282">
`Field` no longer supports arbitrary keyword arguments to be added to the JSON schema. Instead, any extra
data you want to add to the JSON schema should be passed as a dictionary to the `json_schema_extra` keyword argument.
In Pydantic V1, the `alias` property returns the field's name when no alias is set.
In Pydantic V2, this behavior has changed to return `None` when no alias is set.
The following properties have been removed from or changed in `Field`:
* `const`
* `min_items` (use `min_length` instead)
* `max_items` (use `max_length` instead)
* `unique_items`
* `allow_mutation` (use `frozen` instead)
* `regex` (use `pattern` instead)
* `final` (use the [typing.Final][] type hint instead)
</untrusted>