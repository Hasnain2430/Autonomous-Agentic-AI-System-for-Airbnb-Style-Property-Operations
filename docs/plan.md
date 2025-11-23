# Detailed Implementation Plan

This document provides a step-by-step plan to build the Autonomous Airbnb Property Operations Manager. Each step builds on the previous one, allowing us to test and verify as we go.

---

## 📋 Overview

**Total Steps:** 17 major steps
**Estimated Time:** 2 days
**Approach:** Hybrid incremental development - infrastructure first, then testable components with immediate testing capability

---

## Step 1: Project Foundation & Environment Setup

### 1.1 Create Project Structure

```
Project/
├── agents/
├── api/
│   ├── routes/
│   └── models/
├── database/
├── config/
├── storage/
│   ├── photos/
│   └── payment_screenshots/
├── n8n_workflows/
├── tests/
├── docs/
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

### 1.2 Create Virtual Environment

- Create Python virtual environment
- Activate it

### 1.3 Install Core Dependencies

Create `requirements.txt` with:

- `fastapi` - API framework
- `uvicorn` - ASGI server
- `python-telegram-bot` - Telegram bot library
- `langchain` - Agent framework
- `langgraph` - Agent orchestration
- `sqlalchemy` - Database ORM
- `python-dotenv` - Environment variables
- `pydantic` - Data validation
- `google-api-python-client` - Google Calendar API
- `google-auth-httplib2` - Google auth
- `google-auth-oauthlib` - Google OAuth
- `aiofiles` - Async file operations
- `python-multipart` - File uploads

### 1.4 Create Environment File Template

Create `.env.example` with placeholders:

- `QWEN_API_KEY=`
- `QWEN_API_ENDPOINT=`
- `GUEST_BOT_TOKEN=`
- `HOST_BOT_TOKEN=`
- `GOOGLE_CALENDAR_CREDENTIALS_PATH=`
- `DATABASE_PATH=./database/properties.db`
- `HOST_TELEGRAM_ID=`
- `API_HOST=localhost`
- `API_PORT=8000`

### 1.5 Initialize Git (Optional)

- Create `.gitignore`
- Initialize repository

**Deliverable:** Project structure ready, dependencies installed, environment configured

---

## Step 2: Database Schema & Models

### 2.1 Design Database Schema

Create SQLite database with tables:

**hosts**

- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `email` (TEXT)
- `phone` (TEXT)
- `telegram_id` (TEXT UNIQUE)
- `preferred_language` (TEXT)
- `google_calendar_id` (TEXT)
- `google_credentials_path` (TEXT)
- `created_at` (TIMESTAMP)

**properties**

- `id` (INTEGER PRIMARY KEY)
- `host_id` (INTEGER, FOREIGN KEY)
- `property_identifier` (TEXT UNIQUE)
- `name` (TEXT)
- `location` (TEXT)
- `base_price` (REAL)
- `min_price` (REAL)
- `max_price` (REAL)
- `max_guests` (INTEGER)
- `check_in_time` (TEXT)
- `check_out_time` (TEXT)
- `cleaning_rules` (TEXT)
- `check_in_template` (TEXT)
- `check_out_template` (TEXT)
- `photo_paths` (TEXT) - JSON array of paths
- `cleaner_telegram_id` (TEXT)
- `cleaner_name` (TEXT)
- `created_at` (TIMESTAMP)

**bookings**

- `id` (INTEGER PRIMARY KEY)
- `property_id` (INTEGER, FOREIGN KEY)
- `guest_telegram_id` (TEXT)
- `guest_name` (TEXT)
- `check_in_date` (DATE)
- `check_out_date` (DATE)
- `number_of_nights` (INTEGER)
- `number_of_guests` (INTEGER)
- `requested_price` (REAL)
- `final_price` (REAL)
- `payment_status` (TEXT) - 'pending', 'approved', 'rejected'
- `payment_screenshot_path` (TEXT)
- `booking_status` (TEXT) - 'pending', 'confirmed', 'cancelled'
- `calendar_event_id` (TEXT)
- `created_at` (TIMESTAMP)
- `confirmed_at` (TIMESTAMP)

**cleaning_tasks**

- `id` (INTEGER PRIMARY KEY)
- `property_id` (INTEGER, FOREIGN KEY)
- `booking_id` (INTEGER, FOREIGN KEY, nullable)
- `task_type` (TEXT) - 'pre_checkin', 'post_checkout', 'during_stay'
- `scheduled_date` (DATE)
- `scheduled_time` (TIME)
- `status` (TEXT) - 'scheduled', 'in_progress', 'completed', 'cancelled'
- `cleaner_notified_at` (TIMESTAMP)
- `cleaner_confirmed_at` (TIMESTAMP)
- `completed_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)

