# Bot Context Memory Fix - Complete

## Issue
Bot was not remembering dates from conversation history and asking for them repeatedly, especially during negotiation.

## Root Cause
1. Negotiation logic was re-extracting dates instead of using `current_dates` already extracted from context
2. Negotiation only triggered when both price AND dates were found
3. Context summary wasn't being emphasized strongly enough
4. Dates weren't being used automatically when negotiation was requested

## Fixes Applied

### 1. Use Already-Extracted Dates
- Changed negotiation logic to use `current_dates` (already extracted from context)
- No longer re-extracts dates unnecessarily
- Falls back to history extraction only if `current_dates` is None

### 2. Negotiation Without Specific Price
- Now handles negotiation requests even when no specific price is mentioned
- For 3+ nights: Offers 5% discount (3-6 nights) or 10% discount (7+ nights)
- For <3 nights: Explains no discount available

### 3. Stronger Context Instructions
- Enhanced context summary message to emphasize using dates automatically
- Added explicit instruction: "DO NOT ask for dates that are already in this context"

### 4. Better Date Extraction
- Dates are extracted from conversation history BEFORE negotiation check
- Dates from context are used automatically in negotiation logic
- Clearer error handling when dates are missing

## Code Changes

### `agents/inquiry_booking_agent.py`:

1. **Line ~485**: Changed to use `current_dates` instead of re-extracting
   ```python
   dates = current_dates  # Use dates already extracted from context
   ```

2. **Line ~515**: Changed condition from `if price_matches and dates:` to `if dates:`
   - Now negotiates even without specific price mentioned

3. **Line ~530-550**: Added logic for negotiation without specific price
   - Calculates discount based on stay length
   - Offers appropriate discount percentage

4. **Line ~368**: Enhanced context summary message
   - Added "CRITICAL" emphasis
   - Added explicit instruction about using dates automatically

## Testing

The bot should now:
- ✅ Remember dates from conversation history
- ✅ Use dates automatically during negotiation
- ✅ Offer discounts even when no specific price is mentioned
- ✅ Never ask for dates if they're already in context
- ✅ Work correctly with the conversation flow shown by user

## Expected Behavior

**User:** "24th Nov 2025 - 30th Nov 2025"
**Bot:** [Remembers dates, calculates price]

**User:** "I'm staying for a long duration is there a way we can negotiate on the price?"
**Bot:** [Uses dates from context, offers discount for 6 nights, doesn't ask for dates]

**User:** "So no discounts or lower price?"
**Bot:** [Uses dates from context, explains discount already offered, doesn't ask for dates]

