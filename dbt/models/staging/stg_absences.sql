-- One row per absence event.

with source as (
    select * from {{ source('hr_app', 'Absence') }}
),

renamed as (
    select
        absence_id,
        employe_id,
        date_absence,
        coalesce(justifiee, false) as est_justifiee,
        motif,
        statut,
        date_creation
    from source
)

select * from renamed
