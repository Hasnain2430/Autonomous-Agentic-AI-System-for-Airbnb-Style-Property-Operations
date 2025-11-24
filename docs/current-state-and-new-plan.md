# Current State & New Implementation Plan

## Executive Summary

This document summarizes the current implementation status and outlines the revised plan based on the simplified requirements. The system is approximately **50% complete** with core infrastructure and booking flow working, but needs significant changes to align with the new simplified scope.

---

## Current Implementation Status

### ⚠️ **CRITICAL ARCHITECTURAL ISSUE**

**Current Architecture (WRONG):**

```
┌─────────────┐
│  Telegram   │
│   (Guest)   │
└──────┬──────┘
       │ Webhook
       ▼
┌─────────────────────┐
│  FastAPI            │
│  /api/webhook/guest │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ handle_guest_       │
│ message()           │
│ (Python)            │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Agent              │
│  (Python)           │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Telegram API       │
│  (Direct call)      │
└─────────────────────┘

❌ n8n is NOT in the flow
❌ All logic in Python
❌ No workflow orchestration
```

**Required Architecture (CORRECT):**

```
┌─────────────┐
│  Telegram   │
│   (Guest)   │
└──────┬──────┘
       │ Webhook
       ▼
┌─────────────────────┐
│  n8n                │
│  Telegram Trigger   │
│  (Webhook)          │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  n8n Router         │
│  (IF/ELSE nodes)    │
│  - /inquiry         │
│  - /qna             │
│  - booking intent   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  n8n HTTP Request   │
│  → FastAPI          │
│  /api/agents/...    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Agent Endpoint     │
│  (Python service)   │
│  Returns JSON only  │
└──────┬──────────────┘
       │ JSON Response
       ▼
┌─────────────────────┐
│  n8n                │
│  Telegram Send      │
│  Message            │
└──────┬──────────────┘
       │
       ▼
┌─────────────┐
│  Telegram   │
│   (Guest)   │
└─────────────┘

✅ n8n orchestrates everything
✅ Python agents are pure services
✅ Workflow management in n8n
✅ Scheduled tasks in n8n
```

**Key Differences:**

- ❌ **Current:** Telegram → FastAPI → Python handlers → Agents → Telegram (direct)
- ✅ **Required:** Telegram → n8n → FastAPI agents → n8n → Telegram
- ❌ **Current:** All routing logic in Python
- ✅ **Required:** Routing logic in n8n workflows
- ❌ **Current:** Agents call Telegram API directly
- ✅ **Required:** Agents return JSON, n8n sends to Telegram

**This is a major architectural change that needs to be addressed!**

### ✅ Completed Components

#### 1. **Infrastructure & Foundation** (100% Complete)

- ✅ Project structure and environment setup
- ✅ Database schema with all models (Host, Property, Booking, CleaningTask, SystemLog)
- ✅ FastAPI application structure with routes
- ✅ Configuration system for hosts and properties
- ✅ Comprehensive logging system
- ✅ Telegram bot setup (both guest and host bots)
- ⚠️ Basic n8n integration (webhook endpoints exist, but **not used in main flow**)

#### 2. **Agents Implemented** (Partial)

- ✅ **Inquiry Agent** (`agents/inquiry_agent.py`) - Fully implemented
  - Handles property inquiries, availability checks
  - Detects booking intent and transitions to booking agent
  - Uses conversation context for date tracking
- ✅ **Booking Agent** (`agents/booking_agent.py`) - Fully implemented

  - Handles booking, price negotiation, payment requests
  - Manages payment screenshot collection
  - **NOTE:** Currently includes negotiation logic that needs to be removed

- ⚠️ **InquiryBookingAgent** (`agents/inquiry_booking_agent.py`) - Exists but deprecated

  - This was the original combined agent
  - Still imported in some places but not actively used
  - Can be removed

- ❌ **QnA Agent** - Not implemented
- ❌ **Host Summary Agent** - Not implemented
- ❌ **Cleaner Coordination Agent** - Not implemented (will be removed)

#### 3. **Payment Workflow** (90% Complete)

- ✅ Payment screenshot handling
- ✅ Host payment approval/rejection via host bot
- ✅ Booking confirmation after approval
- ✅ Customer details collection (name, bank)
- ⚠️ Missing: Basic info collection before payment (needs to be added)

