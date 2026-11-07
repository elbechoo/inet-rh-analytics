-- =============================================================
-- 002_perf_indexes.sql - hot-column indexes for the OLTP database
-- =============================================================
-- Run once against GestionRH_Intelligente. Idempotent: every CREATE
-- INDEX is guarded by an IF NOT EXISTS check so re-running is safe.
--
-- These indexes target the three slow dashboard endpoints:
--   * /pointages/kpis/global         (Pointage.statut + duree_travail)
--   * /pointages/kpis/departement    (Employe + Pointage join)
--   * /pointages/stats/evolution     (YEAR(date_pointage), YEAR(date_absence))
-- =============================================================

USE GestionRH_Intelligente;
GO

-- ── Pointage ──────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_employe_id')
    CREATE INDEX IX_Pointage_employe_id ON Pointage(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_date_pointage')
    CREATE INDEX IX_Pointage_date_pointage ON Pointage(date_pointage);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_statut')
    CREATE INDEX IX_Pointage_statut ON Pointage(statut)
    INCLUDE (employe_id, duree_travail, date_pointage);

-- ── Absence ───────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Absence_employe_id')
    CREATE INDEX IX_Absence_employe_id ON Absence(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Absence_date_absence')
    CREATE INDEX IX_Absence_date_absence ON Absence(date_absence);

-- ── Conge ─────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Conge_employe_id')
    CREATE INDEX IX_Conge_employe_id ON Conge(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Conge_date_debut')
    CREATE INDEX IX_Conge_date_debut ON Conge(date_debut);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Conge_statut')
    CREATE INDEX IX_Conge_statut ON Conge(statut);

-- ── Employe ───────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Employe_departement_statut')
    CREATE INDEX IX_Employe_departement_statut ON Employe(departement_id, statut);

-- ── PointageLog ───────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PointageLog_employe_ts')
    CREATE INDEX IX_PointageLog_employe_ts ON PointageLog(employe_id, timestamp_pointage DESC);

PRINT 'Performance indexes installed.';
GO
