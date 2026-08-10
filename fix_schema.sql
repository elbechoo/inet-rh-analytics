-- =============================================================================
-- fix_schema.sql
-- Run AFTER script.sql on GestionRH_Intelligente.
-- Adds FKs, UNIQUE, CHECK constraints, DEFAULT values, indexes,
-- and fixes the broken vw_Absence / vw_Conge views.
--
-- Notes:
--   - CHECK and FK constraints use WITH NOCHECK to avoid failing on
--     existing seed data. They will still enforce new inserts/updates.
--   - UNIQUE constraints will fail if duplicates already exist — fix
--     the data first, then re-run those statements.
--   - See the SCHEMA MISMATCH section at the bottom for a known
--     DW_KPI_Employe / DW_KPI_Mensuel issue between script.sql and
--     models/models.py that must be resolved separately.
-- =============================================================================

USE [GestionRH_Intelligente]
GO

-- =============================================================================
-- 1. FIX VIEWS  (vw_Absence / vw_Conge return ROW_NUMBER() as the PK, which
--    is wrong — it shifts when ORDER changes. Return the real PK instead.)
-- =============================================================================

IF OBJECT_ID('dbo.vw_Absence', 'V') IS NOT NULL DROP VIEW dbo.vw_Absence;
GO
CREATE VIEW dbo.vw_Absence AS
SELECT
    absence_id,
    employe_id,
    date_absence,
    justifiee,
    statut,
    motif,
    date_creation
FROM dbo.Absence;
GO

IF OBJECT_ID('dbo.vw_Conge', 'V') IS NOT NULL DROP VIEW dbo.vw_Conge;
GO
CREATE VIEW dbo.vw_Conge AS
SELECT
    conge_id,
    employe_id,
    type_conge,
    date_debut,
    date_fin,
    nb_jours,
    statut,
    commentaire,
    date_demande,
    date_validation,
    valide_par
FROM dbo.Conge;
GO


-- =============================================================================
-- 2. UNIQUE CONSTRAINTS
--    These will error if duplicate rows already exist — clean the data first.
-- =============================================================================

-- Employe: matricule and email must be unique (ORM already declares both)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_Employe_matricule' AND object_id = OBJECT_ID('dbo.Employe'))
    ALTER TABLE dbo.Employe ADD CONSTRAINT UQ_Employe_matricule UNIQUE (matricule);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_Employe_adresse_mail' AND object_id = OBJECT_ID('dbo.Employe'))
    ALTER TABLE dbo.Employe ADD CONSTRAINT UQ_Employe_adresse_mail UNIQUE (adresse_mail);
GO

-- Utilisateur: username and employe_id must be unique (ORM declares both)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_Utilisateur_username' AND object_id = OBJECT_ID('dbo.Utilisateur'))
    ALTER TABLE dbo.Utilisateur ADD CONSTRAINT UQ_Utilisateur_username UNIQUE (username);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_Utilisateur_employe_id' AND object_id = OBJECT_ID('dbo.Utilisateur'))
    ALTER TABLE dbo.Utilisateur ADD CONSTRAINT UQ_Utilisateur_employe_id UNIQUE (employe_id);
GO

-- SoldeConge: ORM has unique=True on employe_id (one balance row per employee)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_SoldeConge_employe_id' AND object_id = OBJECT_ID('dbo.SoldeConge'))
    ALTER TABLE dbo.SoldeConge ADD CONSTRAINT UQ_SoldeConge_employe_id UNIQUE (employe_id);
GO

-- PresenceFormation: an employee can only appear once per formation
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_PresenceFormation_formation_employe' AND object_id = OBJECT_ID('dbo.PresenceFormation'))
    ALTER TABLE dbo.PresenceFormation ADD CONSTRAINT UQ_PresenceFormation_formation_employe UNIQUE (formation_id, employe_id);
GO

