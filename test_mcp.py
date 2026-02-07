"""
Quick script to test MCP server and list available tools.
Run: python test_mcp.py
"""
from src.mcp import mcp

print("MCP Server Name:", mcp.name)
print("\nAvailable Tools:")
print("-" * 50)

# Get all registered tools
tools = list(mcp._tool_manager._tools.keys())
for i, tool_name in enumerate(tools, 1):
    print(f"{i}. {tool_name}")

print(f"\nTotal: {len(tools)} tools registered")
print("\nMCP Endpoint: http://localhost:8000/api/mcp/mcp")



























