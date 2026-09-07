"""
oc/queue.py

Step 6, part 1: build the approval queue.

Runs the agent over emails and writes each result to data/queue.json with
status "pending". Nothing is sent. There is no send function in this project.

Usage from the project root:
    python -m oc.queue                 queue every email
    python -m oc.queue --limit 5       queue the first five
    python -m oc.queue --reset         wipe the queue and start over

Then review with:  python -m oc.review

Synthetic data. Not legal advice.
"""

import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
import anthropic

from oc.agent import run_agent, DATA_PATH

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(ROOT, "data", "queue.json")


def load_queue():
    if not os.path.exists(QUEUE_PATH):
        return {"items": []}
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)


def main():
    if "--reset" in sys.argv:
        if os.path.exists(QUEUE_PATH):
            os.remove(QUEUE_PATH)
        print("queue cleared")
        return

    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    emails = data["emails"][:limit] if limit else data["emails"]
    queue = load_queue()
    already = {item["email_id"] for item in queue["items"]}

    todo = [e for e in emails if e["id"] not in already]
    if not todo:
        print("nothing new to queue. %d items already waiting." % len(queue["items"]))
        print("run: python -m oc.review")
        return

    print("queueing %d emails (%d already queued)\n" % (len(todo), len(already)))
    client = anthropic.Anthropic()

    for i, email in enumerate(todo, 1):
        print("[%2d/%d] %s %s" % (i, len(todo), email["id"], email["subject"][:40]))

        result, tool_calls, error = run_agent(
            client, email, data["categories"], data["urgency_definitions"],
            verbose=False,
        )

        if error:
            print("        ERROR: %s" % error[:80])
            continue

        queue["items"].append({
            "queue_id": "Q%03d" % (len(queue["items"]) + 1),
            "email_id": email["id"],
            "queued_at": datetime.now().isoformat(timespec="seconds"),
            "status": "pending",
            "email": {
                "scheme_id": email["scheme_id"],
                "lot": email.get("lot"),
                "from": email["from"],
                "subject": email["subject"],
                "body": email["body"],
            },
            "agent": {
                "category": result.get("category"),
                "secondary_category": result.get("secondary_category"),
                "urgency": result.get("urgency"),
                "requires_committee_decision": result.get("requires_committee_decision"),
                "rules_cited": result.get("rules_cited"),
                "reasoning": result.get("reasoning"),
                "tool_calls": len(tool_calls),
            },
            # original_draft is never modified after this point. If the manager
            # edits, the new text goes in final_draft and both are kept. That
            # pair is the data any future feedback loop would learn from.
            "original_draft": result.get("draft_reply") or "",
            "final_draft": None,
            "review": {
                "decision": None,
                "reviewed_at": None,
                "reason": None,
                "edited": False,
            },
        })
        save_queue(queue)
        time.sleep(0.3)

    pending = sum(1 for i in queue["items"] if i["status"] == "pending")
    print("\n%d items in queue, %d pending" % (len(queue["items"]), pending))
    print("review them with:  python -m oc.review")


if __name__ == "__main__":
    main()