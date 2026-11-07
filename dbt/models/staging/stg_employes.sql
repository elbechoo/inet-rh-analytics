-- One row per employee. Rename to snake_case English, cast, no business logic.

with source as (
    select * from {{ source('hr_app', 'Employe') }}
),

renamed as (
    select
        employe_id,
        matricule,
        upper(trim(nom))    as nom,
        initcap(trim(prenom)) as prenom,
        trim(prenom) || ' ' || upper(trim(nom)) as nom_complet,
        sexe,
        lower(trim(adresse_mail)) as email,
        date_naissance,
        date_embauche,
        poste,
        type_contrat,
        statut,
        statut = 'Actif'    as est_actif,
        departement_id,
        manager_id,
        manager_id is not null as a_un_manager
    from source
)

select * from renamed