**system_logs**

- `id` (INTEGER PRIMARY KEY)
- `event_type` (TEXT) - 'guest_message', 'agent_decision', 'booking_confirmed', 'cleaning_scheduled', 'issue_escalated', etc.
- `property_id` (INTEGER, FOREIGN KEY, nullable)
- `booking_id` (INTEGER, FOREIGN KEY, nullable)
- `agent_name` (TEXT)
- `message` (TEXT)
- `metadata` (TEXT) - JSON string
- `created_at` (TIMESTAMP)

### 2.2 Create Database Models

Create `database/models.py`:

- SQLAlchemy models for all tables
- Relationships between models
- Helper methods for common queries

### 2.3 Create Database Initialization

Create `database/db.py`:

- Database connection setup
- Table creation function
- Database session management

### 2.4 Test Database

- Create test script to verify schema
- Insert sample data
- Test queries

**Deliverable:** Database schema created, models defined, database initialized and tested

---

## Step 3: FastAPI Application Structure

### 3.1 Create Main FastAPI App

Create `api/main.py`:

- FastAPI app instance
- CORS configuration
- Health check endpoint
- API router mounting

### 3.2 Create API Routes Structure

Create route files in `api/routes/`:

- `__init__.py`
- `agents.py` - Agent endpoints
- `telegram.py` - Telegram webhook endpoints
- `bookings.py` - Booking management
- `properties.py` - Property management
- `health.py` - Health checks

### 3.3 Create Request/Response Models

Create `api/models/`:

- `schemas.py` - Pydantic models for requests/responses
- Request models for each agent
- Response models

### 3.4 Create Utility Functions

Create `api/utils/`:

- `logging.py` - System logging utilities
- `telegram.py` - Telegram message sending helpers
- `calendar.py` - Google Calendar helpers (stub for now)

### 3.5 Test FastAPI Server

- Start server with `uvicorn`
- Test health endpoint
- Verify CORS

**Deliverable:** FastAPI application structure ready, basic endpoints working

---

## Step 4: Configuration System & Initial Setup

### 5.1 Create Configuration Manager

Create `config/config_manager.py`:

- Load/save host configuration
- Load/save property configuration
- Validate configuration data

### 5.2 Create Host Setup Flow

**Host Bot Command: `/setup`**

1. Prompt for host name
2. Prompt for email
3. Prompt for phone
4. Prompt for Google Calendar credentials (file upload or path)
5. Save to database

### 5.3 Create Property Setup Flow

**Host Bot Command: `/add_property`**

1. Prompt for property identifier
2. Prompt for property name
3. Prompt for location
4. Prompt for base price, min price, max price
5. Prompt for max guests
6. Prompt for check-in/check-out times
7. Prompt for cleaning rules
8. Prompt for check-in template
9. Prompt for check-out template
10. Prompt for property photos (multiple file uploads)
11. Prompt for cleaner Telegram ID and name
12. Save to database

### 5.4 Create Configuration API Endpoints

In `api/routes/properties.py`:

- `GET /properties` - List all properties
- `GET /properties/{id}` - Get property details
- `POST /properties` - Create property (via API, for testing)
- `GET /host` - Get host configuration

### 5.5 Test Configuration

- Use host bot to set up host info
- Add a test property
- Verify data in database
- Test API endpoints

**Deliverable:** Configuration system working, host can set up properties via Telegram

---

## Step 5: System Logging Infrastructure

### 6.1 Create Logging Service

Create `api/utils/logging.py`:

- `log_event()` function
- Event type constants
- Metadata handling
- Database logging

### 6.2 Integrate Logging Throughout

- Add logging to Telegram handlers
- Add logging to agent calls
- Add logging to booking operations
- Add logging to cleaning operations

### 6.3 Create Log Query Functions

- Get logs by property
- Get logs by date range
- Get logs by event type
- Get logs for summary generation

### 6.4 Test Logging

