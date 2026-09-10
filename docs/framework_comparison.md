# I built the same agent twice

V1 is a hand written tool calling loop against the Anthropic SDK.
V2 is the same agent as a LangGraph graph.

Same model. Same system prompt, imported from the V1 module so the two cannot
drift apart. Same three tools. Same output schema, scored by the same
`batch.py`. The only variable is the framework.

This document is the result.

---

## The headline

The framework changed nothing measurable.

| | V1 (5 runs, n=40) | V2 run 1 (n=40) | V2 run 2 (n=35) |
|---|---|---|---|
| Category accuracy | 88-92% | 92% | 91% |
| Urgency accuracy | 82-90% | 88% | 86% |
| Authority accuracy | 92-98% | 98% | 97% |
| Citation validity | 100% | 100% | 100% |
| Grounding | 100% | 100% | 100% |
| Mean tool calls | 1.9-2.0 | 1.9 | 2.0 |

Every V2 figure sits inside the V1 range.

More telling than the percentages: **the failures are the same emails.**
V1's three persistent category misses are EM020, EM023 and EM058. V2 missed
exactly those three, in both runs.

That is what you would expect. The model, the prompt and the tools are
identical, and none of them live in the loop. The loop was never where the
accuracy came from, so replacing it could not move the accuracy.

V2 run 2 hit five network errors and scored 35 emails rather than 40, so its
percentages are over a smaller set. Reported as measured rather than dropped.

---

## What the framework actually replaced

Three concrete things, all in V1's `oc/agent.py`:

**About 60 lines of hand written JSON tool schemas.** In V2 the `@tool`
decorator generates them from the function signature and docstring. The
docstring becomes the description the model sees, so the information did not
disappear - it moved somewhere more natural to maintain.

**The tool_use / tool_result plumbing.** V1 walks `response.content`, finds
`tool_use` blocks, dispatches each one, and assembles `tool_result` blocks
with matching `tool_use_id`. V2 uses the prebuilt `ToolNode`. This was the
fiddliest part of V1 to get right and it is now one line.

**The loop itself.** `while turn in range(MAX_TURNS)` with a
`stop_reason == "tool_use"` check becomes a conditional edge between two
nodes.

Net effect on line count is roughly a wash. V2 deletes the schemas and the
plumbing, and adds imports, a state definition and graph construction.

---

## What the framework did not replace

The approval queue. V1 hand rolls it: drafts written to `data/queue.json` with
a status field, a separate CLI to review them.

LangGraph has `interrupt()` and a checkpointer, which is the same thing with
persistence and resumability built in. A graph can pause at a review node,
persist its entire state to SQLite, and resume days later when a human
responds.

That is not used in this comparison, deliberately - adding it would have
changed more than the framework and invalidated the numbers above.

**This is where I would argue the framework earns its place.** Not in the
agent loop, where it is a stylistic preference, but in the human in the loop
step, where it replaces something I had to build myself and adds capability I
had not built.

---

## Something the comparison surfaced by accident

V2 run 2 hit five `Connection error` failures. Neither version retries.

In V1, adding retry means writing it into the loop by hand. LangGraph lets you
attach a retry policy to a node. That is a real difference, it is exactly the
kind of thing that matters in production, and I did not use it.

Noting it as an observed gap rather than claiming it as a benefit.

---

## What I would tell someone choosing between them

Start with the loop. It is about forty lines of real logic and writing it
teaches you what the abstraction is doing. If you reach for the framework
first, tool calling stays magic.

Adopt the framework when you hit something it solves that you would otherwise
build: durable state across a human pause, retry policies, coordinating
several agents. Not for accuracy - it will not touch your accuracy.

The measurement that made this legible was not the port. It was running the
same evaluation five times on V1 first, to find out that authority accuracy
moved 9 points with no code changes at all. Without that noise floor I would
have read V2's 98% as an improvement over V1's 92%. It is not. It is the same
system twice.

---

## Reproducing