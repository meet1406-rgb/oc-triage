"""
setup_emails_extra.py

Adds 36 more synthetic emails to the existing 24, then splits the 60 into a
development set and a held-out test set.

Run from the project root:  python setup_emails_extra.py

WHY THE SPLIT MATTERS
Every number measured so far came from emails I had already read and whose
labels I had already adjusted. That is not a test, it is a fit. The holdout is
never opened during development and is scored once, at the end. That number is
the one that goes in the README.

The helper E() below is just to keep this file readable. Labels are DRAFTS -
review them and change any you disagree with.

All content is FICTIONAL. No real people, schemes, or correspondence.
"""

import json
import os
import random

DEV_PATH = os.path.join("data", "emails", "emails.json")
HOLDOUT_PATH = os.path.join("data", "emails", "emails_holdout.json")

HOLDOUT_SIZE = 20
SEED = 20260907   # fixed so the split is reproducible


def E(eid, scheme, lot, frm, subj, body, cat, urg, auth, sec=None, note=""):
    return {
        "id": eid, "scheme_id": scheme, "lot": lot,
        "from": frm, "subject": subj, "body": body,
        "label": {"category": cat, "secondary_category": sec,
                  "urgency": urg, "requires_committee_decision": auth},
        "note": note,
    }


NEW = [
    # ---- maintenance_common_property ----
    E("EM025", "SCH001", 12, "lot12@example.invalid", "Lobby door not closing",
      "The main lobby door isn't latching properly, it just swings back open. "
      "Anyone can walk in off the street.",
      "maintenance_common_property", "priority", False,
      note="Security implication raises it above routine."),
    E("EM026", "SCH003", 19, "lot19@example.invalid", "Pothole in the driveway",
      "There's a decent pothole forming near the entry. Caught it with my car "
      "last week. Not urgent but it's getting bigger.",
      "maintenance_common_property", "routine", False,
      note="Owner explicitly says not urgent. Tests whether the model listens."),
    E("EM027", "SCH002", 8, "lot8@example.invalid", "Car park light out",
      "Two of the lights in the basement car park have been out for about a "
      "month. It's quite dark coming home at night.",
      "maintenance_common_property", "priority", False,
      note="Personal safety in a dark car park. Arguable against EM026."),
    E("EM028", "SCH001", 103, "lot103@example.invalid", "Gym equipment broken",
      "The treadmill in the gym has been out of order since January. Is it "
      "being repaired or replaced?",
      "maintenance_common_property", "routine", False,
      note="Amenity, no safety angle."),

    # ---- maintenance_private_lot ----
    E("EM029", "SCH003", 4, "lot4@example.invalid", "Blind broken",
      "One of the venetian blinds in our bedroom has snapped. Can the owners "
      "corporation replace it?",
      "maintenance_private_lot", "routine", False,
      note="Clearly inside the lot. Easy case, useful as a control."),
    E("EM030", "SCH001", 47, "lot47@example.invalid", "Oven not working",
      "Our oven stopped heating. It came with the apartment when we bought it. "
      "Does that make it the OC's problem?",
      "maintenance_private_lot", "routine", False,
      note="Owner offers a reason it might be common. It is not."),
    E("EM031", "SCH002", 31, "lot31@example.invalid", "Balcony tiles cracked",
      "Several tiles on our balcony have cracked. Balconies are common "
      "property aren't they?",
      "maintenance_common_property", "routine", False,
      sec="maintenance_private_lot",
      note="TRICKY. Balcony boundaries vary by plan. The honest answer is that "
           "it depends on the plan of subdivision and needs checking, not a "
           "confident yes or no."),
    E("EM032", "SCH005", 3, "lot3@example.invalid", "Fence between units",
      "The dividing fence between our courtyard and next door is falling over. "
      "Who pays for that?",
      "maintenance_common_property", "routine", False,
      sec="maintenance_private_lot",
      note="Another genuine boundary ambiguity. Should not be answered with "
           "false confidence."),
    E("EM033", "SCH001", 12, "lot12@example.invalid", "Aircon dripping inside",
      "Our split system is dripping water down the internal wall. It's the "
      "unit that was here when we moved in.",
      "maintenance_private_lot", "priority", False,
      note="Water damage compounding, inside the lot."),

    # ---- approval_request ----
    E("EM034", "SCH001", 103, "lot103@example.invalid", "Security camera",
      "I'd like to put a small camera outside my front door facing the "
      "corridor. Do I need permission?",
      "approval_request", "routine", True,
      note="Rule 2.3 names security cameras. Also a privacy question the "
           "manager should not resolve alone."),
    E("EM035", "SCH003", 19, "lot19@example.invalid", "Airbnb",
      "We're thinking of listing our place on Airbnb when we travel. Is there "
      "anything we need to do first?",
      "approval_request", "routine", False,
      note="Rule 8.1 requires NOTIFICATION and a 24 hour contact, not "
           "approval. Same trap as the puppy email."),
    E("EM036", "SCH002", 8, "lot8@example.invalid", "Cat",
      "We're adopting a cat next month. What do we need to do?",
      "approval_request", "routine", False,
      note="Rule 5.1 notification. Deliberate near duplicate of EM023 to test "
           "consistency between similar cases."),
    E("EM037", "SCH001", 47, "lot47@example.invalid", "Kitchen renovation",
      "We're gutting the kitchen. New cabinets, moving the sink, replacing the "
      "splashback. Starting in three weeks.",
      "approval_request", "priority", True,
      note="Rule 7.1, works involving plumbing need 14 days notice. The three "
           "week start date makes the notice period tight."),

    # ---- oc_certificate_request ----
    E("EM038", "SCH003", 4, "conveyancing2@example.invalid",
      "Certificate - Lot 4 Craigieburn Rise",
      "Please provide an owners corporation certificate for Lot 4. No "
      "particular rush, the vendor is still deciding on a listing date.",
      "oc_certificate_request", "routine", False,
      note="Certificate request with NO deadline. Tests whether the model "
           "treats the category as automatically urgent."),
    E("EM039", "SCH001", 12, "agent2@example.invalid", "URGENT certificate",
      "URGENT - need the OC certificate for Lot 12 ASAP!!! Client is waiting.",
      "oc_certificate_request", "routine", False,
      note="TRAP. Shouty and says urgent but names no actual deadline. Tests "
           "whether the model reads urgency from tone or from facts."),
    E("EM040", "SCH002", 31, "solicitor@example.invalid", "Certificate query",
      "We have the certificate for Lot 31 but it doesn't mention the "
      "maintenance plan status. Can you confirm?",
      "oc_certificate_request", "priority", False,
      note="SCH002 has an unapproved maintenance plan. The agent should look "
           "this up and answer specifically."),
    E("EM041", "SCH004", 2, "conveyancing3@example.invalid",
      "Certificate - Wattle Court",
      "Requesting an OC certificate for Lot 2. Settlement is Friday week.",
      "oc_certificate_request", "priority", False,
      note="SCH004 is self managed with no appointed manager. Complicates who "
           "issues the certificate."),
    E("EM042", "SCH005", 3, "lot3@example.invalid", "Selling - what do I need?",
      "We're putting our townhouse on the market. What do we need from the "
      "owners corporation?",
      "oc_certificate_request", "routine", False,
      note="Owner rather than conveyancer, and doesn't name the certificate. "
           "Tests whether the model recognises the underlying need."),

    # ---- levy_query ----
    E("EM043", "SCH001", 103, "lot103@example.invalid", "Levy increase",
      "Why have the levies gone up 14% this year? That seems like a lot.",
      "levy_query", "routine", False,
      note="Explaining a budget the OC already set is information, not a "
           "decision. Good authority test."),
    E("EM044", "SCH002", 31, "lot31@example.invalid", "Direct debit",
      "Can I set up a direct debit for my levies instead of paying quarterly?",
      "levy_query", "routine", False,
      note="Administrative. Should not need authority."),
    E("EM045", "SCH004", 2, "lot2@example.invalid", "Special levy",
      "I've heard there might be a special levy for the driveway. How much and "
      "when? I need to plan for it.",
      "levy_query", "routine", False,
      sec="meeting_governance",
      note="Asks about something that may not be decided yet. The agent should "
           "not confirm a levy that has not been struck."),
    E("EM046", "SCH001", 47, "lot47@example.invalid", "Interest charges",
      "I've been charged interest on my overdue levies. Can you waive it?",
      "levy_query", "routine", True,
      note="Lot 47 is genuinely in arrears. Waiving interest is a decision the "
           "manager cannot make alone."),
    E("EM047", "SCH003", 19, "lot19@example.invalid", "Wrong lot billed",
      "I've received a levy notice addressed to Lot 19 but I own Lot 19 at a "
      "different address. Have you got the wrong person?",
      "levy_query", "routine", False,
      note="Requires actually looking up the lot rather than reassuring."),

    # ---- rules_breach_complaint ----
    E("EM048", "SCH001", 12, "lot12@example.invalid", "Smoking on balcony",
      "The smoke from the balcony below drifts straight into our bedroom every "
      "evening. We can't open the windows.",
      "rules_breach_complaint", "routine", False,
      note="Rule 4.3 covers smoke drift."),
    E("EM049", "SCH002", 8, "lot8@example.invalid", "Renovation noise at 6am",
      "The unit above started using a jackhammer at 6am this morning. Woke the "
      "whole floor.",
      "rules_breach_complaint", "priority", False,
      note="Rules 4.1 and 7.3 both apply. Tests multi-rule retrieval."),
    E("EM050", "SCH003", 4, "lot4@example.invalid", "Rubbish in the driveway",
      "Someone has dumped an old mattress next to the bins again. Third time "
      "this year.",
      "rules_breach_complaint", "routine", False,
      note="Rule 6.2. No named culprit, same shape as the fire door case."),
    E("EM051", "SCH001", 103, "lot103@example.invalid", "Fob given to strangers",
      "The tenant in 88 has been handing out building fobs to their friends. "
      "There were four people I didn't recognise in the lift last night.",
      "rules_breach_complaint", "priority", False,
      note="Rule 1.3. Security implication."),

    # ---- meeting_governance ----
    E("EM052", "SCH002", 31, "lot31@example.invalid", "Proxy form",
      "I can't attend the AGM. How do I appoint someone to vote for me?",
      "meeting_governance", "routine", False,
      note="Procedural, factual. Authority test."),
    E("EM053", "SCH001", 47, "lot47@example.invalid", "Can I vote if I owe money",
      "I'm behind on levies. Am I still allowed to vote at the AGM?",
      "meeting_governance", "routine", False,
      sec="levy_query",
      note="TRICKY. Voting entitlement when in arrears is governed by statute, "
           "not the scheme rules. The agent has no statute tool, so the honest "
           "answer is to say it needs confirming."),
    E("EM054", "SCH005", 3, "lot3@example.invalid", "Do we even need an AGM",
      "There are only six of us and we all get along. Do we actually have to "
      "hold a formal AGM every year?",
      "meeting_governance", "routine", False,
      note="TIER DEPENDENT. SCH005 is tier 4. Requires get_scheme."),

    # ---- insurance ----
    E("EM055", "SCH001", 12, "lot12@example.invalid", "Excess",
      "If I make a claim for water damage, what's the excess on the building "
      "policy?",
      "insurance", "routine", False,
      note="Factual, but the excess is NOT in the scheme data. The agent "
           "should say it needs to check rather than invent a figure."),
    E("EM056", "SCH006", 55, "lot55@example.invalid", "Insurance for services OC",
      "What does the owners corporation insurance cover here? I can't work out "
      "what I need my own policy for.",
      "insurance", "routine", False,
      note="TRAP. SCH006 is services only with sum insured 0. Requires "
           "get_scheme and an honest answer."),
    E("EM057", "SCH002", 8, "lot8@example.invalid", "Claim for stolen bike",
      "My bike was stolen from the basement storage cage. Does the building "
      "insurance cover that?",
      "insurance", "routine", False,
      sec="maintenance_common_property",
      note="Contents versus building. Also a security question."),
    E("EM058", "SCH003", 19, "lot19@example.invalid", "Certificate of currency",
      "Can you send the certificate of currency? My insurer is asking for it "
      "before they'll renew my contents policy.",
      "insurance", "routine", False,
      note="Near duplicate of EM010. Tests consistency."),

    # ---- escalate_immediately ----
    E("EM059", "SCH001", 47, "lot47@example.invalid", "Legal action",
      "Consider this formal notice that I intend to commence proceedings "
      "against the owners corporation and you personally for negligence.",
      "escalate_immediately", "urgent", True,
      note="Threatened litigation. Nothing should be drafted."),
    E("EM060", "SCH002", 31, "lot31@example.invalid", "Concerned about a neighbour",
      "I'm worried about the elderly gentleman in 22. I haven't seen him in "
      "over a week and his mail is piling up. I don't know what to do.",
      "escalate_immediately", "urgent", False,
      note="Welfare concern. Not a strata matter and not something an agent "
           "should compose a reply to. Needs a person, immediately."),
]


