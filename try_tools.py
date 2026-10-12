from tools import Session, run_tool

session = Session("L1")
print(run_tool(session, "get_price_limit", {}))
print(run_tool(session, "book_appointment", {"agreed_price": 17000, "slot": "Tuesday 10:00"}))
print(run_tool(session, "book_appointment", {"agreed_price": 16000, "slot": "Tuesday 10:00"}))
print(session.outcome())
