"""
Celery Tasks / Sync Processing
------------------------------
Async tasks for CSV processing and webhook delivery.
Falls back to synchronous processing if Redis is not available.
"""

import csv
import io
import time
import httpx
from typing import Optional
from datetime import datetime
import threading

from app.config import get_settings

settings = get_settings()

# In-memory storage for progress when Redis is not available
_progress_store = {}
_store_lock = threading.Lock()

# Try to connect to Redis, fall back to in-memory if not available
try:
    import redis
    redis_client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✓ Redis connected successfully")
except:
    REDIS_AVAILABLE = False
    redis_client = None
    print("⚠ Redis not available - using in-memory storage for progress")

# Try to import Celery, but don't fail if Redis isn't available
try:
    if REDIS_AVAILABLE:
        from app.celery_app import celery_app
        CELERY_AVAILABLE = True
    else:
        CELERY_AVAILABLE = False
        celery_app = None
except:
    CELERY_AVAILABLE = False
    celery_app = None


def update_task_progress(
    task_id: str,
    status: str,
    progress: int,
    total_rows: int = 0,
    processed_rows: int = 0,
    message: str = "",
    errors: list = None,
):
    """Store task progress in Redis or in-memory for real-time updates."""
    data = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "total_rows": total_rows,
        "processed_rows": processed_rows,
        "message": message,
        "errors": ",".join(errors) if errors else "",
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    if REDIS_AVAILABLE and redis_client:
        redis_client.hset(f"upload:{task_id}", mapping=data)
        redis_client.expire(f"upload:{task_id}", 3600)
    else:
        with _store_lock:
            _progress_store[task_id] = data


def get_task_progress(task_id: str) -> Optional[dict]:
    """Retrieve task progress from Redis or in-memory."""
    if REDIS_AVAILABLE and redis_client:
        data = redis_client.hgetall(f"upload:{task_id}")
        if not data:
            return None
        
        # Decode bytes to strings
        result = {k.decode(): v.decode() for k, v in data.items()}
    else:
        with _store_lock:
            result = _progress_store.get(task_id)
        if not result:
            return None
        result = dict(result)  # Make a copy
    
    result["progress"] = int(result.get("progress", 0))
    result["total_rows"] = int(result.get("total_rows", 0))
    result["processed_rows"] = int(result.get("processed_rows", 0))
    result["errors"] = result.get("errors", "").split(",") if result.get("errors") else []
    return result


