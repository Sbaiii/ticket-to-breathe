-- ADR-007: a daily outcome never mixes out-of-fold (pre-treatment) hours with post-treatment
-- hours predicted by the fold-model mean.
select sampling_point_id, local_date, valid_hours, oof_hours
from {{ ref('fct_station_day_resid') }}
where oof_hours not in (0, valid_hours)
