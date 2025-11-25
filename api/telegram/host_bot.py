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
                message="👋 Welcome! I'm your property management assistant.\n\n"
                        "I can help you:\n"
                        "• Set up your host profile\n"
                        "• Add and manage properties\n"
                        "• Approve payment requests\n\n"
                        "Use /help to see all available commands."
            )
            return {"status": "command_processed", "command": "start"}
        
        elif command == "cancel":
            if user_id in _conversation_states:
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="✅ Setup cancelled. You can start again anytime with /setup or /add_property"
                )
            else:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="No active setup to cancel. Use /help to see available commands."
                )
            return {"status": "command_processed", "command": "cancel"}
        
        elif command == "setup":
            # Check if already in a flow
            if user_id in _conversation_states:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="⚠️ You're already in a setup flow. Use /cancel to exit first."
                )
                return {"status": "command_processed", "command": "setup"}
            
            # Start host setup flow
            _conversation_states[user_id] = {"step": "setup_name", "data": {}}
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="👤 Let's set up your host profile!\n\n"
                        "Please send me your name:\n"
                        "(Use /cancel anytime to exit)"
            )
            return {"status": "command_processed", "command": "setup"}
        
        elif command == "add_property":
            # Check if already in a flow
            if user_id in _conversation_states:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="⚠️ You're already in a setup flow. Use /cancel to exit first."
                )
                return {"status": "command_processed", "command": "add_property"}
            
            # Ensure host exists first
            host = _ensure_host_record(db, user_id)
            if not host.name or host.name == "Host":
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="⚠️ Please set up your host profile first using /setup"
                )
                return {"status": "command_processed", "command": "add_property"}
            
            # Start property setup flow
            _conversation_states[user_id] = {"step": "property_identifier", "data": {}}
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="🏠 Let's add a new property!\n\n"
                        "Please send me a unique property identifier (e.g., PROP001):\n"
                        "(Use /cancel anytime to exit)"
            )
            return {"status": "command_processed", "command": "add_property"}
        
        elif command == "help":
            help_text = (
                "🤖 Host Bot Commands:\n\n"
                "📋 Setup & Configuration:\n"
                "  /setup - Set up your host profile (name, email, phone)\n"
                "  /add_property - Add a new property step-by-step\n"
                "  /cancel - Cancel current setup flow\n"
                "  /help - Show this help message\n\n"
                "💰 Payment Management:\n"
                "  When you receive a payment request, reply:\n"
                "  • 'yes' or 'approve' - Approve payment\n"
                "  • 'no' or 'reject' - Reject payment\n\n"
                "💡 Tips:\n"
                "  • Use /setup first to configure your profile\n"
                "  • Then use /add_property to add properties\n"
                "  • You can add multiple properties\n"
                "  • Payment approvals are handled automatically"
            )
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=help_text
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
    if text_lower in ["yes", "y", "approve", "confirm", "verified", "verify"]:
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
    
    # Handle cancel command in conversation flow
    if text_lower in ["/cancel", "cancel"] and user_id in _conversation_states:
        _conversation_states.pop(user_id, None)
        await send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            message="✅ Setup cancelled. You can start again anytime with /setup or /add_property"
        )
        return {"status": "cancelled"}
    
    # Handle conversation states (multi-step flows)
    if user_id in _conversation_states:
        state = _conversation_states[user_id]
        step = state.get("step")
        data = state.get("data", {})
        
        # Handle host setup flow
        if step == "setup_name":
            data["name"] = text
            state["step"] = "setup_email"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Great! Name saved: {text}\n\nNow please send me your email address:"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "setup_email":
            data["email"] = text
            state["step"] = "setup_phone"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Email saved: {text}\n\nNow please send me your phone number (optional - send 'skip' to skip):"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "setup_phone":
            phone = None if text.lower() == "skip" else text
            data["phone"] = phone
            state["step"] = "setup_bank_name"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Phone saved: {phone or 'Not provided'}\n\n"
                        f"Now please send me your bank name (e.g., HBL Bank, JazzCash, EasyPaisa, SadaPay):"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "setup_bank_name":
            data["bank_name"] = text
            state["step"] = "setup_bank_account"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Bank name saved: {text}\n\n"
                        f"Now please send me your bank account number or wallet number:"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "setup_bank_account":
            data["bank_account"] = text
            
            # Save host configuration
            try:
                host = ConfigManager.create_host(
                    db=db,
                    name=data["name"],
                    email=data["email"],
                    telegram_id=user_id,
                    phone=data.get("phone"),
                    preferred_language="en"
                )
                
                # Add payment method
                ConfigManager.add_payment_method(
                    db=db,
                    host_id=host.id,
                    bank_name=data["bank_name"],
                    account_number=data["bank_account"],
                    account_name=data["name"],  # Use host name as account name
                    instructions="Please include booking reference in transfer description"
                )
                
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"✅ Host profile setup complete!\n\n"
                            f"Name: {host.name}\n"
                            f"Email: {host.email}\n"
                            f"Phone: {host.phone or 'Not provided'}\n"
                            f"Bank: {data['bank_name']}\n"
                            f"Account: {data['bank_account']}\n\n"
                            f"You can now add properties using /add_property"
                )
                log_event(
                    db=db,
                    event_type=EventType.HOST_ESCALATION_RECEIVED,
                    agent_name="HostBot",
                    message=f"Host profile setup completed by {user_id}",
                    metadata={"host_id": host.id, "user_id": user_id}
                )
                return {"status": "setup_complete", "host_id": host.id}
            except Exception as e:
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"❌ Error saving host profile: {str(e)}\n\nPlease try /setup again."
                )
                return {"status": "error", "message": str(e)}
        
        # Handle property setup flow
        elif step == "property_identifier":
            data["property_identifier"] = text.strip().upper()
            state["step"] = "property_name"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Property identifier saved: {text}\n\nNow please send me the property name:"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "property_name":
            data["name"] = text
            state["step"] = "property_location"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Property name saved: {text}\n\nNow please send me the property location (address):"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "property_location":
            data["location"] = text
            state["step"] = "property_base_price"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Location saved: {text}\n\nNow please send me the base price per night (e.g., 150):"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "property_base_price":
            try:
                base_price = float(text)
                data["base_price"] = base_price
                # Set min and max to same as base (fixed pricing)
                data["min_price"] = base_price
                data["max_price"] = base_price
                state["step"] = "property_max_guests"
                state["data"] = data
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"Base price saved: PKR {base_price:,.2f}/night\n\n"
                            f"Note: Prices are fixed (no negotiation).\n\n"
                            f"Now please send me the maximum number of guests (e.g., 4):"
                )
                return {"status": "conversation_state_handled"}
            except ValueError:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="❌ Invalid price. Please send a number (e.g., 150):"
                )
                return {"status": "conversation_state_handled"}
        
        elif step == "property_max_guests":
            try:
                max_guests = int(text)
                data["max_guests"] = max_guests
                state["step"] = "property_check_in_time"
                state["data"] = data
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"Max guests saved: {max_guests}\n\nNow please send me the check-in time (format: HH:MM, e.g., 14:00):"
                )
                return {"status": "conversation_state_handled"}
            except ValueError:
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message="❌ Invalid number. Please send a whole number (e.g., 4):"
                )
                return {"status": "conversation_state_handled"}
        
        elif step == "property_check_in_time":
            data["check_in_time"] = text
            state["step"] = "property_check_out_time"
            state["data"] = data
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message=f"Check-in time saved: {text}\n\nNow please send me the check-out time (format: HH:MM, e.g., 11:00):"
            )
            return {"status": "conversation_state_handled"}
        
        elif step == "property_check_out_time":
            data["check_out_time"] = text
            state["step"] = "property_finish"
            state["data"] = data
            
            # Get host
            host = _ensure_host_record(db, user_id)
            
            # Create property
            try:
                property = ConfigManager.create_property(
                    db=db,
                    host_id=host.id,
                    property_identifier=data["property_identifier"],
                    name=data["name"],
                    location=data["location"],
                    base_price=data["base_price"],
                    min_price=data["min_price"],
                    max_price=data["max_price"],
                    max_guests=data["max_guests"],
                    check_in_time=data["check_in_time"],
                    check_out_time=data["check_out_time"]
                )
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"✅ Property added successfully!\n\n"
                            f"Property ID: {property.id}\n"
                            f"Identifier: {property.property_identifier}\n"
                            f"Name: {property.name}\n"
                            f"Location: {property.location}\n"
                            f"Base Price: PKR {property.base_price:,.2f}/night\n"
                            f"Max Guests: {property.max_guests}\n"
                            f"Check-in: {property.check_in_time}\n"
                            f"Check-out: {property.check_out_time}\n\n"
                            f"You can add more properties using /add_property"
                )
                log_event(
                    db=db,
                    event_type=EventType.HOST_ESCALATION_RECEIVED,
                    agent_name="HostBot",
                    property_id=property.id,
                    message=f"Property added via host bot by {user_id}",
                    metadata={"property_id": property.id, "user_id": user_id, "property_identifier": property.property_identifier}
                )
                return {"status": "property_added", "property_id": property.id}
            except ValueError as e:
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"❌ Error: {str(e)}\n\nPlease try /add_property again."
                )
                return {"status": "error", "message": str(e)}
            except Exception as e:
                _conversation_states.pop(user_id, None)
                await send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=f"❌ Error saving property: {str(e)}\n\nPlease try /add_property again."
                )
                return {"status": "error", "message": str(e)}
        
        else:
            # Unknown step, clear state
            _conversation_states.pop(user_id, None)
            await send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                message="❌ Unknown step. Please start over with /setup or /add_property"
            )
            return {"status": "error", "message": "Unknown step"}
    
    # Default: show help if message doesn't match any flow
    if text:
        await send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            message="I didn't understand that. Use /help to see available commands.\n\n"
                    "Or start a setup flow:\n"
                    "  /setup - Set up your host profile\n"
                    "  /add_property - Add a new property"
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
        f"Amount: PKR {amount:,.2f}\n"
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

