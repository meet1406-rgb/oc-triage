"""
setup_emails.py

Creates 24 synthetic inbound emails with DRAFT labels.
Run from the project root:  python setup_emails.py

LABEL SCHEMA
  category                     one of CATEGORIES. Accuracy is measured on this.
                               This is also what determines routing, so there can
                               only ever be one.
  secondary_category           optional. Captures genuine overlap. Not scored as
                               accuracy, but used to ask a softer question: when
                               the model got the primary wrong, did it pick what
                               was labelled secondary?
  urgency                      urgent | priority | routine. See URGENCY_DEFINITIONS.
  requires_committee_decision  True when the manager cannot act on this alone.

The labels are DRAFTS. Review them and change any you disagree with. Record the
changes; the disagreements are the interesting part.

All content is FICTIONAL. No real people, schemes, or correspondence.
"""

import json
import os

CATEGORIES = [
    "maintenance_common_property",   # repairs the OC is responsible for
    "maintenance_private_lot",       # repairs the owner is responsible for
    "approval_request",              # owner wants permission to do something
    "oc_certificate_request",        # certificate for a sale
    "levy_query",                    # balances, statements, payment arrangements
    "rules_breach_complaint",        # someone reporting someone else
    "meeting_governance",            # AGMs, motions, committee, voting
    "insurance",                     # claims, cover, renewals
    "escalate_immediately",          # the agent must not draft a substantive reply
]

URGENCY_DEFINITIONS = {
    "urgent": "Any of: a safety risk to a person; a situation getting materially "
              "worse by the hour; or a firm external deadline falling within about "
              "48 hours where missing it causes irreversible harm such as a failed "
              "settlement. Needs attention today.",
    "priority": "A real deadline within days, or significant financial or legal "
                "consequence if it slips. Needs attention this week.",
    "routine": "Everything else. Handle in normal course.",
}

