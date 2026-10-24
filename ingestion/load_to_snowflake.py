"""
Usage:
  python ingestion/load_to_snowflake.py --file data/incoming/yellow_tripdata_2025-01.parquet
  python ingestion/load_to_snowflake.py            # loads every .parquet in data/incoming
"""
import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(PROJECT_ROOT))

from common.snowflake_conn import get_connection 

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("loader")

INCOMING = PROJECT_ROOT / "data" / "incoming"
PROCESSED = PROJECT_ROOT / "data" / "processed"
FAILED = PROJECT_ROOT / "data" / "failed"

COLUMN_MAP = [
    ("VENDORID",              "$1:VendorID::NUMBER"),
    ("TPEP_PICKUP_DATETIME",  "$1:tpep_pickup_datetime::TIMESTAMP_NTZ"),
    ("TPEP_DROPOFF_DATETIME", "$1:tpep_dropoff_datetime::TIMESTAMP_NTZ"),
    ("PASSENGER_COUNT",       "$1:passenger_count::FLOAT"),
    ("TRIP_DISTANCE",         "$1:trip_distance::FLOAT"),
    ("RATECODEID",            "COALESCE($1:RatecodeID, $1:RateCodeID)::FLOAT"),
    ("STORE_AND_FWD_FLAG",    "$1:store_and_fwd_flag::VARCHAR"),
    ("PULOCATIONID",          "$1:PULocationID::NUMBER"),
    ("DOLOCATIONID",          "$1:DOLocationID::NUMBER"),
    ("PAYMENT_TYPE",          "$1:payment_type::NUMBER"),
    ("FARE_AMOUNT",           "$1:fare_amount::NUMBER(18,2)"),
    ("EXTRA",                 "$1:extra::NUMBER(18,2)"),
    ("MTA_TAX",               "$1:mta_tax::NUMBER(18,2)"),
    ("TIP_AMOUNT",            "$1:tip_amount::NUMBER(18,2)"),
    ("TOLLS_AMOUNT",          "$1:tolls_amount::NUMBER(18,2)"),
    ("IMPROVEMENT_SURCHARGE", "$1:improvement_surcharge::NUMBER(18,2)"),
    ("TOTAL_AMOUNT",          "$1:total_amount::NUMBER(18,2)"),
    ("CONGESTION_SURCHARGE",  "$1:congestion_surcharge::NUMBER(18,2)"),
    ("AIRPORT_FEE",           "COALESCE($1:Airport_fee, $1:airport_fee)::NUMBER(18,2)"),
    ("CBD_CONGESTION_FEE",    "$1:cbd_congestion_fee::NUMBER(18,2)"),
]


def move_to(path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / path.name
    if dest.exists():
        dest = target_dir / f"{path.stem}_{datetime.now():%Y%m%d%H%M%S}{path.suffix}"
    shutil.move(str(path), str(dest))
    log.info("Moved %s -> %s", path.name, dest.relative_to(PROJECT_ROOT))


def load_file(conn, path: Path) -> int:
    cur = conn.cursor()

    log.info("PUT %s (%.1f MB)", path.name, path.stat().st_size / 1e6)
    cur.execute(
        f"PUT 'file://{path.as_posix()}' @BRONZE.RAW_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
    )

    insert_cols = ", ".join([c for c, _ in COLUMN_MAP] + ["_SOURCE_FILE", "_LOADED_AT"])
    select_exprs = ", ".join([e for _, e in COLUMN_MAP] + ["METADATA$FILENAME", "CURRENT_TIMESTAMP()"])

    log.info("COPY INTO BRONZE.YELLOW_TRIPS_RAW from %s", path.name)
    cur.execute(
        f"""
        COPY INTO BRONZE.YELLOW_TRIPS_RAW ({insert_cols})
        FROM (SELECT {select_exprs} FROM @BRONZE.RAW_STAGE)
        FILES = ('{path.name}')
        FILE_FORMAT = (FORMAT_NAME = 'BRONZE.PARQUET_FORMAT')
        ON_ERROR = 'ABORT_STATEMENT'
        """
    )
    rows = cur.fetchall()
    first = str(rows[0][0]) if rows else ""
    if first.startswith("Copy executed with 0 files"):
        log.warning("%s was already loaded before - skipped by COPY INTO", path.name)
        return 0
    loaded = sum(int(r[3]) for r in rows)  
    log.info("Loaded %s rows from %s", f"{loaded:,}", path.name)
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="", help="path (relative to project root or absolute)")
    args = parser.parse_args()

    if args.file:
        p = Path(args.file)
        files = [p if p.is_absolute() else PROJECT_ROOT / p]
    else:
        files = sorted(INCOMING.glob("*.parquet"))

    files = [f for f in files if f.exists()]
    if not files:
        log.warning("No files to load.")
        return 0

    conn = get_connection(role="LOADER_ROLE", warehouse="LOADING_WH", schema="BRONZE")
    failures = 0
    try:
        for f in files:
            try:
                load_file(conn, f)
                move_to(f, PROCESSED)
            except Exception:
                log.exception("Failed to load %s", f.name)
                move_to(f, FAILED)
                failures += 1
    finally:
        conn.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
