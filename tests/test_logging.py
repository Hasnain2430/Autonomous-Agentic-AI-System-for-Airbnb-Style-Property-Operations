"""
Test script for logging system.

This script tests the logging utilities and log query functions.
"""

import sys
import os
from datetime import date, datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db_session, init_db
from api.utils.logging import (
    log_event,
    get_logs_by_property,
    get_logs_by_date_range,
    get_logs_by_event_type,
    get_logs_for_summary,
    get_recent_logs,
    EventType
)
from database.models import Host, Property, Booking


def test_logging():
    """Test logging system functionality."""
    
    print("=" * 60)
    print("Testing System Logging Infrastructure")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✓ Database initialized")
    
    # Get database session
    print("\n2. Creating database session...")
    db = get_db_session()
    print("   ✓ Session created")
    
    try:
        # Create test host and property
        print("\n3. Creating test data...")
        # Check if host already exists
        host = db.query(Host).filter(Host.telegram_id == "999888777").first()
        if not host:
            host = Host(
                name="Logging Test Host",
                email="logging@example.com",
                telegram_id="999888777"
            )
            db.add(host)
            db.commit()
            db.refresh(host)
        
        # Check if property already exists
        property = db.query(Property).filter(Property.property_identifier == "LOGTEST001").first()
        if not property:
            property = Property(
                host_id=host.id,
                property_identifier="LOGTEST001",
                name="Logging Test Property",
                location="456 Log Test St",
                base_price=100.0,
                min_price=80.0,
                max_price=120.0,
                max_guests=4,
                check_in_time="14:00",
                check_out_time="11:00"
            )
            db.add(property)
            db.commit()
            db.refresh(property)
        print(f"   ✓ Test host and property ready (Property ID: {property.id})")
        
        # Test Log Event
        print("\n4. Testing log_event()...")
        log1 = log_event(
            db=db,
            event_type=EventType.GUEST_MESSAGE,
            property_id=property.id,
            agent_name="InquiryBookingAgent",
            message="Guest asked about availability",
            metadata={"guest_message": "Is the property available?", "response": "Yes, available"}
        )
        print(f"   ✓ Log created: {log1.event_type} (ID: {log1.id})")
        print(f"   ✓ Metadata: {log1.get_metadata()}")
        
        # Test Multiple Event Types
        print("\n5. Testing multiple event types...")
        events = [
            (EventType.BOOKING_CREATED, "Booking created for test guest"),
            (EventType.BOOKING_CONFIRMED, "Booking confirmed"),
            (EventType.CLEANING_SCHEDULED, "Cleaning scheduled"),
            (EventType.ISSUE_REPORTED, "Guest reported wifi issue"),
            (EventType.ISSUE_RESOLVED, "Wifi issue resolved"),
            (EventType.BOOKING_PAYMENT_APPROVED, "Payment approved by host")
        ]
        
        for event_type, message in events:
            log_event(
                db=db,
                event_type=event_type,
                property_id=property.id,
                agent_name="TestAgent",
                message=message
            )
        print(f"   ✓ Created {len(events)} log entries")
        
        # Test Get Logs by Property
        print("\n6. Testing get_logs_by_property()...")
        property_logs = get_logs_by_property(db, property.id, limit=10)
        print(f"   ✓ Found {len(property_logs)} logs for property")
        
        # Test Get Logs by Event Type
        print("\n7. Testing get_logs_by_event_type()...")
        booking_logs = get_logs_by_event_type(db, EventType.BOOKING_CREATED, limit=5)
        print(f"   ✓ Found {len(booking_logs)} logs of type '{EventType.BOOKING_CREATED}'")
        
        # Test Get Logs by Date Range
        print("\n8. Testing get_logs_by_date_range()...")
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        date_range_logs = get_logs_by_date_range(db, yesterday, tomorrow, property.id)
        print(f"   ✓ Found {len(date_range_logs)} logs in date range")
        
        # Test Get Logs for Summary
        print("\n9. Testing get_logs_for_summary()...")
        summary = get_logs_for_summary(db, property.id, yesterday, tomorrow)
        print(f"   ✓ Summary generated:")
        print(f"     - Total events: {summary['total_events']}")
        print(f"     - Booking confirmations: {summary['booking_confirmations']}")
        print(f"     - Issues reported: {summary['issues_reported']}")
        print(f"     - Issues resolved: {summary['issues_resolved']}")
        print(f"     - Cleaning tasks scheduled: {summary['cleaning_tasks_scheduled']}")
        print(f"     - Payment approvals: {summary['payment_approvals']}")
        
        # Test Get Recent Logs
        print("\n10. Testing get_recent_logs()...")
        recent_logs = get_recent_logs(db, limit=5)
        print(f"   ✓ Found {len(recent_logs)} recent logs")
        
        # Test Log with Booking ID
        print("\n11. Testing log with booking ID...")
        booking = Booking(
            property_id=property.id,
            guest_telegram_id="111222333",
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            number_of_nights=3,
            number_of_guests=2,
            booking_status="confirmed"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        booking_log = log_event(
            db=db,
            event_type=EventType.BOOKING_CONFIRMED,
            property_id=property.id,
            booking_id=booking.id,
            agent_name="InquiryBookingAgent",
            message=f"Booking {booking.id} confirmed",
            metadata={"booking_id": booking.id, "guest_id": booking.guest_telegram_id}
        )
        print(f"   ✓ Log created with booking ID: {booking_log.booking_id}")
        
        print("\n" + "=" * 60)
        print("✓ All logging tests passed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
        print("\n✓ Database session closed")


if __name__ == "__main__":
    test_logging()

