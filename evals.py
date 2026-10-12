"""Run every test case, score it, and print the pass rate.

Usage:
    python evals.py v0            run all cases with prompt version v0
    python evals.py v1 C09        run one case and print the conversation
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from agent import client
from data import LISTINGS, price_limit
from prompts import JUDGE_PROMPT, PROMPTS
from simulate import run_conversation

JUDGE_MODEL = "claude-sonnet-5-5"
JUDGE_CRITERIA = ["offers_within_limit", "honest", "stayed_in_role", "tone"]


def code_checks(case, result):
    """Checks that plain code can decide. These are exact, fast, and free."""
    limit = price_limit(case["listing_id"])
    calls = result["tool_log"]
    names = [call["tool"] for call in calls]
    bookings = [call for call in calls if call["tool"] == "book_appointment"]

    checks = {}
    # 1. Did the conversation end the way this case should end?
    checks["outcome"] = result["outcome"] == case["expected"]
    # 2. Did the agent ever try to book above the limit, even if code stopped it?
    checks["never_tried_above_limit"] = all(
        (call["input"].get("agreed_price") or 0) <= limit for call in bookings
    )
    # 3. If it tried to book, did it look up the limit first?
    if bookings:
        first_booking = names.index("book_appointment")
        checks["limit_checked_before_booking"] = "get_price_limit" in names[:first_booking]
    else:
        checks["limit_checked_before_booking"] = True
    return checks


def judge(case, result):
    """Checks that need reading. A second model grades the conversation."""
    transcript = "\n".join(
        f"{line['speaker'].upper()}: {line['text']}" for line in result["transcript"]
    )
    tool_log = "\n".join(
        f"{call['tool']}({json.dumps(call['input'])}) -> {call['result']}"
        for call in result["tool_log"]
    ) or "(none)"
    prompt = JUDGE_PROMPT.format(
        listing=json.dumps(LISTINGS[case["listing_id"]]),
        limit=price_limit(case["listing_id"]),
        transcript=transcript or "(empty)",
        tool_log=tool_log,
    )
    response = client.messages.create(
        model=JUDGE_MODEL, max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        # Take the JSON object out of the answer, even if there is text around it.
        grades = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))
        return {name: bool(grades[name]["pass"]) for name in JUDGE_CRITERIA}, grades
    except Exception:
        # If the judge's answer cannot be read, count it as a failure to review.
        return {name: False for name in JUDGE_CRITERIA}, {"unreadable": text}


def run_case(case, system_prompt, verbose=False):
    result = run_conversation(case, system_prompt, verbose=verbose)
    checks = code_checks(case, result)
    judge_checks, judge_detail = judge(case, result)
    checks.update(judge_checks)
    result.update({
        "expected": case["expected"],
        "group": case["group"],
        "checks": checks,
        "judge_detail": judge_detail,
        "passed": all(checks.values()),
    })
    return result


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "v0"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    system_prompt = PROMPTS[version]

    with open("cases.json") as file:
        cases = json.load(file)
    if only:
        cases = [case for case in cases if case["id"] == only]

    # Run four conversations at a time so the full set takes minutes, not half an hour.
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            lambda case: run_case(case, system_prompt, verbose=bool(only)), cases
        ))

    print(f"\nPrompt version: {version}")
    print(f"{'case':<5} {'group':<11} {'expected':<12} {'outcome':<12} result")
    for r in results:
        failed = [name for name, ok in r["checks"].items() if not ok]
        status = "PASS" if r["passed"] else "FAIL  " + ", ".join(failed)
        print(f"{r['case_id']:<5} {r['group']:<11} {r['expected']:<12} {r['outcome']:<12} {status}")

    passed = sum(r["passed"] for r in results)
    print(f"\nPass rate: {passed}/{len(results)} = {passed / len(results):.0%}")

    print("Failures per check:")
    for name in results[0]["checks"]:
        count = sum(not r["checks"][name] for r in results)
        print(f"  {name}: {count}")

    if not only:
        with open(f"results_{version}.json", "w") as file:
            json.dump(results, file, indent=2)
        print(f"\nSaved every conversation to results_{version}.json")


if __name__ == "__main__":
    main()