- Trigger various events
- Verify logs in database
- Test log queries

**Deliverable:** Comprehensive logging system working, all events logged

---

## Step 6: Telegram Bot Setup & Basic Integration

### 6.1 Create Telegram Bots

**Instructions for user:**

1. Create Telegram account (if not done)
2. Contact @BotFather on Telegram
3. Create guest bot: `/newbot` → follow prompts
4. Create host bot: `/newbot` → follow prompts
5. Get bot tokens for both bots
6. Add tokens to `.env`

### 6.2 Create Telegram Bot Handlers

Create `api/telegram/`:

- `guest_bot.py` - Guest bot handler
- `host_bot.py` - Host bot handler
- `base.py` - Shared utilities

### 6.3 Implement Basic Message Handling

**Guest Bot:**

- Echo messages (for testing)
- Log all messages
- Store guest Telegram ID
- Route messages to configuration system (for property setup testing)

**Host Bot:**

- Echo messages (for testing)
- Log all messages
- Store host Telegram ID
- Handle configuration commands (`/setup`, `/add_property`)

### 6.4 Create Webhook Endpoints

In `api/routes/telegram.py`:

- `/webhook/guest` - Guest bot webhook
- `/webhook/host` - Host bot webhook
- Webhook verification
- Message parsing

### 6.5 Test Telegram Bots

- Send test messages to both bots
- Verify webhooks receive messages
- Test configuration via host bot
- Check database logging

**Deliverable:** Both Telegram bots created, webhooks configured, basic message handling working, can test configuration flow

---

## Step 7: n8n Basic Integration Setup

### 7.1 Set Up Basic n8n Connection

- Verify n8n is running and accessible
- Test HTTP connection from n8n to FastAPI
- Create basic webhook endpoint for n8n to call
- Test webhook from n8n

### 7.2 Create Simple Test Workflow

**Basic Message Router Workflow:**

1. Telegram trigger node (for testing)
2. HTTP Request node → FastAPI health endpoint
3. Test response handling

### 7.3 Create Webhook Endpoints for n8n

In `api/routes/`:

- `POST /webhooks/n8n/message` - Receive messages from n8n
- `POST /webhooks/n8n/trigger` - Trigger workflows from agents
- Basic authentication/verification

### 7.4 Test n8n Integration

- Test webhook from n8n to FastAPI
- Test FastAPI calling n8n webhook
- Verify message flow
- Document n8n workflow structure

**Deliverable:** Basic n8n integration working, can send/receive messages between n8n and FastAPI

---

## Step 8: Inquiry & Booking Agent

### 7.1 Create Agent Base Class

Create `agents/base_agent.py`:

- Base agent class with LLM initialization
- Common methods for all agents
- Qwen API integration (using provided code snippet)

### 7.2 Create Inquiry & Booking Agent

Create `agents/inquiry_booking_agent.py`:

- Initialize with LangChain/LangGraph
- Property context loading
- Date availability checking
- Price calculation
- Negotiation logic
- Booking flow state machine

### 7.3 Implement Agent Methods

**Methods:**

- `handle_inquiry(message, property_id, guest_context)` - Handle availability questions
- `check_availability(property_id, check_in, check_out)` - Check dates against bookings
- `calculate_price(property_id, nights, guests)` - Calculate base price
- `negotiate_price(requested_price, property_id)` - Negotiate within range
- `request_payment(booking_details)` - Request payment screenshot
- `confirm_booking(booking_id)` - Confirm after host approval

### 7.4 Create Agent API Endpoint

In `api/routes/agents.py`:

- `POST /agents/inquiry-booking/process` - Process guest message
- Request: `{message, guest_telegram_id, property_id}`
- Response: `{response, action, metadata}`

### 7.5 Integrate with Telegram Guest Bot

- Route guest messages to agent
- Handle agent responses
- Handle payment screenshot uploads
- Update booking status

### 7.6 Test Inquiry & Booking Agent

- Test availability inquiries
- Test price questions
- Test negotiation
- Test booking flow (without payment for now)

**Deliverable:** Inquiry & Booking Agent working, handles inquiries and booking requests

**Note:** At this point, you can test the agent immediately via Telegram! Send messages to the guest bot and see agent responses.

---

## Step 9: Payment Verification Workflow

### 8.1 Enhance Booking Agent

