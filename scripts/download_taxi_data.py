"""
Downloads official NYC TLC data.

  # yellow taxi, January-March 2025 -> data/incoming/ (the watcher picks them up)
  python scripts/download_taxi_data.py --year 2025 --months 1 2 3

  # whole year
  python scripts/download_taxi_data.py --year 2024

  # taxi zone lookup (CSV) -> dbt_project/seeds/
  python scripts/download_taxi_data.py --zones

Files are written as '.part' and renamed when complete, so the watcher only
ever sees finished files. TLC publishes monthly with ~2 months of delay.
"""
import argparse
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = "https://d37ci6vzurychx.cloudfront.net"


def download(url: str, dest: Path) -> bool:
    part = dest.with_name(f".{dest.name}.part")
    with requests.get(url, stream=True, timeout=60) as r:
        if r.status_code == 404:
            print(f"  not published: {url}")
            return False
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(part, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {dest.name}: {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="")
    print()
    part.rename(dest) 
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--months", type=int, nargs="*", default=list(range(1, 13)))
    ap.add_argument("--out", default="data/incoming")
    ap.add_argument("--zones", action="store_true", help="download taxi_zone_lookup.csv into dbt seeds")
    args = ap.parse_args()

    if args.zones:
        dest = PROJECT_ROOT / "dbt_project" / "seeds" / "taxi_zone_lookup.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        print("Downloading taxi zone lookup...")
        return 0 if download(f"{BASE}/misc/taxi_zone_lookup.csv", dest) else 1

    if not args.year:
        ap.error("--year is required (or use --zones)")

    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    for m in args.months:
        name = f"yellow_tripdata_{args.year}-{m:02d}.parquet"
        print(f"Downloading {name}")
        download(f"{BASE}/trip-data/{name}", out_dir / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