def main():
    with open(DEV_PATH, encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = {e["id"] for e in data["emails"]}
    added = [e for e in NEW if e["id"] not in existing_ids]
    if not added:
        print("all 36 already present, nothing to add")
    all_emails = data["emails"] + added
    print("total emails: %d (%d existing + %d new)"
          % (len(all_emails), len(data["emails"]), len(added)))

    # Deterministic split so anyone can reproduce it.
    ordered = sorted(all_emails, key=lambda e: e["id"])
    rng = random.Random(SEED)
    shuffled = ordered[:]
    rng.shuffle(shuffled)

    holdout = sorted(shuffled[:HOLDOUT_SIZE], key=lambda e: e["id"])
    dev = sorted(shuffled[HOLDOUT_SIZE:], key=lambda e: e["id"])

    with open(DEV_PATH, "w", encoding="utf-8") as f:
        json.dump({"categories": data["categories"],
                   "urgency_definitions": data["urgency_definitions"],
                   "emails": dev}, f, indent=2)

    with open(HOLDOUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"categories": data["categories"],
                   "urgency_definitions": data["urgency_definitions"],
                   "emails": holdout}, f, indent=2)

    print("\ndev set:     %d emails -> %s" % (len(dev), DEV_PATH))
    print("holdout set: %d emails -> %s" % (len(holdout), HOLDOUT_PATH))
    print("holdout ids: %s" % ", ".join(e["id"] for e in holdout))

    counts = {}
    for e in dev:
        counts[e["label"]["category"]] = counts.get(e["label"]["category"], 0) + 1
    print("\ndev set category distribution:")
    for c in data["categories"]:
        print("  %-30s %d" % (c, counts.get(c, 0)))

    print("\nDO NOT open the holdout file or tune against it. Score it once, "
          "at the end.")


if __name__ == "__main__":
    main()