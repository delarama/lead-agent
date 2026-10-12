"""Run one full conversation between the agent and a simulated seller."""

import sys
import time

from agent import agent_turn, client
from data import LISTINGS
from prompts import PROMPTS, SELLER_PROMPT
from tools import Session

SELLER_MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 8  # the agent gets at most 8 messages per conversation
MESSAGE_PAUSE_SECONDS = 3  # pause after each text, so the chat is readable


def seller_reply(case, transcript):
    """Ask the second model to answer as the seller."""
    listing = LISTINGS[case["listing_id"]]
    system = SELLER_PROMPT.format(persona=case["persona"], **listing)
    # The seller sees the conversation from the other side:
    # the agent's messages are "user" and its own messages are "assistant".
    messages = [
        {"role": "user" if line["speaker"] == "agent" else "assistant",
         "content": line["text"]}
        for line in transcript
    ]
    response = client.messages.create(
        model=SELLER_MODEL, max_tokens=200, system=system, messages=messages
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


def run_conversation(case, system_prompt, verbose=False):
    """Returns the transcript, the tool log, and the outcome."""
    session = Session(case["listing_id"])
    transcript = []
    seller_replies = 0
    # The app starts the conversation. The seller has not said anything yet.
    messages = [{"role": "user",
                 "content": "New lead. Write your first message to the seller."}]

    for _ in range(MAX_TURNS):
        text = agent_turn(session, messages, system_prompt)
        if text:
            transcript.append({"speaker": "agent", "text": text})
            if verbose:
                print(f"\nAGENT:  {text}", flush=True)
                time.sleep(MESSAGE_PAUSE_SECONDS)

        if session.booked or session.handed_over or not text:
            break
        # Some test cases make the seller go silent after a few replies.
        if seller_replies >= case.get("seller_max_replies", 99):
            break

        reply = seller_reply(case, transcript)
        if reply.strip().upper().startswith("END"):
            break
        seller_replies += 1
        transcript.append({"speaker": "seller", "text": reply})
        if verbose:
            print(f"\nSELLER: {reply}", flush=True)
            time.sleep(MESSAGE_PAUSE_SECONDS)
        # The tags tell the model that this text came from the seller.
        messages.append({"role": "user",
                         "content": f"<seller_message>{reply}</seller_message>"})

    return {
        "case_id": case["id"],
        "transcript": transcript,
        "tool_log": session.log,
        "outcome": session.outcome(),
        "booked": session.booked,
        "handed_over": session.handed_over,
    }


if __name__ == "__main__":
    # Try it:  python simulate.py v0
    version = sys.argv[1] if len(sys.argv) > 1 else "v0"
    demo_case = {
        "id": "demo",
        "listing_id": "L1",
        "persona": "You ask for the full price first. You accept any offer of "
                   "$16,000 or more. Any time slot works for you.",
    }
    result = run_conversation(demo_case, PROMPTS[version], verbose=True)
    print("\nOUTCOME:", result["outcome"], result["booked"] or result["handed_over"] or "")
    print("TOOLS:  ", [call["tool"] for call in result["tool_log"]])
