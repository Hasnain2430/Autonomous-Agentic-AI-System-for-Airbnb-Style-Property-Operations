"""
Bot Testing Script

Tests all Telegram bot functionalities by simulating user interactions.
Calls webhook endpoints directly to test guest and host bot flows.

Usage:
    python scripts/test_bots.py [--host-only] [--guest-only] [--full-flow]
"""

import asyncio
import aiohttp
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import random
import string

# Configuration
BASE_URL = "http://localhost:8000"
GUEST_WEBHOOK = f"{BASE_URL}/api/webhook/guest"
HOST_WEBHOOK = f"{BASE_URL}/api/webhook/host"

# Test user IDs (simulated Telegram IDs)
TEST_GUEST_ID = f"test_guest_{random.randint(10000, 99999)}"
TEST_HOST_ID = f"test_host_{random.randint(10000, 99999)}"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

# Fix Windows encoding
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_test(name: str, passed: bool, details: str = ""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"  {status} {name}")
    if details and not passed:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")


def print_section(name: str):
    print(f"\n{Colors.CYAN}▶ {name}{Colors.END}")


def create_telegram_update(
    user_id: str,
    text: str = None,
    photo: bool = False,
    first_name: str = "Test User",
    chat_type: str = "private"
) -> Dict[str, Any]:
    """Create a simulated Telegram update object."""
    update_id = random.randint(100000, 999999)
    message_id = random.randint(1000, 9999)
    
    update = {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "from": {
                "id": int(user_id.split("_")[-1]) if "_" in user_id else int(user_id),
                "is_bot": False,
                "first_name": first_name,
                "language_code": "en"
            },
            "chat": {
                "id": int(user_id.split("_")[-1]) if "_" in user_id else int(user_id),
                "first_name": first_name,
                "type": chat_type
            },
            "date": int(datetime.now().timestamp())
        }
    }
    
    if text:
        update["message"]["text"] = text
    
    if photo:
        update["message"]["photo"] = [
            {"file_id": f"test_photo_{random.randint(1000, 9999)}", "width": 100, "height": 100},
            {"file_id": f"test_photo_{random.randint(1000, 9999)}", "width": 320, "height": 320},
            {"file_id": f"test_photo_{random.randint(1000, 9999)}", "width": 800, "height": 800}
        ]
    
    return update


async def send_message(session: aiohttp.ClientSession, webhook_url: str, update: Dict) -> Dict:
    """Send a message to the webhook and get response."""
    try:
        async with session.post(webhook_url, json=update, timeout=30) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"HTTP {response.status}", "text": await response.text()}
    except asyncio.TimeoutError:
        return {"error": "Timeout"}
    except Exception as e:
        return {"error": str(e)}


