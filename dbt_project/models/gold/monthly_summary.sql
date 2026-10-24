-- GOLD: monthly totals with month-over-month growth
with monthly as (
    select
        pickup_month,
        count(*)                         as total_trips,
        sum(total_amount)                as total_revenue,
        round(avg(fare_amount), 2)       as avg_fare,
        round(avg(trip_distance), 2)     as avg_distance_miles
    from {{ ref('stg_yellow_trips') }}
    group by pickup_month
)

select
    *,
    round((total_trips - lag(total_trips) over (order by pickup_month))
          / nullif(lag(total_trips) over (order by pickup_month), 0) * 100, 2)      as trips_mom_pct,
    round((total_revenue - lag(total_revenue) over (order by pickup_month))
          / nullif(lag(total_revenue) over (order by pickup_month), 0) * 100, 2)    as revenue_mom_pct
from monthly
