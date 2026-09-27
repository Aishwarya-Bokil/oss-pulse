with expected as (
    select count(distinct repo_name) as repo_count
    from {{ ref('stg_github_repos') }}
),

daily as (
    select snapshot_date, count(distinct repo_name) as repo_count
    from {{ ref('stg_github_repos') }}
    group by snapshot_date
)

select daily.snapshot_date, daily.repo_count, expected.repo_count as expected_repo_count
from daily
cross join expected
where daily.repo_count < expected.repo_count