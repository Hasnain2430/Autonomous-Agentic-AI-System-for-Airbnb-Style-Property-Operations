# Project Implementation Summary

This document confirms our understanding of what we're building together. Please review to ensure we're on the same page before we start implementation.

---

## 🎯 Project Overview

We're building an **Autonomous Airbnb Property Operations Manager** - a multi-agent system that manages digital operations for up to 3 Airbnb-style properties. The system will handle guest interactions, bookings, payments, cleaning coordination, issue resolution, and calendar management autonomously.

---

## 🛠️ Technology Stack

### Core Technologies
- **Programming Language:** Python
- **Agent Framework:** LangChain/LangGraph
- **LLM Provider:** Qwen (API key and code snippet to be provided later)
- **API Framework:** FastAPI (for REST endpoints that n8n will call)
- **Database:** SQLite (for host config, properties, bookings, logs)
- **Workflow Engine:** n8n (self-hosted, already set up)
- **Chat Platform:** Telegram (two separate bots)

### Storage
- **Database:** SQLite for:
  - Host configuration
  - Property details (including cleaner information)
  - Booking records
  - System logs (all actions/events)
- **Files:** Local folder for property photos (file paths stored in database)

---

## 🤖 Agents to Implement

We will implement **ALL 4 agents** from the project description:

### 1. Inquiry and Booking Agent
- Handles guest inquiries about availability, price, property details
- Checks date availability based on property rules
- Negotiates price within host-defined min/max range
- Guides booking process and payment collection
- Requests payment screenshot from guest
- Sends payment details to host for verification
- Confirms booking after host approval
- Triggers follow-up actions (calendar, cleaning)

### 2. Issue Handling Agent
- Receives messages during active guest stays
- Classifies issues:
  - FAQ/simple questions → direct answers
  - Cleaning/missing items → forwards to Cleaner Coordination Agent
  - Urgent/serious → escalates to host
- Responds to guests about issue resolution

### 3. Cleaner Coordination Agent
- Schedules cleaning tasks:
  - Before check-in (if needed)
  - After check-out
- Handles cleanliness issues during stays
- Sends cleaning requests to cleaner via Telegram
- Receives cleaner confirmation ("okay will clean")
- Updates system when cleaner reports completion
- Notifies host if cleaning cannot be scheduled

### 4. Host Summary Agent
- Generates weekly and monthly reports
- Uses system logs to gather events
- Groups information by property
- Reports include:
  - Booking requests vs confirmations
  - Nights booked vs free
  - Issues reported and resolutions
  - Escalations to host
  - Cleaning tasks scheduled/completed
  - Failures/unusual patterns
- Formats as readable messages (PDF optional)

---

## 💬 Telegram Bots Setup

### Two Separate Bots

#### 1. Guest Bot
- **Purpose:** Guest interactions (inquiries, bookings, issues)
- **Features:**
  - Receives guest messages
  - Sends agent responses
  - Receives payment screenshots
  - Sends booking confirmations
  - Sends check-in/check-out instructions

#### 2. Host Bot
- **Purpose:** Host communication and property setup
- **Features:**
  - Initial property configuration (host info, property details, images)
  - Payment verification requests (screenshot + approval prompt)
  - Escalation alerts for urgent issues
  - Summary reports (weekly/monthly)
  - Cleaner assignment notifications (if needed)

**Note:** Creating Telegram bots is completely free via BotFather. We'll provide step-by-step instructions for bot creation.

---

## 🔄 Key Workflows

### Booking Flow
1. Guest asks about availability → Inquiry Agent responds
2. Guest wants to book → Agent calculates price, explains process
3. Guest uploads payment screenshot → Agent forwards to host via host bot
4. Host reviews and approves/rejects via host bot
5. If approved:
   - Booking confirmed
   - Google Calendar event created
   - Cleaning scheduled (before check-in, after check-out)
   - Confirmation sent to guest
6. Pre-check-in: Instructions sent to guest
7. During stay: Issue Handling Agent manages problems
8. Check-out: Instructions sent, post-checkout cleaning scheduled

### Payment Verification
- Guest sends screenshot via guest Telegram bot
- System forwards screenshot to host via host Telegram bot
- Host replies "yes" or "no" via host bot
- System processes approval/rejection

### Cleaning Coordination
- Cleaner details stored in property configuration
- System sends cleaning request to cleaner via Telegram
- Cleaner auto-replies "okay will clean"
- Cleaner updates system when cleaning is complete
- System logs all cleaning activities

---

## 📅 Google Calendar Integration