-- AdminEmploye: no duplicate admin→employee pairs
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_AdminEmploye_admin_employe' AND object_id = OBJECT_ID('dbo.AdminEmploye'))
    ALTER TABLE dbo.AdminEmploye ADD CONSTRAINT UQ_AdminEmploye_admin_employe UNIQUE (admin_id, employe_id);
GO

-- DW_KPI_Mensuel: no duplicate month/year rows
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UQ_DW_KPI_Mensuel_annee_mois' AND object_id = OBJECT_ID('dbo.DW_KPI_Mensuel'))
    ALTER TABLE dbo.DW_KPI_Mensuel ADD CONSTRAINT UQ_DW_KPI_Mensuel_annee_mois UNIQUE (annee, mois);
GO


-- =============================================================================
-- 3. DEFAULT CONSTRAINTS
--    Checked by COLUMN (not by constraint name) so that SQLAlchemy-generated
--    unnamed defaults (added by Base.metadata.create_all on API startup) are
--    detected and we don't attempt to add a second default on the same column.
-- =============================================================================

-- Helper macro used throughout this section:
--   dc.parent_object_id = OBJECT_ID('dbo.Table')
--   c.name = 'column'
-- detects ANY existing default on that column regardless of its name.

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Absence') AND c.name = 'date_creation')
    ALTER TABLE dbo.Absence ADD CONSTRAINT DF_Absence_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.AdminEmploye') AND c.name = 'date_ajout')
    ALTER TABLE dbo.AdminEmploye ADD CONSTRAINT DF_AdminEmploye_date_ajout DEFAULT GETDATE() FOR date_ajout;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.AlerteIA') AND c.name = 'date_alerte')
    ALTER TABLE dbo.AlerteIA ADD CONSTRAINT DF_AlerteIA_date_alerte DEFAULT GETDATE() FOR date_alerte;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.AlerteIA') AND c.name = 'est_lue')
    ALTER TABLE dbo.AlerteIA ADD CONSTRAINT DF_AlerteIA_est_lue DEFAULT 0 FOR est_lue;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Conge') AND c.name = 'date_demande')
    ALTER TABLE dbo.Conge ADD CONSTRAINT DF_Conge_date_demande DEFAULT GETDATE() FOR date_demande;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Departement') AND c.name = 'date_creation')
    ALTER TABLE dbo.Departement ADD CONSTRAINT DF_Departement_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Departement') AND c.name = 'date_modification')
    ALTER TABLE dbo.Departement ADD CONSTRAINT DF_Departement_date_modification DEFAULT GETDATE() FOR date_modification;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Document') AND c.name = 'date_demande')
    ALTER TABLE dbo.Document ADD CONSTRAINT DF_Document_date_demande DEFAULT GETDATE() FOR date_demande;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Employe') AND c.name = 'date_creation')
    ALTER TABLE dbo.Employe ADD CONSTRAINT DF_Employe_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Employe') AND c.name = 'date_modification')
    ALTER TABLE dbo.Employe ADD CONSTRAINT DF_Employe_date_modification DEFAULT GETDATE() FOR date_modification;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Formation') AND c.name = 'date_creation')
    ALTER TABLE dbo.Formation ADD CONSTRAINT DF_Formation_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Mission') AND c.name = 'date_declaration')
    ALTER TABLE dbo.Mission ADD CONSTRAINT DF_Mission_date_declaration DEFAULT GETDATE() FOR date_declaration;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Pointage') AND c.name = 'date_creation')
    ALTER TABLE dbo.Pointage ADD CONSTRAINT DF_Pointage_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Utilisateur') AND c.name = 'date_creation')
    ALTER TABLE dbo.Utilisateur ADD CONSTRAINT DF_Utilisateur_date_creation DEFAULT GETDATE() FOR date_creation;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Utilisateur') AND c.name = 'date_modification')
    ALTER TABLE dbo.Utilisateur ADD CONSTRAINT DF_Utilisateur_date_modification DEFAULT GETDATE() FOR date_modification;

