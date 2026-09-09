# Overview — what Mechnari.ai is

## The instrument

A **Design FMEA** (Failure Mode and Effects Analysis) is the mandatory
instrument for catching how a part fails before it is built. For each way a
part can fail it records the effect, how bad that effect is (**Severity**),
how likely the cause is (**Occurrence**), whether design verification would
catch it (**Detection**), and what will be done about it. It is an audited
document: IATF 16949 expects one, and an auditor expects it to be defensible.

## The failure mode of the instrument itself

In practice a DFMEA is filled in by a room of engineers relying on memory.
If nobody present happens to remember that a similar hose cracked in the
field three years ago, that failure mode simply does not make it onto the
list.

This is not a hypothetical scale problem:

- A DFMEA for one 10–14 part package assembly takes about **one calendar
  week**, run as a cross-functional workshop — design, quality and
  manufacturing in the room together.
- A tractor has **1,000+ parts**. That is on the order of **70–100 such
  workshops per program**, run by different people at different times.
- Nothing keeps them consistent with each other, or with what the last
  program already learned.

The company already owns the answer. Warranty claims, 8D reports and field
failure records describe exactly what went wrong on the parts it has already
built. That record is not in the room during the workshop.

## What Mechnari.ai does

It reads the company's own failure history and cross-checks it against the
DFMEA on file:

> *This new part is a cousin of five parts we have built before. Those parts
> had these known failure modes. Which of them did the engineer actually
> write down?*

Whatever is missing gets flagged, with the warranty record identifiers
attached as proof. It also derives Occurrence from the measured claim rate
instead of a workshop opinion, and ranks by **Action Priority** — the
AIAG-VDA lookup that replaced RPN in 2019 — instead of a multiplication that
misranks safety-relevant risk.

## The claim it makes, and the one it refuses to make

**The claim is not speed.** Speed is unverifiable, and filling in the table
is the part engineers least want automated.

The defensible claim is the inverse:

> *You have already seen this failure, and this DFMEA did not check for it.*

That is checkable against an 8D number, and it survives an audit.

## The rule the whole system rests on

**Agents read findings and write English. Deterministic engines own every
number.**

No agent holds a tool that could write a Severity, Occurrence, Detection
score or Action Priority — [`test_mechnari_tools.py`](../test_mechnari_tools.py)
enforces that rather than the documentation asserting it, and the frontend
half of the same guarantee is enforced in
[`CopilotActions.tsx`](../web/src/components/CopilotActions.tsx) by simply
not defining such a tool. An action the agent has no tool for is an action
it cannot take, whatever it is asked.

Three things the copilot must refuse, and has no tool for:

1. **Changing a Severity, Occurrence or Detection score.** Severity comes
   from the organisation's effect registry; Occurrence is counted from
   warranty claims. Editing either turns evidence back into opinion. The
   engineer *can* override Occurrence in the review — with a written reason
   that gets recorded.
2. **Marking an action complete.**
3. **Naming who owns an action.**

The last two are claims about the real world that only a person can make.

## What it is not

- Not a document generator that writes plausible FMEA prose. Every row it
  proposes traces to a catalogue entry and warranty records.
- Not an autonomous approver. It proposes; an engineer accepts, edits or
  declines, and a Quality engineer reviews.
- Not a replacement for the workshop. It replaces the blank page the
  workshop starts from.
