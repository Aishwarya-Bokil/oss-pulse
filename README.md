# OSS Pulse

A data pipeline that tracks the "health" of popular open source GitHub repos over time — star trajectory, fork growth, and open-issue backlog trend — surfaced through a Streamlit dashboard.

Unlike one-shot repo health checkers (repohealth.com, OpenSSF Scorecard), this tracks a curated list of repos continuously and stores historical trends for comparison, rather than a single point-in-time snapshot.

## Stack

| Stage | Tool |
|---|---|
| Orchestration | Apache Airflow 3.x (Docker Compose) |
| Ingestion | Python + GitHub REST API |
| Warehouse | Google BigQuery |
| Transformation | dbt (containerized, BigQuery adapter) |
| Dashboard | Streamlit (containerized) |

Each stage runs in its own container. Airflow and dbt use bind-mounted code for fast local iteration; the dashboard bakes its code into the image, since it's the piece most likely to actually be deployed somewhere as a running service.

## Pipeline

```
GitHub API → Airflow DAG → BigQuery (raw) → dbt (staging + marts) → Streamlit
```

- **Ingestion** (`dags/github_ingest.py`): a daily Airflow DAG fetches stats for each tracked repo and batch-loads them into BigQuery in a single job per run, so a failure never leaves a partially-loaded day.
- **Staging** (`dbt/oss_pulse/models/staging/`): deduplicates raw rows down to one snapshot per repo per day.
- **Marts** (`dbt/oss_pulse/models/marts/`): computes day-over-day change in stars, forks, and open issues.
- **Dashboard** (`dashboard/app.py`): star/fork trajectory, open-issue backlog trend, and a "fastest growing" leaderboard, per tracked repo.

Data quality is enforced with 7 dbt tests — deduplication checks, null checks, and a daily-completeness check across all tracked repos.

## Running it locally

```bash
# Airflow
docker compose up -d

# dbt
docker compose -f docker-compose.dbt.yml run --rm dbt run
docker compose -f docker-compose.dbt.yml run --rm dbt test

# Dashboard
docker compose -f docker-compose.dashboard.yml up --build
```

Requires a `.env` (GitHub token, GCP project ID) and a GCP service account key under `config/` — both gitignored, not included.

## Engineering notes

A few real issues surfaced and fixed along the way, since this project prioritizes doing things the way production teams would over the fastest path:

- **BigQuery's free tier rejects streaming inserts.** Switched ingestion from `insert_rows_json` to a batch `load_table_from_json` job.
- **A per-repo load design caused partial, duplicated data** when a run was interrupted mid-way (diagnosed from Airflow task logs down to the exact failed API call). Fixed by fetching all repos first, then loading them as a single all-or-nothing batch.
- **GitHub's `watchers_count` field is a legacy alias for `stargazers_count`**, not real "watching" data — excluded from the dashboard rather than presented as an independent signal.
- **A `.gitignore` rule silently never worked** (`*.json  # comment` — `.gitignore` doesn't support trailing comments), which nearly let a GCP service account key get committed. Caught by GitHub's push protection before it ever reached the remote branch.

## Known limitations / roadmap

- One real, permanent data gap exists (2026-09-25, one repo) from an interrupted run, predating the fix above — trend charts tolerate missing days rather than assuming continuity.
- v1 intentionally ships with only what's cheaply available from GitHub's repo endpoint (stars, forks, open-issue count). PR velocity, issue resolution rate, and contributor trends — the original stretch goals — need new ingestion (pull requests, issue timestamps, contributors) and are planned for v2, along with a composite health score built on top of them.
- No CI/CD yet.
