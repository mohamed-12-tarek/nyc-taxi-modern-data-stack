{{
  config(
    materialized = 'incremental',
    unique_key = 'trip_id',
    incremental_strategy = 'merge'
  )
}}

-- SILVER: typed, validated, enriched and deduplicated yellow-taxi trips.
-- Incremental: each run only processes rows loaded into BRONZE since the last run.

with source as (

    select * from {{ source('bronze', 'yellow_trips_raw') }}
    {% if is_incremental() %}
    where _loaded_at > (select coalesce(max(_loaded_at), '1900-01-01'::timestamp_ntz) from {{ this }})
    {% endif %}

),

renamed as (

    select
        vendorid::int                         as vendor_id,
        tpep_pickup_datetime                  as pickup_datetime,
        tpep_dropoff_datetime                 as dropoff_datetime,
        passenger_count::int                  as passenger_count,
        trip_distance::number(10, 2)          as trip_distance,
        ratecodeid::int                       as ratecode_id,
        upper(trim(store_and_fwd_flag))       as store_and_fwd_flag,
        pulocationid::int                     as pickup_location_id,
        dolocationid::int                     as dropoff_location_id,
        payment_type::int                     as payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        coalesce(airport_fee, 0)              as airport_fee,
        coalesce(cbd_congestion_fee, 0)       as cbd_congestion_fee,
        total_amount,
        _source_file,
        _loaded_at
    from source

),

basic_validation as (

    -- TLC data is raw meter output: drop impossible / test records
    select *
    from renamed
    where pickup_datetime  >= to_timestamp_ntz('{{ var("min_valid_date") }}')
      and pickup_datetime  <  dateadd(day, 1, current_date())
      and dropoff_datetime >  pickup_datetime
      and trip_distance    >  0 and trip_distance <= 200
      and fare_amount      >  0
      and total_amount     >  0 and total_amount <= 1000
      and pickup_location_id  between 1 and 265
      and dropoff_location_id between 1 and 265
      and coalesce(passenger_count, 1) between 0 and 8

),

enriched as (

    select
        *,
        round(datediff('second', pickup_datetime, dropoff_datetime) / 60.0, 2) as trip_duration_min,
        round(trip_distance / nullif(datediff('second', pickup_datetime, dropoff_datetime) / 3600.0, 0), 2) as avg_speed_mph
    from basic_validation

)

select
    md5(
        coalesce(vendor_id::varchar, '') || '|' || pickup_datetime::varchar || '|' ||
        dropoff_datetime::varchar || '|' || pickup_location_id::varchar || '|' ||
        dropoff_location_id::varchar || '|' || fare_amount::varchar || '|' || total_amount::varchar
    )                                                    as trip_id,
    vendor_id,
    pickup_datetime,
    dropoff_datetime,
    pickup_datetime::date                                as pickup_date,
    date_trunc('month', pickup_datetime)::date           as pickup_month,
    hour(pickup_datetime)                                as pickup_hour,
    dayofweekiso(pickup_datetime)                        as day_of_week,
    dayname(pickup_datetime)                             as day_name,
    dayofweekiso(pickup_datetime) >= 6                   as is_weekend,
    passenger_count,
    trip_distance,
    trip_duration_min,
    avg_speed_mph,
    ratecode_id,
    case ratecode_id
        when 1 then 'Standard rate'
        when 2 then 'JFK'
        when 3 then 'Newark'
        when 4 then 'Nassau or Westchester'
        when 5 then 'Negotiated fare'
        when 6 then 'Group ride'
        else 'Other'
    end                                                  as ratecode_desc,
    store_and_fwd_flag,
    pickup_location_id,
    dropoff_location_id,
    payment_type,
    case payment_type
        when 0 then 'Flex Fare'
        when 1 then 'Credit card'
        when 2 then 'Cash'
        when 3 then 'No charge'
        when 4 then 'Dispute'
        when 5 then 'Unknown'
        when 6 then 'Voided'
        else 'Other'
    end                                                  as payment_type_desc,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    airport_fee,
    cbd_congestion_fee,
    total_amount,
    -- tips are only recorded for credit-card trips
    case when payment_type = 1 then round(tip_amount / fare_amount * 100, 2) end as tip_pct,
    _source_file,
    _loaded_at
from enriched
where trip_duration_min between 1 and 1440     -- 1 minute .. 24 hours
  and avg_speed_mph <= 100
-- keep only the latest version of each trip (handles re-sent / overlapping files)
qualify row_number() over (partition by trip_id order by _loaded_at desc) = 1