#### 4. **Telegram Integration** (80% Complete)

- ✅ Guest bot with `/start` and `/inquiry` commands
- ✅ Host bot with payment approval
- ✅ Agent routing (InquiryAgent ↔ BookingAgent)
- ❌ Missing: `/qna` command for QnA agent
- ⚠️ Missing: Weekly summary delivery to host

#### 5. **n8n Integration** (5% Complete - **CRITICAL GAP**)

- ✅ Basic webhook endpoints exist (but not used)
- ✅ Health check endpoint
- ❌ **Telegram webhooks NOT going through n8n** (currently direct to FastAPI)
- ❌ No message routing workflows in n8n
- ❌ No Telegram Trigger nodes configured
- ❌ No HTTP Request nodes to call agent endpoints
- ❌ No scheduled triggers (pre-check-in, check-out, summaries)
- ❌ No calendar integration via n8n
- ⚠️ **Architecture is backwards - needs complete restructuring**

#### 6. **Google Calendar Integration** (0% Complete)

- ❌ Not implemented
- ⚠️ Stub exists in `api/utils/calendar.py`

---

## What Needs to Be Removed/Changed

### 0. **RESTRUCTURE ARCHITECTURE: Move to n8n-First Flow** (CRITICAL - HIGHEST PRIORITY)

**Current Flow (WRONG):**

```
Telegram → FastAPI /api/webhook/guest → handle_guest_message() → Agent → Response
```

**Required Flow (CORRECT):**

```
Telegram → n8n (Telegram Trigger) → n8n (HTTP Request to agent endpoint) → Agent → n8n → Telegram (Send Message)
```

**Changes Needed:**

1. **Remove Direct Telegram Handling from Python:**

   - ❌ Remove or deprecate `handle_guest_message()` direct agent calls
   - ❌ Remove or deprecate `handle_host_message()` direct agent calls
   - ✅ Keep webhook endpoints but make them simple passthroughs OR remove them
   - ✅ Agents should ONLY be called via HTTP endpoints (for n8n to call)

2. **Create n8n Workflows:**

   - ✅ Telegram Trigger node for guest bot
   - ✅ Telegram Trigger node for host bot
   - ✅ Message routing logic in n8n (IF/ELSE nodes)
   - ✅ HTTP Request nodes to call agent endpoints
   - ✅ Telegram Send Message nodes for responses

3. **Update Telegram Webhook Configuration:**

   - ❌ Currently: Telegram webhook → FastAPI endpoint
   - ✅ Should be: Telegram webhook → n8n webhook URL

4. **Refactor Python Code:**

   - ✅ Keep agent endpoints as pure services (no Telegram logic)
   - ✅ Remove Telegram message sending from agent handlers
   - ✅ Agents return structured responses, n8n handles Telegram communication
   - ✅ Keep utility functions (payment handling, etc.) but call from n8n

5. **Update Agent Endpoints:**
   - ✅ Ensure all agent endpoints are pure HTTP APIs
   - ✅ Accept structured JSON input
   - ✅ Return structured JSON output
   - ✅ No direct Telegram API calls in agents

### 1. **Remove Cleaner Agent & Related Code**

