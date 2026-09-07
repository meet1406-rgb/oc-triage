"""
oc/agent.py

Step 5: the agent loop.

The model is given three tools and decides for itself which to call and when.
Your code just runs whatever it asks for and hands the result back, until it
stops asking.

There is NO send function in this file. The agent drafts and routes. It does not
send and it does not decide.

Usage from the project root:
    python -m oc.agent EM023            run one email
    python -m oc.agent EM023 --quiet    hide the step by step trace
    python -m oc.agent --dry-run        print the tool schemas, no API call

Synthetic data. Not legal advice.
"""

import json
import os
import sys

from dotenv import load_dotenv
import anthropic

from oc.tools import get_scheme, get_lot_owner, search_oc_rules

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 8

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "emails", "emails.json",
)

# ---------------------------------------------------------------------------
# Tool schemas
#
# This is the ONLY thing the model sees about your functions. It cannot read
# your source code. If a description is vague, the model will use the tool
# wrongly, and that is a bug in this dict, not in the model.
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "get_scheme",
        "description": (
            "Look up an owners corporation by its scheme id. Returns the number of "
            "occupiable lots, whether it is a services only owners corporation, its "
            "computed tier (1 to 5) and the obligations that attach to that tier, "
            "plus committee status, manager, insurance renewal date, maintenance "
            "plan status and AGM dates. Call this before answering any question "
            "where the correct answer could depend on the size or type of the "
            "scheme, such as whether a committee or a maintenance plan is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scheme_id": {
                    "type": "string",
                    "description": "Scheme id such as SCH001. Case insensitive.",
                },
            },
            "required": ["scheme_id"],
        },
    },
    {
        "name": "get_lot_owner",
        "description": (
            "Look up the owner record for one lot in one scheme. Returns the owner "
            "name, email, levy balance in AUD, whether they are in arrears, and "
            "whether they occupy the lot. Only call this when the specific owner's "
            "details are relevant to answering, for example a levy or arrears "
            "question. Do not call it just to personalise a greeting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scheme_id": {"type": "string", "description": "Scheme id such as SCH001."},
                "lot_number": {"type": "integer", "description": "The lot number."},
            },
            "required": ["scheme_id", "lot_number"],
        },
    },
    {
        "name": "search_oc_rules",
        "description": (
            "Search the owners corporation rules for rules relevant to a query. "
            "Returns rule numbers, titles and full text. Call this whenever the "
            "email concerns something the rules might govern: pets, parking, noise, "
            "rubbish, alterations, floor coverings, works, smoking, short stay, or "
            "use of common property. IMPORTANT: this search matches on keywords, "
            "not meaning, so if your first query returns nothing, try again with "
            "the words the rules themselves would use rather than the words the "
            "owner used. If you still find nothing, say so rather than answering "
            "from general knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search for, for example 'animals pets dog'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "How many rules to return. Default 3.",
                },
            },
            "required": ["query"],
        },
    },
]

TOOL_FUNCTIONS = {
    "get_scheme": get_scheme,
    "get_lot_owner": get_lot_owner,
    "search_oc_rules": search_oc_rules,
}


def build_system_prompt(categories, urgency_definitions):
    category_lines = "\n".join("- " + c for c in categories)
    urgency_lines = "\n".join("- %s: %s" % (k, v) for k, v in urgency_definitions.items())

    return f"""You triage inbound email for a Victorian owners corporation (strata)
manager in Australia.

YOUR LIMITS
You draft. You do not send, and you do not decide. Under the Owners Corporations
Act framework the owners corporation makes decisions and the manager executes
them. Never write a draft that grants approval, authorises expenditure, commits
to enforcement action, or gives legal advice.
WHAT IS NOT A DECISION
Answering a factual question is not a decision. Set
requires_committee_decision to false when the reply only states facts the
manager already holds or can look up: meeting dates, levy balances, insurance
renewal dates, what a rule says, what the scheme's tier is, or what obligations
attach to that tier. Explaining that something cannot be done, or that a body
does not exist, is also just information.
Changing how an owner pays is not a payment arrangement. Setting up a direct
debit, changing a billing address, or switching payment frequency commits the
owners corporation to nothing and needs no authority. A payment arrangement
means changing what is owed or when it falls due.

An owner's arrears balance is a fact about their account, not about their
request. Do not raise arrears in a reply unless the owner asked about their
balance, or the request cannot be answered without it. Do not let an arrears
balance change your urgency assessment on an unrelated question.

Set it to true only when the owner is asking for something that would commit the
owners corporation: approving works, authorising expenditure or towing, agreeing
a payment arrangement, choosing a supplier, or starting enforcement action.
USE YOUR TOOLS
Do not answer from general knowledge about strata. Look things up. In particular:
- Anything that depends on the size or type of the scheme: call get_scheme.
- Anything the rules might govern: call search_oc_rules.
- Never state what a rule requires unless you have retrieved that rule.
- If a search returns nothing, try different words. If it still returns nothing,
  say in your draft that the rule could not be located, and set
  requires_committee_decision to true so a human checks. Do not invent a rule.
  NEVER CITE LEGISLATION
Do not cite sections of the Owners Corporations Act or any other legislation.
You have no tool that returns statute, so any section number you produce is
invented. Describe obligations in plain terms instead, or say the manager should
confirm the statutory position.

NEVER ASSERT FACTS YOU DID NOT LOOK UP
Do not state a levy balance, arrears status, owner name, or any other fact about
a specific lot unless you called get_lot_owner for that lot in this
conversation. If you did not look it up, do not mention it.

CATEGORIES
{category_lines}
Category disambiguation:
- oc_certificate_request means ONLY the owners corporation certificate prepared
  for a property sale, for a section 32 statement, usually requested by a
  conveyancer or solicitor. Nothing else.
- A request for a certificate of currency, proof of insurance, or insurance
  policy details is category "insurance", never oc_certificate_request, even
  though the word certificate appears.
URGENCY
{urgency_lines}
Do not inflate urgency out of sympathy. Frustration or a long running problem
does not by itself raise urgency. Financial hardship raised by an owner IS
priority.

WHEN YOU HAVE FINISHED LOOKING THINGS UP
Reply with JSON only. No markdown fences, no commentary.
{{
  "category": "one of the categories above",
  "secondary_category": "another category, or null",
  "urgency": "urgent, priority or routine",
  "requires_committee_decision": true or false,
  "rules_cited": ["2.3", "7.2"],
  "draft_reply": "the email you propose the manager sends, signed off as the owners corporation manager",
  "reasoning": "one or two sentences on how you reached this"
}}
If the category is escalate_immediately, set draft_reply to an empty string and
explain in reasoning why a human must handle it."""


