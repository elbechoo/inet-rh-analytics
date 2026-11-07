-- Employee dimension (Type 1), denormalised with department and manager so a
-- report can slice without a second hop.
--
-- anciennete_mois is recomputed at build time rather than stored, so it never
-- goes stale between loads.

with employes as (
    select * from {{ ref('stg_employes') }}
),

departements as (
    select * from {{ ref('stg_departements') }}
)

select
    e.employe_id,
    e.matricule,
    e.nom,
    e.prenom,
    e.nom_complet,
    e.email,
    e.sexe,
    e.poste,
    e.type_contrat,
    e.statut,
    e.est_actif,
    e.date_embauche,
    e.date_naissance,

    d.departement_id,
    d.nom_departement,
    d.sous_departement,
    d.departement_complet,

    e.manager_id,
    m.nom_complet as manager_nom,

    -- Derived attributes, banded for slicing rather than left continuous.
    --
    -- age() is used rather than subtracting the dates: in Postgres date - date
    -- yields an integer count of days, not an interval, so extract() cannot be
    -- applied to it. age() returns a real interval, which also makes this exact
    -- calendar months instead of days divided by an average month length.
    (extract(year  from age(current_date, e.date_embauche)) * 12
   + extract(month from age(current_date, e.date_embauche)))::int
        as anciennete_mois,
    case
        when e.date_embauche > current_date - interval '1 year'  then '< 1 an'
        when e.date_embauche > current_date - interval '3 years' then '1-3 ans'
        when e.date_embauche > current_date - interval '5 years' then '3-5 ans'
        else '5 ans +'
    end as tranche_anciennete,
    case
        when e.date_naissance is null then 'Inconnu'
        when e.date_naissance > current_date - interval '30 years' then '< 30'
        when e.date_naissance > current_date - interval '40 years' then '30-39'
        when e.date_naissance > current_date - interval '50 years' then '40-49'
        else '50 +'
    end as tranche_age
from employes e
left join departements d on d.departement_id = e.departement_id
left join employes      m on m.employe_id    = e.manager_id