- ❌ Remove cleaner agent implementation (doesn't exist yet, but remove references)
- ❌ Remove `CleaningTask` model usage (or keep model but don't use it)
- ❌ Remove cleaner-related fields from Property model (or keep but ignore)
- ❌ Remove cleaner coordination endpoints from `api/routes/agents.py`
- ❌ Remove cleaner-related logging events
- ⚠️ **Decision needed:** Keep database model for future or remove completely?

### 2. **Remove Price Negotiation**

- ❌ Remove `negotiate_price()` method from BookingAgent
- ❌ Remove negotiation logic from booking flow
- ❌ Simplify to fixed rate only (base_price × nights)
- ❌ Remove min_price/max_price usage (or keep in DB but don't use)
- ❌ Update system prompts to remove negotiation mentions

### 3. **Remove Issue Handling Agent References**

- ❌ The original plan had an "Issue Handling Agent" but new plan uses QnA agent instead
- ❌ Remove any references to issue handling agent

### 4. **Clean Up Deprecated Code**

- ❌ Remove `InquiryBookingAgent` (deprecated, replaced by split agents)
- ❌ Clean up imports and references

---

## What Needs to Be Implemented

### 1. **QnA Agent** (NEW - High Priority)

**Purpose:** Answer questions from guests during their stay

**Requirements:**

- Create `agents/qna_agent.py`
- Handle FAQ questions about property (wifi, amenities, check-in/check-out times, etc.)
- Use property configuration as knowledge base
- Accessible via `/qna` command in guest bot
- Should detect if guest has active booking (optional enhancement)
- Integrate with conversation context

**Implementation Steps:**

1. Create QnAAgent class extending BaseAgent
2. Add `/qna` command handler in `api/telegram/guest_bot.py`
3. Create API endpoint `POST /api/agents/qna/process`
4. Update agent router to handle QnA requests
5. Test with sample questions

### 2. **Host Summary Agent** (NEW - Medium Priority)

**Purpose:** Generate weekly summaries for host about property performance

**Requirements:**

- Create `agents/host_summary_agent.py`
- Generate weekly reports with:
  - Booking requests vs confirmations
  - Total nights booked
  - Payment approvals/rejections
  - Guest inquiries count
- Format as readable message
- Send to host via host bot
- Trigger via n8n scheduled workflow (weekly)

**Implementation Steps:**

1. Create HostSummaryAgent class
2. Implement report generation logic using system logs
3. Create API endpoint `POST /api/agents/host-summary/weekly`
4. Add n8n workflow to trigger weekly
5. Integrate with host bot for delivery

### 3. **Basic Info Collection Before Payment** (NEW - High Priority)

**Requirements:**

- Before requesting payment, collect:
  - Guest full name
  - Number of guests
  - Contact information (optional)
- Store in booking record
- Update booking flow to request this info first

**Implementation Steps:**

1. Update BookingAgent to request basic info before payment
2. Add fields to booking context
3. Update payment request flow
4. Store info in Booking model (some fields may already exist)

### 4. **Remove Negotiation, Use Fixed Rate** (HIGH Priority)

**Requirements:**

- Simplify pricing to: `base_price × number_of_nights`
- Remove all negotiation logic
- Update system prompts
- Update booking flow

**Implementation Steps:**

1. Remove `negotiate_price()` method
2. Simplify `calculate_price()` to just multiply base_price × nights
3. Update BookingAgent system prompt
4. Remove negotiation keywords detection
5. Test booking flow

### 5. **n8n Workflow Integration** (CRITICAL - HIGHEST PRIORITY - Focus Area)

**Current State:** Architecture is backwards. Telegram goes directly to Python, n8n is not in the flow.

**Required Architecture Change:**

1. **Move Telegram webhooks to n8n** (not FastAPI)
2. **n8n becomes the orchestrator** for all message flows
3. **Python agents become services** that n8n calls

**Required Workflows:**

#### 5.1 Guest Message Router Workflow (CRITICAL - Main Entry Point)

**Flow:**

```
Telegram Trigger (Guest Bot)
  → Parse message (command, text, photo, etc.)
  → Route based on command/content:
     - /start → Send welcome message (n8n)
     - /inquiry → HTTP Request → /api/agents/inquiry/process
     - /qna → HTTP Request → /api/agents/qna/process
     - Booking intent → HTTP Request → /api/agents/booking/process
     - Photo (payment) → HTTP Request → /api/payment/handle-screenshot
  → Get agent response
  → Telegram Send Message (n8n)
```

**Implementation:**

- Telegram Trigger node (guest bot webhook)
- IF/ELSE nodes for routing
- HTTP Request nodes to FastAPI agent endpoints
- Telegram Send Message node for responses
- Error handling nodes

#### 5.2 Host Message Router Workflow (CRITICAL - Main Entry Point)

**Flow:**

```
Telegram Trigger (Host Bot)
  → Parse message (command, text)
  → Route based on command/content:
     - /start, /setup, /add_property → HTTP Request → /api/host/commands
     - Payment approval (yes/no) → HTTP Request → /api/payment/approve
     - Other → Handle in n8n or route to appropriate endpoint
  → Telegram Send Message (n8n)
```

**Implementation:**

- Telegram Trigger node (host bot webhook)
- IF/ELSE nodes for routing
- HTTP Request nodes to FastAPI endpoints
- Telegram Send Message node for responses

#### 5.3 Booking Confirmation Workflow

**Flow:**

```
Trigger: HTTP Request from Python (when booking confirmed)
  → Create Google Calendar event (n8n Google Calendar node OR HTTP to FastAPI)
  → Send confirmation message to guest (Telegram Send Message)
  → Log event (HTTP Request → /api/logs/event)
  → Trigger pre-check-in scheduling (n8n Schedule node)
```

**Implementation:**

- Webhook Trigger node (called from Python after payment approval)
- Google Calendar node (or HTTP to FastAPI calendar endpoint)
- Telegram Send Message node
- Schedule node for pre-check-in

#### 5.4 Pre-Check-in Workflow

**Flow:**

```
Trigger: Schedule (1 day before check-in)
  → Query bookings (HTTP Request → /api/bookings/upcoming-checkin)
  → For each booking:
     → Get property check-in instructions (HTTP Request → /api/properties/{id})
     → Send check-in message to guest (Telegram Send Message)
     → Log event
```

**Implementation:**

- Schedule Trigger node (Cron: daily at specific time)
- HTTP Request to get upcoming check-ins
- Loop node for multiple bookings
- Telegram Send Message node

#### 5.5 Check-out Workflow

**Flow:**

```
Trigger: Schedule (on check-out date)
  → Query bookings (HTTP Request → /api/bookings/checkout-today)
  → For each booking:
     → Get property check-out instructions (HTTP Request → /api/properties/{id})
     → Send check-out message to guest (Telegram Send Message)
     → Log event
```

**Implementation:**

- Schedule Trigger node (Cron: daily)
- HTTP Request to get check-outs
- Loop node
- Telegram Send Message node

#### 5.6 Weekly Summary Workflow

**Flow:**

```
Trigger: Schedule (Weekly, e.g., Monday 9 AM)
  → Call Host Summary Agent (HTTP Request → /api/agents/host-summary/weekly)
  → Get report from agent
  → Send to host (Telegram Send Message to host bot)
  → Log event
```

**Implementation:**

- Schedule Trigger node (Cron: weekly)
- HTTP Request to Host Summary Agent endpoint
- Telegram Send Message node

**Implementation Steps:**

1. **CRITICAL FIRST:** Change Telegram webhook URLs to point to n8n (not FastAPI)
2. Create Guest Message Router workflow in n8n
3. Create Host Message Router workflow in n8n
4. Refactor Python code to remove direct Telegram handling
5. Ensure all agent endpoints are pure HTTP APIs
6. Create booking confirmation workflow
7. Create pre-check-in workflow
8. Create check-out workflow
9. Create weekly summary workflow
10. Test end-to-end flows
11. Document workflow structure

### 6. **Google Calendar Integration** (Medium Priority)

**Requirements:**

- When booking confirmed, create calendar event
- Store event ID in booking record
- Include: property name, guest name, dates, times

**Implementation Steps:**

1. Set up Google Calendar API credentials
2. Implement `create_calendar_event()` in `api/utils/calendar.py`
3. Integrate with booking confirmation flow
4. Call from n8n workflow or directly from Python
5. Test event creation

### 7. **Host Bot Enhancements** (Medium Priority)

**Requirements:**

- Weekly summary delivery (via Host Summary Agent)
- Property setup improvements (if needed)
- Payment method configuration (if not already done)

**Current State:** Host bot handles payment approvals and basic setup commands.

---

## Implementation Priority Order

### Phase 0: Architecture Restructure (CRITICAL - Do First!)

1. ✅ **Change Telegram webhook URLs to point to n8n** (not FastAPI)
2. ✅ Create Guest Message Router workflow in n8n
3. ✅ Create Host Message Router workflow in n8n
4. ✅ Refactor Python code: Remove direct Telegram handling from agents
5. ✅ Ensure agent endpoints are pure HTTP APIs (no Telegram calls)
6. ✅ Test basic message flow: Telegram → n8n → Agent → n8n → Telegram

### Phase 1: Core Functionality (After Architecture Fix)

7. ✅ Remove negotiation logic, use fixed rate
8. ✅ Add basic info collection before payment
9. ✅ Create QnA agent with `/qna` command
10. ✅ Clean up deprecated code (InquiryBookingAgent, cleaner references)

### Phase 2: n8n Workflows (Continue n8n Integration)

11. ✅ Create booking confirmation workflow (with calendar)
12. ✅ Create pre-check-in workflow
13. ✅ Create check-out workflow

### Phase 3: Summary & Polish

14. ✅ Create Host Summary Agent
15. ✅ Create weekly summary n8n workflow
16. ✅ Test end-to-end flows
17. ✅ Update documentation

---

## Key Differences from Original Plan

| Original Plan                      | New Plan                              | Status                        |
| ---------------------------------- | ------------------------------------- | ----------------------------- |
| Inquiry & Booking Agent (combined) | Inquiry Agent + Booking Agent (split) | ✅ Done (already split)       |
| Price negotiation                  | Fixed rate only                       | ❌ Needs change               |
| Cleaner Coordination Agent         | **Removed**                           | ✅ Not implemented, will skip |
| Issue Handling Agent               | QnA Agent (simpler)                   | ❌ Needs implementation       |
| Host Summary Agent                 | Host Summary Agent (weekly only)      | ❌ Needs implementation       |
| n8n integration (later)            | **n8n integration NOW**               | ❌ Needs implementation       |
| Basic info before payment          | **Required**                          | ❌ Needs implementation       |

---

## Database Schema Status

### Models That Exist:

- ✅ `Host` - Complete
- ✅ `Property` - Complete (has cleaner fields, can ignore)
- ✅ `Booking` - Complete (has all needed fields)
- ✅ `CleaningTask` - Exists but won't be used
- ✅ `SystemLog` - Complete

### Fields That May Need Addition:

- ⚠️ Check if `Booking` has all fields for basic info (name, guests, contact)
- ⚠️ Verify payment method storage in `Host` model

---

## Testing Checklist

### Guest Flow:

- [ ] `/start` command works
- [ ] `/inquiry` command works
- [ ] `/qna` command works
- [ ] Inquiry about availability
- [ ] Booking with fixed rate (no negotiation)
- [ ] Basic info collection
- [ ] Payment screenshot upload
- [ ] Payment approval notification

### Host Flow:

- [ ] Payment approval/rejection
- [ ] Weekly summary receipt
- [ ] Property setup (if needed)

### n8n Workflows:

- [ ] Message routing works
- [ ] Booking confirmation triggers calendar event
- [ ] Pre-check-in message sent
- [ ] Check-out message sent
- [ ] Weekly summary generated and sent

---

## Files That Need Modification

### CRITICAL - Architecture Restructure (Do First!):

1. `api/telegram/guest_bot.py` - **REFACTOR**: Remove direct agent calls, make it a simple service or remove
2. `api/telegram/host_bot.py` - **REFACTOR**: Remove direct agent calls, make it a simple service or remove
3. `api/routes/telegram.py` - **REFACTOR**: Either remove webhook endpoints OR make them passthroughs to n8n
4. `n8n_workflows/guest-message-router.json` - **CREATE NEW** - Main guest message workflow
5. `n8n_workflows/host-message-router.json` - **CREATE NEW** - Main host message workflow
6. Agent endpoints - **VERIFY**: Ensure they don't call Telegram API directly, only return JSON

### High Priority (After Architecture Fix):

7. `agents/booking_agent.py` - Remove negotiation, add basic info collection
8. `agents/qna_agent.py` - **CREATE NEW**
9. `agents/host_summary_agent.py` - **CREATE NEW**
10. `api/routes/agents.py` - Add QnA and Host Summary endpoints
11. `n8n_workflows/booking-confirmation.json` - **CREATE NEW**
12. `n8n_workflows/pre-checkin.json` - **CREATE NEW**
13. `n8n_workflows/checkout.json` - **CREATE NEW**
14. `n8n_workflows/weekly-summary.json` - **CREATE NEW**

### Medium Priority:

7. `api/utils/calendar.py` - Implement Google Calendar integration
8. `api/telegram/host_bot.py` - Add weekly summary handling
9. `api/utils/agent_router.py` - Add QnA routing

### Cleanup:

10. `agents/inquiry_booking_agent.py` - **DELETE** (deprecated)
11. `api/routes/agents.py` - Remove cleaner coordination endpoints
12. Remove cleaner-related code references

---

## Estimated Remaining Work

### Architecture Restructure (CRITICAL):

- **Move Telegram webhooks to n8n:** 2-3 hours
- **Create Guest Message Router workflow:** 3-4 hours
- **Create Host Message Router workflow:** 2-3 hours
- **Refactor Python code (remove Telegram handling):** 2-3 hours
- **Test new architecture:** 1-2 hours

### Core Functionality:

- **QnA Agent:** 2-3 hours
- **Host Summary Agent:** 3-4 hours
- **Remove Negotiation:** 1-2 hours
- **Basic Info Collection:** 1-2 hours

### n8n Workflows (Additional):

- **Booking Confirmation workflow:** 1-2 hours
- **Pre-Check-in workflow:** 1-2 hours
- **Check-out workflow:** 1-2 hours
- **Weekly Summary workflow:** 1 hour

### Other:

- **Google Calendar Integration:** 2-3 hours
- **Testing & Bug Fixes:** 3-4 hours
- **Documentation Updates:** 1-2 hours

**Total Estimated Time:** 28-40 hours (3.5-5 days of focused work)

**With 1 day available:**

- **MUST DO:** Phase 0 (Architecture restructure) - 8-12 hours
- **Then:** Phase 1 core functionality (QnA, remove negotiation) - 4-6 hours
- **Defer:** Host Summary, scheduled workflows, calendar (can be done later)

---

## Notes

1. **n8n-First Architecture (CRITICAL):** The user emphasized that "currently the code runs through python code but it should be mostly on n8n". This means:

   - Telegram webhooks MUST go to n8n first (not FastAPI)
   - n8n should orchestrate all message flows
   - Python agents should be pure HTTP services
   - This is the **highest priority** architectural change

2. **Fixed Rate:** The user wants to "remove the negotiation part" and use "just a fix rate", so this is a critical change.

3. **Basic Info:** User mentioned "before we book or go to payment, the customer must also provide basic info for booking" - this needs to be added.

4. **QnA Agent:** Should be accessible via `/qna` command, similar to how `/inquiry` works currently.

5. **Weekly Summaries:** Host should receive weekly summaries about their property - this is a key feature that needs implementation.

6. **Cleaner Agent:** Completely removed from scope - any existing references should be cleaned up but database models can stay for future use.

7. **Current Architecture Problem:** The system currently has Telegram webhooks going directly to FastAPI, which bypasses n8n entirely. This needs to be completely restructured so n8n is the main orchestrator.

---

## Next Steps

1. **URGENT:** Review this document with the user
2. **URGENT:** Confirm the architecture change (n8n-first approach)
3. **Start with Phase 0:** Restructure architecture to use n8n as orchestrator
   - Change Telegram webhook URLs to point to n8n
   - Create message router workflows in n8n
   - Refactor Python code to remove direct Telegram handling
4. **Then Phase 1:** Core functionality changes (remove negotiation, add QnA)
5. **Then Phase 2:** Additional n8n workflows (scheduled tasks)
6. **Finally Phase 3:** Summary and polish

## Architecture Migration Checklist

### Step 1: Set Up n8n Workflows

- [ ] Create Guest Message Router workflow in n8n
- [ ] Create Host Message Router workflow in n8n
- [ ] Test workflows can receive Telegram webhooks
- [ ] Test workflows can call FastAPI endpoints
- [ ] Test workflows can send Telegram messages

### Step 2: Change Telegram Webhook URLs

- [ ] Update Guest Bot webhook URL to n8n webhook URL
- [ ] Update Host Bot webhook URL to n8n webhook URL
- [ ] Verify webhooks are working in n8n

### Step 3: Refactor Python Code

- [ ] Remove direct Telegram API calls from agent handlers
- [ ] Ensure agent endpoints only return JSON (no Telegram sending)
- [ ] Update `handle_guest_message()` to be a service (or remove)
- [ ] Update `handle_host_message()` to be a service (or remove)
- [ ] Keep utility functions but make them callable from n8n

### Step 4: Test End-to-End

- [ ] Test guest message flow: Telegram → n8n → Agent → n8n → Telegram
- [ ] Test host message flow: Telegram → n8n → Service → n8n → Telegram
- [ ] Test payment approval flow
- [ ] Test booking confirmation flow

### Step 5: Create Additional Workflows

- [ ] Booking confirmation workflow
- [ ] Pre-check-in workflow
- [ ] Check-out workflow
- [ ] Weekly summary workflow
