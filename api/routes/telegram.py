"""
Telegram webhook endpoints.

These endpoints receive webhooks from Telegram bots.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import json

from database.db import get_db
from api.telegram.guest_bot import handle_guest_message
from api.telegram.host_bot import handle_host_message

router = APIRouter()


@router.post("/webhook/guest")
async def guest_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for guest Telegram bot.
    
    Receives updates from Telegram and processes guest messages.
    """
    try:
        # Get webhook data
        update_data = await request.json()
        
        # Process the message
        result = await handle_guest_message(db, update_data)
        
        return JSONResponse(content={
            "status": "ok",
            "result": result
        })
    
    except Exception as e:
        print(f"Error processing guest webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.post("/webhook/host")
async def host_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for host Telegram bot.
    
    Receives updates from Telegram and processes host messages.
    """
    try:
        # Get webhook data
        update_data = await request.json()
        
        # Process the message
        result = await handle_host_message(db, update_data)
        
        return JSONResponse(content={
            "status": "ok",
            "result": result
        })
    
    except Exception as e:
        print(f"Error processing host webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@router.get("/webhook/guest")
async def verify_guest_webhook():
    """Webhook verification for Telegram (GET request)."""
    return {"status": "webhook endpoint ready", "bot": "guest"}


@router.get("/webhook/host")
async def verify_host_webhook():
    """Webhook verification for Telegram (GET request)."""
    return {"status": "webhook endpoint ready", "bot": "host"}