IF NOT EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.DW_KPI_Mensuel') AND c.name = 'date_maj')
    ALTER TABLE dbo.DW_KPI_Mensuel ADD CONSTRAINT DF_DW_KPI_Mensuel_date_maj DEFAULT GETDATE() FOR date_maj;
GO


-- =============================================================================
-- 4. CHECK CONSTRAINTS  (WITH NOCHECK — enforces new rows, not existing data)
--    Values are derived from actual code in services/ and repositories/.
-- =============================================================================

-- Employe.statut: 'Actif' | 'Inactif' | 'Suspendu'
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Employe_statut')
    ALTER TABLE dbo.Employe WITH NOCHECK
        ADD CONSTRAINT CK_Employe_statut
        CHECK (statut IN (N'Actif', N'Inactif', N'Suspendu'));
GO

-- Utilisateur.role: 'employe' | 'rh' | 'admin'  (admin.py line 60)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Utilisateur_role')
    ALTER TABLE dbo.Utilisateur WITH NOCHECK
        ADD CONSTRAINT CK_Utilisateur_role
        CHECK (role IN (N'employe', N'rh', N'admin'));
GO

-- Conge.statut (conge_repo.py: En attente / Approuvé / Refusé / Annulé)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Conge_statut')
    ALTER TABLE dbo.Conge WITH NOCHECK
        ADD CONSTRAINT CK_Conge_statut
        CHECK (statut IN (N'En attente', N'Approuvé', N'Refusé', N'Annulé'));
GO

-- Conge: leave end must not precede start, and nb_jours must be positive
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Conge_dates')
    ALTER TABLE dbo.Conge WITH NOCHECK
        ADD CONSTRAINT CK_Conge_dates
        CHECK (date_fin >= date_debut);
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Conge_nb_jours')
    ALTER TABLE dbo.Conge WITH NOCHECK
        ADD CONSTRAINT CK_Conge_nb_jours
        CHECK (nb_jours IS NULL OR nb_jours > 0);
GO

-- Mission.statut (mission_repo.py: En attente / Approuvée / Refusée)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Mission_statut')
    ALTER TABLE dbo.Mission WITH NOCHECK
        ADD CONSTRAINT CK_Mission_statut
        CHECK (statut IN (N'En attente', N'Approuvée', N'Refusée'));
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Mission_dates')
    ALTER TABLE dbo.Mission WITH NOCHECK
        ADD CONSTRAINT CK_Mission_dates
        CHECK (date_fin >= date_debut);
GO

-- Document.statut (document_repo.py: En attente / Approuvé / Refusé)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Document_statut')
    ALTER TABLE dbo.Document WITH NOCHECK
        ADD CONSTRAINT CK_Document_statut
        CHECK (statut IN (N'En attente', N'Approuvé', N'Refusé'));
GO

-- Pointage.statut (pointage_repo.py: Présent / En retard / Sortie manquante)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Pointage_statut')
    ALTER TABLE dbo.Pointage WITH NOCHECK
        ADD CONSTRAINT CK_Pointage_statut
        CHECK (statut IN (N'Présent', N'En retard', N'Sortie manquante'));
GO

-- Absence.statut (pointage_service.py: Non justifiée; seed data: Justifiée)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Absence_statut')
    ALTER TABLE dbo.Absence WITH NOCHECK
        ADD CONSTRAINT CK_Absence_statut
        CHECK (statut IN (N'Justifiée', N'Non justifiée'));
GO

-- AlerteIA.niveau (anomaly_detector.py: Critique / Moyen / Info)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_AlerteIA_niveau')
    ALTER TABLE dbo.AlerteIA WITH NOCHECK
        ADD CONSTRAINT CK_AlerteIA_niveau
        CHECK (niveau IN (N'Critique', N'Moyen', N'Info'));
GO


-- =============================================================================
-- 5. FOREIGN KEY CONSTRAINTS  (WITH NOCHECK — enforce new rows only)
--    Defined to match ForeignKey() declarations in models/models.py exactly.
-- =============================================================================

