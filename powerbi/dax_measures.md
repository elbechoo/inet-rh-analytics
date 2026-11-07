# iNET RH - Power BI Report on the Kimball Star Schema

This report is built **directly on the data-warehouse star schema** (`Dim_Date`, `Dim_Employe`, `Dim_Departement`, `Dim_Formation`, `Fact_Pointage`, `Fact_Absence`, `Fact_Conge`, `Fact_Formation`) - not on the operational tables. The star schema is created by `powerbi/star_schema.sql` and populated by `etl/load_star.py`. The three core dimensions (Date, Employee, Department) are conformed: each of the four facts joins to them by the same surrogate keys.

Current load: Dim_Date 4 748 · Dim_Departement 10 · Dim_Employe 76 · Dim_Formation 54 · Fact_Pointage ≈195 591 · Fact_Absence ≈13 846 · Fact_Conge ≈14 848 · Fact_Formation ≈2 194.

---

## Step 1 - Connect

1. Power BI Desktop -> **Home -> Get Data -> SQL Server**.
2. Server: `localhost` · Database: `GestionRH_Intelligente` · Data Connectivity mode: **Import**.
3. Select exactly these eight tables and load them:
   `Dim_Date`, `Dim_Employe`, `Dim_Departement`, `Dim_Formation`, `Fact_Pointage`, `Fact_Absence`, `Fact_Conge`, `Fact_Formation`.

## Step 2 - Model (relationships)

In **Model view**, create these relationships (Many -> One, single direction, from fact to dimension). Power BI may auto-detect most of them; verify each one.

| From (fact) | Column | To (dimension) | Column | Active |
|---|---|---|---|---|
| Fact_Pointage | date_id | Dim_Date | date_id | Yes |
| Fact_Pointage | employe_sk | Dim_Employe | employe_sk | Yes |
| Fact_Pointage | departement_sk | Dim_Departement | departement_sk | Yes |
| Fact_Absence | date_id | Dim_Date | date_id | Yes |
| Fact_Absence | employe_sk | Dim_Employe | employe_sk | Yes |
| Fact_Absence | departement_sk | Dim_Departement | departement_sk | Yes |
| Fact_Conge | date_debut_id | Dim_Date | date_id | Yes |
| Fact_Conge | date_fin_id | Dim_Date | date_id | No (inactive) |
| Fact_Conge | employe_sk | Dim_Employe | employe_sk | Yes |
| Fact_Conge | departement_sk | Dim_Departement | departement_sk | Yes |
| Fact_Formation | date_id | Dim_Date | date_id | Yes |
| Fact_Formation | employe_sk | Dim_Employe | employe_sk | Yes |
| Fact_Formation | departement_sk | Dim_Departement | departement_sk | Yes |
| Fact_Formation | formation_sk | Dim_Formation | formation_sk | Yes |

Notes:
- A pair of tables can have only one **active** relationship. `Fact_Conge` has two links to `Dim_Date` (start and end); keep `date_debut_id` active and `date_fin_id` inactive. The end-date link is only needed if you build an end-date measure with `USERELATIONSHIP`.
- Mark `Dim_Date` as the date table: select `Dim_Date` -> Table tools -> **Mark as date table** -> `date_complete`.

## Step 3 - Measures

Create one empty table named `_Measures` (Home -> Enter Data -> table `_Measures`, delete the dummy column), then add the measures below. They use only columns that exist in the star schema.

