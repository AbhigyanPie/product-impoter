"""
CRUD Operations
---------------
Database operations for Products and Webhooks.
Compatible with both SQLite and PostgreSQL.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

from app.models import Product, Webhook
from app.schemas import ProductCreate, ProductUpdate, WebhookCreate, WebhookUpdate
from app.config import get_settings

settings = get_settings()


# ============ Product Operations ============

def get_product(db: Session, product_id: int) -> Optional[Product]:
    """Get a single product by ID."""
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    """Get a product by SKU (case-insensitive)."""
    return db.query(Product).filter(Product.sku == sku.lower()).first()


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    active: Optional[bool] = None,
) -> Tuple[List[Product], int]:
    """
    Get paginated list of products with optional filtering.
    Returns tuple of (products, total_count).
    """
    query = db.query(Product)
    
    # Apply filters
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Product.sku.ilike(search_term),
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )
    
    if active is not None:
        query = query.filter(Product.active == active)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination and ordering
    products = query.order_by(Product.id.desc()).offset(skip).limit(limit).all()
    
    return products, total


def create_product(db: Session, product: ProductCreate) -> Product:
    """Create a new product."""
    db_product = Product(
        sku=product.sku.lower(),
        name=product.name,
        description=product.description,
        price=product.price,
        quantity=product.quantity,
        active=product.active,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product: ProductUpdate) -> Optional[Product]:
    """Update an existing product."""
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    # Update only provided fields
    update_data = product.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db_product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete a product by ID."""
    db_product = get_product(db, product_id)
    if not db_product:
        return False
    
    db.delete(db_product)
    db.commit()
    return True


def delete_all_products(db: Session) -> int:
    """Delete all products. Returns count of deleted items."""
    count = db.query(Product).count()
    db.query(Product).delete()
    db.commit()
    return count


def bulk_upsert_products(db: Session, products_data: List[dict]) -> int:
    """
    Bulk upsert products.
    Works with both SQLite and PostgreSQL.
    Updates existing products based on SKU (case-insensitive).
    Returns count of affected rows.
    """
    if not products_data:
        return 0
    
    affected = 0
    
    for p in products_data:
        sku = p['sku'].lower().strip()
        
        # Check if product exists
        existing = db.query(Product).filter(Product.sku == sku).first()
        
        if existing:
            # Update existing product
            existing.name = p.get('name', existing.name)
            existing.description = p.get('description', existing.description)
            existing.price = p.get('price', existing.price)
            existing.quantity = p.get('quantity', existing.quantity)
            existing.updated_at = datetime.utcnow()
        else:
            # Create new product
            new_product = Product(
                sku=sku,
                name=p.get('name', sku),
                description=p.get('description'),
                price=p.get('price', 0.0),
                quantity=p.get('quantity', 0),
                active=p.get('active', True),
            )
            db.add(new_product)
        
        affected += 1
    
    db.commit()
    return affected


# ============ Webhook Operations ============

def get_webhook(db: Session, webhook_id: int) -> Optional[Webhook]:
    """Get a single webhook by ID."""
    return db.query(Webhook).filter(Webhook.id == webhook_id).first()


def get_webhooks(db: Session) -> List[Webhook]:
    """Get all webhooks."""
    return db.query(Webhook).order_by(Webhook.id.desc()).all()


def get_enabled_webhooks_for_event(db: Session, event: str) -> List[Webhook]:
    """Get all enabled webhooks that subscribe to a specific event."""
    webhooks = db.query(Webhook).filter(Webhook.enabled == True).all()
    # Filter by event in Python (works with both SQLite and PostgreSQL)
    return [w for w in webhooks if event in (w.events or [])]


def create_webhook(db: Session, webhook: WebhookCreate) -> Webhook:
    """Create a new webhook."""
    db_webhook = Webhook(
        url=webhook.url,
        events=webhook.events,
        enabled=webhook.enabled,
    )
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook


def update_webhook(db: Session, webhook_id: int, webhook: WebhookUpdate) -> Optional[Webhook]:
    """Update an existing webhook."""
    db_webhook = get_webhook(db, webhook_id)
    if not db_webhook:
        return None
    
    update_data = webhook.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_webhook, field, value)
    
    db_webhook.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_webhook)
    return db_webhook


def delete_webhook(db: Session, webhook_id: int) -> bool:
    """Delete a webhook by ID."""
    db_webhook = get_webhook(db, webhook_id)
    if not db_webhook:
        return False
    
    db.delete(db_webhook)
    db.commit()
    return True