- Add payment screenshot handling
- Store screenshot in `storage/payment_screenshots/`
- Update booking with screenshot path
- Set payment status to 'pending'

### 8.2 Create Host Payment Notification

- When payment screenshot received, send to host via host bot
- Include booking details
- Include screenshot
- Request approval (yes/no buttons or text)

### 8.3 Create Host Payment Response Handler

**Host Bot:**

- Parse "yes" or "no" responses
- Update booking payment status
- If approved: trigger booking confirmation
- If rejected: notify guest

### 8.4 Implement Booking Confirmation Flow

When payment approved:

1. Update booking status to 'confirmed'
2. Create booking record
3. Log booking confirmation
4. Send confirmation to guest
5. Trigger n8n webhook for calendar and cleaning

### 8.5 Test Payment Workflow

- Guest uploads screenshot
- Host receives notification
- Host approves/rejects
- Booking confirmed/rejected
- Guest notified

**Deliverable:** Complete payment verification workflow working

---

## Step 10: Google Calendar Integration

### 9.1 Set Up Google Calendar API

- Create Google Cloud project (if needed)
- Enable Calendar API
- Create OAuth credentials
- Download credentials file
- Add to `.env`

### 9.2 Create Calendar Service

Create `api/utils/calendar.py`:

- `authenticate()` - OAuth flow
- `create_calendar()` - Create property bookings calendar
- `create_event()` - Create booking event
- `update_event()` - Update event
- `delete_event()` - Delete event

### 9.3 Integrate with Booking Confirmation

- When booking confirmed, create calendar event
- Store calendar event ID in booking
- Include property name, guest name, dates, times

### 9.4 Test Calendar Integration

- Create test booking
- Verify calendar event created
- Check event details
- Test event updates

**Deliverable:** Google Calendar integration working, events created automatically

---

## Step 11: Cleaner Coordination Agent

### 10.1 Create Cleaner Coordination Agent

Create `agents/cleaner_coordination_agent.py`:

- Initialize with LangChain
- Cleaning task scheduling logic
- Cleaner availability checking (simple: always available)
- Task assignment logic

### 10.2 Implement Agent Methods

**Methods:**

- `schedule_pre_checkin_cleaning(booking_id)` - Schedule before check-in
- `schedule_post_checkout_cleaning(booking_id)` - Schedule after check-out
- `handle_cleaning_request(property_id, issue_description)` - Handle during-stay requests
- `notify_cleaner(task_id)` - Send Telegram message to cleaner
- `update_task_status(task_id, status)` - Update task status

### 10.3 Create Cleaning Task Management

- Create cleaning tasks in database
- Link to bookings
- Track status
- Log all cleaning activities

### 10.4 Implement Cleaner Telegram Handler

**Cleaner receives message:**

- Cleaning task details
- Property information
- Date and time
- Auto-reply: "okay will clean"

**Cleaner completion:**

- Cleaner sends completion message
- Update task status to 'completed'
- Log completion
- Notify system

### 10.5 Create Agent API Endpoint

In `api/routes/agents.py`:

- `POST /agents/cleaner-coordination/schedule` - Schedule cleaning
- `POST /agents/cleaner-coordination/handle-request` - Handle cleaning request

### 10.6 Integrate with Booking Flow

- When booking confirmed, trigger pre-checkin cleaning
- Schedule post-checkout cleaning
- Test cleaner notifications

### 10.7 Test Cleaner Coordination

- Test scheduling from booking
- Test cleaner notification
- Test cleaner response
- Test completion update

**Deliverable:** Cleaner Coordination Agent working, cleaning tasks scheduled and managed

---

## Step 12: Issue Handling Agent

### 11.1 Create Issue Handling Agent

Create `agents/issue_handling_agent.py`:

- Initialize with LangChain
- Issue classification logic
- Property FAQ knowledge
- Escalation decision logic

### 11.2 Implement Agent Methods

**Methods:**

- `classify_issue(message, property_id, booking_context)` - Classify issue type
- `handle_faq(question, property_id)` - Answer FAQ questions
- `handle_cleaning_issue(issue, property_id, booking_id)` - Forward to cleaner agent
- `escalate_to_host(issue, property_id, booking_id)` - Escalate urgent issues

### 11.3 Implement Issue Classification

**Categories:**

- FAQ (wifi, amenities, rules) → Direct answer
- Cleaning/missing items → Cleaner Coordination Agent
- Urgent (safety, major problems) → Host escalation

