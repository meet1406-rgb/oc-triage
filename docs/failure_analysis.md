# Failure analysis

## Urgency calibration experiment

Before (zero-shot):         67% urgency, 96% category
After (3 examples + rules): 83% urgency, 100% category

Fixed:      EM002, EM005, EM010, EM015, EM016, EM020
Broke:      EM011 - regression. The "no stated deadline is routine"
            guidance wrongly downgraded an insurance cover question.
Unresolved: EM001, EM021, EM022

Caveat: the guidance was written against failures observed on this
same set, so the improvement is partly fitted to the test. A clean
replication needs held-out emails.

## Retrieval failures (keyword search, step 3)

"can I put floorboards in my apartment"  -> returns nothing.
    Rule 7.2 says "hard floor coverings". No shared word.
"air conditioner on the balcony wall"    -> ranks rule 2.4 above 2.3.
    Rule 2.3 says "air conditioning condensers". Vocabulary mismatch.

Both are classic keyword-search failures. Not fixed yet - kept as the
baseline to measure semantic retrieval against later.

## Open label disputes

EM005 - does a rule complaint need committee authority, or is a
        courtesy reminder within the manager's normal function?
EM020 - does rules_breach_complaint require a named culprit? The fire
        door has none.
EM022 - no hot water for a week. Labelled routine, model said
        priority. The model may be right.
EM021 - the "urgent" definition only covers safety. A hard external
        deadline about to be missed is a different kind of urgent that
        the definitions don't currently allow for.

## Variance study - 3 identical runs, no code changes

              Run1  Run2  Run3   Range
category       92%   96%   96%   92-96
urgency        75%   75%   75%   75 exactly
authority      79%   88%   88%   79-88
citations     100%  100%  100%   100

Consistent misses (real, worth fixing):
  urgency:   EM001, EM021, EM022
  authority: EM005, EM009, EM014

Intermittent (variance, do not chase):
  EM002, EM004, EM010, EM011, EM016, EM020, EM023

Note: urgency scored 75% in all three runs but the failing emails
differed each time. Same error rate, different error locations.

Implication: any single-run improvement under ~9 points on
authority, or ~4 on category, is indistinguishable from noise.

## Classifier vs agent

                  Classifier   Agent (3-run range)
category               100%          92-96%
urgency                 83%             75%
authority             22/24          79-88%
rules cited            never     10 of 24, 100% valid

Adding tool use improved rule handling and degraded calibration.
The agent gets EM023 right on the rule itself (notification, not
approval) but is less consistent on urgency and over-flags
authority. Five authority misses in run 1 were all in the same
direction: the agent said True where the label said False. It
never went the other way.

## Structured output parsing

The model was instructed "reply with JSON only, no markdown". It
complied on all 24 classification calls but broke on the first
agent call, prefixing "I have everything I need. Here is the
triage output:" before a fenced code block.

Fix: stop assuming the reply's shape. Extract from the first {
to the last }.

Takeaway: prompt instructions about output format are a strong
default, not a guarantee. Parse defensively.

## Retrieval, revised after step 5

The step 3 finding above holds when I query the search directly.
It does NOT hold when the agent writes the query.

On EM006 the agent searched "floor coverings floorboards timber" -
it guessed the formal vocabulary and included it alongside the
owner's word. Found rule 7.2 first try. Same on EM007, which
retrieved 2.3 correctly.

Caveat: the tool description explicitly tells the model to retry
using the words the rules would use, so this is partly engineered
rather than emergent.

Implication: keyword retrieval is weaker than semantic retrieval
for direct queries, but the gap narrows when a model writes the
query. Measure properly before assuming embeddings are needed.

## Tool use behaviour

Mean 2.1 to 2.4 tool calls per email across three runs.
10 of 24 emails cited a rule. The agent did not reach for
citations where rules were not relevant.

Two behaviours worth noting:

EM014 (services-only scheme, owner asking to nominate for a
committee that does not exist): the agent searched twice, got
zero results both times, and said so in the draft rather than
filling the gap. It also correctly identified tier 5 from
get_scheme and explained no committee is required. This required
overriding a strong prior about strata committees with a
retrieved fact.

EM019 (harassment plus a request for legal advice): the agent
had two rules retrieved and still cited none, and produced an
empty draft. Declining to answer was the correct behaviour and
it did so without being told about this specific case.

One over-call: on EM006 the agent called get_lot_owner and
learned the owner was $620 in arrears, which was irrelevant to
a floorboards question. It correctly did not mention it, but
the call should not have been made. The tool description says
to call it only when owner details are relevant.

## Open items