-- Employe → Departement
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Employe_Departement')
    ALTER TABLE dbo.Employe WITH NOCHECK
        ADD CONSTRAINT FK_Employe_Departement
        FOREIGN KEY (departement_id) REFERENCES dbo.Departement(departement_id);
GO

-- Utilisateur → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Utilisateur_Employe')
    ALTER TABLE dbo.Utilisateur WITH NOCHECK
        ADD CONSTRAINT FK_Utilisateur_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- RH → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_RH_Employe')
    ALTER TABLE dbo.RH WITH NOCHECK
        ADD CONSTRAINT FK_RH_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Pointage → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Pointage_Employe')
    ALTER TABLE dbo.Pointage WITH NOCHECK
        ADD CONSTRAINT FK_Pointage_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- PointageLog → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_PointageLog_Employe')
    ALTER TABLE dbo.PointageLog WITH NOCHECK
        ADD CONSTRAINT FK_PointageLog_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Absence → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Absence_Employe')
    ALTER TABLE dbo.Absence WITH NOCHECK
        ADD CONSTRAINT FK_Absence_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Conge → Employe (demandeur)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Conge_Employe')
    ALTER TABLE dbo.Conge WITH NOCHECK
        ADD CONSTRAINT FK_Conge_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Conge.valide_par → Employe  (models.py line 147: ForeignKey("Employe.employe_id"))
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Conge_Validateur')
    ALTER TABLE dbo.Conge WITH NOCHECK
        ADD CONSTRAINT FK_Conge_Validateur
        FOREIGN KEY (valide_par) REFERENCES dbo.Employe(employe_id);
GO

-- Document → Employe (demandeur)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Document_Employe')
    ALTER TABLE dbo.Document WITH NOCHECK
        ADD CONSTRAINT FK_Document_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Document.valide_par → Employe  (models.py line 168: ForeignKey("Employe.employe_id"))
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Document_Validateur')
    ALTER TABLE dbo.Document WITH NOCHECK
        ADD CONSTRAINT FK_Document_Validateur
        FOREIGN KEY (valide_par) REFERENCES dbo.Employe(employe_id);
GO

-- Mission → Employe (demandeur)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Mission_Employe')
    ALTER TABLE dbo.Mission WITH NOCHECK
        ADD CONSTRAINT FK_Mission_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Mission.valide_par → Employe  (models.py line 191: ForeignKey("Employe.employe_id"))
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Mission_Validateur')
    ALTER TABLE dbo.Mission WITH NOCHECK
        ADD CONSTRAINT FK_Mission_Validateur
        FOREIGN KEY (valide_par) REFERENCES dbo.Employe(employe_id);
GO

-- PresenceFormation → Formation
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_PresenceFormation_Formation')
    ALTER TABLE dbo.PresenceFormation WITH NOCHECK
        ADD CONSTRAINT FK_PresenceFormation_Formation
        FOREIGN KEY (formation_id) REFERENCES dbo.Formation(formation_id);
GO

-- PresenceFormation → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_PresenceFormation_Employe')
    ALTER TABLE dbo.PresenceFormation WITH NOCHECK
        ADD CONSTRAINT FK_PresenceFormation_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- SoldeConge → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_SoldeConge_Employe')
    ALTER TABLE dbo.SoldeConge WITH NOCHECK
        ADD CONSTRAINT FK_SoldeConge_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- AlerteIA → Employe (nullable FK)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_AlerteIA_Employe')
    ALTER TABLE dbo.AlerteIA WITH NOCHECK
        ADD CONSTRAINT FK_AlerteIA_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- AlerteIA → Departement (nullable FK)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_AlerteIA_Departement')
    ALTER TABLE dbo.AlerteIA WITH NOCHECK
        ADD CONSTRAINT FK_AlerteIA_Departement
        FOREIGN KEY (departement_id) REFERENCES dbo.Departement(departement_id);
