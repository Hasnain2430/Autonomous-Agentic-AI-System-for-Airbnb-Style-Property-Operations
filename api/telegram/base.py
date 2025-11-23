"""
Base utilities for Telegram bot handlers.

Shared functions and constants for both guest and host bots.
"""

import os
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
import httpx

load_dotenv()


def get_bot_token(bot_type: str) -> Optional[str]:
    """
    Get bot token from environment variables.
    
    Args:
        bot_type: 'guest' or 'host'
    
    Returns:
        Bot token or None if not found
    """
    if bot_type == "guest":
        return os.getenv("GUEST_BOT_TOKEN")
    elif bot_type == "host":
        return os.getenv("HOST_BOT_TOKEN")
    return None


def _get_telegram_request() -> Optional[HTTPXRequest]:
    """
    Get HTTPXRequest with proxy configuration if available.
    
    Checks for proxy settings in environment variables:
    - TELEGRAM_PROXY_URL: Full proxy URL (e.g., "socks5://127.0.0.1:1080")
    - TELEGRAM_PROXY_HOST and TELEGRAM_PROXY_PORT: For HTTP proxy
    
    By default, uses local proxy server at 127.0.0.1:1080 if available.
    
    Returns:
        HTTPXRequest with proxy or None for direct connection
    """
    proxy_url = os.getenv("TELEGRAM_PROXY_URL")
    proxy_host = os.getenv("TELEGRAM_PROXY_HOST")
    proxy_port = os.getenv("TELEGRAM_PROXY_PORT")
    
    # Default to local proxy server if no explicit config
    if not proxy_url and not (proxy_host and proxy_port):
        # Check if local proxy server is running (default port 1080)
        import socket
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            result = test_socket.connect_ex(('127.0.0.1', 1080))
            test_socket.close()
            if result == 0:
                proxy_url = "socks5://127.0.0.1:1080"
                print(f"✅ Using local proxy: {proxy_url}")
                return HTTPXRequest(proxy=proxy_url)
            else:
                print("⚠️  Local proxy server not running on port 1080")
                print("   Start it with: python proxy_server.py")
                return None
        except:
            print("⚠️  Could not check proxy server status")
            return None
    
    if proxy_url:
        # Use full proxy URL (supports socks5://, http://, https://)
        print(f"Using Telegram proxy: {proxy_url}")
        return HTTPXRequest(proxy=proxy_url)
    elif proxy_host and proxy_port:
        # Use HTTP proxy
        proxy_url = f"http://{proxy_host}:{proxy_port}"
        print(f"Using Telegram HTTP proxy: {proxy_url}")
        return HTTPXRequest(proxy=proxy_url)
    
    return None


async def send_message(
    bot_token: str,
    chat_id: str,
    message: str,
    parse_mode: Optional[str] = None,
    timeout: int = 10,
    retries: int = 2
) -> bool:
    """
    Send a message via Telegram bot with retry logic and proxy support.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID to send message to
        message: Message text
        parse_mode: Parse mode (e.g., 'HTML', 'Markdown')
        timeout: Timeout in seconds (default: 10)
        retries: Number of retry attempts (default: 2)
    
    Returns:
        True if message sent successfully, False otherwise
    """
    import asyncio
    
    # Get proxy configuration
    request = _get_telegram_request()
    
    for attempt in range(retries + 1):
        try:
            # Create bot with proxy if available
            if request:
                bot = Bot(token=bot_token, request=request)
            else:
                bot = Bot(token=bot_token)
            
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                read_timeout=timeout,
                write_timeout=timeout,
                connect_timeout=timeout
            )
            return True
        except TelegramError as e:
            error_text = str(e)
            if "Chat not found" in error_text:
                print("Telegram error: Chat not found. Ask the recipient to open the bot in Telegram and send /start once.")
                return False
            if attempt < retries:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s
                print(f"Telegram error (attempt {attempt + 1}/{retries + 1}): {error_text}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            print(f"Error sending Telegram message after {retries + 1} attempts: {error_text}")
            return False
        except Exception as e:
            error_type = type(e).__name__
            if "Connect" in error_type or "Timeout" in error_type:
                if attempt < retries:
                    wait_time = (attempt + 1) * 2
                    print(f"Connection error (attempt {attempt + 1}/{retries + 1}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                print(f"Connection error sending Telegram message: {e}")
                print("⚠️  This might be due to VPN/firewall blocking Telegram API. Check your network settings.")
            else:
                print(f"Unexpected error sending Telegram message: {e}")
            return False
    
    return False


async def send_photo(
    bot_token: str,
    chat_id: str,
    photo_path: str,
    caption: Optional[str] = None
) -> bool:
    """
    Send a photo via Telegram bot with proxy support.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID to send photo to
        photo_path: Path to photo file
        caption: Optional caption for the photo
    
    Returns:
        True if photo sent successfully, False otherwise
    """
    try:
        # Get proxy configuration
        request = _get_telegram_request()
        
        if request:
            bot = Bot(token=bot_token, request=request)
        else:
            bot = Bot(token=bot_token)
        
        with open(photo_path, 'rb') as photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption
            )
        return True
    except TelegramError as e:
        error_text = str(e)
        print(f"Error sending Telegram photo: {error_text}")
        if "Chat not found" in error_text:
            print("Tip: Ask the host to open the host bot in Telegram and send /start at least once so the bot can reach them.")
        elif "bot was blocked" in error_text.lower():
            print("Tip: Host bot appears to be blocked. Ask the host to unblock the bot in Telegram.")
        return False
    except FileNotFoundError:
        print(f"Photo file not found: {photo_path}")
        return False


def parse_telegram_update(update_data: dict) -> dict:
    """
    Parse Telegram webhook update data.
    
    Args:
        update_data: Raw update data from Telegram
    
    Returns:
        Parsed update dictionary with message info
    """
    parsed = {
        "update_id": update_data.get("update_id"),
        "message": None,
        "chat_id": None,
        "user_id": None,
        "text": None,
        "photo": None,
        "document": None,
        "is_command": False,
        "command": None
    }
    
    # Get message (could be in message or edited_message)
    message = update_data.get("message") or update_data.get("edited_message")
    if not message:
        return parsed
    
    parsed["message"] = message
    parsed["chat_id"] = str(message.get("chat", {}).get("id"))
    parsed["user_id"] = str(message.get("from", {}).get("id"))
    parsed["text"] = message.get("text", "")
    
    # Check for photos
    if "photo" in message:
        parsed["photo"] = message["photo"]
    
    # Check for documents
    if "document" in message:
        parsed["document"] = message["document"]
    
    # Check for commands
    if parsed["text"] and parsed["text"].startswith("/"):
        parsed["is_command"] = True
        parts = parsed["text"].split()
        parsed["command"] = parts[0][1:] if parts else None  # Remove leading /
    
    return parsed