```dax
// ---------- Headcount ----------
Total Employes =
DISTINCTCOUNT ( Dim_Employe[employe_id] )

Nb Departements =
DISTINCTCOUNT ( Dim_Departement[departement_id] )

// ---------- Attendance volumes ----------
Nb Pointages = COUNTROWS ( Fact_Pointage )

Nb Presents =
CALCULATE ( COUNTROWS ( Fact_Pointage ), Fact_Pointage[est_present] = 1 )

Nb Retards =
CALCULATE ( COUNTROWS ( Fact_Pointage ), Fact_Pointage[est_retard] = 1 )

Nb Sorties Manquantes =
CALCULATE ( COUNTROWS ( Fact_Pointage ), Fact_Pointage[sortie_manquante] = 1 )

// ---------- Absence / leave volumes ----------
Nb Absences = SUM ( Fact_Absence[nb_absences] )

Nb Absences Justifiees =
CALCULATE ( SUM ( Fact_Absence[nb_absences] ), Fact_Absence[est_justifiee] = 1 )

Nb Absences Non Justifiees =
CALCULATE ( SUM ( Fact_Absence[nb_absences] ), Fact_Absence[est_justifiee] = 0 )

Nb Conges = COUNTROWS ( Fact_Conge )

Total Jours Conge = SUM ( Fact_Conge[nb_jours] )

// ---------- Core HR KPIs ----------
Taux Presence % =
DIVIDE ( [Nb Presents], [Nb Pointages], 0 ) * 100

Taux Retard % =
DIVIDE ( [Nb Retards], [Nb Pointages], 0 ) * 100

Taux Absenteisme % =
DIVIDE ( [Nb Absences], [Nb Pointages] + [Nb Absences], 0 ) * 100

Taux Justification % =
DIVIDE ( [Nb Absences Justifiees], [Nb Absences], 0 ) * 100

Moy Heures Jour =
AVERAGEX (
    FILTER ( Fact_Pointage, Fact_Pointage[duree_travail] > 0 ),
    Fact_Pointage[duree_travail]
)

Moy Minutes Retard =
CALCULATE (
    AVERAGE ( Fact_Pointage[retard_minutes] ),
    Fact_Pointage[est_retard] = 1
)

Heure Entree Moyenne =
AVERAGE ( Fact_Pointage[heure_entree_decimal] )

// ---------- Year-over-year ----------
Absenteisme Annee Prec % =
CALCULATE (
    [Taux Absenteisme %],
    DATEADD ( Dim_Date[date_complete], -1, YEAR )
)

Variation Absenteisme YoY (pts) =
[Taux Absenteisme %] - [Absenteisme Annee Prec %]

// ---------- Leave with end-date relationship (optional) ----------
Conges Termines Periode =
CALCULATE (
    COUNTROWS ( Fact_Conge ),
    USERELATIONSHIP ( Fact_Conge[date_fin_id], Dim_Date[date_id] )
)

// ---------- Training (Fact_Formation) ----------
Nb Formations =
DISTINCTCOUNT ( Dim_Formation[formation_id] )

Nb Inscriptions =
SUM ( Fact_Formation[nb_participations] )

Nb Participants Presents =
CALCULATE ( SUM ( Fact_Formation[nb_participations] ), Fact_Formation[est_present] = 1 )

Taux Participation Formation % =
DIVIDE ( [Nb Participants Presents], [Nb Inscriptions], 0 ) * 100

Score Moyen Formation =
CALCULATE (
    AVERAGE ( Fact_Formation[score] ),
    Fact_Formation[est_present] = 1
)

Mentions Excellent =
CALCULATE (
    COUNTROWS ( Fact_Formation ),
    Fact_Formation[est_present] = 1,
    Fact_Formation[score] >= 85
)

Heures Formation =
SUMX (
    SUMMARIZE ( Fact_Formation, Dim_Formation[formation_id], "d", MAX ( Dim_Formation[duree_jours] ) ),
    [d] * 7
)
```

## Step 4 - Pages and visuals

The report has five pages built only from the four fact tables, so every visual is backed by real warehouse data.

### Page 1 - Executive Overview
| Visual | Configuration |
|---|---|
| KPI cards (row) | `Total Employes`, `Taux Absenteisme %`, `Taux Retard %`, `Moy Heures Jour` |
| Line chart | Axis `Dim_Date[annee]` -> values `Taux Presence %`, `Taux Retard %`, `Taux Absenteisme %` |
| Clustered bar | Axis `Dim_Departement[nom_departement]` -> `Taux Absenteisme %` |
| Donut | Legend `Dim_Employe[type_contrat]` -> `Total Employes` |
| Slicer | `Dim_Date[annee]` |

