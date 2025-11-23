"""
System logging utilities.

This module provides functions for logging system events to the database.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from database.models import SystemLog
import json


# Event type constants
class EventType:
    """Constants for system event types."""
    
    # Guest interactions
    GUEST_MESSAGE = "guest_message"
    GUEST_INQUIRY = "guest_inquiry"
    GUEST_BOOKING_REQUEST = "guest_booking_request"
    GUEST_PAYMENT_UPLOADED = "guest_payment_uploaded"
    
    # Agent actions
    AGENT_DECISION = "agent_decision"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"
    AGENT_ESCALATION = "agent_escalation"
    
    # Booking events
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_PAYMENT_APPROVED = "booking_payment_approved"
    BOOKING_PAYMENT_REJECTED = "booking_payment_rejected"
    
    # Cleaning events
    CLEANING_SCHEDULED = "cleaning_scheduled"
    CLEANING_NOTIFIED = "cleaning_notified"
    CLEANING_CONFIRMED = "cleaning_confirmed"
    CLEANING_COMPLETED = "cleaning_completed"
    CLEANING_CANCELLED = "cleaning_cancelled"
    
    # Issue handling
    ISSUE_REPORTED = "issue_reported"
    ISSUE_RESOLVED = "issue_resolved"
    ISSUE_ESCALATED = "issue_escalated"
    
    # Host actions
    HOST_PAYMENT_APPROVAL = "host_payment_approval"
    HOST_PAYMENT_REJECTION = "host_payment_rejection"
    HOST_ESCALATION_RECEIVED = "host_escalation_received"
    
    # Calendar events
    CALENDAR_EVENT_CREATED = "calendar_event_created"
    CALENDAR_EVENT_UPDATED = "calendar_event_updated"
    CALENDAR_EVENT_DELETED = "calendar_event_deleted"
    
    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_UPDATED = "configuration_updated"
    PROPERTY_ADDED = "property_added"
    HOST_SETUP = "host_setup"


def log_event(
    db: Session,
    event_type: str,
    agent_name: Optional[str] = None,
    property_id: Optional[int] = None,
    booking_id: Optional[int] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> SystemLog:
    """
    Log a system event to the database.
    
    Args:
        db: Database session
        event_type: Type of event (use EventType constants)
        agent_name: Name of the agent that triggered the event
        property_id: Associated property ID (optional)
        booking_id: Associated booking ID (optional)
        message: Event message
        metadata: Additional metadata as dictionary
    
    Returns:
        Created SystemLog object
    """
    log_entry = SystemLog(
        event_type=event_type,
        agent_name=agent_name,
        property_id=property_id,
        booking_id=booking_id,
        message=message
    )
    
    # Set metadata if provided
    if metadata:
        log_entry.set_metadata(metadata)
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    return log_entry


def get_logs_by_property(
    db: Session,
    property_id: int,
    limit: Optional[int] = None
) -> List[SystemLog]:
    """
    Get logs for a specific property.
    
    Args:
        db: Database session
        property_id: Property ID
        limit: Maximum number of logs to return (optional)
    
    Returns:
        List of SystemLog objects
    """
    query = db.query(SystemLog).filter(
        SystemLog.property_id == property_id
    ).order_by(SystemLog.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_logs_by_date_range(
    db: Session,
    start_date: date,
    end_date: date,
    property_id: Optional[int] = None
) -> List[SystemLog]:
    """
    Get logs within a date range.
    
    Args:
        db: Database session
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        property_id: Optional property ID to filter by
    
    Returns:
        List of SystemLog objects
    """
    # Convert dates to datetime for comparison
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    query = db.query(SystemLog).filter(
        SystemLog.created_at >= start_datetime,
        SystemLog.created_at <= end_datetime
    )
    
    if property_id:
        query = query.filter(SystemLog.property_id == property_id)
    
    return query.order_by(SystemLog.created_at.desc()).all()


def get_logs_by_event_type(
    db: Session,
    event_type: str,
    limit: Optional[int] = None,
    property_id: Optional[int] = None
) -> List[SystemLog]:
    """
    Get logs by event type.
    
    Args:
        db: Database session
        event_type: Event type to filter by
        limit: Maximum number of logs to return (optional)
        property_id: Optional property ID to filter by
    
    Returns:
        List of SystemLog objects
    """
    query = db.query(SystemLog).filter(SystemLog.event_type == event_type)
    
    if property_id:
        query = query.filter(SystemLog.property_id == property_id)
    
    query = query.order_by(SystemLog.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_logs_for_summary(
    db: Session,
    property_id: int,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Get aggregated logs for summary report generation.
    
    Args:
        db: Database session
        property_id: Property ID
        start_date: Start date for summary period
        end_date: End date for summary period
    
    Returns:
        Dictionary with aggregated log data
    """
    logs = get_logs_by_date_range(db, start_date, end_date, property_id)
    
    # Aggregate data
    summary = {
        "property_id": property_id,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_events": len(logs),
        "event_counts": {},
        "booking_requests": 0,
        "booking_confirmations": 0,
        "booking_cancellations": 0,
        "payment_approvals": 0,
        "payment_rejections": 0,
        "issues_reported": 0,
        "issues_resolved": 0,
        "issues_escalated": 0,
        "cleaning_tasks_scheduled": 0,
        "cleaning_tasks_completed": 0,
        "escalations_to_host": 0
    }
    
    # Count events by type
    for log in logs:
        event_type = log.event_type
        summary["event_counts"][event_type] = summary["event_counts"].get(event_type, 0) + 1
        
        # Count specific event types
        if event_type == EventType.GUEST_BOOKING_REQUEST:
            summary["booking_requests"] += 1
        elif event_type == EventType.BOOKING_CONFIRMED:
            summary["booking_confirmations"] += 1
        elif event_type == EventType.BOOKING_CANCELLED:
            summary["booking_cancellations"] += 1
        elif event_type == EventType.BOOKING_PAYMENT_APPROVED:
            summary["payment_approvals"] += 1
        elif event_type == EventType.BOOKING_PAYMENT_REJECTED:
            summary["payment_rejections"] += 1
        elif event_type == EventType.ISSUE_REPORTED:
            summary["issues_reported"] += 1
        elif event_type == EventType.ISSUE_RESOLVED:
            summary["issues_resolved"] += 1
        elif event_type == EventType.ISSUE_ESCALATED:
            summary["issues_escalated"] += 1
        elif event_type == EventType.CLEANING_SCHEDULED:
            summary["cleaning_tasks_scheduled"] += 1
        elif event_type == EventType.CLEANING_COMPLETED:
            summary["cleaning_tasks_completed"] += 1
        elif event_type == EventType.AGENT_ESCALATION or event_type == EventType.HOST_ESCALATION_RECEIVED:
            summary["escalations_to_host"] += 1
    
    return summary


def get_recent_logs(
    db: Session,
    limit: int = 50,
    property_id: Optional[int] = None
) -> List[SystemLog]:
    """
    Get recent logs.
    
    Args:
        db: Database session
        limit: Maximum number of logs to return
        property_id: Optional property ID to filter by
    
    Returns:
        List of SystemLog objects, most recent first
    """
    query = db.query(SystemLog)
    
    if property_id:
        query = query.filter(SystemLog.property_id == property_id)
    
    return query.order_by(SystemLog.created_at.desc()).limit(limit).all()
