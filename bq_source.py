"""
Mechnari.ai - BigQuery as the source of record
==============================================
Reads the knowledge-base tables out of BigQuery into the same DataFrames
`data_layer` used to build from CSV.

Why the tables are read whole, once, instead of being queried
-------------------------------------------------------------
The engines are not SQL workloads. Retrieval is TF-IDF cosine over every
part description; gap detection is a set difference; the backtest re-runs
retrieval across several temporal cutoffs. Those are iterative in-memory
computations, and pushing them into SQL would mean rewriting the four
modules that 137 tests cover.

So BigQuery is the *source*, not the query engine: each table is read once
per process into a DataFrame, `data_layer` caches it exactly as it cached
the CSV, and every engine downstream is unchanged and just as fast. When a
pilot company's real warranty history arrives - millions of claims rather
than hundreds - that is the point to push aggregation down, and the seam
for it is this module.

`list_rows` rather than `SELECT *`
----------------------------------
A table read through `list_rows` goes over the storage API and is not
billed as a query - no bytes scanned, no slot time. `SELECT *` would bill
the whole table on every cold start for no benefit, since nothing here
filters or aggregates.

Failure is not fatal
--------------------
Every function raises `BigQuerySourceError` rather than exiting, because
`data_layer` falls back to the CSVs on any failure. That keeps a missing
dataset, a revoked permission or an unreachable API from taking the app
down - the same posture `queue_store` takes with Firestore.
"""

import os
from typing import List

# Load .env here, in the module whose behaviour depends on it.
#
# Not decoration: api.py does not load .env at all, and the only reason
# GOOGLE_CLOUD_PROJECT was reaching this code locally is that api.py
# imports mechnari_agent, which happens to call load_dotenv at import
# time. So whether the app read from BigQuery depended on import order -
# and when that lost, `configured()` returned False and every table fell
# back to CSV silently. Cloud Run sets real environment variables so it
# was never affected, which is the worst shape for a bug like this: it
# only misbehaves on the machine you develop on.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:  # pragma: no cover - python-dotenv is declared
    pass

_PROJECT_ENV = ("MECHNARI_BQ_PROJECT", "GOOGLE_CLOUD_PROJECT")

DATASET = os.getenv("MECHNARI_BQ_DATASET", "mechnari_engineering")

# BigQuery table name per data_layer table key. Kept here rather than
# derived from the CSV filenames so a rename on either side is a visible
# edit instead of a silent mismatch.
BQ_TABLES = {
    "part_types": "part_types",
    "failure_effects": "failure_effects",
    "bom": "bom_package_hierarchy",
    "material_master": "material_master",
    "failure_mode_catalog": "failure_mode_catalog",
    "field_issues": "field_issues",
    "dfmea_worksheet": "dfmea_worksheet",
}


class BigQuerySourceError(RuntimeError):
    """BigQuery could not serve a table. Callers fall back to CSV."""


def project() -> str:
    """The project holding the dataset, or "" if none is configured."""
    for name in _PROJECT_ENV:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def configured() -> bool:
    """Whether BigQuery is the requested source AND a project is set.

    Both halves matter: asking for BigQuery without a project is a
    misconfiguration that should fall back visibly rather than raise on
    the first table read.
    """
    requested = os.getenv("MECHNARI_DATA_SOURCE", "csv").strip().lower()
    return requested == "bigquery" and bool(project())


def _client():
    try:
        from google.cloud import bigquery
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise BigQuerySourceError("google-cloud-bigquery is not installed") from exc
    try:
        return bigquery.Client(project=project())
    except Exception as exc:
        raise BigQuerySourceError("could not create a BigQuery client: %s" % exc) from exc


def table_id(table: str) -> str:
    if table not in BQ_TABLES:
        raise BigQuerySourceError("no BigQuery table mapped for %r" % table)
    return "%s.%s.%s" % (project(), DATASET, BQ_TABLES[table])


def read_table(table: str):
    """One knowledge-base table as a DataFrame, read whole.

    Raises BigQuerySourceError on anything at all - a missing dataset, a
    permission problem, an empty table - so the caller can fall back.
    """
    import pandas as pd  # local: keeps import cost off modules that never read

    client = _client()
    try:
        rows = client.list_rows(table_id(table))
        df = rows.to_dataframe()
    except Exception as exc:
        raise BigQuerySourceError(
            "could not read %s: %s" % (table_id(table), exc)
        ) from exc

    if df is None or df.empty:
        raise BigQuerySourceError("%s returned no rows" % table_id(table))

    # BigQuery has no column order guarantee that pandas relies on, and a
    # DATE column arrives as dbdate rather than the string read_csv would
    # have produced. Normalising both here keeps every engine downstream
    # byte-identical between the two sources, which is what makes swapping
    # the source safe rather than merely plausible.
    for column in df.columns:
        if str(df[column].dtype) in ("dbdate", "dbtime", "datetime64[ns]"):
            df[column] = df[column].astype(str)
    return df


def missing_tables() -> List[str]:
    """Mapped tables that BigQuery cannot currently serve."""
    absent = []
    for table in BQ_TABLES:
        try:
            read_table(table)
        except BigQuerySourceError:
            absent.append(table)
    return absent
