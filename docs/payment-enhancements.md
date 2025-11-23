# Payment Workflow Enhancements

## Overview
Enhanced the payment workflow to include host bank details, customer payment information collection, and improved host verification process.

---

## Database Changes

### Host Model (`database/models.py`)
- **Added:** `payment_methods` column (Text, JSON array)
  - Stores list of payment methods with bank name and account number
  - Helper methods: `get_payment_methods()`, `set_payment_methods()`

### Booking Model (`database/models.py`)
- **Added:** `customer_name` column (String)
  - Customer's full name who sent the payment
- **Added:** `customer_bank_name` column (String)
  - Bank name customer sent payment from (e.g., JazzCash, SadaPay, EasyPaisa)
- **Added:** `customer_payment_details` column (Text, JSON)
  - Additional customer payment details (extensible)
  - Helper methods: `get_customer_payment_details()`, `set_customer_payment_details()`

**Note:** Database migration needed - existing databases will need these columns added.

---

## New Features

### 1. Host Payment Methods Setup

**API Endpoints:**
- `POST /api/host/{host_id}/payment-methods` - Add payment method
  - Parameters: `bank_name`, `account_number`
- `GET /api/host/{host_id}/payment-methods` - Get all payment methods
- `GET /api/host` - Now includes `payment_methods` in response

**Config Manager:**
- `ConfigManager.add_payment_method()` - Add payment method to host
- `ConfigManager.get_payment_methods()` - Get all payment methods for host

**Example Payment Methods:**
```json
[
  {"bank_name": "JazzCash", "account_number": "03001234567"},
  {"bank_name": "SadaPay", "account_number": "1234567890123"},
  {"bank_name": "EasyPaisa", "account_number": "03001234567"},
  {"bank_name": "HBL", "account_number": "1234567890123456"}
]
```

---

### 2. Enhanced Booking Flow

**New Flow:**
1. Guest negotiates price and agrees to book
2. Bot asks: **"Do we continue to payment?"**
3. Guest confirms: "yes"
4. Bot displays **all payment methods** with bank names and account numbers
5. Bot asks for payment screenshot **along with**:
   - Customer's full name
   - Bank name customer is sending from

**Agent Changes (`agents/inquiry_booking_agent.py`):**
- Retrieves payment methods from host configuration
- Asks "Do we continue to payment?" before showing payment details
- Displays all bank details when showing payment methods
- Requests customer details along with screenshot

---

### 3. Customer Details Collection

**Guest Bot (`api/telegram/guest_bot.py`):**
- Extracts customer name and bank name from message text
- Supports formats:
  - "Name: John Doe"
  - "Bank: JazzCash"
  - Or combined: "Name: John Doe\nBank: JazzCash"
- If details missing, asks guest to provide them
- Stores customer details in booking record

**Payment Handler (`api/utils/payment.py`):**
- Saves `customer_name` and `customer_bank_name` to booking
- Includes customer details in booking metadata

---

### 4. Enhanced Host Verification

**Host Notification (`api/telegram/host_bot.py`):**
- Shows customer name and bank name customer sent from
- **Important:** Prompts host to check the specific bank account
- Message format:
  ```
  💰 Payment Verification Request
  
  Booking ID: 123
  Guest: John Doe
  Property: Beautiful Apartment
  Amount: $600.00
  Dates: 2025-11-24 to 2025-11-30
  
  📋 Customer Payment Details:
  • Customer Name: John Doe
  • Bank Sent From: JazzCash
  
  ⚠️ IMPORTANT: Please check your JazzCash account for the payment.
  
  After verifying, reply:
  ✅ 'yes' if payment received
  ❌ 'no' if payment not found
  ```

**Host Bot Handler:**
- Finds pending bookings for host's properties
- Approves/rejects based on host response
- Notifies guest of approval/rejection

---

## Updated Files

1. **`database/models.py`**
   - Added `payment_methods` to Host model
   - Added `customer_name`, `customer_bank_name`, `customer_payment_details` to Booking model

2. **`config/config_manager.py`**
   - Added `add_payment_method()` function
   - Added `get_payment_methods()` function

3. **`api/routes/properties.py`**
   - Added `POST /api/host/{host_id}/payment-methods` endpoint
   - Added `GET /api/host/{host_id}/payment-methods` endpoint
   - Updated `GET /api/host` to include payment methods

4. **`agents/inquiry_booking_agent.py`**
   - Updated to retrieve and display payment methods from host
   - Changed booking flow to ask "Do we continue to payment?" first
   - Enhanced payment instructions to include all bank details

5. **`api/telegram/guest_bot.py`**
   - Enhanced payment screenshot handling to extract customer details
   - Asks for customer name and bank name if not provided

6. **`api/utils/payment.py`**
   - Updated to save customer details to booking
   - Includes customer information in booking creation

7. **`api/telegram/host_bot.py`**
   - Enhanced payment notification to show customer details
   - Prompts host to check specific bank account

---

## Usage

### Setting Up Payment Methods (via API)

```bash
# Add JazzCash
curl -X POST "http://localhost:8000/api/host/1/payment-methods?bank_name=JazzCash&account_number=03001234567"

# Add SadaPay
curl -X POST "http://localhost:8000/api/host/1/payment-methods?bank_name=SadaPay&account_number=1234567890123"

# Get all payment methods
curl "http://localhost:8000/api/host/1/payment-methods"
```

### Booking Flow Example

1. **Guest:** "I want to book for 24th Nov - 30th Nov"
2. **Bot:** "Great! Total is $600. Do we continue to payment?"
3. **Guest:** "Yes"
4. **Bot:** "Please send payment to one of these accounts:
   - JazzCash: 03001234567
   - SadaPay: 1234567890123
   - EasyPaisa: 03001234567
   
   Please send the payment screenshot along with:
   - Your full name
   - Bank name you're sending from"
5. **Guest:** [Sends screenshot with message: "Name: John Doe\nBank: JazzCash"]
6. **Host:** [Receives notification with customer details and bank to check]
7. **Host:** "yes" [After verifying in JazzCash account]
8. **Guest:** [Receives confirmation]

---

## Database Migration

**Important:** If you have an existing database, you need to add the new columns:

```sql
-- Add payment_methods to hosts table
ALTER TABLE hosts ADD COLUMN payment_methods TEXT;

-- Add customer details to bookings table
ALTER TABLE bookings ADD COLUMN customer_name TEXT;
ALTER TABLE bookings ADD COLUMN customer_bank_name TEXT;
ALTER TABLE bookings ADD COLUMN customer_payment_details TEXT;
```

Or delete the existing database and let it recreate with the new schema.

---

## Testing

1. **Add payment methods** via API
2. **Start booking flow** via Telegram guest bot
3. **Verify** bot asks "Do we continue to payment?"
4. **Verify** bot shows all payment methods
5. **Upload screenshot** with customer details
6. **Check host bot** receives notification with bank name
7. **Approve/reject** via host bot
8. **Verify** guest receives confirmation/rejection

---

## Next Steps

- [ ] Add Telegram bot command for hosts to add payment methods
- [ ] Enhance customer details extraction (support more formats)
- [ ] Add validation for bank names
- [ ] Add ability to remove payment methods
- [ ] Add payment method editing

