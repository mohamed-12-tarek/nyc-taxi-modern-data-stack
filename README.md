

<h1 align="center">NYC Taxi Platform</h1>

<p align="center">
  <b>An event-driven modern data stack.</b><br>
  Drop a TLC Parquet file in a folder and get clean, tested, analytics-ready data in Snowflake, an automated insights report and a Streamlit app for end users.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg"></a>
  <img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Snowflake" src="https://img.shields.io/badge/Snowflake-warehouse-29B5E8?logo=snowflake&logoColor=white">
  <img alt="dbt" src="https://img.shields.io/badge/dbt-transformations-FF694A?logo=dbt&logoColor=white">
  <img alt="Airflow 2.10" src="https://img.shields.io/badge/Airflow-2.10-017CEE?logo=apacheairflow&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white">
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#getting-started">Getting started</a> ·
  <a href="#data-model">Data model</a> ·
  <a href="#security">Security</a> ·
  <a href="#roadmap">Roadmap</a> ·
  <a href="#license">License</a>
</p>

---

<p align="center">
  <img width="1280" height="640" alt="banner" src="https://github.com/user-attachments/assets/ae49b620-630d-4af1-8957-ff6f0f4aa75a" />
</p>


## Overview

This project turns the official **NYC TLC yellow-taxi trip records** into analytics-ready data using the **medallion architecture** (Bronze, Silver, Gold) on **Snowflake**.

Everything is automated and event-driven:

1. A new Parquet file lands in `data/incoming/`.
2. A file watcher detects it and triggers an **Airflow** DAG through the REST API.
3. The file is loaded into the **Bronze** layer in Snowflake.
4. **dbt** cleans and models it into **Silver** and **Gold**, running data-quality tests on the way.
5. An insights job renders a dashboard, and a **Streamlit** app lets end users explore the results.

### Highlights

