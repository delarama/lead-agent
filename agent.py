"""The agent loop: call the model, run the tools it asks for, repeat."""

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, run_tool

load_dotenv()  # reads ANTHROPIC_API_KEY from the .env file
client = anthropic.Anthropic(max_retries=5)

AGENT_MODEL = "claude-sonnet-5-5"
MAX_STEPS = 8  # a safety stop, so one turn can never loop forever


def agent_turn(session, messages, system_prompt):
    """Run the model until it stops calling tools.

    Returns the text that the app sends to the seller.
    `messages` is the full history and is changed in place.
    """
    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=500,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        # Keep the model's full answer in the history, including tool calls.
        messages.append({"role": "assistant", "content": response.content})

        # No tool call means the model is done. Its text is the message.
        if response.stop_reason != "tool_use":
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

        # Run every tool the model asked for and send the results back.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                content, is_error = run_tool(session, block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                })
        messages.append({"role": "user", "content": results})

    return ""  # the model used too many steps in one turn
