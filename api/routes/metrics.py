"""
Metrics API endpoints.

Provides evaluation metrics for the property booking system.
"""

from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, distinct

from database.db import get_db
from database.models import Host, Property, Booking, SystemLog
from api.utils.logging import EventType

router = APIRouter()


def get_date_range(period: str = "week", custom_start: Optional[date] = None, custom_end: Optional[date] = None):
    """Get date range based on period."""
    today = date.today()
    
    if custom_start and custom_end:
        return custom_start, custom_end
    
    if period == "today":
        return today, today
    elif period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        return start, today
    elif period == "month":
        start = today.replace(day=1)
        return start, today
    elif period == "year":
        start = today.replace(month=1, day=1)
        return start, today
    elif period == "all":
        return date(2020, 1, 1), today
    else:
        # Default to week
        start = today - timedelta(days=7)
        return start, today


@router.get("/metrics")
async def get_all_metrics(
    period: str = Query("week", description="Time period: today, week, month, year, all"),
    host_id: Optional[int] = Query(None, description="Filter by host ID"),
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all evaluation metrics for the system.
    
    **How it works:**
    - Queries the database for bookings, system logs, and user data
    - Calculates metrics based on the specified time period
    - Returns comprehensive metrics for agent performance, bookings, users, and system health
    
    **Parameters:**
    - `period`: Time period to analyze (today, week, month, year, all)
    - `host_id`: Optional filter for specific host
    - `property_id`: Optional filter for specific property
    
    **Returns:**
    - Agent performance metrics (FAQ hit rate, response accuracy, etc.)
    - Booking metrics (conversion rate, payment success, revenue, etc.)
    - User engagement metrics (active users, return rate, etc.)
    - System metrics (error rate, uptime indicators)
    """
    start_date, end_date = get_date_range(period)
    
    # Build property filter
    property_ids = []
    if property_id:
        property_ids = [property_id]
    elif host_id:
        properties = db.query(Property).filter(Property.host_id == host_id).all()
        property_ids = [p.id for p in properties]
    
    # Get all metrics
    agent_metrics = calculate_agent_metrics(db, start_date, end_date, property_ids)
    booking_metrics = calculate_booking_metrics(db, start_date, end_date, property_ids)
    user_metrics = calculate_user_metrics(db, start_date, end_date, property_ids)
    system_metrics = calculate_system_metrics(db, start_date, end_date)
    
    return {
        "period": {
            "type": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "filters": {
            "host_id": host_id,
            "property_id": property_id
        },
        "agent_performance": agent_metrics,
        "booking_metrics": booking_metrics,
        "user_engagement": user_metrics,
        "system_health": system_metrics,
        "generated_at": datetime.now().isoformat()
    }


def calculate_agent_metrics(db: Session, start_date: date, end_date: date, property_ids: List[int]) -> Dict[str, Any]:
    """Calculate agent performance metrics."""
    
    # Base query for logs in date range
    base_query = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1)
    )
    
    if property_ids:
        base_query = base_query.filter(SystemLog.property_id.in_(property_ids))
    
    # Total QnA queries (guest inquiries)
    total_inquiries = base_query.filter(
        SystemLog.event_type.in_([EventType.GUEST_INQUIRY, EventType.GUEST_MESSAGE])
    ).count()
    
    # FAQ hits (responses from database)
    faq_hits = 0
    llm_responses = 0
    
    inquiry_logs = base_query.filter(
        SystemLog.event_type == EventType.AGENT_RESPONSE
    ).all()
    
    for log in inquiry_logs:
        metadata = log.get_metadata()
        if metadata.get("source") == "database":
            faq_hits += 1
        elif metadata.get("source") == "llm":
            llm_responses += 1
    
    total_responses = faq_hits + llm_responses
    
    # Agent decisions
    agent_decisions = base_query.filter(
        SystemLog.event_type == EventType.AGENT_DECISION
    ).count()
    
    # Calculate rates
    faq_hit_rate = (faq_hits / total_responses * 100) if total_responses > 0 else 0
    llm_fallback_rate = (llm_responses / total_responses * 100) if total_responses > 0 else 0
    
    # Response time (average time between guest message and agent response)
    # This would require pairing messages - simplified version
    response_times = []
    guest_messages = base_query.filter(
        SystemLog.event_type == EventType.GUEST_MESSAGE
    ).order_by(SystemLog.created_at).all()
    
    agent_responses = base_query.filter(
        SystemLog.event_type == EventType.AGENT_RESPONSE
    ).order_by(SystemLog.created_at).all()
    
    # Simple pairing by proximity
    for gm in guest_messages[:100]:  # Limit for performance
        for ar in agent_responses:
            if ar.created_at > gm.created_at:
                diff = (ar.created_at - gm.created_at).total_seconds()
                if diff < 60:  # Within 1 minute
                    response_times.append(diff)
                break
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return {
        "total_inquiries": total_inquiries,
        "total_responses": total_responses,
        "faq_hits": faq_hits,
        "llm_responses": llm_responses,
        "faq_hit_rate_percent": round(faq_hit_rate, 2),
        "llm_fallback_rate_percent": round(llm_fallback_rate, 2),
        "agent_decisions": agent_decisions,
        "avg_response_time_seconds": round(avg_response_time, 2),
        "description": {
            "faq_hit_rate": "Percentage of queries answered from database FAQs",
            "llm_fallback_rate": "Percentage of queries requiring LLM processing",
            "avg_response_time": "Average seconds between user message and bot response"
        }
    }


def calculate_booking_metrics(db: Session, start_date: date, end_date: date, property_ids: List[int]) -> Dict[str, Any]:
    """Calculate booking and revenue metrics."""
    
    # Base query for bookings in date range
    base_query = db.query(Booking).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date + timedelta(days=1)
    )
    
    if property_ids:
        base_query = base_query.filter(Booking.property_id.in_(property_ids))
    
    # Booking counts by status
    total_bookings = base_query.count()
    confirmed_bookings = base_query.filter(Booking.booking_status == 'confirmed').count()
    pending_bookings = base_query.filter(Booking.booking_status == 'pending').count()
    cancelled_bookings = base_query.filter(Booking.booking_status == 'cancelled').count()
    
    # Payment status
    approved_payments = base_query.filter(Booking.payment_status == 'approved').count()
    pending_payments = base_query.filter(Booking.payment_status == 'pending').count()
    rejected_payments = base_query.filter(Booking.payment_status == 'rejected').count()
    
    # Revenue calculations
    confirmed_revenue = db.query(func.sum(Booking.final_price)).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date + timedelta(days=1),
        Booking.booking_status == 'confirmed'
    )
    if property_ids:
        confirmed_revenue = confirmed_revenue.filter(Booking.property_id.in_(property_ids))
    confirmed_revenue = confirmed_revenue.scalar() or 0
    
    # Guest and nights totals
    guest_nights_query = db.query(
        func.sum(Booking.number_of_guests),
        func.sum(Booking.number_of_nights)
    ).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date + timedelta(days=1),
        Booking.booking_status == 'confirmed'
    )
    if property_ids:
        guest_nights_query = guest_nights_query.filter(Booking.property_id.in_(property_ids))
    
    result = guest_nights_query.first()
    total_guests = result[0] or 0
    total_nights = result[1] or 0
    
    # Calculate rates
    booking_conversion_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0
    payment_success_rate = (approved_payments / (approved_payments + rejected_payments) * 100) if (approved_payments + rejected_payments) > 0 else 0
    cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
    avg_booking_value = (confirmed_revenue / confirmed_bookings) if confirmed_bookings > 0 else 0
    
    # Booking flow completion (from SystemLog)
    log_query = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1)
    )
    
    booking_started = log_query.filter(
        SystemLog.event_type == EventType.GUEST_BOOKING_REQUEST
    ).count()
    
    booking_completed = log_query.filter(
        SystemLog.event_type == EventType.BOOKING_CONFIRMED
    ).count()
    
    flow_completion_rate = (booking_completed / booking_started * 100) if booking_started > 0 else 0
    
    return {
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "pending_bookings": pending_bookings,
        "cancelled_bookings": cancelled_bookings,
        "booking_conversion_rate_percent": round(booking_conversion_rate, 2),
        "cancellation_rate_percent": round(cancellation_rate, 2),
        "flow_completion_rate_percent": round(flow_completion_rate, 2),
        "payments": {
            "approved": approved_payments,
            "pending": pending_payments,
            "rejected": rejected_payments,
            "success_rate_percent": round(payment_success_rate, 2)
        },
        "revenue": {
            "total_confirmed_pkr": round(confirmed_revenue, 2),
            "average_booking_value_pkr": round(avg_booking_value, 2)
        },
        "guests": {
            "total_guests": total_guests,
            "total_nights": total_nights,
            "avg_guests_per_booking": round(total_guests / confirmed_bookings, 1) if confirmed_bookings > 0 else 0,
            "avg_nights_per_booking": round(total_nights / confirmed_bookings, 1) if confirmed_bookings > 0 else 0
        },
        "description": {
            "booking_conversion_rate": "Percentage of bookings that get confirmed",
            "payment_success_rate": "Percentage of payments approved vs rejected",
            "flow_completion_rate": "Percentage of started booking flows that complete"
        }
    }


def calculate_user_metrics(db: Session, start_date: date, end_date: date, property_ids: List[int]) -> Dict[str, Any]:
    """Calculate user engagement metrics."""
    
    # Unique guests from bookings
    guest_query = db.query(distinct(Booking.guest_telegram_id)).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date + timedelta(days=1)
    )
    if property_ids:
        guest_query = guest_query.filter(Booking.property_id.in_(property_ids))
    
    unique_guests = guest_query.count()
    
    # Unique guests from system logs (more comprehensive)
    log_guests = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1),
        SystemLog.event_type == EventType.GUEST_MESSAGE
    ).all()
    
    unique_telegram_ids = set()
    for log in log_guests:
        metadata = log.get_metadata()
        if metadata.get("guest_telegram_id"):
            unique_telegram_ids.add(metadata.get("guest_telegram_id"))
        elif metadata.get("user_id"):
            unique_telegram_ids.add(metadata.get("user_id"))
    
    active_users = len(unique_telegram_ids)
    
    # Return users (guests with more than 1 booking ever)
    returning_guests = db.query(Booking.guest_telegram_id).group_by(
        Booking.guest_telegram_id
    ).having(func.count(Booking.id) > 1).count()
    
    total_guests_ever = db.query(distinct(Booking.guest_telegram_id)).count()
    return_rate = (returning_guests / total_guests_ever * 100) if total_guests_ever > 0 else 0
    
    # Messages per session (approximate)
    total_messages = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1),
        SystemLog.event_type == EventType.GUEST_MESSAGE
    ).count()
    
    avg_messages_per_user = (total_messages / active_users) if active_users > 0 else 0
    
    # Host count
    total_hosts = db.query(Host).count()
    
    return {
        "active_users_period": active_users,
        "unique_guests_with_bookings": unique_guests,
        "total_messages": total_messages,
        "avg_messages_per_user": round(avg_messages_per_user, 1),
        "returning_guests": returning_guests,
        "return_rate_percent": round(return_rate, 2),
        "total_hosts": total_hosts,
        "total_guests_all_time": total_guests_ever,
        "description": {
            "active_users": "Unique users who sent messages in the period",
            "return_rate": "Percentage of guests who made more than one booking",
            "avg_messages_per_user": "Average messages sent per active user"
        }
    }


def calculate_system_metrics(db: Session, start_date: date, end_date: date) -> Dict[str, Any]:
    """Calculate system health metrics."""
    
    # Total events logged
    total_events = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1)
    ).count()
    
    # Error events (if any logged)
    error_events = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1),
        SystemLog.message.like('%error%')
    ).count()
    
    error_rate = (error_events / total_events * 100) if total_events > 0 else 0
    
    # Events by type
    event_breakdown = {}
    event_types = db.query(
        SystemLog.event_type,
        func.count(SystemLog.id)
    ).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1)
    ).group_by(SystemLog.event_type).all()
    
    for event_type, count in event_types:
        event_breakdown[event_type] = count
    
    # Webhook success (guest messages that got responses)
    guest_messages = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1),
        SystemLog.event_type == EventType.GUEST_MESSAGE
    ).count()
    
    agent_responses = db.query(SystemLog).filter(
        SystemLog.created_at >= start_date,
        SystemLog.created_at <= end_date + timedelta(days=1),
        SystemLog.event_type == EventType.AGENT_RESPONSE
    ).count()
    
    response_rate = (agent_responses / guest_messages * 100) if guest_messages > 0 else 0
    
    # Database stats
    total_properties = db.query(Property).count()
    total_bookings_all = db.query(Booking).count()
    total_logs = db.query(SystemLog).count()
    
    return {
        "total_events_period": total_events,
        "error_events": error_events,
        "error_rate_percent": round(error_rate, 2),
        "response_rate_percent": round(response_rate, 2),
        "event_breakdown": event_breakdown,
        "database_stats": {
            "total_properties": total_properties,
            "total_bookings": total_bookings_all,
            "total_log_entries": total_logs
        },
        "description": {
            "error_rate": "Percentage of events that contain errors",
            "response_rate": "Percentage of guest messages that received responses"
        }
    }


@router.get("/metrics/summary")
async def get_metrics_summary(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a quick summary of key metrics.
    
    Returns the most important metrics at a glance.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # This week's bookings
    week_bookings = db.query(Booking).filter(
        Booking.created_at >= week_start
    ).count()
    
    week_confirmed = db.query(Booking).filter(
        Booking.created_at >= week_start,
        Booking.booking_status == 'confirmed'
    ).count()
    
    week_revenue = db.query(func.sum(Booking.final_price)).filter(
        Booking.created_at >= week_start,
        Booking.booking_status == 'confirmed'
    ).scalar() or 0
    
    # Pending actions
    pending_payments = db.query(Booking).filter(
        Booking.payment_status == 'pending',
        Booking.booking_status == 'pending'
    ).count()
    
    # Total stats
    total_properties = db.query(Property).count()
    total_hosts = db.query(Host).count()
    total_bookings = db.query(Booking).count()
    
    return {
        "this_week": {
            "bookings": week_bookings,
            "confirmed": week_confirmed,
            "revenue_pkr": round(week_revenue, 2)
        },
        "pending_actions": {
            "payments_awaiting_verification": pending_payments
        },
        "totals": {
            "properties": total_properties,
            "hosts": total_hosts,
            "all_time_bookings": total_bookings
        },
        "generated_at": datetime.now().isoformat()
    }


@router.get("/metrics/evaluation")
async def get_evaluation_metrics(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get evaluation metrics as simple percentages and scores.
    
    Returns key performance indicators (KPIs) for system evaluation:
    - Accuracy metrics (as percentages)
    - Performance scores
    - Success rates
    
    Ideal for academic evaluation and reporting.
    """
    
    # === BOOKING METRICS ===
    total_bookings = db.query(Booking).count()
    confirmed_bookings = db.query(Booking).filter(Booking.booking_status == 'confirmed').count()
    cancelled_bookings = db.query(Booking).filter(Booking.booking_status == 'cancelled').count()
    
    # Payment metrics
    approved_payments = db.query(Booking).filter(Booking.payment_status == 'approved').count()
    rejected_payments = db.query(Booking).filter(Booking.payment_status == 'rejected').count()
    total_payment_decisions = approved_payments + rejected_payments
    
    # === AGENT METRICS ===
    total_guest_messages = db.query(SystemLog).filter(
        SystemLog.event_type == EventType.GUEST_MESSAGE
    ).count()
    
    total_agent_responses = db.query(SystemLog).filter(
        SystemLog.event_type == EventType.AGENT_RESPONSE
    ).count()
    
    # FAQ vs LLM responses
    faq_responses = 0
    llm_responses = 0
    agent_logs = db.query(SystemLog).filter(
        SystemLog.event_type == EventType.AGENT_RESPONSE
    ).all()
    
    for log in agent_logs:
        metadata = log.get_metadata()
        if metadata.get("source") == "database":
            faq_responses += 1
        else:
            llm_responses += 1
    
    total_responses = faq_responses + llm_responses
    
    # === USER METRICS ===
    total_unique_guests = db.query(distinct(Booking.guest_telegram_id)).count()
    returning_guests = db.query(Booking.guest_telegram_id).group_by(
        Booking.guest_telegram_id
    ).having(func.count(Booking.id) > 1).count()
    
    # === CALCULATE PERCENTAGES ===
    
    # Booking Success Rate (Accuracy of booking completion)
    booking_success_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0
    
    # Payment Verification Accuracy
    payment_accuracy = (approved_payments / total_payment_decisions * 100) if total_payment_decisions > 0 else 100
    
    # Agent Response Rate (% of messages that got responses)
    response_rate = (total_agent_responses / total_guest_messages * 100) if total_guest_messages > 0 else 0
    
    # FAQ Accuracy (% answered from database - more reliable)
    faq_accuracy = (faq_responses / total_responses * 100) if total_responses > 0 else 0
    
    # User Retention Rate
    retention_rate = (returning_guests / total_unique_guests * 100) if total_unique_guests > 0 else 0
    
    # Cancellation Rate (lower is better)
    cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
    
    # Overall System Score (weighted average)
    # Weights: Booking 30%, Payment 25%, Response 20%, FAQ 15%, Retention 10%
    overall_score = (
        (booking_success_rate * 0.30) +
        (payment_accuracy * 0.25) +
        (response_rate * 0.20) +
        (faq_accuracy * 0.15) +
        (retention_rate * 0.10)
    )
    
    # Revenue metrics
    total_revenue = db.query(func.sum(Booking.final_price)).filter(
        Booking.booking_status == 'confirmed'
    ).scalar() or 0
    
    avg_booking_value = (total_revenue / confirmed_bookings) if confirmed_bookings > 0 else 0
    
    # Guest satisfaction proxy (bookings per guest)
    avg_bookings_per_guest = (total_bookings / total_unique_guests) if total_unique_guests > 0 else 0
    
    return {
        "evaluation_scores": {
            "overall_system_score": round(overall_score, 2),
            "booking_success_rate": round(booking_success_rate, 2),
            "payment_accuracy": round(payment_accuracy, 2),
            "agent_response_rate": round(response_rate, 2),
            "faq_hit_rate": round(faq_accuracy, 2),
            "user_retention_rate": round(retention_rate, 2),
            "cancellation_rate": round(cancellation_rate, 2)
        },
        "raw_numbers": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "approved_payments": approved_payments,
            "rejected_payments": rejected_payments,
            "total_guest_messages": total_guest_messages,
            "total_agent_responses": total_agent_responses,
            "faq_responses": faq_responses,
            "llm_responses": llm_responses,
            "unique_guests": total_unique_guests,
            "returning_guests": returning_guests
        },
        "financial_metrics": {
            "total_revenue_pkr": round(total_revenue, 2),
            "average_booking_value_pkr": round(avg_booking_value, 2),
            "avg_bookings_per_guest": round(avg_bookings_per_guest, 2)
        },
        "score_interpretation": {
            "overall_system_score": "Weighted average of all metrics (0-100)",
            "booking_success_rate": "% of bookings that get confirmed",
            "payment_accuracy": "% of payment verifications approved",
            "agent_response_rate": "% of guest messages that received responses",
            "faq_hit_rate": "% of responses from database (vs LLM)",
            "user_retention_rate": "% of guests who made multiple bookings",
            "cancellation_rate": "% of bookings cancelled (lower is better)"
        },
        "generated_at": datetime.now().isoformat()
    }

