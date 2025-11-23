"""
Configuration Manager.

This module handles loading, saving, and validating host and property configurations.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from database.models import Host, Property
from datetime import datetime
import json
import os


class ConfigManager:
    """Manages host and property configurations."""
    
    @staticmethod
    def create_host(
        db: Session,
        name: str,
        email: str,
        telegram_id: str,
        phone: Optional[str] = None,
        preferred_language: str = "en",
        google_calendar_id: Optional[str] = None,
        google_credentials_path: Optional[str] = None
    ) -> Host:
        """
        Create or update host configuration.
        
        Args:
            db: Database session
            name: Host name
            email: Host email
            telegram_id: Host Telegram ID
            phone: Host phone number (optional)
            preferred_language: Preferred language (default: "en")
            google_calendar_id: Google Calendar ID (optional)
            google_credentials_path: Path to Google credentials file (optional)
        
        Returns:
            Host object
        """
        # Check if host already exists
        existing_host = db.query(Host).filter(Host.telegram_id == telegram_id).first()
        
        if existing_host:
            # Update existing host
            existing_host.name = name
            existing_host.email = email
            existing_host.phone = phone
            existing_host.preferred_language = preferred_language
            if google_calendar_id:
                existing_host.google_calendar_id = google_calendar_id
            if google_credentials_path:
                existing_host.google_credentials_path = google_credentials_path
            db.commit()
            db.refresh(existing_host)
            return existing_host
        else:
            # Create new host
            host = Host(
                name=name,
                email=email,
                phone=phone,
                telegram_id=telegram_id,
                preferred_language=preferred_language,
                google_calendar_id=google_calendar_id,
                google_credentials_path=google_credentials_path
            )
            db.add(host)
            db.commit()
            db.refresh(host)
            return host
    
    @staticmethod
    def get_host_by_telegram_id(db: Session, telegram_id: str) -> Optional[Host]:
        """Get host by Telegram ID."""
        return db.query(Host).filter(Host.telegram_id == telegram_id).first()
    
    @staticmethod
    def add_payment_method(
        db: Session,
        host_id: int,
        bank_name: str,
        account_number: str,
        account_name: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> bool:
        """
        Add a payment method to a host.
        
        Args:
            db: Database session
            host_id: Host ID
            bank_name: Bank/app name (e.g., "JazzCash", "SadaPay", "EasyPaisa", "HBL")
            account_number: Account number or wallet number
            account_name: Account holder name (optional)
            instructions: Additional payment instructions (optional)
        
        Returns:
            True if added successfully
        """
        host = db.query(Host).filter(Host.id == host_id).first()
        if not host:
            return False
        
        # Get existing payment methods
        payment_methods = host.get_payment_methods()
        
        # Add new payment method
        payment_methods.append({
            "bank_name": bank_name,
            "account_number": account_number,
            "account_name": account_name,
            "instructions": instructions
        })
        
        # Save back to host
        host.set_payment_methods(payment_methods)
        db.commit()
        
        return True
    
    @staticmethod
    def get_payment_methods(db: Session, host_id: int) -> List[Dict[str, str]]:
        """
        Get all payment methods for a host.
        
        Args:
            db: Database session
            host_id: Host ID
        
        Returns:
            List of payment method dictionaries
        """
        host = db.query(Host).filter(Host.id == host_id).first()
        if not host:
            return []
        
        return host.get_payment_methods()
    
    @staticmethod
    def create_property(
        db: Session,
        host_id: int,
        property_identifier: str,
        name: str,
        location: str,
        base_price: float,
        min_price: float,
        max_price: float,
        max_guests: int,
        check_in_time: str,
        check_out_time: str,
        cleaning_rules: Optional[str] = None,
        check_in_template: Optional[str] = None,
        check_out_template: Optional[str] = None,
        photo_paths: Optional[List[str]] = None,
        cleaner_telegram_id: Optional[str] = None,
        cleaner_name: Optional[str] = None
    ) -> Property:
        """
        Create a new property.
        
        Args:
            db: Database session
            host_id: Host ID
            property_identifier: Unique property identifier
            name: Property name
            location: Property location
            base_price: Base nightly price
            min_price: Minimum acceptable price
            max_price: Maximum acceptable price
            max_guests: Maximum number of guests
            check_in_time: Check-in time (e.g., "14:00")
            check_out_time: Check-out time (e.g., "11:00")
            cleaning_rules: Cleaning rules text
            check_in_template: Check-in instruction template
            check_out_template: Check-out instruction template
            photo_paths: List of photo file paths
            cleaner_telegram_id: Cleaner's Telegram ID
            cleaner_name: Cleaner's name
        
        Returns:
            Property object
        """
        # Check if property identifier already exists
        existing = db.query(Property).filter(
            Property.property_identifier == property_identifier
        ).first()
        
        if existing:
            raise ValueError(f"Property with identifier '{property_identifier}' already exists")
        
        # Validate host exists
        host = db.query(Host).filter(Host.id == host_id).first()
        if not host:
            raise ValueError(f"Host with ID {host_id} not found")
        
        # Validate price range
        if min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price")
        if base_price < min_price or base_price > max_price:
            raise ValueError("base_price must be between min_price and max_price")
        
        # Create property
        property = Property(
            host_id=host_id,
            property_identifier=property_identifier,
            name=name,
            location=location,
            base_price=base_price,
            min_price=min_price,
            max_price=max_price,
            max_guests=max_guests,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            cleaning_rules=cleaning_rules,
            check_in_template=check_in_template,
            check_out_template=check_out_template,
            cleaner_telegram_id=cleaner_telegram_id,
            cleaner_name=cleaner_name
        )
        
        # Set photo paths if provided
        if photo_paths:
            property.set_photo_paths(photo_paths)
        
        db.add(property)
        db.commit()
        db.refresh(property)
        return property
    
    @staticmethod
    def update_property(
        db: Session,
        property_id: int,
        **updates
    ) -> Optional[Property]:
        """
        Update property configuration.
        
        Args:
            db: Database session
            property_id: Property ID to update
            **updates: Fields to update (e.g., name="New Name", base_price=120.0)
        
        Returns:
            Updated Property object, or None if not found
        """
        property = db.query(Property).filter(Property.id == property_id).first()
        if not property:
            return None
        
        # Handle photo_paths specially
        if 'photo_paths' in updates:
            property.set_photo_paths(updates.pop('photo_paths'))
        
        # Update other fields
        for key, value in updates.items():
            if hasattr(property, key) and value is not None:
                setattr(property, key, value)
        
        db.commit()
        db.refresh(property)
        return property
    
    @staticmethod
    def add_property_photos(
        db: Session,
        property_id: int,
        photo_paths: List[str]
    ) -> Optional[Property]:
        """
        Add photos to an existing property.
        
        Args:
            db: Database session
            property_id: Property ID
            photo_paths: List of new photo file paths to add
        
        Returns:
            Updated Property object, or None if not found
        """
        property = db.query(Property).filter(Property.id == property_id).first()
        if not property:
            return None
        
        # Get existing photos
        existing_photos = property.get_photo_paths()
        
        # Add new photos
        all_photos = existing_photos + photo_paths
        
        # Update property
        property.set_photo_paths(all_photos)
        db.commit()
        db.refresh(property)
        return property
    
    @staticmethod
    def validate_property_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate property configuration data.
        
        Args:
            data: Dictionary with property data
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = [
            'property_identifier', 'name', 'location', 'base_price',
            'min_price', 'max_price', 'max_guests', 'check_in_time', 'check_out_time'
        ]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate price range
        if data['min_price'] > data['max_price']:
            return False, "min_price cannot be greater than max_price"
        
        if data['base_price'] < data['min_price'] or data['base_price'] > data['max_price']:
            return False, "base_price must be between min_price and max_price"
        
        # Validate max_guests
        if data['max_guests'] < 1:
            return False, "max_guests must be at least 1"
        
        # Validate time format (basic check)
        try:
            # Check if time is in HH:MM format
            check_in = data['check_in_time'].split(':')
            check_out = data['check_out_time'].split(':')
            if len(check_in) != 2 or len(check_out) != 2:
                return False, "Time format should be HH:MM (e.g., 14:00)"
            int(check_in[0])
            int(check_in[1])
            int(check_out[0])
            int(check_out[1])
        except (ValueError, AttributeError):
            return False, "Invalid time format. Use HH:MM (e.g., 14:00)"
        
        return True, None

