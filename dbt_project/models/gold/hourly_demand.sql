-- GOLD: demand by day-of-week x hour (feeds the heatmap)
select
    day_of_week,
    day_name,
    pickup_hour,
    count(*)                         as total_trips,
    round(avg(fare_amount), 2)       as avg_fare,
    round(avg(trip_distance), 2)     as avg_distance_miles,
    round(avg(avg_speed_mph), 2)     as avg_speed_mph
from {{ ref('stg_yellow_trips') }}
group by day_of_week, day_name, pickup_hour
