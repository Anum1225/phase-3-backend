# MCP Server Testing Guide

## MCP Server Endpoint
- **URL**: `http://localhost:8000/api/mcp/mcp`
- **Mount Point**: `/api/mcp`
- **Transport**: Streamable HTTP (JSON response)

## Available Tools

1. **add_task** - Create a new task
2. **list_tasks** - List tasks with filters
3. **complete_task** - Mark tasks complete/incomplete
4. **delete_task** - Delete tasks
5. **update_task** - Update task details

## Quick Test Commands

### 1. Check if MCP server is running
```bash
curl http://localhost:8000/api/mcp/mcp
```

### 2. Test with Python script
```bash
cd backend
python test_mcp.py
```

### 3. Verify tools programmatically
```bash
cd backend
python -c "from src.mcp import mcp; print(list(mcp._tool_manager._tools.keys()))"
```

Expected output:
```
['add_task', 'list_tasks', 'complete_task', 'delete_task', 'update_task']
```

### 4. Check server health
```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

## Browser Testing

1. Open browser and go to: `http://localhost:8000/api/mcp/mcp`
2. You should see an MCP protocol response
3. Check FastAPI docs: `http://localhost:8000/docs`

## Testing MCP Tools (via HTTP)

MCP tools are typically called via the MCP protocol, not direct HTTP. However, you can test the server is responding:

```bash
# GET request to MCP endpoint
curl -X GET http://localhost:8000/api/mcp/mcp \
  -H "Content-Type: application/json"

# POST request (MCP protocol format)
curl -X POST http://localhost:8000/api/mcp/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

## Expected Behavior

- ✅ Server responds at `/api/mcp/mcp`
- ✅ 5 tools are registered
- ✅ Database connection works (via lifespan context)
- ✅ Tools can access database via context



























