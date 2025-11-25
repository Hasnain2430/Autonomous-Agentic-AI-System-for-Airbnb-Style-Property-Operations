"""
Booking Agent.

Handles price negotiation, booking confirmation, and payment processing.
Receives context from InquiryAgent (dates, property info) and manages booking flow.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from database.models import Property, Booking
from api.utils.conversation_context import get_conversation_context, get_context_summary_for_llm
from api.utils.conversation import extract_dates_from_history
from api.utils.logging import log_event, EventType
import json
import re


class BookingAgent(BaseAgent):
    """
    Agent for handling booking, negotiation, and payment.
    
    Focus: Price negotiation, booking confirmation, payment methods, payment collection.
    Receives dates and property info from InquiryAgent via shared context.
    """
    
    def __init__(self):
        """Initialize Booking Agent."""
        super().__init__("BookingAgent", model="qwen-max")
    
    def format_system_prompt(self, property_data: Dict[str, Any], db: Session = None, property_id: int = None) -> str:
        """
        Format system prompt focused on booking and payment tasks.
        
        Args:
            property_data: Property configuration dictionary
            db: Database session
            property_id: Property ID
        
        Returns:
            Formatted system prompt
        """
        # Get host payment methods from database
        payment_methods = "Bank transfer, mobile payment apps (JazzCash, EasyPaisa, etc.), or other methods as agreed"
        payment_methods_list = []
        if db and property_id:
            try:
                from database.models import Host
                property_obj = db.query(Property).filter(Property.id == property_id).first()
                if property_obj and property_obj.host:
                    host = property_obj.host
                    payment_methods_list = host.get_payment_methods()
                    if payment_methods_list:
                        methods_text = []
                        for method in payment_methods_list:
                            bank_name = method.get('bank_name', 'Unknown')
                            account = method.get('account_number', 'N/A')
                            account_name = method.get('account_name')
                            instructions = method.get('instructions')
                            line = f"{bank_name}"
                            if account_name:
                                line += f" ({account_name})"
                            line += f": {account}"
                            if instructions:
                                line += f" - {instructions}"
                            methods_text.append(line)
                        payment_methods = "\n".join(methods_text) if methods_text else payment_methods
            except Exception as e:
                print(f"Error getting payment methods: {e}")
                pass
        
        prompt = f"""You are a professional booking and payment specialist for an Airbnb-style property.

Property Information:
- Name: {property_data.get('name', 'Unknown')}
- Location: {property_data.get('location', 'Unknown')}
- Base Price: PKR {property_data.get('base_price', 0):,.2f} per night
- Max Guests: {property_data.get('max_guests', 1)}
- Check-in Time: {property_data.get('check_in_time', 'Unknown')}
- Check-out Time: {property_data.get('check_out_time', 'Unknown')}

Payment Information:
- Payment methods: {payment_methods}
- Payment is required before booking confirmation
- Guest must send payment screenshot for verification

Your role:
1. When guest wants to book, IMMEDIATELY display payment details with host bank information
2. Display payment methods clearly with ALL bank details
3. Guide guests through the payment process
4. Tell them to upload payment screenshot after transfer

IMPORTANT GUIDELINES:
- ONLY handle booking and payment-related questions
- Prices are FIXED - base price × number of nights (NO negotiation, NO discounts)
- If guest asks for discount or negotiation, politely explain that prices are fixed
- REMEMBER dates from conversation context - NEVER ask again if already provided
- Use clean, simple formatting - avoid excessive markdown like *** or long dashes
- Be friendly, professional, and concise
- Calculate prices accurately: base price × number of nights
- IMMEDIATELY show payment methods with ALL bank details when guest confirms booking
- Payment explanation MUST include: bank name, account number, amount to pay in PKR
- After showing payment details, tell guest to upload their payment screenshot
- NEVER mention "booking agent" or "transfer to agent" - you ARE handling the booking
- Keep responses clear and easy to read

