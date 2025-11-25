"""
QnA Handler - Hybrid approach with database FAQs and LLM fallback.

Checks database for common questions first, then falls back to LLM if not found.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.models import Property, Booking
import re


def check_faq_in_database(
    db: Session,
    question: str,
    property_id: Optional[int] = None
) -> Optional[str]:
    """
    Check if question matches any FAQ in the database.
    
    Args:
        db: Database session
        question: User's question
        property_id: Optional property ID to check property-specific FAQs
    
    Returns:
        FAQ answer if found, None otherwise
    """
    question_lower = question.lower().strip()
    
    # Common question keywords
    wifi_keywords = ['wifi', 'wi-fi', 'internet', 'wireless', 'network', 'connection']
    parking_keywords = ['parking', 'car', 'vehicle', 'park']
    amenities_keywords = ['amenities', 'facilities', 'features', 'what is included', 'what\'s included']
    checkin_keywords = ['check in', 'check-in', 'checkin', 'arrival', 'when can i arrive']
    checkout_keywords = ['check out', 'check-out', 'checkout', 'departure', 'when do i leave']
    address_keywords = ['address', 'location', 'where is', 'where\'s', 'directions']
    
    # Check property-specific FAQs first
    if property_id:
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if property_obj:
            faqs = property_obj.get_faqs()
            for faq in faqs:
                if isinstance(faq, dict):
                    faq_question = faq.get('question', '').lower()
                    faq_answer = faq.get('answer', '')
                    # Check if question matches FAQ question or keywords
                    if faq_question in question_lower or question_lower in faq_question:
                        return faq_answer
                    # Check keyword matches
                    if any(keyword in question_lower for keyword in wifi_keywords) and 'wifi' in faq_question:
                        return faq_answer
                    if any(keyword in question_lower for keyword in parking_keywords) and 'parking' in faq_question:
                        return faq_answer
    
    # Check all properties for general FAQs
    all_properties = db.query(Property).all()
    for prop in all_properties:
        faqs = prop.get_faqs()
        for faq in faqs:
            if isinstance(faq, dict):
                faq_question = faq.get('question', '').lower()
                faq_answer = faq.get('answer', '')
                if faq_question in question_lower or question_lower in faq_question:
                    return faq_answer
    
    # Check for common questions based on keywords
    # WiFi questions
    if any(keyword in question_lower for keyword in wifi_keywords):
        if property_id:
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            if property_obj:
                # Try to find WiFi info in property data
                # For now, return a generic response - can be enhanced with property-specific data
                return "Yes, WiFi is available at the property. The WiFi password and network name will be provided in your check-in instructions."
    
    # Parking questions
    if any(keyword in question_lower for keyword in parking_keywords):
        return "Parking availability varies by property. Please check the property details or contact the host for specific parking information."
    
    # Check-in questions
    if any(keyword in question_lower for keyword in checkin_keywords):
        if property_id:
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            if property_obj:
                return f"Check-in time is {property_obj.check_in_time}. {property_obj.check_in_template or 'Please refer to your booking confirmation for detailed check-in instructions.'}"
    
    # Check-out questions
    if any(keyword in question_lower for keyword in checkout_keywords):
        if property_id:
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            if property_obj:
                return f"Check-out time is {property_obj.check_out_time}. {property_obj.check_out_template or 'Please ensure you check out on time and follow the check-out procedures.'}"
    
    # Address/location questions
    if any(keyword in question_lower for keyword in address_keywords):
        if property_id:
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            if property_obj:
                return f"The property is located at: {property_obj.location}. Detailed directions and address will be provided in your check-in instructions."
    
    return None


def handle_qna_with_fallback(
    db: Session,
    question: str,
    property_id: Optional[int],
    guest_telegram_id: str,
    llm_agent
) -> Dict[str, Any]:
    """
    Handle QnA with database FAQ check first, then LLM fallback.
    
    Args:
        db: Database session
        question: User's question
        property_id: Property ID (optional)
        guest_telegram_id: Guest's Telegram ID
        llm_agent: LLM agent instance (InquiryAgent)
    
    Returns:
        Dictionary with response and metadata
    """
    # First, check database FAQs
    faq_answer = check_faq_in_database(db, question, property_id)
    
    if faq_answer:
        return {
            "response": faq_answer,
            "action": "faq_answer",
            "metadata": {
                "source": "database",
                "property_id": property_id
            }
        }
    
    # If no FAQ found, use LLM
    # Get property for LLM context
    if property_id:
        property_obj = db.query(Property).filter(Property.id == property_id).first()
    else:
        # Try to find property from guest's bookings
        confirmed_booking = db.query(Booking).filter(
            Booking.guest_telegram_id == guest_telegram_id,
            Booking.booking_status == 'confirmed'
        ).order_by(Booking.check_in_date.desc()).first()
        
        if confirmed_booking:
            property_obj = confirmed_booking.property
            property_id = property_obj.id
        else:
            # Use first property as fallback for LLM
            property_obj = db.query(Property).first()
            if property_obj:
                property_id = property_obj.id
    
    if not property_obj:
        return {
            "response": "I'm sorry, I couldn't find any property information. Please contact support.",
            "action": "error",
            "metadata": {}
        }
    
    # Use LLM agent to answer
    from api.utils.conversation import get_conversation_history
    conversation_history = get_conversation_history(
        db=db,
        guest_telegram_id=guest_telegram_id,
        property_id=property_id,
        limit=10
    )
    
    result = llm_agent.handle_inquiry(
        db=db,
        message=question,
        property_id=property_id,
        guest_telegram_id=guest_telegram_id,
        conversation_history=conversation_history
    )
    
    # Mark as LLM response
    if "metadata" in result:
        result["metadata"]["source"] = "llm"
    else:
        result["metadata"] = {"source": "llm"}
    
    return result


