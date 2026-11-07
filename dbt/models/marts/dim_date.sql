-- Calendar dimension. One row per date, conformed across every fact table.
--
-- Carries est_jour_ouvrable so Power BI can compute attendance rates against
-- the correct denominator without re-implementing the holiday rule in DAX.

select * from {{ ref('int_calendrier') }}