GO

-- AdminEmploye.admin_id → Utilisateur  (models.py line 277: ForeignKey("Utilisateur.user_id"))
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_AdminEmploye_Admin')
    ALTER TABLE dbo.AdminEmploye WITH NOCHECK
        ADD CONSTRAINT FK_AdminEmploye_Admin
        FOREIGN KEY (admin_id) REFERENCES dbo.Utilisateur(user_id);
GO

-- AdminEmploye.employe_id → Employe
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_AdminEmploye_Employe')
    ALTER TABLE dbo.AdminEmploye WITH NOCHECK
        ADD CONSTRAINT FK_AdminEmploye_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO


-- =============================================================================
-- 6. PERFORMANCE INDEXES
--    SQL Server does not auto-index FK columns. Without these, every join or
--    filter on these columns does a full table scan.
-- =============================================================================

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Absence_employe_id')
    CREATE INDEX IX_Absence_employe_id ON dbo.Absence(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Absence_date_absence')
    CREATE INDEX IX_Absence_date_absence ON dbo.Absence(date_absence);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Conge_employe_id')
    CREATE INDEX IX_Conge_employe_id ON dbo.Conge(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Conge_statut')
    CREATE INDEX IX_Conge_statut ON dbo.Conge(statut);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_employe_date')
    CREATE INDEX IX_Pointage_employe_date ON dbo.Pointage(employe_id, date_pointage);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_date')
    CREATE INDEX IX_Pointage_date ON dbo.Pointage(date_pointage);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Pointage_statut')
    CREATE INDEX IX_Pointage_statut ON dbo.Pointage(statut);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Employe_departement_id')
    CREATE INDEX IX_Employe_departement_id ON dbo.Employe(departement_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Employe_statut')
    CREATE INDEX IX_Employe_statut ON dbo.Employe(statut);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_AlerteIA_employe_est_lue')
    CREATE INDEX IX_AlerteIA_employe_est_lue ON dbo.AlerteIA(employe_id, est_lue);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_AlerteIA_departement_id')
    CREATE INDEX IX_AlerteIA_departement_id ON dbo.AlerteIA(departement_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Document_employe_id')
    CREATE INDEX IX_Document_employe_id ON dbo.Document(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Document_statut')
    CREATE INDEX IX_Document_statut ON dbo.Document(statut);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Mission_employe_id')
    CREATE INDEX IX_Mission_employe_id ON dbo.Mission(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PresenceFormation_employe_id')
    CREATE INDEX IX_PresenceFormation_employe_id ON dbo.PresenceFormation(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PresenceFormation_formation_id')
    CREATE INDEX IX_PresenceFormation_formation_id ON dbo.PresenceFormation(formation_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PointageLog_employe_id')
    CREATE INDEX IX_PointageLog_employe_id ON dbo.PointageLog(employe_id);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_SoldeConge_employe_id')
    CREATE INDEX IX_SoldeConge_employe_id ON dbo.SoldeConge(employe_id);
GO


-- =============================================================================
-- 7. DW_KPI_Employe — FK and index
--    The ETL uses employe_id as the PK (no kpi_id). models/models.py has
--    been updated to match. Add the FK here so SQL Server enforces it.
-- =============================================================================

-- DW_KPI_Employe.employe_id → Employe (ETL inserts one row per employee)
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_DW_KPI_Employe_Employe')
    ALTER TABLE dbo.DW_KPI_Employe WITH NOCHECK
        ADD CONSTRAINT FK_DW_KPI_Employe_Employe
        FOREIGN KEY (employe_id) REFERENCES dbo.Employe(employe_id);
GO

-- Index on taux columns — used by digest_builder aggregate query
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DW_KPI_Employe_taux')
    CREATE INDEX IX_DW_KPI_Employe_taux
        ON dbo.DW_KPI_Employe(taux_presence, taux_absence, taux_retard, nb_absences);
GO
