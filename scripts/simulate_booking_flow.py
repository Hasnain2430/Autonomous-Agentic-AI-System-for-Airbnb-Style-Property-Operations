import os
import asyncio
import shutil
from typing import List, Tuple

# Use an isolated SQLite file for the simulation
os.environ.setdefault("DATABASE_PATH", "./database/test_booking_flow.db")
os.environ.setdefault("DASHSCOPE_API_KEY", "DUMMY_KEY")

from database.db import reset_db, get_db_session
from config.config_manager import ConfigManager
from database.models import Property
from agents.inquiry_booking_agent import InquiryBookingAgent
from api.utils.logging import log_event, EventType
from api.utils.conversation_context import get_conversation_context
from api.utils import payment as payment_utils
from api.telegram import host_bot
from api.telegram import base as telegram_base

GUEST_ID = "GUEST_SIM"


def _ensure_property(db):
    """Create or fetch a demo property with host payment methods."""
    host = ConfigManager.create_host(
        db=db,
        name="Simulation Host",
        email="host@example.com",
        telegram_id="HOST_SIM",
        phone="+10000000000",
        preferred_language="en",
    )
    try:
        property_obj = ConfigManager.create_property(
            db=db,
            host_id=host.id,
            property_identifier="SIM-PROP-001",
            name="Simulation Apartment",
            location="123 Demo St",
            base_price=120.0,
            min_price=90.0,
            max_price=150.0,
            max_guests=4,
            check_in_time="14:00",
            check_out_time="11:00",
        )
    except ValueError:
        property_obj = db.query(Property).filter(Property.property_identifier == "SIM-PROP-001").first()
    
    if not host.get_payment_methods():
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="JazzCash Wallet",
            account_number="0300-0000000",
            account_name="Simulation Host",
            instructions="Send receipt once paid"
        )
        ConfigManager.add_payment_method(
            db=db,
            host_id=host.id,
            bank_name="EasyPaisa Wallet",
            account_number="0311-1111111",
            account_name="Simulation Host",
            instructions="Use booking dates as reference"
        )
    
    return host, property_obj


def _log_guest_message(db, property_id: int, text: str, history: List[dict]) -> None:
    """Persist a guest message for context and append to local history."""
    log_event(
        db=db,
        event_type=EventType.GUEST_MESSAGE,
        agent_name="Simulation",
        property_id=property_id,
        message=f"Guest: {text}",
        metadata={"user_id": GUEST_ID, "guest_telegram_id": GUEST_ID, "text": text, "property_id": property_id},
    )
    history.append({"role": "user", "content": text})


def _log_agent_response(db, property_id: int, agent_name: str, response: str, metadata: dict, history: List[dict]) -> None:
    """Persist agent response metadata for conversation context."""
    history.append({"role": "assistant", "content": response})
    log_event(
        db=db,
        event_type=EventType.AGENT_RESPONSE,
        agent_name=agent_name,
        property_id=property_id,
        message=response,
        metadata={"user_id": GUEST_ID, "guest_telegram_id": GUEST_ID, "property_id": property_id, **(metadata or {})},
    )


async def run_simulation() -> Tuple[List[Tuple[str, str]], str]:
    """Run a full inquiry → negotiation → payment → approval simulation."""
    reset_db()
    db = get_db_session()
    host, property_obj = _ensure_property(db)
    agent = InquiryBookingAgent()
    scripted_responses = iter([
        "Yes, Simulation Apartment is available for your requested timeframe.",
        "Great choice! 24th Nov 2025 to 30th Nov 2025 is open and fits perfectly.",
        "Because you're staying 6 nights, I can offer $95 per night for a total of $570.",
        "Perfect. I'll hold those dates for you. Do we continue to payment?",
        "Awesome! Once you're ready, send the payment screenshot with your name and bank details.",
    ])
    
    def fake_llm_response(self, messages, temperature=0.7):
        try:
            return next(scripted_responses)
        except StopIteration:
            return "Just let me know if you need anything else about your stay."
    
    agent.get_llm_response = fake_llm_response.__get__(agent, InquiryBookingAgent)
    convo_history: List[dict] = []
    transcript: List[Tuple[str, str]] = []
    
    messages = [
        "Hi, is the Simulation Apartment available later this month?",
        "I'd like to stay from 24th Nov 2025 to 30th Nov 2025",
        "I'm staying 6 nights, can you do better on price?",
        "yes this works",
        "yes",
    ]
    
    for msg in messages:
        _log_guest_message(db, property_obj.id, msg, convo_history)
        transcript.append(("Guest", msg))
        result = agent.handle_inquiry(
            db=db,
            message=msg,
            property_id=property_obj.id,
            guest_telegram_id=GUEST_ID,
            conversation_history=convo_history[-10:],
        )
        response = result.get("response", "")
        transcript.append(("Bot", response))
        _log_agent_response(db, property_obj.id, agent.agent_name, response, result.get("metadata"), convo_history)
    
    # Prepare dummy screenshot file
    os.makedirs("tests/data", exist_ok=True)
    dummy_path = "tests/data/dummy_payment.jpg"
    with open(dummy_path, "wb") as handle:
        handle.write(b"fake-image")
    
    async def fake_download(*_, save_path: str, **__):
        shutil.copy(dummy_path, save_path)
        return True
    
    payment_utils.download_telegram_photo = fake_download
    
    async def fake_host_message(chat_id: str, message: str, photo_path: str | None = None):
        print("\n[Host Notification]")
        print(f"Chat: {chat_id}")
        print(message)
        if photo_path:
            print(f"Photo: {photo_path}")
        return True
    
    async def fake_send_payment_request(db, host_telegram_id, booking, screenshot_path, booking_details):
        return await fake_host_message(
            host_telegram_id,
            f"Payment request for {booking_details['property_name']} ${booking_details['amount']:.2f}",
            screenshot_path,
        )
    
    host_bot.send_host_message = fake_host_message
    host_bot.send_payment_approval_request = fake_send_payment_request
    
    async def fake_guest_message(bot_token: str, chat_id: str, message: str, **_):
        print(f"\n[Guest Notification] ({chat_id})")
        print(message)
        return True
    
    telegram_base.send_message = fake_guest_message
    
    context = get_conversation_context(db, GUEST_ID, property_obj.id)
    booking_details = {
        "check_in": context["dates"]["check_in"],
        "check_out": context["dates"]["check_out"],
        "final_price": context.get("negotiated_price"),
        "number_of_guests": 2,
        "customer_name": "Hasnain Ibrar",
        "customer_bank_name": "JazzCash",
        "guest_name": "Hasnain Ibrar",
    }
    
    booking = await payment_utils.handle_payment_screenshot(
        db=db,
        guest_telegram_id=GUEST_ID,
        file_id="SIMULATED_FILE_ID",
        property_id=property_obj.id,
        booking_details=booking_details,
    )
    if booking:
        await payment_utils.send_payment_to_host(db=db, booking=booking)
        await payment_utils.confirm_booking(db=db, booking_id=booking.id)
    
    transcript.append(("System", "Payment screenshot received and sent to host."))
    transcript.append(("System", "Host approved payment and guest was notified."))
    
    return transcript, property_obj.name


if __name__ == "__main__":
    conversation, property_name = asyncio.run(run_simulation())
    print("\n=== Simulation Transcript ===")
    for speaker, text in conversation:
        print(f"{speaker}: {text}\n")

