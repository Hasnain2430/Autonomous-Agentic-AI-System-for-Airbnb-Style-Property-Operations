# Agent Split Implementation Plan

## Overview

Split the monolithic `InquiryBookingAgent` into two focused agents:

1. **InquiryAgent**: Handles basic questions, availability checks, property information
2. **BookingAgent**: Handles price negotiation, booking confirmation, and payment processing

## Goals

- Reduce prompt complexity and hallucinations
- Improve context management
- Better separation of concerns
- Maintain seamless conversation flow

## Implementation Steps

### Step 1: Create InquiryAgent

**File**: `agents/inquiry_agent.py`

**Responsibilities**:

- Answer property questions (location, amenities, check-in/out times, max guests)
- Check availability for dates
- Provide base pricing information
- Detect booking intent (when user wants to proceed with booking)

**System Prompt Focus**:

- Property information display
- Availability checking
- Basic pricing (base price only, no negotiation)
- Guardrails for domain-related questions only
- Clean, simple responses

**Output Actions**:

- `action: "inquiry"` - Normal inquiry response
- `action: "transition_to_booking"` - User wants to book/negotiate
- `action: "availability_check"` - Availability confirmed

**Context Saved**:

- Dates mentioned by user
- Property questions asked
- Availability status

---

### Step 2: Create BookingAgent

**File**: `agents/booking_agent.py`

**Responsibilities**:

- Price negotiation (dynamic pricing, discounts for longer stays)
- Booking confirmation
- Payment method display (with actual bank details)
- Payment screenshot collection guidance
- Handle payment-related follow-ups

**System Prompt Focus**:

- Negotiation strategies
- Payment methods (retrieved from database)
- Booking confirmation flow
- Payment screenshot requirements
- Context about dates and negotiated prices

**Output Actions**:

- `action: "negotiation"` - Price negotiation in progress
- `action: "booking_confirmed"` - User confirmed booking
- `action: "payment_requested"` - Payment methods displayed, awaiting screenshot
- `action: "payment_received"` - Screenshot received (handled by guest_bot.py)

**Context Saved**:

- Negotiated price
- Negotiated dates
- Booking status
- Payment method preferences

---

### Step 3: Create Agent Router Logic

**File**: `api/utils/agent_router.py`

**Purpose**: Determine which agent should handle a message

**Routing Logic**:

1. **Check conversation context for active agent**:

   - If `booking_intent: true` or `active_agent: "booking"` → BookingAgent
   - If `active_agent: "inquiry"` → InquiryAgent
   - Default: InquiryAgent

2. **Detect transition triggers**:

   - **Inquiry → Booking**:

     - User says "yes" to booking
     - User asks about discounts/negotiation
     - User mentions payment
     - User confirms dates and wants to proceed

   - **Booking → Inquiry** (rare, but possible):
     - User asks a general property question during booking
     - User wants to change property

3. **Context preservation**:
   - Both agents read from same conversation context
   - Both agents write to same conversation context
   - Dates, property info, guest preferences shared

**Functions**:

- `determine_agent(db, guest_id, property_id, message, conversation_history) -> str`
- `should_transition_to_booking(message, context) -> bool`
- `should_transition_to_inquiry(message, context) -> bool`

---

### Step 4: Update Conversation Context Manager

**File**: `api/utils/conversation_context.py`

**Enhancements**:

- Add `active_agent` field to track current agent
- Add `booking_intent` flag to indicate booking flow started
- Add `transition_history` to track agent switches
- Ensure both agents can read/write context seamlessly

**New Context Fields**:

```python
{
    "active_agent": "inquiry" | "booking",
    "booking_intent": bool,
    "dates": {...},
    "negotiated_price": float,
    "negotiated_dates": {...},
    "booking_status": str,
    "transition_history": [...]
}
```

---

### Step 5: Update Guest Bot Handler

**File**: `api/telegram/guest_bot.py`

**Changes**:

1. Import both agents and router
2. Use router to determine which agent to call
3. Handle agent transitions smoothly
4. Update context when agent switches
5. Maintain existing payment screenshot handling

**Flow**:

