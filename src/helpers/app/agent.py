import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SYSTEM_PROMPT = """\
You are an assistant for operators of modular process plants described by Module Type Packages (MTP).

- Answer questions about the plant configuration ONLY from tool results. Never invent module names,
  tags or signals.
- If you are not sure of the exact module ID, call list_modules first and pick the matching entry.
- The MTP contains structure only: which elements exist, their types and signals. It contains no
  live values and no description of the process purpose. If a question needs more than that, state
  what the tools show and what is not available. Do not guess.
- Answer in the language of the user.
"""

project_root = Path(__file__).resolve().parents[3]
server_script_path = project_root / "src" / "helpers" / "mtp" / "mtp_server.py"


class MTP_MCP_Toolbox:
    def __init__(self):
        self.session: ClientSession | None = None
        self.current_task: asyncio.Task[None] | None = None
        self.tools: list[dict[str, Any]] = []
        self.ready = asyncio.Event()
        self.stop = asyncio.Event()

    async def start_server(self):
        if self.current_task is None:
            self.current_task = asyncio.create_task(self.run())
        await self.ready.wait()

    async def run(self):
        params = StdioServerParameters(
            command=sys.executable, args=[str(server_script_path)], cwd=project_root
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            self.session = session

            result = await session.list_tools()
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
                for tool in result.tools
            ]

            self.ready.set()

            await self.stop.wait()

    async def stop_server(self):
        self.stop.set()
        if self.current_task:
            await self.current_task

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        if self.session is None:
            raise RuntimeError("The MTP MCP server is not running.")

        response = await self.session.call_tool(name, args)
        text = "\n".join(
            item.text
            for item in response.content
            if isinstance(getattr(item, "text", None), str)
        )
        if response.is_error:
            return f"MCP tool '{name}' returned an error: {text}"
        if text:
            return text
        return json.dumps(response.model_dump(mode="json"), ensure_ascii=False)
