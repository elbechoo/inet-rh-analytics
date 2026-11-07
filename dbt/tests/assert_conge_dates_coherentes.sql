-- A leave request cannot end before it starts.
--
-- The database has a CHECK constraint for this, but the warehouse should not
-- assume the source is clean - the same model will later run against client
-- databases whose constraints we did not write.

select
    conge_id,
    employe_id,
    date_debut,
    date_fin
from {{ ref('fct_conge') }}
where date_fin < date_debut
