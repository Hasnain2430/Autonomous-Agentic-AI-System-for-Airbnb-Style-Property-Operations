"""
Conversation context management for persistent chat memory.

Stores conversation context in database for long-term memory across sessions.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import SystemLog
from api.utils.logging import EventType
import json
from datetime import datetime


def get_conversation_context(
    db: Session,
    guest_telegram_id: str,
    property_id: Optional[int] = None,
    limit: int = 200
) -> Dict[str, Any]:
    """
    Get full conversation context for a guest/property pair.
    
    Returns the most recent dates, negotiated price, booking status,
    and other metadata persisted via SystemLog.
    """
    context = {
        "dates": None,
        "negotiated_price": None,
        "negotiated_dates": None,
        "booking_status": None,
        "last_interaction": None,
        "guest_preferences": {},
    }
    
    query = (
        db.query(SystemLog)
        .filter(
            SystemLog.event_type.in_(
                [
                    EventType.GUEST_MESSAGE,
                    EventType.AGENT_RESPONSE,
                    EventType.AGENT_DECISION,
                    EventType.GUEST_INQUIRY,
                    EventType.GUEST_BOOKING_REQUEST,
                    EventType.GUEST_PAYMENT_UPLOADED,
                    EventType.BOOKING_CONFIRMED,
                ]
            )
        )
        .order_by(SystemLog.created_at.desc())
        .limit(limit)
    )
    
    for log in query.all():
        try:
            metadata = log.get_metadata()
        except Exception:
            metadata = {}
        
        log_guest_id = metadata.get("user_id") or metadata.get("guest_telegram_id")
        if log_guest_id != guest_telegram_id:
            continue
        
        # Respect property scope when provided
        meta_property_id = metadata.get("property_id") or log.property_id
        if property_id and meta_property_id and meta_property_id != property_id:
            continue
        
        # Persist booking status
        if log.event_type == EventType.BOOKING_CONFIRMED:
            context["booking_status"] = "confirmed"
        
        # Persist dates from explicit metadata first
        if not context["dates"] and metadata.get("dates"):
            context["dates"] = metadata["dates"]
        
        # Persist negotiated price/dates
        if metadata.get("negotiated_price") and context["negotiated_price"] is None:
            context["negotiated_price"] = metadata.get("negotiated_price")
            context["negotiated_dates"] = metadata.get("negotiated_dates") or metadata.get("dates")
        
        # As a fallback, extract dates from text content
        if not context["dates"]:
            from api.utils.conversation import extract_dates_from_history
            
            try:
                message_content = metadata.get("text") or log.message or ""
                if message_content:
                    dates = extract_dates_from_history([{"role": "user", "content": message_content}])
                    if dates:
                        context["dates"] = dates
            except Exception:
                pass
        
        if context["last_interaction"] is None:
            context["last_interaction"] = log.created_at.isoformat()
    
    return context


def save_conversation_context(
    db: Session,
    guest_telegram_id: str,
    property_id: Optional[int],
    context_updates: Dict[str, Any]
) -> None:
    """
    Save conversation context updates.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        property_id: Property ID
        context_updates: Dictionary with context to save
    """
    # Context is stored in SystemLog metadata, so we just need to ensure
    # important context is saved when logging events
    # This function can be called to explicitly save context
    pass


def get_context_summary_for_llm(
    db: Session,
    guest_telegram_id: str,
    property_id: Optional[int] = None,
    context_data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Get a formatted context summary for LLM prompts.
    """
    context = context_data or get_conversation_context(db, guest_telegram_id, property_id)
    summary_parts = []
    
    if context.get("dates"):
        dates = context["dates"]
        summary_parts.append(
            f"Guest has mentioned dates: Check-in {dates['check_in']}, Check-out {dates['check_out']}"
        )
    
    if context.get("negotiated_price") and context.get("negotiated_dates"):
        summary_parts.append(
            f"Previous negotiation: ${context['negotiated_price']:.2f} for dates "
            f"{context['negotiated_dates']['check_in']} to {context['negotiated_dates']['check_out']}"
        )
        if context.get("dates") and context["dates"] != context["negotiated_dates"]:
            summary_parts.append("Note: Current dates differ from negotiated dates - price may need adjustment")
    
    if context.get("booking_status"):
        summary_parts.append(f"Booking status: {context['booking_status']}")
    
    if context.get("last_interaction"):
        last_date = datetime.fromisoformat(context["last_interaction"])
        days_ago = (datetime.now() - last_date.replace(tzinfo=None)).days
        if days_ago > 0:
            summary_parts.append(f"Last interaction: {days_ago} day(s) ago")
    
    return "\n".join(summary_parts) if summary_parts else None

