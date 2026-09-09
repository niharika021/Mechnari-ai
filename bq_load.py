"""
Mechnari.ai - load the knowledge base into BigQuery
===================================================
Creates the dataset if it does not exist and loads each CSV into the table
`bq_source.BQ_TABLES` names for it. Idempotent: every load is
WRITE_TRUNCATE, so running it twice leaves the same rows, not double.

Run it from the repository root:

    py bq_load.py                      # load into the configured project
    py bq_load.py --dataset my_ds      # somewhere else
    py bq_load.py --verify             # compare BigQuery against the CSVs

Schema is autodetected rather than taken from schema.sql. That is
deliberate: autodetect reads the actual CSV that `generate_csv_data.py`
just wrote, so the loaded types cannot drift from the data the way a
hand-maintained DDL does - schema.sql had drifted to two tables with
names that no longer matched any CSV. schema.sql is documentation of the
target warehouse shape; this is the thing that has to agree with reality.

--verify is the check that matters. Loading is easy to do and easy to do
wrongly - a column typed as STRING where the CSV had integers, a date
parsed to a different resolution - and none of that shows up until an
engine divides by it. It reads every table back through the same code
path the app uses and compares row counts and column names against the
CSV, so a mismatch is caught here rather than as a wrong number on a
DFMEA row.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import bq_source  # noqa: E402
import data_layer  # noqa: E402


def _client(project: str):
    from google.cloud import bigquery

    return bigquery.Client(project=project)


def ensure_dataset(client, project: str, dataset: str, location: str) -> None:
    from google.cloud import bigquery
    from google.api_core.exceptions import Conflict

    ref = bigquery.Dataset("%s.%s" % (project, dataset))
    ref.location = location
    ref.description = (
        "Mechnari.ai DFMEA knowledge base: taxonomy, failure-mode catalog, "
        "warranty/8D history and the DFMEA on file."
    )
    try:
        client.create_dataset(ref)
        print("created dataset %s.%s in %s" % (project, dataset, location))
    except Conflict:
        print("dataset %s.%s already exists" % (project, dataset))


def schema_from_csv(key: str):
    """A BigQuery schema taken from what pandas reads out of the CSV.

    Autodetect was tried first and got one table wrong in a way worth
    recording: `bom_package_hierarchy` is all-string, so BigQuery could
    not tell its header row from a data row and loaded the columns as
    `string_field_0..5`. Row count was right, every column name was
    gone, and nothing failed - the app would simply have found no
    `part_id` and served an empty BOM.

    Deriving the schema from `pd.read_csv` fixes both halves at once:
    the names come from the header explicitly rather than by inference,
    and the types come from the same dtype inference the CSV path
    already applies. So a column is INT64 in BigQuery exactly when it
    was int64 in the DataFrame the engines used to get, which is what
    makes the two sources interchangeable instead of merely similar.
    """
    from google.cloud import bigquery

    df = data_layer._read_csv(key)
    fields = []
    for column in df.columns:
        dtype = str(df[column].dtype)
        if dtype.startswith("int"):
            bq_type = "INT64"
        elif dtype.startswith("float"):
            bq_type = "FLOAT64"
        elif dtype == "bool":
            bq_type = "BOOL"
        else:
            # Dates included: read_csv hands them over as strings and
            # field_issues() does its own to_datetime, so typing them as
            # DATE here would change what the engines receive.
            bq_type = "STRING"
        fields.append(bigquery.SchemaField(column, bq_type))
    return fields


def load_all(project: str, dataset: str, location: str) -> int:
    from google.cloud import bigquery

    client = _client(project)
    ensure_dataset(client, project, dataset, location)

    failures = 0
    for key, table in bq_source.BQ_TABLES.items():
        csv_path = os.path.join(data_layer.DATA_DIR, data_layer.TABLES[key])
        if not os.path.exists(csv_path):
            print("  SKIP  %-24s no CSV at %s" % (table, csv_path))
            failures += 1
            continue

        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=schema_from_csv(key),
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        target = "%s.%s.%s" % (project, dataset, table)
        with open(csv_path, "rb") as handle:
            job = client.load_table_from_file(handle, target, job_config=config)
        try:
            job.result()
        except Exception as exc:
            print("  FAIL  %-24s %s" % (table, str(exc)[:120]))
            failures += 1
            continue
        loaded = client.get_table(target)
        print("  ok    %-24s %4d rows, %2d columns"
              % (table, loaded.num_rows, len(loaded.schema)))
    return failures


def verify(project: str, dataset: str) -> int:
    """Read every table back the way the app does, and compare to the CSV."""
    os.environ["MECHNARI_DATA_SOURCE"] = "bigquery"
    os.environ["MECHNARI_BQ_PROJECT"] = project
    bq_source.DATASET = dataset

    problems = 0
    for key in bq_source.BQ_TABLES:
        csv_df = data_layer._read_csv(key)
        try:
            bq_df = bq_source.read_table(key)
        except bq_source.BigQuerySourceError as exc:
            print("  FAIL  %-24s %s" % (key, str(exc)[:110]))
            problems += 1
            continue

        notes = []
        if len(bq_df) != len(csv_df):
            notes.append("rows %d vs %d" % (len(bq_df), len(csv_df)))
        missing = set(csv_df.columns) - set(bq_df.columns)
        extra = set(bq_df.columns) - set(csv_df.columns)
        if missing:
            notes.append("missing columns %s" % sorted(missing))
        if extra:
            notes.append("extra columns %s" % sorted(extra))
        if notes:
            print("  DIFF  %-24s %s" % (key, "; ".join(notes)))
            problems += 1
        else:
            print("  ok    %-24s %4d rows match the CSV" % (key, len(bq_df)))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=bq_source.project())
    parser.add_argument("--dataset", default=bq_source.DATASET)
    parser.add_argument("--location", default=os.getenv("MECHNARI_BQ_LOCATION", "US"))
    parser.add_argument("--verify", action="store_true",
                        help="only compare BigQuery against the CSVs")
    args = parser.parse_args()

    if not args.project:
        print("No project. Set GOOGLE_CLOUD_PROJECT or pass --project.")
        return 2

    if args.verify:
        print("Verifying %s.%s against data/*.csv" % (args.project, args.dataset))
        problems = verify(args.project, args.dataset)
        print("\n%s" % ("all tables match" if not problems
                        else "%d table(s) differ" % problems))
        return 1 if problems else 0

    print("Loading data/*.csv into %s.%s" % (args.project, args.dataset))
    failures = load_all(args.project, args.dataset, args.location)
    if failures:
        print("\n%d table(s) failed to load" % failures)
        return 1

    print("\nVerifying what was just written:")
    problems = verify(args.project, args.dataset)
    if problems:
        print("\n%d table(s) do not match the CSVs" % problems)
        return 1
    print("\nLoaded and verified. Set MECHNARI_DATA_SOURCE=bigquery to serve from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
