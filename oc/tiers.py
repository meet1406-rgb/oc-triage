"""
Tier classification for Victorian owners corporations.

Thresholds sourced from Consumer Affairs Victoria, "Tiers of owners corporations".
The five tier system replaced "prescribed" owners corporations from 1 December 2021.

DETERMINISTIC LOOKUP. Deliberately not something the language model is asked to
recall. Statutory thresholds should not be improvised by a model.

Not legal advice. Re-verify against the current Act before any real use.
"""

TIER_OBLIGATIONS = {
    1: {"definition": "More than 100 occupiable lots, not services only",
        "committee_required": True, "manager_required": True,
        "financial_statements_required": True,
        "financial_check": "audit by a registered or authorised auditor, or an accredited accountant",
        "maintenance_plan_required": True},
    2: {"definition": "51 to 100 occupiable lots, not services only",
        "committee_required": True, "manager_required": False,
        "financial_statements_required": True,
        "financial_check": "review by a member of CPA Australia, IPA or CAANZ",
        "maintenance_plan_required": True},
    3: {"definition": "10 to 50 occupiable lots, not services only",
        "committee_required": True, "manager_required": False,
        "financial_statements_required": True,
        "financial_check": "audit or review, at the owners corporation's choice",
        "maintenance_plan_required": False},
    4: {"definition": "3 to 9 occupiable lots, not services only",
        "committee_required": False, "manager_required": False,
        "financial_statements_required": "only for a year in which annual fees are levied",
        "financial_check": "audit or review, at the owners corporation's choice",
        "maintenance_plan_required": False},
    5: {"definition": "A two lot subdivision, or a services only owners corporation",
        "committee_required": False, "manager_required": False,
        "financial_statements_required": False,
        "financial_check": "audit or review, at the owners corporation's choice",
        "maintenance_plan_required": False},
}


def compute_tier(occupiable_lots: int, services_only: bool) -> int:
    """Return the tier (1-5). services_only is checked FIRST: a services only OC
    is tier 5 no matter how many lots it has. SCH006 exists to catch this."""
    if services_only:
        return 5
    if occupiable_lots <= 2:
        return 5
    if occupiable_lots <= 9:
        return 4
    if occupiable_lots <= 50:
        return 3
    if occupiable_lots <= 100:
        return 2
    return 1


def get_tier_obligations(tier: int) -> dict:
    """Look up what a given tier must do. Not model generated."""
    if tier not in TIER_OBLIGATIONS:
        raise ValueError("tier must be 1-5, got %r" % tier)
    return TIER_OBLIGATIONS[tier]


if __name__ == "__main__":
    cases = [(148, False, 1), (72, False, 2), (34, False, 3),
             (16, False, 3), (6, False, 4), (2, False, 5), (140, True, 5)]
    for lots, svc, expected in cases:
        got = compute_tier(lots, svc)
        flag = "ok  " if got == expected else "FAIL"
        print("%s lots=%4d services_only=%-5s -> tier %d (expected %d)"
              % (flag, lots, svc, got, expected))
