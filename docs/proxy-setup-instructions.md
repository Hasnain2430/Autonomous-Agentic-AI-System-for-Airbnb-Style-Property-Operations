# Local Proxy Server Setup Instructions

## Why This Is Needed

Since Telegram is blocked in Pakistan, your Python application can't directly connect to Telegram's API. This local proxy server routes all Telegram API requests through your VPN connection.

## How It Works

1. **Proxy Server** (`proxy_server.py`) runs on your computer
2. It listens on `127.0.0.1:1080` (localhost)
3. Your Python app connects to this local proxy
4. The proxy forwards requests through your VPN (which is already working)
5. Telegram API receives the request through the VPN

## Setup Steps

### Step 1: Start the Proxy Server

**Option A: Using the batch file (Easiest)**
1. Double-click `start_proxy.bat`
2. Keep this window open (don't close it)

**Option B: Using Command Line**
1. Open PowerShell in the project folder
2. Run: `python proxy_server.py`
3. Keep this window open

You should see:
```
✅ Proxy server started on 127.0.0.1:1080
   This proxy routes traffic through your VPN connection
   Press Ctrl+C to stop
```

### Step 2: Make Sure VPN is Connected

- Your VPN must be running and connected
- The proxy routes through your VPN, so VPN must be active

### Step 3: Start FastAPI Server

1. Open a **new** PowerShell window (keep proxy running)
2. Run: `uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
3. You should see: `Using default local proxy: socks5://127.0.0.1:1080`

### Step 4: Test

1. Send a message to your Telegram bot
2. Check the proxy server window - you should see connection logs
3. Check FastAPI server - should work without errors

## Important Notes

- **Keep proxy server running** while using the bot
- **VPN must be connected** for the proxy to work
- The proxy automatically starts when you run `start_proxy.bat`
- To stop: Press `Ctrl+C` in the proxy server window

## Troubleshooting

### "Connection refused" error
- Make sure proxy server is running
- Check if port 1080 is already in use

### Still getting timeout errors
- Verify VPN is connected
- Check proxy server logs for errors
- Try restarting both proxy and FastAPI server

### Proxy server won't start
- Make sure `pysocks` is installed: `pip install pysocks`
- Check if port 1080 is available

## Running on Startup (Optional)

You can add the proxy server to Windows startup:
1. Press `Win + R`
2. Type `shell:startup`
3. Copy `start_proxy.bat` to that folder
4. Proxy will start automatically when Windows starts

## Next Steps

Once this is working:
- The proxy will handle all Telegram API requests
- Your bot will work as long as VPN is connected
- No need to configure anything in `.env` (uses default local proxy)

