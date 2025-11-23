"""
Log management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, timedelta

from database.db import get_db
from database.models import SystemLog
from api.utils.logging import (
    get_logs_by_property,
    get_logs_by_date_range,
    get_logs_by_event_type,
    get_logs_for_summary,
    get_recent_logs,
    EventType
)

router = APIRouter()


@router.get("/logs")
async def list_logs(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[date] = Query(None, description="Start date for date range filter"),
    end_date: Optional[date] = Query(None, description="End date for date range filter"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    db: Session = Depends(get_db)
):
    """List system logs with optional filters."""
    
    if start_date and end_date:
        logs = get_logs_by_date_range(db, start_date, end_date, property_id)
    elif event_type:
        logs = get_logs_by_event_type(db, event_type, limit, property_id)
    elif property_id:
        logs = get_logs_by_property(db, property_id, limit)
    else:
        logs = get_recent_logs(db, limit, property_id)
    
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "property_id": log.property_id,
                "booking_id": log.booking_id,
                "agent_name": log.agent_name,
                "message": log.message,
                "metadata": log.get_metadata(),
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


@router.get("/logs/summary")
async def get_logs_summary(
    property_id: int = Query(..., description="Property ID"),
    start_date: date = Query(..., description="Start date for summary period"),
    end_date: date = Query(..., description="End date for summary period"),
    db: Session = Depends(get_db)
):
    """Get aggregated logs for summary report generation."""
    
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
    
    summary = get_logs_for_summary(db, property_id, start_date, end_date)
    return summary


@router.get("/logs/event-types")
async def get_event_types():
    """Get list of available event types."""
    return {
        "event_types": [
            attr for attr in dir(EventType) 
            if not attr.startswith('_') and isinstance(getattr(EventType, attr), str)
        ],
        "descriptions": {
            "guest_message": "Guest sent a message",
            "guest_inquiry": "Guest made an inquiry",
            "guest_booking_request": "Guest requested a booking",
            "guest_payment_uploaded": "Guest uploaded payment screenshot",
            "agent_decision": "Agent made a decision",
            "agent_response": "Agent sent a response",
            "agent_escalation": "Agent escalated an issue",
            "booking_created": "Booking was created",
            "booking_confirmed": "Booking was confirmed",
            "booking_cancelled": "Booking was cancelled",
            "booking_payment_approved": "Payment was approved by host",
            "booking_payment_rejected": "Payment was rejected by host",
            "cleaning_scheduled": "Cleaning task was scheduled",
            "cleaning_notified": "Cleaner was notified",
            "cleaning_confirmed": "Cleaner confirmed task",
            "cleaning_completed": "Cleaning task was completed",
            "cleaning_cancelled": "Cleaning task was cancelled",
            "issue_reported": "Guest reported an issue",
            "issue_resolved": "Issue was resolved",
            "issue_escalated": "Issue was escalated to host",
            "host_payment_approval": "Host approved payment",
            "host_payment_rejection": "Host rejected payment",
            "host_escalation_received": "Host received escalation",
            "calendar_event_created": "Calendar event was created",
            "calendar_event_updated": "Calendar event was updated",
            "calendar_event_deleted": "Calendar event was deleted",
            "system_error": "System error occurred",
            "configuration_updated": "Configuration was updated",
            "property_added": "Property was added",
            "host_setup": "Host setup was completed"
        }
    }

