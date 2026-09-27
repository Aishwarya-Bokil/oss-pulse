with source as (

    select * from {{ source('github', 'github_repos') }}

),

deduplicated as (

    select
        *,
        row_number() over (
            partition by repo_name, date(ingested_at)
            order by ingested_at desc
        ) as row_num
    from source

)

select
    repo_name,
    stars,
    forks,
    open_issues,
    watchers,
    ingested_at,
    date(ingested_at) as snapshot_date
from deduplicated
where row_num = 1