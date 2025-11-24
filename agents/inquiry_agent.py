"""
Inquiry Agent.

Handles basic guest inquiries, availability checks, and property information.
Detects booking intent and transitions to BookingAgent when needed.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from database.models import Property, Booking
from api.utils.conversation_context import get_conversation_context, get_context_summary_for_llm
from api.utils.conversation import extract_dates_from_history
from api.utils.logging import log_event, EventType
import json


class InquiryAgent(BaseAgent):
    """
    Agent for handling guest inquiries and property information.
    
    Focus: Basic questions, availability, property details.
    Transitions to BookingAgent when user wants to book/negotiate.
    """
    
    def __init__(self):
        """Initialize Inquiry Agent."""
        super().__init__("InquiryAgent", model="qwen-max")
    
    def format_system_prompt(self, property_data: Dict[str, Any], db: Session = None, property_id: int = None) -> str:
        """
        Format system prompt focused on inquiry tasks only.
        
        Args:
            property_data: Property configuration dictionary
            db: Database session
            property_id: Property ID
        
        Returns:
            Formatted system prompt
        """
        prompt = f"""You are a friendly and professional property inquiry assistant for an Airbnb-style property.

Property Information:
- Name: {property_data.get('name', 'Unknown')}
- Location: {property_data.get('location', 'Unknown')}
- Base Price: ${property_data.get('base_price', 0):.2f} per night
- Max Guests: {property_data.get('max_guests', 1)}
- Check-in Time: {property_data.get('check_in_time', 'Unknown')}
- Check-out Time: {property_data.get('check_out_time', 'Unknown')}

Your role:
1. Answer questions about the property (location, amenities, check-in/out times, max guests)
2. Check availability for requested dates
3. Provide base pricing information (base price × number of nights)
4. Be helpful and friendly
5. Detect when the guest wants to book or negotiate (then transition to booking agent)

IMPORTANT GUIDELINES:
- ONLY answer questions related to property information, availability, and basic pricing
- If asked about discounts, negotiations, or payment → indicate that you'll connect them to booking
- DO NOT mention discounts, price ranges, or negotiations - that's handled by the booking agent
- NEVER reveal price ranges (min/max) - only mention base price
- REMEMBER dates from conversation - don't ask for information already provided
- Use clean, simple formatting - avoid excessive markdown like *** or long dashes
- Be friendly, professional, and concise
- Calculate prices accurately (base price × number of nights)
- When guest wants to book or negotiate, acknowledge and indicate transition to booking process

