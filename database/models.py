"""
Database models for the Airbnb Property Operations Manager.

This module defines all SQLAlchemy models for the database tables.
"""

from sqlalchemy import Column, Integer, String, Float, Date, Time, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()


class Host(Base):
    """Host model - stores host information."""
    
    __tablename__ = "hosts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    preferred_language = Column(String, default="en")
    google_calendar_id = Column(String, nullable=True)
    google_credentials_path = Column(String, nullable=True)
    payment_methods = Column(Text, nullable=True)  # JSON array of payment methods
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    properties = relationship("Property", back_populates="host", cascade="all, delete-orphan")
    
    def get_payment_methods(self):
        """Parse payment_methods JSON string to Python list."""
        if self.payment_methods:
            try:
                return json.loads(self.payment_methods)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_payment_methods(self, methods_list):
        """Convert Python list to JSON string for payment_methods."""
        self.payment_methods = json.dumps(methods_list) if methods_list else None
    
    def __repr__(self):
        return f"<Host(id={self.id}, name='{self.name}', telegram_id='{self.telegram_id}')>"


class Property(Base):
    """Property model - stores property information."""
    
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id"), nullable=False)
    property_identifier = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    max_guests = Column(Integer, nullable=False)
    check_in_time = Column(String, nullable=False)  # e.g., "14:00"
    check_out_time = Column(String, nullable=False)  # e.g., "11:00"
    cleaning_rules = Column(Text, nullable=True)
    check_in_template = Column(Text, nullable=True)
    check_out_template = Column(Text, nullable=True)
    faqs = Column(Text, nullable=True)  # JSON array of FAQ questions and answers
    photo_paths = Column(Text, nullable=True)  # JSON array of file paths
    cleaner_telegram_id = Column(String, nullable=True)
    cleaner_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    host = relationship("Host", back_populates="properties")
    bookings = relationship("Booking", back_populates="property", cascade="all, delete-orphan")
    cleaning_tasks = relationship("CleaningTask", back_populates="property", cascade="all, delete-orphan")
    logs = relationship("SystemLog", back_populates="property")
    
    def get_photo_paths(self):
        """Parse photo_paths JSON string to Python list."""
        if self.photo_paths:
            try:
                return json.loads(self.photo_paths)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_photo_paths(self, paths_list):
        """Convert Python list to JSON string for photo_paths."""
        self.photo_paths = json.dumps(paths_list) if paths_list else None
    
    def get_faqs(self):
        """Parse FAQs JSON string to Python list."""
        if self.faqs:
            try:
                return json.loads(self.faqs)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_faqs(self, faqs_list):
        """Convert Python list to JSON string for FAQs."""
        self.faqs = json.dumps(faqs_list) if faqs_list else None
    
    def __repr__(self):
        return f"<Property(id={self.id}, identifier='{self.property_identifier}', name='{self.name}')>"


class Booking(Base):
    """Booking model - stores booking information."""
    
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    guest_telegram_id = Column(String, nullable=False, index=True)
    guest_name = Column(String, nullable=True)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    number_of_nights = Column(Integer, nullable=False)
    number_of_guests = Column(Integer, nullable=False)
    requested_price = Column(Float, nullable=True)
    final_price = Column(Float, nullable=True)
    payment_status = Column(String, default="pending")  # 'pending', 'approved', 'rejected'
    payment_screenshot_path = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)  # Customer's full name
    customer_bank_name = Column(String, nullable=True)  # Bank name customer sent payment from
    customer_payment_details = Column(Text, nullable=True)  # JSON for additional customer details
    booking_status = Column(String, default="pending")  # 'pending', 'confirmed', 'cancelled'
    calendar_event_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    
    def get_customer_payment_details(self):
        """Parse customer_payment_details JSON string to Python dict."""
        if self.customer_payment_details:
            try:
                return json.loads(self.customer_payment_details)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_customer_payment_details(self, details_dict):
        """Convert Python dict to JSON string for customer_payment_details."""
        self.customer_payment_details = json.dumps(details_dict) if details_dict else None
    
    # Relationships
    property = relationship("Property", back_populates="bookings")
    cleaning_tasks = relationship("CleaningTask", back_populates="booking")
    logs = relationship("SystemLog", back_populates="booking")
    
    def __repr__(self):
        return f"<Booking(id={self.id}, property_id={self.property_id}, status='{self.booking_status}')>"


class CleaningTask(Base):
    """CleaningTask model - stores cleaning task information."""
    
    __tablename__ = "cleaning_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    task_type = Column(String, nullable=False)  # 'pre_checkin', 'post_checkout', 'during_stay'
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time, nullable=True)
    status = Column(String, default="scheduled")  # 'scheduled', 'in_progress', 'completed', 'cancelled'
    cleaner_notified_at = Column(DateTime, nullable=True)
    cleaner_confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    property = relationship("Property", back_populates="cleaning_tasks")
    booking = relationship("Booking", back_populates="cleaning_tasks")
    
    def __repr__(self):
        return f"<CleaningTask(id={self.id}, property_id={self.property_id}, type='{self.task_type}', status='{self.status}')>"


class SystemLog(Base):
    """SystemLog model - stores system event logs."""
    
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # 'guest_message', 'agent_decision', etc.
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    agent_name = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    event_metadata = Column(Text, nullable=True)  # JSON string (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    property = relationship("Property", back_populates="logs")
    booking = relationship("Booking", back_populates="logs")
    
    def get_metadata(self):
        """Parse event_metadata JSON string to Python dict."""
        if self.event_metadata:
            try:
                return json.loads(self.event_metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Convert Python dict to JSON string for event_metadata."""
        self.event_metadata = json.dumps(metadata_dict) if metadata_dict else None
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, event_type='{self.event_type}', created_at='{self.created_at}')>"

