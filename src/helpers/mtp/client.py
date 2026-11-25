import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable, args=[str(HERE / "mtp_server.py")]
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        print("Tools:", [t.name for t in tools.tools], "\n")

        async def call(name: str, **args):
            res = await session.call_tool(name, args)
            text = "\n".join(c.text for c in res.content if hasattr(c, "text"))
            is_error = getattr(
                res, "is_error", getattr(res, "isError", False)
            )  # mcp 2.x / 1.x
            print(f"--- {name}({args}){' [FEHLER]' if is_error else ''}\n{text}\n")

        await call("list_modules")
        first = "Ammonika"
        await call("get_module_overview", module=first)
        await call("describe_data_assembly", module=first, da_name="p7001")
        await call("describe_signal", module=first, da_name="p7001", signal="OSLevel")


if __name__ == "__main__":
    asyncio.run(main())
