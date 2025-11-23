"""
Pydantic schemas for request/response models.

This file contains all the data validation models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime


# Agent Request/Response Models

class AgentProcessRequest(BaseModel):
    """Request model for agent processing."""
    message: str = Field(..., description="Message or input for the agent")
    guest_telegram_id: Optional[str] = Field(None, description="Guest Telegram ID")
    property_id: Optional[int] = Field(None, description="Property ID")
    booking_id: Optional[int] = Field(None, description="Booking ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AgentResponse(BaseModel):
    """Response model from agents."""
    response: str = Field(..., description="Agent's response message")
    action: str = Field(..., description="Action to take: 'reply', 'request_payment', 'escalate', etc.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Property Models

class PropertyCreate(BaseModel):
    """Model for creating a property."""
    host_id: int
    property_identifier: str
    name: str
    location: str
    base_price: float
    min_price: float
    max_price: float
    max_guests: int
    check_in_time: str
    check_out_time: str
    cleaning_rules: Optional[str] = None
    check_in_template: Optional[str] = None
    check_out_template: Optional[str] = None
    cleaner_telegram_id: Optional[str] = None
    cleaner_name: Optional[str] = None


class PropertyResponse(BaseModel):
    """Model for property response."""
    id: int
    property_identifier: str
    name: str
    location: str
    base_price: float
    min_price: float
    max_price: float
    max_guests: int
    photo_paths: List[str]
    
    class Config:
        from_attributes = True


# Booking Models

class BookingCreate(BaseModel):
    """Model for creating a booking."""
    property_id: int
    guest_telegram_id: str
    guest_name: Optional[str] = None
    check_in_date: date
    check_out_date: date
    number_of_guests: int
    requested_price: Optional[float] = None


class BookingResponse(BaseModel):
    """Model for booking response."""
    id: int
    property_id: int
    guest_name: Optional[str]
    check_in_date: date
    check_out_date: date
    number_of_nights: int
    final_price: Optional[float]
    booking_status: str
    payment_status: str
    
    class Config:
        from_attributes = True


# Host Models

class HostCreate(BaseModel):
    """Model for creating a host."""
    name: str
    email: str
    phone: Optional[str] = None
    telegram_id: str
    preferred_language: str = "en"
    google_calendar_id: Optional[str] = None
    google_credentials_path: Optional[str] = None


class HostResponse(BaseModel):
    """Model for host response."""
    id: int
    name: str
    email: str
    telegram_id: str
    
    class Config:
        from_attributes = True


class PaymentMethodCreate(BaseModel):
    bank_name: str
    account_number: str
    account_name: Optional[str] = None
    instructions: Optional[str] = None
