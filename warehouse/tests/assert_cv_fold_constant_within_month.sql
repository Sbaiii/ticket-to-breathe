-- ADR-007: cross-fitting blocks are whole local calendar months, so each station-month belongs to
-- exactly one fold.
select sampling_point_id, date_trunc('month', local_date) as month, count(distinct cv_fold) as folds
from {{ ref('fct_station_hour_deweathered') }}
where is_oof
group by all
having count(distinct cv_fold) != 1
