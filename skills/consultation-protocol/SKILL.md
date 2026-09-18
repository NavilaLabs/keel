---
name: consultation-protocol
description: How a consultation with the developer is prepared, presented and recorded in state.json. Use at every consultation point of the ticket workflow - steps 2, 4, 5, 6, 7 and any step reached by a jump.
---

# Consultation protocol

A consultation is the point where the developer checks that everything was
understood and defined correctly. It is not a status update and not a request
for approval to continue.

## Before asking

Write the consultation to `consultations[]` in `state.json` with
`status: "open"` and set the block's status to `awaiting_consultation`. The
`consultation-gate` hook blocks writes while a consultation is open, so
recording it first is what makes the pause real rather than a promise.

## What to present

The developer needs a coherent overview, not a transcript of how you got
there. Present:

1. **The result of the step** - the goals, the blocks, the architecture, the
   contracts. In full, not summarised to the point of being unreviewable
2. **What you decided and why** - especially where you chose between options
3. **What you are unsure about** - name it explicitly rather than presenting
   a guess with the same confidence as a conclusion
4. **What changes if this is wrong** - which later steps depend on it

For step 7 specifically, present the LikeC4 diff and the stub signatures
together. Those two are what everything after step 7 is implemented against,
and this consultation is the last point where changing them is cheap.

## How to ask

Ask one question where one will do. Several questions are fine when they are
genuinely separate decisions; they are not fine as a way of offloading a
judgement you should have made yourself.

Offer options where real options exist, and say which you would pick and why.
"Which do you prefer, A or B?" without a recommendation makes the developer
do work you already did.

Never bundle a consultation with the next step's work. Ask, stop, wait.

## After the answer

Record the answer in the consultation object, set `status: "answered"` and
`answered_at`. Restore the block's status. Then continue.

If the answer changes something already decided, that is a jump: log it in
`jump_log[]` and append a line to `knowledge.md`. Do not silently absorb a
correction into the current step.

## Jumps reactivate consultations

A jump back to a step reactivates that step's own consultation rule,
regardless of which zone the jump came from. Arriving at step 7 from step 8
means step 7's consultation, even though step 8 itself has none.

## Where there is no consultation

Steps 3, 8, 9, 10, 11 and 12 have no scheduled consultation. That is
deliberate: by step 8 the guardrails are set, and interrupting there would
cost flow for nothing.

It does not mean these steps proceed silently past a problem. When step 8
hits something that needs a decision, the answer is the jump back to 7 -
which carries its consultation with it.
