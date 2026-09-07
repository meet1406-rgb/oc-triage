"""
setup_data.py

Creates the synthetic data for the OC triage project.
Run once:  python setup_data.py

All scheme data is FICTIONAL. Not real owners corporations. Not legal advice.
Tier thresholds are sourced from Consumer Affairs Victoria, "Tiers of owners
corporations" (five tier system, effective 1 December 2021).
"""

import json
import os

SCHEMES = [
    {
        "scheme_id": "SCH001", "plan_number": "PS612884K",
        "name": "Elara Residences",
        "address": "88 Kavanagh Street, Southbank VIC 3006",
        "occupiable_lots": 148, "services_only": False,
        "manager_appointed": True, "manager_name": "Fictional Strata Partners Pty Ltd",
        "committee_elected": True, "committee_members": 7,
        "annual_fees_levied": True, "annual_fee_total_aud": 1284000,
        "maintenance_plan": {"exists": True, "approved": True, "last_approved": "2025-11-14"},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-8841-A",
                      "renewal_date": "2026-10-01", "sum_insured_aud": 96000000},
        "financials": {"last_checked": "2025-09-30", "method": "audit"},
        "agm": {"last_held": "2025-11-14", "next_due": "2026-11-14"},
        "common_property": ["lobby", "two lifts", "rooftop terrace", "gymnasium",
                            "pool", "basement car park", "corridors", "bin room"],
        "notes": "High rise. Tier 1.",
        "lot_owners": [
            {"lot": 12, "name": "A. Fictional", "email": "lot12@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": True},
            {"lot": 47, "name": "B. Fictional", "email": "lot47@example.invalid",
             "levy_balance_aud": 1840.50, "in_arrears": True, "owner_occupier": False},
            {"lot": 103, "name": "C. Fictional", "email": "lot103@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": True},
        ],
    },
    {
        "scheme_id": "SCH002", "plan_number": "PS540117J",
        "name": "The Nicholson",
        "address": "412 Nicholson Street, Carlton North VIC 3054",
        "occupiable_lots": 72, "services_only": False,
        "manager_appointed": True, "manager_name": "Fictional Strata Partners Pty Ltd",
        "committee_elected": True, "committee_members": 5,
        "annual_fees_levied": True, "annual_fee_total_aud": 486000,
        "maintenance_plan": {"exists": True, "approved": False, "last_approved": None},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-2210-B",
                      "renewal_date": "2026-09-12", "sum_insured_aud": 41000000},
        "financials": {"last_checked": "2025-10-20", "method": "review"},
        "agm": {"last_held": "2025-10-20", "next_due": "2026-10-20"},
        "common_property": ["lobby", "one lift", "shared laundry", "courtyard",
                            "basement car park", "corridors"],
        "notes": "Tier 2. Maintenance plan exists but is NOT approved. Edge case.",
        "lot_owners": [
            {"lot": 8, "name": "D. Fictional", "email": "lot8@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": True},
            {"lot": 31, "name": "E. Fictional", "email": "lot31@example.invalid",
             "levy_balance_aud": 620.00, "in_arrears": True, "owner_occupier": True},
        ],
    },
    {
        "scheme_id": "SCH003", "plan_number": "PS703442C",
        "name": "Craigieburn Rise",
        "address": "22 Hanson Road, Craigieburn VIC 3064",
        "occupiable_lots": 34, "services_only": False,
        "manager_appointed": True, "manager_name": "Fictional Strata Partners Pty Ltd",
        "committee_elected": True, "committee_members": 3,
        "annual_fees_levied": True, "annual_fee_total_aud": 142000,
        "maintenance_plan": {"exists": False, "approved": False, "last_approved": None},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-5537-C",
                      "renewal_date": "2026-08-29", "sum_insured_aud": 14200000},
        "financials": {"last_checked": "2025-08-29", "method": "review"},
        "agm": {"last_held": "2025-08-29", "next_due": "2026-08-29"},
        "common_property": ["driveway", "visitor parking", "shared garden",
                            "letterbox bank", "bin enclosure"],
        "notes": "Tier 3 townhouse estate. Insurance renewal is soon.",
        "lot_owners": [
            {"lot": 4, "name": "F. Fictional", "email": "lot4@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": True},
            {"lot": 19, "name": "G. Fictional", "email": "lot19@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": False},
        ],
    },
    {
        "scheme_id": "SCH004", "plan_number": "PS448209M",
        "name": "Wattle Court",
        "address": "9 Wattle Grove, Preston VIC 3072",
        "occupiable_lots": 16, "services_only": False,
        "manager_appointed": False, "manager_name": None,
        "committee_elected": True, "committee_members": 3,
        "annual_fees_levied": True, "annual_fee_total_aud": 61000,
        "maintenance_plan": {"exists": False, "approved": False, "last_approved": None},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-1198-D",
                      "renewal_date": "2027-02-11", "sum_insured_aud": 7400000},
        "financials": {"last_checked": "2025-07-02", "method": "neither"},
        "agm": {"last_held": "2025-07-02", "next_due": "2026-07-02"},
        "common_property": ["driveway", "shared garden", "bin enclosure"],
        "notes": "Tier 3. Self managed, no professional manager appointed.",
        "lot_owners": [
            {"lot": 2, "name": "H. Fictional", "email": "lot2@example.invalid",
             "levy_balance_aud": 310.00, "in_arrears": True, "owner_occupier": True},
        ],
    },
    {
        "scheme_id": "SCH005", "plan_number": "PS331076F",
        "name": "Mercer Lane Terraces",
        "address": "5 Mercer Lane, Brunswick VIC 3056",
        "occupiable_lots": 6, "services_only": False,
        "manager_appointed": False, "manager_name": None,
        "committee_elected": False, "committee_members": 0,
        "annual_fees_levied": True, "annual_fee_total_aud": 18400,
        "maintenance_plan": {"exists": False, "approved": False, "last_approved": None},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-7702-E",
                      "renewal_date": "2026-12-03", "sum_insured_aud": 3100000},
        "financials": {"last_checked": None, "method": "neither"},
        "agm": {"last_held": "2025-12-03", "next_due": "2026-12-03"},
        "common_property": ["shared driveway", "bin area"],
        "notes": "Tier 4. No committee, decisions made by the OC in general meeting.",
        "lot_owners": [
            {"lot": 3, "name": "J. Fictional", "email": "lot3@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": True},
        ],
    },
    {
        "scheme_id": "SCH006", "plan_number": "PS629915T",
        "name": "Harbour Quarter Services OC",
        "address": "1 Bourke Street, Docklands VIC 3008",
        "occupiable_lots": 140, "services_only": True,
        "manager_appointed": True, "manager_name": "Fictional Strata Partners Pty Ltd",
        "committee_elected": False, "committee_members": 0,
        "annual_fees_levied": True, "annual_fee_total_aud": 305000,
        "maintenance_plan": {"exists": False, "approved": False, "last_approved": None},
        "insurance": {"insurer": "Fictional Mutual", "policy_number": "FM-9043-F",
                      "renewal_date": "2026-09-30", "sum_insured_aud": 0},
        "financials": {"last_checked": None, "method": "neither"},
        "agm": {"last_held": "2025-09-30", "next_due": "2026-09-30"},
        "common_property": ["shared water supply", "shared fire services", "access road"],
        "notes": "TRAP CASE. 140 lots but services only, so tier 5 not tier 1.",
        "lot_owners": [
            {"lot": 55, "name": "K. Fictional", "email": "lot55@example.invalid",
             "levy_balance_aud": 0.0, "in_arrears": False, "owner_occupier": False},
        ],
    },
]

