# Booking Flow Test Log

This document captures the checklist the user can follow while performing Telegram end-to-end testing. Update the “Result” column as you validate each scenario.

| # | Scenario | Steps | Expected Outcome | Result |
|---|----------|-------|------------------|--------|
| 1 | Conversation memory | Provide dates once, then negotiate price | Bot references the stored dates, never re-asks, and shows negotiated total | ☐ |
| 2 | Duplicate payment prompt guard | Say “yes” multiple times after negotiation | Bot only asks “Do we continue to payment?” once, then shows payment methods immediately | ☐ |
| 3 | Payment metadata enforcement | Send screenshot without name/bank | Bot asks specifically for the missing fields, remembers the screenshot, and resumes once data arrives | ☐ |
| 4 | Host notification | Upload screenshot + details | Host bot receives property, guest, amount, bank info, and screenshot | ☐ |
| 5 | Host approval path | Host replies “yes” | Guest receives confirmation message; booking/payment marked approved | ☐ |
| 6 | Host rejection path | Host replies “no” | Guest receives rejection message; booking/payment marked rejected | ☐ |

### Notes
- All backend logging occurs in `system_logs`; to inspect, use any SQLite browser and filter by `event_type`.
- If any scenario fails, jot details below so they can be revisited quickly.

```
Additional Notes:
- 
- 
```

