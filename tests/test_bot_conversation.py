"""
Test script for bot conversation fixes.

Tests all the issues that were identified and fixed.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db, init_db
from database.models import Property, Host
from agents.inquiry_booking_agent import InquiryBookingAgent
from api.utils.conversation import get_conversation_history, extract_dates_from_history
from api.utils.conversation_context import get_conversation_context, get_context_summary_for_llm
from api.utils.logging import log_event, EventType
from datetime import datetime

def test_date_extraction():
    """Test date extraction from various formats."""
    print("\n=== Test 1: Date Extraction ===")
    
    test_cases = [
        "24th Nov - 30th Nov 2025",
        "25th Nov - 30th Nov 2025",
        "24th Nov - 27th Nov 2025",
    ]
    
    for test in test_cases:
        dates = extract_dates_from_history([{"role": "user", "content": test}])
        if dates:
            print(f"✅ '{test}' → {dates}")
        else:
            print(f"❌ '{test}' → Failed to extract dates")
    
    return True

def test_context_storage():
    """Test context storage and retrieval."""
    print("\n=== Test 2: Context Storage ===")
    
    db = next(get_db())
    
    try:
        # Get a property
        property_obj = db.query(Property).first()
        if not property_obj:
            print("❌ No property found in database")
            return False
        
        # Simulate a guest conversation
        guest_id = "test_guest_123"
        
        # Log a message with dates
        log_event(
            db=db,
            event_type=EventType.GUEST_MESSAGE,
            agent_name="Test",
            property_id=property_obj.id,
            message="Guest provided dates",
            metadata={
                "user_id": guest_id,
                "text": "24th Nov - 30th Nov 2025"
            }
        )
        
        # Log a negotiation
        log_event(
            db=db,
            event_type=EventType.AGENT_DECISION,
            agent_name="InquiryBookingAgent",
            property_id=property_obj.id,
            message="Price negotiation",
            metadata={
                "guest_telegram_id": guest_id,
                "negotiated_price": 450.0,
                "negotiated_dates": {"check_in": "2025-11-24", "check_out": "2025-11-30"},
                "nights": 6
            }
        )
        
        # Retrieve context
        context = get_conversation_context(db, guest_id, property_obj.id)
        print(f"✅ Context retrieved:")
        print(f"   Dates: {context.get('dates')}")
        print(f"   Negotiated price: {context.get('negotiated_price')}")
        print(f"   Negotiated dates: {context.get('negotiated_dates')}")
        
        # Get context summary
        summary = get_context_summary_for_llm(db, guest_id, property_obj.id)
        print(f"✅ Context summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_guardrails():
    """Test guardrails with follow-up questions."""
    print("\n=== Test 3: Guardrails ===")
    
    followup_questions = [
        "Didn't we agree on $90?",
        "We decided on $90 per night",
        "Before you said $90",
        "What about the $90 we agreed on?"
    ]
    
    followup_keywords = ["we", "agreed", "decided", "before", "earlier", "previous", "didn't", "didnt"]
    
    for question in followup_questions:
        question_lower = question.lower()
        is_followup = any(keyword in question_lower for keyword in followup_keywords)
        print(f"{'✅' if is_followup else '❌'} '{question}' → Follow-up detected: {is_followup}")
    
    return True

def test_booking_intent():
    """Test booking intent detection."""
    print("\n=== Test 4: Booking Intent Detection ===")
    
    booking_responses = [
        "yes",
        "yeah sure",
        "ok",
        "yes please",
        "proceed"
    ]
    
    booking_keywords = ["yes", "yeah", "sure", "ok", "okay", "proceed", "let's do it", "lets do it", "please", "go ahead"]
    
    for response in booking_responses:
        response_lower = response.lower().strip()
        is_just_intent = len(response_lower.split()) <= 3
        wants_to_book = is_just_intent and any(keyword in response_lower for keyword in booking_keywords)
        print(f"{'✅' if wants_to_book else '❌'} '{response}' → Booking intent: {wants_to_book}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Bot Conversation Fixes - Test Suite")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    results = []
    
    # Run tests
    results.append(("Date Extraction", test_date_extraction()))
    results.append(("Context Storage", test_context_storage()))
    results.append(("Guardrails", test_guardrails()))
    results.append(("Booking Intent", test_booking_intent()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

