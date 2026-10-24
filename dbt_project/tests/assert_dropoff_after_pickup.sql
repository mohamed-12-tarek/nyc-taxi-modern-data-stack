-- Singular test: returns offending rows (test passes when 0 rows are returned)
select trip_id, pickup_datetime, dropoff_datetime
from {{ ref('stg_yellow_trips') }}
where dropoff_datetime <= pickup_datetime
