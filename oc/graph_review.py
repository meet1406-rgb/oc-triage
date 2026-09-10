"""
oc/graph_review.py

V2 with human in the loop, done properly.

WHAT THIS ADDS OVER graph_agent.py
graph_agent.py was a controlled comparison: same prompt, same tools, same
output, only the framework changed. It found that the framework changed
nothing measurable.

This file is where the framework actually earns its place. The graph pauses
at a human_review node using interrupt(), persists its entire state to SQLite,
and resumes from that state whenever the reviewer answers - minutes or days
later, in a different process.

That replaces data/queue.json and the review CLI with something that survives
a restart mid-case.

THERE IS STILL NO SEND FUNCTION. Approve means the manager signed off on the
text, not that anything was delivered.

A NOTE ON RE-EXECUTION
When a graph resumes, the interrupted node runs again from the top and
interrupt() returns the resume value instead of pausing. So any code before
the interrupt() call executes twice. Keep side effects out of that node.

Usage from the project root:
    python -m oc.graph_review start EM023     triage and pause for review
    python -m oc.graph_review list            show every paused case
    python -m oc.graph_review show EM023      show one paused draft
    python -m oc.graph_review approve EM023
    python -m oc.graph_review reject EM023 "reason"
    python -m oc.graph_review start-all       queue the whole dev set

Synthetic data. Not legal advice.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command

from oc.agent import build_system_prompt, parse_json_reply, DATA_PATH, MAX_TURNS
from oc.graph_agent import TOOLS, llm
from oc.grounding import check_grounding

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "checkpoints.db")


# ---------------------------------------------------------------------------
# State
#
# Wider than graph_agent.py's state, because the review step needs the
# triage result and the grounding verdict available when the human looks at
# it - possibly days after the model produced them.
# ---------------------------------------------------------------------------

class ReviewState(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int
    email: dict
    triage: dict
    tool_calls: list
    grounding: dict
    decision: str
    final_draft: str
    reviewed_at: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def agent_node(state: ReviewState) -> dict:
    reply = llm.invoke(state["messages"])
    return {"messages": [reply], "turns": state.get("turns", 0) + 1}


def should_continue(state: ReviewState) -> str:
    if state.get("turns", 0) >= MAX_TURNS:
        return "parse"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "parse"


def parse_node(state: ReviewState) -> dict:
    """Pull the structured result out of the final message, and collect the
    tool calls that were made along the way."""
    calls = []
    for message in state["messages"]:
        for call in getattr(message, "tool_calls", None) or []:
            calls.append({"tool": call["name"], "input": call["args"]})

    last = state["messages"][-1]
    text = last.content if isinstance(last.content, str) else "".join(
        b.get("text", "") for b in last.content if isinstance(b, dict))

    try:
        triage = parse_json_reply(text)
    except Exception as exc:
        triage = {"error": "could not parse: %s" % exc, "draft_reply": ""}

    return {"triage": triage, "tool_calls": calls}


def grounding_node(state: ReviewState) -> dict:
    """Run the grounding check BEFORE the human sees the draft, so any
    unsupported claim is flagged on the review screen rather than left for
    the reviewer to catch by reading carefully."""
    result = check_grounding(
        state["triage"].get("draft_reply"),
        state["tool_calls"],
        state["triage"].get("rules_cited"),
    )
    return {"grounding": result}


def human_review_node(state: ReviewState) -> dict:
    """Pause here. Everything above this line has already run; everything
    below waits for a person.

    interrupt() returns whatever is passed to Command(resume=...). Until then
    the graph stops and its state sits in SQLite.
    """
    answer = interrupt({
        "email": state["email"],
        "triage": state["triage"],
        "grounding": state["grounding"],
        "tool_calls": [c["tool"] for c in state["tool_calls"]],
    })

    return {
        "decision": answer.get("decision", "skipped"),
        "final_draft": answer.get("text") or state["triage"].get("draft_reply", ""),
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
    }


def finalise_node(state: ReviewState) -> dict:
    """The end of the line. Deliberately does nothing but record.

    If this project ever sent email, this is the node where it would happen,
    and it is the node that does not exist.
    """
    return {}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

builder = StateGraph(ReviewState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(TOOLS))
builder.add_node("parse", parse_node)
builder.add_node("grounding", grounding_node)
builder.add_node("human_review", human_review_node)
builder.add_node("finalise", finalise_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, ["tools", "parse"])
builder.add_edge("tools", "agent")
builder.add_edge("parse", "grounding")
builder.add_edge("grounding", "human_review")
builder.add_edge("human_review", "finalise")
builder.add_edge("finalise", END)


def build_graph():
    """A new connection each time. Cheap, and it proves the point: the state
    lives in the file, not in the process."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return builder.compile(checkpointer=SqliteSaver(conn))


