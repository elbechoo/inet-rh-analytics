-- Does the public holiday over-charging bug appear in THIS dataset?
--
-- fct_conge.ecart_jours is what the application charged minus what the calendar
-- says it should have charged. A positive value means the employee paid for a
-- public holiday out of their own leave balance.
--
-- Run against whichever database you want to characterise:
--   docker compose cp dbt\analyses\verif_ecart_conges.sql db:/tmp/v.sql
--   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atf /tmp/v.sql'

select 'conges_total='        || count(*)
    || '  approuves='         || count(*) filter (where est_approuve)
    || '  sur_charges='       || count(*) filter (where ecart_jours > 0)
    || '  jours_en_trop='     || coalesce(sum(ecart_jours) filter (where ecart_jours > 0), 0)
    || '  feries_couverts='   || coalesce(sum(jours_feries_couverts), 0)
    || '  consommes_zero='    || count(*) filter (where est_approuve and jours_consommes <= 0)
  from analytics_marts.fct_conge;
