"""
Mechnari.ai - which source serves the knowledge base
====================================================
Run with:  python test_data_source.py     (or: pytest test_data_source.py)

These tests never touch BigQuery. They cover the switching and the
fallback, which is where the risk actually is: a warehouse that stops
answering must degrade to the CSVs rather than take the app down, and it
must say so rather than pretending the data came from BigQuery.

The one thing they deliberately assert about defaults is that an
unconfigured process reads CSV. Every other suite depends on that - if
the default ever flipped, 137 tests would start needing cloud
credentials and the figures in the README would stop being reproducible
offline.
"""

import os
import sys

import bq_source
import data_layer


def _clear():
    for name in ("MECHNARI_DATA_SOURCE", "MECHNARI_BQ_PROJECT"):
        os.environ.pop(name, None)
    data_layer.reload()


def test_default_source_is_csv():
    """No configuration means the CSVs, so no suite needs cloud auth."""
    _clear()
    try:
        assert not bq_source.configured()
        data_layer.parts()
        assert data_layer.source() == "csv", data_layer.source()
    finally:
        _clear()


def test_bigquery_without_a_project_is_not_configured():
    """Asking for BigQuery with no project falls back rather than raising.

    A half-set configuration is a likely deployment mistake, and the
    useful behaviour is a working app plus a visible note - not a stack
    trace on the first table read."""
    _clear()
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("MECHNARI_BQ_PROJECT", None)
    try:
        assert not bq_source.configured()
    finally:
        _clear()


def test_unreachable_bigquery_degrades_to_the_csv():
    """The whole safety argument for pointing at a warehouse."""
    _clear()
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ["MECHNARI_BQ_PROJECT"] = "no-such-project-mechnari-test"
    real = bq_source.read_table

    def explode(table):
        raise bq_source.BigQuerySourceError("simulated outage")

    bq_source.read_table = explode
    try:
        parts = data_layer.parts()
        assert len(parts) == 50, len(parts)
        assert data_layer.source() == "csv", data_layer.source()
        notes = data_layer.source_notes()
        assert any("bigquery unavailable" in n for n in notes.values()), notes
    finally:
        bq_source.read_table = real
        _clear()


def test_a_served_table_is_reported_as_bigquery():
    """source() reflects what was read, not what was asked for.

    This is the distinction that caught a real bug: with the source set
    to bigquery but no project resolvable, every table fell back to CSV
    and a flag reporting the *intent* would have said "bigquery" while
    the CSVs did the work."""
    _clear()
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ["MECHNARI_BQ_PROJECT"] = "fake-project-for-test"
    real = bq_source.read_table
    bq_source.read_table = lambda table: data_layer._read_csv(table)
    try:
        data_layer.parts()
        assert data_layer.source() == "bigquery", data_layer.source()
        assert set(data_layer.source_notes().values()) == {"bigquery"}
    finally:
        bq_source.read_table = real
        _clear()


def test_mixed_is_reported_when_only_some_tables_fall_back():
    """Partial degradation is its own state and must not read as either."""
    _clear()
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ["MECHNARI_BQ_PROJECT"] = "fake-project-for-test"
    real = bq_source.read_table

    def only_part_types(table):
        if table == "part_types":
            return data_layer._read_csv(table)
        raise bq_source.BigQuerySourceError("simulated partial outage")

    bq_source.read_table = only_part_types
    try:
        data_layer.parts()  # reads bom, material_master and part_types
        assert data_layer.source() == "mixed", data_layer.source()
    finally:
        bq_source.read_table = real
        _clear()


def test_every_data_layer_table_has_a_bigquery_table():
    """A table added to one map and not the other would fall back forever
    while looking configured."""
    assert set(bq_source.BQ_TABLES) == set(data_layer.TABLES), (
        sorted(set(bq_source.BQ_TABLES) ^ set(data_layer.TABLES))
    )


def test_table_id_is_fully_qualified():
    _clear()
    os.environ["MECHNARI_BQ_PROJECT"] = "proj-x"
    try:
        assert bq_source.table_id("field_issues") == (
            "proj-x.%s.field_issues" % bq_source.DATASET
        )
    finally:
        _clear()


def test_an_unmapped_table_is_an_error_not_a_guess():
    try:
        bq_source.table_id("not_a_table")
    except bq_source.BigQuerySourceError:
        return
    raise AssertionError("expected BigQuerySourceError for an unmapped table")


def test_source_reads_before_answering_rather_than_reporting_intent():
    """A cold cache must not answer from configuration.

    This is the bug this whole function exists to prevent, and it shipped
    once: a freshly started Cloud Run instance answered /api/health with
    "bigquery" before it had read a single table. Here the source is set
    to bigquery with a project that resolves, but every read fails - so
    the only honest answer is csv, and an intent-based one would say
    bigquery."""
    _clear()
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ["MECHNARI_BQ_PROJECT"] = "fake-project-for-test"
    real = bq_source.read_table

    def explode(table):
        raise bq_source.BigQuerySourceError("simulated outage")

    bq_source.read_table = explode
    try:
        assert data_layer.source_notes() == {}, "cache should start cold"
        assert data_layer.source() == "csv", data_layer.source()
        assert data_layer.source_notes(), "source() should have read something"
    finally:
        bq_source.read_table = real
        _clear()


def test_reload_forgets_which_source_served():
    """Otherwise a health check keeps reporting a source that is no longer
    the one in use after the data is reloaded."""
    _clear()
    data_layer.parts()
    assert data_layer.source_notes()
    data_layer.reload()
    assert data_layer.source_notes() == {}
    _clear()


def _main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except AssertionError as exc:
            failures += 1
            print("FAIL  %s\n      %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            failures += 1
            print("ERROR %s\n      %s: %s" % (name, type(exc).__name__, exc))
    print("\n%d passed, %d failed" % (len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
