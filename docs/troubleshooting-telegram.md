# Troubleshooting Telegram Connection Issues

## Problem: "ConnectError: All connection attempts failed" or "Timed out"

This error means your server cannot connect to Telegram's API (`api.telegram.org`).

## Common Causes

### 1. VPN Blocking Outbound Connections

**Most Likely Cause:** Your VPN might be blocking HTTPS connections to Telegram's API.

**Solution:**

- Temporarily disconnect your VPN and test again
- Or configure your VPN to allow connections to `api.telegram.org`
- Or use a different VPN server that allows Telegram

### 2. Firewall Blocking HTTPS

Your Windows firewall or antivirus might be blocking outbound HTTPS.

**Solution:**

- Check Windows Firewall settings
- Temporarily disable firewall/antivirus to test
- Add Python/uvicorn to firewall exceptions

### 3. Network Configuration

Your network might have restrictions.

**Solution:**

- Try from a different network (mobile hotspot)
- Check if you can access `https://api.telegram.org` in a browser

## Quick Test

Run this in PowerShell to test connectivity:

```powershell
Test-NetConnection -ComputerName api.telegram.org -Port 443
```

If this fails, it confirms the connection issue.

## Workaround

The code now:

1. ✅ Logs all agent responses to the database
2. ✅ Returns success to Telegram webhook (prevents retries)
3. ✅ Retries sending messages (2 retries with backoff)
4. ✅ Handles errors gracefully

**You can still test the agent** - responses are logged even if they can't be sent to Telegram.

## Check Logs

To see agent responses even if Telegram fails:

```python
from database.db import get_db
from api.utils.logging import get_recent_logs

db = next(get_db())
logs = get_recent_logs(db, limit=10)
for log in logs:
    if log.event_type == "agent_response":
        print(f"Agent said: {log.message}")
```

## Next Steps

1. **Disconnect VPN** and test again
2. **Check firewall** settings
3. **Test from different network** (mobile hotspot)
4. If still failing, we can implement a message queue system

## Note

The agent is working correctly - it's processing messages and generating responses. The only issue is sending responses back to Telegram. All responses are logged in the database, so you can verify the agent is working.

## Host Bot: "Chat not found"

If you see `Error sending Telegram photo: Chat not found`, it means the host has not opened the host bot chat yet.

**Fix:**

1. Share the host bot link with the host.
2. Ask them to open the chat in Telegram and send `/start` once (this lets the bot message them).
3. Retry the payment flow. The bot will automatically resend future payment screenshots.