Response Format:
- Use simple line breaks for readability
- Avoid bold/italic markdown unless absolutely necessary
- Use simple dashes (-) not long dashes (—)
- Keep formatting minimal and clean

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
        return prompt
    
    def check_availability(
        self,
        db: Session,
        property_id: int,
        check_in: datetime,
        check_out: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if property is available for given dates.
        
        Args:
            db: Database session
            property_id: Property ID
            check_in: Check-in date
            check_out: Check-out date
        
        Returns:
            Tuple of (is_available, reason_if_not_available)
        """
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return False, "Property not found"
        
        # Check for overlapping bookings
        overlapping = db.query(Booking).filter(
            Booking.property_id == property_id,
            Booking.status == "confirmed",
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).first()
        
        if overlapping:
            return False, f"Property is already booked from {overlapping.check_in.date()} to {overlapping.check_out.date()}"
        
        # Check property rules (minimum stay, advance booking, etc.)
        rules = {}
        
        # Check minimum stay
        nights = (check_out - check_in).days
        min_stay = rules.get("minimum_stay_nights", 1)
        if nights < min_stay:
            return False, f"Minimum stay is {min_stay} nights"
        
        # Check advance booking
        days_until_checkin = (check_in - datetime.now()).days
        min_advance = rules.get("minimum_advance_booking_days", 0)
        if days_until_checkin < min_advance:
            return False, f"Bookings must be made at least {min_advance} days in advance"
        
        return True, None
    
    def detect_booking_intent(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Detect if user wants to proceed with booking or negotiation.
        
        Args:
            message: Current user message
            conversation_history: Previous conversation messages
        
        Returns:
            True if booking intent detected, False otherwise
        """
        message_lower = message.lower().strip()
        
        # Booking intent keywords
        booking_keywords = [
            "book", "booking", "reserve", "reservation",
            "yes", "yeah", "sure", "ok", "okay", "proceed",
            "let's do it", "lets do it", "go ahead",
            "negotiate", "negotiation", "discount", "lower price",
            "payment", "pay", "how to pay"
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
                    if any(word in context_text for word in ["book", "booking", "available", "price", "proceed"]):
                        return True
                return True  # Default to booking intent for simple confirmations
        
        return False
    
    def handle_inquiry(
        self,
        db: Session,
        message: str,
        property_id: int,
        guest_telegram_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Handle guest inquiry message.
        
        Args:
            db: Database session
            message: Guest's message
            property_id: Property ID
            guest_telegram_id: Guest's Telegram ID
            conversation_history: Previous conversation messages
        
        Returns:
            Dictionary with response and action metadata
        """
        # Get property data
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return {
                "response": "I'm sorry, I couldn't find the property information. Please contact support.",
                "action": "error",
                "metadata": {}
            }
        
        # Format property data
        property_data = {
            "name": property_obj.name,
            "location": property_obj.location,
            "base_price": property_obj.base_price,
            "min_price": property_obj.min_price,
            "max_price": property_obj.max_price,
            "max_guests": property_obj.max_guests,
            "check_in_time": property_obj.check_in_time,
            "check_out_time": property_obj.check_out_time,
            "rules": {}
        }
        
        # Build conversation messages
        messages = []
        
        # System prompt
        system_prompt = self.format_system_prompt(property_data, db=db, property_id=property_id)
        messages.append({"role": "system", "content": system_prompt})
        
        # Get conversation context
        persistent_context: Dict[str, Any] = {}
        try:
            persistent_context = get_conversation_context(db, guest_telegram_id, property_id)
            context_summary = get_context_summary_for_llm(
                db,
                guest_telegram_id,
                property_id,
                context_data=persistent_context,
            )
            if context_summary:
                context_note = (
                    "\n\n[CONVERSATION CONTEXT - Use this information:\n"
                    f"{context_summary}\n"
                    "If dates are mentioned here, use them automatically. DO NOT ask for dates that are already in this context.]"
                )
                messages.append({"role": "system", "content": context_note})
        except Exception as e:
            print(f"Error getting conversation context: {e}")
        
        # Extract dates from current message or history
        current_dates = None
        try:
            # Check current message for dates
            current_message_dates = extract_dates_from_history([{"role": "user", "content": message}])
            if current_message_dates:
                current_dates = current_message_dates
            
            # Check history for dates
            if conversation_history:
                history_dates = extract_dates_from_history(conversation_history)
                if history_dates and not current_dates:
                    current_dates = history_dates
                    
                # Add context note if dates exist
                if current_dates:
                    context_note = (
                        f"\n\n[CONTEXT: Guest has provided dates - Check-in: {current_dates['check_in']}, "
                        f"Check-out: {current_dates['check_out']}. Use these dates automatically. "
                        "DO NOT ask for dates again.]"
                    )
                    messages.insert(-1, {"role": "system", "content": context_note})
        except Exception as e:
            print(f"Error extracting dates: {e}")
        
        if not current_dates and persistent_context.get("dates"):
            current_dates = persistent_context["dates"]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Check for booking intent
        booking_intent = self.detect_booking_intent(message, conversation_history)
        
        if booking_intent and current_dates:
            # User wants to book - transition to booking agent
            transition_note = (
                "\n\n[IMPORTANT: Guest wants to proceed with booking. "
                "Acknowledge their request and indicate that you'll connect them to the booking process. "
                "Mention that they can discuss pricing and payment options with the booking specialist.]"
            )
            messages.insert(-1, {"role": "system", "content": transition_note})
        
        # Get LLM response
        try:
            response = self.get_llm_response(messages, temperature=0.7)
            
            # Determine action
            action = "inquiry"
            metadata = {
                "property_id": property_id,
                "guest_telegram_id": guest_telegram_id,
                "user_id": guest_telegram_id,
            }
            
            # Save dates if found
            if current_dates:
                metadata["dates"] = current_dates
                # Save to context
                from api.utils.conversation_context import save_conversation_context
                save_conversation_context(
                    db,
                    guest_telegram_id,
                    property_id,
                    {"dates": current_dates}
                )
            
            # Check availability if dates provided
            if current_dates:
                try:
                    check_in = datetime.strptime(current_dates["check_in"], "%Y-%m-%d")
                    check_out = datetime.strptime(current_dates["check_out"], "%Y-%m-%d")
                    is_available, reason = self.check_availability(db, property_id, check_in, check_out)
                    metadata["availability"] = is_available
                    if not is_available:
                        metadata["availability_reason"] = reason
                    action = "availability_check"
                except Exception as e:
                    print(f"Error checking availability: {e}")
            
            # If booking intent detected, mark for transition
            if booking_intent:
                action = "transition_to_booking"
                metadata["booking_intent"] = True
                # Save booking intent to context
                from api.utils.conversation_context import save_conversation_context
                save_conversation_context(
                    db,
                    guest_telegram_id,
                    property_id,
                    {"booking_intent": True, "active_agent": "booking"}
                )
            
            # Log the inquiry
            log_event(
                db=db,
                event_type=EventType.GUEST_INQUIRY,
                message=f"Inquiry from guest: {message[:100]}",
                property_id=property_id,
                metadata=metadata
            )
            
            # Log agent response
            log_event(
                db=db,
                event_type=EventType.AGENT_RESPONSE,
                message=f"InquiryAgent response: {response[:100]}",
                property_id=property_id,
                metadata={
                    "agent_name": "InquiryAgent",
                    "action": action,
                    "user_id": guest_telegram_id,
                }
            )
            
            return {
                "response": response,
                "action": action,
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"Error in InquiryAgent.handle_inquiry: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": "I'm sorry, I encountered an error processing your inquiry. Please try again.",
                "action": "error",
                "metadata": {"error": str(e)}
            }

