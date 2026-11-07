-- Public holidays. `chome` marks a day as non-working; a holiday the company
-- chooses to work is kept here but must not reduce the working-day count.

with source as (
    select * from {{ source('hr_app', 'JourFerie') }}
),

renamed as (
    select
        jour_ferie_id,
        date_ferie,
        nom         as nom_ferie,
        type_ferie,
        chome       as est_chome
    from source
)

select * from renamed
