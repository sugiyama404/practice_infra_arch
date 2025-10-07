# PostgreSQL UUID & Cross-Database ID Benchmark

This project benchmarks ID lookup latency across PostgreSQL, MySQL, and Redis for several identifier strategies, and drills into UUIDv4 vs UUIDv7 behaviour on PostgreSQL 18.

## Prerequisites

- macOS or Linux with Docker Desktop running
- [uv](https://github.com/astral-sh/uv) for Python environment management
- Python 3.11+

## Quick start

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Bring up the data stores:

```bash
docker compose up -d --remove-orphans
```

## Running the benchmark notebook

Open `id_benchmark.ipynb` in VS Code or Jupyter Lab and execute cells one-by-one. The notebook will:

1. Seed one million rows per identifier strategy in PostgreSQL and MySQL.
2. Populate Redis keys mirroring each ID format.
3. Execute 10,000 random lookups per dataset, capturing average and p95 latency.
4. Plot comparative results and export a `results.csv` summary.
5. Run a PostgreSQL-only workload to contrast UUIDv4 vs UUIDv7 insert/select/order performance, optionally verifying the ~3× improvement expectation for UUIDv7.

At the end, the notebook exports a copy named `uuid_benchmark_report.ipynb` to share results without intermediate output cells.

## Tuning knobs

You can downsize workloads for dry runs by overriding environment variables before launching the notebook:

- `RECORD_COUNT` — rows per table (default `1000000`)
- `LOOKUP_ITERATIONS` — random lookups per dataset (default `10000`)
- `BATCH_SIZE` — insert batch size (default `20000`)
- `UUID_WORKLOAD_ROWS` — rows for the PostgreSQL UUID comparison (default `200000`)

Set them via `export RECORD_COUNT=100000` (or use `.env`).

## Cleanup

```bash
docker compose down -v
```

> **Note:** The Compose file pins a `postgres:18beta1-alpine` image for UUIDv7 support. Switch to a GA tag when PostgreSQL 18 is officially released.
