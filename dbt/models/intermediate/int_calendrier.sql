{{ config(materialized='ephemeral') }}

-- The working-day calendar: every date in range, flagged weekend / holiday /
-- working day.
--
-- This model exists so that "is this a working day" is answered in exactly one
-- place. The original application defined it per-caller, which is how the rule
-- came to exclude weekends but not public holidays - leave spanning Aïd was
-- charged to the employee, and nobody absent on a holiday was recorded. Every
-- downstream fact joins here rather than re-deriving it.
--
-- A holiday only reduces the working-day count when est_chome is true: a
-- holiday the company chooses to work is still a working day.

with bounds as (
    select
        cast('{{ var("date_start") }}' as date) as date_min,
        cast('{{ var("date_end") }}'   as date) as date_max
),

spine as (
    select generate_series(
        (select date_min from bounds),
        (select date_max from bounds),
        interval '1 day'
    )::date as date_complete
),

feries as (
    select date_ferie, nom_ferie, type_ferie, est_chome
    from {{ ref('stg_jours_feries') }}
),

joined as (
    select
        s.date_complete,
        f.nom_ferie,
        f.type_ferie,
        coalesce(f.est_chome, false)                 as est_jour_ferie_chome,
        f.date_ferie is not null                     as est_jour_ferie,
        extract(isodow from s.date_complete) >= 6    as est_weekend
    from spine s
    left join feries f on f.date_ferie = s.date_complete
)

select
    cast(to_char(date_complete, 'YYYYMMDD') as integer) as date_id,
    date_complete,
    extract(year    from date_complete)::int  as annee,
    extract(quarter from date_complete)::int  as trimestre,
    extract(month   from date_complete)::int  as mois,
    to_char(date_complete, 'TMMonth')         as nom_mois,
    extract(week    from date_complete)::int  as semaine_iso,
    extract(day     from date_complete)::int  as jour,
    to_char(date_complete, 'TMDay')           as nom_jour,
    extract(isodow  from date_complete)::int  as jour_semaine_num,   -- 1=Mon
    est_weekend,
    est_jour_ferie,
    est_jour_ferie_chome,
    nom_ferie,
    type_ferie,

    -- The definition everything else depends on.
    (not est_weekend and not est_jour_ferie_chome) as est_jour_ouvrable,

    case extract(month from date_complete)
        when 12 then 'Hiver' when 1 then 'Hiver' when 2 then 'Hiver'
        when 3  then 'Printemps' when 4 then 'Printemps' when 5 then 'Printemps'
        when 6  then 'Été' when 7 then 'Été' when 8 then 'Été'
        else 'Automne'
    end as saison
from joined
