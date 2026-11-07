-- Grain: one row per leave request.
--
-- The warehouse recomputes the number of days charged rather than trusting
-- nb_jours from the application, and exposes the difference as ecart_jours so
-- the size of the problem stays visible.
--
-- ecart_jours is NOT a holiday count. It is simply applied minus correct, and
-- what it is made of depends on the source system:
--
--   production  nb_jours excluded weekends but not public holidays, so the gap
--               is holidays only - this is the bug the project set out to fix
--   seeded demo nb_jours is the raw calendar span, excluding neither, so the
--               gap is weekends plus holidays and is dominated by weekends
--
-- Read the gap through jours_weekend_couverts and jours_feries_couverts, which
-- decompose it, rather than quoting ecart_jours as a holiday figure. On the
-- demo database those two sum to ecart_jours exactly.

with conges as (
    select * from {{ ref('stg_conges') }}
),

calendrier as (
    select * from {{ ref('int_calendrier') }}
),

-- Count the working days actually covered by each request by expanding it
-- against the calendar. One row per request per day in range, then aggregated.
jours_par_conge as (
    select
        c.conge_id,
        count(*) filter (where cal.est_jour_ouvrable)                         as jours_ouvrables,
        count(*) filter (where cal.est_jour_ferie_chome and not cal.est_weekend) as jours_feries_couverts,
        count(*) filter (where cal.est_weekend)                               as jours_weekend_couverts
    from conges c
    join calendrier cal
      on cal.date_complete between c.date_debut and c.date_fin
    group by c.conge_id
)

select
    c.conge_id,
    d.date_id                       as date_debut_id,
    c.employe_id,
    e.departement_id,

    c.type_conge,
    c.statut,
    c.est_approuve,
    c.date_debut,
    c.date_fin,
    c.date_demande,
    c.date_validation,
    c.valide_par_employe_id,

    c.duree_calendaire_jours,
    coalesce(j.jours_weekend_couverts, 0) as jours_weekend_couverts,
    coalesce(j.jours_feries_couverts, 0)  as jours_feries_couverts,

    -- What the application charged, and what it should have charged.
    c.nb_jours_applique,
    coalesce(j.jours_ouvrables, 0)        as nb_jours_corrige,
    c.nb_jours_applique - coalesce(j.jours_ouvrables, 0) as ecart_jours,

    -- Only approved leave consumes a balance.
    case when c.est_approuve then coalesce(j.jours_ouvrables, 0) else 0 end
        as jours_consommes
from conges c
left join jours_par_conge j on j.conge_id = c.conge_id
left join calendrier d      on d.date_complete = c.date_debut
left join {{ ref('stg_employes') }} e on e.employe_id = c.employe_id
