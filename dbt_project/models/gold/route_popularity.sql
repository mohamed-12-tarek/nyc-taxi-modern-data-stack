-- GOLD: top 1000 pickup -> dropoff zone pairs
with routes as (
    select
        t.pickup_location_id,
        t.dropoff_location_id,
        coalesce(pz.zone, 'Unknown')   as pickup_zone,
        coalesce(dz.zone, 'Unknown')   as dropoff_zone,
        count(*)                       as trips,
        round(avg(t.fare_amount), 2)   as avg_fare,
        round(avg(t.trip_distance), 2) as avg_distance_miles,
        round(avg(t.trip_duration_min), 2) as avg_duration_min
    from {{ ref('stg_yellow_trips') }} t
    left join {{ ref('dim_zones') }} pz on t.pickup_location_id  = pz.location_id
    left join {{ ref('dim_zones') }} dz on t.dropoff_location_id = dz.location_id
    group by 1, 2, 3, 4
)

select *, row_number() over (order by trips desc) as route_rank
from routes
qualify route_rank <= 1000
