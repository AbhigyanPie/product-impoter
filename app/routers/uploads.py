"""
Uploads Router
--------------
API endpoints for CSV file upload and progress tracking.
"""

import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from app.tasks import start_csv_processing, get_task_progress
from app.config import get_settings
from app import schemas

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
settings = get_settings()


@router.post("", response_model=schemas.UploadStatus)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file for processing.
    
    The file is processed asynchronously (via Celery if available, otherwise in a thread).
    Returns a task_id that can be used to track progress.
    
    Expected CSV columns: sku, name, description, price, quantity
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted"
        )
    
    # Check file size (approximate)
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )
    
    # Decode content
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            file_content = content.decode('latin-1')
        except:
            raise HTTPException(
                status_code=400,
                detail="Could not decode file. Please ensure UTF-8 encoding."
            )
    
    # Generate task ID and start processing
    task_id = str(uuid.uuid4())
    start_csv_processing(task_id, file_content)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "total_rows": 0,
        "processed_rows": 0,
        "message": "Upload received. Processing started.",
        "errors": [],
    }


@router.get("/{task_id}", response_model=schemas.UploadStatus)
def get_upload_status(task_id: str):
    """Get the current status of an upload task."""
    progress = get_task_progress(task_id)
    
    if not progress:
        raise HTTPException(
            status_code=404,
            detail="Task not found or expired"
        )
    
    return progress


@router.get("/{task_id}/stream")
async def stream_upload_status(task_id: str):
    """
    Stream upload progress via Server-Sent Events (SSE).
    
    The client receives real-time updates as the CSV is processed.
    Connection closes when processing completes or fails.
    """
    async def event_generator():
        last_progress = -1
        retries = 0
        max_retries = 5
        
        while True:
            progress = get_task_progress(task_id)
            
            if not progress:
                retries += 1
                if retries >= max_retries:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "Task not found"})
                    }
                    break
                await asyncio.sleep(0.5)
                continue
            
            retries = 0
            current_progress = progress.get("progress", 0)
            
            # Only send if progress changed
            if current_progress != last_progress:
                last_progress = current_progress
                yield {
                    "event": "progress",
                    "data": json.dumps(progress)
                }
            
            # Check if complete
            status = progress.get("status", "")
            if status in ("completed", "failed"):
                yield {
                    "event": "complete",
                    "data": json.dumps(progress)
                }
                break
            
            await asyncio.sleep(0.3)
    
    return EventSourceResponse(event_generator())