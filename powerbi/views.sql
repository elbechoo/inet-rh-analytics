-- =============================================================
-- iNET RH — Power BI Views
-- Run once against GestionRH_Intelligente
-- All views are idempotent (DROP + CREATE)
-- =============================================================

USE GestionRH_Intelligente;
GO

-- =============================================================
-- 1. vw_PBI_Employe  (dimension — used by all pages)
-- =============================================================
IF OBJECT_ID('vw_PBI_Employe', 'V') IS NOT NULL DROP VIEW vw_PBI_Employe;
GO
CREATE VIEW vw_PBI_Employe AS
SELECT
    e.employe_id,
    e.matricule,
    CONCAT(e.prenom, ' ', e.nom)          AS nom_complet,
    e.nom,
    e.prenom,
    e.sexe,
    e.poste,
    e.type_contrat,
    e.statut,
    e.date_embauche,
    DATEDIFF(YEAR, e.date_embauche, GETDATE())  AS anciennete_annees,
    d.nom_departement,
    d.sous_departement,
    d.departement_id
FROM Employe e
JOIN Departement d ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 2. vw_PBI_Pointage  (Page 2: Attendance)
-- =============================================================
IF OBJECT_ID('vw_PBI_Pointage', 'V') IS NOT NULL DROP VIEW vw_PBI_Pointage;
GO
CREATE VIEW vw_PBI_Pointage AS
SELECT
    p.pointage_id,
    p.employe_id,
    CONCAT(e.prenom, ' ', e.nom)          AS nom_complet,
    d.nom_departement,
    e.poste,
    p.date_pointage,
    YEAR(p.date_pointage)                 AS annee,
    MONTH(p.date_pointage)                AS mois,
    DATENAME(MONTH, p.date_pointage)      AS nom_mois,
    DATENAME(WEEKDAY, p.date_pointage)    AS jour_semaine,
    DATEPART(WEEK, p.date_pointage)       AS semaine,
    p.heure_entree,
    p.heure_sortie,
    p.duree_travail,
    p.retard_minutes,
    p.statut,
    CASE WHEN p.statut = 'En retard'        THEN 1 ELSE 0 END  AS est_en_retard,
    CASE WHEN p.statut = 'Présent'          THEN 1 ELSE 0 END  AS est_present,
    CASE WHEN p.statut = 'Sortie manquante' THEN 1 ELSE 0 END  AS sortie_manquante,
    CASE WHEN p.retard_minutes > 30         THEN 1 ELSE 0 END  AS retard_severe
FROM Pointage p
JOIN Employe   e ON p.employe_id    = e.employe_id
JOIN Departement d ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 3. vw_PBI_Absence  (Page 2: Absences)
-- =============================================================
IF OBJECT_ID('vw_PBI_Absence', 'V') IS NOT NULL DROP VIEW vw_PBI_Absence;
GO
CREATE VIEW vw_PBI_Absence AS
SELECT
    a.absence_id,
    a.employe_id,
    CONCAT(e.prenom, ' ', e.nom)          AS nom_complet,
    d.nom_departement,
    e.poste,
    a.date_absence,
    YEAR(a.date_absence)                  AS annee,
    MONTH(a.date_absence)                 AS mois,
    DATENAME(MONTH, a.date_absence)       AS nom_mois,
    DATENAME(WEEKDAY, a.date_absence)     AS jour_semaine,
    a.justifiee,
    a.motif,
    a.statut,
    CASE WHEN a.justifiee = 1 THEN 'Justifiée' ELSE 'Non justifiée' END  AS type_absence,
    -- Season
    CASE
        WHEN MONTH(a.date_absence) IN (6,7,8)   THEN 'Été'
        WHEN MONTH(a.date_absence) IN (12,1,2)  THEN 'Hiver'
        WHEN MONTH(a.date_absence) IN (3,4,5)   THEN 'Printemps'
        ELSE 'Automne'
    END AS saison
