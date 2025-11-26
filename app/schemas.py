"""
Pydantic Schemas
----------------
Request and response validation schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ============ Product Schemas ============

class ProductBase(BaseModel):
    """Base product fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(default=0.0, ge=0)
    quantity: Optional[int] = Field(default=0, ge=0)
    active: bool = True


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    sku: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('sku')
    @classmethod
    def lowercase_sku(cls, v: str) -> str:
        """Store SKU in lowercase for case-insensitive matching."""
        return v.strip().lower()


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: int
    sku: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Webhook Schemas ============

class WebhookBase(BaseModel):
    """Base webhook fields."""
    url: str = Field(..., min_length=1, max_length=500)
    events: List[str] = Field(default_factory=list)
    enabled: bool = True


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""
    pass


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    url: Optional[str] = Field(None, max_length=500)
    events: Optional[List[str]] = None
    enabled: Optional[bool] = None


class WebhookResponse(WebhookBase):
    """Schema for webhook response."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WebhookTestResult(BaseModel):
    """Result of testing a webhook."""
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


# ============ Upload Schemas ============

class UploadStatus(BaseModel):
    """Upload task status response."""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0  # 0-100
    total_rows: int = 0
    processed_rows: int = 0
    message: str = ""
    errors: List[str] = Field(default_factory=list)


# ============ General Schemas ============

class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True