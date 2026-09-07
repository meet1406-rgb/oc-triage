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
## Cost

$4.92 and 871.7K tokens across development. That covered roughly
250 email triages: 2 classifier runs over 24 emails, ~9 agent
batch runs, and individual email testing.

Approximately $0.02 per email triaged.

Agent runs cost about 3x the classifier per email, because each
email makes 2-4 tool-calling round trips and carries a long
system prompt through every one of them.

Prompt caching is available and not enabled. The system prompt is
identical on every call and is the largest part of each request,
so caching it would cut cost noticeably. Not done - noted as an
obvious optimisation rather than an implemented one.
## Not built: statutory retrieval

The agent has no tool that returns legislation, so it is
forbidden from citing sections and the grounding check flags any
statutory reference as ungrounded.

A search_legislation tool over the Owners Corporations Act 2006
would let it answer questions like EM053 (voting entitlement when
in arrears), which are governed by statute rather than scheme
rules.

Deliberately not built. Legal text is substantially harder to
retrieve correctly than 23 short scheme rules, a wrong section is
worse than no section, and the Act was under review in 2024-25 so
currency would need verifying. Out of scope for a triage agent.
## Variance at n=40 - 3 identical runs

              Run1  Run2  Run3   Range
category       92%   90%   90%   90-92
urgency        90%   90%   82%   82-90
authority      98%   92%   95%   92-98
grounding     100%  100%  100%   100

Category variance narrowed from 8 points at n=24 to 2 at n=40.
Authority narrowed from 9 to 6. Urgency WIDENED, from a flat 75%
to an 8 point range, which suggests the earlier flatness was not
stability.

Consistent failures (all three runs):
  category:  EM020, EM023, EM058
  urgency:   EM016, EM044
  authority: EM044

EM044 (direct debit request) fails on both urgency and authority
in every run. Most consistent failure in the set.

Run 3 took 2630s vs 608s and 667s for identical work. API
latency, not code.
## EM044 fix - direct debit

EM044 failed both urgency and authority in all three baseline
runs. The agent looked up the owner, found $620 in arrears, and
let that single fact drive both: urgency to priority "given the
financial consequence", authority to true by reframing a direct
debit as a "payment arrangement" that "commits the owners
corporation financially".

It also worked the arrears into the draft, so an owner asking to
pay more conveniently received a debt-chasing line back.

Added two rules: changing how someone pays is not a payment
arrangement; an arrears balance is a fact about the account, not
the request, and must not be raised unprompted or affect urgency.

Result: EM044 clears both metrics. Authority 98%, top of the
92-98% range.

Side effect on EM040: the agent no longer discloses arrears to
the solicitor. That resolves an open question I had flagged but
had not decided. Accepting it, but noting it was a side effect
rather than a decision.

Still unresolved: the agent calls get_lot_owner on both emails
even when it does not use the result. The instruction changed
what is said, not what is fetched. In a system with real owner
data that is still an unnecessary access. Probably needs a code
fix - restricting which categories can reach the tool - rather
than a prompt one.

This is the third fix in the same family. The model over-applies
caution instructions to adjacent-sounding cases: EM009 (a diary
lookup read as a decision), EM014 (explaining a committee does
not exist read as deciding to form one), EM044 (a direct debit
read as a payment arrangement).
## Three consistent category failures - diagnosed

EM058: genuine model error. "Certificate of currency" (insurance
proof) was classified as oc_certificate_request (sale disclosure).
Two different documents sharing the word "certificate". Same
vocabulary-collision failure the keyword search had with
"floorboards". Fixed by naming the distinction in the prompt.

EM020 (fire door propped open): not a misclassification. The
agent classifies it escalate_immediately and produces no draft,
reasoning that an active life-safety risk needs a human today.
I defined escalate_immediately as threats, harassment, abuse and
legal advice - content the agent must not compose. The agent has
extended it to "a human must act now". Both readings are
defensible. The category is doing two jobs. Left unresolved and
documented rather than forced.

EM023 (new puppy): the draft is entirely correct - cites 5.1,
states explicitly that this is notification not approval, adds
5.2. It then labels the email rules_breach_complaint, though
nobody complained. The taxonomy has no home for "owner asks what
the rules say". Considered adding rules_enquiry; did not, because
the taxonomy has already been split once and every split creates
new edges.

Note: two of three consistent failures were taxonomy problems,
not model errors. Persistent misclassification is worth reading
before it is worth fixing.
## EM058 - two failed prompt fixes

"Certificate of currency" (insurance proof) is consistently
classified oc_certificate_request instead of insurance. Failed
five baseline runs.

Attempt 1: explained that a certificate of currency is proof of
insurance and an OC certificate is a sale disclosure document.
No change.

Attempt 2: named the category explicitly - "is category
insurance, never oc_certificate_request, even though the word
certificate appears". No change. The model now adds insurance as
SECONDARY, so it recognises the insurance dimension and still
chooses the other as primary.

The draft itself is correct throughout: it explains the building
versus contents distinction accurately. This is not a knowledge
gap. The label appears driven by the word "certificate" rather
than by reasoning the model demonstrably performed.

Stopped after two attempts rather than tuning further.

Pattern across three fixes: the two that worked (EM009/EM014
authority, EM044 direct debit) both SUPPLIED a distinction the
model had not considered. This one tried to SUPPRESS an
association it already had, and did not work. Two data points,
not proof, but a useful hypothesis: prompts add reasoning more
reliably than they remove it.

Options not taken: rename the category (oc_certificate_request ->
sale_disclosure_request) to remove the collision, or handle it in
code with a keyword pre-check. Both would work. Neither was tried
because the finding is more useful than the fix.