Response Format:
- Use simple line breaks for readability
- Avoid bold/italic markdown unless absolutely necessary
- Use simple dashes (-) not long dashes (—)
- Keep formatting minimal and clean

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""
        return prompt
    
    def calculate_price(
        self,
        property_id: int,
        check_in: datetime,
        check_out: datetime,
        num_guests: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Calculate booking price with dynamic pricing.
        
        Pricing factors:
        - Base price per night
        - Number of nights (longer stays may get discounts)
        - Days until check-in (last-minute bookings get higher rates)
        
        Args:
            property_id: Property ID
            check_in: Check-in date
            check_out: Check-out date
            num_guests: Number of guests
            db: Database session
        
        Returns:
            Dictionary with price breakdown
        """
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return {"error": "Property not found"}
        
        nights = (check_out - check_in).days
        base_price = property_obj.base_price
        
        # Calculate days until check-in (for validation only)
        days_until_checkin = (check_in - datetime.now()).days
        if days_until_checkin < 0:
            return {"error": "Check-in date cannot be in the past"}
        
        # Fixed pricing: base price × number of nights (no discounts, no urgency multipliers)
        adjusted_price_per_night = base_price
        
        # Calculate totals
        total_base = adjusted_price_per_night * nights
        
        # Check guest limit
        if num_guests > property_obj.max_guests:
            return {"error": f"Maximum {property_obj.max_guests} guests allowed"}
        
        # Additional guest charges (if any)
        rules = {}
        extra_guest_charge = rules.get("extra_guest_charge", 0)
        extra_guests = max(0, num_guests - rules.get("base_guests", 1))
        extra_guest_total = extra_guest_charge * extra_guests * nights
        
        total = total_base + extra_guest_total
        
        return {
            "base_price_per_night": base_price,
            "adjusted_price_per_night": adjusted_price_per_night,
            "nights": nights,
            "days_until_checkin": days_until_checkin,
            "base_total": total_base,
            "num_guests": num_guests,
            "extra_guest_charge": extra_guest_total,
            "total_price": total
        }
    
    
    def handle_booking(
        self,
        db: Session,
        message: str,
        property_id: int,
        guest_telegram_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Handle booking, negotiation, and payment messages.
        
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
                    "\n\n[CONVERSATION CONTEXT - CRITICAL: Remember and use this information:\n"
                    f"{context_summary}\n"
                    "If dates are mentioned here, use them automatically. DO NOT ask for dates that are already in this context.]"
                )
                messages.append({"role": "system", "content": context_note})
        except Exception as e:
            print(f"Error getting conversation context: {e}")
        
        # Extract dates from current message or history
        current_dates = None
        previous_dates = None
        try:
            current_message_dates = extract_dates_from_history([{"role": "user", "content": message}])
            if current_message_dates:
                current_dates = current_message_dates
            
            if conversation_history:
                history_dates = extract_dates_from_history(conversation_history)
                if history_dates:
                    previous_dates = history_dates
                    if not current_dates:
                        current_dates = history_dates
                    
                    # Check if dates changed (for price reset logic)
                    dates_changed = False
                    if current_dates and previous_dates:
                        curr_checkin = current_dates.get('check_in')
                        curr_checkout = current_dates.get('check_out')
                        prev_checkin = previous_dates.get('check_in')
                        prev_checkout = previous_dates.get('check_out')
                        
                        if curr_checkin and curr_checkout and prev_checkin and prev_checkout:
                            if (curr_checkin != prev_checkin or curr_checkout != prev_checkout):
                                dates_changed = True
                                print(f"Date change detected: {prev_checkin}-{prev_checkout} → {curr_checkin}-{curr_checkout}")
                    
                    # Add context note
                    if dates_changed:
                        prev_negotiation = ""
                        try:
                            prev_context = persistent_context or get_conversation_context(db, guest_telegram_id, property_id)
                            if prev_context.get("negotiated_price") and prev_context.get("negotiated_dates"):
                                prev_price = prev_context["negotiated_price"]
                                prev_dates = prev_context["negotiated_dates"]
                                prev_negotiation = (
                                    f" Previous negotiation: PKR {prev_price:,.2f} for "
                                    f"{prev_dates['check_in']} to {prev_dates['check_out']}. This price was for different dates."
                                )
                        except Exception:
                            pass
                        
                        context_note = (
                            f"\n\n[CRITICAL CONTEXT: Guest CHANGED dates. Previous: {previous_dates['check_in']} to {previous_dates['check_out']}. "
                            f"New: {current_dates['check_in']} to {current_dates['check_out']}.{prev_negotiation} "
                            "Explain that the previous rate was for different dates. Calculate new price for new dates. "
                            "Use the new dates automatically - DO NOT ask for them.]"
                        )
                    else:
                        context_note = (
                            f"\n\n[CRITICAL CONTEXT - MANDATORY: Guest has already provided dates - "
                            f"Check-in: {current_dates['check_in']}, Check-out: {current_dates['check_out']}. "
                            "These dates are CONFIRMED and MUST be used. DO NOT ask for these dates again under ANY circumstances. "
                            "Use these dates automatically in ALL responses. If user says 'yes', 'ok', 'sure' to booking, "
                            "proceed DIRECTLY to payment explanation using these dates. NEVER ask for dates if they exist in this context.]"
                        )
                    messages.insert(-1, {"role": "system", "content": context_note})
        except Exception as e:
            print(f"Error extracting dates: {e}")
        
        if not current_dates and persistent_context.get("dates"):
            current_dates = persistent_context["dates"]
        if not previous_dates and persistent_context.get("dates"):
            previous_dates = persistent_context["dates"]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Handle price negotiation requests - inform that prices are fixed
        message_lower = message.lower()
        negotiation_keywords = ["discount", "negotiate", "negotiation", "lower", "cheaper", "deal", "best price", "can you reduce", "reduce price"]
        is_negotiation = any(keyword in message_lower for keyword in negotiation_keywords)
        
        if is_negotiation and current_dates:
            try:
                check_in = datetime.strptime(current_dates["check_in"], "%Y-%m-%d")
                check_out = datetime.strptime(current_dates["check_out"], "%Y-%m-%d")
                nights = (check_out - check_in).days
                price_info = self.calculate_price(property_id, check_in, check_out, 1, db)
                
                if "error" not in price_info:
                    base_total = price_info['total_price']
                    price_per_night = base_total / nights if nights > 0 else base_total
                    
                    fixed_price_context = (
                        f"\n\n[IMPORTANT: Guest asked for discount/negotiation. "
                        f"Prices are FIXED - base price × number of nights. "
                        f"For {nights} nights, the fixed price is PKR {base_total:,.2f} (PKR {price_per_night:,.2f} per night). "
                        f"Politely explain that prices are fixed and cannot be negotiated. "
                        f"DO NOT ask for dates again - dates are already confirmed: {current_dates['check_in']} to {current_dates['check_out']}.]"
                    )
                    messages.insert(-1, {"role": "system", "content": fixed_price_context})
            except Exception as e:
                print(f"Error handling price inquiry: {e}")
        
        # Check if user wants to proceed with booking
        booking_intent_keywords = ["yes", "yeah", "sure", "ok", "okay", "proceed", "let's do it", "lets do it", "please", "go ahead"]
        message_lower_for_booking = message.lower().strip()
        is_just_booking_intent = len(message_lower_for_booking.split()) <= 3
        wants_to_book = is_just_booking_intent and any(keyword in message_lower_for_booking for keyword in booking_intent_keywords)
        
        payment_discussed = False
        payment_keywords = ["payment", "screenshot", "bank", "jazzcash", "easypaisa", "sadapay", "transfer"]
        if conversation_history:
            for history_msg in reversed(conversation_history):
                content = history_msg.get("content", "").lower()
                if any(keyword in content for keyword in payment_keywords):
                    payment_discussed = True
                    break
        
        if wants_to_book and current_dates:
            try:
                check_in = datetime.strptime(current_dates["check_in"], "%Y-%m-%d")
                check_out = datetime.strptime(current_dates["check_out"], "%Y-%m-%d")
                price_info = self.calculate_price(property_id, check_in, check_out, 1, db)
                total_price = price_info.get("total_price", 0)
                
                # Use negotiated price if exists and dates match
                negotiated_price = persistent_context.get("negotiated_price")
                negotiated_dates = persistent_context.get("negotiated_dates")
                if negotiated_price and negotiated_dates == current_dates:
                    total_price = negotiated_price
                
                # Get payment methods
                payment_methods_text = ""
                try:
                    if property_obj and property_obj.host:
                        payment_methods = property_obj.host.get_payment_methods()
                        if payment_methods:
                            methods_list = []
                            for method in payment_methods:
                                bank_name = method.get("bank_name", "Unknown")
                                account = method.get("account_number", "N/A")
                                account_name = method.get("account_name")
                                instructions = method.get("instructions")
                                line = f"- {bank_name}"
                                if account_name:
                                    line += f" ({account_name})"
                                line += f": {account}"
                                if instructions:
                                    line += f" — {instructions}"
                                methods_list.append(line)
                            payment_methods_text = "\n".join(methods_list)
                except Exception:
                    pass
                
                # Add booking instruction
                if payment_discussed:
                    if payment_methods_text:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User confirmed the booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}. "
                            f"Total: PKR {total_price:,.2f}. Payment methods were already discussed earlier. "
                            f"Immediately show ALL payment methods below and ask for screenshot with full name and bank name:\n{payment_methods_text}\n"
                            "Mention that payment has to be verified by the host afterwards.]"
                        )
                    else:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User confirmed the booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}. "
                            f"Total: PKR {total_price:,.2f}. Payment was already discussed but host payment methods are missing. "
                            "Tell the guest that the host will share specific payment details shortly and still ask for payment screenshot "
                            "with their full name and bank name once details are provided.]"
                        )
                else:
                    if payment_methods_text:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User wants to proceed with booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}. "
                            f"Total: PKR {total_price:,.2f}. FIRST ask 'Do we continue to payment?' and wait for confirmation. "
                            f"After they say yes, explain payment methods with ALL bank details:\n{payment_methods_text}\n"
                            "Then ask for payment screenshot along with full name and bank name they're sending from.]"
                        )
                    else:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User wants to proceed with booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}. "
                            f"Total: PKR {total_price:,.2f}. Host payment methods are not configured. "
                            "Ask 'Do we continue to payment?' and once they say yes, explain that the host will provide payment details manually. "
                            "Still ask them to prepare a payment screenshot along with their full name and bank name.]"
                        )
                messages.insert(-1, {"role": "system", "content": booking_instruction})
            except Exception:
                booking_instruction = (
                    f"\n\n[CRITICAL: User wants to proceed with booking. Dates are confirmed: {current_dates['check_in']} to {current_dates['check_out']}. "
                    "DO NOT ask for dates again. Guide them to payment with the best available information.]"
                )
                messages.insert(-1, {"role": "system", "content": booking_instruction})
        
        # Get LLM response
        try:
            response = self.get_llm_response(messages, temperature=0.7)
            
            # Determine action
            action = "booking"
            metadata = {
                "property_id": property_id,
                "guest_telegram_id": guest_telegram_id,
                "user_id": guest_telegram_id,
            }
            
            # Save dates if found
            if current_dates:
                metadata["dates"] = current_dates
                from api.utils.conversation_context import save_conversation_context
                save_conversation_context(
                    db,
                    guest_telegram_id,
                    property_id,
                    {"dates": current_dates}
                )
            
            # Check if response indicates payment request
            payment_keywords = ["payment", "screenshot", "bank", "transfer"]
            if any(keyword in response.lower() for keyword in payment_keywords) or wants_to_book:
                action = "payment_requested"
                metadata["booking_intent"] = True
                if current_dates:
                    metadata["booking_dates"] = current_dates
            
            # Log the booking interaction
            log_event(
                db=db,
                event_type=EventType.GUEST_BOOKING_REQUEST,
                message=f"Booking request from guest: {message[:100]}",
                property_id=property_id,
                metadata=metadata
            )
            
            # Log agent response
            log_event(
                db=db,
                event_type=EventType.AGENT_RESPONSE,
                message=f"BookingAgent response: {response[:100]}",
                property_id=property_id,
                metadata={
                    "agent_name": "BookingAgent",
                    "action": action,
                    "user_id": guest_telegram_id,
                }
            )
            
            return {
                "response": response,
                "action": action,
                "metadata": metadata,
                "property_id": property_id
            }
            
        except Exception as e:
            print(f"Error in BookingAgent.handle_booking: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": "I'm sorry, I encountered an error processing your booking request. Please try again.",
                "action": "error",
                "metadata": {"error": str(e)}
            }

