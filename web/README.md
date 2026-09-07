# Mechnari.ai — web frontend

Three role views over the same deterministic core:

| Route      | Role                 | What it does                                                                      |
| ---------- | -------------------- | --------------------------------------------------------------------------------- |
| `/design`  | Design Engineer      | Describe a new part, get a drafted DFMEA with evidence and AP levers, send it up.  |
| `/quality` | Quality Engineer     | Review submitted drafts, audit a part already on file, approve or return.          |
| `/company` | Company & Leadership | Program rollup: coverage, open safety gaps, and the temporal backtest.             |

## Running it

Two processes. From the repository root:

```bash
py -m uvicorn api:app --port 8000 --reload
```

```bash
npm --prefix web run dev
```

Then open <http://localhost:3000>. Both are also defined in `.claude/launch.json`
as `api` and `web`.

Copy `.env.example` to `.env.local` first — `NEXT_PUBLIC_API_BASE` has to point
at the backend origin the browser can reach.

## How it talks to the backend

Every number on every screen comes from `api.py`, which is itself a thin wrapper
around the Python engines (`retrieval`, `risk_engine`, `gap_detection`,
`backtest`, `queue_store`). Nothing here computes a score, a priority or a
recall figure — `src/lib/api.ts` is the only place that knows the API exists,
and it is typed against those route shapes.

The Action Priority levers ("what would bring this down") are computed
server-side by `risk_engine.find_ap_levers` and ride along on each candidate
row, so the client never fetches them per row.

`/company` and the server components of the other routes fetch on the server, so
the API must be reachable from the Next.js process as well as from the browser.
