-- One row per department. sous_departement is optional in the source, so an
-- empty string and a null both mean "no sub-department" - normalise to null.

with source as (
    select * from {{ source('hr_app', 'Departement') }}
),

renamed as (
    select
        departement_id,
        trim(nom_departement) as nom_departement,
        nullif(trim(coalesce(sous_departement, '')), '') as sous_departement,
        trim(nom_departement)
            || coalesce(' - ' || nullif(trim(coalesce(sous_departement, '')), ''), '')
            as departement_complet
    from source
)

select * from renamed
