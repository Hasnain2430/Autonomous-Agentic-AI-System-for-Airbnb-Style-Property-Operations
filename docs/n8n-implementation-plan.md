# Simple n8n Implementation Plan

## Goal
Move the system to use n8n as the main orchestrator. Keep it simple and working.

---

## Current Problem
- Telegram messages go directly to Python FastAPI
- Python handles everything (routing, agents, Telegram responses)
- n8n is not being used

## Solution
- Telegram messages go to n8n first
- n8n routes to Python agent endpoints
- n8n sends responses back to Telegram
- Python agents just return JSON (no Telegram calls)

---

## Step-by-Step Implementation

### Step 1: Set Up n8n Telegram Triggers (30 minutes)

**What to do:**
1. Open n8n
2. Create new workflow: "Guest Bot Router"
3. Add "Telegram Trigger" node
4. Configure with Guest Bot token
5. Test: Send a message to guest bot, see if n8n receives it

**Result:** n8n receives Telegram messages from guest bot

---

### Step 2: Create Guest Message Router in n8n (1-2 hours)

**What to do:**
1. After Telegram Trigger node, add "IF" node
2. Check if message is a command (`/start`, `/inquiry`, `/qna`)
3. For each command, route to appropriate endpoint:
   - `/start` → Send welcome message (n8n Telegram node)
   - `/inquiry` → HTTP Request to `http://192.168.100.11:8000/api/agents/inquiry/process`
   - `/qna` → HTTP Request to `http://192.168.100.11:8000/api/agents/qna/process`
   - Regular message → HTTP Request to inquiry or booking agent
4. After HTTP Request, add Telegram Send Message node
5. Send agent response back to guest

**Workflow Structure:**
```
Telegram Trigger
  ↓
IF (is /start?)
  YES → Telegram Send Message (welcome)
  NO → IF (is /inquiry?)
    YES → HTTP Request → /api/agents/inquiry/process → Telegram Send Message
    NO → IF (is /qna?)
      YES → HTTP Request → /api/agents/qna/process → Telegram Send Message
      NO → HTTP Request → /api/agents/inquiry/process → Telegram Send Message
```

**Result:** Guest messages are routed through n8n to agents

---

### Step 3: Update Telegram Webhook URL (10 minutes)

**What to do:**
1. Get n8n webhook URL for Guest Bot Router workflow
2. Update Telegram bot webhook:
   ```
   https://api.telegram.org/bot<GUEST_BOT_TOKEN>/setWebhook?url=<n8n_webhook_url>
   ```
3. Remove old FastAPI webhook URL
4. Test: Send message to bot, verify it goes through n8n

**Result:** Telegram sends messages to n8n instead of FastAPI

---

### Step 4: Refactor Python Agents (1 hour)

**What to do:**
1. Check agent endpoints in `api/routes/agents.py`
2. Ensure they:
   - Accept JSON input: `{message, guest_telegram_id, property_id, conversation_history}`
   - Return JSON output: `{response, action, metadata}`
   - Do NOT call Telegram API directly
3. Remove any Telegram API calls from agent code
4. Test endpoints directly with HTTP requests

**Result:** Agents are pure HTTP services

---

### Step 5: Handle Payment Screenshots in n8n (1 hour)

**What to do:**
1. In Guest Router workflow, add check for photos
2. If photo received:
   - HTTP Request to `http://192.168.100.11:8000/api/payment/handle-screenshot`
   - Send confirmation message via Telegram
3. Test with a payment screenshot

**Result:** Payment screenshots handled through n8n

---

### Step 6: Create Host Bot Router in n8n (1 hour)

**What to do:**
1. Create new workflow: "Host Bot Router"
2. Add Telegram Trigger for Host Bot
3. Route messages:
   - Payment approval (yes/no) → HTTP Request to `/api/payment/approve`
   - Commands (/setup, /add_property) → HTTP Request to appropriate endpoint
4. Send responses via Telegram
5. Update Host Bot webhook URL to n8n

**Result:** Host messages go through n8n

---

### Step 7: Create Booking Confirmation Workflow (30 minutes)

**What to do:**
1. Create workflow: "Booking Confirmed"
2. Add Webhook Trigger node
3. When called (from Python after payment approval):
   - Create Google Calendar event (or HTTP to FastAPI)
   - Send confirmation to guest via Telegram
   - Log event
4. In Python payment approval code, call this n8n webhook

**Result:** Booking confirmations trigger calendar and notifications

---

### Step 8: Create Pre-Check-in Workflow (30 minutes)

