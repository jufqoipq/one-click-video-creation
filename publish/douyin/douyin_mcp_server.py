"""抖音 MCP Server - 通过 MCP 协议暴露抖音发布工具"""

import asyncio
import json
import sys
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ListToolsResult, CallToolResult

sys.path.insert(0, str(Path(__file__).parent))
from douyin_tools import login, check_login, publish_video

TOOLS = [
    Tool(name="login", description="扫码登录抖音创作者中心",
         inputSchema={"type": "object", "properties": {"headless": {"type": "boolean", "default": False}}}),
    Tool(name="check_login", description="检查抖音登录状态",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="publish_video", description="发布视频到抖音",
         inputSchema={"type": "object", "properties": {
             "video_path": {"type": "string", "description": "视频文件路径"},
             "title": {"type": "string", "description": "标题(最多30字)"},
             "tags": {"type": "array", "items": {"type": "string"}, "default": []},
             "headless": {"type": "boolean", "default": True},
         }, "required": ["video_path", "title"]}),
]


async def _on_list_tools(ctx, params):
    return ListToolsResult(tools=TOOLS)


async def _on_call_tool(ctx, params):
    name, args = params.name, params.arguments
    if name == "login":
        result = await login(headless=args.get("headless", False))
    elif name == "check_login":
        result = await check_login()
    elif name == "publish_video":
        result = await publish_video(args["video_path"], args["title"], args.get("tags", []), args.get("headless", True))
    else:
        result = {"status": "error", "message": f"未知工具: {name}"}
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))])


server = Server("douyin-mcp", on_list_tools=_on_list_tools, on_call_tool=_on_call_tool)


async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
