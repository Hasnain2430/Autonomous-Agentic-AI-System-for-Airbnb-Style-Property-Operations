"""
Booking management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from database.db import get_db
from database.models import Booking, Property

router = APIRouter()


@router.get("/bookings")
async def list_bookings(
    property_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all bookings, optionally filtered by property or status."""
    query = db.query(Booking)
    
    if property_id:
        query = query.filter(Booking.property_id == property_id)
    if status:
        query = query.filter(Booking.booking_status == status)
    
    bookings = query.all()
    return {
        "count": len(bookings),
        "bookings": [
            {
                "id": b.id,
                "property_id": b.property_id,
                "guest_name": b.guest_name,
                "check_in_date": str(b.check_in_date),
                "check_out_date": str(b.check_out_date),
                "number_of_nights": b.number_of_nights,
                "final_price": b.final_price,
                "booking_status": b.booking_status,
                "payment_status": b.payment_status
            }
            for b in bookings
        ]
    }


@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get booking details by ID."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {
        "id": booking.id,
        "property_id": booking.property_id,
        "guest_telegram_id": booking.guest_telegram_id,
        "guest_name": booking.guest_name,
        "check_in_date": str(booking.check_in_date),
        "check_out_date": str(booking.check_out_date),
        "number_of_nights": booking.number_of_nights,
        "number_of_guests": booking.number_of_guests,
        "requested_price": booking.requested_price,
        "final_price": booking.final_price,
        "payment_status": booking.payment_status,
        "payment_screenshot_path": booking.payment_screenshot_path,
        "booking_status": booking.booking_status,
        "calendar_event_id": booking.calendar_event_id,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
        "confirmed_at": booking.confirmed_at.isoformat() if booking.confirmed_at else None
    }

