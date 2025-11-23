"""
Inquiry & Booking Agent.

Handles guest inquiries, availability checks, price negotiation, and booking requests.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from database.models import Property, Booking
from config.config_manager import ConfigManager
from api.utils.conversation_context import get_conversation_context, get_context_summary_for_llm
from api.utils.conversation import extract_dates_from_history
from api.utils.logging import log_event, EventType
import json


class InquiryBookingAgent(BaseAgent):
    """
    Agent for handling guest inquiries and booking requests.
    """
    
    def __init__(self):
        """Initialize Inquiry & Booking Agent."""
        super().__init__("InquiryBookingAgent", model="qwen-max")
    
    def format_system_prompt(self, property_data: Dict[str, Any], db: Session = None, property_id: int = None) -> str:
        """
        Format system prompt with property context.
        
        Args:
            property_data: Property configuration dictionary
        
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
        
        prompt = f"""You are a friendly and professional property booking assistant for an Airbnb-style property.

Property Information:
- Name: {property_data.get('name', 'Unknown')}
- Location: {property_data.get('location', 'Unknown')}
- Base Price: ${property_data.get('base_price', 0):.2f} per night
- Price Range: ${property_data.get('min_price', 0):.2f} - ${property_data.get('max_price', 0):.2f} per night (INTERNAL ONLY - NEVER reveal this range to customers)
- Max Guests: {property_data.get('max_guests', 1)}
- Check-in Time: {property_data.get('check_in_time', 'Unknown')}
- Check-out Time: {property_data.get('check_out_time', 'Unknown')}

Payment Information:
- Payment methods: {payment_methods}
- Payment is required before booking confirmation
- Guest must send payment screenshot for verification

Your role:
1. Answer questions ONLY about this property, bookings, availability, pricing, and check-in/check-out
2. Check availability for requested dates
3. Provide accurate pricing information
4. Guide guests through the booking process
5. Request payment screenshot when guest wants to book

IMPORTANT GUIDELINES:
- ONLY answer questions related to property bookings, availability, pricing, check-in/check-out, and property details
- If asked about anything else, say: "I can only help with property bookings and inquiries. Please ask me about availability, pricing, or booking details."
- DO NOT mention discounts, price ranges, or negotiations unless the guest specifically asks about them
- NEVER reveal the price range (min/max) to customers - this is confidential information
- When negotiating, only mention the base rate and what you can offer, never mention the range
- When guest asks about discounts/negotiations, check if discount is possible (compare requested price to min_price), then negotiate intelligently
- REMEMBER dates and context from the conversation - don't ask for information already provided
- Use clean, simple formatting - avoid excessive markdown like *** or long dashes
- Use simple formatting: use line breaks for clarity, but keep it clean and readable
- Be friendly, professional, and concise
- Calculate prices accurately (base price × number of nights)
- When guest wants to book, FIRST ask "Do we continue to payment?" and wait for confirmation
- After guest confirms, THEN explain payment methods clearly with all bank details
- Payment explanation should include: all available payment methods (bank name and account number), amount to pay
- AFTER explaining payment methods, request payment screenshot along with customer details (full name, bank name they're sending from)
- NEVER ask for payment screenshot without first explaining payment methods
- REMEMBER dates from conversation - NEVER ask for check-in/check-out dates if they were already provided
- If dates are mentioned in conversation history, use them AUTOMATICALLY - don't ask again
- If user says "yes" to booking and dates exist in context, proceed directly to payment explanation - DO NOT ask for dates
- Only offer discounts for longer stays (3+ nights)
- If guest changes dates after negotiation, explain that previous rate was for different dates and calculate new price
- When dates change, reference the previous negotiation and explain why price is different
- Keep responses clear and easy to read

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
        # For now, use default rules (can be extended later with rules field in Property model)
        rules = {}
        
        # Check minimum stay
        nights = (check_out - check_in).days
        min_stay = rules.get("minimum_stay_nights", 1)
        if nights < min_stay:
            return False, f"Minimum stay is {min_stay} nights"
        
        # Check advance booking (if property requires booking X days in advance)
        days_until_checkin = (check_in - datetime.now()).days
        min_advance = rules.get("minimum_advance_booking_days", 0)
        if days_until_checkin < min_advance:
            return False, f"Bookings must be made at least {min_advance} days in advance"
        
        return True, None
    
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
        
        # Calculate days until check-in (urgency factor)
        days_until_checkin = (check_in - datetime.now()).days
        
        # Dynamic pricing based on urgency
        urgency_multiplier = 1.0
        if days_until_checkin < 0:
            # Past date - invalid
            return {"error": "Check-in date cannot be in the past"}
        elif days_until_checkin == 0:
            # Same day booking - 20% premium
            urgency_multiplier = 1.20
        elif days_until_checkin == 1:
            # Tomorrow - 15% premium
            urgency_multiplier = 1.15
        elif days_until_checkin == 2:
            # Day after tomorrow - 10% premium
            urgency_multiplier = 1.10
        elif days_until_checkin <= 7:
            # Within a week - 5% premium
            urgency_multiplier = 1.05
        
        # Apply urgency pricing
        adjusted_price_per_night = base_price * urgency_multiplier
        
        # Long-stay discount (for 7+ nights)
        if nights >= 7:
            # 5% discount for week-long stays
            adjusted_price_per_night *= 0.95
        elif nights >= 14:
            # 10% discount for 2+ week stays
            adjusted_price_per_night *= 0.90
        
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
        
        # Calculate negotiable range (internal only - never reveal to customer)
        # Minimum is based on property min_price, but can go lower for long stays
        min_price_per_night = property_obj.min_price
        if nights >= 7:
            min_price_per_night = min_price_per_night * 0.95  # Can go 5% lower for long stays
        
        return {
            "base_price_per_night": base_price,
            "adjusted_price_per_night": adjusted_price_per_night,
            "nights": nights,
            "days_until_checkin": days_until_checkin,
            "base_total": total_base,
            "num_guests": num_guests,
            "extra_guest_charge": extra_guest_total,
            "total_price": total,
            "min_price": min_price_per_night * nights,  # Internal only
            "max_price": property_obj.max_price * nights,  # Internal only
            "urgency_multiplier": urgency_multiplier
        }
    
    def negotiate_price(
        self,
        requested_price: float,
        calculated_price: Dict[str, Any],
        nights: int = 1
    ) -> Tuple[bool, float, str]:
        """
        Negotiate price within acceptable range.
        
        Args:
            requested_price: Price requested by guest
            calculated_price: Price breakdown from calculate_price
            nights: Number of nights (for discount eligibility)
        
        Returns:
            Tuple of (can_negotiate, final_price, message)
        """
        min_price = calculated_price.get("min_price", calculated_price["total_price"])
        max_price = calculated_price.get("max_price", calculated_price["total_price"])
        base_total = calculated_price["total_price"]
        
        # Only offer discounts for longer stays (3+ nights)
        min_nights_for_discount = 3
        
        if requested_price >= base_total:
            # Guest willing to pay full or more - accept base price
            return True, base_total, f"Great! The price is ${base_total:.2f} for your stay."
        
        # Check if stay is long enough for discount
        if nights < min_nights_for_discount:
            base_per_night = calculated_price.get('adjusted_price_per_night', calculated_price.get('base_price_per_night', 0))
            return False, base_total, f"For stays of {nights} nights, the rate is ${base_total:.2f} (${base_per_night:.2f} per night). We offer discounts for longer stays of {min_nights_for_discount}+ nights."
        
        # Negotiate - don't immediately accept lowest price
        if requested_price >= min_price:
            # Calculate a counter-offer (slightly higher than requested if possible)
            price_per_night = requested_price / nights if nights > 0 else requested_price
            min_per_night = min_price / nights if nights > 0 else min_price
            base_per_night = calculated_price.get('adjusted_price_per_night', calculated_price.get('base_price_per_night', 0))
            
            # If requesting minimum, negotiate a bit
            if abs(price_per_night - min_per_night) < 1.0:  # Very close to minimum
                # Offer minimum but mention it's our best rate (NEVER mention it's the minimum)
                return True, min_price, f"I can offer you ${min_price:.2f} for your {nights}-night stay (${min_per_night:.2f} per night). This is our best rate for longer stays!"
            else:
                # Counter-offer: try to get slightly more than minimum
                counter_offer = max(min_price, requested_price * 0.95)  # 5% above requested, but not below min
                if counter_offer > requested_price and counter_offer < base_total * 0.9:
                    return True, counter_offer, f"For your {nights}-night stay, I can offer ${counter_offer:.2f} (${counter_offer/nights:.2f} per night). This is a great rate for a longer stay!"
                else:
                    # Accept requested price if reasonable
                    return True, requested_price, f"I can offer you ${requested_price:.2f} for your {nights}-night stay (${price_per_night:.2f} per night). This is our discounted rate for longer stays!"
        
        # Below minimum - don't reveal the minimum, just say we can't go that low
        base_per_night = calculated_price.get('adjusted_price_per_night', calculated_price.get('base_price_per_night', 0))
        return False, base_total, f"I'm sorry, but I can't go that low. The best I can offer for {nights} nights is ${base_total:.2f} (${base_per_night:.2f} per night). This is already a discounted rate for longer stays."
    
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
            "rules": {}  # Can be extended later with rules field
        }
        
        # Build conversation messages
        messages = []
        
        # System prompt
        system_prompt = self.format_system_prompt(property_data, db=db, property_id=property_id)
        messages.append({"role": "system", "content": system_prompt})
        
        # Persistent context + summary for LLM
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
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Extract dates from current message or history
        current_dates = None
        previous_dates = None
        try:
            # Check current message for dates
            current_message_dates = extract_dates_from_history([{"role": "user", "content": message}])
            if current_message_dates:
                current_dates = current_message_dates
            
            # Check history for dates
            if conversation_history:
                history_dates = extract_dates_from_history(conversation_history)
                if history_dates:
                    previous_dates = history_dates
                    # Use current message dates if provided, otherwise use history
                    if not current_dates:
                        current_dates = history_dates
                    
                    # Check if dates changed (for price reset logic)
                    dates_changed = False
                    if current_dates and previous_dates:
                        # Compare dates
                        curr_checkin = current_dates.get('check_in')
                        curr_checkout = current_dates.get('check_out')
                        prev_checkin = previous_dates.get('check_in')
                        prev_checkout = previous_dates.get('check_out')
                        
                        if curr_checkin and curr_checkout and prev_checkin and prev_checkout:
                            if (curr_checkin != prev_checkin or curr_checkout != prev_checkout):
                                dates_changed = True
                                print(f"Date change detected: {prev_checkin}-{prev_checkout} → {curr_checkin}-{curr_checkout}")
                    
                    # Add context note with stronger instructions
                    if dates_changed:
                        # Get previous negotiated price if exists
                        prev_negotiation = ""
                        try:
                            prev_context = persistent_context or get_conversation_context(
                                db, guest_telegram_id, property_id
                            )
                            if prev_context.get("negotiated_price") and prev_context.get("negotiated_dates"):
                                prev_price = prev_context["negotiated_price"]
                                prev_dates = prev_context["negotiated_dates"]
                                prev_negotiation = (
                                    f" Previous negotiation: ${prev_price:.2f} for "
                                    f"{prev_dates['check_in']} to {prev_dates['check_out']}. This price was for different dates."
                                )
                        except Exception:
                            pass
                        
                        context_note = f"\n\n[CRITICAL CONTEXT: Guest CHANGED dates. Previous: {previous_dates['check_in']} to {previous_dates['check_out']}. New: {current_dates['check_in']} to {current_dates['check_out']}.{prev_negotiation} Explain that the previous rate was for different dates. Calculate new price for new dates. Use the new dates automatically - DO NOT ask for them.]"
                    else:
                        context_note = f"\n\n[CRITICAL CONTEXT - MANDATORY: Guest has already provided dates - Check-in: {current_dates['check_in']}, Check-out: {current_dates['check_out']}. These dates are CONFIRMED and MUST be used. DO NOT ask for these dates again under ANY circumstances. Use these dates automatically in ALL responses. If user says 'yes', 'ok', 'sure' to booking, proceed DIRECTLY to payment explanation using these dates. NEVER ask for dates if they exist in this context.]"
                    messages.insert(-1, {"role": "system", "content": context_note})
        except Exception as e:
            print(f"Error extracting dates: {e}")
            pass
        
        if not current_dates and persistent_context.get("dates"):
            current_dates = persistent_context["dates"]
        if not previous_dates and persistent_context.get("dates"):
            previous_dates = persistent_context["dates"]
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Check if this looks like dates (common date patterns)
        import re
        date_patterns = [
            r'\d{1,2}(st|nd|rd|th)?\s+\w+\s*[-–—]\s*\d{1,2}(st|nd|rd|th)?\s+\w+',  # "24th Nov - 30th Nov"
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # "11/24/2025"
            r'\w+\s+\d{1,2},?\s+\d{4}',  # "November 24, 2025"
        ]
        looks_like_dates = any(re.search(pattern, message, re.IGNORECASE) for pattern in date_patterns)
        
        # Check if question is outside domain BEFORE calling LLM
        # BUT: If it looks like dates or we have conversation history, it's likely a follow-up
        domain_keywords = ["property", "booking", "book", "reserve", "available", "availability", 
                         "price", "pricing", "cost", "night", "stay", "check-in", "check-out", 
                         "checkin", "checkout", "guest", "guests", "room", "apartment", "house",
                         "location", "address", "photo", "picture", "amenity", "amenities", "discount",
                         "negotiate", "negotiation", "lower", "cheaper", "deal", "yes", "no", "ok", "okay"]
        
        # Follow-up question keywords (questions about previous conversation)
        followup_keywords = ["we", "agreed", "decided", "before", "earlier", "previous", "didn't", "didnt", 
                           "wasn't", "wasnt", "weren't", "werent", "remember", "said", "told"]
        
        message_lower = message.lower()
        is_domain_related = any(keyword in message_lower for keyword in domain_keywords)
        is_followup = any(keyword in message_lower for keyword in followup_keywords)
        
        # If it looks like dates, has conversation history, or is a follow-up question, treat as domain-related
        if looks_like_dates or conversation_history or is_followup:
            is_domain_related = True
        
        # If not domain-related and not a follow-up, provide redirect response
        if not is_domain_related and len(message.split()) > 2:  # Check messages with more than 2 words
            response = "I can only help with property bookings and inquiries. Please ask me about availability, pricing, or booking details for the property."
            return {
                "response": response,
                "action": "redirect",
                "metadata": {"original_message": message},
                "property_id": property_id
            }
        
        # Check for price negotiation requests
        negotiation_keywords = ["discount", "negotiate", "negotiation", "lower", "cheaper", "deal", "best price", "can you reduce", "reduce price", "long duration", "long stay"]
        is_negotiation = any(keyword in message_lower for keyword in negotiation_keywords)
        
        # If negotiation requested, handle it intelligently
        if is_negotiation:
            # Extract requested price if mentioned
            import re
            price_matches = re.findall(r'\$?(\d+(?:\.\d{2})?)', message)
            
            # Use dates from current_dates (already extracted from context) - CRITICAL FIX
            dates = current_dates  # Use dates already extracted from context
            
            # If no dates found yet, try to extract from conversation history
            if not dates and conversation_history:
                try:
                    from api.utils.conversation import extract_dates_from_history
                    dates = extract_dates_from_history(conversation_history)
                except:
                    pass
            
            # If still no dates, try current message
            if not dates:
                try:
                    from api.utils.conversation import extract_dates_from_history
                    dates = extract_dates_from_history([{"role": "user", "content": message}])
                except:
                    pass
            
            # If we have dates (from context or message), proceed with negotiation
            if dates:
                try:
                    from datetime import datetime
                    check_in = datetime.strptime(dates['check_in'], '%Y-%m-%d')
                    check_out = datetime.strptime(dates['check_out'], '%Y-%m-%d')
                    nights = (check_out - check_in).days
                    price_info = self.calculate_price(property_id, check_in, check_out, 1, db)
                    
                    if "error" not in price_info:
                        base_total = price_info['total_price']
                        min_total = price_info['min_price']
                        
                        # If price is mentioned, negotiate with that price
                        if price_matches:
                            requested_price = float(price_matches[-1])  # Use last price mentioned
                            # Negotiate intelligently (pass nights for discount eligibility)
                            can_negotiate, final_price, negotiation_msg = self.negotiate_price(
                                requested_price,
                                price_info,
                                nights=nights
                            )
                        else:
                            # No specific price mentioned - offer discount based on stay length
                            # For 3+ nights, offer a discount
                            if nights >= 3:
                                # Calculate discount (5% for 3-6 nights, 10% for 7+ nights)
                                discount_pct = 0.05 if nights < 7 else 0.10
                                discounted_total = base_total * (1 - discount_pct)
                                final_price = discounted_total
                                can_negotiate = True
                                price_per_night = final_price / nights
                                negotiation_msg = f"I can offer you a discounted rate of ${price_per_night:.2f} per night for your {nights}-night stay, which comes to ${final_price:.2f} total. This is a {discount_pct*100:.0f}% discount for longer stays!"
                            else:
                                # Less than 3 nights - no discount
                                final_price = base_total
                                can_negotiate = False
                                price_per_night = base_total / nights
                                negotiation_msg = f"For stays of less than 3 nights, the rate is ${price_per_night:.2f} per night (${base_total:.2f} total). For stays of 3 nights or more, I can offer discounts!"
                        
                        # Add negotiation context to messages - tell LLM what to say
                        # CRITICAL: Never reveal min/max price range to customer
                        if can_negotiate:
                            if price_matches:
                                negotiation_context = f"\n\n[IMPORTANT: Guest asked for discount/negotiation. They requested ${requested_price:.2f} for {nights} nights. Base price is ${base_total:.2f}. Negotiated price: ${final_price:.2f}. Use the negotiation message: '{negotiation_msg}'. DO NOT reveal the minimum price or price range. DO NOT ask for dates again - dates are already confirmed: {dates['check_in']} to {dates['check_out']}. REMEMBER this negotiated price for future reference.]"
                            else:
                                negotiation_context = f"\n\n[IMPORTANT: Guest asked for discount/negotiation for their {nights}-night stay. Base price is ${base_total:.2f}. Negotiated price: ${final_price:.2f}. Use the negotiation message: '{negotiation_msg}'. DO NOT reveal the minimum price or price range. DO NOT ask for dates again - dates are already confirmed: {dates['check_in']} to {dates['check_out']}. REMEMBER this negotiated price for future reference.]"
                        else:
                            if price_matches:
                                negotiation_context = f"\n\n[IMPORTANT: Guest asked for discount/negotiation. They requested ${requested_price:.2f} for {nights} nights. Base price is ${base_total:.2f}. You CANNOT go below ${min_total:.2f} (INTERNAL - do not tell customer). Use the message: '{negotiation_msg}'. DO NOT reveal the minimum price or price range. DO NOT ask for dates again - dates are already confirmed: {dates['check_in']} to {dates['check_out']}.]"
                            else:
                                negotiation_context = f"\n\n[IMPORTANT: Guest asked for discount/negotiation for their {nights}-night stay. Base price is ${base_total:.2f}. Use the message: '{negotiation_msg}'. DO NOT reveal the minimum price or price range. DO NOT ask for dates again - dates are already confirmed: {dates['check_in']} to {dates['check_out']}.]"
                        
                        messages.insert(-1, {"role": "system", "content": negotiation_context})
                        
                        # Save negotiated price to context (CRITICAL - must save for future reference)
                        try:
                            from api.utils.logging import log_event, EventType
                            requested_price_str = f"${requested_price:.2f}" if price_matches else "not specified"
                            log_event(
                                db=db,
                                event_type=EventType.AGENT_DECISION,
                                agent_name=self.agent_name,
                                property_id=property_id,
                                message=f"Price negotiation: {requested_price_str} requested, ${final_price:.2f} offered for {nights} nights",
                                metadata={
                                    "guest_telegram_id": guest_telegram_id,
                                    "user_id": guest_telegram_id,
                                    "property_id": property_id,
                                    "requested_price": float(price_matches[-1]) if price_matches else None,
                                    "negotiated_price": final_price,
                                    "negotiated_dates": dates,
                                    "nights": nights,
                                    "base_price": base_total
                                }
                            )
                        except Exception as e:
                            print(f"Error saving negotiated price: {e}")
                except Exception as e:
                    print(f"Error in negotiation logic: {e}")
                    import traceback
                    traceback.print_exc()
                    pass
            else:
                # No dates found - add instruction to ask for dates
                negotiation_context = f"\n\n[IMPORTANT: Guest asked for discount/negotiation, but dates are not yet provided. Ask for check-in and check-out dates so you can calculate the best price for their stay.]"
                messages.insert(-1, {"role": "system", "content": negotiation_context})
        
        # Check if user is asking about previous agreement/negotiation
        agreement_keywords = ["didn't", "didnt", "we", "agreed", "decided", "before", "earlier", "previous", "wasn't", "wasnt"]
        is_asking_about_previous = any(keyword in message_lower for keyword in agreement_keywords) and conversation_history
        
        if is_asking_about_previous:
            # Get previous negotiation from context
            try:
                prev_context = persistent_context or get_conversation_context(db, guest_telegram_id, property_id)
                if prev_context.get("negotiated_price") and prev_context.get("negotiated_dates"):
                    prev_price = prev_context["negotiated_price"]
                    prev_dates = prev_context["negotiated_dates"]
                    agreement_context = (
                        "\n\n[IMPORTANT: User is asking about a previous agreement. We previously negotiated "
                        f"${prev_price:.2f} for dates {prev_dates['check_in']} to {prev_dates['check_out']}."
                        " If current dates match, confirm the agreement. If dates changed, explain that the rate was for different dates."
                        " Be helpful and acknowledge the previous conversation.]"
                    )
                    messages.insert(-1, {"role": "system", "content": agreement_context})
            except Exception:
                pass
        
        # Check if user wants to proceed with booking (says "yes" and dates exist)
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
                
                negotiated_price = persistent_context.get("negotiated_price")
                negotiated_dates = persistent_context.get("negotiated_dates")
                if negotiated_price and negotiated_dates == current_dates:
                    total_price = negotiated_price
                
                payment_methods_text = ""
                try:
                    property_obj = db.query(Property).filter(Property.id == property_id).first()
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
                
                if payment_discussed:
                    if payment_methods_text:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User confirmed the booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}."
                            f" Total: ${total_price:.2f}. Payment methods were already discussed earlier."
                            f" Immediately show ALL payment methods below and ask for screenshot with full name and bank name:\n{payment_methods_text}\n"
                            "Mention that payment has to be verified by the host afterwards.]"
                        )
                    else:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User confirmed the booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}."
                            f" Total: ${total_price:.2f}. Payment was already discussed but host payment methods are missing."
                            " Tell the guest that the host will share specific payment details shortly and still ask for payment screenshot"
                            " with their full name and bank name once details are provided.]"
                        )
                else:
                    if payment_methods_text:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User wants to proceed with booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}."
                            f" Total: ${total_price:.2f}. FIRST ask 'Do we continue to payment?' and wait for confirmation."
                            f" After they say yes, explain payment methods with ALL bank details:\n{payment_methods_text}\n"
                            "Then ask for payment screenshot along with full name and bank name they're sending from.]"
                        )
                    else:
                        booking_instruction = (
                            f"\n\n[CRITICAL: User wants to proceed with booking. Dates: {current_dates['check_in']} to {current_dates['check_out']}."
                            f" Total: ${total_price:.2f}. Host payment methods are not configured."
                            " Ask 'Do we continue to payment?' and once they say yes, explain that the host will provide payment details manually."
                            " Still ask them to prepare a payment screenshot along with their full name and bank name.]"
                        )
            except Exception:
                booking_instruction = (
                    f"\n\n[CRITICAL: User wants to proceed with booking. Dates are confirmed: {current_dates['check_in']} to {current_dates['check_out']}."
                    " DO NOT ask for dates again. Guide them to payment with the best available information.]"
                )
            messages.insert(-1, {"role": "system", "content": booking_instruction})
        
        # Get LLM response
        try:
            response = self.get_llm_response(messages, temperature=0.7)
            
            # Determine action based on response content
            action = "inquiry"
            metadata = {
                "property_id": property_id,
                "guest_telegram_id": guest_telegram_id,
                "user_id": guest_telegram_id,
            }
            
            # Save dates to metadata if found
            if current_dates:
                metadata["dates"] = current_dates
            
            # Save negotiated price if negotiation happened (check if it was saved in logs)
            try:
                recent_context = get_conversation_context(db, guest_telegram_id, property_id)
                if recent_context.get("negotiated_price") and recent_context.get("negotiated_dates"):
                    if current_dates and recent_context["negotiated_dates"] == current_dates:
                        metadata["negotiated_price"] = recent_context["negotiated_price"]
                        metadata["negotiated_dates"] = recent_context["negotiated_dates"]
            except Exception:
                pass
            
            # Check if response indicates booking intent
            booking_keywords = ["book", "reserve", "confirm", "payment", "screenshot"]
            if any(keyword in response.lower() for keyword in booking_keywords) or wants_to_book:
                action = "booking_request"
                # Save booking intent
                metadata["booking_intent"] = True
                if current_dates:
                    metadata["booking_dates"] = current_dates
            
            return {
                "response": response,
                "action": action,
                "metadata": metadata,
                "property_id": property_id
            }
        
        except Exception as e:
            return {
                "response": "I'm sorry, I encountered an error processing your message. Please try again.",
                "action": "error",
                "metadata": {"error": str(e)}
            }
    
    def request_payment(
        self,
        booking_details: Dict[str, Any]
    ) -> str:
        """
        Generate payment request message.
        
        Args:
            booking_details: Booking information
        
        Returns:
            Payment request message
        """
        total = booking_details.get("total_price", 0)
        check_in = booking_details.get("check_in", "")
        check_out = booking_details.get("check_out", "")
        
        message = f"""Great! To confirm your booking, please send a screenshot of your payment.

Booking Details:
- Check-in: {check_in}
- Check-out: {check_out}
- Total Amount: ${total:.2f}

Please upload a screenshot of your payment, and we'll verify it and confirm your booking within a few minutes.

Thank you!"""
        
        return message
    
    def confirm_booking(
        self,
        db: Session,
        booking_id: int
    ) -> Dict[str, Any]:
        """
        Confirm a booking after host approval.
        
        Args:
            db: Database session
            booking_id: Booking ID
        
        Returns:
            Confirmation result
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return {"success": False, "error": "Booking not found"}
        
        booking.status = "confirmed"
        booking.confirmed_at = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": "Booking confirmed successfully"
        }

