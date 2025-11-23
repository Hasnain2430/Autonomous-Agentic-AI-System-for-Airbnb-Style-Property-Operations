"""
Property management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database.db import get_db
from database.models import Property, Host
from config.config_manager import ConfigManager
from api.models.schemas import PropertyCreate, HostCreate, PropertyResponse, HostResponse, PaymentMethodCreate

router = APIRouter()


@router.get("/properties")
async def list_properties(
    host_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all properties, optionally filtered by host."""
    query = db.query(Property)
    
    if host_id:
        query = query.filter(Property.host_id == host_id)
    
    properties = query.all()
    return {
        "count": len(properties),
        "properties": [
            {
                "id": p.id,
                "property_identifier": p.property_identifier,
                "name": p.name,
                "location": p.location,
                "base_price": p.base_price,
                "max_guests": p.max_guests,
                "host_id": p.host_id
            }
            for p in properties
        ]
    }


@router.get("/properties/{property_id}")
async def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get property details by ID."""
    property = db.query(Property).filter(Property.id == property_id).first()
    
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return {
        "id": property.id,
        "host_id": property.host_id,
        "property_identifier": property.property_identifier,
        "name": property.name,
        "location": property.location,
        "base_price": property.base_price,
        "min_price": property.min_price,
        "max_price": property.max_price,
        "max_guests": property.max_guests,
        "check_in_time": property.check_in_time,
        "check_out_time": property.check_out_time,
        "cleaning_rules": property.cleaning_rules,
        "check_in_template": property.check_in_template,
        "check_out_template": property.check_out_template,
        "photo_paths": property.get_photo_paths(),
        "cleaner_telegram_id": property.cleaner_telegram_id,
        "cleaner_name": property.cleaner_name,
        "created_at": property.created_at.isoformat() if property.created_at else None
    }


@router.post("/host", response_model=HostResponse)
async def create_host(host_data: HostCreate, db: Session = Depends(get_db)):
    """Create or update host configuration."""
    try:
        host = ConfigManager.create_host(
            db=db,
            name=host_data.name,
            email=host_data.email,
            telegram_id=host_data.telegram_id,
            phone=host_data.phone,
            preferred_language=host_data.preferred_language,
            google_calendar_id=host_data.google_calendar_id,
            google_credentials_path=host_data.google_credentials_path
        )
        return HostResponse(
            id=host.id,
            name=host.name,
            email=host.email,
            telegram_id=host.telegram_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/host")
async def get_host(host_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get host configuration."""
    if host_id:
        host = db.query(Host).filter(Host.id == host_id).first()
    else:
        # Get first host if no ID provided (for single-host setup)
        host = db.query(Host).first()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    return {
        "id": host.id,
        "name": host.name,
        "email": host.email,
        "phone": host.phone,
        "telegram_id": host.telegram_id,
        "preferred_language": host.preferred_language,
        "google_calendar_id": host.google_calendar_id,
        "payment_methods": host.get_payment_methods(),
        "created_at": host.created_at.isoformat() if host.created_at else None
    }


@router.post("/host/{host_id}/payment-methods")
async def add_payment_method(
    host_id: int,
    method: PaymentMethodCreate,
    db: Session = Depends(get_db)
):
    """Add a payment method to a host."""
    success = ConfigManager.add_payment_method(
        db=db,
        host_id=host_id,
        bank_name=method.bank_name,
        account_number=method.account_number,
        account_name=method.account_name,
        instructions=method.instructions
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Host not found")
    
    host = db.query(Host).filter(Host.id == host_id).first()
    return {
        "message": "Payment method added successfully",
        "payment_methods": host.get_payment_methods()
    }


@router.get("/host/{host_id}/payment-methods")
async def get_payment_methods(host_id: int, db: Session = Depends(get_db)):
    """Get all payment methods for a host."""
    payment_methods = ConfigManager.get_payment_methods(db=db, host_id=host_id)
    return {
        "host_id": host_id,
        "payment_methods": payment_methods
    }


@router.post("/properties", response_model=PropertyResponse)
async def create_property(property_data: PropertyCreate, db: Session = Depends(get_db)):
    """Create a new property."""
    try:
        # Validate data
        data_dict = property_data.dict()
        is_valid, error_msg = ConfigManager.validate_property_data(data_dict)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        property = ConfigManager.create_property(
            db=db,
            host_id=property_data.host_id,
            property_identifier=property_data.property_identifier,
            name=property_data.name,
            location=property_data.location,
            base_price=property_data.base_price,
            min_price=property_data.min_price,
            max_price=property_data.max_price,
            max_guests=property_data.max_guests,
            check_in_time=property_data.check_in_time,
            check_out_time=property_data.check_out_time,
            cleaning_rules=property_data.cleaning_rules,
            check_in_template=property_data.check_in_template,
            check_out_template=property_data.check_out_template,
            cleaner_telegram_id=property_data.cleaner_telegram_id,
            cleaner_name=property_data.cleaner_name
        )
        
        return PropertyResponse(
            id=property.id,
            property_identifier=property.property_identifier,
            name=property.name,
            location=property.location,
            base_price=property.base_price,
            min_price=property.min_price,
            max_price=property.max_price,
            max_guests=property.max_guests,
            photo_paths=property.get_photo_paths()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating property: {str(e)}")

