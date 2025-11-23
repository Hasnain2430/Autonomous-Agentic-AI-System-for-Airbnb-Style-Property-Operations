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
from agents.inquiry_booking_agent import InquiryBookingAgent

# Global state for /clear confirmation flow
CLEAR_CONFIRMATION_STATE: Dict[str, int] = {}


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
    
    # Get property for logging (use first property if available)
    property_obj_for_log = db.query(Property).first()
    property_id_for_log = property_obj_for_log.id if property_obj_for_log else None
    
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
                pending_event, _ = get_pending_payment_request(db, user_id)
                if pending_event:
                    await clear_pending_payment_request(db, pending_event)
                _delete_guest_history(db, user_id)
                _reset_clear_state(user_id)
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="✅ Conversation reset complete. All stored context has been deleted. You can start fresh now!"
                )
                return {"status": "command_processed", "command": "clear_confirm_done"}
            else:
                await send_message(
                    bot_token=get_bot_token("guest"),
                    chat_id=chat_id,
                    message="No pending /clear request. Send /clear first if you want to reset the chat."
                )
                return {"status": "command_processed", "command": "clear_confirm_noop"}
    
    # Handle /start command
    if parsed["is_command"] and parsed["command"] == "start":
        bot_token = get_bot_token("guest")
        if bot_token:
            # Get all properties for the welcome message
            properties = db.query(Property).all()
            
            if not properties:
                welcome_message = """Welcome! 👋

I'm your property booking assistant. I can help you with:
- Checking property availability
- Getting pricing information
- Making bookings
- Answering questions about properties

However, no properties are currently available. Please contact the host for more information."""
            else:
                welcome_message = "Welcome! 👋\n\n"
                welcome_message += "I'm your property booking assistant. I can help you with:\n"
                welcome_message += "- Checking property availability\n"
                welcome_message += "- Getting pricing information\n"
                welcome_message += "- Making bookings\n"
                welcome_message += "- Answering questions about properties\n\n"
                welcome_message += "Available Properties:\n\n"
                
                for prop in properties:
                    welcome_message += f"🏠 {prop.name}\n"
                    welcome_message += f"📍 {prop.location}\n"
                    welcome_message += f"💰 ${prop.base_price:.2f} per night\n"
                    welcome_message += f"👥 Max {prop.max_guests} guests\n"
                    welcome_message += f"🕐 Check-in: {prop.check_in_time} | Check-out: {prop.check_out_time}\n\n"
                
                welcome_message += "Just ask me about availability, pricing, or anything else about these properties!"
            
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=welcome_message,
                timeout=10
            )
            
            return {"status": "command_processed", "command": "start"}
    
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
        
        booking_details = {
            "check_in": dates["check_in"],
            "check_out": dates["check_out"],
            "final_price": pending_metadata.get("negotiated_price") or context.get("negotiated_price"),
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
        # Check if this is a payment screenshot (should have customer details in previous message or caption)
        # For now, we'll check the previous message for customer details
        # In a more sophisticated implementation, we could use a state machine
        
        # Get the largest photo (last in the array)
        photos = parsed["photo"]
        if not photos:
            return {"status": "error", "message": "No photo found"}
        
        # Get largest photo (Telegram sends multiple sizes)
        largest_photo = photos[-1]
        file_id = largest_photo.get("file_id")
        
        if not file_id:
            return {"status": "error", "message": "No file ID found"}
        
        # Get property
        property_obj = db.query(Property).first()
        if not property_obj:
            await send_message(
                bot_token=get_bot_token("guest"),
                chat_id=chat_id,
                message="I'm sorry, no properties are configured yet. Please contact the host."
            )
            return {"status": "error", "message": "No properties configured"}
        
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
        negotiated_price = context.get("negotiated_price")
        
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
                negotiated_price=negotiated_price
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
            "final_price": negotiated_price,
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
    
    # Route message to Inquiry & Booking Agent
    bot_token = get_bot_token("guest")
    if bot_token and text:
        # Get property - for now, use the first property (can be enhanced later)
        property_obj = db.query(Property).first()
        
        if not property_obj:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="I'm sorry, no properties are configured yet. Please contact the host."
            )
            return {"status": "error", "message": "No properties configured"}
        
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
        
        # Initialize agent and process message
        try:
            agent = InquiryBookingAgent()
            
            # Get conversation history for context
            conversation_history = get_conversation_history(
                db=db,
                guest_telegram_id=user_id,
                property_id=property_obj.id,
                limit=10  # Last 10 messages
            )
            
            # Process message with agent (this may take time for LLM call)
            result = agent.handle_inquiry(
                db=db,
                message=text,
                property_id=property_obj.id,
                guest_telegram_id=user_id,
                conversation_history=conversation_history
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
                success = await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=response_text,
                    timeout=10,  # Shorter timeout, will retry
                    retries=2    # Retry twice
                )
                
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
                            agent_name="InquiryBookingAgent",
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

