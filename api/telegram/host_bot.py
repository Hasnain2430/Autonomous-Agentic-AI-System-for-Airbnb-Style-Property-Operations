"""
Host bot handler.

Handles messages from host via the host Telegram bot.
Includes configuration commands and payment approvals.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from api.telegram.base import get_bot_token, send_message, send_photo, parse_telegram_update
from api.utils.logging import log_event, EventType
from config.config_manager import ConfigManager
from database.models import Host, Booking, Property


# Store conversation state for multi-step setup flows
# In production, use Redis or database for this
_conversation_states = {}


def _ensure_host_record(db: Session, telegram_id: str) -> Host:
    """
    Ensure there is a host row associated with this Telegram ID.
    If an existing host record uses a placeholder/old ID, update it.
    """
    host = db.query(Host).filter(Host.telegram_id == telegram_id).first()
    if host:
        return host
    
    existing_host = db.query(Host).first()
    if existing_host:
        existing_host.telegram_id = telegram_id
        db.commit()
        db.refresh(existing_host)
        return existing_host
    
    # No host yet — create a minimal one so approval flow works
    return ConfigManager.create_host(
        db=db,
        name="Host",
        email="host@example.com",
        telegram_id=telegram_id,
        preferred_language="en"
    )


async def handle_host_message(
    db: Session,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle incoming message from host bot.
    
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
    text = parsed["text"] or ""
    
    # Always link this Telegram ID to the primary host record
    host_record = _ensure_host_record(db, user_id)
    
    # Log the host message
    log_event(
        db=db,
        event_type=EventType.HOST_ESCALATION_RECEIVED,
        agent_name="HostBot",
        message=f"Host {user_id}: {text}",
        metadata={
            "chat_id": chat_id,
            "user_id": user_id,
            "text": text
        }
    )
    
    bot_token = get_bot_token("host")
    if not bot_token:
        return {"status": "error", "message": "Host bot token not configured"}
    
    # Handle commands
    if parsed["is_command"]:
        command = parsed["command"]
        
        if command == "start":
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Welcome! I'm your property management assistant.\n\n"
                        "Available commands:\n"
                        "/setup - Set up your host profile\n"
                        "/add_property - Add a new property\n"
                        "/help - Show this help message"
            )
            return {"status": "command_processed", "command": "start"}
        
        elif command == "setup":
            # Start host setup flow
            _conversation_states[user_id] = {"step": "setup_name", "data": {}}
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Let's set up your host profile!\n\nPlease send me your name:"
            )
            return {"status": "command_processed", "command": "setup"}
        
        elif command == "add_property":
            # Start property setup flow
            _conversation_states[user_id] = {"step": "property_identifier", "data": {}}
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Let's add a new property!\n\nPlease send me a unique property identifier (e.g., PROP001):"
            )
            return {"status": "command_processed", "command": "add_property"}
        
        elif command == "help":
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Available commands:\n"
                        "/setup - Set up your host profile\n"
                        "/add_property - Add a new property\n"
                        "/help - Show this help message\n\n"
                        "For payment approvals, just reply 'yes' or 'no' when asked."
            )
            return {"status": "command_processed", "command": "help"}
        
        else:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Unknown command: /{command}\n\nUse /help to see available commands."
            )
            return {"status": "command_processed", "command": "unknown"}
    
    # Handle payment approval/rejection
    # Check if there's a pending payment approval for this host
    text_lower = text.lower().strip()
    if text_lower in ["yes", "y", "approve", "confirm"]:
        # Find pending booking for this host
        host = db.query(Host).filter(Host.telegram_id == user_id).first()
        if not host:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Host not found. Please set up your host profile first using /setup"
            )
            return {"status": "error", "message": "Host not found"}
        
        # Get pending bookings for this host's properties
        from database.models import Property
        properties = db.query(Property).filter(Property.host_id == host.id).all()
        property_ids = [p.id for p in properties]
        
        pending_booking = db.query(Booking).filter(
            Booking.property_id.in_(property_ids),
            Booking.payment_status == 'pending',
            Booking.booking_status == 'pending'
        ).order_by(Booking.created_at.desc()).first()
        
        if pending_booking:
            # Approve booking
            from api.utils.payment import confirm_booking
            success = await confirm_booking(db=db, booking_id=pending_booking.id)
            
            if success:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"✅ Payment approved! Booking #{pending_booking.id} has been confirmed. The guest has been notified."
                )
                return {"status": "payment_approved", "booking_id": pending_booking.id}
            else:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="❌ Error confirming booking. Please try again."
                )
                return {"status": "error", "message": "Failed to confirm booking"}
        else:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="No pending payment requests found. If you just received a payment request, please wait a moment and try again."
            )
            return {"status": "no_pending_booking"}
    
    elif text_lower in ["no", "n", "reject", "decline"]:
        # Find pending booking for this host
        host = db.query(Host).filter(Host.telegram_id == user_id).first()
        if not host:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="Host not found. Please set up your host profile first using /setup"
            )
            return {"status": "error", "message": "Host not found"}
        
        # Get pending bookings for this host's properties
        from database.models import Property
        properties = db.query(Property).filter(Property.host_id == host.id).all()
        property_ids = [p.id for p in properties]
        
        pending_booking = db.query(Booking).filter(
            Booking.property_id.in_(property_ids),
            Booking.payment_status == 'pending',
            Booking.booking_status == 'pending'
        ).order_by(Booking.created_at.desc()).first()
        
        if pending_booking:
            # Reject booking
            from api.utils.payment import reject_booking
            success = await reject_booking(
                db=db,
                booking_id=pending_booking.id,
                reason="Payment could not be verified. Please contact support if you believe this is an error."
            )
            
            if success:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"❌ Payment rejected. Booking #{pending_booking.id} has been cancelled. The guest has been notified."
                )
                return {"status": "payment_rejected", "booking_id": pending_booking.id}
            else:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="❌ Error rejecting booking. Please try again."
                )
                return {"status": "error", "message": "Failed to reject booking"}
        else:
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="No pending payment requests found. If you just received a payment request, please wait a moment and try again."
            )
            return {"status": "no_pending_booking"}
    
    # Handle conversation states (multi-step flows)
    if user_id in _conversation_states:
        state = _conversation_states[user_id]
        # This will be enhanced in Step 6.3 with full setup flows
        # For now, just acknowledge
        await send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            message="Setup flow will be fully implemented. For now, use the API endpoints to configure properties."
        )
        return {"status": "conversation_state_handled"}
    
    # Default: echo message for testing
    if text:
        response = f"Echo: {text}\n\n(Full host bot functionality coming in later steps)"
        await send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            message=response
        )
    
    return {"status": "processed", "chat_id": chat_id, "user_id": user_id}


async def send_host_message(
    chat_id: str,
    message: str,
    photo_path: Optional[str] = None
) -> bool:
    """
    Send a message to the host.
    
    Args:
        chat_id: Host chat ID
        message: Message to send
        photo_path: Optional path to photo to send
    
    Returns:
        True if sent successfully
    """
    bot_token = get_bot_token("host")
    if not bot_token:
        print("Host bot token not configured")
        return False
    
    if photo_path:
        return await send_photo(bot_token, chat_id, photo_path, caption=message)
    else:
        return await send_message(bot_token, chat_id, message)


async def send_payment_approval_request(
    db: Session,
    host_telegram_id: str,
    booking: Booking,
    screenshot_path: str,
    booking_details: Dict[str, Any]
) -> bool:
    """
    Send payment approval request to host.
    
    This will be fully implemented in Step 9.
    
    Args:
        db: Database session
        host_telegram_id: Host's Telegram ID
        booking_id: Booking ID
        screenshot_path: Path to payment screenshot
        booking_details: Booking information
    
    Returns:
        True if sent successfully
    """
    host = db.query(Host).filter(Host.telegram_id == host_telegram_id).first()
    if not host:
        return False
    
    customer_name = booking.customer_name or booking_details.get("guest_name") or f"Guest {booking.guest_telegram_id}"
    customer_bank = booking.customer_bank_name or booking_details.get("customer_bank_name") or "Not specified"
    
    # Calculate amount (handle None values)
    amount = booking_details.get("amount")
    if amount is None:
        amount = booking.final_price or booking.requested_price
    if amount is None:
        # Fallback: calculate from property base price
        amount = booking.property.base_price * booking.number_of_nights
    
    message = (
        "💰 Payment Verification Request\n\n"
        f"Booking ID: {booking.id}\n"
        f"Guest: {customer_name}\n"
        f"Property: {booking_details.get('property_name', booking.property.name)}\n"
        f"Amount: ${amount:.2f}\n"
        f"Dates: {booking_details.get('check_in')} to {booking_details.get('check_out')}\n\n"
        "📋 Customer Payment Details:\n"
        f"• Customer Name: {customer_name}\n"
        f"• Bank Sent From: {customer_bank}\n\n"
        f"⚠️ IMPORTANT: Please check your {customer_bank} account for the payment.\n\n"
        "After verifying, reply:\n"
        "✅ 'yes' if payment received\n"
        "❌ 'no' if payment not found"
    )
    
    success = await send_host_message(host.telegram_id, message, screenshot_path)
    
    if success:
        log_event(
            db=db,
            event_type=EventType.HOST_PAYMENT_APPROVAL,
            agent_name="HostBot",
            property_id=booking.property_id,
            booking_id=booking.id,
            message=f"Payment approval request sent to host {host_telegram_id}",
            metadata={
                "booking_id": booking.id,
                "host_telegram_id": host_telegram_id,
                "screenshot_path": screenshot_path,
                "guest_telegram_id": booking.guest_telegram_id,
            }
        )
    
    return success

