-- GOLD: how many raw rows each file contributed vs how many survived cleaning
with bronze as (
    select
        _source_file,
        count(*)         as bronze_rows,
        min(_loaded_at)  as loaded_at
    from {{ source('bronze', 'yellow_trips_raw') }}
    group by _source_file
),

silver as (
    select _source_file, count(*) as silver_rows
    from {{ ref('stg_yellow_trips') }}
    group by _source_file
)

select
    b._source_file                                            as source_file,
    b.loaded_at,
    b.bronze_rows,
    coalesce(s.silver_rows, 0)                                as silver_rows,
    b.bronze_rows - coalesce(s.silver_rows, 0)                as rejected_rows,
    round(100 * (b.bronze_rows - coalesce(s.silver_rows, 0)) / nullif(b.bronze_rows, 0), 2) as rejected_pct
from bronze b
left join silver s using (_source_file)
