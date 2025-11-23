"""
Reset the SQLite database and seed it with a single host plus two properties.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import reset_db, get_db_session
from config.config_manager import ConfigManager

def main():
    print("🔄 Resetting database...")
    reset_db()

    db = get_db_session()
    try:
        print("👤 Creating host...")
        host = ConfigManager.create_host(
            db=db,
            name="Hasnain Host",
            email="host@example.com",
            telegram_id="HOST_TELEGRAM_ID_PLACEHOLDER",
            phone="+1234567890",
            preferred_language="en"
        )

        print("🏦 Adding payment methods...")
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="National Bank Transfer",
            account_number="PK00-0000-0000-0000",
            account_name="Hasnain Host",
            instructions="Use reference LAKESIDE"
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

        print("🏠 Adding Property #1...")
        ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="PROP-001",
            name="Lakeside Loft",
            location="Lakeview Road 12, City",
            base_price=150.0,
            min_price=110.0,
            max_price=220.0,
            max_guests=4,
            check_in_time="15:00",
            check_out_time="11:00",
            cleaning_rules="Clean before each check-in",
            check_in_template="Self check-in via lockbox code 4321.",
            check_out_template="Please leave keys on the table."
        )

        print("🏠 Adding Property #2...")
        ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="PROP-002",
            name="Downtown Suite",
            location="Main Street 45, City",
            base_price=180.0,
            min_price=130.0,
            max_price=260.0,
            max_guests=5,
            check_in_time="14:00",
            check_out_time="10:00",
            cleaning_rules="Deep clean after every checkout",
            check_in_template="Front-desk check-in, mention booking ID.",
            check_out_template="Return keycards to reception."
        )

        print("✅ Database seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

