# OC Triage

An AI agent that triages inbound email for Victorian owners corporation
(strata) managers. It classifies the request, resolves the scheme's
regulatory tier, retrieves the relevant scheme rules, drafts a cited reply,
and routes every one to a human for approval.

**It never sends. There is no send function in this codebase.**

| Metric | Result |
|---|---|
| Category accuracy | 90–92% |
| Urgency accuracy | 82–90% |
| Authority accuracy | 92–98% |
| Citation validity | 100% |
| Grounding | 100% |

Built twice: once as a hand-written tool-calling loop, once as a LangGraph
graph. The framework changed nothing measurable — same accuracy, same
failures, same emails. See [docs/framework_comparison.md](docs/framework_comparison.md).

Measured over 5 runs on a 40-email development set. Ranges are the
observed spread across identical runs, not confidence intervals. A
20-email holdout set exists and has not been scored yet.

**All data in this repository is synthetic.** The six owners corporations,
their rules, the owners and the 60 emails are fabricated. No real owners
corporation data was used. Not legal advice.

---

## Why

Australia has over 368,000 strata schemes containing more than 3.19 million
lots. Industry research reports that 69% of strata managers name managing
their workload as their greatest challenge, and 60% work more than 38-hour
weeks.

The bottleneck is not portfolio size. It is inbound volume from people who
are frequently upset, arriving faster than one person can draft considered
replies to.

This agent removes the routine volume so the manager has time for the parts
that need judgement. It does not do strata management.

---

## The design decision that matters

Under the Victorian model the owners corporation makes decisions and the
manager executes them. A manager cannot approve works, authorise
expenditure, or enforce rules on their own initiative.

So an agent that confidently answers those questions is failing at the job,
not doing it well. Human approval is not a safety feature bolted on the
side; it is the shape of the product.

Two consequences run through the whole codebase:

**Statutory obligations are code, not prompt.** The five-tier thresholds
from the *Owners Corporations Act 2006* live in a hardcoded dictionary in
`oc/tiers.py`, sourced from Consumer Affairs Victoria. The model is never
asked to recall legislation. It routes; it does not remember statute.

**The agent has no statute tool, so it is forbidden from citing
legislation.** The grounding check flags any statutory reference as
ungrounded. This was added after the agent invented a section number and a
levy balance in an early draft.

---

## How it works

email → agent loop ──┬─ get_scheme (lot count, tier, obligations)
├─ get_lot_owner (levy balance, arrears)
└─ search_oc_rules (scheme rules, cited by number)
│
▼
draft + classification
│
▼
APPROVAL QUEUE ──→ human: approve / edit / reject


The agent decides which tools to call and when. Mean 1.9–2.4 tool calls per
email.

Tier resolution is the branching logic. The same question gets opposite
correct answers depending on the scheme: a 148-lot tower must have an
approved maintenance plan, a 6-lot townhouse block need not. One test scheme
has 140 lots but is services-only, so it is tier 5 rather than tier 1 —
included specifically to catch naive lot-count logic.

---

## What the evaluation measures

Five metrics. Three compare against labels, which are opinions. Two are
objective.

- **Category** — did it route the email correctly (9 categories)
- **Urgency** — urgent / priority / routine, against written definitions
- **Authority** — did it know when the manager cannot act alone
- **Citation validity** — does every cited rule number exist in the rules file
- **Grounding** — is every factual claim in the draft backed by an actual tool call

Grounding exists because the other four could not tell a good draft from a
bad one. An early draft invented a statute section and asserted a levy
balance it had never looked up, and scored 100% clean on citation validity
because it cited no rule numbers. See `docs/failure_analysis.md`.

**Variance was measured before anything was tuned.** Three identical runs
with no code changes moved authority accuracy 9 points at n=24. That set the
bar any fix had to clear.

---

## What does not work

Kept deliberately, not hidden.

**Urgency calibration is unresolved.** It sat at exactly 75% across eight of
nine runs at n=24, with a different set of six emails failing each time.
Correcting four labels moved it not at all. It now sits at 82–90% on the
larger set, which is a different distribution rather than an improvement.

**One classification failure resisted two prompt fixes.** A "certificate of
currency" (proof of insurance) is consistently classified as an owners
corporation certificate (a sale disclosure document) because both contain
the word "certificate". The draft itself explains the distinction correctly.
The label appears driven by surface features rather than by reasoning the
model demonstrably performed.

**Two other persistent failures turned out to be taxonomy problems, not
model errors.** Documented rather than papered over.

**The agent fetches owner data it does not use.** Instructions changed what
it says, not what it looks up. In a system with real data that is still an
unnecessary access to a financial record.
Full experiment log, including the fixes that failed, is in
[docs/failure_analysis.md](docs/failure_analysis.md).

---

## Cost

$4.92 and 871.7K tokens across all development — roughly 250 email triages.
About **$0.02 per email**.

Prompt caching is available and not enabled. The system prompt is identical
on every call and is the largest part of each request, so caching it would
cut this noticeably.

---

## Not built

**Statutory retrieval.** A tool over the full *Owners Corporations Act 2006*
would let the agent answer questions governed by statute rather than scheme
rules. Deliberately not built: legal text is substantially harder to
retrieve correctly than 23 short rules, a wrong section is worse than no
section, and the Act was under review in 2024–25.

**A feedback loop.** The queue stores original and edited drafts as pairs so
one is possible later. Not built, because with this few reviewed drafts
there is not enough signal to learn from.

---

## Running it

python -m venv .venv
.venv\Scripts\Activate.ps1 # Windows
pip install anthropic python-dotenv


Put your key in `.env`:

ANTHROPIC_API_KEY=sk-ant-...


Then:

python setup_data.py # six schemes, rules, tier logic
python setup_emails.py # 24 labelled emails
python setup_emails_extra.py # 36 more, split dev/holdout

python -m oc.tools # check the tools work, no API calls
python -m oc.agent EM023 # run one email, verbose
python -m oc.batch # run and score everything

python -m oc.queue # build the approval queue
python -m oc.review # review drafts one at a time


---

## Repository

oc/
  tiers.py       tier thresholds and obligations, hardcoded from CAV
  tools.py       get_scheme, get_lot_owner, search_oc_rules
  classify.py    single-call classifier (no tools) - the baseline
  agent.py       V1 - the hand-written agent loop
  graph_agent.py V2 - the same agent as a LangGraph graph
  batch.py       run and score every email
  grounding.py   checks claims against tool calls
  queue.py       builds the approval queue
  review.py      approve / edit / reject CLI
data/
  schemes/       six fictional owners corporations, tiers 1 to 5
  rules/         23 fictional scheme rules
  emails/        40 dev + 20 holdout, labelled
docs/
  failure_analysis.md       every experiment, including the ones that failed
  framework_comparison.md   V1 vs V2, same eval, same dataset
eval/results/               every scored run, timestamped

Sources for the tier framework: Consumer Affairs Victoria, *Tiers of owners
corporations*. Everything else is invented.