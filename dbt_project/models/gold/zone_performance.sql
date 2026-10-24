-- GOLD: pickup-zone performance
select
    t.pickup_location_id,
    coalesce(z.borough, 'Unknown')   as borough,
    coalesce(z.zone, 'Unknown')      as zone,
    count(*)                         as trips,
    sum(t.total_amount)              as total_revenue,
    round(avg(t.fare_amount), 2)     as avg_fare,
    round(avg(t.trip_distance), 2)   as avg_distance_miles,
    round(avg(t.tip_pct), 2)         as avg_tip_pct,
    rank() over (order by count(*) desc) as trips_rank
from {{ ref('stg_yellow_trips') }} t
left join {{ ref('dim_zones') }} z
    on t.pickup_location_id = z.location_id
group by t.pickup_location_id, z.borough, z.zone
