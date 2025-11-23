"""
Conversation history management for Telegram bots.

Stores and retrieves conversation history for maintaining context.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database.models import SystemLog
from api.utils.logging import EventType
import json


def get_conversation_history(
    db: Session,
    guest_telegram_id: str,
    property_id: Optional[int] = None,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Get conversation history for a guest.
    
    Args:
        db: Database session
        guest_telegram_id: Guest's Telegram ID
        property_id: Optional property ID to filter by
        limit: Maximum number of messages to retrieve
    
    Returns:
        List of message dictionaries with 'role' and 'content'
    """
    # Get recent guest messages and agent responses
    query = db.query(SystemLog).filter(
        SystemLog.event_type.in_([
            EventType.GUEST_MESSAGE,
            EventType.AGENT_RESPONSE,
            EventType.GUEST_INQUIRY
        ])
    ).order_by(SystemLog.created_at.desc()).limit(limit * 2)
    
    # Filter by guest if metadata contains guest_telegram_id
    messages = []
    for log in query.all():
        # Get metadata
        try:
            if hasattr(log, 'get_metadata'):
                metadata = log.get_metadata()
            elif hasattr(log, 'event_metadata') and log.event_metadata:
                metadata = json.loads(log.event_metadata) if isinstance(log.event_metadata, str) else log.event_metadata
            else:
                metadata = {}
        except:
            metadata = {}
        
        # Check if this log is for this guest
        log_guest_id = metadata.get('user_id') or metadata.get('guest_telegram_id')
        if log_guest_id != guest_telegram_id:
            continue
        
        # Check property_id if specified
        if property_id and log.property_id != property_id:
            continue
        
        # Determine role
        if log.event_type == EventType.GUEST_MESSAGE:
            role = "user"
            content = metadata.get('text') or log.message
        elif log.event_type in [EventType.AGENT_RESPONSE, EventType.GUEST_INQUIRY]:
            role = "assistant"
            content = log.message
        else:
            continue
        
        if content and len(content.strip()) > 0:
            messages.append({"role": role, "content": content})
    
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    
    return messages[-limit:] if len(messages) > limit else messages


def extract_dates_from_history(conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Extract check-in and check-out dates from conversation history.
    
    Args:
        conversation_history: List of conversation messages
    
    Returns:
        Dictionary with 'check_in' and 'check_out' dates if found, None otherwise
    """
    import re
    from datetime import datetime
    
    # Common date patterns - including "24th Nov - 30th Nov 2025"
    date_patterns = [
        r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s*[-–—]\s*\d{1,2}(?:st|nd|rd|th)?\s+\w+(?:\s+\d{4})?)',  # "24th Nov - 30th Nov 2025"
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # MM-DD-YYYY or DD-MM-YYYY
        r'(\w+\s+\d{1,2},?\s+\d{4})',  # December 1, 2025
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
    ]
    
    dates_found = []
    for msg in conversation_history:
        text = msg.get('content', '')
        
        # First try to find date ranges (e.g., "24th Nov - 30th Nov 2025")
        range_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s*[-–—]\s*(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)(?:\s+(\d{4}))?'
        range_match = re.search(range_pattern, text, re.IGNORECASE)
        if range_match:
            day1, month1, day2, month2, year = range_match.groups()
            year = year or str(datetime.now().year)
            try:
                # Parse first date
                date1_str = f"{day1} {month1} {year}"
                date1 = datetime.strptime(date1_str, "%d %b %Y")
                # Parse second date
                date2_str = f"{day2} {month2} {year}"
                date2 = datetime.strptime(date2_str, "%d %b %Y")
                return {
                    "check_in": date1.strftime('%Y-%m-%d'),
                    "check_out": date2.strftime('%Y-%m-%d')
                }
            except:
                # Try full month names
                try:
                    date1 = datetime.strptime(f"{day1} {month1} {year}", "%d %B %Y")
                    date2 = datetime.strptime(f"{day2} {month2} {year}", "%d %B %Y")
                    return {
                        "check_in": date1.strftime('%Y-%m-%d'),
                        "check_out": date2.strftime('%Y-%m-%d')
                    }
                except:
                    pass
        
        # Try other patterns
        for pattern in date_patterns[1:]:  # Skip first pattern (already handled)
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates_found.extend(matches)
    
    # Try to parse individual dates
    parsed_dates = []
    for date_str in dates_found[:4]:  # Limit to first 4 dates found
        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y']:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    parsed_dates.append(parsed)
                    break
                except:
                    continue
        except:
            continue
    
    if len(parsed_dates) >= 2:
        # Assume first is check-in, second is check-out
        return {
            "check_in": parsed_dates[0].strftime('%Y-%m-%d'),
            "check_out": parsed_dates[1].strftime('%Y-%m-%d')
        }
    
    return None