def config_for(email_id):
    """thread_id is what ties a case to its saved state. One email, one thread."""
    return {"configurable": {"thread_id": email_id}}


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def load_emails():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def start(email_id):
    data = load_emails()
    match = [e for e in data["emails"] if e["id"] == email_id.upper()]
    if not match:
        print("no email with id", email_id)
        return
    email = match[0]

    graph = build_graph()
    cfg = config_for(email["id"])

    if graph.get_state(cfg).next:
        print("%s is already in progress. Use show/approve/reject." % email["id"])
        return

    system = build_system_prompt(data["categories"], data["urgency_definitions"])
    user = ("Triage this email.\n\nScheme id: %s\nLot: %s\nFrom: %s\n"
            "Subject: %s\nBody: %s"
            % (email["scheme_id"], email.get("lot"), email["from"],
               email["subject"], email["body"]))

    result = graph.invoke({
        "messages": [SystemMessage(content=system), HumanMessage(content=user)],
        "turns": 0,
        "email": {"id": email["id"], "scheme_id": email["scheme_id"],
                  "lot": email.get("lot"), "from": email["from"],
                  "subject": email["subject"], "body": email["body"]},
        "triage": {}, "tool_calls": [], "grounding": {},
        "decision": "", "final_draft": "", "reviewed_at": "",
    }, cfg)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("%s paused for review" % email["id"])
        print("  %s | %s" % (payload["triage"].get("category"),
                             payload["triage"].get("urgency")))
        flag = "" if payload["grounding"]["grounded"] else "  UNGROUNDED"
        print("  grounding: %s%s" % (payload["grounding"]["grounded"], flag))
        print("\nreview it with: python -m oc.graph_review show %s" % email["id"])
    else:
        print("%s finished without pausing, which should not happen" % email["id"])


def paused_cases():
    """Every thread whose graph is stopped at human_review."""
    graph = build_graph()
    found = []
    for email in load_emails()["emails"]:
        snap = graph.get_state(config_for(email["id"]))
        if snap.next and "human_review" in snap.next:
            found.append((email["id"], snap.values))
    return found


def cmd_list():
    cases = paused_cases()
    if not cases:
        print("nothing waiting. start one with: python -m oc.graph_review start EM023")
        return
    print("%d case(s) waiting for review\n" % len(cases))
    for email_id, values in cases:
        triage = values.get("triage", {})
        grounded = values.get("grounding", {}).get("grounded", True)
        print("%-7s %-28s %-9s %s%s" % (
            email_id,
            triage.get("category", "?"),
            triage.get("urgency", "?"),
            values["email"]["subject"][:32],
            "" if grounded else "   UNGROUNDED",
        ))


def show(email_id):
    graph = build_graph()
    snap = graph.get_state(config_for(email_id.upper()))
    if not snap.next:
        print("%s is not waiting for review" % email_id.upper())
        return

    values = snap.values
    email = values["email"]
    triage = values["triage"]
    grounding = values["grounding"]

    print("=" * 70)
    print("%s | %s | %s" % (email["id"], email["subject"], email["scheme_id"]))
    print("=" * 70)
    print(email["body"])
    print("-" * 70)
    print("category:  %s" % triage.get("category"))
    print("urgency:   %s" % triage.get("urgency"))
    print("authority: %s" % ("committee decision needed"
                             if triage.get("requires_committee_decision")
                             else "manager can act"))
    print("rules:     %s" % (triage.get("rules_cited") or "none"))
    print("tools:     %s" % ", ".join(values.get("tool_calls", []) and
                                      [c["tool"] for c in values["tool_calls"]] or ["none"]))

    if not grounding.get("grounded", True):
        print("\nGROUNDING FAILED:")
        for issue in grounding["issues"]:
            print("  - %s: %s" % (issue["type"], issue["detail"]))

    print("\n--- proposed reply ---")
    print(triage.get("draft_reply") or "(no draft - escalated)")
    print("--- end ---")
    print("\napprove: python -m oc.graph_review approve %s" % email["id"])
    print("reject:  python -m oc.graph_review reject %s \"reason\"" % email["id"])


def resume(email_id, decision, text=None, reason=None):
    graph = build_graph()
    cfg = config_for(email_id.upper())
    if not graph.get_state(cfg).next:
        print("%s is not waiting for review" % email_id.upper())
        return

    payload = {"decision": decision}
    if text:
        payload["text"] = text
    if reason:
        payload["reason"] = reason

    graph.invoke(Command(resume=payload), cfg)
    final = graph.get_state(cfg)
    print("%s %s at %s" % (email_id.upper(), final.values["decision"],
                           final.values["reviewed_at"]))
    print("graph complete, nothing sent")


def start_all():
    data = load_emails()
    graph = build_graph()
    todo = [e for e in data["emails"]
            if not graph.get_state(config_for(e["id"])).next]
    print("starting %d case(s)\n" % len(todo))
    for i, email in enumerate(todo, 1):
        print("[%2d/%d] %s" % (i, len(todo), email["id"]))
        start(email["id"])


def main():
    if len(sys.argv) < 2:
        print(__doc__.split("Usage from the project root:")[1].split("Synthetic")[0])
        return

    command = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "start" and arg:
        start(arg)
    elif command == "start-all":
        start_all()
    elif command == "list":
        cmd_list()
    elif command == "show" and arg:
        show(arg)
    elif command == "approve" and arg:
        resume(arg, "approved")
    elif command == "reject" and arg:
        resume(arg, "rejected", reason=sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print("unknown command. try: start, start-all, list, show, approve, reject")


if __name__ == "__main__":
    main()