- **Calendar Type:** New calendar specifically for property bookings
- **Multi-Host Support:** Each host's credentials stored in configuration
- **Events Created:** When booking is confirmed
- **Event Details:**
  - Property name
  - Guest name/identifier
  - Start/end dates and times
  - Payment status
  - Special notes

---

## 🗄️ Data Structure

### Host Configuration
- Name, email, phone/messaging handle
- Preferred language
- Google Calendar credentials

### Property Configuration (per property)
- Property identifier, name, location
- Base nightly price
- Min/max negotiation range
- Max guests
- Check-in/check-out times
- Cleaning rules
- Check-in/check-out instruction templates
- Property photos (file paths)
- Cleaner details (Telegram handle/ID)

### Booking Records
- Guest information
- Property ID
- Dates
- Price
- Payment status
- Confirmation status
- Related cleaning tasks

### System Logs
- All guest messages
- Agent decisions
- Booking confirmations/cancellations
- Cleaning tasks scheduled/completed
- Escalations to host
- Calendar events created
- Issue resolutions

---

## 🔌 n8n Integration

### Architecture
- **Agents:** Python FastAPI endpoints
- **n8n:** Calls agent endpoints via HTTP Request nodes
- **Communication:** HTTP webhooks (agents expose REST API)
- **Workflow Management:** n8n handles:
  - Message routing
  - Timeline management (pre-check-in, check-out triggers)
  - Calendar integration
  - Periodic summary generation
  - Logging coordination

---

## 🔒 Security

- **API Keys:** Stored in environment variables
- **Enhanced Security:** Where possible and easy to implement
- **Payment Screenshots:** Securely handled (stored temporarily for host review)

---

## 📁 Project Structure

```
Project/
├── docs/                          # Documentation
│   ├── project Description.md
│   ├── questions.md
│   ├── project-summary.md
│   └── plan.md (to be created)
├── agents/                        # Agent implementations
│   ├── inquiry_booking_agent.py
│   ├── issue_handling_agent.py
│   ├── cleaner_coordination_agent.py
│   └── host_summary_agent.py
├── api/                           # FastAPI application
│   ├── main.py
│   ├── routes/
│   └── models/
├── database/                      # Database and migrations
│   ├── db.py
│   └── models.py
├── config/                        # Configuration files
│   └── properties.json (optional, if needed)
├── storage/                       # File storage
│   ├── photos/                   # Property photos
│   └── payment_screenshots/       # Temporary payment images
├── n8n_workflows/                 # n8n workflow exports (optional)
├── tests/                         # Test scripts
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⏱️ Implementation Timeline

**Total Time:** 2 days

**Scope:** Full implementation of all features from project description:
- All 4 agents
- Telegram bot integration (both bots)
- Google Calendar integration
- Payment verification workflow
- Cleaning coordination
- Issue handling
- Host summary reports
- n8n workflow integration
- Database setup
- Testing scenarios

---

## 🧪 Testing Approach

We will create:
- **Test Scenarios:** Scripted conversations covering:
  - Normal booking flow
  - Payment approval/rejection
  - Multiple booking requests
  - Price negotiation
  - Issue handling (FAQ, cleaning, urgent)
  - Cleaning coordination
  - Edge cases and failures
- **Test Results:** Metrics and logs that can be used in your report:
  - Booking request vs confirmation rates
  - Response times
  - Issue resolution rates
  - System behavior documentation

---

## ✅ Confirmation Checklist

Before we proceed, please confirm:

- [ ] You understand we're implementing the FULL project (all 4 agents, all features)
- [ ] You're okay with the 2-day timeline (we'll work efficiently)
- [ ] You'll provide Qwen API key and code snippet when needed
- [ ] You'll create Telegram account and we'll help with bot creation
- [ ] You'll provide Google Calendar credentials
- [ ] You understand the two-bot architecture (guest + host)
- [ ] You're ready to provide property/cleaner details during setup
- [ ] You understand SQLite database will store all data locally

---

## 🚀 Next Steps

1. **You confirm this summary is correct**
2. **We create the detailed implementation plan** (`plan.md`)
3. **We start building!**

---

## 📝 Notes

- **Property Photos:** Stored as file paths in local folder, referenced in database
- **Cleaner Simulation:** Simple - cleaner receives Telegram message, auto-replies "okay will clean", updates when done
- **Host Summary:** Will generate reports even though you said to skip initially - but you clarified you want full implementation
- **n8n:** Already set up, we'll integrate with it
- **Documentation:** Multiple READMEs during development, comprehensive docs at the end

---

**Please review this summary and let me know if anything needs clarification or adjustment!**

