"""
Webhooks Router
---------------
API endpoints for webhook configuration and management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas
from app.tasks import test_webhook as test_webhook_task

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Available webhook events
WEBHOOK_EVENTS = [
    "product.created",
    "product.updated",
    "product.deleted",
    "bulk.imported",
    "bulk.deleted",
]


@router.get("/events", response_model=List[str])
def list_webhook_events():
    """List all available webhook event types."""
    return WEBHOOK_EVENTS


@router.get("", response_model=List[schemas.WebhookResponse])
def list_webhooks(db: Session = Depends(get_db)):
    """List all configured webhooks."""
    return crud.get_webhooks(db)


@router.get("/{webhook_id}", response_model=schemas.WebhookResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Get a single webhook by ID."""
    webhook = crud.get_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.post("", response_model=schemas.WebhookResponse, status_code=201)
def create_webhook(webhook: schemas.WebhookCreate, db: Session = Depends(get_db)):
    """
    Create a new webhook.
    
    Available events: product.created, product.updated, product.deleted,
    bulk.imported, bulk.deleted
    """
    # Validate events
    invalid_events = [e for e in webhook.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}. Available: {WEBHOOK_EVENTS}"
        )
    
    return crud.create_webhook(db, webhook)


@router.put("/{webhook_id}", response_model=schemas.WebhookResponse)
def update_webhook(
    webhook_id: int,
    webhook: schemas.WebhookUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing webhook."""
    # Validate events if provided
    if webhook.events:
        invalid_events = [e for e in webhook.events if e not in WEBHOOK_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid events: {invalid_events}. Available: {WEBHOOK_EVENTS}"
            )
    
    db_webhook = crud.update_webhook(db, webhook_id, webhook)
    if not db_webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return db_webhook


@router.delete("/{webhook_id}", response_model=schemas.MessageResponse)
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Delete a webhook by ID."""
    success = crud.delete_webhook(db, webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted successfully", "success": True}


@router.post("/{webhook_id}/test", response_model=schemas.WebhookTestResult)
def test_webhook_endpoint(webhook_id: int, db: Session = Depends(get_db)):
    """
    Test a webhook by sending a test payload.
    
    Returns the response status code and response time.
    This call is synchronous for immediate feedback.
    """
    webhook = crud.get_webhook(db, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Execute test synchronously for immediate feedback
    result = test_webhook_task(webhook.url)
    return result