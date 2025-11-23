# Booking Conversation Fix Plan

## Goal
Ensure the end-to-end guest ↔ host booking workflow works flawlessly:

1. Guest inquiries, negotiates, and confirms booking.
2. Bot references existing context (dates, negotiated price) without repeating questions.
3. Payment screenshot flow collects name + bank, sends to host, and awaits approval.
4. Host approval/denial notifies guest and updates booking/payment status.

## Constraints
- Must rely on existing FastAPI + Telegram bots + SQLite without introducing new services.
- Plan/execute/test sequentially; update documentation after each phase.
- All new documentation lives in `docs/booking-flow-*` folders.

## Work Breakdown

### 1. Conversation Memory & Negotiation Reliability
- [ ] Persist dates and negotiation results immediately after they occur.
- [ ] Ensure `get_conversation_context()` and `get_context_summary_for_llm()` pull the latest metadata filtered by property + guest.
- [ ] Pass richer context + recent history to the LLM to stop it from re-asking for dates or negotiation info.
- [ ] Adjust booking-intent guardrails so “yes / proceed” flows straight into payment without repeated prompts.

### 2. Payment Screenshot Intake
- [ ] Enforce host payment methods in DB and expose via API prompt.
- [ ] When guest uploads screenshot, capture:
  - file path
  - customer full name
  - bank name (JazzCash/SadaPay/EasyPaisa/etc.)
  - derived booking reference
- [ ] If metadata missing, request only the missing pieces rather than restarting the flow.

### 3. Host Notification & Decision Loop
- [ ] Expand host bot handler so payment notification includes:
  - guest name & Telegram
  - property + booking dates
  - negotiated price
  - bank name + screenshot
- [ ] Host replies “yes” or “no”; system updates booking/payment status, informs guest, and logs event.

### 4. Testing & Observability
- [ ] Create scripted conversation simulation that mimics inquiry → negotiation → payment → approval.
- [ ] Log every major step (guest intent, agent response, payment receipt, host decision) to `SystemLog`.
- [ ] Capture test transcript & DB snapshots into `docs/booking-flow-tests/README.md`.

## Deliverables
1. **Code fixes** across agents, bots, and utils.
2. **Execution summary** in `docs/booking-flow-execution/README.md`.
3. **Test log** in `docs/booking-flow-tests/README.md` with transcript + assertions.

## Acceptance Criteria
- Bot never re-asks for dates once provided.
- Negotiated price sticks to the provided dates; changes when dates change.
- Payment instructions show real host payment methods or clearly state missing data.
- Uploading screenshot without metadata triggers targeted prompts, not restart.
- Host receives screenshot and details, can approve/deny, and guest is notified accordingly.
- Automated test run demonstrates the full happy path in the test README.

