"""
Database Models
---------------
SQLAlchemy ORM models for Products and Webhooks.
Compatible with both SQLite and PostgreSQL.
"""

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Index, TypeDecorator
from sqlalchemy.sql import func
from app.database import Base


class JSONType(TypeDecorator):
    """
    Custom type for JSON storage.
    Works with both SQLite (as TEXT) and PostgreSQL.
    """
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class Product(Base):
    """
    Product model.
    
    SKU is stored in lowercase for case-insensitive uniqueness.
    The active field allows marking products without CSV support.
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True, default=0.0)
    quantity = Column(Integer, nullable=True, default=0)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "quantity": self.quantity,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Webhook(Base):
    """
    Webhook configuration model.
    
    Stores webhook URLs and the events they subscribe to.
    Events: product.created, product.updated, product.deleted, bulk.deleted
    """
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    events = Column(JSONType, nullable=False, default=list)  # List of event types
    enabled = Column(Boolean, default=True)
    secret = Column(String(100), nullable=True)  # Optional secret for signing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events or [],
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }