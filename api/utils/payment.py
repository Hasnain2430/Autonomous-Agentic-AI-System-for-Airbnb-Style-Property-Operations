"""
Payment verification utilities.

Handles payment screenshot processing and booking creation.
"""

import os
import aiofiles
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Booking, Property, Host, SystemLog
from api.utils.logging import log_event, EventType


async def download_telegram_photo(
    bot_token: str,
    file_id: str,
    save_path: str
) -> bool:
    """
    Download a photo from Telegram.
    
    Args:
        bot_token: Telegram bot token
        file_id: Telegram file ID
        save_path: Path to save the file
    
    Returns:
        True if downloaded successfully
    """
    try:
        from telegram import Bot
        from api.telegram.base import _get_telegram_request
        
        bot = Bot(token=bot_token, request=_get_telegram_request())
        
        # Get file info
        file_info = await bot.get_file(file_id)
        
        # Download file
        await file_info.download_to_drive(save_path)
        
        return True
    except Exception as e:
        print(f"Error downloading Telegram photo: {e}")
        return False


async def save_pending_payment_request(
    db: Session,
    guest_telegram_id: str,
    property_id: int,
    file_id: str,
    dates: Dict[str, str],
    negotiated_price: Optional[float] = None,
) -> None:
    """
    Log a pending payment screenshot that still requires customer details.
    """
    metadata = {
        "guest_telegram_id": guest_telegram_id,
        "user_id": guest_telegram_id,
        "property_id": property_id,
        "file_id": file_id,
        "dates": dates,
        "negotiated_price": negotiated_price,
        "awaiting_customer_details": True,
    }
    
    log_event(
        db=db,
        event_type=EventType.GUEST_PAYMENT_UPLOADED,
        agent_name="PaymentHandler",
        property_id=property_id,
        message=f"Payment screenshot received from {guest_telegram_id} - awaiting customer details",
        metadata=metadata,
    )


def get_pending_payment_request(
    db: Session,
    guest_telegram_id: str,
    property_id: Optional[int] = None,
) -> Tuple[Optional[SystemLog], Optional[Dict[str, Any]]]:
    """
    Retrieve the most recent pending payment request for a guest.
    """
    query = (
        db.query(SystemLog)
        .filter(SystemLog.event_type == EventType.GUEST_PAYMENT_UPLOADED)
        .order_by(SystemLog.created_at.desc())
        .limit(50)
    )
    
    for log in query.all():
        metadata = {}
        try:
            metadata = log.get_metadata()
        except Exception:
            continue
        
        if metadata.get("guest_telegram_id") != guest_telegram_id:
            continue
        if property_id and metadata.get("property_id") and metadata.get("property_id") != property_id:
            continue
        if metadata.get("awaiting_customer_details"):
            return log, metadata
    
    return None, None


async def clear_pending_payment_request(
    db: Session,
    pending_log: SystemLog
) -> None:
    """
    Mark a pending payment request as resolved.
    """
    if not pending_log:
        return
    
    try:
        metadata = pending_log.get_metadata()
        metadata["awaiting_customer_details"] = False
        pending_log.set_metadata(metadata)
        db.add(pending_log)
        db.commit()
    except Exception:
        db.rollback()


async def handle_payment_screenshot(
    db: Session,
    guest_telegram_id: str,
    file_id: str,
    property_id: int,
    booking_details: Dict[str, Any]
) -> Optional[Booking]:
    """
    Handle payment screenshot upload.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        file_id: Telegram file ID of the screenshot
        property_id: Property ID
        booking_details: Booking details (dates, price, etc.)
    
    Returns:
        Booking object if created successfully, None otherwise
    """
    try:
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return None
        
        # Create storage directory if it doesn't exist
        storage_dir = "storage/payment_screenshots"
        os.makedirs(storage_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"payment_{guest_telegram_id}_{timestamp}.jpg"
        screenshot_path = os.path.join(storage_dir, filename)
        
        # Download photo from Telegram
        from api.telegram.base import get_bot_token
        bot_token = get_bot_token("guest")
        if not bot_token:
            return None
        
        success = await download_telegram_photo(bot_token, file_id, screenshot_path)
        if not success:
            return None
        
        # Parse dates
        check_in = datetime.strptime(booking_details['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(booking_details['check_out'], '%Y-%m-%d').date()
        nights = (check_out - check_in).days
        
        # Create booking record
        booking = Booking(
            property_id=property_id,
            guest_telegram_id=guest_telegram_id,
            guest_name=booking_details.get('guest_name') or booking_details.get('customer_name'),
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_nights=nights,
            number_of_guests=booking_details.get('number_of_guests', 1),
            requested_price=booking_details.get('requested_price'),
            final_price=booking_details.get('final_price'),
            payment_status='pending',
            payment_screenshot_path=screenshot_path,
            customer_name=booking_details.get('customer_name'),
            customer_bank_name=booking_details.get('customer_bank_name'),
            booking_status='pending'
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log event
        log_event(
            db=db,
            event_type=EventType.GUEST_PAYMENT_UPLOADED,
            agent_name="PaymentHandler",
            property_id=property_id,
            booking_id=booking.id,
            message=f"Payment screenshot uploaded by guest {guest_telegram_id}",
            metadata={
                "guest_telegram_id": guest_telegram_id,
                "booking_id": booking.id,
                "screenshot_path": screenshot_path,
                "amount": booking_details.get('final_price')
            }
        )
        
        return booking
        
    except Exception as e:
        print(f"Error handling payment screenshot: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None


async def send_payment_to_host(
    db: Session,
    booking: Booking
) -> bool:
    """
    Send payment screenshot to host for approval.
    
    Args:
        db: Database session
        booking: Booking object
    
    Returns:
        True if sent successfully
    """
    try:
        from api.telegram.host_bot import send_payment_approval_request
        
        # Get property and host
        property_obj = booking.property
        if not property_obj:
            return False
        
        host = property_obj.host
        if not host or not host.telegram_id:
            return False
        
        # Prepare booking details
        booking_details = {
            "guest_name": booking.guest_name or f"Guest {booking.guest_telegram_id}",
            "property_name": property_obj.name,
            "amount": booking.final_price or booking.requested_price or 0,
            "check_in": booking.check_in_date.strftime('%Y-%m-%d'),
            "check_out": booking.check_out_date.strftime('%Y-%m-%d'),
            "nights": booking.number_of_nights,
            "guests": booking.number_of_guests,
            "customer_bank_name": booking.customer_bank_name
        }
        
        # Send to host
        success = await send_payment_approval_request(
            db=db,
            host_telegram_id=host.telegram_id,
            booking=booking,
            screenshot_path=booking.payment_screenshot_path,
            booking_details=booking_details
        )
        
        if not success:
            log_event(
                db=db,
                event_type=EventType.HOST_ESCALATION_RECEIVED,
                agent_name="HostBot",
                property_id=booking.property_id,
                booking_id=booking.id,
                message="Host notification failed - host bot may not be configured yet",
                metadata={
                    "booking_id": booking.id,
                    "host_telegram_id": host.telegram_id,
                    "reason": "host_bot_unreachable"
                }
            )
        
        return success
        
    except Exception as e:
        print(f"Error sending payment to host: {e}")
        import traceback
        traceback.print_exc()
        return False


async def confirm_booking(
    db: Session,
    booking_id: int
) -> bool:
    """
    Confirm a booking after payment approval.
    
    Args:
        db: Database session
        booking_id: Booking ID
    
    Returns:
        True if confirmed successfully
    """
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return False
        
        # Update booking status
        booking.booking_status = 'confirmed'
        booking.payment_status = 'approved'
        booking.confirmed_at = datetime.utcnow()
        
        db.commit()
        
        # Log event
        log_event(
            db=db,
            event_type=EventType.BOOKING_CONFIRMED,
            agent_name="BookingHandler",
            property_id=booking.property_id,
            booking_id=booking.id,
            message=f"Booking {booking_id} confirmed",
            metadata={
                "booking_id": booking.id,
                "guest_telegram_id": booking.guest_telegram_id,
                "confirmed_at": booking.confirmed_at.isoformat()
            }
        )
        
        # Send confirmation to guest
        from api.telegram.base import get_bot_token, send_message
        bot_token = get_bot_token("guest")
        if bot_token:
            confirmation_message = (
                f"✅ Booking Confirmed!\n\n"
                f"Your booking has been confirmed:\n"
                f"Property: {booking.property.name}\n"
                f"Check-in: {booking.check_in_date.strftime('%B %d, %Y')}\n"
                f"Check-out: {booking.check_out_date.strftime('%B %d, %Y')}\n"
                f"Total: ${booking.final_price or booking.requested_price:.2f}\n\n"
                f"Check-in instructions will be sent to you before your arrival."
            )
            await send_message(
                bot_token=bot_token,
                chat_id=booking.guest_telegram_id,
                message=confirmation_message
            )
        
        return True
        
    except Exception as e:
        print(f"Error confirming booking: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


async def reject_booking(
    db: Session,
    booking_id: int,
    reason: Optional[str] = None
) -> bool:
    """
    Reject a booking after payment rejection.
    
    Args:
        db: Database session
        booking_id: Booking ID
        reason: Optional rejection reason
    
    Returns:
        True if rejected successfully
    """
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return False
        
        # Update booking status
        booking.booking_status = 'cancelled'
        booking.payment_status = 'rejected'
        
        db.commit()
        
        # Log event
        log_event(
            db=db,
            event_type=EventType.BOOKING_CANCELLED,
            agent_name="BookingHandler",
            property_id=booking.property_id,
            booking_id=booking.id,
            message=f"Booking {booking_id} rejected",
            metadata={
                "booking_id": booking.id,
                "guest_telegram_id": booking.guest_telegram_id,
                "reason": reason
            }
        )
        
        # Send rejection to guest
        from api.telegram.base import get_bot_token, send_message
        bot_token = get_bot_token("guest")
        if bot_token:
            rejection_message = (
                f"❌ Payment Verification Failed\n\n"
                f"Unfortunately, we were unable to verify your payment.\n"
                f"{reason or 'Please contact support if you believe this is an error.'}"
            )
            await send_message(
                bot_token=bot_token,
                chat_id=booking.guest_telegram_id,
                message=rejection_message
            )
        
        return True
        
    except Exception as e:
        print(f"Error rejecting booking: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

