"""
Mechnari.ai - Normalized Data Layer
====================================
One place that knows how the DFMEA knowledge base is stored, so the agents
and the UI never touch file paths or CSV parsing.

Tables
------
part_types            family / type taxonomy every part belongs to
failure_effects       one standard severity per effect, organization wide
parts                 active BOM joined to material master and part type
failure_mode_catalog  failure modes keyed by TYPE or FAMILY, with provenance
field_issues          warranty / 8D records, many per part
dfmea_worksheet       the DFMEA on file today (part_id + mode_id + S/O/D)

Where the tables come from
--------------------------
BigQuery when `MECHNARI_DATA_SOURCE=bigquery` and a project is set,
otherwise the CSVs in data/. That promise the previous version of this
docstring made - "swapping the source for a real query later is a change
inside this module only" - turned out to be true: `_read` is the only
function that ever touched a file, so it is the only one that changed.

The fallback is deliberate and one-directional. If BigQuery cannot serve
a table for any reason - dataset absent, permission revoked, API
unreachable - that table is read from the CSV instead and the reason is
recorded in `source_notes()`. A warehouse being unavailable should not
take the app down, which is the same posture `queue_store` takes with
Firestore. The reverse is not offered: nothing writes back to BigQuery
from here, because the knowledge base is loaded, not edited.

Tests run on CSV. They do not set the env var, so no suite needs cloud
credentials and the figures they assert stay reproducible offline.
"""

import os
from functools import lru_cache

import pandas as pd

import bq_source

# Resolve data/ relative to this file so the app works from any cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "data")

TABLES = {
    "part_types": "part_types.csv",
    "failure_effects": "failure_effects.csv",
    "bom": "bom_package_hierarchy.csv",
    "material_master": "material_master.csv",
    "failure_mode_catalog": "failure_mode_catalog.csv",
    "field_issues": "field_issues.csv",
    "dfmea_worksheet": "dfmea_worksheet.csv",
}


class DatasetError(RuntimeError):
    """Raised when the knowledge base is missing or unreadable."""


def _path(table: str) -> str:
    return os.path.join(DATA_DIR, TABLES[table])


def missing_tables():
    """Tables the knowledge base needs but does not have."""
    return [name for name in TABLES if not os.path.exists(_path(name))]


# Which source actually served each table, and why, so /api/health can
# report the truth rather than the configured intent. A table that fell
# back is far more useful to see than a global flag that says "bigquery"
# while the CSVs are doing the work.
_NOTES: dict = {}


def _read_csv(table: str) -> pd.DataFrame:
    path = _path(table)
    if not os.path.exists(path):
        raise DatasetError(
            "Missing %s. Run: python generate_csv_data.py" % os.path.relpath(path, _HERE)
        )
    df = pd.read_csv(path)
    if df.empty:
        raise DatasetError("%s is empty." % os.path.relpath(path, _HERE))
    return df


@lru_cache(maxsize=None)
def _read(table: str) -> pd.DataFrame:
    if bq_source.configured():
        try:
            df = bq_source.read_table(table)
            _NOTES[table] = "bigquery"
            return df
        except bq_source.BigQuerySourceError as exc:
            # Recorded, not raised: the CSV below is a working knowledge
            # base, so a warehouse problem degrades the provenance of the
            # data rather than the availability of the app.
            _NOTES[table] = "csv (bigquery unavailable: %s)" % exc
    else:
        _NOTES[table] = "csv"
    return _read_csv(table)


def source() -> str:
    """"bigquery", "csv", "mixed", or "unavailable" - what actually served.

    Reads the smallest table first if nothing has been read yet, rather
    than reporting the configured intent. That distinction is the entire
    point of this function, and reporting intent when the cache was cold
    was a real bug: a freshly started Cloud Run instance answered
    /api/health with "bigquery" before it had read a single table, which
    is exactly the reassuring-but-unearned answer this exists to avoid.

    part_types is 17 rows and is cached after the first read, so the cost
    is one small read per process.
    """
    if not _NOTES:
        try:
            _read("part_types")
        except DatasetError:
            return "unavailable"
    kinds = {"bigquery" if note == "bigquery" else "csv" for note in _NOTES.values()}
    return kinds.pop() if len(kinds) == 1 else "mixed"


def source_notes() -> dict:
    """Per table, which source served it and why. Empty until first read."""
    return dict(_NOTES)


def reload():
    """Drop cached tables - call after regenerating the CSVs or reloading
    BigQuery, so the next read picks the source up fresh."""
    _read.cache_clear()
    _NOTES.clear()


def part_types() -> pd.DataFrame:
    return _read("part_types").copy()


def failure_effects() -> pd.DataFrame:
    return _read("failure_effects").copy()


