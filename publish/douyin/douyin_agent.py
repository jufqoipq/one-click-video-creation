"""抖音 Agent - 通过 MCP Client 调用抖音发布工具"""

import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# MCP Server 脚本路径
SERVER_PATH = Path(__file__).parent / "douyin_mcp_server.py"


class DouyinAgent:
    """抖音发布 Agent，封装 MCP 调用逻辑"""

    def __init__(self):
        self.server_path = str(SERVER_PATH)

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用 MCP Server 的工具"""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_path],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                # 解析返回的 TextContent
                text = result.content[0].text
                return json.loads(text)

    async def login(self, headless: bool = False) -> dict:
        """扫码登录"""
        return await self._call_tool("login", {"headless": headless})

    async def check_login(self) -> dict:
        """检查登录状态"""
        return await self._call_tool("check_login", {})

    async def publish(
        self,
        video_path: str,
        title: str,
        tags: list[str] = [],
        headless: bool = True,
    ) -> dict:
        """发布视频"""
        return await self._call_tool("publish_video", {
            "video_path": video_path,
            "title": title,
            "tags": tags,
            "headless": headless,
        })


# 便捷函数（外部直接调用）
async def login_douyin(headless: bool = False):
    return await DouyinAgent().login(headless)

async def check_douyin_login():
    return await DouyinAgent().check_login()

async def publish_to_douyin(video_path: str, title: str, tags: list[str] = []):
    return await DouyinAgent().publish(video_path, title, tags)
