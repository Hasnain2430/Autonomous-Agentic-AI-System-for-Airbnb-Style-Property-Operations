"""
Integration test for full conversation flow.

Simulates the actual conversation scenarios to verify all fixes work together.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db, init_db
from database.models import Property, Host
from agents.inquiry_booking_agent import InquiryBookingAgent
from api.utils.conversation import get_conversation_history
from api.utils.conversation_context import get_conversation_context
from api.utils.logging import log_event, EventType
from datetime import datetime

def simulate_conversation():
    """Simulate the full conversation flow from user testing."""
    print("\n" + "=" * 60)
    print("Simulating Full Conversation Flow")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Get property
        property_obj = db.query(Property).first()
        if not property_obj:
            print("❌ No property found")
            return False
        
        guest_id = "test_guest_999"
        property_id = property_obj.id
        
        agent = InquiryBookingAgent()
        
        # Conversation 1: Ask about availability
        print("\n--- Message 1: Ask about availability ---")
        message1 = "are the beautiful apartment available?"
        result1 = agent.handle_inquiry(db, message1, property_id, guest_id, None)
        print(f"User: {message1}")
        print(f"Bot: {result1['response'][:100]}...")
        
        # Log the response
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name=agent.agent_name,
            property_id=property_id,
            message=result1['response'],
            metadata={"user_id": guest_id}
        )
        
        # Conversation 2: Provide dates
        print("\n--- Message 2: Provide dates ---")
        message2 = "25th Nov - 30th Nov 2025"
        history = get_conversation_history(db, guest_id, property_id, limit=5)
        result2 = agent.handle_inquiry(db, message2, property_id, guest_id, history)
        print(f"User: {message2}")
        print(f"Bot: {result2['response'][:150]}...")
        
        # Check if bot asked for dates (should NOT)
        if "date" in result2['response'].lower() and ("provide" in result2['response'].lower() or "tell" in result2['response'].lower()):
            print("❌ Bot asked for dates when they were provided!")
            return False
        else:
            print("✅ Bot used dates from message")
        
        # Log
        log_event(
            db=db,
            event_type=EventType.GUEST_MESSAGE,
            agent_name="GuestBot",
            property_id=property_id,
            message=message2,
            metadata={"user_id": guest_id, "text": message2}
        )
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name=agent.agent_name,
            property_id=property_id,
            message=result2['response'],
            metadata={"user_id": guest_id}
        )
        
        # Conversation 3: Ask for discount
        print("\n--- Message 3: Ask for discount ---")
        message3 = "I'm staying for 5 nights is there any way i can get a lower rate?"
        history = get_conversation_history(db, guest_id, property_id, limit=10)
        result3 = agent.handle_inquiry(db, message3, property_id, guest_id, history)
        print(f"User: {message3}")
        print(f"Bot: {result3['response'][:150]}...")
        
        # Check if negotiated price was saved
        context_after = get_conversation_context(db, guest_id, property_id)
        if context_after.get("negotiated_price"):
            print(f"✅ Negotiated price saved: ${context_after['negotiated_price']:.2f}")
        else:
            print("⚠️  Negotiated price not found in context")
        
        # Log
        log_event(
            db=db,
            event_type=EventType.GUEST_MESSAGE,
            agent_name="GuestBot",
            property_id=property_id,
            message=message3,
            metadata={"user_id": guest_id, "text": message3}
        )
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name=agent.agent_name,
            property_id=property_id,
            message=result3['response'],
            metadata={"user_id": guest_id}
        )
        
        # Conversation 4: Change dates
        print("\n--- Message 4: Change dates ---")
        message4 = "25th Nov - 27th Nov 2025"
        history = get_conversation_history(db, guest_id, property_id, limit=10)
        result4 = agent.handle_inquiry(db, message4, property_id, guest_id, history)
        print(f"User: {message4}")
        print(f"Bot: {result4['response'][:200]}...")
        
        # Check if bot explained price change
        if "different" in result4['response'].lower() or "previous" in result4['response'].lower() or "was for" in result4['response'].lower():
            print("✅ Bot explained price change")
        else:
            print("⚠️  Bot may not have explained price change")
        
        # Log
        log_event(
            db=db,
            event_type=EventType.GUEST_MESSAGE,
            agent_name="GuestBot",
            property_id=property_id,
            message=message4,
            metadata={"user_id": guest_id, "text": message4}
        )
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name=agent.agent_name,
            property_id=property_id,
            message=result4['response'],
            metadata={"user_id": guest_id}
        )
        
        # Conversation 5: Ask about previous agreement
        print("\n--- Message 5: Ask about previous agreement ---")
        message5 = "Didn't we decide and agree on $90?"
        history = get_conversation_history(db, guest_id, property_id, limit=10)
        result5 = agent.handle_inquiry(db, message5, property_id, guest_id, history)
        print(f"User: {message5}")
        print(f"Bot: {result5['response'][:200]}...")
        
        # Check if guardrails blocked it
        if "can only help" in result5['response'].lower() and "property bookings" in result5['response'].lower():
            print("❌ Guardrails blocked valid follow-up question!")
            return False
        else:
            print("✅ Guardrails allowed follow-up question")
        
        # Conversation 6: Say yes to booking
        print("\n--- Message 6: Say yes to booking ---")
        message6 = "Yes please"
        history = get_conversation_history(db, guest_id, property_id, limit=10)
        result6 = agent.handle_inquiry(db, message6, property_id, guest_id, history)
        print(f"User: {message6}")
        print(f"Bot: {result6['response'][:200]}...")
        
        # Check if bot asked for dates (should NOT)
        if "date" in result6['response'].lower() and ("provide" in result6['response'].lower() or "tell" in result6['response'].lower() or "let me know" in result6['response'].lower()):
            print("❌ Bot asked for dates when user said yes!")
            return False
        else:
            print("✅ Bot proceeded without asking for dates")
        
        # Check if payment was mentioned
        if "payment" in result6['response'].lower() or "screenshot" in result6['response'].lower():
            print("✅ Bot proceeded to payment")
        else:
            print("⚠️  Bot may not have proceeded to payment")
        
        print("\n" + "=" * 60)
        print("✅ All conversation flow tests completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    success = simulate_conversation()
    sys.exit(0 if success else 1)

