-- The companion no-BLH model may only be used inside the documented BLH gap
-- (2024-01-01 → 2024-06-30, ADR-005/006).
select sampling_point_id, ts_utc
from {{ ref('fct_station_hour_deweathered') }}
where pred_source = 'noblh'
  and not (ts_utc >= timestamp '2024-01-01' and ts_utc < timestamp '2024-07-01')
