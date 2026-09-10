# Frontend

Two frontends over the same engines.

| | Stack | Purpose |
| --- | --- | --- |
| **`web/`** | Next.js 16, React 19, Tailwind 4, CopilotKit v2 | The product — three role views and the copilot |

Neither contains arithmetic, so neither can produce a number the engines did
not produce.

---

## The three role views

Drafting a DFMEA, auditing one, and reporting on program risk are different
jobs and do not want the same screen.

### `/design` — Part Intake

*Draft a DFMEA, or open one already on file.*

- `PartIntake.tsx` — describe a part (number, description, function, material,
  system package), or pick one already in the BOM.
- `AnalysisOverview.tsx` — what retrieval found: the neighbours, the inferred
  type and its confidence, and how many safety-relevant candidates came back.
- `DfmeaSheet.tsx` — the proposal, laid out as AIAG-VDA form-sheet rows.
  Editing Detection on a row re-derives Action Priority through
  `POST /api/rescore`, never in the browser.
- `ExistingDfmeaView.tsx` — for a part on file: what was filed, what the
  warranty record says now, and which applicable modes were never analysed.
- `MyReports.tsx` — saved analyses. Signed in they live in Firestore and
  follow the user across machines; signed out they fall back to this
  browser's local storage.
- `/design/report/[id]` — one saved report, by URL.

On every High row the sheet shows the AP lever: the single change in
Occurrence or Detection that would actually move the band, computed against
the AP table rather than suggested.

### `/quality` — Review Queue

*Audit submitted drafts against the registry and the warranty record.*

- `QueueBrowser.tsx` — submitted drafts, each linkable by URL
  (`/quality?draft=...`). Accepted and **declined** rows are shown separately:
  a declined High row reads as *considered and declined*, not as missing.
  Status moves between `needs_review`, `returned` and `approved`.
- `PartAuditor.tsx` — the same audit suite against a part already on file:
  severity consistency, Occurrence against the warranty record, and coverage.

### `/company` — Program Health

*Rollup across the program, with the backtest behind it.*

Metric tiles (parts covered, mean DFMEA coverage, open safety gaps at S≥9,
the backtest lift in points), open safety gaps ranked by system package,
`BacktestChart.tsx` for the recall curve across cutoffs, and `IssueHistory.tsx`
for what has actually gone wrong.

Pages are React Server Components: they fetch from the API on the server and
render, so the first paint has real numbers in it.

---

## The copilot

`MechnariCopilot.tsx` mounts CopilotKit's chat against the AG-UI endpoint,
relayed through `web/src/app/api/copilotkit/[[...path]]/route.ts`. That Next.js
route calls no model — the ADK agent behind FastAPI does the model work.

### It knows what is on screen

`useAgentContext` publishes the intake fields, the stage of the workflow, and
any rows under review. So "why is this row High" is answerable about the row
in front of the engineer, without asking which one.

That context is typed `JsonSerializable`, not `Record<string, unknown>`,
because CopilotKit stringifies it before sending: a `Date`, a function or a
component would silently reach the model as `null`, and the agent would answer
about a screen state that is not the one in front of the engineer.

### What it is allowed to do to the UI

| Tool | Effect |
| --- | --- |
| `fillPartIntake` | Fills the intake form from a part the engineer described in conversation. Descriptive fields only. |
| `buildDfmea` | Runs the analysis on whatever is in the form, so findings land in the review where they can be edited. |
| `reanalyseAsPartType` | Re-runs it as a corrected part type when the engineer says the inferred one is wrong. |
| `openExistingPartDfmea` | Opens the DFMEA on file for a BOM part, by id or name. |
| `goToView` | Switches between `design`, `quality` and `company`. |
| `proposeDeclineRow` | **Proposes** leaving a row out. Human-in-the-loop: the engineer approves it in the chat before anything changes. |
| `explainWhyICannotChangeScores` | Says plainly which of the three refusals applies, and why. |

The agent is told to prefer a client tool over answering in text whenever one
exists for what was asked — acting on the screen beats describing it — and
**not** to transfer to a sub-agent for one, because sub-agents cannot reach
these tools and delegating a UI instruction silently turns it back into prose.

### What it is not allowed to do

The line drawn here is the one the whole product rests on: **the agent may
drive the tedium, and may not make the judgements.**

Three refusals, and there is no tool for any of them:

1. **Set a Severity, Occurrence or Detection score.** Severity comes from the
   effect registry; Occurrence is counted from warranty claims. The engineer
   *can* override Occurrence in the review — with a written reason that gets
   recorded.
2. **Mark an action complete.**
3. **Name who owns an action.**

Data entry, navigation and re-running an analysis are all reversible by
looking at the screen. Writing a score, asserting that work happened or
inventing a commitment would make the resulting DFMEA a fabrication rather
than a record.

Declining a row is the interesting middle case — a real engineering judgement
with audit consequences — which is why it is proposed and approved rather than
done.

This is the frontend half of a guarantee whose backend half is asserted by
`test_mechnari_tools.py`. An action the agent has no tool for is an action it
cannot take, whatever it is asked.

### CopilotKit v2

Parameters are zod schemas rather than v1's `parameters: [{ name, type,
required }]` arrays. Worth the migration for one reason: handler `args` are
now typed from the schema, so a field renamed in one place and not the other
is a compile error instead of an `undefined` that quietly writes a blank into
a form.

`useHumanInTheLoop` has no `handler` by construction — the type omits it —
which is a better shape than v1's, where `handler` and
`renderAndWaitForResponse` were both accepted but mutually exclusive at
runtime, and supplying both silently applied the change before the engineer
was asked.

---

## Sign-in

Google sign-in via Firebase (`SignIn.tsx`, `lib/auth.tsx`), verified
server-side. Optional everywhere: every read view works signed out. Signing in
buys ownership of saved reports.

If the four `NEXT_PUBLIC_FIREBASE_*` values are absent at **build** time the
app still works — permanently signed out, with the sign-in button hidden. The
backend reports `auth_available` on `/api/health` so the frontend hides a
button that could not work rather than offering one that fails.

## Theme

`ThemeToggle.tsx` — light and dark, with the choice persisted.

---


