"""
Products Router
---------------
API endpoints for product CRUD operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas
from app.tasks import trigger_webhooks

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=schemas.ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    List products with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    - **search**: Search in SKU, name, description
    - **active**: Filter by active status
    """
    skip = (page - 1) * page_size
    products, total = crud.get_products(
        db, skip=skip, limit=page_size, search=search, active=active
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "items": products,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=schemas.ProductResponse, status_code=201)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product.
    
    SKU must be unique (case-insensitive).
    """
    # Check for existing SKU
    existing = crud.get_product_by_sku(db, product.sku)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Product with SKU '{product.sku}' already exists"
        )
    
    db_product = crud.create_product(db, product)
    
    # Trigger webhook
    trigger_webhooks("product.created", db_product.to_dict())
    
    return db_product


@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing product."""
    db_product = crud.update_product(db, product_id, product)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Trigger webhook
    trigger_webhooks("product.updated", db_product.to_dict())
    
    return db_product


@router.delete("/{product_id}", response_model=schemas.MessageResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product by ID."""
    # Get product info before deletion for webhook
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = product.to_dict()
    success = crud.delete_product(db, product_id)
    
    if success:
        # Trigger webhook
        trigger_webhooks("product.deleted", product_data)
        return {"message": "Product deleted successfully", "success": True}
    
    raise HTTPException(status_code=500, detail="Failed to delete product")


@router.delete("", response_model=schemas.MessageResponse)
def delete_all_products(
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    db: Session = Depends(get_db),
):
    """
    Delete ALL products.
    
    This is a destructive operation. Pass confirm=true to proceed.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm deletion by setting confirm=true"
        )
    
    count = crud.delete_all_products(db)
    
    # Trigger webhook
    trigger_webhooks("bulk.deleted", {"count": count})
    
    return {
        "message": f"Successfully deleted {count} products",
        "success": True,
    }