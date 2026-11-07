-- Approved leave must consume at least one working day.
--
-- Zero means the request covered nothing but weekends and holidays, which is
-- not a real leave request - it is usually a data-entry error, and it silently
-- distorts the leave-consumption rate.

select
    conge_id,
    employe_id,
    date_debut,
    date_fin,
    jours_consommes
from {{ ref('fct_conge') }}
where est_approuve
  and jours_consommes <= 0