- **Event-driven.** No schedules and no manual steps: a file arrives, the pipeline runs.
- **Idempotent and incremental.** Snowflake load history prevents double loading, and the Silver model merges only newly loaded rows.
- **Data quality built in.** Explicit cleaning rules, dbt tests and a per-file rejection report (`data_quality_by_file`).
- **Secure by default.** Passwordless key-pair authentication, three least-privilege roles, dedicated warehouses and a credit-capped resource monitor.
- **Reproducible.** Locked Python dependencies with [uv](https://docs.astral.sh/uv/), Airflow in Docker, and a single SQL script for the Snowflake environment.

---

## Architecture

<p align="center">
  <img width="1600" height="900" alt="architecture" src="https://github.com/user-attachments/assets/83156ead-37ec-4249-99c7-adbf73c95c87" />
</p>


### Tech stack

| Layer | Technology | Responsibility |
|---|---|---|
| Source | NYC TLC (Parquet, CSV) | Monthly yellow-taxi trips and the taxi zone lookup |
| Ingestion | Python, `watchdog` | Detects stable new files, triggers the DAG, loads files to Snowflake |
| Orchestration | Apache Airflow 2.10 (Docker) | Event-driven DAG, one run at a time, retries and timeouts |
| Warehouse | Snowflake | BRONZE / SILVER / GOLD schemas, three dedicated warehouses |
| Transformation | dbt (`dbt-snowflake`) | Incremental Silver, Gold metrics, seeds, macros, tests |
| Serving | Streamlit, Python | Self-service app and an automated dashboard |
| Tooling | uv, Docker Compose | Locked environments and containers |

### Pipeline stages

| # | Stage | What happens |
|---|---|---|
| 1 | **Ingest** | TLC publishes monthly Parquet files; `scripts/download_taxi_data.py` downloads them atomically (`.part` file, renamed when complete) |
| 2 | **Detect** | `watchdog` waits until the file size is stable, then calls the Airflow REST API with the file path |
| 3 | **Load** | `PUT` to an internal stage, then `COPY INTO` the Bronze table (raw data, loaded once) |
| 4 | **Clean** | dbt builds `STG_YELLOW_TRIPS` (typed, validated, enriched, deduplicated) and `DIM_ZONES` |
| 5 | **Model** | dbt builds seven Gold tables and runs tests |
| 6 | **Serve** | Insights dashboard and the Streamlit app read the curated data |

### Airflow DAG: `nyc_taxi_pipeline`

```
load_to_bronze > dbt_seed_zones > dbt_run_silver > dbt_test_silver > dbt_run_gold > dbt_test_gold > generate_insights
```

- Triggered by the watcher with `{"file_path": "data/incoming/<file>.parquet"}`; a manual trigger loads every file waiting in `data/incoming/`.
- `max_active_runs=1` keeps files ordered; tasks retry once after two minutes and time out after two hours.
- dbt and the Snowflake connector live in an isolated virtual environment inside the Airflow image, avoiding dependency conflicts.

---

## Getting started

### Prerequisites

| Tool | Notes |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python environment and task runner |
| [Docker](https://docs.docker.com/get-docker/) + Compose | Runs Airflow. On Windows use WSL2 |
| `openssl`, `curl` | Key generation and downloads |
| A [Snowflake](https://signup.snowflake.com/) account | A trial account is enough |

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/nyc-taxi-platform.git
cd nyc-taxi-platform
uv sync
```

### 2. Create the key pair

The pipeline authenticates to Snowflake with an RSA key pair (no password). Keys are git-ignored.

```bash
mkdir -p keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt
openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub
chmod 600 keys/rsa_key.p8

# print the public key on one line (paste it into the SQL script in the next step)
grep -v '^-----' keys/rsa_key.pub | tr -d '\n'
```

### 3. Set up Snowflake

1. Open `snowflake/01_setup.sql`.
2. Replace the value in `ALTER USER PIPELINE_USER SET RSA_PUBLIC_KEY = '...'` with your public key from step 2.
3. In Snowsight, paste the script into a worksheet and choose **Run All** (the script switches roles, so run it as `ACCOUNTADMIN`).

Verify:

```sql
SHOW SCHEMAS IN DATABASE NYC_TAXI_DB;   -- BRONZE, SILVER, GOLD
DESC USER PIPELINE_USER;                -- RSA_PUBLIC_KEY_FP must not be empty
```

### 4. Configure the environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
SNOWFLAKE_ACCOUNT=MYORG-MYACCOUNT   # Snowsight > account menu > "Copy account identifier"
SNOWFLAKE_USER=PIPELINE_USER
SNOWFLAKE_DATABASE=NYC_TAXI_DB
AIRFLOW_UID=1000                    # output of `id -u` on Linux/macOS
```

Check that dbt can connect:

```bash
cd dbt_project
uv run --env-file ../.env dbt debug --profiles-dir .
cd ..
```

You should see `All checks passed!`.

### 5. Start Airflow

```bash
docker compose up --build -d
```

Open <http://localhost:8080> (user `admin`, password `admin`; change these for anything beyond local use). The `nyc_taxi_pipeline` DAG is enabled automatically.

### 6. Start the watcher and feed it data

In one terminal:

```bash
uv run python ingestion/file_watcher.py
```

In another:

```bash
# taxi zone lookup (dbt seed), only needed once
uv run python scripts/download_taxi_data.py --zones

# one month of yellow-taxi trips (about 60 MB)
uv run python scripts/download_taxi_data.py --year 2025 --months 1
```

The watcher logs `Detected new file` and `Triggered DAG`; follow the run in the Airflow **Grid** view. When it finishes you will find:

- `reports/dashboard.png` and `reports/summary.md`
- the processed file in `data/processed/`
- data in `NYC_TAXI_DB.BRONZE`, `SILVER` and `GOLD` (see `snowflake/02_verify.sql`)

> **Tip:** start with a single month, then add more. The Silver model is incremental, so each new file only processes its own rows.

### 7. Run the Streamlit app

<!-- Update the path below to match where the app lives in your repository, and add a screenshot at docs/images/streamlit.png -->

```bash
uv run streamlit run streamlit_app/app.py
```

The app gives end users a self-service view of the curated data without writing SQL.

---

## Data model

<p align="center">
  <img width="1280" height="720" alt="medallion" src="https://github.com/user-attachments/assets/cc3fae4a-3e5c-403a-ba21-67c346809b29" />
</p>

| Schema | Objects |
|---|---|
| `NYC_TAXI_DB.BRONZE` | `YELLOW_TRIPS_RAW` table, `RAW_STAGE` internal stage, `PARQUET_FORMAT` file format |
| `NYC_TAXI_DB.SILVER` | `STG_YELLOW_TRIPS` (incremental), `DIM_ZONES`, `TAXI_ZONE_LOOKUP` (seed) |
| `NYC_TAXI_DB.GOLD` | Seven metric tables (below) |

### Silver validation rules

| Rule | Condition |
|---|---|
| Valid period | Pick-up on or after `2019-01-01` (dbt var `min_valid_date`) and not in the future |
| Chronology | Drop-off strictly after pick-up |
| Distance | Greater than 0 and at most 200 miles |
| Amounts | Fare greater than 0; total greater than 0 and at most 1,000 USD |
| Zones | Pick-up and drop-off location IDs between 1 and 265 |
| Passengers | Between 0 and 8 (missing values are kept) |
| Duration and speed | 1 minute to 24 hours; average speed up to 100 mph |
| Deduplication | Latest load wins per `trip_id` (hash of vendor, times, zones and amounts) |

Derived columns include trip duration, average speed, pick-up date/month/hour/weekday, weekend flag, payment type and rate code descriptions, and tip percentage (credit-card trips only).

### Gold tables

| Model | Grain | Key measures |
|---|---|---|
| `daily_trips` | Day | Trips, passengers, miles, fare / tip / total revenue, averages |
| `monthly_summary` | Month | Trips, revenue, average fare, month-over-month growth |
| `hourly_demand` | Weekday x hour | Trips, average fare, distance and speed (heatmap) |
| `zone_performance` | Pick-up zone | Trips, revenue, average fare, tip %, rank |
| `payment_analysis` | Payment type | Trips, revenue, average fare and tip, share of trips |
| `route_popularity` | Pick-up and drop-off pair | Top 1,000 routes with average fare, distance, duration |
| `data_quality_by_file` | Source file | Raw rows, valid rows, rejected rows and % |

### Tests

- `unique` and `not_null` on the trip key, zone key and every Gold grain
- `accepted_values` on payment type
- `relationships` from trips to zones (warning severity)
- A singular test failing if any trip drops off before it picks up

Run them manually:

```bash
cd dbt_project
uv run --env-file ../.env dbt run  --select silver --profiles-dir .
uv run --env-file ../.env dbt test --select gold   --profiles-dir .
```

---

## Security

| Role | Used by | Privileges |
|---|---|---|
| `LOADER_ROLE` | Ingestion script | Read/write the Bronze stage, insert/select on Bronze tables, uses `LOADING_WH` |
| `TRANSFORMER_ROLE` | dbt | Reads Bronze, owns and writes Silver and Gold, uses `TRANSFORM_WH` |
| `ANALYST_ROLE` | Insights and serving layer | Read-only on Gold, uses `ANALYTICS_WH` |

- **Key-pair authentication** with a `TYPE = SERVICE` user; no passwords in the repo.
- **Secrets stay local:** `.env` and `keys/` are git-ignored; dbt reads credentials from environment variables.
- **Cost guardrails:** all warehouses are XSMALL with a 60-second auto-suspend, and a resource monitor caps usage at 20 credits per month (notify at 80%, suspend at 100%).
- **Lineage:** every raw row stores its source file and load time.

> Never commit `keys/` or `.env`. If a private key is ever exposed, rotate it with `ALTER USER PIPELINE_USER SET RSA_PUBLIC_KEY = '...'`.

---

## Repository structure

<details>
<summary>Show the tree</summary>

```
nyc-taxi-platform/
├── README.md
├── LICENSE
├── pyproject.toml, uv.lock          # Python dependencies (uv)
├── docker-compose.yml               # Airflow + Postgres
├── .env.example                     # Template for local settings
├── data/
│   ├── incoming/                    # Drop zone for new .parquet files
│   ├── processed/                   # Successfully loaded files
│   └── failed/                      # Files that failed to load
├── docs/images/                     # README images
├── snowflake/
│   ├── 01_setup.sql                 # Roles, warehouses, DB, schemas, grants, user, monitor
│   └── 02_verify.sql                # Post-run sanity checks
├── common/snowflake_conn.py         # Shared Snowflake connection (key-pair auth)
├── ingestion/
│   ├── file_watcher.py              # Watches data/incoming, triggers Airflow
│   └── load_to_snowflake.py         # PUT + COPY INTO Bronze, archives the file
├── scripts/download_taxi_data.py    # Downloads TLC Parquet files and the zone lookup
├── dbt_project/
│   ├── models/silver/               # stg_yellow_trips, dim_zones
│   ├── models/gold/                 # Seven metric tables
│   ├── seeds/                       # taxi_zone_lookup.csv
│   ├── macros/                      # Schema naming override
│   └── tests/                       # Singular data tests
├── airflow/
│   ├── Dockerfile                   # Airflow image + isolated tooling venv (built with uv)
│   └── dags/nyc_taxi_pipeline.py    # The orchestration DAG
├── insights/generate_insights.py    # Dashboard + KPI summary from Gold
└── reports/                         # Generated output (git-ignored)
```

</details>

---

## Troubleshooting

<details>
<summary>Common issues</summary>

| Symptom | Likely cause |
|---|---|
| `JWT token is invalid` | Wrong account identifier, public key not set on `PIPELINE_USER`, or the setup SQL was not fully run |
| `Role ... is not granted to this user` | The grants at the end of `01_setup.sql` did not run |
| Watcher returns 401 or connection refused | Airflow is still starting, or `AIRFLOW_API_*` in `.env` is wrong |
| DAG not visible | Check "DAG Import Errors" at the top of the Airflow UI |
| `dim_zones` fails | `dbt_project/seeds/taxi_zone_lookup.csv` is missing: run `download_taxi_data.py --zones` |
| `COPY INTO` fails on a column | TLC changed a column name; update `COLUMN_MAP` in `ingestion/load_to_snowflake.py` |
| Permission denied on `keys/` or `data/` inside Docker | `AIRFLOW_UID` does not match `id -u` |

</details>

---

## Roadmap

- [ ] Alerting on DAG or dbt test failures (email / Slack)
- [ ] Green taxi and high-volume for-hire vehicle (Uber/Lyft) data
- [ ] Incremental Gold models as history grows
- [ ] CI: `dbt parse` and tests on every pull request
- [ ] Interactive documentation with `dbt docs`

## Project status

- [x] Snowflake environment, loader, watcher, downloader
- [x] dbt project (2 Silver models, 7 Gold models, seed, tests)
- [x] Airflow DAG and Docker setup
- [x] Insights dashboard and Streamlit app
- [x] Project scaffolding validated: Python and YAML checks, `uv sync`, `dbt parse`
- [ ] End-to-end run against a live Snowflake account on real TLC data

---

## Contributing

Contributions are welcome.

1. Fork the repository and create a feature branch.
2. Make your change and run `dbt parse` / `dbt test` where relevant.
3. Open a pull request describing what changed and why.

## License

Released under the [Apache License](LICENSE).

## Acknowledgements and disclaimer

- Trip data: [NYC Taxi & Limousine Commission (TLC) Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), publicly available. TLC publishes data with a delay of roughly two months and may adjust file schemas over time.
- This project is not affiliated with or endorsed by the NYC TLC, Snowflake, dbt Labs, the Apache Software Foundation or Streamlit. All product names and trademarks belong to their respective owners.
- Running the pipeline on Snowflake consumes credits; monitor your usage.
