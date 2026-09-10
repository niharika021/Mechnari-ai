# Mechnari.ai

*Turning a manufacturer's own warranty history into the evidence a Design FMEA is missing.*

---

## 1. Project description

A **Design FMEA (Failure Mode and Effects Analysis)** is the mandatory engineering document for catching how a part can fail before it is built. For every way a part can fail, it records the effect, how bad that effect is (Severity), how likely the cause is (Occurrence), whether design verification would catch it (Detection), and what will be done about it.

In practice, a DFMEA is filled in by a room of engineers relying on memory. If nobody in the workshop happens to remember that a similar hose cracked in the field three years ago, that failure mode simply never makes it onto the sheet. This isn't a small-scale problem — a single 10–14 part assembly takes about a week of cross-functional workshop time, and a machine with 1,000+ parts requires 70–100 such workshops per program, run by different people at different times, with nothing keeping them consistent with each other or with what the last program already learned.

Meanwhile the company already owns the answer. Warranty claims, 8D reports, and field failure records describe exactly what has gone wrong on the parts it has already built — that record is simply never in the room during the workshop.

**Mechnari.ai** closes that gap. It reads a company's own failure history and cross-checks it against the DFMEA on file, asking: *this new part is a cousin of five parts we've built before; those parts had these known failure modes — which of them did the engineer actually write down?* Whatever is missing is flagged, with the warranty record identifiers attached as proof. It also derives Occurrence from the measured claim rate instead of a workshop guess, and ranks findings by **Action Priority** — the AIAG-VDA lookup table that replaced RPN in 2019 — instead of a multiplication that misranks safety-relevant risk.

The system rests on one architectural rule: **deterministic engines own every number; an AI agent only reads findings and writes English.** No agent holds a tool that can write a Severity, Occurrence, Detection, or Action Priority value — that guarantee is enforced by a dedicated test suite, not just documented. The claim the product makes is deliberately narrow and checkable: *you have already seen this failure, and this DFMEA did not check for it* — verifiable against an 8D number, and defensible in an audit.

Validated on a temporal backtest across five historical cutoffs, the system lifts failure-mode recall from **71.7% (manual DFMEA baseline) to 98.3%**, newly catching 16 failure modes — each learned from a *different* part than the one it's flagging — behind 228 warranty claims.

## 2. Project use case

**Primary users, three different jobs:**

| Role | Job | What they get |
| --- | --- | --- |
| **Design / Reliability Engineer** | Draft a DFMEA for a part — often one that doesn't exist yet | A described part returns candidate failure modes grounded in the company's own history, each traced to the field records behind it, plus the single Occurrence/Detection change that would move a High-risk row to a lower band |
| **Quality Engineer** | Defend these documents in an audit; catch thin ones before they ship | A review queue of submitted drafts; declined rows are shown as *considered and declined*, not missing — the audit trail an auditor asks for |
| **Company / Leadership** | Know where program risk actually sits; justify the spend | Coverage across the program, open safety gaps by subsystem, and the backtest evidence — not row-level detail |

**Concrete scenario:** An engineer is specifying a new fuel-return-line clamp. They type a name, function, and material — no part number required. Mechnari finds the five most similar parts already in the BOM, pulls every failure mode those *kinds* of part are known for (from both the part's specific type and its broader family), scores each one from the actual warranty rate rather than opinion, and hands back a draft AIAG-VDA form-sheet row set the engineer edits, accepts, or declines.

**Who this fits:** manufacturers with years of warranty/8D history, a product family with recurring part kinds (hoses, brackets, valves, clamps recurring across programs), a real DFMEA obligation (IATF 16949 or equivalent), and enough parts that memory alone stops working as a consistency mechanism. Built against agricultural machinery, but the same shape holds for automotive, off-highway, and industrial equipment — any manufacturer of durable products with a warranty tail.

**Who this is not for (yet):** a company with no failure history to mine, or a team that wants the FMEA *written for them* — Mechnari deliberately will not assert a part type, set a score, or close an action.

## 3. Architecture diagram

![Mechnari.ai system architecture](architecture-diagram.png)

**Reading the layers, top to bottom:**

- **Frontend** — Next.js serves the three role views (`/design`, `/quality`, `/company`) plus an embedded Copilot chat, which can fill the intake form, run the analysis and move between views but holds no tool that writes a score.
- **Service (FastAPI)** — `api.py` is deliberately thin. Every route calls a module that already has its own test suite and shapes the return value as JSON. It computes nothing, so the frontend cannot produce a number the engines didn't produce.
- **Deterministic engines** — the actual product. `retrieval.py` (TF-IDF cosine similarity, head-noun weighted) finds similar historical parts; `gap_detection.py` is a set difference between applicable and analysed failure modes; `risk_engine.py` derives Severity/Occurrence/Detection and looks up Action Priority; `dfmea_sheet.py` assembles AIAG-VDA form-sheet rows without computing any score itself; `backtest.py` runs the temporal and cold-start validation harnesses.
- **Data layer** — `data_layer.py` is the single function that ever touches a file or table. BigQuery is the source of record; the CSV tables are the fallback (and what the test suite runs on), so a knowledge-base swap is a change inside one module with every engine downstream unaffected.
- **Agent layer** — a Google ADK 2.x agent (`mechnari_agent`) holds only read-only tools: it can look up findings and drive UI navigation, but has no tool capable of writing a score, marking an action complete, or naming an owner. It talks to Gemini through Vertex AI purely to turn findings into English explanation — the model never touches a number.

The enforcement of the core rule — *no agent can write a score* — lives in a test (`test_mechnari_tools.py`), not just in a design doc, so it survives a refactor rather than living in a comment.
