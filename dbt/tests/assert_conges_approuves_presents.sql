{{ config(severity = 'warn') }}

-- Guard against vacuous test results.
--
-- assert_jours_consommes_positifs filters on est_approuve. If a dataset
-- contains no approved leave at all, that test returns an empty set and reports
-- PASS while having examined nothing - coverage that looks real and is not.
-- This happened: the seeded demo database held 1,122 leave requests and every
-- single one was 'En attente'.
--
-- Severity is warn rather than error on purpose. A database with no approved
-- leave is not corrupt - a brand new deployment legitimately has none - but it
-- does mean the approval-path tests downstream are not actually being
-- exercised, and that should be visible in the build output instead of being
-- silently mistaken for a clean run.

select
    'aucun conge approuve dans ce jeu de donnees' as probleme,
    count(*)                                      as conges_total,
    count(*) filter (where est_approuve)          as conges_approuves
from {{ ref('fct_conge') }}
having count(*) filter (where est_approuve) = 0
