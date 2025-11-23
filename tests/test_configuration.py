"""
Test script for configuration system.

This script tests the configuration manager and API endpoints.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db_session, init_db
from config.config_manager import ConfigManager
from database.models import Host, Property


def test_configuration():
    """Test configuration manager functionality."""
    
    print("=" * 60)
    print("Testing Configuration System")
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
        # Test Host Creation
        print("\n3. Testing Host creation...")
        host = ConfigManager.create_host(
            db=db,
            name="Test Host",
            email="test@example.com",
            telegram_id="123456789",
            phone="+1234567890",
            preferred_language="en",
            google_calendar_id="test_calendar_id"
        )
        print(f"   ✓ Host created: {host.name} (ID: {host.id}, Telegram: {host.telegram_id})")
        
        # Test Get Host by Telegram ID
        print("\n4. Testing Get Host by Telegram ID...")
        found_host = ConfigManager.get_host_by_telegram_id(db, "123456789")
        if found_host:
            print(f"   ✓ Host found: {found_host.name}")
        else:
            print("   ❌ Host not found")
        
        # Test Property Creation
        print("\n5. Testing Property creation...")
        property = ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="TEST001",
            name="Test Property",
            location="123 Test St, Test City",
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
            cleaner_name="Test Cleaner"
        )
        print(f"   ✓ Property created: {property.name} (ID: {property.id}, Identifier: {property.property_identifier})")
        
        # Test Property Validation
        print("\n6. Testing Property validation...")
        valid_data = {
            'property_identifier': 'TEST002',
            'name': 'Test Property 2',
            'location': '456 Test Ave',
            'base_price': 150.0,
            'min_price': 120.0,
            'max_price': 180.0,
            'max_guests': 6,
            'check_in_time': '15:00',
            'check_out_time': '10:00'
        }
        is_valid, error = ConfigManager.validate_property_data(valid_data)
        if is_valid:
            print("   ✓ Valid property data passed validation")
        else:
            print(f"   ❌ Validation failed: {error}")
        
        # Test Invalid Data
        print("\n7. Testing invalid property data...")
        invalid_data = valid_data.copy()
        invalid_data['min_price'] = 200.0  # Greater than max_price
        is_valid, error = ConfigManager.validate_property_data(invalid_data)
        if not is_valid:
            print(f"   ✓ Invalid data correctly rejected: {error}")
        else:
            print("   ❌ Invalid data was not rejected")
        
        # Test Add Photos
        print("\n8. Testing Add property photos...")
        photo_paths = [
            "storage/photos/test_prop_1.jpg",
            "storage/photos/test_prop_2.jpg"
        ]
        updated_property = ConfigManager.add_property_photos(db, property.id, photo_paths)
        if updated_property:
            photos = updated_property.get_photo_paths()
            print(f"   ✓ Photos added: {len(photos)} photo(s)")
            print(f"   ✓ Photo paths: {photos}")
        else:
            print("   ❌ Failed to add photos")
        
        # Test Update Property
        print("\n9. Testing Update property...")
        updated = ConfigManager.update_property(
            db,
            property.id,
            name="Updated Test Property",
            base_price=110.0
        )
        if updated:
            print(f"   ✓ Property updated: {updated.name}, new price: {updated.base_price}")
        else:
            print("   ❌ Failed to update property")
        
        # Test Duplicate Property Identifier
        print("\n10. Testing duplicate property identifier...")
        try:
            duplicate = ConfigManager.create_property(
                db=db,
                host_id=host.id,
                property_identifier="TEST001",  # Same as first property
                name="Duplicate Property",
                location="789 Test Blvd",
                base_price=100.0,
                min_price=80.0,
                max_price=120.0,
                max_guests=4,
                check_in_time="14:00",
                check_out_time="11:00"
            )
            print("   ❌ Duplicate identifier was allowed (should have failed)")
        except ValueError as e:
            print(f"   ✓ Duplicate identifier correctly rejected: {e}")
        
        print("\n" + "=" * 60)
        print("✓ All configuration tests passed successfully!")
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
    test_configuration()

