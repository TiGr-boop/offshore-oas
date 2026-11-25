import asyncio

import chainlit as cl
from agent import SYSTEM_PROMPT, MTP_MCP_Toolbox
from llm import call_llm

_toolbox: MTP_MCP_Toolbox | None = None
_toolbox_lock = asyncio.Lock()

LLM_MODEL = "llama3.2:3b"


async def get_toolbox() -> MTP_MCP_Toolbox:
    global _toolbox
    async with _toolbox_lock:
        if _toolbox is None:
            toolbox = MTP_MCP_Toolbox()
            await toolbox.start_server()
            _toolbox = toolbox
    return _toolbox


@cl.on_chat_start
async def on_start():
    await get_toolbox()
    await cl.Message(content=("What do you want to know?")).send()


@cl.on_message
async def main(message: cl.Message):
    toolbox = await get_toolbox()
    await call_llm(message.content, LLM_MODEL, toolbox, SYSTEM_PROMPT)
