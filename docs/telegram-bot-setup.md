# Telegram Bot Setup Instructions

This guide will help you create the two Telegram bots needed for the system.

## Prerequisites

- A Telegram account (create one at https://telegram.org if you don't have one)
- Access to Telegram (mobile app or web)
- The `.env` file in the project root (it should already exist, or copy from `.env.example`)

## Step 1: Create Guest Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat with BotFather
3. Send the command: `/newbot`
4. BotFather will ask for a name for your bot. Enter something like: **"Property Guest Bot"**
5. BotFather will ask for a username. It must end with `bot`. Enter something like: **"your_property_guest_bot"** (must be unique)
6. BotFather will give you a **token** that looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
7. **Copy this token** - you'll need it for the `.env` file
8. This is your **GUEST_BOT_TOKEN**

## Step 2: Create Host Bot

1. Still in the chat with BotFather, send: `/newbot` again
2. Enter a name like: **"Property Host Bot"**
3. Enter a username like: **"your_property_host_bot"** (must be unique and different from guest bot)
4. BotFather will give you another token
5. **Copy this token** - this is your **HOST_BOT_TOKEN**

## Step 3: Configure Webhooks (After Server is Running)

Once your FastAPI server is running, you need to set up webhooks so Telegram can send messages to your server.

### Option A: Using ngrok (Recommended for Local Development)

1. Install ngrok: https://ngrok.com/download
2. Start your FastAPI server: `uvicorn api.main:app --reload`
3. In a new terminal, run: `ngrok http 8000`
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Set webhook for guest bot:
   ```
   curl -X POST "https://api.telegram.org/bot<GUEST_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok.io/api/webhook/guest"
   ```
6. Set webhook for host bot:
   ```
   curl -X POST "https://api.telegram.org/bot<HOST_BOT_TOKEN>/setWebhook?url=https://abc123.ngrok.io/api/webhook/host"
   ```

### Option B: Using Your Public IP (If Deployed)

If your server is deployed with a public URL:

1. Set webhook for guest bot:
   ```
   curl -X POST "https://api.telegram.org/bot<GUEST_BOT_TOKEN>/setWebhook?url=https://your-domain.com/api/webhook/guest"
   ```
2. Set webhook for host bot:
   ```
   curl -X POST "https://api.telegram.org/bot<HOST_BOT_TOKEN>/setWebhook?url=https://your-domain.com/api/webhook/host"
   ```

## Step 4: Add Tokens to .env File

1. **Locate the `.env` file** in the project root directory:
   - Path: `B:\Uni\Seventh Semester\Agentic AI\Project\.env`
   - If the file doesn't exist, copy `.env.example` to `.env`:
     - On Windows: `Copy-Item .env.example .env` in PowerShell
     - Or manually copy the file and rename it
2. **Open the `.env` file** in a text editor
3. **Add your tokens** (replace the placeholder values):
   ```
   GUEST_BOT_TOKEN=your_guest_bot_token_here
   HOST_BOT_TOKEN=your_host_bot_token_here
   ```
   - Replace `your_guest_bot_token_here` with the actual token from BotFather
   - Replace `your_host_bot_token_here` with the actual token from BotFather
4. **Save the file**

## Step 5: Get Your Telegram ID (For Host)

You'll need your Telegram ID for the `HOST_TELEGRAM_ID` in `.env`:

1. Search for **@userinfobot** on Telegram
2. Start a chat with it
3. It will send you your user ID
4. Add it to `.env`: `HOST_TELEGRAM_ID=your_telegram_id_here`

## Step 6: Test the Bots

1. Start your FastAPI server: `uvicorn api.main:app --reload`
2. Send a message to your guest bot on Telegram
3. Send a message to your host bot on Telegram
4. Check the server logs to see if messages are received
5. The bots should echo your messages (for testing)

## Troubleshooting

- **Webhook not working?** Make sure:

  - Your server is running
  - ngrok is running (if using local development)
  - The webhook URL is correct
  - The tokens are correct in `.env`

- **Bot not responding?** Check:

  - Server logs for errors
  - That tokens are in `.env` file
  - That webhooks are set correctly

- **Can't find BotFather?** Make sure you're searching for `@BotFather` (with the @ symbol)

## Next Steps

Once bots are set up and working:

- Step 6 will be complete
- You can test the configuration flow via host bot
- In Step 8, guest bot will be connected to agents
- In Step 9, host bot will handle payment approvals
