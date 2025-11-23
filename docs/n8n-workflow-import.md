# How to Import n8n Workflows

## Quick Import Guide

1. **Open n8n** in your browser
2. **Click the menu** (three lines/hamburger icon) in the top left
3. **Select "Workflows"**
4. **Click "Import from File"** or the import button
5. **Select the JSON file** from `n8n_workflows/` folder
6. **The workflow will be imported** and you can see it in your workflow list

## Available Workflows

### 1. Test FastAPI Connection (`test-fastapi-connection.json`)
- Tests connection to FastAPI
- Calls health check endpoints
- Sends a test message to FastAPI
- **URL to update:** Make sure the IP address `192.168.100.11` matches your current IP (or update it in the workflow after importing)

## After Importing

1. **Open the imported workflow**
2. **Check the HTTP Request nodes** - verify the URLs are correct
3. **Update IP address if needed** - if your IP changed, update `192.168.100.11` to your current IP
4. **Click "Execute Workflow"** to test

## Updating the IP Address

If your IP address changes (e.g., after reconnecting Wi-Fi):

1. Open the workflow in n8n
2. Click on each HTTP Request node
3. Update the URL to use your new IP address
4. Save the workflow

## Note

The workflows use `192.168.100.11` as the default IP. If your IP is different, you'll need to update it in the workflow nodes after importing.

