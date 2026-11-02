"""Land the legacy CSV export in bronze as partitioned Parquet.

Bronze keeps what arrived: no cleaning, no deduplication, no dropped rows.
Rerunning gives the same files, so the script is safe to repeat.

Choices (argued in docs/adr/0002-bronze-layout.md):
- Every column is read as text, with only truly empty cells as null. pandas'
  defaults would drop the leading zeros of phones, zips and p_id, and turn the
  strings None, NA, N/A, NULL into nulls. Only the columns in INT_COLUMNS,
  FLOAT_COLUMNS and DATE_COLUMNS are cast, and only because they are numbers
  or dates in every file.
- The unnamed index column of 25 files is kept, as csv_index.
- orders is partitioned by year of order_date (hive layout order_year=YYYY).
  By month it was 37 files of about 180 KB: too small.
  Every other table is one file: the biggest has 408,560 rows.
- customer and payment_details are never landed: they hold plaintext
  passwords and card numbers, and ADR-0001 says they are never extracted.

Usage:
    python ingestion/land_export.py --src C:/de/export/legacy_csv/legacy_csv
    python ingestion/land_export.py --src ... --upload --external
"""

import argparse
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT = "data-engineering-i1"
BUCKET = "gs://data-engineering-i1-g04"
DATASET = "g04_bronze"
LOCATION = "europe-west1"

# Never landed: they hold plaintext passwords and card numbers.
SKIP_TABLES = {"customer", "payment_details"}
SECRET_COLUMNS = {"pwd", "card_no", "cvv"}

# table -> (column to partition by, function that gives the partition value)
PARTITIONS = {"orders": ("order_date", "order_year", lambda s: s.str[:4])}

INT_COLUMNS = {
    "csv_index", "order_id", "payment_id", "discount_id", "address_id",
    "review_id", "qty", "rating", "category_id",
}
FLOAT_COLUMNS = {"price", "price_at_purchase"}
DATE_COLUMNS = {"order_date"}


def read_csv(path: Path) -> pd.DataFrame:
    """Read one CSV as text. Only an empty cell is null; 'NA' stays 'NA'."""
    df = pd.read_csv(
        path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8"
    )
    if df.columns[0].startswith("Unnamed"):
        df = df.rename(columns={df.columns[0]: "csv_index"})
    leaked = SECRET_COLUMNS & set(df.columns)
    if leaked:
        raise SystemExit(f"{path.name} has secret columns {leaked}: refusing")
    for col in df.columns:
        if col in INT_COLUMNS:
            df[col] = pd.to_numeric(df[col]).astype("Int64")
        elif col in FLOAT_COLUMNS:
            df[col] = pd.to_numeric(df[col]).astype("float64")
        elif col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], format="%Y-%m-%d").dt.date
    return df


def to_arrow(df: pd.DataFrame) -> pa.Table:
    """Text columns are string even when empty: BigQuery refuses a null type."""
    fields = {
        col: pa.string()
        for col in df.columns
        if col not in DATE_COLUMNS and not pd.api.types.is_numeric_dtype(df[col])
    }
    schema = pa.Schema.from_pandas(df, preserve_index=False)
    for i, field in enumerate(schema):
        if field.name in fields:
            schema = schema.set(i, pa.field(field.name, pa.string()))
    return pa.Table.from_pandas(df, schema=schema, preserve_index=False)


def write_table(table: str, df: pd.DataFrame, out: Path) -> int:
    """Write a table under out/<table>/. Returns the number of files."""
    target = out / table
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    if table in PARTITIONS:
        source, part_col, fn = PARTITIONS[table]
        key = fn(df[source].astype(str))
        for value, chunk in df.groupby(key):
            folder = target / f"{part_col}={value}"
            folder.mkdir()
            pq.write_table(
                to_arrow(chunk),
                folder / "part-0.parquet",
                compression="snappy",
            )
        return df.groupby(key).ngroups
    pq.write_table(
        to_arrow(df),
        target / "part-0.parquet",
        compression="snappy",
    )
    return 1


def run(cmd: list[str]) -> None:
    exe = shutil.which(cmd[0]) or cmd[0]
    subprocess.run([exe, *cmd[1:]], check=True)


def upload(out: Path, tables: list[str]) -> None:
    # One prefix per table, so a rerun never touches the other paths into
    # bronze (extractor, clickstream, _dlq).
    for table in tables:
        run(["gcloud", "storage", "rsync", "--recursive", "--delete-unmatched-destination-objects",
             str(out / table), f"{BUCKET}/bronze/{table}"])


def create_external_tables(tables: list[str]) -> None:
    for table in tables:
        uri = f"{BUCKET}/bronze/{table}"
        if table in PARTITIONS:
            options = (
                f"uris = ['{uri}/*'], format = 'PARQUET', "
                f"hive_partition_uri_prefix = '{uri}'"
            )
            clause = " WITH PARTITION COLUMNS"
        else:
            options = f"uris = ['{uri}/*.parquet'], format = 'PARQUET'"
            clause = ""
        sql = (
            f"CREATE OR REPLACE EXTERNAL TABLE `{PROJECT}.{DATASET}.{table}_external`"
            f"{clause} OPTIONS ({options})"
        )
        run(["bq", f"--location={LOCATION}", "query", "--use_legacy_sql=false", sql])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--src", required=True, type=Path, help="folder of the CSV files")
    parser.add_argument("--out", type=Path, default=Path("out/bronze"))
    parser.add_argument("--upload", action="store_true", help="rsync out/ to the bucket")
    parser.add_argument("--external", action="store_true", help="create the BigQuery external tables")
    args = parser.parse_args()

    landed = []
    for path in sorted(args.src.glob("*.csv")):
        table = path.stem
        if table in SKIP_TABLES:
            print(f"skip   {table} (secret columns)")
            continue
        df = read_csv(path)
        files = write_table(table, df, args.out)
        landed.append(table)
        print(f"landed {table}: {len(df)} rows, {files} file(s)")
    if args.upload:
        upload(args.out, landed)
    if args.external:
        create_external_tables(landed)


if __name__ == "__main__":
    main()