def parse_json_reply(text):
    """Find the JSON in the reply, wherever it is."""
    cleaned = text.strip().replace("```json", "").replace("```", "")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in reply")
    return json.loads(cleaned[start:end + 1])


def run_agent(client, email, categories, urgency_definitions, verbose=True):
    """The loop. This is the whole idea of an agent, in about fifteen lines."""
    system = build_system_prompt(categories, urgency_definitions)

    user_message = (
        "Triage this email.\n\n"
        "Scheme id: %s\n"
        "Lot: %s\n"
        "From: %s\n"
        "Subject: %s\n"
        "Body: %s" % (email["scheme_id"], email.get("lot"), email["from"],
                      email["subject"], email["body"])
    )

    messages = [{"role": "user", "content": user_message}]
    tool_calls_made = []

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # The model has finished asking for things.
        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            try:
                return parse_json_reply(final_text), tool_calls_made, None
            except Exception as exc:
                return None, tool_calls_made, "could not parse: %s | %r" % (exc, final_text[:300])

        # Keep the model's turn in the transcript, then answer every tool_use
        # block it produced. There can be more than one in a single turn.
        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            func = TOOL_FUNCTIONS.get(block.name)
            if func is None:
                output = {"error": "no such tool: %s" % block.name}
            else:
                try:
                    output = func(**block.input)
                except Exception as exc:
                    output = {"error": "tool raised: %s" % exc}

            tool_calls_made.append({"tool": block.name, "input": block.input})

            if verbose:
                print("  [turn %d] %s(%s)" % (turn + 1, block.name,
                      ", ".join("%s=%r" % kv for kv in block.input.items())))
                preview = json.dumps(output)
                print("           -> %s" % (preview[:180] + ("..." if len(preview) > 180 else "")))

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(output, default=str),
            })

        messages.append({"role": "user", "content": results})

    return None, tool_calls_made, "hit MAX_TURNS (%d) without a final answer" % MAX_TURNS


def show_result(email, result, tool_calls):
    label = email["label"]
    print("\n" + "-" * 70)
    for field in ["category", "secondary_category", "urgency",
                  "requires_committee_decision"]:
        got = result.get(field)
        want = label.get(field)
        mark = "ok  " if got == want else "MISS"
        print("%s %-28s agent=%-28s label=%s" % (mark, field, got, want))

    print("\ntools called: %d" % len(tool_calls))
    print("rules cited:  %s" % (result.get("rules_cited") or "none"))
    print("\nreasoning: %s" % result.get("reasoning"))
    print("\n--- draft reply ---")
    print(result.get("draft_reply") or "(none - escalated)")
    print("--- end draft ---")
    print("\nyour note: %s" % email.get("note", ""))


def main():
    if "--dry-run" in sys.argv:
        print("Tool schemas the model will see:\n")
        print(json.dumps(TOOL_SCHEMAS, indent=2))
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: python -m oc.agent EM023 [--quiet]")
        print("       python -m oc.agent --dry-run")
        return

    wanted = args[0].upper()
    match = [e for e in data["emails"] if e["id"] == wanted]
    if not match:
        print("no email with id", wanted)
        return
    email = match[0]

    print("=" * 70)
    print(email["id"], "|", email["subject"], "|", email["scheme_id"])
    print("=" * 70)
    print(email["body"])
    print()

    client = anthropic.Anthropic()
    result, tool_calls, error = run_agent(
        client, email, data["categories"], data["urgency_definitions"],
        verbose="--quiet" not in sys.argv,
    )

    if error:
        print("\nERROR:", error)
        print("tools called before failing:", tool_calls)
        return

    show_result(email, result, tool_calls)


if __name__ == "__main__":
    main()