FROM Absence a
JOIN Employe    e ON a.employe_id    = e.employe_id
JOIN Departement d ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 4. vw_PBI_Conge  (Page 3: Congés)
-- =============================================================
IF OBJECT_ID('vw_PBI_Conge', 'V') IS NOT NULL DROP VIEW vw_PBI_Conge;
GO
CREATE VIEW vw_PBI_Conge AS
SELECT
    c.conge_id,
    c.employe_id,
    CONCAT(e.prenom, ' ', e.nom)          AS nom_complet,
    d.nom_departement,
    e.poste,
    c.type_conge,
    c.date_debut,
    c.date_fin,
    c.nb_jours,
    c.statut,
    YEAR(c.date_debut)                    AS annee,
    MONTH(c.date_debut)                   AS mois,
    DATENAME(MONTH, c.date_debut)         AS nom_mois,
    sc.solde_annuel,
    sc.solde_utilise,
    (sc.solde_annuel - sc.solde_utilise)  AS solde_restant
FROM Conge c
JOIN Employe     e  ON c.employe_id    = e.employe_id
JOIN Departement d  ON e.departement_id = d.departement_id
LEFT JOIN SoldeConge sc ON sc.employe_id = c.employe_id;
GO

-- =============================================================
-- 5. vw_PBI_Formation  (Page 3: Formations)
-- =============================================================
IF OBJECT_ID('vw_PBI_Formation', 'V') IS NOT NULL DROP VIEW vw_PBI_Formation;
GO
CREATE VIEW vw_PBI_Formation AS
SELECT
    f.formation_id,
    f.titre,
    f.type_formation,
    f.organisateur,
    f.date_debut,
    f.date_fin,
    DATEDIFF(DAY, f.date_debut, f.date_fin) + 1  AS duree_jours,
    YEAR(f.date_debut)                            AS annee,
    MONTH(f.date_debut)                           AS mois,
    DATENAME(MONTH, f.date_debut)                 AS nom_mois,
    pf.employe_id,
    CONCAT(e.prenom, ' ', e.nom)                  AS nom_complet,
    d.nom_departement,
    e.poste,
    pf.presence,
    pf.score,
    CASE
        WHEN pf.score >= 85 THEN 'Excellent'
        WHEN pf.score >= 70 THEN 'Bien'
        WHEN pf.score >= 60 THEN 'Passable'
        WHEN pf.score IS NULL THEN 'Absent'
        ELSE 'Insuffisant'
    END AS mention
FROM Formation f
JOIN PresenceFormation pf ON f.formation_id  = pf.formation_id
JOIN Employe           e  ON pf.employe_id   = e.employe_id
JOIN Departement       d  ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 6. vw_PBI_Mission  (Page 4: Missions)
-- =============================================================
IF OBJECT_ID('vw_PBI_Mission', 'V') IS NOT NULL DROP VIEW vw_PBI_Mission;
GO
CREATE VIEW vw_PBI_Mission AS
SELECT
    m.mission_id,
    m.employe_id,
    CONCAT(e.prenom, ' ', e.nom)               AS nom_complet,
    d.nom_departement,
    e.poste,
    m.lieu,
    m.type_mission,
    m.role,
    m.statut,
    m.date_debut,
    m.date_fin,
    DATEDIFF(DAY, m.date_debut, m.date_fin) + 1 AS duree_jours,
    YEAR(m.date_debut)                           AS annee,
    MONTH(m.date_debut)                          AS mois,
    DATENAME(MONTH, m.date_debut)                AS nom_mois,
    CASE
        WHEN m.lieu IN ('Paris','Lyon','Tunis','Casablanca','Dubaï')
        THEN 'International' ELSE 'National'
    END AS portee