### 11.4 Create Agent API Endpoint

In `api/routes/agents.py`:

- `POST /agents/issue-handling/process` - Process issue message

### 11.5 Integrate with Guest Bot

- Detect active bookings for guest
- Route messages during stay to Issue Handling Agent
- Handle agent responses
- Forward to cleaner or host as needed

### 11.6 Implement Host Escalation

- When issue escalated, send to host via host bot
- Include issue details
- Include guest information
- Log escalation

### 11.7 Test Issue Handling

- Test FAQ questions
- Test cleaning issues
- Test urgent escalations
- Test guest responses

**Deliverable:** Issue Handling Agent working, handles guest issues during stays

---

## Step 13: Host Summary Agent

### 12.1 Create Host Summary Agent

Create `agents/host_summary_agent.py`:

- Initialize with LangChain
- Log analysis logic
- Report generation logic
- Data aggregation

### 12.2 Implement Agent Methods

**Methods:**

- `generate_weekly_report(property_id, week_start_date)` - Generate weekly report
- `generate_monthly_report(property_id, month)` - Generate monthly report
- `aggregate_logs(property_id, date_range)` - Aggregate log data
- `format_report(data)` - Format report as readable text

### 12.3 Implement Report Generation

**Report includes:**

- Date range
- Booking requests vs confirmations
- Total nights booked vs free
- Issues reported and resolutions
- Escalations to host
- Cleaning tasks scheduled/completed
- Failures/unusual patterns

### 12.4 Create Agent API Endpoint

In `api/routes/agents.py`:

- `POST /agents/host-summary/weekly` - Generate weekly report
- `POST /agents/host-summary/monthly` - Generate monthly report

### 12.5 Integrate Report Delivery

- Generate report
- Send to host via host bot
- Format as readable message
- Log report generation

### 12.6 Test Host Summary

- Generate test reports
- Verify data accuracy
- Test report formatting
- Test delivery to host

**Deliverable:** Host Summary Agent working, generates and delivers reports

---

## Step 14: n8n Full Workflow Integration

### 14.1 Design Full n8n Workflows

**Main Workflows:**

1. **Message Router** - Routes Telegram messages to appropriate agents (enhance from Step 7)
2. **Booking Confirmation** - Handles post-booking actions (calendar, cleaning)
3. **Pre-Check-in** - Sends check-in instructions before check-in date
4. **Check-out** - Sends check-out instructions and schedules cleaning
5. **Periodic Reports** - Triggers weekly/monthly reports
6. **Cleaning Reminders** - Sends reminders for scheduled cleanings

### 14.2 Enhance Webhook Endpoints

In `api/routes/`:

- Complete webhook endpoints for all workflows
- Webhook authentication
- Error handling

### 14.3 Implement Full n8n Triggers

**From Agents:**

- Booking confirmed → Trigger booking confirmation workflow
- Cleaning scheduled → Trigger cleaning reminder workflow
- Issue escalated → Trigger host notification

**From n8n:**

- Scheduled triggers for pre-check-in
- Scheduled triggers for check-out
- Scheduled triggers for reports

### 14.4 Create Complete n8n Workflow Configurations

Document workflow structure:

- Node types needed
- Connections between nodes
- HTTP Request nodes to agent endpoints
- Telegram nodes for notifications
- Google Calendar nodes
- Schedule nodes
- Error handling nodes

### 14.5 Test Full n8n Integration

- Test message routing
- Test booking confirmation flow
- Test scheduled triggers
- Test calendar integration via n8n
- Test all workflow connections

**Deliverable:** Complete n8n workflows configured, fully integrated with agents and services

---

## Step 15: Check-in/Check-out Automation

### 15.1 Implement Pre-Check-in Workflow

**n8n Scheduled Workflow:**

- Trigger: 1 day before check-in
- Fetch booking details
- Get check-in instructions from property config
- Send to guest via guest bot
- Remind cleaner about pre-check-in cleaning

### 15.2 Implement Check-out Workflow

**n8n Scheduled Workflow:**

- Trigger: On check-out date
- Fetch booking details
- Get check-out instructions from property config
- Send to guest via guest bot
- Trigger post-checkout cleaning

### 15.3 Test Automation

- Create test booking
- Verify pre-check-in message sent
- Verify check-out message sent
- Verify cleaning triggered

