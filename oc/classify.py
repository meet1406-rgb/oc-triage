"""
oc/classify.py

Step 4: the first real model call. One email in, one JSON object out.

No tools. No loop. The model sees only the email text and the category
definitions. It does NOT see scheme data, rules, or tier information yet.

Usage from the project root:
    python -m oc.classify EM001      one email, verbose
    python -m oc.classify            all emails, summary table

Synthetic data. Not legal advice.
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
import anthropic

load_dotenv()

MODEL = "claude-sonnet-4-6"

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "emails", "emails.json",
)
URGENCY_EXAMPLES = """
Worked examples of urgency. These emails are NOT in the dataset; they exist only
to calibrate the scale.

Example A - routine
  "The light in the stairwell on level 3 has been flickering for a couple of
   weeks. Not urgent, but could someone look at it eventually."
  urgency: routine
  why: A minor common property defect. Nobody is at risk and nothing is
  deteriorating quickly. Being annoying for weeks does not make it priority.

Example B - priority
  "Our AGM notice says the meeting is in 12 days but I still haven't received
   the financial statements. I need them before I can vote on the budget."
  urgency: priority
  why: A real, dated deadline a few days out with a concrete consequence if it
  slips. Not a safety issue, so not urgent.

Example C - urgent
  "There is smoke coming from the electrical cupboard in the basement car park
   and it smells like burning plastic. I've called 000."
  urgency: urgent
  why: Immediate risk to people and property, right now.

CALIBRATION GUIDANCE
Do not inflate urgency out of sympathy. An owner being frustrated, or a problem
having gone on a long time, does not by itself raise urgency. Apply this test in
order:
  1. Is a person at risk, or is this getting materially worse by the hour?
     If yes: urgent.
  2. Is there a specific deadline within days, or a real financial or legal
     consequence if this slips this week?
     If yes: priority.
  3. Otherwise: routine.

A leaking appliance inside someone's own apartment is routine unless it is
actively flooding. A document request with no stated deadline is routine.
Financial hardship raised by an owner IS priority, because delay causes real
harm to a person even though nothing is physically at risk.
"""

def load_emails():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_prompt(email, categories, urgency_definitions):
    """Build the classification prompt.

    Everything the model needs is in here. If the model gets something wrong,
    this string is the first place to look, before blaming the model.
    """
    category_lines = "\n".join("- " + c for c in categories)
    urgency_lines = "\n".join(
        "- %s: %s" % (k, v) for k, v in urgency_definitions.items()
    )

    return f"""You are triaging inbound email for a Victorian owners corporation
(strata) manager in Australia.

Classify the email below. Reply with JSON only.

CATEGORIES (choose exactly one as the primary):
{category_lines}

Notes on the harder distinctions:
- maintenance_common_property vs maintenance_private_lot: common property is
  shared (lifts, lobbies, roofs, shared plumbing, driveways, bin rooms).
  A private lot is inside someone's apartment or townhouse (appliances, internal
  fixtures, their own hot water unit). If it is genuinely unclear which one it
  is, choose common property, because that is the safer default for the manager.
- approval_request: the owner wants permission to do something. Use this even
  when the works are inside their own lot.
- escalate_immediately: threats, harassment, abuse toward staff, or a request
  for legal advice. Use this when a human must look at it before any reply is
  drafted at all.

URGENCY:
{urgency_lines}
{URGENCY_EXAMPLES}

requires_committee_decision: true when the owners corporation manager cannot act
on this alone and needs a decision from the committee or the owners corporation.
The manager executes decisions of the owners corporation; they do not make them.
Examples that need a decision: authorising towing, agreeing a payment
arrangement, approving an alteration, choosing an insurer.

EMAIL
From: {email['from']}
Subject: {email['subject']}
Body: {email['body']}

Reply with this JSON structure and nothing else. No markdown, no explanation.
{{
  "category": "one of the categories above",
  "secondary_category": "another category, or null if there is no genuine overlap",
  "urgency": "urgent, priority, or routine",
  "requires_committee_decision": true or false,
  "reasoning": "one short sentence"
}}"""


def parse_reply(text):
    """Pull JSON out of the model's reply.

    The model is told to return JSON only. It usually does. Sometimes it wraps
    the JSON in markdown code fences anyway, so strip those before parsing.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def classify(client, email, categories, urgency_definitions):
    """Classify one email. Returns (result_dict, error_string)."""
    prompt = build_prompt(email, categories, urgency_definitions)
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        return None, "API error: %s" % exc

    raw = message.content[0].text
    try:
        return parse_reply(raw), None
    except Exception as exc:
        return None, "could not parse reply (%s): %r" % (exc, raw[:200])


def run_one(client, email, categories, urgency_definitions):
    print("=" * 70)
    print(email["id"], "|", email["subject"])
    print("-" * 70)
    print(email["body"])
    print("-" * 70)

    result, error = classify(client, email, categories, urgency_definitions)
    if error:
        print("ERROR:", error)
        return

    label = email["label"]
    for field in ["category", "secondary_category", "urgency",
                  "requires_committee_decision"]:
        got = result.get(field)
        want = label.get(field)
        mark = "ok  " if got == want else "MISS"
        print("%s %-28s model=%-30s label=%s" % (mark, field, got, want))

    print("\nmodel reasoning:", result.get("reasoning"))
    print("your note:", email.get("note", ""))


def run_all(client, emails, categories, urgency_definitions):
    correct = 0
    urgency_correct = 0
    secondary_rescue = 0
    committee_misses = []
    rows = []

    for email in emails:
        result, error = classify(client, email, categories, urgency_definitions)
        if error:
            rows.append((email["id"], "ERROR", error[:40], "", ""))
            continue

        label = email["label"]
        got = result.get("category")
        want = label.get("category")
        hit = got == want
        if hit:
            correct += 1
        elif got == label.get("secondary_category"):
            secondary_rescue += 1

        if result.get("requires_committee_decision") != label.get("requires_committee_decision"):
            committee_misses.append(email["id"])

        rows.append((
            email["id"],
            "ok  " if hit else "MISS",
            want,
            got,
            "%s/%s" % (result.get("urgency"), label.get("urgency")),
        ))
        if result.get("urgency") == label.get("urgency"):
            urgency_correct += 1
        time.sleep(0.3)  # be gentle on the API

    print("%-7s %-5s %-28s %-28s %s" % ("id", "", "label", "model", "urgency model/label"))
    print("-" * 100)
    for row in rows:
        print("%-7s %-5s %-28s %-28s %s" % row)

    total = len(emails)
    total = len(emails)
    total = len(emails)
    print("\ncategory accuracy:            %d/%d = %.0f%%"
          % (correct, total, 100.0 * correct / total))
    print("urgency accuracy:             %d/%d = %.0f%%"
          % (urgency_correct, total, 100.0 * urgency_correct / total))
    print("wrong but matched secondary:  %d" % secondary_rescue)
    print("requires_committee_decision misses: %d %s"
          % (len(committee_misses), committee_misses))
if __name__ == "__main__":
    data = load_emails()
    categories = data["categories"]
    urgency_definitions = data["urgency_definitions"]
    emails = data["emails"]

    client = anthropic.Anthropic()

    if len(sys.argv) > 1:
        wanted = sys.argv[1].upper()
        match = [e for e in emails if e["id"] == wanted]
        if not match:
            print("no email with id", wanted)
            print("available:", ", ".join(e["id"] for e in emails))
            sys.exit(1)
        run_one(client, match[0], categories, urgency_definitions)
    else:
        run_all(client, emails, categories, urgency_definitions)