-- Nobody should have a clock-in on a Saturday or Sunday.
--
-- Weekend work is not part of this company's model, so a row here means either
-- a badly configured terminal or a date parsed wrongly on import. Either way
-- it skews worked-hours totals and should be investigated rather than averaged
-- into the numbers.

select
    p.pointage_id,
    p.employe_id,
    d.date_complete,
    d.nom_jour
from {{ ref('fct_pointage') }} p
join {{ ref('dim_date') }} d using (date_id)
where d.est_weekend
