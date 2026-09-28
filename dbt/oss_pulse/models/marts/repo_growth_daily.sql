with staged as (

    select * from {{ ref('stg_github_repos') }}

),

with_previous_day as (

    select
        *,
        lag(stars) over (partition by repo_name order by snapshot_date) as prev_stars,
        lag(forks) over (partition by repo_name order by snapshot_date) as prev_forks,
        lag(open_issues) over (partition by repo_name order by snapshot_date) as prev_open_issues
    from staged

)

select
    repo_name,
    snapshot_date,
    stars,
    forks,
    open_issues,
    stars - prev_stars as stars_change,
    safe_divide(stars - prev_stars, prev_stars) as stars_pct_change,
    forks - prev_forks as forks_change,
    safe_divide(forks - prev_forks, prev_forks) as forks_pct_change,
    open_issues - prev_open_issues as open_issues_change
from with_previous_day