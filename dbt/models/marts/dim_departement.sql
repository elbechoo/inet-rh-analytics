-- Department dimension (Type 1 - the source keeps no history, so neither can we).

with departements as (
    select * from {{ ref('stg_departements') }}
),

effectif as (
    select departement_id, count(*) as nb_employes_actifs
    from {{ ref('stg_employes') }}
    where est_actif
    group by 1
)

select
    d.departement_id,
    d.nom_departement,
    d.sous_departement,
    d.departement_complet,
    coalesce(e.nb_employes_actifs, 0) as nb_employes_actifs
from departements d
left join effectif e using (departement_id)
