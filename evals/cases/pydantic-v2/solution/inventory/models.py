import json
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Item(BaseModel):
    sku: str = Field(..., pattern=r"^[A-Z]{3}-\d{4}$")
    name: str
    price: float
    quantity: int = 0
    tags: List[str] = []

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def price_not_negative(self):
        if self.price < 0:
            raise ValueError("price must not be negative")
        return self


class Order(BaseModel):
    order_id: int
    items: List[Item]
    note: Optional[str] = None

    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2, sort_keys=True)
