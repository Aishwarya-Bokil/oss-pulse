select
    repo_name,
    count(*) as null_count
from {{ ref('repo_growth_daily') }}
where stars_change is null
group by repo_name
having count(*) > 1