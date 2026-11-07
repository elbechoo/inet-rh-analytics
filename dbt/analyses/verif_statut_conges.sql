-- Why does fct_conge report zero approved leave requests?
--
-- stg_conges derives est_approuve as (statut = 'Approuvé'). If that comparison
-- never matches, jours_consommes is always zero and
-- tests/assert_jours_consommes_positifs passes vacuously - it filters on
-- est_approuve, so an empty set of approved requests means an empty result set
-- and a green test that proves nothing.
--
-- Prints the exact stored bytes so an accent encoding mismatch (precomposed
-- U+00E9 vs decomposed e + U+0301) is visible rather than inferred.

select statut
    || '  n=' || count(*)
    || '  octets=' || encode(convert_to(statut, 'UTF8'), 'hex')
    || '  longueur=' || length(statut)
    || '  est_approuve=' || bool_or(statut = 'Approuvé')
  from analytics_staging.stg_conges
 group by statut
 order by count(*) desc;

-- Is ecart_jours really about public holidays?
-- If the over-charge total far exceeds the holidays covered, the gap is coming
-- from nb_jours itself being unreliable in seeded data, not from the holiday
-- rule. duree_calendaire_jours is the raw span including weekends.
select 'ecart_total=' || coalesce(sum(ecart_jours) filter (where ecart_jours > 0), 0)
    || '  feries_couverts=' || coalesce(sum(jours_feries_couverts), 0)
    || '  weekends_couverts=' || coalesce(sum(jours_weekend_couverts), 0)
    || '  nb_jours_depasse_la_duree=' || count(*) filter (where nb_jours_applique > duree_calendaire_jours)
  from analytics_marts.fct_conge;

-- A handful of raw rows: applique / duree_calendaire / corrige / feries.
-- If nb_jours_applique bears no relation to the span, it is seeded noise.
select 'echantillon  ' || string_agg(
           nb_jours_applique || '/' || duree_calendaire_jours
             || '/' || nb_jours_corrige || '/' || jours_feries_couverts,
           '   ' order by conge_id)
  from (select * from analytics_marts.fct_conge order by conge_id limit 10) s;
