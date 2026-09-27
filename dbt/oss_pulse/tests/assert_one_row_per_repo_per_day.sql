select
    repo_name,
    snapshot_date,
    count(*) as row_count
from {{ ref('stg_github_repos') }}
group by repo_name, snapshot_date
having count(*) > 1