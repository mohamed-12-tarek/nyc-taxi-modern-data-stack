-- GOLD: payment type mix and tipping behaviour (tips exist only for card trips)
with agg as (
    select
        payment_type_desc,
        count(*)                        as trips,
        sum(total_amount)               as total_revenue,
        round(avg(fare_amount), 2)      as avg_fare,
        round(avg(tip_amount), 2)       as avg_tip_amount,
        round(avg(tip_pct), 2)          as avg_tip_pct
    from {{ ref('stg_yellow_trips') }}
    group by payment_type_desc
)

select
    *,
    round(100 * trips / sum(trips) over (), 2) as share_of_trips_pct
from agg