**What to do:**
1. Create workflow: "Pre-Check-in Reminder"
2. Add Schedule Trigger (daily at 9 AM)
3. HTTP Request to get bookings with check-in tomorrow
4. For each booking:
   - Get property check-in instructions
   - Send message to guest via Telegram
5. Activate workflow

**Result:** Guests get check-in reminders automatically

---

### Step 9: Create Check-out Workflow (30 minutes)

**What to do:**
1. Create workflow: "Check-out Reminder"
2. Add Schedule Trigger (daily at 9 AM)
3. HTTP Request to get bookings checking out today
4. For each booking:
   - Get property check-out instructions
   - Send message to guest via Telegram
5. Activate workflow

**Result:** Guests get check-out reminders automatically

---

### Step 10: Create Weekly Summary Workflow (30 minutes)

**What to do:**
1. Create workflow: "Weekly Summary"
2. Add Schedule Trigger (weekly, Monday 9 AM)
3. HTTP Request to `/api/agents/host-summary/weekly`
4. Get report from agent
5. Send to host via Telegram
6. Activate workflow

**Result:** Host gets weekly summaries automatically

---

## Quick Reference: n8n Workflows Needed

1. **Guest Bot Router** - Routes guest messages to agents
2. **Host Bot Router** - Routes host messages to services
3. **Booking Confirmed** - Handles booking confirmation actions
4. **Pre-Check-in Reminder** - Sends check-in instructions
5. **Check-out Reminder** - Sends check-out instructions
6. **Weekly Summary** - Sends weekly reports to host

---

## Python Endpoints Needed (for n8n to call)

### Agent Endpoints:
- `POST /api/agents/inquiry/process` - Handle inquiries
- `POST /api/agents/booking/process` - Handle bookings
- `POST /api/agents/qna/process` - Handle QnA (to be created)
- `POST /api/agents/host-summary/weekly` - Generate weekly report (to be created)

### Service Endpoints:
- `POST /api/payment/handle-screenshot` - Process payment screenshot
- `POST /api/payment/approve` - Approve/reject payment
- `GET /api/bookings/upcoming-checkin` - Get bookings checking in tomorrow
- `GET /api/bookings/checkout-today` - Get bookings checking out today
- `GET /api/properties/{id}` - Get property details

---

## Testing Checklist

### Basic Flow:
- [ ] Send message to guest bot → n8n receives it
- [ ] n8n routes to agent endpoint
- [ ] Agent returns response
- [ ] n8n sends response to guest
- [ ] Guest receives message

### Commands:
- [ ] `/start` works
- [ ] `/inquiry` works
- [ ] `/qna` works (after creating QnA agent)

### Payment:
- [ ] Upload payment screenshot → n8n handles it
- [ ] Host approves payment → booking confirmed
- [ ] Guest receives confirmation

### Scheduled:
- [ ] Pre-check-in message sent (test with manual trigger)
- [ ] Check-out message sent (test with manual trigger)
- [ ] Weekly summary sent (test with manual trigger)

---

## Important Notes

1. **Keep it simple:** n8n handles routing and Telegram, Python handles logic
2. **No Telegram calls in Python:** All Telegram communication via n8n
3. **Test each step:** Don't move to next step until current one works
4. **Use HTTP Request nodes:** n8n calls FastAPI endpoints
5. **Error handling:** Add error nodes in n8n workflows

---

## Time Estimate

- Step 1: 30 min
- Step 2: 1-2 hours
- Step 3: 10 min
- Step 4: 1 hour
- Step 5: 1 hour
- Step 6: 1 hour
- Step 7: 30 min
- Step 8: 30 min
- Step 9: 30 min
- Step 10: 30 min

**Total: 6-8 hours** (can be done in one day)

---

## Priority Order

**Must Do First:**
1. Step 1-3: Get basic message flow working (n8n receives, routes, responds)
2. Step 4: Ensure Python agents work as HTTP services
3. Step 5-6: Handle payments and host messages

**Can Do Later:**
4. Step 7-10: Scheduled workflows (can test manually first)

---

## Troubleshooting

**Problem:** n8n not receiving Telegram messages
- Check webhook URL is correct
- Verify Telegram bot token in n8n
- Check n8n workflow is active

**Problem:** Agent endpoint not responding
- Check FastAPI is running
- Verify endpoint URL in n8n HTTP Request node
- Check request format matches what agent expects

**Problem:** Response not sent to Telegram
- Check Telegram Send Message node is configured
- Verify bot token in n8n
- Check node execution in n8n

---

## Next Steps After This Works

1. Remove negotiation logic (use fixed rate)
2. Add QnA agent
3. Add basic info collection before payment
4. Add Host Summary agent
5. Clean up deprecated code

But first, get n8n working as the orchestrator!

