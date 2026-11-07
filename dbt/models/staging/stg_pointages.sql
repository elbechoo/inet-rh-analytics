-- One row per employee per worked day.
--
-- duree_travail is stored as a float of hours by the application. Keeping it
-- as-is and deriving minutes separately avoids rounding twice.

with source as (
    select * from {{ source('hr_app', 'Pointage') }}
),

renamed as (
    select
        pointage_id,
        employe_id,
        date_pointage,
        heure_entree,
        heure_debut_pause,
        heure_fin_pause,
        heure_sortie,
        duree_travail               as heures_travaillees,
        coalesce(retard_minutes, 0) as retard_minutes,
        coalesce(retard_minutes, 0) > 0 as est_en_retard,
        statut,
        heure_sortie is null        as sortie_manquante,
        date_creation
    from source
)

select * from renamed
