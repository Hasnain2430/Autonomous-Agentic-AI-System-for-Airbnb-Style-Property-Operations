"""
Script to create a test property for testing the agent.

Run this to set up a test property if needed.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db, init_db
from config.config_manager import ConfigManager
from database.models import Host, Property
from sqlalchemy.orm import Session

def create_test_property():
    """Create a test host and property."""
    # Initialize database
    init_db()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if host exists
        host = db.query(Host).first()
        
        if not host:
            # Create test host
            host = ConfigManager.create_host(
                db=db,
                name="Test Host",
                email="test@example.com",
                telegram_id="123456789",  # Replace with your actual Telegram ID if needed
                phone="+1234567890",
                preferred_language="en"
            )
            print(f"Created test host: {host.name} (ID: {host.id})")
        else:
            print(f"Using existing host: {host.name} (ID: {host.id})")
        
        # Check if property exists
        property_obj = db.query(Property).filter(
            Property.property_identifier == "TEST001"
        ).first()
        
        if not property_obj:
            # Create test property
            property_obj = ConfigManager.create_property(
                db=db,
                host_id=host.id,
                property_identifier="TEST001",
                name="Cozy Downtown Apartment",
                location="123 Main Street, City Center",
                base_price=100.0,
                min_price=80.0,
                max_price=120.0,
                max_guests=4,
                check_in_time="14:00",
                check_out_time="11:00",
                cleaning_rules="Clean before check-in and after check-out",
                check_in_template="Welcome! Your apartment is ready. Key is in the lockbox. Code: 1234",
                check_out_template="Thank you for staying! Please leave the key in the lockbox."
            )
            print(f"Created test property: {property_obj.name} (ID: {property_obj.id})")
        else:
            print(f"Property already exists: {property_obj.name} (ID: {property_obj.id})")
        
        db.commit()
        print("\n✅ Test property setup complete!")
        print(f"Property ID: {property_obj.id}")
        print(f"Property Name: {property_obj.name}")
        print(f"Base Price: ${property_obj.base_price}/night")
        print(f"Price Range: ${property_obj.min_price} - ${property_obj.max_price}/night")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test property: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_property()

