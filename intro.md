# Mechnari.ai — Plain-Language Introduction

## What it does

When engineers design a new part for a tractor (a hose, a bracket, a valve,
whatever), they're required to fill out a document called a **DFMEA** —
basically a checklist of "how could this part fail, how bad would it be,
and how would we catch it before it hurts someone." Right now that
checklist gets filled out by a room of engineers relying on memory. If
nobody in the room happens to remember that a similar hose cracked in the
field three years ago, that failure mode just doesn't make it onto the
list.

**Mechnari's job is to make sure that never happens.** It reads through
the company's own history — old warranty claims, old failure reports —
and cross-checks: "this new part is basically a cousin of five parts we've
built before, and those parts had these known failure modes. Which of
those did the engineer actually write down?" Whatever's missing, it
flags, with the exact warranty report number attached as proof.

It also fixes the scoring. DFMEAs rate each risk on three 1–10 scores (how
bad, how often, how detectable) and multiply them into one number. The
problem: those three scores are usually just someone's gut feeling.
Mechnari calculates the "how often" score from actual claims data instead
of guessing, and it checks whether the DFMEA's math is even using the
right formula (the official standard changed the formula in 2019 and a
lot of tools never caught up).

## How it works, simply

1. **You describe a part** — name, material, what it does. Doesn't need
   to exist yet.
2. **It finds similar parts** the company has already built, using the
   words in the description.
3. **It pulls up what went wrong** with those similar parts historically
   — real incident reports, not guesses.
4. **It compares that list against what the current DFMEA actually
   covers**, and shows you the gap.
5. **An AI writes up the explanation in plain English**, but — and this
   is the important part — the AI never touches the actual risk numbers.
   Those come from straight arithmetic on the historical data. The AI
   explains; it doesn't decide.

This was tested by hiding half the company's failure history and asking:
"if we'd only had the older half, would this have caught the failures
that showed up later?" It caught 98% of the ones that were catchable,
versus 72% for what a manual review actually caught historically.

## Who it's for

- **Design/reliability engineers** at a manufacturer (tractors, in this
  build's example, but the idea works for any physical product) who
  currently sit in multi-week DFMEA workshops — it gives them a first
  draft grounded in real history instead of a blank page.
- **Quality engineers** who have to defend these documents in an audit —
  every flagged risk comes with a citation, which is exactly what an
  auditor wants to see.
- **A company that has been building similar products for years** and
  has a pile of warranty/failure data sitting unused — that data is the
  entire value; a brand-new company with no history wouldn't get much
  benefit yet.

Basically: anyone whose job is "make sure we don't repeat a mistake we
already know about," but who currently has no good way to check that
against the company's own past.
