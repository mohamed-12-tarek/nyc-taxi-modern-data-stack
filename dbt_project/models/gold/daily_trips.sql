-- GOLD: one row per day
select
    pickup_date,
    count(*)                              as total_trips,
    sum(passenger_count)                  as total_passengers,
    sum(trip_distance)                    as total_miles,
    sum(fare_amount)                      as fare_revenue,
    sum(tip_amount)                       as tips,
    sum(total_amount)                     as total_revenue,
    round(avg(fare_amount), 2)            as avg_fare,
    round(avg(trip_distance), 2)          as avg_distance_miles,
    round(avg(trip_duration_min), 2)      as avg_duration_min,
    round(avg(avg_speed_mph), 2)          as avg_speed_mph
from {{ ref('stg_yellow_trips') }}
group by pickup_date
