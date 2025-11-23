# n8n Integration Setup Guide

This guide explains how to set up and test n8n integration with the FastAPI application.

## Prerequisites

- n8n installed and running (you mentioned you already have this)
- FastAPI server running on `http://localhost:8000` (or your configured port)
- ngrok running (for webhook testing, if needed)

## Step 1: Verify n8n is Running

1. Open your n8n interface (usually `http://localhost:5678`)
2. Make sure n8n is accessible and working

## Step 2: Test Connection to FastAPI

### Test 1: Health Check

1. In n8n, create a new workflow
2. Add an **HTTP Request** node
3. Configure it:
   - **Method:** GET
   - **URL:** `http://localhost:8000/api/health`
   - **Response Format:** JSON
4. Execute the workflow
5. You should see a response like:
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-11-23T...",
     "service": "Airbnb Property Operations Manager API"
   }
   ```

### Test 2: n8n Health Check

1. Add another **HTTP Request** node
2. Configure it:
   - **Method:** GET
   - **URL:** `http://localhost:8000/api/webhooks/n8n/health`
3. Execute - should return n8n integration status

## Step 3: Create Basic Test Workflow

### Simple Message Router Workflow

1. **Create a new workflow** in n8n
2. **Add nodes in this order:**

   **Node 1: Manual Trigger** (for testing)
   - Just use the default Manual Trigger node
   
   **Node 2: HTTP Request** (call FastAPI)
   - **Method:** GET
   - **URL:** `http://localhost:8000/api/health`
   - **Response Format:** JSON
   
   **Node 3: Set** (process response)
   - Set a value to store the response
   
3. **Connect the nodes:** Manual Trigger → HTTP Request → Set
4. **Execute the workflow** using the "Execute Workflow" button
5. **Check the results** - you should see the health check response

## Step 4: Test Webhook Endpoints

### Test Receiving Messages from n8n

1. **Create a new workflow**
2. **Add HTTP Request node:**
   - **Method:** POST
   - **URL:** `http://localhost:8000/api/webhooks/n8n/message`
   - **Body Content Type:** JSON
   - **Body:** 
     ```json
     {
       "test": "message from n8n",
       "timestamp": "2025-11-23"
     }
     ```
3. **Execute** - should return success response
4. **Check FastAPI logs** - you should see the message logged

### Test Trigger Endpoint

1. **Add HTTP Request node:**
   - **Method:** POST
   - **URL:** `http://localhost:8000/api/webhooks/n8n/trigger`
   - **Body Content Type:** JSON
   - **Body:**
     ```json
     {
       "workflow_type": "booking_confirmation",
       "payload": {
         "booking_id": 1,
         "property_id": 1
       }
     }
     ```
2. **Execute** - should return trigger acknowledgment

## Step 5: Create Webhook in n8n (for FastAPI to Call n8n)

1. **In n8n, create a new workflow**
2. **Add a Webhook node:**
   - **HTTP Method:** POST
   - **Path:** `test-webhook` (or any path you want)
   - **Response Mode:** Respond to Webhook
3. **Save the workflow**
4. **Copy the webhook URL** - it will look like:
   - `http://localhost:5678/webhook/test-webhook` (if n8n is local)
   - Or your n8n public URL if deployed
5. **Add a Set node** to process the incoming data
6. **Test the webhook** by calling it from FastAPI (we'll do this in Step 14)

## Available n8n Endpoints in FastAPI

### Receiving from n8n:
- `POST /api/webhooks/n8n/message` - Receive any message from n8n
- `POST /api/webhooks/n8n/trigger` - Trigger workflow request
- `POST /api/webhooks/n8n/booking-confirmed` - Booking confirmation handler
- `POST /api/webhooks/n8n/cleaning-scheduled` - Cleaning scheduled handler

### Health Checks:
- `GET /api/webhooks/n8n/health` - n8n integration health check

## Testing Checklist

- [ ] n8n can call FastAPI health endpoint
- [ ] n8n can send messages to `/api/webhooks/n8n/message`
- [ ] FastAPI receives and logs n8n messages
- [ ] n8n webhook created and accessible
- [ ] Basic workflow executes successfully

## Next Steps

Once basic integration is working:
- Step 8: Connect agents to Telegram bots
- Step 14: Full n8n workflow integration
- Agents will trigger n8n workflows
- n8n will handle scheduled tasks (check-in/check-out)

## Troubleshooting

- **Can't connect to FastAPI?** 
  - Make sure FastAPI server is running
  - Check the URL is correct (`http://localhost:8000`)
  - Check firewall settings

- **Webhook not receiving?**
  - Verify n8n webhook URL is correct
  - Check n8n workflow is active
  - Check FastAPI logs for errors

- **CORS errors?**
  - FastAPI CORS is configured to allow all origins
  - If issues persist, check n8n and FastAPI are on same network

