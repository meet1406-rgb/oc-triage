"""
oc/grounding.py

Checks whether claims in a draft are backed by tool calls.

WHAT THIS IS
A crude keyword scan, not a proof. It looks for phrases that assert a fact and
then asks whether the matching tool was actually called. It will produce false
positives (a draft saying "if you fall into arrears" asserts nothing) and it
will miss things a determined model could phrase around.

It is still worth having, because it turns "I read the draft and got suspicious"
into a number that runs on every email every time.

WHY IT EXISTS
Citation validity only checks rule numbers against the rules file. A draft that
cites no rules scores 100% clean even if it invents a statute section or asserts
a levy balance it never looked up. That happened on EM003 and the evaluation
could not tell the grounded version from the invented one.

Synthetic data. Not legal advice.
"""

import re

from oc.tools import list_all_rules


# Phrases that assert something about a specific lot's financial position or
# owner. If any appear, get_lot_owner should have been called for that lot.
LOT_FACT_PATTERNS = [
    r"\bin arrears\b",
    r"\bnot currently in arrears\b",
    r"\blevy balance\b",
    r"\boutstanding balance\b",
    r"\bnil balance\b",
    r"\byour balance\b",
    r"\bowe[sd]?\s+\$",
    r"\byour account is\b",
    r"\bpaid in full\b",
]

# Anything that looks like a citation to legislation. There is no statute tool
# in this project, so every one of these is invented by definition.
STATUTE_PATTERNS = [
    r"\bsection\s+\d+",
    r"\bs\.?\s?\d+\s+of the\b",
    r"\bunder the (Owners Corporations )?Act\b",
    r"\bOwners Corporations Act\b",
    r"\bstatutory\s+\d+",
    r"\bregulation\s+\d+",
]

# Claims about the scheme itself. get_scheme should have been called.
SCHEME_FACT_PATTERNS = [
    r"\btier\s+[1-5]\b",
    r"\bmaintenance plan\b",
    r"\bsum insured\b",
    r"\brenewal date\b",
    r"\bpolicy\s+FM-",
    r"\bnext AGM\b",
    r"\blast AGM\b",
    r"\boccupiable lots\b",
]

# "section 32" is the vendor statement in a property contract, which owners and
# conveyancers name in ordinary correspondence. Referring to it is not a claim
# about what any statute says, so it is excluded from the statute check.
STATUTE_ALLOWLIST = [
    r"\bsection\s+32\b",
]


def _matches(text, patterns):
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append(match.group(0).strip())
    return sorted(set(found))


def _strip_allowlisted(text):
    for pattern in STATUTE_ALLOWLIST:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def check_grounding(draft, tool_calls, rules_cited):
    """Return a dict describing whether the draft's claims are backed.

    draft        the proposed reply text
    tool_calls   list of {"tool": name, "input": {...}} from run_agent
    rules_cited  list of rule numbers the agent said it relied on
    """
    draft = draft or ""
    issues = []

    tools_called = {call["tool"] for call in tool_calls}
    lot_lookups = [call for call in tool_calls if call["tool"] == "get_lot_owner"]

    # 1. Lot facts need get_lot_owner
    lot_claims = _matches(draft, LOT_FACT_PATTERNS)
    if lot_claims and not lot_lookups:
        issues.append({
            "type": "ungrounded_lot_fact",
            "detail": "draft asserts %s but get_lot_owner was never called" % lot_claims,
        })

    # 2. Statute references are always ungrounded - there is no statute tool
    statute_claims = _matches(_strip_allowlisted(draft), STATUTE_PATTERNS)
    if statute_claims:
        issues.append({
            "type": "statute_reference",
            "detail": "draft refers to legislation (%s) but no tool returns statute"
                      % statute_claims,
        })

    # 3. Scheme facts need get_scheme
    scheme_claims = _matches(draft, SCHEME_FACT_PATTERNS)
    if scheme_claims and "get_scheme" not in tools_called:
        issues.append({
            "type": "ungrounded_scheme_fact",
            "detail": "draft asserts %s but get_scheme was never called" % scheme_claims,
        })

    # 4. Rule numbers must exist (this duplicates the citation check, kept here
    #    so grounding is a single self-contained verdict)
    valid = {r["rule_number"] for r in list_all_rules()}
    bad_rules = [r for r in (rules_cited or []) if str(r).strip() not in valid]
    if bad_rules:
        issues.append({
            "type": "invented_rule",
            "detail": "cited rules that do not exist: %s" % bad_rules,
        })

    # 5. A rule quoted in the draft body but never searched for
    inline_rules = sorted(set(re.findall(r"\bRule\s+(\d+\.\d+)", draft)))
    if inline_rules and "search_oc_rules" not in tools_called:
        issues.append({
            "type": "unsearched_rule",
            "detail": "draft quotes %s but search_oc_rules was never called" % inline_rules,
        })

    return {
        "grounded": not issues,
        "issues": issues,
        "lot_claims": lot_claims,
        "statute_claims": statute_claims,
        "scheme_claims": scheme_claims,
        "inline_rules": inline_rules,
        "tools_called": sorted(tools_called),
    }


if __name__ == "__main__":
    # The two real EM003 drafts, before and after the prompt prohibitions.
    invented = ("We are able to prepare an owners corporation certificate for Lot 8 "
                "in accordance with section 151 of the Owners Corporations Act 2006. "
                "As at our last records, the lot is not in arrears and carries a nil "
                "outstanding levy balance. Please note the statutory 10-business-day "
                "period.")
    grounded = ("Thank you for your email regarding Lot 8. For your information, the "
                "lot is not currently in arrears. The scheme is a Tier 2 owners "
                "corporation (72 occupiable lots). A maintenance plan exists; however, "
                "it has not yet been approved.")

    print("=== EM003 original draft, get_scheme only ===")
    result = check_grounding(invented, [{"tool": "get_scheme", "input": {}}], [])
    print("grounded:", result["grounded"])
    for issue in result["issues"]:
        print("  -", issue["type"], "|", issue["detail"])

    print("\n=== EM003 after prohibitions, both tools called ===")
    result = check_grounding(
        grounded,
        [{"tool": "get_scheme", "input": {"scheme_id": "SCH002"}},
         {"tool": "get_lot_owner", "input": {"scheme_id": "SCH002", "lot_number": 8}}],
        [],
    )
    print("grounded:", result["grounded"])
    for issue in result["issues"]:
        print("  -", issue["type"], "|", issue["detail"])

    print("\n=== a draft quoting a rule it never searched for ===")
    result = check_grounding("Under Rule 7.2 you need written approval.",
                             [{"tool": "get_scheme", "input": {}}], ["7.2"])
    print("grounded:", result["grounded"])
    for issue in result["issues"]:
        print("  -", issue["type"], "|", issue["detail"])

    print("\n=== an invented rule number ===")
    result = check_grounding("See Rule 9.9.",
                             [{"tool": "search_oc_rules", "input": {}}], ["9.9"])
    print("grounded:", result["grounded"])
    for issue in result["issues"]:
        print("  -", issue["type"], "|", issue["detail"])