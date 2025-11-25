"""
Guest bot handler.

Handles messages from guests via the guest Telegram bot.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from api.telegram.base import get_bot_token, send_message, parse_telegram_update
from api.utils.logging import log_event, EventType
from api.utils.conversation import get_conversation_history
from api.utils.conversation_context import get_conversation_context
from api.utils.payment import (
    handle_payment_screenshot,
    send_payment_to_host,
    save_pending_payment_request,
    get_pending_payment_request,
    clear_pending_payment_request,
)
from database.models import Booking, Property, SystemLog
from agents.inquiry_booking_agent import InquiryBookingAgent  # Deprecated, kept for backward compatibility
from agents.inquiry_agent import InquiryAgent
from agents.booking_agent import BookingAgent
from api.utils.agent_router import determine_agent, update_agent_context

# Global state for /clear confirmation flow
CLEAR_CONFIRMATION_STATE: Dict[str, int] = {}

# Global state for /book_property flow
BOOK_PROPERTY_STATE: Dict[str, Dict[str, Any]] = {}

# Global state for fixed booking questions flow
BOOKING_QUESTIONS_STATE: Dict[str, Dict[str, Any]] = {}


def _reset_clear_state(user_id: str) -> None:
    """Reset the clear confirmation state for a user."""
    CLEAR_CONFIRMATION_STATE.pop(user_id, None)


def _delete_guest_history(db: Session, guest_id: str) -> None:
    """Remove bookings and logs associated with a guest."""
    # Delete bookings
    db.query(Booking).filter(Booking.guest_telegram_id == guest_id).delete(synchronize_session=False)
    
    # Delete logs that mention this guest
    db.query(SystemLog).filter(
        or_(
            SystemLog.event_metadata.like(f"%{guest_id}%"),
            SystemLog.message.like(f"%{guest_id}%")
        )
    ).delete(synchronize_session=False)
    
    db.commit()


def _extract_customer_details(text: Optional[str]) -> Dict[str, Optional[str]]:
    """Extract customer name and bank name from a text snippet."""
    if not text:
        return {"customer_name": None, "customer_bank_name": None}
    
    import re
    
    name_match = re.search(r"(?:name|full name)[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
    bank_match = re.search(r"(?:bank|from|sent from)[:\s]+([A-Za-z0-9\s]+)", text, re.IGNORECASE)
    
    return {
        "customer_name": name_match.group(1).strip() if name_match else None,
        "customer_bank_name": bank_match.group(1).strip() if bank_match else None,
    }


async def handle_guest_message(
    db: Session,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle incoming message from guest bot.
    
    Args:
        db: Database session
        update_data: Telegram webhook update data
    
    Returns:
        Response dictionary
    """
    parsed = parse_telegram_update(update_data)
    
    if not parsed["message"]:
        return {"status": "no_message"}
    
    chat_id = parsed["chat_id"]
    user_id = parsed["user_id"]
    text = parsed["text"]
    
    # Get property for logging (try to find from context, otherwise None)
    property_id_for_log = None
    all_properties = db.query(Property).all()
    for prop in all_properties:
        context = get_conversation_context(db, user_id, prop.id)
        if context.get("selected_property_id"):
            property_id_for_log = context.get("selected_property_id")
            break
    
    # Log the guest message
    log_event(
        db=db,
        event_type=EventType.GUEST_MESSAGE,
        agent_name="GuestBot",
        property_id=property_id_for_log,
        message=f"Guest {user_id}: {text}",
        metadata={
            "chat_id": chat_id,
            "user_id": user_id,
            "property_id": property_id_for_log,
            "text": text,
            "has_photo": parsed["photo"] is not None,
            "has_document": parsed["document"] is not None
        }
    )
    
    # Handle destructive commands /clear
    if parsed["is_command"]:
        command = parsed["command"]
        if command == "clear":
            CLEAR_CONFIRMATION_STATE[user_id] = 1
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message=(
                    "⚠️ Reset requested.\n\n"
                    "All conversation history, negotiation context, and pending bookings tied to this chat will be deleted.\n"
                    "If you're sure, send /clear_confirm (step 1 of 2)."
                )
            )
            return {"status": "command_processed", "command": "clear"}
        if command == "clear_confirm":
            state = CLEAR_CONFIRMATION_STATE.get(user_id)
            if state == 1:
                CLEAR_CONFIRMATION_STATE[user_id] = 2
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message=(
                        "⚠️ Final confirmation.\n\n"
                        "Sending /clear_confirm again right now will permanently delete:\n"
                        "- All previous messages and context\n"
                        "- Any recorded negotiations\n"
                        "- Any pending bookings or payment data\n\n"
                        "This action cannot be undone. Send /clear_confirm once more to proceed."
                    )
                )
                return {"status": "command_processed", "command": "clear_confirm_warning"}
            elif state == 2:
                # Delete all guest data
                pending_event, _ = get_pending_payment_request(db, user_id)
                if pending_event:
                    await clear_pending_payment_request(db, pending_event)
                _delete_guest_history(db, user_id)
                _reset_clear_state(user_id)
                
                # Get and delete bot messages
                from api.telegram.message_tracker import get_bot_message_ids, delete_bot_messages
                bot_token = get_bot_token("guest")
                if bot_token:
                    message_ids = get_bot_message_ids(db, user_id, limit=100)
                    if message_ids:
                        deleted_count = await delete_bot_messages(bot_token, chat_id, message_ids)
                        print(f"Deleted {deleted_count} bot messages for user {user_id}")
                
                # Clear conversation context completely
                from api.utils.conversation_context import save_conversation_context
                save_conversation_context(
                    db,
                    user_id,
                    None,  # No property_id - clear all
                    {
                        "active_agent": None,
                        "booking_intent": False,
                        "dates": None,
                        # Note: negotiated_price removed - prices are now fixed
                    }
                )
                
                # Send final message (this will be the only message left)
                final_msg_id = await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="✅ All data has been deleted. Please use /start to begin a new conversation.\n\nNote: Your messages cannot be deleted (Telegram limitation), but all bot messages and stored data have been removed."
                )
                
                return {"status": "command_processed", "command": "clear_confirm_done", "require_start": True}
            else:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="No pending /clear request. Send /clear first if you want to reset the chat."
                )
                return {"status": "command_processed", "command": "clear_confirm_noop"}
    
    # Handle /book_property command
    if parsed["is_command"] and parsed["command"] == "book_property":
        bot_token = get_bot_token("guest")
        if bot_token:
            # Get all available properties
            properties = db.query(Property).all()
            
            if not properties:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="❌ No properties are currently available. Please contact the host."
                )
                return {"status": "command_processed", "command": "book_property"}
            
            # Start property selection flow
            BOOK_PROPERTY_STATE[user_id] = {"step": "select_property"}
            
            # List available properties
            properties_list = "📋 **Available Properties:**\n\n"
            for i, prop in enumerate(properties, 1):
                properties_list += f"{i}. 🏠 **{prop.name}**\n"
                properties_list += f"   📍 {prop.location}\n"
                properties_list += f"   💰 PKR {prop.base_price:,.2f} per night\n\n"
            
            properties_list += "Please send me the **property name** you want to book (e.g., 'Lakeside Loft'):"
            
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=properties_list
            )
            return {"status": "command_processed", "command": "book_property"}
    
    # Handle property selection in /book_property flow
    if user_id in BOOK_PROPERTY_STATE:
        state = BOOK_PROPERTY_STATE[user_id]
        step = state.get("step")
        
        if step == "select_property":
            # Search for property by name (case-insensitive, partial match)
            property_name = text.strip()
            property_obj = db.query(Property).filter(
                Property.name.ilike(f"%{property_name}%")
            ).first()
            
            if not property_obj:
                # Try exact match first
                property_obj = db.query(Property).filter(
                    Property.name.ilike(property_name)
                ).first()
            
            if not property_obj:
                # List available properties again
                properties = db.query(Property).all()
                properties_list = "❌ Property not found. Available properties:\n\n"
                for prop in properties:
                    properties_list += f"• {prop.name}\n"
                properties_list += "\nPlease send the exact property name:"
                
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message=properties_list
                )
                return {"status": "property_selection"}
            
            # Property found - save to context and clear state
            selected_property_id = property_obj.id
            BOOK_PROPERTY_STATE.pop(user_id, None)
            
            # Save property selection to context
            from api.utils.conversation_context import save_conversation_context
            save_conversation_context(
                db,
                user_id,
                selected_property_id,
                {
                    "active_agent": "booking",
                    "booking_intent": True,
                    "selected_property_id": selected_property_id
                }
            )
            
            # Start fixed booking questions flow
            BOOKING_QUESTIONS_STATE[user_id] = {
                "step": "booking_checkin",
                "property_id": selected_property_id,
                "data": {}
            }
            
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message=f"✅ Selected: **{property_obj.name}**\n\n"
                        f"📍 Location: {property_obj.location}\n"
                        f"💰 Price: PKR {property_obj.base_price:,.2f} per night\n"
                        f"👥 Max Guests: {property_obj.max_guests}\n\n"
                        f"📋 Let's collect your booking details:\n\n"
                        f"**1. Check-in Date:**\n"
                        f"Please provide your check-in date (e.g., 'November 25, 2025' or '25/11/2025'):"
            )
            return {"status": "property_selected", "property_id": selected_property_id}
    
    # Handle fixed booking questions flow
    if user_id in BOOKING_QUESTIONS_STATE:
        state = BOOKING_QUESTIONS_STATE[user_id]
        step = state.get("step")
        data = state.get("data", {})
        property_id = state.get("property_id")
        
        if step == "booking_checkin":
            # Parse check-in date
            from api.utils.conversation import extract_dates_from_history
            from datetime import datetime
            dates = extract_dates_from_history([{"role": "user", "content": text}])
            
            if dates and dates.get("check_in"):
                data["check_in"] = dates["check_in"]
                state["step"] = "booking_checkout"
                state["data"] = data
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message=f"✅ Check-in date saved: {dates['check_in']}\n\n"
                            f"**2. Check-out Date:**\n"
                            f"Please provide your check-out date (e.g., 'November 30, 2025' or '30/11/2025'):"
                )
                return {"status": "booking_question"}
            else:
                # Try to parse single date
                try:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            parsed = datetime.strptime(text.strip(), fmt)
                            data["check_in"] = parsed.strftime('%Y-%m-%d')
                            state["step"] = "booking_checkout"
                            state["data"] = data
                            await send_message(
                                bot_token=get_bot_token("guest"),
                                chat_id=chat_id,
                                message=f"✅ Check-in date saved: {parsed.strftime('%B %d, %Y')}\n\n"
                                        f"**2. Check-out Date:**\n"
                                        f"Please provide your check-out date (e.g., 'November 30, 2025' or '30/11/2025'):"
                            )
                            return {"status": "booking_question"}
                        except:
                            continue
                except:
                    pass
                
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ I couldn't understand the date format. Please provide your check-in date in one of these formats:\n"
                            "• November 25, 2025\n"
                            "• 25/11/2025\n"
                            "• 2025-11-25"
                )
                return {"status": "booking_question"}
        
        elif step == "booking_checkout":
            # Parse check-out date
            from api.utils.conversation import extract_dates_from_history
            from datetime import datetime
            dates = extract_dates_from_history([{"role": "user", "content": text}])
            
            if dates and dates.get("check_out"):
                data["check_out"] = dates["check_out"]
            else:
                # Try to parse single date
                try:
                    for fmt in ['%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            parsed = datetime.strptime(text.strip(), fmt)
                            data["check_out"] = parsed.strftime('%Y-%m-%d')
                            break
                        except:
                            continue
                except:
                    pass
            
            if not data.get("check_out"):
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ I couldn't understand the date format. Please provide your check-out date in one of these formats:\n"
                            "• November 30, 2025\n"
                            "• 30/11/2025\n"
                            "• 2025-11-30"
                )
                return {"status": "booking_question"}
            
            # Validate dates
            check_in = datetime.strptime(data["check_in"], '%Y-%m-%d')
            check_out = datetime.strptime(data["check_out"], '%Y-%m-%d')
            if check_out <= check_in:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ Check-out date must be after check-in date. Please provide a valid check-out date:"
                )
                return {"status": "booking_question"}
            
            state["step"] = "booking_guests"
            state["data"] = data
            
            # Get property for max guests
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            max_guests = property_obj.max_guests if property_obj else 10
            
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message=f"✅ Check-out date saved: {check_out.strftime('%B %d, %Y')}\n\n"
                        f"**3. Number of Guests:**\n"
                        f"How many guests will be staying? (Maximum: {max_guests})"
            )
            return {"status": "booking_question"}
        
        elif step == "booking_guests":
            # Parse number of guests
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                num_guests = int(numbers[0])
                property_obj = db.query(Property).filter(Property.id == property_id).first()
                max_guests = property_obj.max_guests if property_obj else 10
                
                if num_guests < 1:
                    await send_message(
                        bot_token=get_bot_token("guest"),
                        chat_id=chat_id,
                        message="❌ Number of guests must be at least 1. Please provide a valid number:"
                    )
                    return {"status": "booking_question"}
                
                if num_guests > max_guests:
                    await send_message(
                        bot_token=get_bot_token("guest"),
                        chat_id=chat_id,
                        message=f"❌ Maximum {max_guests} guests allowed. Please provide a number between 1 and {max_guests}:"
                    )
                    return {"status": "booking_question"}
                
                data["number_of_guests"] = num_guests
                state["step"] = "payment_name"
                state["data"] = data
                
                # Calculate price
                check_in = datetime.strptime(data["check_in"], '%Y-%m-%d')
                check_out = datetime.strptime(data["check_out"], '%Y-%m-%d')
                nights = (check_out - check_in).days
                property_obj = db.query(Property).filter(Property.id == property_id).first()
                total_price = property_obj.base_price * nights if property_obj else 0
                data["total_price"] = total_price
                data["nights"] = nights
                
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message=f"✅ Number of guests saved: {num_guests}\n\n"
                            f"📋 **Booking Summary:**\n"
                            f"• Check-in: {check_in.strftime('%B %d, %Y')}\n"
                            f"• Check-out: {check_out.strftime('%B %d, %Y')}\n"
                            f"• Nights: {nights}\n"
                            f"• Guests: {num_guests}\n"
                            f"• Total: PKR {total_price:,.2f}\n\n"
                            f"💰 **Payment Details:**\n\n"
                            f"**4. Your Full Name:**\n"
                            f"Please provide your full name as it appears on your ID:"
                )
                return {"status": "booking_question"}
            else:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ Please provide a number for the number of guests (e.g., '2' or '2 guests'):"
                )
                return {"status": "booking_question"}
        
        elif step == "payment_name":
            # Store customer name
            if len(text.strip()) < 2:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ Please provide your full name (at least 2 characters):"
                )
                return {"status": "booking_question"}
            
            data["customer_name"] = text.strip()
            state["step"] = "payment_bank"
            state["data"] = data
            
            # Get host payment details to show to guest (specific to this property's host)
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            host = property_obj.host if property_obj else None
            payment_methods_text = ""
            if host and property_obj:
                # Calculate total amount FIRST
                check_in = datetime.strptime(data["check_in"], "%Y-%m-%d")
                check_out = datetime.strptime(data["check_out"], "%Y-%m-%d")
                nights = (check_out - check_in).days
                total_price = property_obj.base_price * nights
                
                payment_methods_text = f"\n\n💰 **Payment Required:**\n"
                payment_methods_text += f"• Property: {property_obj.name}\n"
                payment_methods_text += f"• {nights} night(s) × PKR {property_obj.base_price:,.2f}\n"
                payment_methods_text += f"• **Total Amount: PKR {total_price:,.2f}**\n"
                
                payment_methods_list = host.get_payment_methods()
                if payment_methods_list:
                    payment_methods_text += f"\n💳 **Transfer to ({host.name}):**\n"
                    for pm in payment_methods_list:
                        bank_name = pm.get('bank_name', 'N/A')
                        account_number = pm.get('account_number', 'N/A')
                        account_name = pm.get('account_name', '')
                        payment_methods_text += f"• **{bank_name}**: {account_number}"
                        if account_name:
                            payment_methods_text += f" ({account_name})"
                        payment_methods_text += "\n"
            
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message=f"✅ Name saved: {text.strip()}{payment_methods_text}\n\n"
                        f"**5. Your Bank Name:**\n"
                        f"Which bank or payment service are you sending payment from?\n"
                        f"(e.g., HBL Bank, JazzCash, EasyPaisa, SadaPay, Meezan Bank, etc.)"
            )
            return {"status": "booking_question"}
        
        elif step == "payment_bank":
            # Store bank name
            if len(text.strip()) < 2:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="❌ Please provide the bank name (e.g., 'JazzCash' or 'HBL Bank'):"
                )
                return {"status": "booking_question"}
            
            data["customer_bank_name"] = text.strip()
            state["step"] = "payment_screenshot"
            state["data"] = data
            BOOKING_QUESTIONS_STATE[user_id] = state
            
            # Get payment methods from the specific property's host
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            host = property_obj.host if property_obj else None
            payment_methods_text = ""
            if host:
                payment_methods_list = host.get_payment_methods()
                if payment_methods_list:
                    payment_methods_text = f"\n\n💳 **Pay to {host.name}:**\n"
                    for pm in payment_methods_list:
                        bank_name = pm.get('bank_name', 'N/A')
                        account_number = pm.get('account_number', 'N/A')
                        account_name = pm.get('account_name', '')
                        payment_methods_text += f"• **{bank_name}**: {account_number}"
                        if account_name:
                            payment_methods_text += f" ({account_name})"
                        payment_methods_text += "\n"
            
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message=f"✅ Bank name saved: {text.strip()}\n\n"
                        f"**6. Payment Screenshot:**\n"
                        f"Please upload a screenshot of your payment transfer.{payment_methods_text}\n\n"
                        f"After uploading, your booking will be sent to the host for verification."
            )
            return {"status": "awaiting_screenshot"}
    
    # Handle /start command
    if parsed["is_command"] and parsed["command"] == "start":
        bot_token = get_bot_token("guest")
        if bot_token:
            # Reset conversation context
            from api.utils.conversation_context import save_conversation_context
            save_conversation_context(
                db,
                user_id,
                None,
                {
                    "active_agent": "inquiry",
                    "booking_intent": False,
                }
            )
            
            welcome_message = """Welcome! 👋

I'm your autonomous property booking assistant. I can help you with:
• Checking property availability
• Getting pricing information
• Making bookings
• Answering questions about properties

📋 **Commands:**
/inquiry - View available properties and ask questions
/book_property - Select a property to book directly
/qna - Ask questions about properties, bookings, or general inquiries

Just use /inquiry or /book_property to begin, or ask me anything about our properties!"""
            
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=welcome_message,
                timeout=10
            )
            
            return {"status": "command_processed", "command": "start"}
    
    # Handle /inquiry command
    if parsed["is_command"] and parsed["command"] == "inquiry":
        bot_token = get_bot_token("guest")
        if bot_token:
            # Get all properties for the inquiry message
            properties = db.query(Property).all()
            
            # Reset to inquiry agent
            from api.utils.conversation_context import save_conversation_context
            save_conversation_context(
                db,
                user_id,
                None,
                {
                    "active_agent": "inquiry",
                    "booking_intent": False,
                }
            )
            
            if not properties:
                inquiry_message = """📋 **Property Inquiry**

I'm sorry, no properties are currently available. Please contact the host for more information.

You can ask me questions about properties, availability, or pricing anytime!"""
            else:
                inquiry_message = "📋 **Available Properties:**\n\n"
                
                for prop in properties:
                    inquiry_message += f"🏠 **{prop.name}**\n"
                    inquiry_message += f"📍 {prop.location}\n"
                    inquiry_message += f"💰 PKR {prop.base_price:,.2f} per night\n"
                    inquiry_message += f"👥 Max {prop.max_guests} guests\n"
                    inquiry_message += f"🕐 Check-in: {prop.check_in_time} | Check-out: {prop.check_out_time}\n\n"
                
                inquiry_message += "You can now ask me about:\n"
                inquiry_message += "• Availability for specific dates\n"
                inquiry_message += "• Pricing information\n"
                inquiry_message += "• Property details\n"
                inquiry_message += "• Booking inquiries"
            
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=inquiry_message,
                timeout=10
            )
            
            return {"status": "command_processed", "command": "inquiry"}
    
    # Handle /qna command
    if parsed["is_command"] and parsed["command"] == "qna":
        bot_token = get_bot_token("guest")
        if bot_token:
            # Get all properties for context
            properties = db.query(Property).all()
            
            # Set to inquiry agent for QnA
            from api.utils.conversation_context import save_conversation_context
            save_conversation_context(
                db,
                user_id,
                None,
                {
                    "active_agent": "inquiry",
                    "booking_intent": False,
                }
            )
            
            if not properties:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="📋 **Q&A**\n\n"
                            "I'm here to answer your questions! However, no properties are currently available.\n\n"
                            "You can ask me general questions, and I'll do my best to help."
                )
            else:
                # Check if guest has any confirmed bookings
                confirmed_bookings = db.query(Booking).filter(
                    Booking.guest_telegram_id == user_id,
                    Booking.booking_status == 'confirmed'
                ).all()
                
                # Get selected property from context
                selected_property = None
                context = get_conversation_context(db, user_id, None)
                if context.get("selected_property_id"):
                    selected_property = db.query(Property).filter(
                        Property.id == context.get("selected_property_id")
                    ).first()
                
                # If guest has bookings, use that property
                if not selected_property and confirmed_bookings:
                    selected_property = confirmed_bookings[0].property
                
                # If still no property, use first available
                if not selected_property and properties:
                    selected_property = properties[0]
                
                # Build property info and amenities
                property_info = ""
                amenities_text = ""
                if selected_property:
                    property_info = f"\n🏠 **{selected_property.name}**\n"
                    property_info += f"📍 {selected_property.location}\n"
                    property_info += f"💰 PKR {selected_property.base_price:,.2f}/night\n"
                    property_info += f"👥 Max {selected_property.max_guests} guests\n"
                    property_info += f"🕐 Check-in: {selected_property.check_in_time} | Check-out: {selected_property.check_out_time}\n"
                    
                    # Build amenities from FAQs
                    faqs = selected_property.get_faqs()
                    if faqs:
                        amenities_text = "\n📦 **Amenities:**\n"
                        wifi_info = None
                        has_ac = False
                        has_tv = False
                        has_parking = False
                        has_kitchen = False
                        
                        for faq in faqs:
                            if isinstance(faq, dict):
                                q = faq.get('question', '').lower()
                                a = faq.get('answer', '')
                                
                                if 'wifi' in q and 'password' in q.lower():
                                    wifi_info = a
                                elif 'wifi' in q and 'yes' in a.lower():
                                    wifi_info = a
                                elif 'air conditioning' in q and 'yes' in a.lower():
                                    has_ac = True
                                elif 'tv' in q and 'yes' in a.lower():
                                    has_tv = True
                                elif 'parking' in q and 'yes' in a.lower():
                                    has_parking = True
                                elif 'kitchen' in q and 'yes' in a.lower():
                                    has_kitchen = True
                        
                        if wifi_info:
                            amenities_text += f"📶 WiFi: {wifi_info}\n"
                        if has_ac:
                            amenities_text += "❄️ Air Conditioning: ✓\n"
                        if has_tv:
                            amenities_text += "📺 TV: ✓\n"
                        if has_parking:
                            amenities_text += "🚗 Parking: ✓\n"
                        if has_kitchen:
                            amenities_text += "🍳 Kitchen: ✓\n"
                
                # Build the message
                if confirmed_bookings:
                    booking_info = "📋 **Q&A - You have active bookings!**\n\n"
                    booking_info += "**Your Bookings:**\n"
                    for booking in confirmed_bookings:
                        booking_info += f"✅ {booking.property.name}\n"
                        booking_info += f"   Check-in: {booking.check_in_date.strftime('%B %d, %Y')}\n"
                        booking_info += f"   Check-out: {booking.check_out_date.strftime('%B %d, %Y')}\n"
                    booking_info += property_info
                    booking_info += amenities_text
                    booking_info += "\n💬 **Ask me anything!**\n"
                    booking_info += "Examples:\n"
                    booking_info += "• What's the WiFi password?\n"
                    booking_info += "• Is parking available?\n"
                    booking_info += "• What time is check-in?\n"
                    booking_info += "• How do I get to the property?"
                else:
                    booking_info = "📋 **Q&A Assistant**\n"
                    booking_info += property_info
                    booking_info += amenities_text
                    booking_info += "\n💬 **Ask me anything!**\n"
                    booking_info += "Examples:\n"
                    booking_info += "• What's the WiFi password?\n"
                    booking_info += "• Is parking available?\n"
                    booking_info += "• What amenities are included?\n"
                    booking_info += "• What's the price per night?\n"
                    booking_info += "• How many guests can stay?"
                
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=booking_info
                )
            
            return {"status": "command_processed", "command": "qna"}
    
    # If we are awaiting customer payment details, intercept the message before other handling
    pending_event = None
    pending_metadata = None
    if text:
        pending_event, pending_metadata = get_pending_payment_request(
            db=db,
            guest_telegram_id=user_id,
            property_id=property_id_for_log
        )
    
    if pending_event and pending_metadata and text and not parsed["photo"]:
        details = _extract_customer_details(text)
        customer_name = details.get("customer_name")
        customer_bank_name = details.get("customer_bank_name")
        
        if not customer_name or not customer_bank_name:
            missing_bits = []
            if not customer_name:
                missing_bits.append("full name")
            if not customer_bank_name:
                missing_bits.append("bank name")
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="I still need the following details before sending your payment for verification:\n"
                        f"- {' and '.join(missing_bits)}\n\n"
                        "Please send them in the format:\nName: John Doe\nBank: JazzCash"
            )
            return {"status": "awaiting_customer_details"}
        
        property_id = pending_metadata.get("property_id") or property_id_for_log
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="I'm sorry, no properties are configured yet. Please contact the host."
            )
            return {"status": "error", "message": "No properties configured"}
        
        context = get_conversation_context(db, user_id, property_obj.id)
        dates = pending_metadata.get("dates") or context.get("dates")
        if not dates:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="I need your booking dates first. Please provide your check-in and check-out dates, then resend your payment details."
            )
            return {"status": "error", "message": "No dates in context"}
        
        # Calculate price: base price × number of nights (fixed pricing)
        from datetime import datetime
        check_in = datetime.strptime(dates["check_in"], "%Y-%m-%d")
        check_out = datetime.strptime(dates["check_out"], "%Y-%m-%d")
        nights = (check_out - check_in).days
        final_price = property_obj.base_price * nights
        
        booking_details = {
            "check_in": dates["check_in"],
            "check_out": dates["check_out"],
            "final_price": final_price,
            "requested_price": final_price,
            "number_of_guests": 1,
            "customer_name": customer_name,
            "customer_bank_name": customer_bank_name,
            "guest_name": customer_name,
        }
        
        booking = await handle_payment_screenshot(
            db=db,
            guest_telegram_id=user_id,
            file_id=pending_metadata.get("file_id"),
            property_id=property_obj.id,
            booking_details=booking_details
        )
        
        if booking:
            await clear_pending_payment_request(db, pending_event)
            await send_payment_to_host(db=db, booking=booking)
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="✅ Thank you! I've received your payment details and screenshot and sent them to the host for verification."
            )
            return {"status": "payment_received", "booking_id": booking.id}
        else:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="❌ There was an issue processing your payment. Please try again or contact support."
            )
            return {"status": "error", "message": "Failed to process payment screenshot"}
    
    # Check if this is a photo (payment screenshot)
    if parsed["photo"]:
        # Get the largest photo (last in the array)
        photos = parsed["photo"]
        if not photos:
            return {"status": "error", "message": "No photo found"}
        
        # Get largest photo (Telegram sends multiple sizes)
        largest_photo = photos[-1]
        file_id = largest_photo.get("file_id")
        
        if not file_id:
            return {"status": "error", "message": "No file ID found"}
        
        # Check if we're in the fixed booking questions flow
        if user_id in BOOKING_QUESTIONS_STATE:
            state = BOOKING_QUESTIONS_STATE[user_id]
            if state.get("step") == "payment_screenshot":
                data = state.get("data", {})
                property_id = state.get("property_id")
                
                # Get property
                property_obj = db.query(Property).filter(Property.id == property_id).first()
                if not property_obj:
                    await send_message(
                        bot_token=get_bot_token("guest"),
                        chat_id=chat_id,
                        message="❌ Error: Property not found. Please start over with /book_property"
                    )
                    BOOKING_QUESTIONS_STATE.pop(user_id, None)
                    return {"status": "error", "message": "Property not found"}
                
                # Prepare booking details from fixed questions
                booking_details = {
                    "check_in": data.get("check_in"),
                    "check_out": data.get("check_out"),
                    "final_price": data.get("total_price"),
                    "number_of_guests": data.get("number_of_guests", 1),
                    "customer_name": data.get("customer_name"),
                    "customer_bank_name": data.get("customer_bank_name")
                }
                
                # Create booking with screenshot
                booking = await handle_payment_screenshot(
                    db=db,
                    guest_telegram_id=user_id,
                    file_id=file_id,
                    property_id=property_id,
                    booking_details=booking_details
                )
                
                if booking:
                    # Clear booking questions state
                    BOOKING_QUESTIONS_STATE.pop(user_id, None)
                    
                    # Send to host for verification
                    await send_payment_to_host(db=db, booking=booking)
                    
                    # Confirm to guest
                    await send_message(
                        bot_token=get_bot_token("guest"),
                        chat_id=chat_id,
                        message="✅ Thank you! Your payment screenshot has been received and sent to the host for verification.\n\n"
                                "You will receive a confirmation message once the host verifies your payment."
                    )
                    
                    return {"status": "payment_received", "booking_id": booking.id}
                else:
                    await send_message(
                        bot_token=get_bot_token("guest"),
                        chat_id=chat_id,
                        message="❌ I'm sorry, there was an error processing your payment screenshot. Please try again or contact support."
                    )
                    return {"status": "error", "message": "Failed to process payment screenshot"}
            else:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="Please complete the booking questions first. We're waiting for your answers."
                )
                return {"status": "error", "message": "Not ready for screenshot"}
        
        # Fallback: Old flow (for backward compatibility)
        # Check if we have a selected property in context
        all_properties = db.query(Property).all()
        selected_property_id = None
        
        # Check context from any property to find selected_property_id
        for prop in all_properties:
            context = get_conversation_context(db, user_id, prop.id)
            if context.get("selected_property_id"):
                selected_property_id = context.get("selected_property_id")
                break
        
        if not selected_property_id:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="📋 Please select a property first using /book_property before uploading a payment screenshot."
            )
            return {"status": "error", "message": "No property selected"}
        
        property_obj = db.query(Property).filter(Property.id == selected_property_id).first()
        if not property_obj:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="❌ Error: Selected property not found. Please use /book_property to select a property again."
            )
            return {"status": "error", "message": "Property not found"}
        
        # Get booking details from conversation context
        context = get_conversation_context(db, user_id, property_obj.id)
        
        # Check if we have dates and price from context
        if not context.get("dates"):
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="I need your booking dates first. Please provide your check-in and check-out dates, then upload the payment screenshot."
            )
            return {"status": "error", "message": "No dates in context"}
        
        dates = context["dates"]
        
        # Calculate price: base price × number of nights (fixed pricing)
        from datetime import datetime
        check_in = datetime.strptime(dates["check_in"], "%Y-%m-%d")
        check_out = datetime.strptime(dates["check_out"], "%Y-%m-%d")
        nights = (check_out - check_in).days
        final_price = property_obj.base_price * nights
        
        details = _extract_customer_details(parsed["text"])
        customer_name = details.get("customer_name")
        customer_bank_name = details.get("customer_bank_name")
        
        # If not found in current message, ask for details and remember pending state
        if not customer_name or not customer_bank_name:
            await save_pending_payment_request(
                db=db,
                guest_telegram_id=user_id,
                property_id=property_obj.id,
                file_id=file_id,
                dates=dates,
                negotiated_price=final_price  # Keep parameter name for backward compatibility
            )
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="Please provide your payment details along with the screenshot:\n\n"
                        "1. Your full name\n"
                        "2. Bank name you're sending payment from (e.g., JazzCash, SadaPay, EasyPaisa, or bank name)\n\n"
                        "You can send it as a message like:\n"
                        "Name: [Your Name]\n"
                        "Bank: [Bank Name]"
            )
            return {"status": "awaiting_customer_details", "file_id": file_id}
        
        # Prepare booking details
        booking_details = {
            "check_in": dates["check_in"],
            "check_out": dates["check_out"],
            "final_price": final_price,
            "number_of_guests": 1,  # Default, can be enhanced later
            "customer_name": customer_name,
            "customer_bank_name": customer_bank_name
        }
        
        booking = await handle_payment_screenshot(
            db=db,
            guest_telegram_id=user_id,
            file_id=file_id,
            property_id=property_obj.id,
            booking_details=booking_details
        )
        
        if booking:
            # Send to host for approval
            await send_payment_to_host(db=db, booking=booking)
            
            # Confirm to guest
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="✅ Thank you for uploading the payment screenshot and details. We have received it and sent it to the host for verification. You will receive a confirmation message once the payment is verified."
            )
            
            return {"status": "payment_received", "booking_id": booking.id}
        else:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="❌ I'm sorry, there was an error processing your payment screenshot. Please try again or contact support."
            )
            return {"status": "error", "message": "Failed to process payment screenshot"}
    
    # Check if user needs to start conversation (after /clear)
    context = get_conversation_context(db, user_id, None)
    if context.get("active_agent") is None and not parsed["is_command"]:
        # User cleared conversation but hasn't started new one
        await send_message(
            bot_token=get_bot_token("guest"),
            chat_id=chat_id,
            message="Please use /start to begin a new conversation."
        )
        return {"status": "require_start"}
    
    # Route message to Inquiry & Booking Agent
    bot_token = get_bot_token("guest")
    if bot_token and text:
        # Get property - check context first for selected property, then use first property as fallback
        property_obj = None
        # Try to get context with any property_id first to check for selected_property_id
        all_properties = db.query(Property).all()
        selected_property_id = None
        
        # Check context from any property to find selected_property_id
        for prop in all_properties:
            context = get_conversation_context(db, user_id, prop.id)
            if context.get("selected_property_id"):
                selected_property_id = context.get("selected_property_id")
                break
        
        if selected_property_id:
            property_obj = db.query(Property).filter(Property.id == selected_property_id).first()
        
        # Check if we're in QnA mode (after /qna command) - allow questions without property
        context_check = get_conversation_context(db, user_id, None)
        is_qna_mode = context_check.get("active_agent") == "inquiry" and not context_check.get("booking_intent")
        
        # For QnA mode, try to find property from bookings if not selected
        if is_qna_mode and not property_obj:
            confirmed_booking = db.query(Booking).filter(
                Booking.guest_telegram_id == user_id,
                Booking.booking_status == 'confirmed'
            ).order_by(Booking.check_in_date.desc()).first()
            
            if confirmed_booking:
                property_obj = confirmed_booking.property
        
        # Require property selection for non-QnA mode
        if not property_obj and not is_qna_mode:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="📋 Please select a property first using /book_property or /inquiry to view available properties.\n\n"
                        "I need to know which property you're asking about before I can help you."
            )
            return {"status": "error", "message": "No property selected"}
        
        # Send "thinking" message immediately to avoid timeout
        # We'll delete it after sending the actual response
        thinking_message_id = None
        try:
            from telegram import Bot as TelegramBot
            bot = TelegramBot(token=bot_token)
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text="🤔 Let me check that for you...",
                read_timeout=5,
                write_timeout=5,
                connect_timeout=5
            )
            thinking_message_id = sent_msg.message_id
        except Exception as e:
            print(f"Warning: Could not send thinking message: {e}")
            # Continue anyway - this is not critical
        
        # Determine which agent to use
        try:
            
            # Use hybrid QnA handler if in QnA mode
            if is_qna_mode:
                from api.utils.qna_handler import handle_qna_with_fallback
                agent = InquiryAgent()
                result = handle_qna_with_fallback(
                    db=db,
                    question=text,
                    property_id=property_obj.id if property_obj else None,
                    guest_telegram_id=user_id,
                    llm_agent=agent
                )
            else:
                # Regular flow - need property
                if not property_obj:
                    await send_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message="📋 Please select a property first using /book_property or /inquiry to view available properties.\n\n"
                                "I need to know which property you're asking about before I can help you."
                    )
                    return {"status": "error", "message": "No property selected"}
                
                # Get conversation history for context
                conversation_history = get_conversation_history(
                    db=db,
                    guest_telegram_id=user_id,
                    property_id=property_obj.id,
                    limit=10  # Last 10 messages
                )
                
                # Use router to determine which agent to use
                agent_type = determine_agent(
                    db=db,
                    guest_telegram_id=user_id,
                    property_id=property_obj.id,
                    message=text,
                    conversation_history=conversation_history
                )
                
                # Initialize appropriate agent
                if agent_type == "booking":
                    agent = BookingAgent()
                    # Process message with booking agent
                    result = agent.handle_booking(
                        db=db,
                        message=text,
                        property_id=property_obj.id,
                        guest_telegram_id=user_id,
                        conversation_history=conversation_history
                    )
                    # Update context with active agent
                    update_agent_context(
                        db=db,
                        guest_telegram_id=user_id,
                        property_id=property_obj.id,
                        agent_name="booking",
                        booking_intent=True
                    )
                else:
                    # Regular inquiry agent
                    agent = InquiryAgent()
                    result = agent.handle_inquiry(
                        db=db,
                        message=text,
                        property_id=property_obj.id,
                        guest_telegram_id=user_id,
                        conversation_history=conversation_history
                    )
                # Check if inquiry agent wants to transition to booking
                if result.get("action") == "transition_to_booking":
                    # Update context to mark booking intent
                    update_agent_context(
                        db=db,
                        guest_telegram_id=user_id,
                        property_id=property_obj.id,
                        agent_name="booking",
                        booking_intent=True
                    )
                else:
                    # Update context to mark inquiry agent
                    update_agent_context(
                        db=db,
                        guest_telegram_id=user_id,
                        property_id=property_obj.id,
                        agent_name="inquiry",
                        booking_intent=False
                    )
            
            # Send agent response to guest
            response_text = result.get("response", "I'm sorry, I couldn't process that.")
            
            # Clean up markdown formatting - remove excessive formatting
            import re
            # Remove triple asterisks (bold/italic)
            response_text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'\1', response_text)
            # Remove double asterisks (bold)
            response_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', response_text)
            # Replace long dashes with simple dashes
            response_text = response_text.replace('—', '-').replace('–', '-')
            # Clean up extra whitespace
            response_text = re.sub(r'\n{3,}', '\n\n', response_text)
            
            # Truncate very long messages (Telegram has 4096 char limit)
            if len(response_text) > 4000:
                response_text = response_text[:4000] + "\n\n[Message truncated]"
            
            # Send response with retry logic
            try:
                message_id = await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=response_text,
                    timeout=10,  # Shorter timeout, will retry
                    retries=2,    # Retry twice
                    return_message_id=True
                )
                success = message_id is not None
                
                # Store message ID for potential deletion
                if message_id:
                    from api.telegram.message_tracker import store_bot_message_id
                    store_bot_message_id(db, user_id, message_id, property_obj.id)
                
                # Delete the "thinking" message if we sent one
                if thinking_message_id and success:
                    try:
                        from telegram import Bot as TelegramBot
                        bot = TelegramBot(token=bot_token)
                        await bot.delete_message(
                            chat_id=chat_id,
                            message_id=thinking_message_id,
                            read_timeout=5,
                            write_timeout=5,
                            connect_timeout=5
                        )
                    except Exception as e:
                        # If deletion fails, that's okay - just log it
                        print(f"Could not delete thinking message: {e}")
                
                if not success:
                    print(f"Warning: Failed to send response to guest {user_id}")
                    # Log it but don't fail the request
                    try:
                        log_event(
                            db=db,
                            event_type=EventType.AGENT_ERROR,
                            agent_name=agent.agent_name,
                            message=f"Failed to send response to guest {user_id}",
                            metadata={"chat_id": chat_id, "user_id": user_id}
                        )
                    except:
                        pass
            except Exception as send_error:
                print(f"Error sending response to guest: {send_error}")
                # Log but continue
                try:
                    log_event(
                        db=db,
                        event_type=EventType.AGENT_ERROR,
                        agent_name="InquiryBookingAgent",
                        message=f"Exception sending response: {str(send_error)}",
                        metadata={"chat_id": chat_id, "user_id": user_id, "error": str(send_error)}
                    )
                except:
                    pass
            
            # Log agent response with full context
            response_metadata = {
                "chat_id": chat_id,
                "user_id": user_id,
                "action": result.get("action"),
                "property_id": property_obj.id
            }
            
            # Add dates and other context from result metadata
            if result.get("metadata"):
                response_metadata.update(result.get("metadata"))
            
            log_event(
                db=db,
                event_type=EventType.AGENT_RESPONSE,
                agent_name=agent.agent_name,
                message=f"Agent response sent to guest {user_id}",
                metadata=response_metadata
            )
            
            return {
                "status": "processed",
                "chat_id": chat_id,
                "user_id": user_id,
                "action": result.get("action")
            }
        
        except Exception as e:
            # Log error
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in handle_guest_message: {error_trace}")
            
            try:
                log_event(
                    db=db,
                    event_type=EventType.AGENT_ERROR,
                    agent_name="InquiryBookingAgent",
                    message=f"Error processing guest message: {str(e)}",
                    metadata={"chat_id": chat_id, "user_id": user_id, "error": str(e)}
                )
            except Exception as log_error:
                print(f"Error logging event: {log_error}")
            
            # Send error message to guest
            try:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="I'm sorry, I encountered an error processing your message. Please try again in a moment.",
                    timeout=10
                )
            except Exception as send_error:
                print(f"Error sending error message to guest: {send_error}")
            
            return {"status": "error", "message": str(e)}
    
    return {"status": "processed", "chat_id": chat_id, "user_id": user_id}


async def send_guest_message(
    chat_id: str,
    message: str
) -> bool:
    """
    Send a message to a guest.
    
    Args:
        chat_id: Guest chat ID
        message: Message to send
    
    Returns:
        True if sent successfully
    """
    bot_token = get_bot_token("guest")
    if not bot_token:
        print("Guest bot token not configured")
        return False
    
    return await send_message(bot_token, chat_id, message)

