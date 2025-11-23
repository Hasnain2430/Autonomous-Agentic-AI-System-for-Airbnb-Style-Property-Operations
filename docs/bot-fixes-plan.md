# Bot Issues Fix Plan

## Overview
This document outlines the step-by-step plan to fix all identified bot conversation issues.

---

## Step 1: Improve Context Storage & Retrieval

### 1.1 Enhance Context Saving
- Save negotiated prices with associated dates
- Store booking intent when user says "yes"
- Save dates from every message (not just when explicitly mentioned)

### 1.2 Improve Context Retrieval
- Retrieve full conversation context including negotiated prices
- Check for dates in both current message and history
- Format context summary more effectively for LLM

### 1.3 Update Metadata Storage
- Save negotiated_price, negotiated_dates in agent response metadata
- Store booking_status when user agrees to book
- Track date changes in metadata

**Files to modify:**
- `api/utils/conversation_context.py`
- `agents/inquiry_booking_agent.py`
- `api/telegram/guest_bot.py`

---

## Step 2: Fix Guardrails Logic

### 2.1 Add Follow-up Question Keywords
- Add keywords: "we", "agreed", "decided", "before", "earlier", "previous"
- Check if message contains these + conversation history exists
- Don't block if it's clearly a follow-up

### 2.2 Improve Domain Detection
- Check conversation history before blocking
- If history exists and message is short, likely a follow-up
- Only block truly off-topic messages

**Files to modify:**
- `agents/inquiry_booking_agent.py`

---

## Step 3: Strengthen Date Memory

### 3.1 Extract Dates from All Messages
- Extract dates from current message
- Extract dates from conversation history
- Use most recent dates

### 3.2 Add Stronger LLM Instructions
- Add explicit instruction: "If dates exist in context, use them automatically"
- Add instruction: "NEVER ask for dates if they were already provided"
- Add instruction: "If user says 'yes' to booking and dates exist, proceed to payment"

### 3.3 Auto-use Dates in Booking Flow
- Check for dates in context before asking
- If dates exist and user says "yes", proceed to payment
- Only ask for dates if truly missing

**Files to modify:**
- `agents/inquiry_booking_agent.py`
- `api/utils/conversation.py`

---

## Step 4: Add Date Change Detection

### 4.1 Compare Dates
- Compare current dates with previous dates from context
- Detect if dates changed
- Calculate price difference

### 4.2 Explain Price Changes
- When dates change, explain why price changed
- Reference previous negotiation if applicable
- Show old vs new dates and prices

**Files to modify:**
- `agents/inquiry_booking_agent.py`

---

## Step 5: Fix Booking Flow

### 5.1 Check for Dates Before Asking
- Before asking for dates, check context
- If dates exist, use them
- Only ask if truly missing

### 5.2 Proceed to Payment When Ready
- If user says "yes" and dates exist, proceed to payment
- Don't ask for dates again
- Explain payment methods immediately

**Files to modify:**
- `agents/inquiry_booking_agent.py`

---

## Step 6: Testing

### 6.1 Test Scenarios
1. **Date Memory Test:**
   - Provide dates
   - Ask about availability
   - Bot should remember dates

2. **Negotiation Memory Test:**
   - Negotiate price
   - Change dates
   - Bot should remember previous negotiation

3. **Booking Flow Test:**
   - Provide dates
   - Say "yes" to booking
   - Bot should proceed to payment (not ask for dates)

4. **Date Change Test:**
   - Negotiate for 5 nights
   - Change to 2 nights
   - Bot should explain price change

5. **Guardrails Test:**
   - Ask "Didn't we agree on $90?"
   - Bot should recognize as follow-up

6. **Context Persistence Test:**
   - Have conversation
   - Wait (simulate)
   - Continue conversation
   - Bot should remember context

---

## Implementation Order

1. Step 1: Context Storage (foundation)
2. Step 2: Guardrails Fix (quick win)
3. Step 3: Date Memory (critical)
4. Step 4: Date Change Detection (enhancement)
5. Step 5: Booking Flow (critical)
6. Step 6: Testing (validation)

---

## Success Criteria

- ✅ Bot never asks for dates if they were already provided
- ✅ Bot remembers negotiated prices across date changes
- ✅ Bot explains price changes when dates change
- ✅ Bot proceeds to payment when user says "yes" and dates exist
- ✅ Guardrails don't block valid follow-up questions
- ✅ Context persists across multiple messages

