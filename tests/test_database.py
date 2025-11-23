"""
Test script to verify database schema and functionality.

Run this script to test the database setup.
"""

import sys
import os
from datetime import date, time, datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db, get_db_session, reset_db
from database.models import Host, Property, Booking, CleaningTask, SystemLog


def test_database():
    """Test database creation and basic operations."""
    
    print("=" * 60)
    print("Testing Database Schema and Models")
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
        # Test Host creation
        print("\n3. Testing Host model...")
        test_host = Host(
            name="Test Host",
            email="test@example.com",
            phone="+1234567890",
            telegram_id="123456789",
            preferred_language="en",
            google_calendar_id="test_calendar_id"
        )
        db.add(test_host)
        db.commit()
        db.refresh(test_host)
        print(f"   ✓ Host created: {test_host}")
        
        # Test Property creation
        print("\n4. Testing Property model...")
        test_property = Property(
            host_id=test_host.id,
            property_identifier="PROP001",
            name="Beautiful Apartment",
            location="123 Main St, City",
            base_price=100.0,
            min_price=80.0,
            max_price=120.0,
            max_guests=4,
            check_in_time="14:00",
            check_out_time="11:00",
            cleaning_rules="Clean before check-in and after check-out",
            check_in_template="Welcome! Your check-in code is 1234.",
            check_out_template="Thank you for staying! Please leave keys on table.",
            cleaner_telegram_id="987654321",
            cleaner_name="John Cleaner"
        )
        # Test photo_paths JSON handling
        test_property.set_photo_paths([
            "storage/photos/prop1_photo1.jpg",
            "storage/photos/prop1_photo2.jpg"
        ])
        db.add(test_property)
        db.commit()
        db.refresh(test_property)
        print(f"   ✓ Property created: {test_property}")
        print(f"   ✓ Photo paths: {test_property.get_photo_paths()}")
        
        # Test Booking creation
        print("\n5. Testing Booking model...")
        test_booking = Booking(
            property_id=test_property.id,
            guest_telegram_id="111222333",
            guest_name="Test Guest",
            check_in_date=date(2025, 12, 1),
            check_out_date=date(2025, 12, 5),
            number_of_nights=4,
            number_of_guests=2,
            requested_price=380.0,
            final_price=400.0,
            payment_status="pending",
            payment_screenshot_path="storage/payment_screenshots/booking_1.png",
            booking_status="pending"
        )
        db.add(test_booking)
        db.commit()
        db.refresh(test_booking)
        print(f"   ✓ Booking created: {test_booking}")
        
        # Test CleaningTask creation
        print("\n6. Testing CleaningTask model...")
        test_cleaning = CleaningTask(
            property_id=test_property.id,
            booking_id=test_booking.id,
            task_type="pre_checkin",
            scheduled_date=date(2025, 11, 30),
            scheduled_time=time(10, 0),
            status="scheduled"
        )
        db.add(test_cleaning)
        db.commit()
        db.refresh(test_cleaning)
        print(f"   ✓ CleaningTask created: {test_cleaning}")
        
        # Test SystemLog creation
        print("\n7. Testing SystemLog model...")
        test_log = SystemLog(
            event_type="guest_message",
            property_id=test_property.id,
            booking_id=test_booking.id,
            agent_name="InquiryBookingAgent",
            message="Guest asked about availability",
            metadata={"guest_message": "Is the property available?"}
        )
        test_log.set_metadata({"guest_message": "Is the property available?", "response": "Yes, available"})
        db.add(test_log)
        db.commit()
        db.refresh(test_log)
        print(f"   ✓ SystemLog created: {test_log}")
        print(f"   ✓ Metadata: {test_log.get_metadata()}")
        
        # Test queries
        print("\n8. Testing queries...")
        
        # Query all hosts
        hosts = db.query(Host).all()
        print(f"   ✓ Found {len(hosts)} host(s)")
        
        # Query properties with host relationship
        properties = db.query(Property).all()
        print(f"   ✓ Found {len(properties)} property/properties")
        if properties:
            prop = properties[0]
            print(f"   ✓ Property host: {prop.host.name}")
        
        # Query bookings
        bookings = db.query(Booking).all()
        print(f"   ✓ Found {len(bookings)} booking(s)")
        
        # Query cleaning tasks
        cleaning_tasks = db.query(CleaningTask).all()
        print(f"   ✓ Found {len(cleaning_tasks)} cleaning task(s)")
        
        # Query logs
        logs = db.query(SystemLog).all()
        print(f"   ✓ Found {len(logs)} log entry/entries")
        
        print("\n" + "=" * 60)
        print("✓ All database tests passed successfully!")
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
    test_database()

