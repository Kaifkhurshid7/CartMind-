from typing import Any

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: str
    name: str
    brand: str = ""
    category: str = ""
    price: float
    currency: str = "INR"
    specs: dict[str, Any] = Field(default_factory=dict)
    rating: float = 0.0
    review_count: int = 0
    available: bool = True
    url: str = ""
    source: str = ""
    features: list[str] = Field(default_factory=list)
    suitability: float | None = None
    score_breakdown: dict[str, float] | None = None
