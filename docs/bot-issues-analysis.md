# Bot Conversation Issues Analysis

## Issues Identified from User Testing

### Issue 1: Context Memory Not Working
**Problem:** After agreeing on $90/night for 5 nights, when user changes dates, bot doesn't remember the previous agreement.

**Example:**
- User: "I'm staying for 5 nights is there any way i can get a lower rate?"
- Bot: "Yes, I can offer you $90 per night for 5 nights"
- User: Changes dates to 2 nights
- Bot: Doesn't remember $90 agreement, gives new price without explanation

**Expected Behavior:** Bot should remember previous negotiations and explain: "The $90/night rate was for 5 nights. For your new dates (2 nights), the rate is different."

---

### Issue 2: Guardrails Blocking Valid Questions
**Problem:** When user asks "Didn't we decide and agree on $90?", guardrails block it as off-topic.

**Example:**
- User: "Didn't we decide and agree on $90?"
- Bot: "I can only help with property bookings and inquiries..."

**Expected Behavior:** Recognize this as a follow-up question about previous negotiation, not off-topic.

---

### Issue 3: Repeatedly Asking for Dates
**Problem:** Bot asks for dates multiple times even after they were provided.

**Examples:**
- After user says "Yes please" to booking → Bot asks for dates again
- After providing "24th Nov - 30th Nov" → Bot asks again in next message

**Expected Behavior:** Remember dates from conversation and use them automatically.

---

### Issue 4: No Explanation When Dates Change
**Problem:** When dates change from 5 nights to 2 nights, bot doesn't explain why price changed.

**Expected Behavior:** "I see you changed your dates. The $90/night rate was for 5 nights. For 2 nights, the rate is $100/night."

---

### Issue 5: Booking Flow Not Proceeding
**Problem:** After user says "Yes please" to booking, bot asks for dates instead of explaining payment.

**Expected Behavior:** Proceed with payment instructions using dates already provided.

---

### Issue 6: Negotiated Price Not Stored/Retrieved
**Problem:** The $90/night agreement isn't being saved or retrieved from context.

**Expected Behavior:** Save negotiated prices and retrieve them when relevant.

---

### Issue 7: Context Summary Not Being Used Effectively
**Problem:** Conversation context system exists but isn't being used effectively.

**Expected Behavior:** Use stored context to remember previous agreements and dates.

---

### Issue 8: LLM Not Following Context Instructions
**Problem:** Even with context notes, LLM asks for dates again.

**Expected Behavior:** Stronger instructions to use dates from context automatically.

---

## Root Causes

1. **Context retrieval happens but isn't being used effectively in prompts**
2. **Guardrails are too aggressive** - blocking valid follow-up questions
3. **LLM instructions need to be stronger** about using context
4. **Negotiated prices aren't being saved properly** in metadata
5. **Booking flow logic needs to check** for existing dates before asking

---

## Priority Fixes Needed

### High Priority:
1. ✅ Fix date memory - stop asking for dates that were already provided
2. ✅ Fix context retrieval - remember negotiated prices and agreements
3. ✅ Fix guardrails - don't block valid follow-up questions

### Medium Priority:
4. ✅ Add date change detection - explain why price changed when dates change
5. ✅ Fix booking flow - proceed with payment when user says "yes" and dates exist

---

## Fix Plan

### Step 1: Improve Context Storage
- Save negotiated prices with dates in metadata
- Store booking intent and dates in context
- Make context retrieval more reliable

### Step 2: Fix Guardrails
- Add keywords for follow-up questions ("we", "agreed", "decided", "before")
- Check conversation history before blocking
- Don't block questions about previous conversations

### Step 3: Strengthen Date Memory
- Extract dates from current message AND history
- Add stronger LLM instructions to NEVER ask for dates if they exist in context
- Use dates automatically in booking flow

### Step 4: Add Date Change Detection
- Compare current dates with previous dates
- Explain price changes when dates change
- Reference previous negotiations when relevant

### Step 5: Fix Booking Flow
- Check if dates exist before asking
- If user says "yes" and dates exist, proceed to payment
- Don't ask for dates if they're already in context

### Step 6: Test All Scenarios
- Test date memory across multiple messages
- Test negotiation memory
- Test booking flow
- Test date changes
- Test guardrails with valid questions

