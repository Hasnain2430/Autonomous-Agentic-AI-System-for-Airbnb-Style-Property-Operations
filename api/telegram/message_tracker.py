"""
Message ID tracking for bot messages.

Stores bot message IDs so they can be deleted when user clears chat.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from database.models import SystemLog
from api.utils.logging import EventType


def store_bot_message_id(
    db: Session,
    guest_telegram_id: str,
    message_id: int,
    property_id: Optional[int] = None
) -> None:
    """
    Store bot message ID in SystemLog for later deletion.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        message_id: Telegram message ID
        property_id: Optional property ID
    """
    try:
        from api.utils.logging import log_event
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name="MessageTracker",
            property_id=property_id,
            message=f"Bot message sent: {message_id}",
            metadata={
                "guest_telegram_id": guest_telegram_id,
                "user_id": guest_telegram_id,
                "telegram_message_id": message_id,
                "is_bot_message": True
            }
        )
    except Exception as e:
        print(f"Error storing message ID: {e}")


def get_bot_message_ids(
    db: Session,
    guest_telegram_id: str,
    limit: int = 100
) -> List[int]:
    """
    Get recent bot message IDs for a guest.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        limit: Maximum number of message IDs to retrieve
    
    Returns:
        List of message IDs
    """
    try:
        # Get all logs for this guest
        logs = (
            db.query(SystemLog)
            .filter(
                SystemLog.event_metadata.like(f'%"user_id":"{guest_telegram_id}"%')
            )
            .order_by(SystemLog.created_at.desc())
            .limit(limit * 2)  # Get more logs to find message IDs
            .all()
        )
        
        message_ids = []
        for log in logs:
            try:
                metadata = log.get_metadata()
                if metadata.get("is_bot_message") and metadata.get("telegram_message_id"):
                    msg_id = metadata["telegram_message_id"]
                    if msg_id not in message_ids:  # Avoid duplicates
                        message_ids.append(msg_id)
            except:
                continue
        
        return message_ids[:limit]  # Return up to limit
    except Exception as e:
        print(f"Error getting bot message IDs: {e}")
        import traceback
        traceback.print_exc()
        return []


async def delete_bot_messages(
    bot_token: str,
    chat_id: str,
    message_ids: List[int]
) -> int:
    """
    Delete bot messages by their IDs.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID
        message_ids: List of message IDs to delete
    
    Returns:
        Number of messages successfully deleted
    """
    from telegram import Bot
    from telegram.error import TelegramError
    from api.telegram.base import _get_telegram_request
    
    if not message_ids:
        return 0
    
    request = _get_telegram_request()
    if request:
        bot = Bot(token=bot_token, request=request)
    else:
        bot = Bot(token=bot_token)
    
    deleted_count = 0
    for msg_id in message_ids:
        try:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=msg_id,
                read_timeout=5,
                write_timeout=5,
                connect_timeout=5
            )
            deleted_count += 1
        except TelegramError as e:
            # Message might already be deleted or not found - that's okay
            if "message to delete not found" not in str(e).lower():
                print(f"Could not delete message {msg_id}: {e}")
        except Exception as e:
            print(f"Error deleting message {msg_id}: {e}")
    
    return deleted_count