**Deliverable:** Automated check-in/check-out messaging working

---

## Step 16: Testing & Validation

### 16.1 Create Test Scenarios

Create `tests/scenarios/`:

- `test_booking_flow.py` - Complete booking scenario
- `test_payment_verification.py` - Payment approval/rejection
- `test_issue_handling.py` - Various issue types
- `test_cleaning_coordination.py` - Cleaning workflows
- `test_multiple_bookings.py` - Overlapping bookings

### 16.2 Implement Test Scripts

- Scripted conversations
- Automated agent calls
- Database verification
- Log verification

### 16.3 Create Test Data

- Sample host configuration
- Sample properties (2-3)
- Sample bookings
- Sample logs

### 16.4 Run Integration Tests

- Test complete booking flow
- Test payment workflow
- Test issue handling
- Test cleaning coordination
- Test calendar integration
- Test report generation

### 16.5 Generate Test Results

- Document test outcomes
- Capture metrics:
  - Response times
  - Success rates
  - Error cases
  - System behavior

**Deliverable:** Comprehensive test suite, test results documented

---

## Step 17: Documentation & Finalization

### 17.1 Create Setup README

Create `README.md`:

- Project overview
- Prerequisites
- Installation instructions
- Environment setup
- Telegram bot creation guide
- Google Calendar setup
- n8n configuration
- Running the application

### 17.2 Create Agent Documentation

Create `docs/agents.md`:

- Agent descriptions
- API endpoints
- Request/response formats
- Usage examples

### 17.3 Create API Documentation

- FastAPI auto-generated docs (Swagger)
- Manual API documentation
- Webhook endpoints
- Authentication

### 17.4 Create n8n Workflow Documentation

Create `docs/n8n_workflows.md`:

- Workflow descriptions
- Node configurations
- Connection details
- Import/export instructions

### 17.5 Create User Guide

Create `docs/user_guide.md`:

- Host setup instructions
- Property configuration
- Using the system
- Troubleshooting

### 17.6 Create Architecture Documentation

Create `docs/architecture.md`:

- System architecture diagram
- Component descriptions
- Data flow
- Integration points

### 17.7 Final Code Review

- Code cleanup
- Add comments
- Verify error handling
- Check security

**Deliverable:** Complete documentation, system ready for demonstration

---

## 🎯 Implementation Order Summary

**Day 1:**

- Steps 1-3: Foundation (setup, database, FastAPI structure)
- Steps 4-5: Configuration & Logging (agents need this data)
- Steps 6-7: Telegram Bots & n8n Basic Setup (testing infrastructure ready!)
- Steps 8-9: Inquiry & Booking Agent + Payment (can test immediately via Telegram!)
- Step 10: Google Calendar integration

**Day 2:**

- Steps 11-13: Additional agents (Cleaner, Issue Handling, Host Summary) - test as we build
- Step 14: n8n Full Integration (enhance from basic setup)
- Step 15: Check-in/Check-out Automation
- Steps 16-17: Testing and documentation

**Key Advantage:** After Step 7, you can test every agent immediately via Telegram as you build it!

---

## ✅ Success Criteria

After completing all steps, the system should:

- [ ] Accept guest inquiries via Telegram
- [ ] Handle booking requests and negotiations
- [ ] Process payment verifications with host approval
- [ ] Create Google Calendar events automatically
- [ ] Schedule and coordinate cleaning tasks
- [ ] Handle guest issues during stays
- [ ] Escalate urgent issues to host
- [ ] Generate and deliver summary reports
- [ ] Automate check-in/check-out messaging
- [ ] Log all system activities
- [ ] Support multiple properties
- [ ] Work autonomously after initial setup

---

## 📝 Notes

- **Qwen API:** We'll integrate the Qwen API when you provide the code snippet
- **Telegram Bots:** Bot creation happens in Step 6, we'll guide you through it
- **n8n:** Basic integration in Step 7 allows testing, full workflows in Step 14
- **Testing:** You can test agents immediately after building them (starting from Step 8) via Telegram
- **Timeline:** This is ambitious for 2 days, but the hybrid approach lets us test and iterate faster
- **Why This Order:** Configuration and logging come before bots so agents have data to work with, but bots come early enough to test everything as we build

---

**Ready to start? Let's begin with Step 1!**