def parts() -> pd.DataFrame:
    """Active BOM joined to material specs and the part type taxonomy."""
    bom = _read("bom")
    material = _read("material_master").drop(columns=["material_id_part_name"])
    types = _read("part_types")

    df = bom.merge(material, on="part_id", how="left", validate="one_to_one")
    unmatched = int(df["drawing_spec_ref"].isna().sum())
    if unmatched:
        # Surfaced rather than silently dropped: a part with no material
        # record is a data problem the engineer needs to know about.
        df["drawing_spec_ref"] = df["drawing_spec_ref"].fillna("NO MATERIAL RECORD")

    df = df.merge(types, on="part_type_id", how="left", validate="many_to_one")
    df.attrs["parts_without_material_record"] = unmatched
    return df


def failure_mode_catalog() -> pd.DataFrame:
    """Failure modes keyed by part type, with the effect and its severity."""
    catalog = _read("failure_mode_catalog")
    effects = _read("failure_effects")
    return catalog.merge(effects, on="effect_id", how="left", validate="many_to_one")


def field_issues() -> pd.DataFrame:
    """Warranty / 8D records. Many rows per part - this is the evidence base."""
    df = _read("field_issues").copy()
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df["claims_per_1000"] = (
        df["claim_count"] / df["units_in_service"].replace(0, pd.NA) * 1000
    ).astype(float)
    return df


def dfmea_worksheet() -> pd.DataFrame:
    """The DFMEA currently on file: which modes each part has actually analysed."""
    return _read("dfmea_worksheet").copy()


def analysed_modes() -> dict:
    """part_id -> set of mode_ids already covered by the DFMEA on file."""
    worksheet = _read("dfmea_worksheet")
    return {
        part_id: set(group["mode_id"])
        for part_id, group in worksheet.groupby("part_id", sort=False)
    }


PART_COLUMNS = [
    "part_id", "item_reference", "system_package", "material_type",
    "part_type_id", "part_type_name", "family_id", "family_name",
]


def applicable_modes() -> pd.DataFrame:
    """
    Every (part, failure mode) pair the knowledge base considers applicable.

    A part inherits modes attached to its own type and modes attached to its
    family. Scope ids are disjoint by prefix (PT- vs FAM-), so the two joins
    cannot produce the same pair twice.
    """
    part_rows = parts()[PART_COLUMNS]
    catalog = failure_mode_catalog()

    by_type = part_rows.merge(
        catalog, left_on="part_type_id", right_on="scope_id", how="inner")
    by_family = part_rows.merge(
        catalog, left_on="family_id", right_on="scope_id", how="inner")
    return pd.concat([by_type, by_family], ignore_index=True)


def coverage_summary() -> pd.DataFrame:
    """Per part: how much of the failure history applicable to it it has analysed."""
    part_rows = parts()[["part_id", "item_reference", "system_package",
                         "part_type_id", "part_type_name"]]
    applicable_counts = (
        applicable_modes().groupby("part_id").size().rename("modes_applicable")
    )
    analysed_counts = (
        dfmea_worksheet().groupby("part_id").size().rename("modes_analysed")
    )

    df = part_rows.merge(applicable_counts, on="part_id", how="left")
    df = df.merge(analysed_counts, on="part_id", how="left")
    df["modes_analysed"] = df["modes_analysed"].fillna(0).astype(int)
    df["modes_applicable"] = df["modes_applicable"].fillna(0).astype(int)
    df["modes_not_analysed"] = df["modes_applicable"] - df["modes_analysed"]
    df["coverage_pct"] = (
        df["modes_analysed"] / df["modes_applicable"].replace(0, pd.NA) * 100
    ).round(0)
    return df


def issue_history(part_id: str = None) -> pd.DataFrame:
    """
    Warranty issues with the failure mode name resolved in, newest first.

    field_issues() carries 71 distinct part_ids but parts() only carries the
    50 still on the active BOM - the other 21 are retired parts kept only
    because their failures are exactly what retrieval learns from. So this
    joins against failure_mode_catalog (universal) rather than parts()
    (partial), and item_reference is left null rather than dropping the row
    for a retired part with no current listing.
    """
    issues = field_issues()
    if part_id:
        issues = issues[issues["part_id"] == part_id]
    modes = failure_mode_catalog()[["mode_id", "failure_mode"]]
    part_names = parts()[["part_id", "item_reference"]]
    df = issues.merge(modes, on="mode_id", how="left")
    df = df.merge(part_names, on="part_id", how="left")
    return df.sort_values("report_date", ascending=False)


def issue_summary() -> pd.DataFrame:
    """Per part_id: how many warranty issues and claims are on record for it -
    across all 71 part_ids that have ever had one, active or retired."""
    issues = field_issues()
    part_names = parts()[["part_id", "item_reference"]]
    summary = (
        issues.groupby("part_id")
        .agg(issue_count=("issue_id", "size"), total_claims=("claim_count", "sum"),
             latest_report=("report_date", "max"))
        .reset_index()
    )
    summary = summary.merge(part_names, on="part_id", how="left")
    summary["item_reference"] = summary["item_reference"].fillna(
        summary["part_id"] + " (retired part, not on current BOM)"
    )
    return summary.sort_values("issue_count", ascending=False)
