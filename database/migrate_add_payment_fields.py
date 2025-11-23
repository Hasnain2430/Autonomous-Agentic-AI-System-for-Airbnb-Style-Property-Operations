"""
Migration script to add payment-related fields to existing database.

This script adds:
- payment_methods column to hosts table
- customer_name, customer_bank_name, customer_payment_details columns to bookings table
"""

import os
import sys
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Get database path from environment or use default
DATABASE_PATH = os.getenv("DATABASE_PATH", "./database/properties.db")

def migrate_database():
    """Add missing columns to existing database."""
    print(f"Migrating database at: {DATABASE_PATH}")
    
    if not os.path.exists(DATABASE_PATH):
        print("Database file not found. Run init_db() first.")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(hosts)")
        host_columns = [row[1] for row in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(bookings)")
        booking_columns = [row[1] for row in cursor.fetchall()]
        
        # Add payment_methods to hosts if missing
        if 'payment_methods' not in host_columns:
            print("Adding payment_methods column to hosts table...")
            cursor.execute("ALTER TABLE hosts ADD COLUMN payment_methods TEXT")
            print("✅ Added payment_methods column")
        else:
            print("✅ payment_methods column already exists")
        
        # Add customer fields to bookings if missing
        if 'customer_name' not in booking_columns:
            print("Adding customer_name column to bookings table...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN customer_name TEXT")
            print("✅ Added customer_name column")
        else:
            print("✅ customer_name column already exists")
        
        if 'customer_bank_name' not in booking_columns:
            print("Adding customer_bank_name column to bookings table...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN customer_bank_name TEXT")
            print("✅ Added customer_bank_name column")
        else:
            print("✅ customer_bank_name column already exists")
        
        if 'customer_payment_details' not in booking_columns:
            print("Adding customer_payment_details column to bookings table...")
            cursor.execute("ALTER TABLE bookings ADD COLUMN customer_payment_details TEXT")
            print("✅ Added customer_payment_details column")
        else:
            print("✅ customer_payment_details column already exists")
        
        conn.commit()
        print("\n✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

