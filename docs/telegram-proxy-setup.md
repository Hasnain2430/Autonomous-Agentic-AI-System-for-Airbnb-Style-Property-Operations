# Telegram Proxy Setup for Blocked Regions

If you're in a region where Telegram is blocked (like Pakistan), you need to configure a proxy for the Telegram bot to work.

## Option 1: Use Your VPN's SOCKS5 Proxy (Recommended)

Most VPNs provide a SOCKS5 proxy that you can use.

### Steps:

1. **Find your VPN's SOCKS5 proxy settings:**
   - Check your VPN client settings
   - Look for "SOCKS5 Proxy" or "Local Proxy" settings
   - Common ports: 1080, 10808, 10809
   - Common host: 127.0.0.1 (localhost)

2. **Add to `.env` file:**
   ```
   TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
   ```
   Replace `127.0.0.1:1080` with your VPN's actual proxy address and port.

3. **Restart FastAPI server**

## Option 2: Use HTTP Proxy

If your VPN provides an HTTP proxy:

1. **Add to `.env` file:**
   ```
   TELEGRAM_PROXY_HOST=127.0.0.1
   TELEGRAM_PROXY_PORT=8080
   ```
   Replace with your actual proxy host and port.

2. **Restart FastAPI server**

## Option 3: Use a Public Proxy (Not Recommended)

⚠️ **Warning:** Public proxies are not secure. Only use for testing.

1. **Find a public SOCKS5 proxy** (search online)
2. **Add to `.env` file:**
   ```
   TELEGRAM_PROXY_URL=socks5://proxy.example.com:1080
   ```

## Option 4: Use Telegram's Built-in Proxy (MTProto)

Telegram has its own proxy protocol. You can set up an MTProto proxy:

1. **Get an MTProto proxy** (from Telegram proxy channels or services)
2. **Add to `.env` file:**
   ```
   TELEGRAM_PROXY_URL=socks5://proxy.example.com:1080
   ```

## Finding Your VPN's Proxy Settings

### For OpenVPN:
- Check your VPN client's advanced settings
- Look for "Local Proxy" or "SOCKS Proxy" options

### For WireGuard:
- Usually doesn't provide a local proxy
- You may need to use a separate proxy service

### For Commercial VPNs (NordVPN, ExpressVPN, etc.):
- Check their documentation for local proxy settings
- Some provide SOCKS5 proxies in their apps

## Testing

After setting up the proxy:

1. Restart your FastAPI server
2. Send a test message to your bot
3. Check server logs - you should see: `Using Telegram proxy: ...`
4. If it works, you'll receive the bot's response

## Troubleshooting

### "Connection refused" error:
- Check if the proxy address and port are correct
- Make sure your VPN is running
- Try `127.0.0.1` instead of `localhost`

### "Authentication failed" error:
- Some proxies require authentication
- Format: `socks5://username:password@host:port`

### Still not working:
- Try a different proxy type (SOCKS5 vs HTTP)
- Check if your VPN allows proxy connections
- Consider using a dedicated proxy service

## Example .env Configuration

```env
# Telegram Bot Tokens
GUEST_BOT_TOKEN=your_token_here
HOST_BOT_TOKEN=your_token_here

# Telegram Proxy (for blocked regions)
TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080

# Or use HTTP proxy:
# TELEGRAM_PROXY_HOST=127.0.0.1
# TELEGRAM_PROXY_PORT=8080
```

## Note

The proxy only affects **outbound** connections from your server to Telegram's API. Incoming webhooks from Telegram to your server still work through ngrok (which is not blocked).