### Page 2 - Attendance & Lateness
| Visual | Configuration |
|---|---|
| KPI cards | `Nb Presents`, `Nb Retards`, `Moy Minutes Retard`, `Nb Sorties Manquantes` |
| Area chart | Axis `Dim_Date[nom_mois]` (sorted by `mois`) -> `Taux Presence %` |
| Matrix (heatmap) | Rows `Dim_Date[nom_mois]`, Columns `Dim_Date[annee]`, Values `Taux Retard %` |
| Clustered bar | Axis `Dim_Departement[nom_departement]` -> `Nb Retards` |
| Column chart | Axis `Dim_Date[saison]` -> `Taux Retard %` |
| Slicers | `Dim_Date[annee]`, `Dim_Departement[nom_departement]` |

### Page 3 - Absences Analysis
| Visual | Configuration |
|---|---|
| KPI cards | `Nb Absences`, `Nb Absences Non Justifiees`, `Taux Justification %`, `Taux Absenteisme %` |
| Stacked column | Axis `Dim_Date[nom_mois]` -> `Nb Absences Justifiees` + `Nb Absences Non Justifiees` |
| Line chart | Axis `Dim_Date[annee]` -> `Nb Absences` |
| Bar chart | Axis `Dim_Departement[nom_departement]` -> `Nb Absences` |
| Column chart | Axis `Dim_Date[saison]` -> `Nb Absences` |
| Table | `Dim_Employe[nom_complet]`, `Nb Absences`, `Nb Absences Non Justifiees`, `Taux Absenteisme %` (sort desc) |
| Slicers | `Dim_Date[annee]`, `Dim_Employe[nom_departement]` |

### Page 4 - Leave Analysis
| Visual | Configuration |
|---|---|
| KPI cards | `Nb Conges`, `Total Jours Conge`, average of `Fact_Conge[nb_jours]`, `Total Employes` |
| Donut | Legend `Fact_Conge[type_conge]` -> `Nb Conges` |
| Bar chart | Axis `Fact_Conge[statut]` -> `Nb Conges` |
| Line chart | Axis `Dim_Date[nom_mois]` -> `Total Jours Conge` |
| Column chart | Axis `Dim_Date[saison]` -> `Total Jours Conge` |
| Bar chart | Axis `Dim_Departement[nom_departement]` -> `Total Jours Conge` |
| Slicer | `Dim_Date[annee]`, `Fact_Conge[type_conge]` |

### Page 5 - Training Analytics
| Visual | Configuration |
|---|---|
| KPI cards | `Nb Formations`, `Nb Inscriptions`, `Taux Participation Formation %`, `Score Moyen Formation` |
| Donut | Legend `Dim_Formation[type_formation]` -> `Nb Inscriptions` |
| Bar chart | Axis `Dim_Departement[nom_departement]` -> `Taux Participation Formation %` |
| Line chart | Axis `Dim_Date[annee]` -> `Nb Formations` |
| Scatter | X `Dim_Employe[nom_complet]`, Y `Score Moyen Formation`, size `Nb Inscriptions` |
| Table | `Dim_Formation[titre]`, `Dim_Formation[type_formation]`, `Nb Inscriptions`, `Taux Participation Formation %`, `Score Moyen Formation` |
| Slicers | `Dim_Date[annee]`, `Dim_Formation[type_formation]` |

## Step 5 - Theme

Apply a custom theme (View -> Themes -> Customize current theme) with:
- Primary `#6366f1`, secondary `#4f46e5`, success `#10b981`, warning `#f59e0b`, danger `#dc2626`, background `#f8fafc`, dark `#0f172a`.

Keep visuals minimal: no 3-D, no decorative backgrounds. Each visual must encode a value (dashboard design principle, Few 2006).

## Step 6 - Capture for the report

Export or screenshot each of the four pages for Figures 5.11-5.14 of the report (see `rapport-pfe/99-screenshot-checklist.md`). Use the Power BI File -> Export -> PDF if you also want a PDF annex.
