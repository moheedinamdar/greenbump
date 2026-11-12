from typing import List, Optional

from pydantic import BaseModel, Field, root_validator, validator


class Item(BaseModel):
    sku: str = Field(..., regex=r"^[A-Z]{3}-\d{4}$")
    name: str
    price: float
    quantity: int = 0
    tags: List[str] = []

    @validator("name")
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @root_validator
    def price_not_negative(cls, values):
        if values.get("price", 0) < 0:
            raise ValueError("price must not be negative")
        return values


class Order(BaseModel):
    order_id: int
    items: List[Item]
    note: Optional[str]

    def total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    def to_json(self) -> str:
        return self.json(indent=2, sort_keys=True)
