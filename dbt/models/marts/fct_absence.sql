-- Grain: one row per absence event.
--
-- est_sur_jour_ferie is deliberately carried rather than filtered out. An
-- absence recorded on a public holiday is a data-quality fault, not a real
-- absence, and surfacing it lets a dashboard show the problem instead of
-- silently inflating the absence rate. The test in
-- tests/assert_no_absence_on_jour_ferie.sql fails the build when any appear.

with absences as (
    select * from {{ ref('stg_absences') }}
),

calendrier as (
    select * from {{ ref('int_calendrier') }}
)

select
    a.absence_id,
    c.date_id,
    a.employe_id,
    e.departement_id,

    a.motif,
    a.statut,
    a.est_justifiee,

    c.est_weekend,
    c.est_jour_ferie_chome                     as est_sur_jour_ferie,
    c.nom_ferie,

    -- Only absences on an actual working day count toward the absence rate.
    case when c.est_jour_ouvrable then 1 else 0 end as nb_absences_reelles,
    1 as nb_absences_brutes
from absences a
join calendrier c on c.date_complete = a.date_absence
left join {{ ref('stg_employes') }} e on e.employe_id = a.employe_id
