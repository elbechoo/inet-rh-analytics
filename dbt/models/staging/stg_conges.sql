-- One row per leave request.
--
-- nb_jours is what the application charged against the employee's balance. The
-- warehouse recomputes the correct figure in fct_conge rather than trusting it,
-- because that column was wrong for any request spanning a public holiday.

with source as (
    select * from {{ source('hr_app', 'Conge') }}
),

renamed as (
    select
        conge_id,
        employe_id,
        type_conge,
        date_debut,
        date_fin,
        nb_jours        as nb_jours_applique,
        statut,
        statut = 'Approuvé' as est_approuve,
        commentaire,
        date_demande,
        date_validation,
        valide_par      as valide_par_employe_id,
        (date_fin - date_debut) + 1 as duree_calendaire_jours
    from source
)

select * from renamed
