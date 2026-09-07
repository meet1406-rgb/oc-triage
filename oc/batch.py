"""
oc/batch.py

Run the agent across every email and score it.

This is the file that turns the project from a demo into an evaluation. It
measures four things:

  category accuracy      did it route the email correctly
  urgency accuracy       did it judge priority correctly
  authority accuracy     did it know when the manager cannot act alone
  citation validity      did every rule it cited actually exist

Citation validity is the important one. The other three compare against your
labels, which are opinions. Citation validity is objective: a rule number either
exists in the rules file or it does not.

Usage from the project root:
    python -m oc.batch                run all emails
    python -m oc.batch --limit 5      run the first five, to check it works
    python -m oc.batch --quiet        no per email trace

Results are written to eval/results/ with a timestamp so you can compare runs.

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
from oc.tools import list_all_rules
from oc.grounding import check_grounding
load_dotenv()

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "eval", "results",
)


def score_run(email, result, tool_calls):
    """Compare one agent result against the label. Returns a dict of outcomes."""
    label = email["label"]
    valid_rules = {r["rule_number"] for r in list_all_rules()}

    cited = result.get("rules_cited") or []
    bad_citations = [c for c in cited if str(c).strip() not in valid_rules]
    grounding = check_grounding(
        result.get("draft_reply"), tool_calls, cited)

    return {
        "id": email["id"],
        "category_hit": result.get("category") == label.get("category"),
        "category_agent": result.get("category"),
        "category_label": label.get("category"),
        "urgency_hit": result.get("urgency") == label.get("urgency"),
        "urgency_agent": result.get("urgency"),
        "urgency_label": label.get("urgency"),
        "authority_hit": (result.get("requires_committee_decision")
                          == label.get("requires_committee_decision")),
        "authority_agent": result.get("requires_committee_decision"),
        "authority_label": label.get("requires_committee_decision"),
        "rules_cited": cited,
        "bad_citations": bad_citations,
        "drafted": bool((result.get("draft_reply") or "").strip()),
        "draft_reply": result.get("draft_reply"),
        "reasoning": result.get("reasoning"),
                "grounded": grounding["grounded"],
        "grounding_issues": grounding["issues"],
    }


def main():
    quiet = "--quiet" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    emails = data["emails"][:limit] if limit else data["emails"]
    client = anthropic.Anthropic()

    print("running the agent over %d emails" % len(emails))
    print("this makes several API calls per email, so expect a few minutes\n")

    scored = []
    errors = []
    tool_call_counts = []
    started = time.time()

    for i, email in enumerate(emails, 1):
        print("[%2d/%d] %s %s" % (i, len(emails), email["id"], email["subject"][:40]))

        result, tool_calls, error = run_agent(
            client, email, data["categories"], data["urgency_definitions"],
            verbose=False,
        )

        if error:
            print("        ERROR: %s" % error[:100])
            errors.append({"id": email["id"], "error": error})
            continue

        row = score_run(email, result, tool_calls)
        row["tool_calls"] = len(tool_calls)
        row["tools_used"] = [t["tool"] for t in tool_calls]
        scored.append(row)
        tool_call_counts.append(len(tool_calls))

        if not quiet:
            flags = []
            if not row["category_hit"]:
                flags.append("cat:%s(want %s)" % (row["category_agent"], row["category_label"]))
            if not row["urgency_hit"]:
                flags.append("urg:%s(want %s)" % (row["urgency_agent"], row["urgency_label"]))
            if not row["authority_hit"]:
                flags.append("auth:%s(want %s)" % (row["authority_agent"], row["authority_label"]))
            if row["bad_citations"]:
                flags.append("BAD CITATION %s" % row["bad_citations"])
            print("        %s | %d tools | rules %s%s"
                  % ("ok" if not flags else "MISS",
                     row["tool_calls"],
                     row["rules_cited"] or "-",
                     ("  <- " + "; ".join(flags)) if flags else ""))

        time.sleep(0.3)

    elapsed = time.time() - started
    n = len(scored)
    if n == 0:
        print("\nno successful runs")
        return

    cat = sum(1 for r in scored if r["category_hit"])
    urg = sum(1 for r in scored if r["urgency_hit"])
    auth = sum(1 for r in scored if r["authority_hit"])
    with_citations = [r for r in scored if r["rules_cited"]]
    clean_citations = [r for r in with_citations if not r["bad_citations"]]

    print("\n" + "=" * 62)
    print("scored %d emails in %.0f seconds (%d errors)" % (n, elapsed, len(errors)))
    print("=" * 62)
    print("category accuracy    %2d/%d = %3.0f%%" % (cat, n, 100.0 * cat / n))
    print("urgency accuracy     %2d/%d = %3.0f%%" % (urg, n, 100.0 * urg / n))
    print("authority accuracy   %2d/%d = %3.0f%%" % (auth, n, 100.0 * auth / n))

    if with_citations:
        print("citation validity    %2d/%d = %3.0f%%  (emails where every cited rule exists)"
              % (len(clean_citations), len(with_citations),
                 100.0 * len(clean_citations) / len(with_citations)))
    else:
        print("citation validity    no emails cited any rules")

    grounded = [r for r in scored if r["grounded"]]
    print("grounding             %2d/%d = %3.0f%%  (drafts where every claim is backed by a tool call)"
          % (len(grounded), n, 100.0 * len(grounded) / n))
    print("\nemails that cited a rule: %d of %d" % (len(with_citations), n))
    print("emails with a draft:      %d of %d" % (sum(1 for r in scored if r["drafted"]), n))
    print("mean tool calls:          %.1f" % (sum(tool_call_counts) / float(n)))

    misses = [r["id"] for r in scored if not r["category_hit"]]
    print("\ncategory misses:  %s" % (misses or "none"))
    print("urgency misses:   %s" % ([r["id"] for r in scored if not r["urgency_hit"]] or "none"))
    print("authority misses: %s" % ([r["id"] for r in scored if not r["authority_hit"]] or "none"))
    bad = [(r["id"], r["bad_citations"]) for r in scored if r["bad_citations"]]
    print("invented rules:   %s" % (bad or "none"))
    ungrounded = [(r["id"], [i["type"] for i in r["grounding_issues"]])
                  for r in scored if not r["grounded"]]
    print("ungrounded:       %s" % (ungrounded or "none"))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULTS_DIR, "agent_run_%s.json" % stamp)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": stamp,
            "emails_scored": n,
            "errors": errors,
            "summary": {
                "category_accuracy": cat / float(n),
                "urgency_accuracy": urg / float(n),
                "authority_accuracy": auth / float(n),
                "citation_validity": (len(clean_citations) / float(len(with_citations))
                                      if with_citations else None),
                "mean_tool_calls": sum(tool_call_counts) / float(n),
            },
            "rows": scored,
        }, f, indent=2)
    print("\nsaved: %s" % out_path)


if __name__ == "__main__":
    main()
    