```
Message received
  ↓
Check pending payment request (existing logic)
  ↓
Use agent_router to determine agent
  ↓
Call appropriate agent (InquiryAgent or BookingAgent)
  ↓
Check if agent wants to transition
  ↓
Update context with new active_agent
  ↓
Send response to user
```

---

### Step 6: Update Agent Imports

**File**: `agents/__init__.py`

**Changes**:

- Export both `InquiryAgent` and `BookingAgent`
- Keep `InquiryBookingAgent` for backward compatibility (deprecated)

---

### Step 7: Update API Routes (if needed)

**File**: `api/routes/agents.py`

**Changes**:

- Update endpoint to support both agents
- Or create separate endpoints for each agent
- Maintain backward compatibility

---

### Step 8: Testing & Validation

**Test Scenarios**:

1. **Basic Inquiry Flow**:

   - User asks about property → InquiryAgent responds
   - User asks about availability → InquiryAgent responds
   - User asks about pricing → InquiryAgent responds with base price

2. **Inquiry to Booking Transition**:

   - User asks about property → InquiryAgent
   - User says "I want to book" → Transition to BookingAgent
   - BookingAgent handles negotiation

3. **Booking Flow**:

   - User negotiates price → BookingAgent
   - User confirms booking → BookingAgent
   - User receives payment instructions → BookingAgent
   - User sends screenshot → guest_bot.py handles (existing)

4. **Context Preservation**:

   - Dates mentioned to InquiryAgent → Available to BookingAgent
   - Negotiated price in BookingAgent → Persisted in context
   - Payment methods displayed correctly (no placeholders)

5. **Edge Cases**:
   - User asks property question during booking → Stay in BookingAgent or transition?
   - User changes dates after negotiation → BookingAgent resets price
   - User says "no" to booking → Transition back to InquiryAgent?

---

## Context Sharing Strategy

### Shared Context Fields:

- `dates`: Check-in/check-out dates (set by InquiryAgent, used by BookingAgent)
- `property_id`: Current property (set by InquiryAgent, used by BookingAgent)
- `guest_preferences`: Any preferences mentioned (both agents can read/write)
- `last_interaction`: Timestamp (both agents update)

### Agent-Specific Context:

- **InquiryAgent**:
  - `questions_asked`: List of questions user asked
  - `availability_checked`: Dates checked for availability
- **BookingAgent**:
  - `negotiated_price`: Final negotiated price
  - `negotiated_dates`: Dates for negotiated price
  - `payment_method_preference`: User's preferred payment method
  - `booking_status`: "pending", "confirmed", "payment_awaiting"

### Context Update Rules:

1. Both agents read from same context source
2. Both agents can update context
3. When agent transitions, context is preserved
4. Dates and property info are always shared
5. Negotiated prices are only set by BookingAgent

---

## Migration Strategy

1. **Phase 1**: Create new agents alongside existing one
2. **Phase 2**: Update guest_bot.py to use router
3. **Phase 3**: Test thoroughly
4. **Phase 4**: Deprecate InquiryBookingAgent (keep for reference)

---

## Success Criteria

✅ InquiryAgent handles all basic questions without mentioning negotiation/payment
✅ BookingAgent handles negotiation and payment without asking basic property questions
✅ Context is preserved when transitioning between agents
✅ Dates are never asked twice
✅ Payment methods display actual bank details (no placeholders)
✅ No hallucinations about pricing or payment
✅ Smooth conversation flow without user noticing agent switch

---

## Files to Create/Modify

### New Files:

- `agents/inquiry_agent.py`
- `agents/booking_agent.py`
- `api/utils/agent_router.py`

### Modified Files:

- `api/telegram/guest_bot.py`
- `api/utils/conversation_context.py`
- `agents/__init__.py`
- `api/routes/agents.py` (if needed)

### Documentation:

- `docs/agent-split-execution.md` (this file's execution log)
- Update `docs/implementation-status.md`

---

## Notes

- Keep system prompts focused and short (40-60 lines max)
- Use explicit instructions for context usage
- Log all agent transitions for debugging
- Ensure backward compatibility during migration
- Test payment flow thoroughly (critical path)
