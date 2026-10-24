-- SILVER: TLC taxi zone dimension (from the taxi_zone_lookup seed)
select
    locationid::int         as location_id,
    nullif(trim(borough), '')      as borough,
    nullif(trim(zone), '')         as zone,
    nullif(trim(service_zone), '') as service_zone
from {{ ref('taxi_zone_lookup') }}
