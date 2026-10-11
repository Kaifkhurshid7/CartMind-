from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)


class StartResponse(BaseModel):
    session_id: str
    status: str = "started"


class ApproveRequest(BaseModel):
    product_id: str | None = None
    approved: bool = True
    accept_price_change: bool = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    action: str | None = None  # e.g. "request_approval", "replanning", "cancelled"


class StatusResponse(BaseModel):
    session_id: str
    status: str
    current_step: str
    error: str | None = None


class SessionOut(BaseModel):
    id: str
    query: str
    status: str
    current_step: str
    requirements: dict[str, Any] = Field(default_factory=dict)
    search_count: int = 0
    shortlisted_products: list[dict[str, Any]] = Field(default_factory=list)
    comparison: dict[str, Any] = Field(default_factory=dict)
    review_analysis: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any] = Field(default_factory=dict)
    cart_state: dict[str, Any] = Field(default_factory=dict)
    browser_state: dict[str, Any] = Field(default_factory=dict)
    near_misses: list[dict[str, Any]] = Field(default_factory=list)
    price_change: dict[str, Any] | None = None
    user_prompt: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
