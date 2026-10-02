-- ratio_pct = 100 × (sum observed / sum predicted − 1); null exactly when sum predicted ≤ 0.
select sampling_point_id, local_date, sum_obs, sum_pred, ratio_pct
from {{ ref('fct_station_day_resid') }}
where (ratio_pct is null) != ratio_guarded
   or abs(ratio_pct - 100 * (sum_obs / sum_pred - 1)) > 1e-9
