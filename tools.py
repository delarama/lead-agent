"""The five tools the agent can call, and the definitions the model reads."""

import json

from data import LISTINGS, SLOTS, price_limit


class Session:
    """Everything that happens in one conversation with one seller."""

    def __init__(self, listing_id: str):
        self.listing_id = listing_id
        self.booked = None        # {"price": ..., "slot": ...} after a booking
        self.handed_over = None   # the reason, after a handover
        self.log = []             # every tool call, for the tests

    def outcome(self) -> str:
        if self.booked:
            return "booked"
        if self.handed_over:
            return "handed_over"
        return "no_deal"


# ---- The five tool functions. Each returns (text for the model, is_error). ----

def get_listing(session, tool_input):
    return json.dumps(LISTINGS[session.listing_id]), False


def get_price_limit(session, tool_input):
    return json.dumps({"price_limit": price_limit(session.listing_id)}), False


def check_calendar(session, tool_input):
    return json.dumps({"free_slots": SLOTS}), False


def book_appointment(session, tool_input):
    price = tool_input.get("agreed_price")
    slot = tool_input.get("slot")
    limit = price_limit(session.listing_id)

    if session.booked:
        return "An appointment is already booked for this seller.", True
    if not isinstance(price, (int, float)) or price <= 0:
        return "agreed_price must be a positive number.", True
    # The rule that must always hold lives here, in code, not in the prompt.
    if price > limit:
        return (f"Rejected: {price} is above the price limit of {limit}. "
                "Do not book. Offer at or below the limit, or hand over to the dealer."), True
    if slot not in SLOTS:
        return f"Rejected: '{slot}' is not free. Free slots: {SLOTS}", True

    session.booked = {"price": price, "slot": slot}
    return json.dumps({"status": "booked", "price": price, "slot": slot}), False


def hand_over_to_dealer(session, tool_input):
    session.handed_over = tool_input.get("reason", "no reason given")
    return json.dumps({"status": "handed_over"}), False


TOOL_FUNCTIONS = {
    "get_listing": get_listing,
    "get_price_limit": get_price_limit,
    "check_calendar": check_calendar,
    "book_appointment": book_appointment,
    "hand_over_to_dealer": hand_over_to_dealer,
}


def run_tool(session, name, tool_input):
    """Run one tool call from the model and record it in the session log."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        content, is_error = f"Unknown tool: {name}", True
    else:
        try:
            content, is_error = function(session, tool_input)
        except Exception as error:  # a tool must never crash the agent
            content, is_error = f"Tool failed: {error}", True
    session.log.append({"tool": name, "input": tool_input,
                        "result": content, "is_error": is_error})
    return content, is_error


# ---- The definitions the model reads. The descriptions are part of the prompt. ----

NO_INPUT = {"type": "object", "properties": {}, "required": []}

TOOLS = [
    {
        "name": "get_listing",
        "description": "Get the details of the car this conversation is about: "
                       "seller name, year, make, model, mileage, and listed price.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "get_price_limit",
        "description": "Get the highest price in dollars that the dealership "
                       "will pay for this car.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "check_calendar",
        "description": "Get the dealer's free appointment slots for this week.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "book_appointment",
        "description": "Book a time for the seller to bring the car to the "
                       "dealership. The booking is rejected if the price is "
                       "above the limit or the slot is not free.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agreed_price": {
                    "type": "number",
                    "description": "The price in dollars the seller agreed to.",
                },
                "slot": {
                    "type": "string",
                    "description": "One free slot, written exactly as "
                                   "check_calendar returned it.",
                },
            },
            "required": ["agreed_price", "slot"],
        },
    },
    {
        "name": "hand_over_to_dealer",
        "description": "Pass this conversation to a person at the dealership. "
                       "After this call, send the seller one last short message "
                       "saying that a person will contact them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "One sentence on why a person is needed.",
                },
            },
            "required": ["reason"],
        },
    },
]
