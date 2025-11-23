# Model Name Fix - Permanent Solution

## Issue
The model name `qvq-max-latest` was not supported by DashScope OpenAI compatibility mode, causing errors.

## Permanent Fix Applied

### Files Updated:
1. **`agents/base_agent.py`**
   - Changed default model from `"qvq-max-latest"` to `"qwen-max"`
   - Updated docstring to reflect new model name

2. **`agents/inquiry_booking_agent.py`**
   - Changed model parameter from `"qvq-max-latest"` to `"qwen-max"`

### Model Name Change:
- **OLD:** `qvq-max-latest` ❌ (Not supported)
- **NEW:** `qwen-max` ✅ (Verified working)

## Verification
- ✅ All references to old model name removed
- ✅ Model tested and confirmed working
- ✅ Default model updated in base class
- ✅ All agents now use `qwen-max`

## Important Note
**The server must be restarted** for the changes to take effect. The running uvicorn process needs to reload the updated code.

To restart:
1. Stop the current uvicorn server (Ctrl+C)
2. Start it again: `uvicorn api.main:app --reload`

The fix is permanent - all future agent instances will use `qwen-max` by default.

