"""
oc/tools.py

The functions the agent is allowed to call. Plain Python, no AI.

Every one of these is deterministic and testable on its own. If the agent later
gives a wrong answer, you check these first: if the tools are right, the problem
is the model or the prompt.

Synthetic data. Not legal advice.
"""

import json
import os
import re

from oc.tiers import compute_tier, get_tier_obligations  # noqa: F401

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SCHEMES_DIR = os.path.join(DATA_DIR, "schemes")
RULES_PATH = os.path.join(DATA_DIR, "rules", "oc_rules.md")


# ----------------------------------------------------------------------------
# Tool 1: get_scheme
# ----------------------------------------------------------------------------

def get_scheme(scheme_id: str) -> dict:
    """Return everything known about one owners corporation.

    The tier is COMPUTED here, not stored in the JSON. That is deliberate: the
    tier is derived from lot count and services_only, so storing it would let the
    two drift out of sync.
    """
    scheme_id = scheme_id.strip().upper()
    path = os.path.join(SCHEMES_DIR, scheme_id + ".json")

    if not os.path.exists(path):
        available = sorted(f[:-5] for f in os.listdir(SCHEMES_DIR) if f.endswith(".json"))
        return {"error": "no such scheme", "scheme_id": scheme_id,
                "available_schemes": available}

    with open(path, encoding="utf-8") as f:
        scheme = json.load(f)

    tier = compute_tier(scheme["occupiable_lots"], scheme["services_only"])
    scheme["tier"] = tier
    scheme["tier_obligations"] = get_tier_obligations(tier)

    # Lot owners are personal data. Return only the count here; use
    # get_lot_owner() when a specific lot is actually relevant.
    scheme["lot_owner_records_available"] = len(scheme.pop("lot_owners", []))
    return scheme


# ----------------------------------------------------------------------------
# Tool 2: get_lot_owner
# ----------------------------------------------------------------------------

def get_lot_owner(scheme_id: str, lot_number: int) -> dict:
    """Return the owner record for one lot in one scheme."""
    scheme_id = scheme_id.strip().upper()
    path = os.path.join(SCHEMES_DIR, scheme_id + ".json")

    if not os.path.exists(path):
        return {"error": "no such scheme", "scheme_id": scheme_id}

    with open(path, encoding="utf-8") as f:
        scheme = json.load(f)

    for owner in scheme.get("lot_owners", []):
        if owner["lot"] == lot_number:
            result = dict(owner)
            result["scheme_id"] = scheme_id
            return result

    known = sorted(o["lot"] for o in scheme.get("lot_owners", []))
    return {"error": "no record for that lot", "scheme_id": scheme_id,
            "lot_number": lot_number, "lots_on_file": known}


# ----------------------------------------------------------------------------
# Tool 3: search_oc_rules
# ----------------------------------------------------------------------------

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "i", "we",
    "my", "our", "it", "its", "of", "to", "in", "on", "for", "and", "or", "but",
    "can", "could", "would", "should", "do", "does", "did", "have", "has", "had",
    "this", "that", "there", "here", "what", "when", "who", "how", "why", "if",
    "not", "no", "yes", "please", "hi", "hello", "thanks", "you", "your", "me",
    "from", "with", "at", "as", "by", "about", "any", "all", "some", "get", "got",
}


def _load_rules() -> list:
    """Split the rules markdown into one dict per rule. Cached on first call."""
    if getattr(_load_rules, "_cache", None) is not None:
        return _load_rules._cache

    with open(RULES_PATH, encoding="utf-8") as f:
        text = f.read()

    rules = []
    # Each rule starts with a line like: **Rule 2.3 - Alterations to common property**
    chunks = re.split(r"\n\*\*Rule ", text)
    for chunk in chunks[1:]:
        header, _, body = chunk.partition("**")
        number, _, title = header.partition(" - ")
        rules.append({
            "rule_number": number.strip(),
            "title": title.strip(),
            "text": " ".join(body.split()).split("## ")[0].strip(),
        })

    _load_rules._cache = rules
    return rules


def search_oc_rules(query: str, max_results: int = 3) -> list:
    """Find rules relevant to a query.

    Deliberately a simple keyword overlap score, NOT a vector database. Start
    dumb. Upgrade only if the eval shows retrieval is the thing that's failing.
    """
    terms = {w for w in re.findall(r"[a-z]+", query.lower())
             if w not in _STOPWORDS and len(w) > 2}
    if not terms:
        return []

    scored = []
    for rule in _load_rules():
        haystack = (rule["title"] + " " + rule["text"]).lower()
        score = sum(1 for t in terms if t in haystack)
        # A hit in the title is worth more than a hit in the body.
        score += sum(1 for t in terms if t in rule["title"].lower())
        if score > 0:
            scored.append((score, rule))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["rule_number"]))
    return [dict(rule, match_score=score) for score, rule in scored[:max_results]]


def list_all_rules() -> list:
    """Every rule number and title. Useful for checking citations in the eval."""
    return [{"rule_number": r["rule_number"], "title": r["title"]} for r in _load_rules()]


# ----------------------------------------------------------------------------
# Self test
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== get_scheme('SCH001') ===")
    s = get_scheme("SCH001")
    print(s["name"], "|", s["occupiable_lots"], "lots | tier", s["tier"])
    print("maintenance plan required:", s["tier_obligations"]["maintenance_plan_required"])

    print("\n=== get_scheme('SCH006') the trap ===")
    s6 = get_scheme("SCH006")
    print(s6["name"], "|", s6["occupiable_lots"], "lots | services_only",
          s6["services_only"], "| tier", s6["tier"])

    print("\n=== get_scheme('SCH999') a bad id ===")
    print(get_scheme("SCH999"))

    print("\n=== get_lot_owner('SCH001', 47) ===")
    print(get_lot_owner("SCH001", 47))

    print("\n=== get_lot_owner('SCH001', 999) ===")
    print(get_lot_owner("SCH001", 999))

    print("\n=== search_oc_rules('my neighbour is playing loud music at 2am') ===")
    for r in search_oc_rules("my neighbour is playing loud music at 2am"):
        print(" ", r["rule_number"], "-", r["title"], "(score", r["match_score"], ")")

    print("\n=== search_oc_rules('can I install an air conditioner on the balcony wall') ===")
    for r in search_oc_rules("can I install an air conditioner on the balcony wall"):
        print(" ", r["rule_number"], "-", r["title"], "(score", r["match_score"], ")")

    print("\n=== search_oc_rules('can I put floorboards in my apartment') ===")
    for r in search_oc_rules("can I put floorboards in my apartment"):
        print(" ", r["rule_number"], "-", r["title"], "(score", r["match_score"], ")")

    print("\n=== list_all_rules() ===")
    print(len(list_all_rules()), "rules loaded")