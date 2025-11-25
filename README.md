# Property Booking Management System

An autonomous property booking management system with Telegram bots for guests and hosts, featuring AI-powered agents, fixed booking flows, payment verification, and automated reporting.

---

## 🎯 System Overview

This system provides a complete property booking solution with:

- **Guest Bot** - Handles inquiries, bookings, and Q&A using AI agents
- **Host Bot** - Manages property setup, payment verification, and receives reports
- **Fixed Booking Flow** - Structured questions for booking and payment details
- **Payment Verification** - Screenshot-based payment with host approval
- **Weekly Reports** - Automated reports with booking, payment, and guest statistics
- **QnA System** - LLM-powered question answering for guests
- **Multi-Property Support** - Manage multiple properties per host

---

## 📋 Features

### Guest Bot Features

**Commands:**
- `/start` - Start conversation and view welcome message
- `/inquiry` - View available properties and ask questions
- `/book_property` - Select a property and start booking process
- `/qna` - Ask questions about properties, bookings, or general inquiries
- `/clear` - Clear conversation history and reset context

**Booking Flow:**
1. Guest selects property using `/book_property`
2. System asks fixed questions:
   - Check-in date
   - Check-out date
   - Number of guests
   - Customer full name (shows payment amount first, then host's bank details)
   - Bank name (payment source)
   - Payment screenshot upload
3. Payment summary shown with total amount and host bank details
4. Screenshot sent to host for verification
5. Guest receives confirmation after host approval
6. Check-in instructions sent automatically with:
   - Property location
   - Check-in/check-out times
   - WiFi credentials (if available)
   - All amenities info (AC, TV, parking, kitchen)

**QnA System:**
- Hybrid Q&A: Database FAQs + LLM fallback
- Shows property details, amenities (WiFi, AC, TV, parking, kitchen)
- Displays WiFi name and password if available
- Context-aware responses based on guest's bookings
- Example questions provided for easy interaction

### Host Bot Features

**Commands:**
- `/start` - Welcome message and setup instructions
- `/setup` - Set up host profile (name, email, phone, bank name, bank account)
- `/add_property` - Add new property with amenities questions
- `/help` - Show all available commands
- `/cancel` - Cancel current setup flow

**Property Setup includes:**
- Basic info (name, location, price, max guests)
- Check-in/check-out times
- Amenities questions:
  - WiFi (name and password)
  - Air conditioning
  - TV
  - Parking
  - Kitchen

**Payment Verification:**
- Receives payment screenshots from guests
- Reply with `yes`, `approve`, `verified`, or `verify` to confirm payment
- Reply with `no`, `reject`, or `decline` to reject payment
- Booking automatically confirmed/rejected based on response

**Weekly Reports:**
- Automatic weekly reports sent via Telegram
- Includes booking statistics, revenue, payment status, and guest counts
- Property-wise breakdown
- Recent bookings list

### Key Features

- **Fixed Pricing** - No negotiation, prices are fixed (base price × nights)
- **Pakistani Rupees (PKR)** - All prices displayed in PKR
- **Property Selection Required** - Guests must select property before booking
- **Check-in Instructions** - Automatically sent after payment verification with amenities info
- **Multi-step Setup Flows** - Guided setup for hosts and properties
- **Payment Method Storage** - Host bank details stored and shown only for the specific property being booked
- **Amenities Management** - WiFi credentials, AC, TV, parking, kitchen stored per property
- **Hybrid QnA** - Database FAQs checked first, then LLM fallback for complex questions
- **No Login Required** - Users identified automatically via Telegram ID (no signup/password needed)

### Authentication

- **No Traditional Login/Signup** - The system uses Telegram's built-in authentication
- **Automatic Identification** - Users are identified by their unique Telegram ID when they message the bot
- **Host Registration** - Hosts create their profile using `/setup` command (name, email, phone, bank details)
- **Guest Tracking** - Guests are tracked automatically; name collected during booking flow

---

# How to Run the System

Simple step-by-step guide to get the system running.

---

## Prerequisites

- Python 3.9 or higher
- VPN connection (must be ON)
- ngrok installed (or we'll install it)
- Virtual environment set up
- Dependencies installed

---

## Step 1: Turn On VPN

**IMPORTANT:** Make sure your VPN is connected and running before starting anything else.

✅ Check that VPN is active before proceeding.

---

## Step 2: Install ngrok (If Not Installed)

### Option A: Download ngrok

1. Go to: https://ngrok.com/download
2. Download ngrok for Windows
3. Extract the zip file
4. Note the path where you extracted it (e.g., `C:\Users\YourName\Downloads\ngrok-v3-stable-windows-amd64\`)

### Option B: Use Package Manager

```bash
# Using Chocolatey (if installed)
choco install ngrok

# Using Scoop (if installed)
scoop install ngrok
```

### Set Up ngrok Authtoken

1. Sign up at https://dashboard.ngrok.com/signup (free)
2. Get your authtoken from the dashboard
3. Run:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

---

## Step 3: Start ngrok

### Option A: Using the Batch File

Double-click `start_ngrok.bat`

**OR** if the path in the file is wrong, edit `start_ngrok.bat` and update the ngrok path, then run it.

### Option B: Manual Command

Open a terminal and run:

```bash
ngrok http 8000
```

**Keep this terminal open!** You'll see a URL like `https://xxxx-xxxx.ngrok-free.app` - this is your public URL.

---

## Step 4: Start FastAPI Server

Open a **new terminal** (keep ngrok running in the first one).

### Activate Virtual Environment

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Start FastAPI

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Keep this terminal open!** You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5: Start Proxy Server

Open a **new terminal** (keep ngrok and FastAPI running).

### Activate Virtual Environment (if not already activated)

```bash
venv\Scripts\activate
```

### Start Proxy Server

```bash
python proxy_server.py
```

**OR** double-click `start_proxy.bat`

**Keep this terminal open!** You should see:

```
✅ Proxy server started on 127.0.0.1:1080
```

---

## Step 6: Set Up Telegram Webhooks

### Get Your ngrok URL

From the ngrok terminal, copy the HTTPS URL (e.g., `https://xxxx-xxxx.ngrok-free.app`)

### Set Guest Bot Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_GUEST_BOT_TOKEN>/setWebhook?url=https://xxxx-xxxx.ngrok-free.app/api/webhook/guest"
```

### Set Host Bot Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_HOST_BOT_TOKEN>/setWebhook?url=https://xxxx-xxxx.ngrok-free.app/api/webhook/host"
```

Replace:

- `<YOUR_GUEST_BOT_TOKEN>` with your actual guest bot token
- `<YOUR_HOST_BOT_TOKEN>` with your actual host bot token
- `https://xxxx-xxxx.ngrok-free.app` with your actual ngrok URL

---

## Summary: What Should Be Running

You should have **3 terminals/windows open**:

1. **Terminal 1:** ngrok (showing the public URL)
2. **Terminal 2:** FastAPI server (running on port 8000)
3. **Terminal 3:** Proxy server (running on port 1080)

**Plus:** VPN must be connected.

---

## Quick Start Commands (All in Order)

```bash
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Terminal 1: Start ngrok
ngrok http 8000

# 3. Terminal 2: Start FastAPI
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Terminal 3: Start proxy
python proxy_server.py
```

---

## Troubleshooting

### ngrok not found

- Make sure ngrok is installed
- Check the path in `start_ngrok.bat` is correct
- Or add ngrok to your system PATH

### Port 8000 already in use

- Stop any other service using port 8000
- Or change the port in FastAPI command: `--port 8001` (and update ngrok accordingly)

### VPN not working

- Make sure VPN is connected
- Check VPN connection status
- Restart VPN if needed

### Webhook not receiving messages

- Check ngrok URL is correct
- Verify webhook is set: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Make sure FastAPI is running
- Check ngrok is still active (free tier has time limits)

### Proxy server errors

- Make sure VPN is connected
- Check port 1080 is not in use
- Verify Python dependencies are installed: `pip install pysocks`

---

## Stopping the System

1. Press `Ctrl+C` in each terminal to stop:

   - Stop proxy server first
   - Stop FastAPI second
   - Stop ngrok last

2. Disconnect VPN (optional)

---

## Environment Variables

Make sure you have a `.env` file with:

- `GUEST_BOT_TOKEN` - Your Telegram guest bot token
- `HOST_BOT_TOKEN` - Your Telegram host bot token
- `HOST_TELEGRAM_ID` - Your Telegram user ID
- `DASHSCOPE_API_KEY` - Your Qwen API key
- `DATABASE_PATH` - Path to database file

See `.env.example` for template.

---

That's it! The system should now be running.

---

## 🚀 Usage Guide

### For Guests

1. **Start Conversation:**
   - Send `/start` to the guest bot
   - View available properties with `/inquiry`
   - Or start booking directly with `/book_property`

2. **Book a Property:**
   ```
   /book_property
   → Select property from list
   → Answer booking questions (dates, guests)
   → Provide payment details (name, bank)
   → Upload payment screenshot
   → Wait for host verification
   → Receive confirmation and check-in instructions
   ```

3. **Ask Questions:**
   ```
   /qna
   → View property details and amenities
   → See WiFi name and password (if available)
   → Ask any question about properties or bookings
   → Get instant answers from database or AI-powered responses
   
   Example questions:
   • What's the WiFi password?
   • Is parking available?
   • What time is check-in?
   • How many guests can stay?
   ```

### For Hosts

1. **Initial Setup:**
   ```
   /setup
   → Provide name, email, phone
   → Provide bank name and account number
   → Profile saved
   ```

2. **Add Properties:**
   ```
   /add_property
   → Provide property details step-by-step:
     - Property identifier (e.g., PROP-001)
     - Name and location
     - Base price (PKR per night)
     - Max guests
     - Check-in/check-out times
   → Answer amenities questions:
     - WiFi available? (if yes: name and password)
     - Air conditioning?
     - TV?
     - Parking?
     - Kitchen?
   ```

3. **Verify Payments:**
   - When payment screenshot received, reply:
     - `yes` or `verified` → Approve and confirm booking
     - `no` or `reject` → Reject payment

4. **Receive Reports:**
   - Weekly reports sent automatically every Monday
   - Or trigger manually via API endpoint

---

## 📊 Weekly Reports

### Automatic Reports

Reports are sent automatically every Monday (can be scheduled via cron or n8n).

### Manual Trigger

```bash
# Send to all hosts
curl -X POST "http://localhost:8000/api/agents/host-summary/weekly"

# Send to specific host
curl -X POST "http://localhost:8000/api/agents/host-summary/weekly?host_id=1"

# Custom week
curl -X POST "http://localhost:8000/api/agents/host-summary/weekly?week_start_date=2025-01-06"
```

### Report Contents

- **Summary Statistics:**
  - Total bookings (confirmed, pending, cancelled)
  - Total revenue (PKR)
  - Payment status breakdown
  - Total guests and nights

- **Property Breakdown:**
  - Per-property statistics
  - Bookings, revenue, guests per property

- **Recent Bookings:**
  - Last 10 bookings with details
  - Guest names, dates, amounts, status

---

## 🔧 API Endpoints

### Guest & Host Webhooks
- `POST /api/webhook/guest` - Guest bot webhook
- `POST /api/webhook/host` - Host bot webhook

### Agent Endpoints
- `POST /api/agents/inquiry-booking/process` - Process guest inquiries/bookings
- `POST /api/agents/host-summary/weekly` - Generate weekly reports

### Booking Endpoints
- `GET /api/bookings` - List bookings
- `GET /api/bookings/{id}` - Get booking details

---

## 💾 Database

### Seed Dummy Data

To populate the database with test data:

```bash
python scripts/seed_dummy_data.py
```

This creates:
- Sample host with payment methods
- Multiple properties
- Sample bookings

### Reset Database

```bash
python scripts/seed_dummy_data.py --reset
```

---

## 🛠️ Development

### Project Structure

```
Project/
├── api/
│   ├── main.py              # FastAPI application
│   ├── routes/               # API routes
│   ├── telegram/             # Bot handlers
│   ├── utils/                # Utilities (logging, payment, reports)
│   └── agents/               # AI agents
├── database/
│   ├── models.py             # SQLAlchemy models
│   └── db.py                 # Database setup
├── config/
│   └── config_manager.py     # Configuration management
├── scripts/
│   └── seed_dummy_data.py    # Database seeding
├── proxy_server.py           # SOCKS5 proxy server
└── .env                      # Environment variables
```

### Key Components

- **Agents:** InquiryAgent, BookingAgent (LLM-powered with Qwen Max)
- **Payment System:** Screenshot handling, host verification, property-specific bank details
- **Report System:** Weekly report generation and delivery
- **Conversation Context:** Persistent conversation state
- **Fixed Questions:** Structured booking and payment flows
- **QnA Handler:** Hybrid system - checks database FAQs first, then LLM fallback
- **Amenities System:** Property amenities stored as FAQs (WiFi, AC, TV, parking, kitchen)

---

## 📝 Notes

- **Currency:** All prices are in Pakistani Rupees (PKR)
- **Pricing:** Fixed pricing only (no negotiation)
- **Property Selection:** Required before booking (no default property)
- **Payment:** Screenshot-based with host verification; bank details shown only for the specific property's host
- **Reports:** Weekly reports sent automatically or on-demand
- **Amenities:** Stored per property and shown in check-in instructions and QnA
- **WiFi:** Network name and password stored and provided to guests after booking confirmation

---

## 🔐 Security

- VPN required for Telegram API access
- SOCKS5 proxy for secure connections
- Environment variables for sensitive data
- Webhook verification

---

That's it! The system should now be running.
