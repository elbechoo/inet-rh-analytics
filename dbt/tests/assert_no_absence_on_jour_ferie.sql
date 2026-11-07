-- No absence should be recorded on a non-working public holiday.
--
-- This is the bug that started the whole holiday project: absence detection
-- skipped weekends but not holidays, so every public holiday generated an
-- absence for the entire workforce. Those phantom absences inflated the
-- absence rate and were fed to the absenteeism model as real signal.
--
-- Encoding it as a test means it cannot come back silently. The test returns
-- offending rows; dbt fails the build if there are any.

select
    f.absence_id,
    f.employe_id,
    d.date_complete,
    d.nom_ferie
from {{ ref('fct_absence') }} f
join {{ ref('dim_date') }} d using (date_id)
where f.est_sur_jour_ferie
