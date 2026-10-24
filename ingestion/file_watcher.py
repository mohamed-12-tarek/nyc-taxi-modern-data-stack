"""
Watches data/incoming/. When a new .parquet lands, it triggers the Airflow DAG
`nyc_taxi_pipeline` through Airflow's REST API, passing the file path.

Usage:  python ingestion/file_watcher.py [--backfill]
"""
import argparse
import logging
import os
import threading
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

INCOMING = PROJECT_ROOT / "data" / "incoming"
AIRFLOW_URL = os.getenv("AIRFLOW_API_URL", "http://localhost:8080")
AIRFLOW_AUTH = (os.getenv("AIRFLOW_API_USER", "admin"), os.getenv("AIRFLOW_API_PASSWORD", "admin"))
DAG_ID = "nyc_taxi_pipeline"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("watcher")

_in_flight: set[str] = set()
_lock = threading.Lock()


def wait_until_stable(path: Path, checks: int = 3, interval: float = 2.0) -> bool:
    last, stable = -1, 0
    while stable < checks:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last and size > 0:
            stable += 1
        else:
            stable, last = 0, size
        time.sleep(interval)
    return True


def trigger_dag(path: Path) -> None:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns"
    try:
        r = requests.post(url, json={"conf": {"file_path": rel}}, auth=AIRFLOW_AUTH, timeout=30)
        r.raise_for_status()
        log.info("Triggered DAG for %s -> run_id=%s", rel, r.json().get("dag_run_id"))
    except requests.RequestException as exc:
        log.error("Could not trigger Airflow for %s: %s", rel, exc)


def process(path: Path) -> None:
    key = str(path)
    with _lock:
        if key in _in_flight:
            return
        _in_flight.add(key)
    try:
        log.info("Detected new file: %s", path.name)
        if wait_until_stable(path):
            trigger_dag(path)
    finally:
        with _lock:
            _in_flight.discard(key)


class Handler(FileSystemEventHandler):
    def _handle(self, p: str, is_dir: bool) -> None:
        path = Path(p)
        if not is_dir and path.suffix.lower() == ".parquet":
            threading.Thread(target=process, args=(path,), daemon=True).start()

    def on_created(self, event):
        self._handle(event.src_path, event.is_directory)

    def on_moved(self, event):  
        self._handle(event.dest_path, event.is_directory)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help="trigger for files already in incoming/")
    args = parser.parse_args()

    INCOMING.mkdir(parents=True, exist_ok=True)
    if args.backfill:
        for f in sorted(INCOMING.glob("*.parquet")):
            threading.Thread(target=process, args=(f,), daemon=True).start()

    observer = Observer()
    observer.schedule(Handler(), str(INCOMING), recursive=False)
    observer.start()
    log.info("Watching %s  (Ctrl+C to stop)", INCOMING)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
