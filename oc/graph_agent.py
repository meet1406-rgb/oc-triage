"""
oc/graph_agent.py

The SAME agent as oc/agent.py, rebuilt as a LangGraph graph.

THE POINT OF THIS FILE
It is a controlled comparison, not an improvement. Same model, same system
prompt word for word, same tools, same output shape. Only the framework
changes. If the numbers move, that tells you something about the framework.
If they do not, that tells you something too.

oc/agent.py is left untouched. Do not "improve" this version - any change
beyond the framework invalidates the comparison.

THE SHAPE

    START -> agent -> (wants tools?) -> tools -> agent -> ... -> END

The agent node calls the model. If the model asked for tools, a conditional
edge routes to the tool node, which runs them and hands the results back. That
cycle is what the while loop in agent.py did by hand.

Usage from the project root:
    python -m oc.graph_agent EM023

Synthetic data. Not legal advice.
"""

import json
import os
import sys
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from oc.tools import get_scheme as _get_scheme
from oc.tools import get_lot_owner as _get_lot_owner
from oc.tools import search_oc_rules as _search_oc_rules
from oc.agent import build_system_prompt, parse_json_reply, DATA_PATH, MODEL, MAX_TURNS

load_dotenv()


# ---------------------------------------------------------------------------
# Tools
#
# In agent.py these were hand written JSON schemas, about 60 lines. Here the
# @tool decorator builds the schema from the function signature and docstring.
# The DOCSTRING IS THE DESCRIPTION the model sees, so it has to carry the same
# information the hand written schema did.
# ---------------------------------------------------------------------------

@tool
def get_scheme(scheme_id: str) -> str:
    """Look up an owners corporation by its scheme id. Returns the number of
    occupiable lots, whether it is a services only owners corporation, its
    computed tier (1 to 5) and the obligations that attach to that tier, plus
    committee status, manager, insurance renewal date, maintenance plan status
    and AGM dates. Call this before answering any question where the correct
    answer could depend on the size or type of the scheme, such as whether a
    committee or a maintenance plan is required.

    Args:
        scheme_id: Scheme id such as SCH001. Case insensitive.
    """
    return json.dumps(_get_scheme(scheme_id), default=str)


@tool
def get_lot_owner(scheme_id: str, lot_number: int) -> str:
    """Look up the owner record for one lot in one scheme. Returns the owner
    name, email, levy balance in AUD, whether they are in arrears, and whether
    they occupy the lot. Only call this when the specific owner's details are
    relevant to answering, for example a levy or arrears question. Do not call
    it just to personalise a greeting.

    Args:
        scheme_id: Scheme id such as SCH001.
        lot_number: The lot number.
    """
    return json.dumps(_get_lot_owner(scheme_id, lot_number), default=str)


@tool
def search_oc_rules(query: str, max_results: int = 3) -> str:
    """Search the owners corporation rules for rules relevant to a query.
    Returns rule numbers, titles and full text. Call this whenever the email
    concerns something the rules might govern: pets, parking, noise, rubbish,
    alterations, floor coverings, works, smoking, short stay, or use of common
    property. IMPORTANT: this search matches on keywords, not meaning, so if
    your first query returns nothing, try again with the words the rules
    themselves would use rather than the words the owner used. If you still
    find nothing, say so rather than answering from general knowledge.

    Args:
        query: Keywords to search for, for example 'animals pets dog'.
        max_results: How many rules to return. Default 3.
    """
    return json.dumps(_search_oc_rules(query, max_results), default=str)


TOOLS = [get_scheme, get_lot_owner, search_oc_rules]


# ---------------------------------------------------------------------------
# State
#
# add_messages is LangGraph's reducer for conversation history. It appends
# rather than replaces, which is exactly what messages.append() did in the
# while loop. Without it, each turn would wipe the previous one.
# ---------------------------------------------------------------------------

class TriageState(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int


llm = ChatAnthropic(model=MODEL, max_tokens=2000).bind_tools(TOOLS)


def agent_node(state: TriageState) -> dict:
    """Call the model. Returns its reply, which may contain tool calls."""
    reply = llm.invoke(state["messages"])
    return {"messages": [reply], "turns": state.get("turns", 0) + 1}


def should_continue(state: TriageState) -> str:
    """Conditional edge. This replaces the `if response.stop_reason ==
    'tool_use'` check in the while loop, and the MAX_TURNS cap."""
    if state.get("turns", 0) >= MAX_TURNS:
        return END
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


builder = StateGraph(TriageState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, ["tools", END])
builder.add_edge("tools", "agent")

graph = builder.compile()


# ---------------------------------------------------------------------------
# Same interface as run_agent in agent.py, so batch.py can score this
# unchanged. Returns (result_dict, tool_calls_made, error_string).
# ---------------------------------------------------------------------------

def run_agent(client, email, categories, urgency_definitions, verbose=True):
    """`client` is accepted and ignored. LangGraph builds its own client. The
    argument stays so batch.py does not have to know which version it is
    calling."""
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

    try:
        final = graph.invoke({
            "messages": [SystemMessage(content=system),
                         HumanMessage(content=user_message)],
            "turns": 0,
        })
    except Exception as exc:
        return None, [], "graph error: %s" % exc

    # Pull the tool calls back out of the message history so the shape matches
    # what agent.py returns.
    tool_calls_made = []
    for message in final["messages"]:
        for call in getattr(message, "tool_calls", None) or []:
            tool_calls_made.append({"tool": call["name"], "input": call["args"]})
            if verbose:
                print("  %s(%s)" % (call["name"],
                      ", ".join("%s=%r" % kv for kv in call["args"].items())))

    last = final["messages"][-1]
    text = last.content if isinstance(last.content, str) else "".join(
        block.get("text", "") for block in last.content
        if isinstance(block, dict)
    )

    try:
        return parse_json_reply(text), tool_calls_made, None
    except Exception as exc:
        return None, tool_calls_made, "could not parse: %s | %r" % (exc, text[:300])


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: python -m oc.graph_agent EM023")
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

    result, tool_calls, error = run_agent(
        None, email, data["categories"], data["urgency_definitions"],
        verbose="--quiet" not in sys.argv,
    )

    if error:
        print("\nERROR:", error)
        return

    label = email["label"]
    print("-" * 70)
    for field in ["category", "secondary_category", "urgency",
                  "requires_committee_decision"]:
        got = result.get(field)
        want = label.get(field)
        mark = "ok  " if got == want else "MISS"
        print("%s %-28s graph=%-28s label=%s" % (mark, field, got, want))

    print("\ntools called: %d" % len(tool_calls))
    print("rules cited:  %s" % (result.get("rules_cited") or "none"))
    print("\nreasoning:", result.get("reasoning"))
    print("\n--- draft reply ---")
    print(result.get("draft_reply") or "(none - escalated)")
    print("--- end draft ---")


if __name__ == "__main__":
    main()