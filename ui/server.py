"""
ui/server.py

A browser front end for the LangGraph review queue.

THE SERVER HOLDS NO STATE.
Every request reads paused cases straight out of data/checkpoints.db, and
every decision resumes the graph. Kill the server mid-review, restart it,
refresh the page, and nothing is lost - because nothing was ever in the
server. That is the point of the checkpointer.

THERE IS STILL NO SEND FUNCTION. A decision records that the manager signed
off on text. Delivery is out of scope.

Run from the project root:
    python ui/server.py

Then open http://127.0.0.1:5000

Synthetic data. Not legal advice.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory
from langgraph.types import Command

from oc.graph_review import build_graph, config_for, load_emails, start

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

VALID_DECISIONS = ("approved", "rejected", "escalated")

# The grounding checker returns machine readable issue types. The reviewer is
# a strata manager, not an engineer, so each one gets a plain heading and the
# exact phrase to look for in the draft.
ISSUE_LABELS = {
    "statute_reference": ("Legislation was not checked",
                          "No source in this system returns legislation, so any "
                          "section number in the draft is unsupported."),
    "ungrounded_lot_fact": ("The lot's finances were not checked",
                            "The draft makes a claim about this lot's account, but "
                            "the owner record was never retrieved."),
    "ungrounded_scheme_fact": ("Building details were not checked",
                               "The draft states facts about the building that were "
                               "not looked up."),
    "invented_rule": ("A cited rule does not exist",
                      "The draft cites a rule number that is not in this scheme's "
                      "registered rules."),
    "unsearched_rule": ("A quoted rule was never retrieved",
                        "The draft quotes a rule without the rules having been "
                        "searched."),
}


def describe_issues(grounding):
    """Turn raw grounding issues into something a manager can act on."""
    out = []
    for issue in grounding.get("issues", []):
        title, explanation = ISSUE_LABELS.get(
            issue["type"], ("Unsupported claim", issue["detail"]))
        out.append({
            "type": issue["type"],
            "title": title,
            "explanation": explanation,
            "detail": issue["detail"],
            # Phrases the UI can select inside the draft.
            "phrases": phrases_for(issue, grounding),
        })
    return out


def phrases_for(issue, grounding):
    if issue["type"] == "statute_reference":
        return grounding.get("statute_claims", [])
    if issue["type"] == "ungrounded_lot_fact":
        return grounding.get("lot_claims", [])
    if issue["type"] == "ungrounded_scheme_fact":
        return grounding.get("scheme_claims", [])
    return []


def case_to_json(email_id, values):
    triage = values.get("triage", {})
    grounding = values.get("grounding", {})
    draft = triage.get("draft_reply") or ""
    return {
        "id": email_id,
        "subject": values["email"]["subject"],
        "building": values["email"]["scheme_id"],
        "lot": values["email"].get("lot"),
        "sender": values["email"]["from"],
        "emailBody": values["email"]["body"],
        "category": triage.get("category"),
        "urgency": triage.get("urgency"),
        "authority": ("Committee decision needed"
                      if triage.get("requires_committee_decision")
                      else "Manager can act"),
        "rulesCited": triage.get("rules_cited") or [],
        "reasoning": triage.get("reasoning") or "",
        "originalDraft": draft,
        "grounded": grounding.get("grounded", True),
        "groundingIssues": describe_issues(grounding),
        "tools": [c["tool"] for c in values.get("tool_calls", [])],
    }


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/api/cases")
def cases():
    """Every email, with its live status read from the checkpoint database.

    Cases stopped at human_review carry their full triage payload. Everything
    else carries just enough for the inbox row.
    """
    graph = build_graph()
    out = []
    for email in load_emails()["emails"]:
        snap = graph.get_state(config_for(email["id"]))

        if snap.next and "human_review" in snap.next:
            row = case_to_json(email["id"], snap.values)
            row["status"] = "awaiting"
            out.append(row)
            continue

        decision = snap.values.get("decision") if snap.values else None
        out.append({
            "id": email["id"],
            "subject": email["subject"],
            "status": decision or "not_started",
            "reviewedAt": snap.values.get("reviewed_at") if snap.values else None,
            "edited": bool(snap.values.get("final_draft")
                           and snap.values.get("final_draft")
                           != snap.values.get("triage", {}).get("draft_reply"))
                      if snap.values else False,
        })
    return jsonify(out)


@app.route("/api/start", methods=["POST"])
def start_case():
    """Run triage for one email so it lands in the review queue.

    This is the only endpoint that calls the model, so it is the only slow
    one. Everything else is a database read.
    """
    email_id = (request.json or {}).get("id", "")
    start(email_id)
    return jsonify({"ok": True, "id": email_id.upper()})


@app.route("/api/decide", methods=["POST"])
def decide():
    """Resume the paused graph with the manager's decision.

    The graph picks up inside human_review, records the outcome, runs
    finalise, and stops. finalise deliberately does nothing. If this project
    ever sent email, that is the node where it would happen, and it is the
    node that does not exist.
    """
    payload = request.json or {}
    email_id = payload.get("id", "").upper()
    decision = payload.get("decision")

    if decision not in VALID_DECISIONS:
        return jsonify({"error": "decision must be one of %s"
                        % ", ".join(VALID_DECISIONS)}), 400

    graph = build_graph()
    cfg = config_for(email_id)
    snap = graph.get_state(cfg)
    if not snap.next or "human_review" not in snap.next:
        return jsonify({"error": "%s is not waiting for review" % email_id}), 409

    resume = {"decision": decision}
    if payload.get("text"):
        resume["text"] = payload["text"]
    if payload.get("reason"):
        resume["reason"] = payload["reason"]

    graph.invoke(Command(resume=resume), cfg)
    final = graph.get_state(cfg).values

    return jsonify({
        "ok": True,
        "id": email_id,
        "decision": final.get("decision"),
        "reviewedAt": final.get("reviewed_at"),
        "edited": bool(payload.get("text")),
    })


if __name__ == "__main__":
    print("OC Triage - correspondence review")
    print("open http://127.0.0.1:5000")
    print("state lives in data/checkpoints.db, not in this process")
    print("nothing in this application sends anything\n")
    app.run(debug=False, port=5000)