TIERS_PY = '''"""
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
'''

RULES_MD = """# Owners Corporation Rules

**FICTIONAL synthetic test data. Not the rules of any real owners corporation.
Not legal advice.**

Applies to: SCH001 to SCH006

---

## Part 1 - Health, safety and security

**Rule 1.1 - Obstruction of common property**
A lot owner or occupier must not obstruct the lawful use of common property by
others, including corridors, stairwells, driveways and fire egress paths. Items
left in these areas may be removed after 7 days written notice.

**Rule 1.2 - Fire safety equipment**
A lot owner or occupier must not tamper with, obstruct or disable any fire safety
equipment, including sprinklers, detectors, hydrants, extinguishers and fire doors.
Propping open a fire door is a breach of this rule.

**Rule 1.3 - Security of the building**
A lot owner or occupier must not lend, copy or transfer a security key, fob or
access code without the written approval of the owners corporation.

**Rule 1.4 - Hazardous items**
A lot owner or occupier must not store flammable liquids, gas cylinders or other
hazardous material on common property or in a car space, except for fuel contained
in a vehicle's tank.

## Part 2 - Management of common property

**Rule 2.1 - Use of common property**
A lot owner or occupier must not use common property in a way that unreasonably
interferes with another person's use and enjoyment of it.

**Rule 2.2 - Damage to common property**
A lot owner or occupier who damages common property, or whose visitor, tenant or
contractor damages common property, is responsible for the cost of repair.

**Rule 2.3 - Alterations to common property**
A lot owner must not alter, install anything on, or attach anything to common
property without the prior written approval of the owners corporation. This
includes air conditioning condensers, security cameras, screen doors, awnings,
satellite dishes and external fixtures.

**Rule 2.4 - Repairs**
Requests for repair to common property must be made in writing to the owners
corporation manager. Repairs within a lot, including internal plumbing fixtures,
floor coverings, internal walls and appliances, are the responsibility of the lot
owner and are not the responsibility of the owners corporation.

## Part 3 - Vehicles and parking

**Rule 3.1 - Allocated spaces**
A lot owner or occupier must park only in the car space allocated to their lot.

**Rule 3.2 - Visitor parking**
Visitor parking is for visitors only, for a maximum of 24 consecutive hours. It
must not be used by lot owners, occupiers or their tenants for regular parking.

**Rule 3.3 - Vehicle maintenance**
A lot owner or occupier must not carry out vehicle repairs or maintenance on
common property, other than minor emergency repairs.

## Part 4 - Behaviour

**Rule 4.1 - Noise**
A lot owner or occupier must not create noise likely to unreasonably interfere
with the peaceful enjoyment of another person. Building work, power tools and
amplified music are not permitted between 8:00 pm and 7:00 am on weekdays, or
between 8:00 pm and 9:00 am on weekends and public holidays.

**Rule 4.2 - Visitors**
A lot owner or occupier is responsible for the behaviour of their visitors,
tenants and contractors while those persons are on common property.

**Rule 4.3 - Smoking**
A lot owner or occupier must not smoke on common property, and must take
reasonable steps to prevent smoke drift from their lot.

## Part 5 - Animals

**Rule 5.1 - Keeping of animals**
A lot owner or occupier who keeps an animal must notify the owners corporation in
writing within 14 days, providing the animal's type, breed and name.

**Rule 5.2 - Animals on common property**
An animal must be under effective control on common property. A dog must be on a
lead. An owner must immediately remove and dispose of any animal waste.

**Rule 5.3 - Assistance animals**
Rules 5.1 and 5.2 do not restrict the keeping or use of an assistance animal.

## Part 6 - Rubbish

**Rule 6.1 - Disposal of rubbish**
A lot owner or occupier must dispose of rubbish in the bins provided and must not
leave rubbish in corridors, bin rooms or bin enclosures outside the bins.

**Rule 6.2 - Hard rubbish**
Hard rubbish, including furniture, mattresses and whitegoods, must not be left on
common property. Disposal is the responsibility of the lot owner or occupier.

## Part 7 - Works within a lot

**Rule 7.1 - Notice of works**
A lot owner must give the owners corporation at least 14 days written notice
before commencing building works within their lot that involve structural change,
waterproofing, or works exceeding 5 consecutive days.

**Rule 7.2 - Hard floor coverings**
A lot owner must obtain the prior written approval of the owners corporation
before installing hard floor coverings in a lot located above another lot.
Approval may be conditional on an acoustic underlay meeting a specified rating.

**Rule 7.3 - Contractor access**
Contractors engaged by a lot owner may access common property between 7:00 am and
6:00 pm on weekdays and 9:00 am and 5:00 pm on Saturdays. No contractor access is
permitted on Sundays or public holidays without prior written approval.

## Part 8 - Short stay accommodation

**Rule 8.1 - Notification**
A lot owner who offers their lot for short stay accommodation must notify the
owners corporation in writing and provide a 24 hour contact number for the person
managing the arrangement.
"""


def main():
    for folder in ["data/schemes", "data/rules", "oc"]:
        os.makedirs(folder, exist_ok=True)
        print("folder ready:", folder)

    for scheme in SCHEMES:
        path = os.path.join("data", "schemes", scheme["scheme_id"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scheme, f, indent=2)
        print("wrote:", path)

    with open(os.path.join("data", "rules", "oc_rules.md"), "w", encoding="utf-8") as f:
        f.write(RULES_MD)
    print("wrote: data/rules/oc_rules.md")

    with open(os.path.join("oc", "tiers.py"), "w", encoding="utf-8") as f:
        f.write(TIERS_PY)
    print("wrote: oc/tiers.py")

    print("\nDone. Now run:  python oc/tiers.py")


if __name__ == "__main__":
    main()