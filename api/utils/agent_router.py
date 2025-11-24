"""
Agent Router.

Determines which agent should handle a message based on context and message content.
Manages transitions between InquiryAgent and BookingAgent.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from api.utils.conversation_context import get_conversation_context


def determine_agent(
    db: Session,
    guest_telegram_id: str,
    property_id: int,
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Determine which agent should handle the current message.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        property_id: Property ID
        message: Current message
        conversation_history: Previous conversation messages
    
    Returns:
        "inquiry" or "booking" - the agent to use
    """
    # Get conversation context
    context = get_conversation_context(db, guest_telegram_id, property_id)
    
    # Check if there's an active agent in context
    active_agent = context.get("active_agent")
    booking_intent = context.get("booking_intent", False)
    
    # If booking intent is set or active agent is booking, use booking agent
    if booking_intent or active_agent == "booking":
        # Check if we should transition back to inquiry (rare case)
        if should_transition_to_inquiry(message, context):
            return "inquiry"
        return "booking"
    
    # Check if we should transition to booking
    if should_transition_to_booking(message, context, conversation_history):
        return "booking"
    
    # Default to inquiry agent
    return "inquiry"


def should_transition_to_booking(
    message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    Determine if we should transition from InquiryAgent to BookingAgent.
    
    Args:
        message: Current message
        context: Conversation context
        conversation_history: Previous conversation messages
    
    Returns:
        True if should transition to booking agent
    """
    message_lower = message.lower().strip()
    
    # Explicit booking intent keywords
    booking_keywords = [
        "book", "booking", "reserve", "reservation",
        "yes", "yeah", "sure", "ok", "okay", "proceed",
        "let's do it", "lets do it", "go ahead",
        "negotiate", "negotiation", "discount", "lower price",
        "payment", "pay", "how to pay", "payment method"
    ]
    
    # Check current message
    if any(keyword in message_lower for keyword in booking_keywords):
        # Additional check: if it's just "yes" or similar, check context
        simple_confirmations = ["yes", "yeah", "sure", "ok", "okay", "proceed"]
        if message_lower in simple_confirmations:
            # Check if previous context suggests booking
            if conversation_history:
                last_few = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
                context_text = " ".join([msg.get("content", "").lower() for msg in last_few])
                if any(word in context_text for word in ["book", "booking", "available", "price", "proceed", "payment"]):
                    return True
            # If dates exist in context, assume booking intent
            if context.get("dates"):
                return True
        return True
    
    # Check if booking intent was already set
    if context.get("booking_intent"):
        return True
    
    return False


def should_transition_to_inquiry(
    message: str,
    context: Dict[str, Any]
) -> bool:
    """
    Determine if we should transition from BookingAgent back to InquiryAgent.
    
    This is rare but can happen if user asks a general property question during booking.
    
    Args:
        message: Current message
        context: Conversation context
    
    Returns:
        True if should transition to inquiry agent
    """
    message_lower = message.lower().strip()
    
    # General property question keywords (not booking/payment related)
    inquiry_keywords = [
        "what is", "tell me about", "where is", "how many",
        "amenities", "amenity", "location", "address",
        "check-in time", "check-out time", "checkin", "checkout",
        "max guests", "maximum guests", "guests allowed"
    ]
    
    # Booking/payment keywords that should keep us in booking agent
    booking_keywords = [
        "book", "booking", "reserve", "payment", "pay", "negotiate",
        "discount", "price", "cost", "screenshot", "bank", "transfer"
    ]
    
    # If message contains inquiry keywords but NOT booking keywords, consider transition
    has_inquiry_keywords = any(keyword in message_lower for keyword in inquiry_keywords)
    has_booking_keywords = any(keyword in message_lower for keyword in booking_keywords)
    
    # Only transition if it's clearly a general question and not booking-related
    if has_inquiry_keywords and not has_booking_keywords:
        # But don't transition if we're in the middle of payment process
        if context.get("booking_status") in ["payment_awaiting", "payment_received"]:
            return False
        return True
    
    return False


def update_agent_context(
    db: Session,
    guest_telegram_id: str,
    property_id: int,
    agent_name: str,
    booking_intent: Optional[bool] = None
) -> None:
    """
    Update conversation context with active agent information.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        property_id: Property ID
        agent_name: "inquiry" or "booking"
        booking_intent: Optional booking intent flag
    """
    from api.utils.conversation_context import save_conversation_context
    
    updates = {"active_agent": agent_name}
    if booking_intent is not None:
        updates["booking_intent"] = booking_intent
    
    save_conversation_context(db, guest_telegram_id, property_id, updates)

