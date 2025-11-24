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
