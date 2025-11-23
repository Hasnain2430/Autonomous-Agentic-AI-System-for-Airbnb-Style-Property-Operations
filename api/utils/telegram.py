"""
Telegram message sending utilities.

This module re-exports functions from api.telegram.base for backward compatibility.
"""

from api.telegram.base import send_message, send_photo

__all__ = ["send_message", "send_photo"]