EMAILS = [
    {
        "id": "EM001", "scheme_id": "SCH001", "lot": 12,
        "from": "lot12@example.invalid",
        "subject": "Lift out of service again",
        "body": "Hi, the south lift has been out of service since Friday afternoon. "
                "This is the third time in two months. I'm on level 14 and my mother "
                "uses a walking frame. Can someone tell me when it will be fixed?",
        "label": {"category": "maintenance_common_property", "secondary_category": None,
                  "urgency": "urgent", "requires_committee_decision": False},
                "note": "Lifts are common property. Relabelled from priority to urgent: a "
                "resident with limited mobility unable to reach level 14 is a safety "
                "risk to a person, which meets the urgent definition.",
    },
    {
        "id": "EM002", "scheme_id": "SCH003", "lot": 4,
        "from": "lot4@example.invalid",
        "subject": "Dishwasher leaking",
        "body": "My dishwasher has been leaking under the kitchen cabinet and the "
                "floor is starting to swell. Can you send a plumber please.",
        "label": {"category": "maintenance_private_lot", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "Appliance inside the lot. Rule 2.4 puts this on the owner. "
                "Confusion pair with EM008.",
    },
    {
        "id": "EM003", "scheme_id": "SCH002", "lot": 8,
        "from": "conveyancing@example.invalid",
        "subject": "OC certificate request - Lot 8, PS540117J",
        "body": "Good morning, we act for the vendor of Lot 8 and require an owners "
                "corporation certificate for the section 32 statement. Settlement is "
                "scheduled and the contract goes out next week. Please advise the fee "
                "and your preferred payment method.",
        "label": {"category": "oc_certificate_request", "secondary_category": None,
                  "urgency": "priority", "requires_committee_decision": False},
        "note": "Statutory window is days, not hours, so priority under the written "
                "definition. Blocks a sale if missed.",
    },
    {
        "id": "EM004", "scheme_id": "SCH001", "lot": 47,
        "from": "lot47@example.invalid",
        "subject": "Levy statement query",
        "body": "I received a notice saying I'm in arrears but I paid in January. "
                "Can you send me a statement showing what's outstanding and how it "
                "was calculated?",
        "label": {"category": "levy_query", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "Lot 47 is genuinely in arrears in SCH001. Agent should check rather "
                "than assume the owner is wrong or right.",
    },
    {
        "id": "EM005", "scheme_id": "SCH001", "lot": 103,
        "from": "lot103@example.invalid",
        "subject": "Dog in 12 - again",
        "body": "The dog in lot 12 is off lead in the lobby every single morning and "
                "there was mess by the lift on Tuesday that nobody cleaned up. I have "
                "raised this twice. What are you actually going to do about it?",
        "label": {"category": "rules_breach_complaint", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": True},
        "note": "Rule 5.2. Relabelled to requires authority True: the owner is asking "
                "what will be done, and enforcement beyond a courtesy reminder needs "
                "instruction from the committee. Previously marked contested.",
    },
    {
        "id": "EM006", "scheme_id": "SCH002", "lot": 31,
        "from": "lot31@example.invalid",
        "subject": "Floorboards",
        "body": "Hi, we're renovating and want to put floorboards through the living "
                "areas. Do we need to ask anyone or can we just go ahead?",
        "label": {"category": "approval_request",
                  "secondary_category": "maintenance_private_lot",
                  "urgency": "routine", "requires_committee_decision": True},
        "note": "Rule 7.2. Works are inside the lot, hence the secondary, but the "
                "actual ask is permission. Retrieval currently FAILS on 'floorboards' "
                "because the rule says 'hard floor coverings'.",
    },
    {
        "id": "EM007", "scheme_id": "SCH003", "lot": 19,
        "from": "lot19@example.invalid",
        "subject": "Air conditioner install",
        "body": "I want to put an air conditioner in. The condenser would go on the "
                "external wall near the courtyard. Is that alright?",
        "label": {"category": "approval_request", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": True},
        "note": "Rule 2.3, attaching to common property. Retrieval currently ranks "
                "rule 2.4 above 2.3 for this wording.",
    },
    {
        "id": "EM008", "scheme_id": "SCH001", "lot": 12,
        "from": "lot12@example.invalid",
        "subject": "Water coming through my ceiling",
        "body": "There is water coming through the ceiling in my bathroom and it's "
                "getting worse. I don't know if it's the apartment above or a pipe in "
                "the wall. It started last night.",
        "label": {"category": "maintenance_common_property",
                  "secondary_category": "maintenance_private_lot",
                  "urgency": "urgent", "requires_committee_decision": False},
        "note": "AMBIGUOUS ON PURPOSE, and the secondary exists precisely because "
                "nobody knows yet. Correct behaviour is to treat as common until "
                "inspected. Getting worse, so urgent.",
    },
    {
        "id": "EM009", "scheme_id": "SCH002", "lot": 8,
        "from": "lot8@example.invalid",
        "subject": "AGM date",
        "body": "When is the AGM this year? I'd also like to put forward a motion "
                "about the bike storage. What's the process and what's the deadline?",
        "label": {"category": "meeting_governance", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "Genuinely about a meeting. This is what the category now means.",
    },
    {
        "id": "EM010", "scheme_id": "SCH003", "lot": 4,
        "from": "lot4@example.invalid",
        "subject": "Insurance certificate for my lender",
        "body": "My bank is refinancing and has asked for a certificate of currency "
                "for the building insurance. Can you email it through?",
        "label": {"category": "insurance", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "Routine document request.",
    },
    {
        "id": "EM011", "scheme_id": "SCH001", "lot": 47,
        "from": "lot47@example.invalid",
        "subject": "Storm damage to my balcony door",
        "body": "The storm on Saturday blew out the seal on my balcony sliding door "
                "and water got into the carpet. Is that covered by the building "
                "insurance or do I claim on my contents?",
        "label": {"category": "insurance",
                  "secondary_category": "maintenance_common_property",
                  "urgency": "priority", "requires_committee_decision": False},
        "note": "The question asked is about cover, so insurance is primary. The "
                "underlying event is damage, hence the secondary.",
    },
    {
        "id": "EM012", "scheme_id": "SCH005", "lot": 3,
        "from": "lot3@example.invalid",
        "subject": "Do we need a maintenance plan?",
        "body": "One of the other owners says we're legally required to have a "
                "maintenance plan and a fund. We're only six townhouses. Is that "
                "right? Seems like a lot of expense for a shared driveway.",
        "label": {"category": "meeting_governance", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "TIER DEPENDENT. SCH005 is tier 4, so a maintenance plan is optional. "
                "Paired with EM013.",
    },
    {
        "id": "EM013", "scheme_id": "SCH001", "lot": 103,
        "from": "lot103@example.invalid",
        "subject": "Do we need a maintenance plan?",
        "body": "A neighbour mentioned we're supposed to have a maintenance plan. Do "
                "we have one, and are we actually required to?",
        "label": {"category": "meeting_governance", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "TIER DEPENDENT PAIR with EM012. SCH001 is tier 1, so it IS required, "
                "and one is approved. Near identical question, opposite answer.",
    },
    {
        "id": "EM014", "scheme_id": "SCH006", "lot": 55,
        "from": "lot55@example.invalid",
        "subject": "Committee election",
        "body": "I'd like to nominate for the committee at the next meeting. What do "
                "I need to submit and by when?",
        "label": {"category": "meeting_governance", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "TRAP. SCH006 is services only, therefore tier 5, therefore no "
                "committee is required and none is elected. A correct reply explains "
                "that rather than describing a nomination process.",
    },
    {
        "id": "EM015", "scheme_id": "SCH004", "lot": 2,
        "from": "lot2@example.invalid",
        "subject": "Payment plan",
        "body": "Things have been tight since I lost hours at work. I owe about $310. "
                "Can I pay it off over a few months instead of all at once?",
        "label": {"category": "levy_query", "secondary_category": None,
                  "urgency": "priority", "requires_committee_decision": True},
        "note": "The manager cannot unilaterally agree a payment arrangement. Tone of "
                "the draft matters here as much as the routing.",
    },
    {
        "id": "EM016", "scheme_id": "SCH002", "lot": 31,
        "from": "lot31@example.invalid",
        "subject": "Bins overflowing",
        "body": "The bin room has been overflowing since the weekend and it smells. "
                "Are the collections still happening?",
        "label": {"category": "maintenance_common_property", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "Rule 6.1. Common property, straightforward.",
    },
    {
        "id": "EM017", "scheme_id": "SCH001", "lot": 12,
        "from": "lot12@example.invalid",
        "subject": "Someone parked in my space",
        "body": "There's a white ute in my car space, bay 12, and it's been there two "
                "days. I've had to park on the street. Can you have it towed?",
        "label": {"category": "rules_breach_complaint", "secondary_category": None,
                  "urgency": "priority", "requires_committee_decision": True},
        "note": "Rule 3.1. Towing is a significant action the manager cannot "
                "authorise alone. Good test of requires_committee_decision.",
    },
    {
        "id": "EM018", "scheme_id": "SCH003", "lot": 19,
        "from": "lot19@example.invalid",
        "subject": "Insurance renewal",
        "body": "I see the policy is up at the end of August. Are we going out to "
                "market or just renewing? The premium went up a lot last year.",
        "label": {"category": "insurance", "secondary_category": None,
                  "urgency": "priority", "requires_committee_decision": True},
        "note": "SCH003 renewal is 2026-08-29, genuinely close. Choice of insurer is "
                "an OC decision, not the manager's.",
    },
    {
        "id": "EM019", "scheme_id": "SCH002", "lot": 8,
        "from": "lot8@example.invalid",
        "subject": "Neighbour dispute - legal advice needed",
        "body": "The owner in lot 14 has been harassing my wife in the car park and "
                "made a threat last week. I want to know what our legal options are "
                "and whether we can force them to sell.",
        "label": {"category": "escalate_immediately",
                  "secondary_category": "rules_breach_complaint",
                  "urgency": "urgent", "requires_committee_decision": True},
        "note": "Threat to a person plus a request for legal advice. The agent must "
                "NOT draft a substantive reply. Correct output is a flag to a human "
                "with no attempt at an answer.",
    },
    {
        "id": "EM020", "scheme_id": "SCH001", "lot": 47,
        "from": "lot47@example.invalid",
        "subject": "Fire door propped open",
        "body": "The fire door on level 6 has been propped open with a fire "
                "extinguisher for at least a week. Isn't that illegal?",
        "label": {"category": "rules_breach_complaint", "secondary_category": None,
                  "urgency": "urgent", "requires_committee_decision": False},
        "note": "Rule 1.2. Safety risk to persons, so urgent under the written "
                "definition despite the category being a complaint.",
    },
    {
        "id": "EM021", "scheme_id": "SCH001", "lot": 103,
        "from": "agent@example.invalid",
        "subject": "Following up - certificate for Lot 103",
        "body": "Following up on my request from last Tuesday. We still haven't "
                "received the owners corporation certificate and the contract is due "
                "with the purchaser's solicitor Thursday. Please advise urgently.",
        "label": {"category": "oc_certificate_request", "secondary_category": None,
                  "urgency": "urgent", "requires_committee_decision": False},
               "note": "Escalated follow up with a named Thursday deadline blocking a "
                "settlement. Stays urgent, now supported by the deadline clause added "
                "to the urgent definition rather than by instinct.",
    },
    {
        "id": "EM022", "scheme_id": "SCH002", "lot": 31,
        "from": "lot31@example.invalid",
        "subject": "No hot water",
        "body": "We've had no hot water since yesterday morning. The unit is the one "
                "in the laundry cupboard inside our apartment. Who do I call?",
        "label": {"category": "maintenance_private_lot", "secondary_category": None,
                 "urgency":"priority", "requires_committee_decision": False},
                "note": "Hot water unit inside the lot is the owner's, so the category is "
                "private lot. Relabelled routine to priority: a week without hot "
                "water is a significant consequence, and responsibility affects "
                "category, not urgency.",
    },
    {
        "id": "EM023", "scheme_id": "SCH003", "lot": 4,
        "from": "lot4@example.invalid",
        "subject": "New puppy",
        "body": "We've just got a puppy, a cavoodle called Biscuit. Someone said we "
                "have to register her with the owners corporation. Do we?",
        "label": {"category": "approval_request", "secondary_category": None,
                  "urgency": "routine", "requires_committee_decision": False},
        "note": "TRICKY. Rule 5.1 requires NOTIFICATION within 14 days, not approval. "
                "Correct reply distinguishes the two. Tests whether the model reads "
                "the rule or assumes pets need permission.",
    },
    {
        "id": "EM024", "scheme_id": "SCH001", "lot": 47,
        "from": "lot47@example.invalid",
        "subject": "ABSOLUTELY FED UP",
        "body": "This is the fourth email and nobody has done anything. You people "
                "are useless and I'm going to make sure everyone in this building "
                "knows it. I'll be at your office tomorrow and you won't like it.",
        "label": {"category": "escalate_immediately", "secondary_category": None,
                  "urgency": "urgent", "requires_committee_decision": False},
        "note": "Implied threat toward staff. The agent must not attempt to placate "
                "or negotiate. Flag to a human, no draft.",
    },
]


def main():
    os.makedirs(os.path.join("data", "emails"), exist_ok=True)

    payload = {
        "categories": CATEGORIES,
        "urgency_definitions": URGENCY_DEFINITIONS,
        "emails": EMAILS,
    }
    path = os.path.join("data", "emails", "emails.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("wrote:", path, "-", len(EMAILS), "emails\n")

    counts = {}
    for e in EMAILS:
        counts[e["label"]["category"]] = counts.get(e["label"]["category"], 0) + 1
    print("primary category distribution:")
    for c in CATEGORIES:
        print("  %-30s %d" % (c, counts.get(c, 0)))

    sec = sum(1 for e in EMAILS if e["label"]["secondary_category"])
    urg = {}
    for e in EMAILS:
        urg[e["label"]["urgency"]] = urg.get(e["label"]["urgency"], 0) + 1
    needs = sum(1 for e in EMAILS if e["label"]["requires_committee_decision"])

    print("\nwith a secondary category:        ", sec, "of", len(EMAILS))
    print("urgency:                          ", urg)
    print("requires_committee_decision true: ", needs, "of", len(EMAILS))
       print("\nREMINDER: labels are drafts. EM001, EM005, EM021 and EM022 were "
          "revised after the first agent runs - see docs/failure_analysis.md.")
if __name__ == "__main__":
    main()