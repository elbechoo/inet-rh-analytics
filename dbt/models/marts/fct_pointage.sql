-- Grain: one row per employee per worked day.
--
-- Joined to the calendar so every attendance metric can be measured against
-- working days rather than calendar days.

with pointages as (
    select * from {{ ref('stg_pointages') }}
),

calendrier as (
    select * from {{ ref('int_calendrier') }}
)

select
    p.pointage_id,
    c.date_id,
    p.employe_id,
    e.departement_id,

    p.heure_entree,
    p.heure_sortie,
    p.heures_travaillees,
    p.retard_minutes,
    p.est_en_retard,
    p.sortie_manquante,
    p.statut,

    c.est_jour_ouvrable,
    c.est_jour_ferie_chome,

    1 as nb_presences
from pointages p
join calendrier c on c.date_complete = p.date_pointage
left join {{ ref('stg_employes') }} e on e.employe_id = p.employe_id
