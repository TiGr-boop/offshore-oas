import json
from typing import Any

import chainlit as cl
from ollama import AsyncClient
from openai import AsyncOpenAI

from agent import MTP_MCP_Toolbox, SYSTEM_PROMPT

OPENAI_API_KEY = ""
OPENAI_MODEL_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")

ollama_client = AsyncClient()
openai_client: AsyncOpenAI | None = (
    AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
)


def is_openai_model(model: str) -> bool:
    return model.startswith(OPENAI_MODEL_PREFIXES)


async def _run_tool(
    toolbox: MTP_MCP_Toolbox, name: str, arguments: Any
) -> str:
    try:
        parsed_arguments = (
            json.loads(arguments) if isinstance(arguments, str) else arguments
        )
    except json.JSONDecodeError as error:
        return f"Tool '{name}' received invalid JSON arguments: {error.msg}"

    if not isinstance(parsed_arguments, dict):
        return f"Tool '{name}' arguments must be a JSON object."

    return await toolbox.call_tool(name, parsed_arguments)


async def _stream_ollama(
    prompt: str,
    model: str,
    msg: cl.Message,
    toolbox: MTP_MCP_Toolbox,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    full_response = ""

    while True:
        stream = await ollama_client.chat(
            model=model,
            messages=messages,
            tools=toolbox.tools,
            stream=True,
        )
        response_text = ""
        tool_calls = []

        async for chunk in stream:
            response_text_part = chunk.message.content or ""
            if response_text_part:
                response_text += response_text_part
                full_response += response_text_part
                await msg.stream_token(response_text_part)
            tool_calls.extend(chunk.message.tool_calls or [])

        if not tool_calls:
            return full_response

        messages.append(
            {
                "role": "assistant",
                "content": response_text,
                "tool_calls": [
                    {
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                    }
                    for tool_call in tool_calls
                ],
            }
        )

        for tool_call in tool_calls:
            name = tool_call.function.name
            result = await _run_tool(
                toolbox, name, tool_call.function.arguments
            )
            messages.append(
                {"role": "tool", "tool_name": name, "content": result}
            )


async def _stream_openai(
    prompt: str,
    model: str,
    msg: cl.Message,
    toolbox: MTP_MCP_Toolbox,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    if openai_client is None:
        raise RuntimeError(
            "An OpenAI model was selected, but no API key is configured."
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    full_response = ""

    while True:
        stream = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=toolbox.tools,
            tool_choice="auto",
            stream=True,
        )
        response_text = ""
        tool_calls: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            content = delta.content or ""
            if content:
                response_text += content
                full_response += content
                await msg.stream_token(content)

            for call_delta in delta.tool_calls or []:
                call = tool_calls.setdefault(
                    call_delta.index, {"id": "", "name": "", "arguments": ""}
                )
                if call_delta.id:
                    call["id"] = call_delta.id
                if call_delta.function and call_delta.function.name:
                    call["name"] += call_delta.function.name
                if call_delta.function and call_delta.function.arguments:
                    call["arguments"] += call_delta.function.arguments

        if not tool_calls:
            return full_response

        assistant_tool_calls = []
        for index, call in sorted(tool_calls.items()):
            call_id = call["id"] or f"call_{index}"
            assistant_tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": call["arguments"] or "{}",
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": response_text or None,
                "tool_calls": assistant_tool_calls,
            }
        )

        for call in assistant_tool_calls:
            name = call["function"]["name"]
            result = await _run_tool(
                toolbox, name, call["function"]["arguments"]
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                }
            )


async def call_llm(
    prompt: str,
    model: str,
    toolbox: MTP_MCP_Toolbox,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    msg = cl.Message(content="")
    await msg.send()

    if is_openai_model(model):
        full_response = await _stream_openai(
            prompt=prompt,
            model=model,
            msg=msg,
            toolbox=toolbox,
            system_prompt=system_prompt,
        )
    else:
        full_response = await _stream_ollama(
            prompt=prompt,
            model=model,
            msg=msg,
            toolbox=toolbox,
            system_prompt=system_prompt,
        )

    await msg.update()
    return full_response
