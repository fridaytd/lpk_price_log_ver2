from pydantic import BaseModel

from typing import Generic, TypeVar

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: str
    data: T


class Product(BaseModel):
    code: str
    category_code: str
    name: str
    provider_code: str
    price: int
    process_time: int
    country_code: str
    status: str


class ProductResponse(BaseModel):
    products: list[Product]
