-- =============================================================
-- iNET RH — Kimball Star Schema (Data Warehouse Layer)
-- Run once against GestionRH_Intelligente
-- Grain of Fact_Pointage  : 1 row per employee per working day
-- Grain of Fact_Absence   : 1 row per absence event
-- Grain of Fact_Conge     : 1 row per leave request
-- =============================================================

USE GestionRH_Intelligente;
GO

-- =============================================================
-- DIMENSION: Dim_Date
-- Standard calendar dimension — populated by ETL (2015–2027)
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Date' AND xtype='U')
CREATE TABLE Dim_Date (
    date_id         INT          NOT NULL PRIMARY KEY,   -- YYYYMMDD
    date_complete   DATE         NOT NULL,
    annee           INT          NOT NULL,
    trimestre       INT          NOT NULL,               -- 1-4
    mois            INT          NOT NULL,               -- 1-12
    nom_mois        VARCHAR(20)  NOT NULL,
    semaine         INT          NOT NULL,               -- ISO week
    jour            INT          NOT NULL,               -- 1-31
    nom_jour        VARCHAR(20)  NOT NULL,
    jour_semaine_num INT         NOT NULL,               -- 0=Mon … 6=Sun
    est_weekend     BIT          NOT NULL DEFAULT 0,
    saison          VARCHAR(20)  NOT NULL                -- Hiver/Printemps/Été/Automne
);
GO

-- =============================================================
-- DIMENSION: Dim_Departement  (Type 1 SCD)
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Departement' AND xtype='U')
CREATE TABLE Dim_Departement (
    departement_sk  INT IDENTITY(1,1) PRIMARY KEY,
    departement_id  INT          NOT NULL,              -- NK from OLTP
    nom_departement VARCHAR(100) NOT NULL,
    sous_departement VARCHAR(100),
    date_chargement DATETIME     NOT NULL DEFAULT GETDATE()
);
GO

-- =============================================================
-- DIMENSION: Dim_Employe  (Type 1 SCD — latest state wins)
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Employe' AND xtype='U')
CREATE TABLE Dim_Employe (
    employe_sk      INT IDENTITY(1,1) PRIMARY KEY,
    employe_id      INT          NOT NULL,              -- NK from OLTP
    matricule       VARCHAR(20)  NOT NULL,
    nom_complet     VARCHAR(200) NOT NULL,
    poste           VARCHAR(100),
    type_contrat    VARCHAR(50),
    date_embauche   DATE,
    anciennete_annees INT,
    departement_id  INT,
    nom_departement VARCHAR(100),
    sous_departement VARCHAR(100),
    date_chargement DATETIME     NOT NULL DEFAULT GETDATE()
);
GO

-- =============================================================
-- FACT: Fact_Pointage
-- Grain: 1 attendance record per employee per working day
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fact_Pointage' AND xtype='U')
CREATE TABLE Fact_Pointage (
    pointage_sk       INT IDENTITY(1,1) PRIMARY KEY,
    -- Foreign keys
    date_id           INT     NOT NULL REFERENCES Dim_Date(date_id),
    employe_sk        INT     NOT NULL REFERENCES Dim_Employe(employe_sk),
    departement_sk    INT     NOT NULL REFERENCES Dim_Departement(departement_sk),
    -- Natural key
    pointage_id       INT,
    -- Degenerate dimensions
    statut            VARCHAR(30),
    -- Measures
    heure_entree_decimal FLOAT,                         -- ex: 8.5 = 08h30
    duree_travail     FLOAT,                            -- hours worked
    retard_minutes    INT,
    -- Indicators (pre-computed for Power BI performance)
    est_present       BIT NOT NULL DEFAULT 0,
    est_retard        BIT NOT NULL DEFAULT 0,
    sortie_manquante  BIT NOT NULL DEFAULT 0
);
GO

-- =============================================================
-- FACT: Fact_Absence
-- Grain: 1 row per absence event (one employee, one day)
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fact_Absence' AND xtype='U')
CREATE TABLE Fact_Absence (
    absence_sk      INT IDENTITY(1,1) PRIMARY KEY,
    -- Foreign keys
    date_id         INT     NOT NULL REFERENCES Dim_Date(date_id),
    employe_sk      INT     NOT NULL REFERENCES Dim_Employe(employe_sk),
    departement_sk  INT     NOT NULL REFERENCES Dim_Departement(departement_sk),
    -- Natural key
    absence_id      INT,
    -- Degenerate dimensions
    motif           VARCHAR(255),
    -- Measures / indicators
    est_justifiee   BIT NOT NULL DEFAULT 0,
    nb_absences     INT NOT NULL DEFAULT 1              -- always 1, for SUM aggregations
);
GO

-- =============================================================
-- FACT: Fact_Conge
-- Grain: 1 row per leave request
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fact_Conge' AND xtype='U')
CREATE TABLE Fact_Conge (
    conge_sk        INT IDENTITY(1,1) PRIMARY KEY,
    -- Foreign keys (start date drives the time dimension)
    date_debut_id   INT     NOT NULL REFERENCES Dim_Date(date_id),
    date_fin_id     INT     NOT NULL REFERENCES Dim_Date(date_id),
    employe_sk      INT     NOT NULL REFERENCES Dim_Employe(employe_sk),
    departement_sk  INT     NOT NULL REFERENCES Dim_Departement(departement_sk),
    -- Natural key
    conge_id        INT,
    -- Degenerate dimensions
    type_conge      VARCHAR(50),
    statut          VARCHAR(30),
    -- Measures
    nb_jours        INT
);
GO

-- =============================================================
-- DIMENSION: Dim_Formation  (Type 1 SCD)
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Dim_Formation' AND xtype='U')
CREATE TABLE Dim_Formation (
    formation_sk    INT IDENTITY(1,1) PRIMARY KEY,
    formation_id    INT          NOT NULL,              -- NK from OLTP
    titre           VARCHAR(200) NOT NULL,
    organisateur   VARCHAR(100),
    type_formation  VARCHAR(50),
    date_debut      DATE,
    date_fin        DATE,
    duree_jours     INT,
    date_chargement DATETIME     NOT NULL DEFAULT GETDATE()
);
GO

-- =============================================================
-- FACT: Fact_Formation
-- Grain: 1 row per employee per training session (participation)
-- Source: PresenceFormation joined to Formation
-- =============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fact_Formation' AND xtype='U')
CREATE TABLE Fact_Formation (
    presence_sk     INT IDENTITY(1,1) PRIMARY KEY,
    -- Foreign keys (date drives the training-start time dimension)
    date_id         INT     NOT NULL REFERENCES Dim_Date(date_id),
    employe_sk      INT     NOT NULL REFERENCES Dim_Employe(employe_sk),
    departement_sk  INT     NOT NULL REFERENCES Dim_Departement(departement_sk),
    formation_sk    INT     NOT NULL REFERENCES Dim_Formation(formation_sk),
    -- Natural key
    presence_id     INT,
    -- Measures / indicators
    est_present     BIT NOT NULL DEFAULT 0,
    score           FLOAT,
    nb_participations INT NOT NULL DEFAULT 1              -- always 1, for SUM aggregations
);
GO

PRINT 'Star schema created successfully (Dim_Date, Dim_Employe, Dim_Departement, Dim_Formation, Fact_Pointage, Fact_Absence, Fact_Conge, Fact_Formation).';
GO
