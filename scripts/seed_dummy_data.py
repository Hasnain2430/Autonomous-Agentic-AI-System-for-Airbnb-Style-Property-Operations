"""
Seed database with dummy data for testing guest bot.

This script populates the database with:
- Host with payment methods
- Multiple properties
- Sample bookings (optional)
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from database.db import init_db, get_db_session
from database.models import Host, Property, Booking
from config.config_manager import ConfigManager


def seed_dummy_data(reset=False):
    """Seed database with dummy data."""
    
    if reset:
        print("🔄 Resetting database...")
        from database.db import reset_db
        reset_db()
    else:
        print("📊 Initializing database...")
        init_db()
    
    db = get_db_session()
    
    try:
        # Get host telegram ID from environment
        host_telegram_id = os.getenv("HOST_TELEGRAM_ID", "Hasnain2422")
        
        print(f"👤 Creating host (Telegram ID: {host_telegram_id})...")
        host = ConfigManager.create_host(
            db=db,
            name="Hasnain Host",
            email="hasnain@example.com",
            telegram_id=host_telegram_id,
            phone="+92-300-1234567",
            preferred_language="en"
        )
        print(f"   ✓ Host created: {host.name} (ID: {host.id})")
        
        print("💳 Adding payment methods...")
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="HBL Bank",
            account_number="PK00HBL0001234567890123",
            account_name="Hasnain Host",
            instructions="Use booking reference in transfer description"
        )
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="JazzCash Wallet",
            account_number="0300-1234567",
            account_name="Hasnain Host",
            instructions="Send screenshot after transfer"
        )
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="EasyPaisa Wallet",
            account_number="0311-7654321",
            account_name="Hasnain Host",
            instructions="Include booking dates in reference"
        )
        print("   ✓ Payment methods added")
        
        print("🏠 Adding Property #1: Lakeside Loft...")
        property1 = ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="PROP-001",
            name="Lakeside Loft",
            location="Lakeview Road 12, Islamabad",
            base_price=150.0,
            min_price=120.0,
            max_price=200.0,
            max_guests=4,
            check_in_time="15:00",
            check_out_time="11:00",
            cleaning_rules="Deep clean before each check-in, quick clean after checkout",
            check_in_template="Welcome! Self check-in via lockbox. Code: 4321. The lockbox is located next to the main entrance. Check-in time is 3:00 PM.",
            check_out_template="Thank you for staying! Please leave keys on the kitchen table. Check-out time is 11:00 AM. We hope you enjoyed your stay!"
        )
        # Add FAQs for property 1
        property1.set_faqs([
            {
                "question": "Is WiFi available?",
                "answer": "Yes, WiFi is available at Lakeside Loft. The network name is 'Lakeside_Guest' and the password is 'Welcome2025'. The WiFi password is also provided in your check-in instructions."
            },
            {
                "question": "Is parking available?",
                "answer": "Yes, free parking is available on-site. You can park in the designated guest parking area near the main entrance."
            },
            {
                "question": "What amenities are included?",
                "answer": "The property includes WiFi, parking, fully equipped kitchen, air conditioning, heating, and all basic amenities. Linens and towels are provided."
            }
        ])
        db.commit()
        print(f"   ✓ Property created: {property1.name} (ID: {property1.id})")
        
        print("🏠 Adding Property #2: Downtown Suite...")
        property2 = ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="PROP-002",
            name="Downtown Suite",
            location="Main Street 45, Lahore",
            base_price=180.0,
            min_price=140.0,
            max_price=240.0,
            max_guests=5,
            check_in_time="14:00",
            check_out_time="10:00",
            cleaning_rules="Full service cleaning after every checkout",
            check_in_template="Welcome to Downtown Suite! Front-desk check-in available. Please mention your booking ID when checking in. Check-in time is 2:00 PM.",
            check_out_template="Thank you for choosing Downtown Suite! Please return keycards to reception before 10:00 AM. Safe travels!"
        )
        # Add FAQs for property 2
        property2.set_faqs([
            {
                "question": "Is WiFi available?",
                "answer": "Yes, high-speed WiFi is available at Downtown Suite. The WiFi details will be provided at check-in at the front desk."
            },
            {
                "question": "Is parking available?",
                "answer": "Valet parking is available for an additional fee. Self-parking is also available nearby. Please contact the front desk for parking options."
            }
        ])
        db.commit()
        print(f"   ✓ Property created: {property2.name} (ID: {property2.id})")
        
        print("🏠 Adding Property #3: Mountain View Apartment...")
        property3 = ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="PROP-003",
            name="Mountain View Apartment",
            location="Hill Station Road 8, Murree",
            base_price=200.0,
            min_price=160.0,
            max_price=280.0,
            max_guests=6,
            check_in_time="16:00",
            check_out_time="12:00",
            cleaning_rules="Standard cleaning before check-in, thorough cleaning after checkout",
            check_in_template="Welcome to Mountain View! Key is in the lockbox at the gate. Code: 5678. Check-in time is 4:00 PM. Enjoy the mountain views!",
            check_out_template="Thank you for staying at Mountain View! Please leave the key in the lockbox. Check-out time is 12:00 PM. Hope to see you again!"
        )
        print(f"   ✓ Property created: {property3.name} (ID: {property3.id})")
        
        # Add some sample bookings for testing
        print("📅 Adding sample bookings...")
        
        # Past confirmed booking
        past_booking = Booking(
            property_id=property1.id,
            guest_telegram_id="GUEST_001",
            guest_name="John Doe",
            check_in_date=date.today() - timedelta(days=10),
            check_out_date=date.today() - timedelta(days=7),
            number_of_nights=3,
            number_of_guests=2,
            final_price=450.0,
            payment_status="approved",
            booking_status="confirmed",
            customer_name="John Doe",
            customer_bank_name="HBL Bank",
            confirmed_at=datetime.now() - timedelta(days=12)
        )
        db.add(past_booking)
        print(f"   ✓ Past booking added for {property1.name}")
        
        # Current active booking
        active_booking = Booking(
            property_id=property2.id,
            guest_telegram_id="GUEST_002",
            guest_name="Jane Smith",
            check_in_date=date.today() - timedelta(days=2),
            check_out_date=date.today() + timedelta(days=3),
            number_of_nights=5,
            number_of_guests=3,
            final_price=900.0,
            payment_status="approved",
            booking_status="confirmed",
            customer_name="Jane Smith",
            customer_bank_name="JazzCash",
            confirmed_at=datetime.now() - timedelta(days=5)
        )
        db.add(active_booking)
        print(f"   ✓ Active booking added for {property2.name}")
        
        # Future booking
        future_booking = Booking(
            property_id=property1.id,
            guest_telegram_id="GUEST_003",
            guest_name="Bob Johnson",
            check_in_date=date.today() + timedelta(days=15),
            check_out_date=date.today() + timedelta(days=18),
            number_of_nights=3,
            number_of_guests=2,
            final_price=450.0,
            payment_status="approved",
            booking_status="confirmed",
            customer_name="Bob Johnson",
            customer_bank_name="EasyPaisa",
            confirmed_at=datetime.now() - timedelta(days=3)
        )
        db.add(future_booking)
        print(f"   ✓ Future booking added for {property1.name}")
        
        # Pending booking (payment not yet approved)
        pending_booking = Booking(
            property_id=property3.id,
            guest_telegram_id="GUEST_004",
            guest_name="Alice Brown",
            check_in_date=date.today() + timedelta(days=20),
            check_out_date=date.today() + timedelta(days=23),
            number_of_nights=3,
            number_of_guests=4,
            requested_price=600.0,
            final_price=600.0,
            payment_status="pending",
            booking_status="pending",
            customer_name="Alice Brown",
            customer_bank_name="HBL Bank"
        )
        db.add(pending_booking)
        print(f"   ✓ Pending booking added for {property3.name}")
        
        db.commit()
        
        print("\n✅ Database seeded successfully!")
        print(f"\n📊 Summary:")
        print(f"   - Host: {host.name} (Telegram: {host.telegram_id})")
        print(f"   - Properties: 3")
        print(f"   - Bookings: 4 (1 past, 1 active, 1 future, 1 pending)")
        print(f"\n💡 The guest bot will use the first property ({property1.name}) by default.")
        print(f"   You can test inquiries and bookings with any of the properties!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with dummy data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before seeding (WARNING: deletes all existing data)"
    )
    
    args = parser.parse_args()
    
    seed_dummy_data(reset=args.reset)