- Resolve contested labels: EM001, EM005, EM021, EM022
- Rename requires_committee_decision to requires_authority. For
  SCH006 there is no committee, so the field can only sensibly
  mean "the manager lacks authority", whoever holds it.
- Define when a secondary_category applies. Currently undefined,
  which is why the agent adds them inconsistently.
- Fix authority over-flagging: the system prompt tells the model
  never to grant approval or commit to enforcement, and it
  appears to generalise this into flagging factual questions
  (EM009 is just a diary lookup). Needs a line saying answering
  a factual question is not a decision. Must beat the 9 point
  noise floor to count.
- Expand dataset to 60-100 emails with 30 held out. 24 is too
  small: one email is 4 percent.
  ## Label correction round - result

Corrected EM001, EM005, EM021, EM022 against the written
definitions. Added a deadline clause to the urgent definition.

Authority: 79-88% -> 92%. EM005 resolved as predicted.
Urgency:   75% -> 75%. NO CHANGE.

EM001 and EM021 were fixed. EM017 and EM023 began failing.
EM022 still fails despite being relabelled to what the agent
had said in three prior runs - so it was a variance case, not
a stable position, and my earlier consistent/intermittent
split was wrong on that email.

Urgency has now been 75% (18/24) in five consecutive runs with
a different failing set each time. Fixing two cases caused two
others to fail. I do not have a verified explanation. Reporting
as an open finding rather than tuning further.
## Authority over-flagging fix

Added a "WHAT IS NOT A DECISION" section to the system prompt,
stating that answering a factual question is not a decision and
that explaining something cannot be done is information.

Authority before: 79, 88, 88, 92%   misses EM009, EM014 every run
Authority after:  100%, 96%          EM009 and EM014 gone from both

This is the first change that clearly beat the measured 9 point
noise floor.

Category dipped to 88% on the first post-fix run, then returned
to 92%. Prior range was 92-96%, so the dip was a low draw rather
than a cost of the change.

Urgency moved 75% -> 75% -> 79%. Treating the 79% as noise until
it repeats.
## Citation validity has a blind spot

Q003 (EM003, certificate request) cited zero rules, so it scored
100% clean on citation validity. But the draft asserted:
  - "section 151 of the Owners Corporations Act 2006"
  - "the statutory 10-business-day period under the Act"
  - "the lot is not in arrears, nil outstanding balance"

None of these came from a tool. There is no statute-lookup tool,
and get_lot_owner was never called for lot 8.

The metric only validates rule numbers against the rules file.
Statutory references and factual claims about a lot are not
checked at all. 100% citation validity is therefore a narrower
result than it appears.

Fix would be either a statute tool, or a prompt rule forbidding
statutory citation, plus a check that any factual claim about a
lot was preceded by a get_lot_owner call.
## Prompt-level prohibitions: statute vs lot facts

Q003 (certificate request) originally invented "section 151 of the
Owners Corporations Act 2006", a "statutory 10-business-day period",
and a levy balance for lot 8. It called get_scheme only. Citation
validity scored it 100% clean because it cited no rule numbers.

Added two prohibitions to the system prompt: never cite legislation,
never assert lot facts without calling get_lot_owner.

Re-run: no statute references anywhere. The levy claim was retained
but tool_calls went 1 -> 2, so it was verified rather than invented.

Both prohibitions held. But the evaluation could not distinguish the
grounded draft from the invented one. Both score identically:
rules_cited is empty in each case, and category, urgency and
authority are unchanged. Citation validity only checks rule numbers.

Caught by reading the draft, which does not scale.

Next: add a grounding check to batch.py. If a draft mentions arrears
or a levy balance, assert that get_lot_owner was called for that lot.

Side note on human review: I approved both the invented version and
the verified version with equal confidence. A fluent draft is harder
to review than a rough one. That is a finding about human-in-the-loop
design, not just about the model.
## Grounding check added

Built oc/grounding.py: a keyword scan that checks whether claims
in a draft are backed by an actual tool call.

Five checks: lot facts need get_lot_owner, statute references are
always flagged (no statute tool exists), scheme facts need
get_scheme, cited rule numbers must exist, and rules quoted inline
need search_oc_rules.

Validated against the two real EM003 drafts. The version that
invented "section 151" and a levy balance is flagged with two
issues. The version that called get_lot_owner is clean. Category,
urgency, authority and citation validity scored these two
identically - grounding is the only metric that separates them.

Limitation, stated deliberately: this is a keyword scan, not a
proof. It will flag phrases that assert nothing ("if you fall
into arrears") and can be phrased around. It converts a manual
spot check into something that runs every time, which is the
point.

First full run:  24/24 grounded, 0 ungrounded drafts.