FROM Mission     m
JOIN Employe     e ON m.employe_id    = e.employe_id
JOIN Departement d ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 7. vw_PBI_AlerteIA  (Page 4: AI Alerts)
-- =============================================================
IF OBJECT_ID('vw_PBI_AlerteIA', 'V') IS NOT NULL DROP VIEW vw_PBI_AlerteIA;
GO
CREATE VIEW vw_PBI_AlerteIA AS
SELECT
    al.alerte_id,
    al.employe_id,
    CONCAT(e.prenom, ' ', e.nom)          AS nom_complet,
    d.nom_departement,
    e.poste,
    al.type_alerte,
    al.niveau,
    al.message,
    al.date_alerte,
    YEAR(al.date_alerte)                  AS annee,
    MONTH(al.date_alerte)                 AS mois,
    DATENAME(MONTH, al.date_alerte)       AS nom_mois,
    al.est_lue,
    CASE al.niveau
        WHEN 'Critique' THEN 3
        WHEN 'Moyen'    THEN 2
        ELSE 1
    END AS niveau_ordre
FROM AlerteIA    al
JOIN Employe     e  ON al.employe_id    = e.employe_id
JOIN Departement d  ON e.departement_id = d.departement_id;
GO

-- =============================================================
-- 8. vw_PBI_KPI_Mensuel  (Page 1: Executive monthly trend)
-- =============================================================
IF OBJECT_ID('vw_PBI_KPI_Mensuel', 'V') IS NOT NULL DROP VIEW vw_PBI_KPI_Mensuel;
GO
CREATE VIEW vw_PBI_KPI_Mensuel AS
SELECT
    YEAR(p.date_pointage)                  AS annee,
    MONTH(p.date_pointage)                 AS mois,
    DATENAME(MONTH, p.date_pointage)       AS nom_mois,
    d.nom_departement,
    COUNT(*)                               AS nb_pointages,
    SUM(CASE WHEN p.statut = 'Présent'          THEN 1 ELSE 0 END) AS nb_presents,
    SUM(CASE WHEN p.statut = 'En retard'        THEN 1 ELSE 0 END) AS nb_retards,
    SUM(CASE WHEN p.statut = 'Sortie manquante' THEN 1 ELSE 0 END) AS nb_sortie_manquante,
    AVG(CAST(p.duree_travail AS FLOAT))    AS moy_heures_jour,
    AVG(CAST(p.retard_minutes AS FLOAT))   AS moy_retard_min,
    ROUND(
        100.0 * SUM(CASE WHEN p.statut = 'Présent' THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2)    AS taux_presence_pct,
    ROUND(
        100.0 * SUM(CASE WHEN p.statut = 'En retard' THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2)    AS taux_retard_pct
FROM Pointage    p
JOIN Employe     e ON p.employe_id    = e.employe_id
JOIN Departement d ON e.departement_id = d.departement_id
GROUP BY
    YEAR(p.date_pointage),
    MONTH(p.date_pointage),
    DATENAME(MONTH, p.date_pointage),
    d.nom_departement;
GO

-- =============================================================
-- 9. vw_PBI_Absence_Mensuel  (Page 1 + 2: absence trend)
-- =============================================================
IF OBJECT_ID('vw_PBI_Absence_Mensuel', 'V') IS NOT NULL DROP VIEW vw_PBI_Absence_Mensuel;
GO
CREATE VIEW vw_PBI_Absence_Mensuel AS
SELECT
    YEAR(a.date_absence)                  AS annee,
    MONTH(a.date_absence)                 AS mois,
    DATENAME(MONTH, a.date_absence)       AS nom_mois,
    d.nom_departement,
    COUNT(*)                              AS nb_absences,
    SUM(CASE WHEN a.justifiee = 1 THEN 1 ELSE 0 END) AS nb_justifiees,
    SUM(CASE WHEN a.justifiee = 0 THEN 1 ELSE 0 END) AS nb_non_justifiees
FROM Absence     a
JOIN Employe     e ON a.employe_id    = e.employe_id
JOIN Departement d ON e.departement_id = d.departement_id
GROUP BY
    YEAR(a.date_absence),
    MONTH(a.date_absence),
    DATENAME(MONTH, a.date_absence),
    d.nom_departement;
GO

PRINT 'All Power BI views created successfully.';
GO
