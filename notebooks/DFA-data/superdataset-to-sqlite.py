#!/usr/bin/env python3
"""Load the DFA superdataset into a SQLite database.

Examples:

    python superdataset-to-sqlite.py merged_dfa_data_cleaned_2026_09_30.csv

    python superdataset-to-sqlite.py -d merged_dfa_data_cleaned_2026_09_30.csv

    python superdataset-to-sqlite.py -d data.xlsx -o my-superdataset.db
"""

import sqlite3
from pathlib import Path

import click
import pandas as pd

# file extension -> pandas reader
READERS = {
    ".csv": pd.read_csv,
    ".tsv": lambda path, **kw: pd.read_csv(path, sep="\t", **kw),
    ".xlsx": lambda path, **kw: pd.read_excel(path, engine="openpyxl", **kw),
    ".xls": lambda path, **kw: pd.read_excel(path, engine="xlrd", **kw),
}

# packages needed by the Excel readers
EXCEL_PACKAGES = {".xlsx": "openpyxl", ".xls": "xlrd"}

# ID columns are read as text so IDs like "00123" or "I-00003-1F-004"
# are not converted to numbers
TEXT_COLUMNS = ["Participant_id", "Participant_id_original"]

# columns to index (if present) for faster queries
INDEX_COLUMNS = ["source", "Participant_id"]


def read_data(path: Path) -> pd.DataFrame:
    """Read a csv, tsv, xlsx or xls file into a DataFrame."""
    ext = path.suffix.lower()
    if ext not in READERS:
        raise click.BadParameter(
            f"unsupported file type '{ext}'; use one of: {', '.join(READERS)}",
            param_hint="'-d' / '--data'",
        )
    dtype = {col: str for col in TEXT_COLUMNS}
    try:
        return READERS[ext](path, dtype=dtype)
    except ImportError as e:
        # e.g., reading .xls without xlrd installed
        package = EXCEL_PACKAGES.get(ext, "")
        raise click.ClickException(
            f"reading {ext} files requires the '{package}' package: pip install {package}"
        ) from e
    except Exception as e:
        raise click.ClickException(f"could not read {path}: {e}") from e


def write_sqlite(df: pd.DataFrame, output: Path, table: str) -> None:
    """Write the DataFrame to a table in the SQLite database (replacing the table)."""
    with sqlite3.connect(output) as con:
        df.to_sql(table, con, if_exists="replace", index=False)
        for col in INDEX_COLUMNS:
            if col in df.columns:
                con.execute(f'CREATE INDEX IF NOT EXISTS "idx_{table}_{col}" ON "{table}" ("{col}")')


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "data_file",
    required=False,
    metavar="[DATA]",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-d", "--data",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="superdataset file to load; types: csv, tsv, xlsx, xls "
         "(can also be given as the first argument, without -d)",
)
@click.option(
    "-o", "--output",
    default="superdataset.db",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="SQLite database to create",
)
@click.option(
    "-t", "--table",
    default="superdataset",
    show_default=True,
    help="name of the table to create (replaced if it already exists)",
)
def cli(data_file: Path, data: Path, output: Path, table: str) -> None:
    """Load the DFA superdataset into a SQLite database.

    DATA is the superdataset file to load (same as -d/--data).
    """
    # the data file can be given either as the first argument or with -d/--data
    if data_file and data and data_file.resolve() != data.resolve():
        raise click.UsageError("give the data file either as the first argument or with -d/--data, not both")
    data = data or data_file
    if data is None:
        raise click.UsageError("missing data file: give it as the first argument or with -d/--data")

    df = read_data(data)
    write_sqlite(df, output, table)
    click.echo(f"Loaded {len(df):,} rows and {len(df.columns)} columns from {data} "
               f"into table '{table}' in {output}")


if __name__ == "__main__":
    cli()
