"""
n8n webhook endpoints.

These endpoints allow n8n to communicate with the FastAPI application.
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from database.db import get_db
from api.utils.logging import log_event, EventType

router = APIRouter()


@router.post("/webhooks/n8n/message")
async def receive_n8n_message(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive messages from n8n workflows.
    
    This endpoint allows n8n to send data to the FastAPI application.
    """
    try:
        data = await request.json()
        
        # Log the incoming message
        log_event(
            db=db,
            event_type=EventType.AGENT_DECISION,
            agent_name="n8n",
            message=f"Received message from n8n: {json.dumps(data)}",
            metadata={"source": "n8n", "data": data}
        )
        
        return JSONResponse(content={
            "status": "received",
            "message": "Message received from n8n",
            "data": data
        })
    
    except Exception as e:
        print(f"Error processing n8n message: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.post("/webhooks/n8n/trigger")
async def trigger_n8n_workflow(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger n8n workflows from agents.
    
    This endpoint receives trigger requests and can be used to call n8n webhooks.
    """
    try:
        data = await request.json()
        workflow_type = data.get("workflow_type")
        payload = data.get("payload", {})
        
        # Log the trigger request
        log_event(
            db=db,
            event_type=EventType.AGENT_DECISION,
            agent_name="Agent",
            message=f"Triggering n8n workflow: {workflow_type}",
            metadata={"workflow_type": workflow_type, "payload": payload}
        )
        
        # This will be enhanced in Step 14 to actually call n8n webhooks
        # For now, just acknowledge the request
        return JSONResponse(content={
            "status": "triggered",
            "workflow_type": workflow_type,
            "message": "Workflow trigger request received (n8n webhook call will be implemented in Step 14)",
            "payload": payload
        })
    
    except Exception as e:
        print(f"Error triggering n8n workflow: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.get("/webhooks/n8n/health")
async def n8n_health_check():
    """Health check endpoint for n8n to verify connection."""
    return {
        "status": "healthy",
        "service": "Airbnb Property Operations Manager API",
        "n8n_integration": "ready"
    }


@router.post("/webhooks/n8n/booking-confirmed")
async def handle_booking_confirmed(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle booking confirmation workflow from n8n.
    
    This will be called by n8n when a booking is confirmed.
    """
    try:
        data = await request.json()
        booking_id = data.get("booking_id")
        
        log_event(
            db=db,
            event_type=EventType.BOOKING_CONFIRMED,
            agent_name="n8n",
            booking_id=booking_id,
            message=f"Booking {booking_id} confirmed via n8n workflow",
            metadata={"source": "n8n", "data": data}
        )
        
        return JSONResponse(content={
            "status": "processed",
            "booking_id": booking_id,
            "message": "Booking confirmation processed"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.post("/webhooks/n8n/cleaning-scheduled")
async def handle_cleaning_scheduled(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle cleaning scheduled workflow from n8n.
    
    This will be called by n8n when cleaning is scheduled.
    """
    try:
        data = await request.json()
        task_id = data.get("task_id")
        
        log_event(
            db=db,
            event_type=EventType.CLEANING_SCHEDULED,
            agent_name="n8n",
            message=f"Cleaning task {task_id} scheduled via n8n",
            metadata={"source": "n8n", "data": data}
        )
        
        return JSONResponse(content={
            "status": "processed",
            "task_id": task_id,
            "message": "Cleaning scheduled processed"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

