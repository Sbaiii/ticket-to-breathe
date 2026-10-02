-- resid must be exactly observed − pred_used, and pred_used must exist.
select sampling_point_id, ts_utc, no2, pred_used, resid
from {{ ref('fct_station_hour_deweathered') }}
where pred_used is null or abs(resid - (no2 - pred_used)) > 1e-9
