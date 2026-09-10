# Mechnari.ai — Documentation

Mechnari.ai turns a manufacturer's own warranty history into the primary
knowledge source for analysing a new part, and tells engineers what the
Design FMEA they just signed never checked.

Live: <https://app.mechnari.in>

These pages are the complete reference. Start wherever your question is.

| Page | Answers |
| --- | --- |
| [Overview](overview.md) | What this is, the problem it exists for, and the one claim it makes |
| [Who it's for](who-its-for.md) | The three roles, the company profile that benefits, and who should not buy it |
| [How it works](how-it-works.md) | The mechanism end to end — retrieval, gap detection, scoring, backtest |
| [Architecture](architecture.md) | Components, the service boundary, and where the agent is *not* allowed |
| [Data model](data-model.md) | The eight tables, the two-level taxonomy, and why severity lives in a registry |
| [API reference](api-reference.md) | Every HTTP route, its request and its response |
| [Frontend](frontend.md) | The three role views and the copilot's action surface |
| [Operations](operations.md) | Install, configure, run, test, deploy, and the storage backends |
| [Evidence and limits](evidence-and-limits.md) | Measured results, the honesty rules behind them, and what is not proven |
| [Glossary](glossary.md) | DFMEA, S/O/D, Action Priority, RPN, 8D, IATF 16949 — for readers outside the field |

Also in the repository:

- [`../README.md`](../README.md) — the short technical pitch with the headline numbers
- [`../intro.md`](../intro.md) — a plain-language introduction with no FMEA vocabulary
- [`../DEPLOY.md`](../DEPLOY.md) — the Cloud Run deployment runbook, step by step
- [`build-dossier.html`](build-dossier.html) — the concept and build report

## Status of the figures in these pages

Every number quoted here was reproduced against the committed code on
2026-09-10: `147 tests across 9 suites, all passing`, and the engine
headlines regenerated from `gap_detection.headline_metrics()`,
`risk_engine.headline_metrics()` and `backtest.headline()` — identically
whether they run against BigQuery or the CSV fallback (`bq_load.py --verify`
confirms it, and `test_data_source.py` covers the switch). Where a figure
is provisional or unverified, the page says so at the point it is used —
most importantly the [Action Priority table](evidence-and-limits.md#the-action-priority-table-is-provisional),
which is not yet checked cell by cell against the published handbook.
