# Complete Implementation Plan - Everything We Need To Do

## Overview
This plan covers EVERYTHING: deletions, changes, additions, and the n8n conversion. Simple and clear.

---

## Part 1: DELETE THINGS

### 1.1 Delete Cleaner Agent References
**Files to modify:**
- `api/routes/agents.py`
  - ❌ DELETE: `/agents/cleaner-coordination/schedule` endpoint
  - ❌ DELETE: `/agents/cleaner-coordination/handle-request` endpoint

**Files to check (remove references if found):**
- `docs/plan.md` - Remove cleaner agent sections
- `docs/project-summary.md` - Remove cleaner agent mentions
- Any test files mentioning cleaner

**Database:**
- ✅ KEEP `CleaningTask` model (don't delete, just don't use it)
- ✅ KEEP cleaner fields in Property model (don't delete, just ignore)

**Time: 15 minutes**

---

### 1.2 Delete Deprecated InquiryBookingAgent
**Files to delete:**
- ❌ DELETE: `agents/inquiry_booking_agent.py` (entire file)

**Files to modify:**
- `api/telegram/guest_bot.py`
  - ❌ DELETE: `from agents.inquiry_booking_agent import InquiryBookingAgent`
  - ❌ DELETE: Any references to `InquiryBookingAgent`

**Time: 10 minutes**

---

### 1.3 Delete Negotiation Logic
**Files to modify:**
- `agents/booking_agent.py`
  - ❌ DELETE: `negotiate_price()` method (entire method)
  - ❌ DELETE: All negotiation keyword detection
  - ❌ DELETE: Negotiation context in system prompts
  - ❌ DELETE: Price negotiation handling in `handle_booking()`
  - ✅ KEEP: `calculate_price()` but simplify it (just base_price × nights)

**Time: 1 hour**

---

### 1.4 Delete Direct Telegram Handling from Python
**Files to modify:**
- `api/telegram/guest_bot.py`
  - ❌ DELETE: Direct agent calls from `handle_guest_message()`
  - ❌ DELETE: Telegram message sending from agent handlers
  - ✅ KEEP: Utility functions (can be called from n8n)
  - ✅ KEEP: Payment screenshot handling logic (but make it a service endpoint)

- `api/telegram/host_bot.py`
  - ❌ DELETE: Direct service calls from `handle_host_message()`
  - ❌ DELETE: Telegram message sending
  - ✅ KEEP: Payment approval logic (but make it a service endpoint)

**Files to modify or delete:**
- `api/routes/telegram.py`
  - ❌ DELETE: `/webhook/guest` endpoint (or make it passthrough to n8n)
  - ❌ DELETE: `/webhook/host` endpoint (or make it passthrough to n8n)
  - ⚠️ OR: Keep them but they just forward to n8n (simpler for migration)

**Time: 2 hours**

---

## Part 2: CHANGE/REFACTOR THINGS

### 2.1 Simplify Booking Agent - Remove Negotiation
**File: `agents/booking_agent.py`**

**Changes:**
1. Simplify `calculate_price()`:
   ```python
   # OLD: Complex with urgency multipliers, discounts, negotiation
   # NEW: Simple
   total_price = base_price * nights
   ```

2. Update `format_system_prompt()`:
   - ❌ DELETE: All mentions of negotiation
   - ❌ DELETE: min_price/max_price mentions
   - ✅ KEEP: Base price only
   - ✅ ADD: "Fixed rate: base_price × number_of_nights"

3. Update `handle_booking()`:
   - ❌ DELETE: All negotiation logic
   - ❌ DELETE: `negotiate_price()` calls
   - ✅ KEEP: Price calculation (simplified)
   - ✅ KEEP: Payment request flow

**Time: 1 hour**

---

### 2.2 Add Basic Info Collection Before Payment
**File: `agents/booking_agent.py`**

**Changes:**
1. Before requesting payment, ask for:
   - Guest full name
   - Number of guests
   - Contact info (optional)

2. Store in conversation context

3. Update system prompt to request this info first

4. Only request payment after basic info is collected

**Time: 1 hour**

---

### 2.3 Make Agents Pure HTTP Services
**Files: `api/routes/agents.py` and agent files**

**Changes:**
1. Ensure all agent endpoints:
   - Accept JSON: `{message, guest_telegram_id, property_id, conversation_history}`
   - Return JSON: `{response, action, metadata}`
   - ❌ NO Telegram API calls
   - ❌ NO direct message sending

2. Remove all `send_message()` calls from agents

3. Agents only return data, n8n handles Telegram

**Files to check:**
- `agents/inquiry_agent.py` - Remove Telegram calls
- `agents/booking_agent.py` - Remove Telegram calls
- `api/routes/agents.py` - Verify endpoints are pure HTTP

**Time: 1 hour**

---

### 2.4 Create Service Endpoints for n8n
**File: `api/routes/agents.py` or new `api/routes/services.py`**

**Create endpoints:**
1. `POST /api/payment/handle-screenshot`
   - Input: `{guest_telegram_id, file_id, property_id, booking_details}`
   - Output: `{booking_id, status}`

2. `POST /api/payment/approve`
   - Input: `{booking_id, approved: true/false, host_telegram_id}`
   - Output: `{status, message}`

3. `GET /api/bookings/upcoming-checkin?days=1`
   - Output: `[{booking_id, guest_telegram_id, property_id, check_in_date, ...}]`

4. `GET /api/bookings/checkout-today`
   - Output: `[{booking_id, guest_telegram_id, property_id, check_out_date, ...}]`

**Time: 2 hours**

---

## Part 3: CREATE NEW THINGS

### 3.1 Create QnA Agent
**File: `agents/qna_agent.py` (NEW)**

**What it does:**
- Answers FAQ questions about property
- Uses property configuration as knowledge base
- Handles questions about: wifi, amenities, check-in/check-out, rules, etc.

**Implementation:**
1. Create `QnAAgent` class extending `BaseAgent`
2. System prompt with property info
3. `handle_qna()` method that processes questions
4. Return JSON response

**File: `api/routes/agents.py`**
- Add endpoint: `POST /api/agents/qna/process`

**Time: 2 hours**

---

### 3.2 Create Host Summary Agent
**File: `agents/host_summary_agent.py` (NEW)**

**What it does:**
- Generates weekly reports
- Aggregates data from system logs
- Reports: bookings, confirmations, payments, inquiries

**Implementation:**
1. Create `HostSummaryAgent` class
2. `generate_weekly_report()` method
3. Query system logs for the week
4. Format as readable text
5. Return JSON

**File: `api/routes/agents.py`**
- Add endpoint: `POST /api/agents/host-summary/weekly`

**Time: 3 hours**

---

### 3.3 Create n8n Workflows

#### 3.3.1 Guest Bot Router Workflow
**File: `n8n_workflows/guest-bot-router.json` (NEW)**

**Structure:**
```
Telegram Trigger (Guest Bot)
  ↓
IF (message.text == "/start")
  → Telegram Send Message (welcome)
  ↓
ELSE IF (message.text == "/inquiry")
  → HTTP Request → /api/agents/inquiry/process
  → Telegram Send Message (response)
  ↓
ELSE IF (message.text == "/qna")
  → HTTP Request → /api/agents/qna/process
  → Telegram Send Message (response)
  ↓
ELSE IF (message.photo exists)
  → HTTP Request → /api/payment/handle-screenshot
  → Telegram Send Message (confirmation)
  ↓
ELSE (regular message)
  → HTTP Request → /api/agents/inquiry/process (or booking if context suggests)
  → Telegram Send Message (response)
```

**Time: 2 hours**

---

#### 3.3.2 Host Bot Router Workflow
**File: `n8n_workflows/host-bot-router.json` (NEW)**

**Structure:**
```
Telegram Trigger (Host Bot)
  ↓
IF (message.text == "/start" or "/setup" or "/add_property")
  → HTTP Request → /api/host/commands
  → Telegram Send Message (response)
  ↓
ELSE IF (message.text == "yes" or "y" or "approve")
  → HTTP Request → /api/payment/approve (with approved=true)
  → Telegram Send Message (confirmation)
  ↓
ELSE IF (message.text == "no" or "n" or "reject")
  → HTTP Request → /api/payment/approve (with approved=false)
  → Telegram Send Message (confirmation)
  ↓
ELSE
  → Telegram Send Message (unknown command)
```

**Time: 1 hour**

---

#### 3.3.3 Booking Confirmation Workflow
**File: `n8n_workflows/booking-confirmed.json` (NEW)**

**Structure:**
```
Webhook Trigger
  ↓
HTTP Request → /api/calendar/create-event (or Google Calendar node)
  ↓
Telegram Send Message → Guest (confirmation)
  ↓
HTTP Request → /api/logs/event (log confirmation)
```

**Time: 30 minutes**

---

#### 3.3.4 Pre-Check-in Workflow
**File: `n8n_workflows/pre-checkin.json` (NEW)**

**Structure:**
```
Schedule Trigger (Daily at 9 AM)
  ↓
HTTP Request → /api/bookings/upcoming-checkin?days=1
  ↓
For Each Booking:
  → HTTP Request → /api/properties/{property_id}
  → Get check-in instructions
  → Telegram Send Message → Guest
```

**Time: 30 minutes**

---

#### 3.3.5 Check-out Workflow
**File: `n8n_workflows/checkout.json` (NEW)**

**Structure:**
```
Schedule Trigger (Daily at 9 AM)
  ↓
HTTP Request → /api/bookings/checkout-today
  ↓
For Each Booking:
  → HTTP Request → /api/properties/{property_id}
  → Get check-out instructions
  → Telegram Send Message → Guest
```

**Time: 30 minutes**

---

#### 3.3.6 Weekly Summary Workflow
**File: `n8n_workflows/weekly-summary.json` (NEW)**

**Structure:**
```
Schedule Trigger (Weekly, Monday 9 AM)
  ↓
HTTP Request → /api/agents/host-summary/weekly
  ↓
Telegram Send Message → Host (with report)
```

**Time: 30 minutes**

---

## Part 4: CONFIGURATION CHANGES

### 4.1 Update Telegram Webhook URLs
**Action:**
1. Get n8n webhook URLs for:
   - Guest Bot Router workflow
   - Host Bot Router workflow

2. Update Telegram webhooks:
   ```bash
   # Guest Bot
   curl "https://api.telegram.org/bot<GUEST_BOT_TOKEN>/setWebhook?url=<n8n_guest_webhook_url>"
   
   # Host Bot
   curl "https://api.telegram.org/bot<HOST_BOT_TOKEN>/setWebhook?url=<n8n_host_webhook_url>"
   ```

3. Remove old FastAPI webhook URLs

**Time: 10 minutes**

---

### 4.2 Update Python Code to Call n8n Webhooks
**Files to modify:**
- `api/utils/payment.py`
  - After payment approval, call n8n booking-confirmed webhook
  - Send: `{booking_id, guest_telegram_id, property_id, dates}`

**Time: 15 minutes**

---

## Part 5: TESTING

### 5.1 Test Basic Flow
- [ ] Send message to guest bot → n8n receives
- [ ] n8n routes to agent
- [ ] Agent returns response
- [ ] n8n sends to guest
- [ ] Guest receives message

### 5.2 Test Commands
- [ ] `/start` works
- [ ] `/inquiry` works
- [ ] `/qna` works

### 5.3 Test Payment
- [ ] Upload screenshot → handled correctly
- [ ] Host approves → booking confirmed
- [ ] Guest receives confirmation

### 5.4 Test Scheduled Workflows
- [ ] Pre-check-in (manual trigger)
- [ ] Check-out (manual trigger)
- [ ] Weekly summary (manual trigger)

**Time: 2 hours**

---

## Complete Checklist - In Order

### Phase 1: Cleanup (2-3 hours)
- [ ] Delete cleaner agent endpoints
- [ ] Delete InquiryBookingAgent file
- [ ] Remove negotiation logic from BookingAgent
- [ ] Remove direct Telegram handling from Python

### Phase 2: Refactor (3-4 hours)
- [ ] Simplify BookingAgent (fixed rate only)
- [ ] Add basic info collection
- [ ] Make agents pure HTTP services
- [ ] Create service endpoints for n8n

### Phase 3: Create New (6-7 hours)
- [ ] Create QnA Agent
- [ ] Create Host Summary Agent
- [ ] Create all 6 n8n workflows
- [ ] Test workflows in n8n

### Phase 4: Configuration (30 minutes)
- [ ] Update Telegram webhook URLs
- [ ] Update Python to call n8n webhooks

### Phase 5: Testing (2 hours)
- [ ] Test all flows
- [ ] Fix any issues

**Total Time: 13-16 hours** (can be done in 2 days)

---

## Files Summary

### Files to DELETE:
- `agents/inquiry_booking_agent.py`

### Files to MODIFY:
- `agents/booking_agent.py` - Remove negotiation, add basic info, simplify
- `agents/inquiry_agent.py` - Remove Telegram calls
- `api/telegram/guest_bot.py` - Remove direct agent calls
- `api/telegram/host_bot.py` - Remove direct service calls
- `api/routes/agents.py` - Add QnA and Host Summary endpoints, remove cleaner
- `api/routes/telegram.py` - Remove or modify webhook endpoints
- `api/utils/payment.py` - Add n8n webhook call

### Files to CREATE:
- `agents/qna_agent.py`
- `agents/host_summary_agent.py`
- `n8n_workflows/guest-bot-router.json`
- `n8n_workflows/host-bot-router.json`
- `n8n_workflows/booking-confirmed.json`
- `n8n_workflows/pre-checkin.json`
- `n8n_workflows/checkout.json`
- `n8n_workflows/weekly-summary.json`

### Files to CREATE (Service Endpoints):
- New endpoints in `api/routes/agents.py` or `api/routes/services.py`:
  - `/api/payment/handle-screenshot`
  - `/api/payment/approve`
  - `/api/bookings/upcoming-checkin`
  - `/api/bookings/checkout-today`

---

## Quick Start Guide

**Day 1 Morning (4 hours):**
1. Delete everything in Phase 1
2. Refactor BookingAgent (remove negotiation, add basic info)

**Day 1 Afternoon (4 hours):**
3. Make agents pure HTTP services
4. Create service endpoints
5. Create QnA Agent

**Day 2 Morning (4 hours):**
6. Create Host Summary Agent
7. Create n8n workflows (Guest and Host routers)

**Day 2 Afternoon (4 hours):**
8. Create remaining n8n workflows
9. Update webhook URLs
10. Test everything

---

## Important Notes

1. **Test after each phase** - Don't move forward if something is broken
2. **Keep it simple** - n8n routes, Python does logic
3. **No Telegram in Python** - All Telegram via n8n
4. **One thing at a time** - Complete each item before moving to next

---

## If Something Breaks

1. Check n8n workflow is active
2. Check FastAPI is running
3. Check endpoint URLs are correct
4. Check request/response formats match
5. Check Telegram webhook URLs are correct
6. Check logs in n8n and FastAPI

---

That's it. Everything in one plan. Simple and clear.

