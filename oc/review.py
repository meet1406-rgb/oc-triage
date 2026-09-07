"""
oc/review.py

Step 6, part 2: the approval queue review tool.

Shows one pending draft at a time and records what the manager decided.

  a  approve       send as drafted (nothing is actually sent)
  e  edit          open the draft in your editor, keep both versions
  r  reject        record a reason, no reply goes out
  s  skip          leave it pending
  q  quit

Usage from the project root:
    python -m oc.review              review pending items
    python -m oc.review --stats      summary of everything reviewed so far
    python -m oc.review --all        include already reviewed items

There is no send function anywhere in this project. Approve means "the manager
signed off on this text", not "this was delivered".

Synthetic data. Not legal advice.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

from oc.queue import load_queue, save_queue

WRAP = 72


def wrap(text, width=WRAP, indent="  "):
    """Wrap text for the terminal without pulling in extra dependencies."""
    lines = []
    for paragraph in (text or "").split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            if len(current) + len(word) + 1 > width:
                lines.append(indent + current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            lines.append(indent + current)
    return "\n".join(lines)


def open_in_editor(text):
    """Drop the draft into a temp file, open it, read back what was saved."""
    editor = os.environ.get("EDITOR")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as handle:
        handle.write(text)
        path = handle.name

    try:
        if editor:
            subprocess.call([editor, path])
        elif os.name == "nt":
            subprocess.call(["notepad.exe", path])
        else:
            subprocess.call(["nano", path])

        with open(path, encoding="utf-8") as handle:
            return handle.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def show_item(item, position, total):
    email = item["email"]
    agent = item["agent"]

    print("\n" + "=" * WRAP)
    print("%s  (%d of %d pending)" % (item["queue_id"], position, total))
    print("=" * WRAP)
    print("%s | lot %s | %s" % (email["scheme_id"], email["lot"], email["from"]))
    print("Subject: %s" % email["subject"])
    print("-" * WRAP)
    print(wrap(email["body"]))
    print("-" * WRAP)

    flag = " *NEEDS AUTHORITY*" if agent["requires_committee_decision"] else ""
    print("agent: %s | %s%s" % (agent["category"], agent["urgency"], flag))
    print("rules cited: %s" % (agent["rules_cited"] or "none"))
    print("reasoning: %s" % wrap(agent["reasoning"] or "", indent="").strip())

    print("\n--- proposed reply " + "-" * (WRAP - 19))
    draft = item["original_draft"]
    if draft.strip():
        print(wrap(draft, indent=""))
    else:
        print("(no draft - agent escalated this to a human)")
    print("-" * WRAP)


def review_loop(queue):
    pending = [i for i in queue["items"] if i["status"] == "pending"]
    if not pending:
        print("nothing pending. queue more with: python -m oc.queue")
        return

    total = len(pending)
    for position, item in enumerate(pending, 1):
        show_item(item, position, total)

        while True:
            choice = input("\n[a]pprove [e]dit [r]eject [s]kip [q]uit > ").strip().lower()

            if choice == "a":
                item["status"] = "approved"
                item["final_draft"] = item["original_draft"]
                item["review"] = {
                    "decision": "approved",
                    "reviewed_at": datetime.now().isoformat(timespec="seconds"),
                    "reason": None,
                    "edited": False,
                }
                print("approved, unchanged")
                break

            if choice == "e":
                edited = open_in_editor(item["original_draft"])
                item["status"] = "approved"
                item["final_draft"] = edited
                item["review"] = {
                    "decision": "approved",
                    "reviewed_at": datetime.now().isoformat(timespec="seconds"),
                    "reason": input("what did you change, and why? > ").strip() or None,
                    "edited": edited.strip() != item["original_draft"].strip(),
                }
                if item["review"]["edited"]:
                    print("approved with edits, both versions kept")
                else:
                    print("no change detected, recorded as approved unchanged")
                break

            if choice == "r":
                item["status"] = "rejected"
                item["final_draft"] = None
                item["review"] = {
                    "decision": "rejected",
                    "reviewed_at": datetime.now().isoformat(timespec="seconds"),
                    "reason": input("why reject it? > ").strip() or None,
                    "edited": False,
                }
                print("rejected, nothing goes out")
                break

            if choice == "s":
                print("skipped, still pending")
                break

            if choice == "q":
                save_queue(queue)
                print("saved. %d still pending."
                      % sum(1 for i in queue["items"] if i["status"] == "pending"))
                return

            print("press a, e, r, s or q")

        save_queue(queue)

    print("\nqueue cleared. run: python -m oc.review --stats")


def show_stats(queue):
    items = queue["items"]
    reviewed = [i for i in items if i["review"]["decision"]]

    if not reviewed:
        print("nothing reviewed yet")
        return

    approved = [i for i in reviewed if i["review"]["decision"] == "approved"]
    edited = [i for i in approved if i["review"]["edited"]]
    untouched = [i for i in approved if not i["review"]["edited"]]
    rejected = [i for i in reviewed if i["review"]["decision"] == "rejected"]

    print("\n" + "=" * WRAP)
    print("review summary")
    print("=" * WRAP)
    print("reviewed             %d of %d queued" % (len(reviewed), len(items)))
    print("approved unchanged   %d  (%.0f%% of reviewed)"
          % (len(untouched), 100.0 * len(untouched) / len(reviewed)))
    print("approved with edits  %d" % len(edited))
    print("rejected             %d" % len(rejected))

    escalated = [i for i in items if not i["original_draft"].strip()]
    print("no draft (escalated) %d" % len(escalated))

    if edited:
        print("\n--- what you changed ---")
        for item in edited:
            print("%s %s" % (item["queue_id"], item["email"]["subject"][:45]))
            if item["review"]["reason"]:
                print("   %s" % item["review"]["reason"])

    if rejected:
        print("\n--- why you rejected ---")
        for item in rejected:
            print("%s %s" % (item["queue_id"], item["email"]["subject"][:45]))
            if item["review"]["reason"]:
                print("   %s" % item["review"]["reason"])

    print("\nThe edit rate is the closest thing you have to a measure of draft")
    print("quality. Original and edited text are both kept in data/queue.json.")


def main():
    queue = load_queue()
    if not queue["items"]:
        print("queue is empty. build it with: python -m oc.queue")
        return

    if "--stats" in sys.argv:
        show_stats(queue)
        return

    if "--all" in sys.argv:
        for item in queue["items"]:
            item["status"] = "pending"

    review_loop(queue)


if __name__ == "__main__":
    main()