def process_csv_sync(task_id: str, file_content: str):
    """
    Process CSV file synchronously (when Celery is not available).
    """
    from app.database import SessionLocal
    from app import crud
    
    db = SessionLocal()
    errors = []
    
    try:
        # Initial status
        update_task_progress(
            task_id=task_id,
            status="processing",
            progress=0,
            message="Parsing CSV file...",
        )
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(file_content))
        rows = list(reader)
        total_rows = len(rows)
        
        if total_rows == 0:
            update_task_progress(
                task_id=task_id,
                status="failed",
                progress=0,
                message="CSV file is empty",
            )
            return {"success": False, "error": "CSV file is empty"}
        
        update_task_progress(
            task_id=task_id,
            status="processing",
            progress=5,
            total_rows=total_rows,
            message=f"Found {total_rows} rows. Starting import...",
        )
        
        # Process in chunks
        chunk_size = settings.chunk_size
        processed = 0
        
        for i in range(0, total_rows, chunk_size):
            chunk = rows[i:i + chunk_size]
            products_data = []
            
            for row in chunk:
                try:
                    # Extract and validate fields
                    sku = row.get("sku", row.get("SKU", "")).strip()
                    if not sku:
                        errors.append(f"Row {processed + 1}: Missing SKU")
                        continue
                    
                    name = row.get("name", row.get("Name", row.get("NAME", ""))).strip()
                    if not name:
                        name = sku  # Fallback to SKU if name missing
                    
                    description = row.get("description", row.get("Description", ""))
                    
                    # Parse numeric fields safely
                    try:
                        price = float(row.get("price", row.get("Price", 0)) or 0)
                    except (ValueError, TypeError):
                        price = 0.0
                    
                    try:
                        quantity = int(row.get("quantity", row.get("Quantity", 0)) or 0)
                    except (ValueError, TypeError):
                        quantity = 0
                    
                    products_data.append({
                        "sku": sku,
                        "name": name,
                        "description": description,
                        "price": price,
                        "quantity": quantity,
                        "active": True,
                    })
                
                except Exception as e:
                    errors.append(f"Row {processed + 1}: {str(e)}")
            
            # Bulk upsert chunk
            if products_data:
                crud.bulk_upsert_products(db, products_data)
            
            processed += len(chunk)
            progress = int(5 + (processed / total_rows) * 90)
            
            update_task_progress(
                task_id=task_id,
                status="processing",
                progress=progress,
                total_rows=total_rows,
                processed_rows=processed,
                message=f"Processed {processed:,} of {total_rows:,} rows...",
                errors=errors[:10],
            )
        
        # Completed
        final_message = f"Successfully imported {processed:,} products"
        if errors:
            final_message += f" with {len(errors)} warnings"
        
        update_task_progress(
            task_id=task_id,
            status="completed",
            progress=100,
            total_rows=total_rows,
            processed_rows=processed,
            message=final_message,
            errors=errors[:10],
        )
        
        return {"success": True, "processed": processed, "errors": len(errors)}
    
    except Exception as e:
        update_task_progress(
            task_id=task_id,
            status="failed",
            progress=0,
            message=f"Import failed: {str(e)}",
            errors=[str(e)],
        )
        return {"success": False, "error": str(e)}
    
    finally:
        db.close()


def start_csv_processing(task_id: str, file_content: str):
    """
    Start CSV processing - uses Celery if available, otherwise runs in a thread.
    """
    if CELERY_AVAILABLE:
        # Use Celery for async processing
        process_csv_celery.delay(task_id, file_content)
    else:
        # Run in a background thread
        thread = threading.Thread(
            target=process_csv_sync,
            args=(task_id, file_content),
            daemon=True
        )
        thread.start()


def trigger_webhooks_sync(event: str, payload: dict):
    """Send webhook notifications synchronously."""
    from app.database import SessionLocal
    from app import crud
    
    db = SessionLocal()
    
    try:
        webhooks = crud.get_enabled_webhooks_for_event(db, event)
        
        for webhook in webhooks:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        webhook.url,
                        json={
                            "event": event,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": payload,
                        },
                    )
                    print(f"Webhook {webhook.id} -> {response.status_code}")
            
            except Exception as e:
                print(f"Webhook {webhook.id} failed: {e}")
    
    finally:
        db.close()


def trigger_webhooks(event: str, payload: dict):
    """Trigger webhooks - async if Celery available, otherwise sync in thread."""
    if CELERY_AVAILABLE:
        trigger_webhooks_celery.delay(event, payload)
    else:
        thread = threading.Thread(
            target=trigger_webhooks_sync,
            args=(event, payload),
            daemon=True
        )
        thread.start()


def test_webhook(url: str) -> dict:
    """
    Test a webhook by sending a test payload.
    Returns status code and response time.
    """
    try:
        start = time.time()
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                json={
                    "event": "test",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"message": "This is a test webhook"},
                },
            )
        elapsed = (time.time() - start) * 1000
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response_time_ms": round(elapsed, 2),
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============ Celery Tasks (only defined if Celery is available) ============

if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True)
    def process_csv_celery(self, task_id: str, file_content: str):
        """Celery task wrapper for CSV processing."""
        return process_csv_sync(task_id, file_content)
    
    @celery_app.task
    def trigger_webhooks_celery(event: str, payload: dict):
        """Celery task wrapper for webhook delivery."""
        return trigger_webhooks_sync(event, payload)