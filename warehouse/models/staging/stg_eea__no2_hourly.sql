-- Valid hourly NO2 in UTC. ADR-003: raw `Start` is the hour start on a fixed UTC+01 clock,
-- so ts_utc = Start - 1 h for every mainland file. Only Validity codes listed in config.
with params as (
    select
        max(case when param = 'first_year' then value end)::int as first_year,
        max(case when param = 'last_year' then value end)::int as last_year
    from {{ ref('config_params') }}
),

raw as (
    select
        regexp_replace("Samplingpoint", '^[A-Z]{2}/', '') as sampling_point_id,
        "Start" - interval 1 hour as ts_utc,
        cast("Value" as double) as no2_ugm3,
        "Validity" as validity,
        "Verification" as verification
    from {{ source('raw', 'eea_e1a_no2_hourly') }}
)

select raw.*
from raw, params
where raw.validity in (select validity_code from {{ ref('config_valid_codes') }})
  and raw.ts_utc >= make_timestamp(params.first_year, 1, 1, 0, 0, 0)
  and raw.ts_utc < make_timestamp(params.last_year + 1, 1, 1, 0, 0, 0)