async def test_guest_bot_commands(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test guest bot commands."""
    results = {}
    
    print_section("Testing Guest Bot Commands")
    
    # Test /start
    update = create_telegram_update(TEST_GUEST_ID, "/start")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response and response.get("status") != "error"
    results["guest_start"] = passed
    print_test("/start command", passed, str(response.get("error", "")))
    
    await asyncio.sleep(0.5)
    
    # Test /inquiry
    update = create_telegram_update(TEST_GUEST_ID, "/inquiry")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["guest_inquiry"] = passed
    print_test("/inquiry command", passed, str(response.get("error", "")))
    
    await asyncio.sleep(0.5)
    
    # Test /qna
    update = create_telegram_update(TEST_GUEST_ID, "/qna")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["guest_qna"] = passed
    print_test("/qna command", passed, str(response.get("error", "")))
    
    await asyncio.sleep(0.5)
    
    # Test /clear
    update = create_telegram_update(TEST_GUEST_ID, "/clear")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["guest_clear"] = passed
    print_test("/clear command", passed, str(response.get("error", "")))
    
    await asyncio.sleep(0.5)
    
    # Test /book_property
    update = create_telegram_update(TEST_GUEST_ID, "/book_property")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["guest_book_property"] = passed
    print_test("/book_property command", passed, str(response.get("error", "")))
    
    return results


async def test_guest_booking_flow(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test complete guest booking flow."""
    results = {}
    guest_id = f"booking_test_{random.randint(10000, 99999)}"
    
    print_section("Testing Guest Booking Flow")
    
    # Step 1: Start booking
    update = create_telegram_update(guest_id, "/book_property")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_start"] = passed
    print_test("Start booking (/book_property)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 2: Select property (send "1" to select first property)
    update = create_telegram_update(guest_id, "1")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_select_property"] = passed
    print_test("Select property (1)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 3: Provide check-in date
    check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    update = create_telegram_update(guest_id, check_in)
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_checkin"] = passed
    print_test(f"Check-in date ({check_in})", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 4: Provide check-out date
    check_out = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    update = create_telegram_update(guest_id, check_out)
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_checkout"] = passed
    print_test(f"Check-out date ({check_out})", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 5: Number of guests
    update = create_telegram_update(guest_id, "2")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_guests"] = passed
    print_test("Number of guests (2)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 6: Customer name
    update = create_telegram_update(guest_id, "Test Customer")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_name"] = passed
    print_test("Customer name (Test Customer)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 7: Bank name
    update = create_telegram_update(guest_id, "JazzCash")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["booking_bank"] = passed
    print_test("Bank name (JazzCash)", passed)
    
    # Note: Screenshot upload would require actual file handling
    # which can't be fully simulated without Telegram's file system
    
    return results


async def test_guest_qna_flow(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test guest QnA functionality."""
    results = {}
    guest_id = f"qna_test_{random.randint(10000, 99999)}"
    
    print_section("Testing Guest QnA Flow")
    
    # Start QnA
    update = create_telegram_update(guest_id, "/qna")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["qna_start"] = passed
    print_test("Start QnA (/qna)", passed)
    
    await asyncio.sleep(0.5)
    
    # Ask about WiFi
    update = create_telegram_update(guest_id, "What is the WiFi password?")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["qna_wifi"] = passed
    print_test("Ask about WiFi", passed)
    
    await asyncio.sleep(0.5)
    
    # Ask about parking
    update = create_telegram_update(guest_id, "Is parking available?")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["qna_parking"] = passed
    print_test("Ask about parking", passed)
    
    await asyncio.sleep(0.5)
    
    # Ask about check-in
    update = create_telegram_update(guest_id, "What time is check-in?")
    response = await send_message(session, GUEST_WEBHOOK, update)
    passed = "error" not in response
    results["qna_checkin"] = passed
    print_test("Ask about check-in time", passed)
    
    return results


async def test_host_bot_commands(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test host bot commands."""
    results = {}
    
    print_section("Testing Host Bot Commands")
    
    # Test /start
    update = create_telegram_update(TEST_HOST_ID, "/start", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["host_start"] = passed
    print_test("/start command", passed, str(response.get("error", "")))
    
    await asyncio.sleep(0.5)
    
    # Test /help
    update = create_telegram_update(TEST_HOST_ID, "/help", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["host_help"] = passed
    print_test("/help command", passed, str(response.get("error", "")))
    
    return results


async def test_host_setup_flow(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test host setup flow."""
    results = {}
    host_id = f"setup_test_{random.randint(10000, 99999)}"
    
    print_section("Testing Host Setup Flow")
    
    # Step 1: Start setup
    update = create_telegram_update(host_id, "/setup", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["setup_start"] = passed
    print_test("Start setup (/setup)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 2: Provide name
    update = create_telegram_update(host_id, "Test Host Name", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["setup_name"] = passed
    print_test("Provide name", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 3: Provide email
    update = create_telegram_update(host_id, "testhost@example.com", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["setup_email"] = passed
    print_test("Provide email", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 4: Provide phone (skip)
    update = create_telegram_update(host_id, "skip", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["setup_phone"] = passed
    print_test("Provide phone (skip)", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 5: Provide bank name
    update = create_telegram_update(host_id, "HBL Bank", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["setup_bank_name"] = passed
    print_test("Provide bank name", passed)
    
    await asyncio.sleep(0.5)
    
    # Step 6: Provide bank account
    update = create_telegram_update(host_id, "1234567890", first_name="Test Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response and response.get("status") == "setup_complete"
    results["setup_bank_account"] = passed
    print_test("Provide bank account (complete)", passed)
    
    return results


async def test_host_add_property_flow(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test host add property flow."""
    results = {}
    host_id = f"property_test_{random.randint(10000, 99999)}"
    
    print_section("Testing Host Add Property Flow")
    
    # First, do quick setup
    update = create_telegram_update(host_id, "/setup", first_name="Property Host")
    await send_message(session, HOST_WEBHOOK, update)
    await asyncio.sleep(0.3)
    
    for msg in ["Property Host", "prophost@test.com", "skip", "EasyPaisa", "03001234567"]:
        update = create_telegram_update(host_id, msg, first_name="Property Host")
        await send_message(session, HOST_WEBHOOK, update)
        await asyncio.sleep(0.3)
    
    # Now add property
    update = create_telegram_update(host_id, "/add_property", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_start"] = passed
    print_test("Start add property (/add_property)", passed)
    
    await asyncio.sleep(0.5)
    
    # Property identifier
    prop_id = f"TEST-{random.randint(100, 999)}"
    update = create_telegram_update(host_id, prop_id, first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_identifier"] = passed
    print_test(f"Property identifier ({prop_id})", passed)
    
    await asyncio.sleep(0.5)
    
    # Property name
    update = create_telegram_update(host_id, "Test Property", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_name"] = passed
    print_test("Property name", passed)
    
    await asyncio.sleep(0.5)
    
    # Location
    update = create_telegram_update(host_id, "Test Location, Islamabad", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_location"] = passed
    print_test("Property location", passed)
    
    await asyncio.sleep(0.5)
    
    # Base price
    update = create_telegram_update(host_id, "5000", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_price"] = passed
    print_test("Base price (5000)", passed)
    
    await asyncio.sleep(0.5)
    
    # Max guests
    update = create_telegram_update(host_id, "4", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_guests"] = passed
    print_test("Max guests (4)", passed)
    
    await asyncio.sleep(0.5)
    
    # Check-in time
    update = create_telegram_update(host_id, "14:00", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_checkin"] = passed
    print_test("Check-in time (14:00)", passed)
    
    await asyncio.sleep(0.5)
    
    # Check-out time
    update = create_telegram_update(host_id, "11:00", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_checkout"] = passed
    print_test("Check-out time (11:00)", passed)
    
    await asyncio.sleep(0.5)
    
    # WiFi available?
    update = create_telegram_update(host_id, "yes", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_wifi"] = passed
    print_test("WiFi available (yes)", passed)
    
    await asyncio.sleep(0.5)
    
    # WiFi name
    update = create_telegram_update(host_id, "TestWiFi", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_wifi_name"] = passed
    print_test("WiFi name (TestWiFi)", passed)
    
    await asyncio.sleep(0.5)
    
    # WiFi password
    update = create_telegram_update(host_id, "test123", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_wifi_password"] = passed
    print_test("WiFi password", passed)
    
    await asyncio.sleep(0.5)
    
    # AC available?
    update = create_telegram_update(host_id, "yes", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_ac"] = passed
    print_test("AC available (yes)", passed)
    
    await asyncio.sleep(0.5)
    
    # TV available?
    update = create_telegram_update(host_id, "yes", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_tv"] = passed
    print_test("TV available (yes)", passed)
    
    await asyncio.sleep(0.5)
    
    # Parking available?
    update = create_telegram_update(host_id, "no", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response
    results["property_parking"] = passed
    print_test("Parking available (no)", passed)
    
    await asyncio.sleep(0.5)
    
    # Kitchen available?
    update = create_telegram_update(host_id, "yes", first_name="Property Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = "error" not in response and response.get("status") == "property_added"
    results["property_kitchen"] = passed
    print_test("Kitchen available (yes) - Complete", passed)
    
    return results


async def test_host_cancel_flow(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test host cancel command during setup."""
    results = {}
    host_id = f"cancel_test_{random.randint(10000, 99999)}"
    
    print_section("Testing Host Cancel Flow")
    
    # Start setup
    update = create_telegram_update(host_id, "/setup", first_name="Cancel Host")
    await send_message(session, HOST_WEBHOOK, update)
    await asyncio.sleep(0.3)
    
    # Provide name
    update = create_telegram_update(host_id, "Cancel Test", first_name="Cancel Host")
    await send_message(session, HOST_WEBHOOK, update)
    await asyncio.sleep(0.3)
    
    # Cancel
    update = create_telegram_update(host_id, "/cancel", first_name="Cancel Host")
    response = await send_message(session, HOST_WEBHOOK, update)
    passed = response.get("status") == "cancelled"
    results["cancel_during_setup"] = passed
    print_test("Cancel during setup (/cancel)", passed)
    
    return results


async def test_metrics_endpoint(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Test metrics API endpoints."""
    results = {}
    
    print_section("Testing Metrics Endpoints")
    
    # Test /api/metrics
    try:
        async with session.get(f"{BASE_URL}/api/metrics") as response:
            passed = response.status == 200
            results["metrics_all"] = passed
            print_test("GET /api/metrics", passed)
    except Exception as e:
        results["metrics_all"] = False
        print_test("GET /api/metrics", False, str(e))
    
    await asyncio.sleep(0.3)
    
    # Test /api/metrics/summary
    try:
        async with session.get(f"{BASE_URL}/api/metrics/summary") as response:
            passed = response.status == 200
            results["metrics_summary"] = passed
            print_test("GET /api/metrics/summary", passed)
    except Exception as e:
        results["metrics_summary"] = False
        print_test("GET /api/metrics/summary", False, str(e))
    
    await asyncio.sleep(0.3)
    
    # Test /api/metrics/evaluation
    try:
        async with session.get(f"{BASE_URL}/api/metrics/evaluation") as response:
            passed = response.status == 200
            if passed:
                data = await response.json()
                has_scores = "evaluation_scores" in data
                has_grade = "grade" in data
                passed = has_scores and has_grade
            results["metrics_evaluation"] = passed
            print_test("GET /api/metrics/evaluation", passed)
    except Exception as e:
        results["metrics_evaluation"] = False
        print_test("GET /api/metrics/evaluation", False, str(e))
    
    return results


async def run_all_tests():
    """Run all bot tests."""
    print_header("BOT TESTING SCRIPT")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Guest ID: {TEST_GUEST_ID}")
    print(f"Test Host ID: {TEST_HOST_ID}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    async with aiohttp.ClientSession() as session:
        # Check if server is running
        try:
            async with session.get(f"{BASE_URL}/api/health") as response:
                if response.status != 200:
                    print(f"\n{Colors.RED}ERROR: Server not responding at {BASE_URL}{Colors.END}")
                    print("Make sure the FastAPI server is running:")
                    print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
                    return
        except Exception as e:
            print(f"\n{Colors.RED}ERROR: Cannot connect to server: {e}{Colors.END}")
            print("Make sure the FastAPI server is running:")
            print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
            return
        
        print(f"\n{Colors.GREEN}✓ Server is running{Colors.END}")
        
        # Run tests
        all_results.update(await test_guest_bot_commands(session))
        all_results.update(await test_guest_booking_flow(session))
        all_results.update(await test_guest_qna_flow(session))
        all_results.update(await test_host_bot_commands(session))
        all_results.update(await test_host_setup_flow(session))
        all_results.update(await test_host_add_property_flow(session))
        all_results.update(await test_host_cancel_flow(session))
        all_results.update(await test_metrics_endpoint(session))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in all_results.values() if v)
    failed = sum(1 for v in all_results.values() if not v)
    total = len(all_results)
    
    print(f"  Total Tests: {total}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.END}")
    print(f"  Success Rate: {passed/total*100:.1f}%")
    
    if failed > 0:
        print(f"\n{Colors.YELLOW}Failed Tests:{Colors.END}")
        for name, result in all_results.items():
            if not result:
                print(f"  - {name}")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all_results


async def run_guest_tests_only():
    """Run only guest bot tests."""
    print_header("GUEST BOT TESTS")
    
    all_results = {}
    
    async with aiohttp.ClientSession() as session:
        all_results.update(await test_guest_bot_commands(session))
        all_results.update(await test_guest_booking_flow(session))
        all_results.update(await test_guest_qna_flow(session))
    
    return all_results


async def run_host_tests_only():
    """Run only host bot tests."""
    print_header("HOST BOT TESTS")
    
    all_results = {}
    
    async with aiohttp.ClientSession() as session:
        all_results.update(await test_host_bot_commands(session))
        all_results.update(await test_host_setup_flow(session))
        all_results.update(await test_host_add_property_flow(session))
        all_results.update(await test_host_cancel_flow(session))
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Test Telegram bot functionalities")
    parser.add_argument("--guest-only", action="store_true", help="Run only guest bot tests")
    parser.add_argument("--host-only", action="store_true", help="Run only host bot tests")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="Base URL for API")
    
    args = parser.parse_args()
    
    global BASE_URL, GUEST_WEBHOOK, HOST_WEBHOOK
    BASE_URL = args.url
    GUEST_WEBHOOK = f"{BASE_URL}/api/webhook/guest"
    HOST_WEBHOOK = f"{BASE_URL}/api/webhook/host"
    
    if args.guest_only:
        asyncio.run(run_guest_tests_only())
    elif args.host_only:
        asyncio.run(run_host_tests_only())
    else:
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()

