"""
Notifications - Digest Builder
Construit le contenu HTML du rapport quotidien RH
"""
import pandas as pd
from sqlalchemy import text
from config.database import engine
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


def get_daily_data() -> dict:
    """Récupérer les données du jour depuis la DB"""
    today     = date.today()
    yesterday = today - timedelta(days=1)

    with engine.connect() as conn:

        # Alertes IA non lues
        alertes = pd.read_sql(text("""
            SELECT a.niveau, a.type_alerte, a.message,
                   a.date_alerte,
                   e.nom + ' ' + e.prenom AS nom_complet,
                   d.nom_departement
            FROM AlerteIA a
            JOIN Employe   e ON a.employe_id    = e.employe_id
            JOIN Departement d ON e.departement_id = d.departement_id
            WHERE a.est_lue = 0
            ORDER BY
                CASE a.niveau
                    WHEN 'Critique' THEN 1
                    WHEN 'Moyen'    THEN 2
                    ELSE 3
                END,
                a.date_alerte DESC
        """), conn)

        # KPIs globaux depuis DW
        kpis = pd.read_sql(text("""
            SELECT
                COUNT(*)                    AS nb_employes,
                AVG(taux_presence)          AS taux_presence_moyen,
                AVG(taux_absence)           AS taux_absence_moyen,
                AVG(taux_retard)            AS taux_retard_moyen,
                SUM(CASE WHEN taux_retard > 40
                         OR nb_absences > 5 THEN 1 ELSE 0 END) AS nb_risque
            FROM DW_KPI_Employe
        """), conn)

        # Congés en attente
        conges = pd.read_sql(text("""
            SELECT e.nom + ' ' + e.prenom AS nom_complet,
                   d.nom_departement,
                   c.type_conge, c.date_debut, c.date_fin, c.nb_jours
            FROM Conge c
            JOIN Employe    e ON c.employe_id    = e.employe_id
            JOIN Departement d ON e.departement_id = d.departement_id
            WHERE c.statut = 'En attente'
            ORDER BY c.date_debut
        """), conn)

        # Absences du jour
        absences_today = pd.read_sql(text(f"""
            SELECT e.nom + ' ' + e.prenom AS nom_complet,
                   d.nom_departement,
                   a.justifiee
            FROM Absence a
            JOIN Employe    e ON a.employe_id    = e.employe_id
            JOIN Departement d ON e.departement_id = d.departement_id
            WHERE CAST(a.date_absence AS DATE) = CAST(GETDATE() AS DATE)
        """), conn)

    return {
        "alertes"        : alertes,
        "kpis"           : kpis.iloc[0] if len(kpis) > 0 else None,
        "conges"         : conges,
        "absences_today" : absences_today,
        "date"           : today.strftime("%d/%m/%Y"),
    }


def _niveau_badge(niveau: str) -> str:
    colors = {
        "Critique": "#dc3545",
        "Moyen":    "#fd7e14",
        "Info":     "#0dcaf0",
    }
    color = colors.get(niveau, "#6c757d")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{niveau}</span>'


def build_html_digest(data: dict) -> str:
    """Construire le rapport HTML quotidien"""

    kpis            = data["kpis"]
    alertes         = data["alertes"]
    conges          = data["conges"]
    absences_today  = data["absences_today"]
    rapport_date    = data["date"]

    nb_critiques = len(alertes[alertes["niveau"] == "Critique"])
    nb_moyennes  = len(alertes[alertes["niveau"] == "Moyen"])
    nb_info      = len(alertes[alertes["niveau"] == "Info"])

    # ── KPI cards ──────────────────────────────────────────
    kpi_html = ""
    if kpis is not None:
        kpi_html = f"""
        <table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom:24px;">
          <tr>
            <td align="center" style="background:#e8f5e9;border-radius:8px;padding:16px;width:19%;">
              <div style="font-size:28px;font-weight:bold;color:#2e7d32;">{int(kpis['nb_employes'])}</div>
              <div style="font-size:12px;color:#555;">Employés Actifs</div>
            </td>
            <td width="2%"></td>
            <td align="center" style="background:#e3f2fd;border-radius:8px;padding:16px;width:19%;">
              <div style="font-size:28px;font-weight:bold;color:#1565c0;">{kpis['taux_presence_moyen']:.1f}%</div>
              <div style="font-size:12px;color:#555;">Taux Présence</div>
            </td>
            <td width="2%"></td>
            <td align="center" style="background:#fff3e0;border-radius:8px;padding:16px;width:19%;">
              <div style="font-size:28px;font-weight:bold;color:#e65100;">{kpis['taux_absence_moyen']:.2f}%</div>
              <div style="font-size:12px;color:#555;">Taux Absentéisme</div>
            </td>
            <td width="2%"></td>
            <td align="center" style="background:#fce4ec;border-radius:8px;padding:16px;width:19%;">
              <div style="font-size:28px;font-weight:bold;color:#c62828;">{kpis['taux_retard_moyen']:.1f}%</div>
              <div style="font-size:12px;color:#555;">Taux Retard</div>
            </td>
            <td width="2%"></td>
            <td align="center" style="background:#{'fce4ec' if kpis['nb_risque'] > 10 else 'f3e5f5'};border-radius:8px;padding:16px;width:19%;">
              <div style="font-size:28px;font-weight:bold;color:#6a1b9a;">{int(kpis['nb_risque'])}</div>
              <div style="font-size:12px;color:#555;">Employés à Risque</div>
            </td>
          </tr>
        </table>"""

    # ── Alertes IA ─────────────────────────────────────────
    alertes_rows = ""
    for _, row in alertes.head(10).iterrows():
        alertes_rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:8px 12px;">{_niveau_badge(row['niveau'])}</td>
          <td style="padding:8px 12px;color:#333;">{row['nom_complet']}</td>
          <td style="padding:8px 12px;color:#666;">{row['nom_departement']}</td>
          <td style="padding:8px 12px;font-size:13px;color:#444;">{row['message'][:80]}{'...' if len(str(row['message'])) > 80 else ''}</td>
        </tr>"""

    # ── Congés en attente ───────────────────────────────────
    conges_rows = ""
    for _, row in conges.head(8).iterrows():
        conges_rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:8px 12px;color:#333;">{row['nom_complet']}</td>
          <td style="padding:8px 12px;color:#666;">{row['nom_departement']}</td>
          <td style="padding:8px 12px;">{row['type_conge']}</td>
          <td style="padding:8px 12px;">{str(row['date_debut'])[:10]} -> {str(row['date_fin'])[:10]}</td>
          <td style="padding:8px 12px;text-align:center;font-weight:bold;">{row['nb_jours']}j</td>
        </tr>"""

    # ── Absences du jour ────────────────────────────────────
    absences_rows = ""
    if len(absences_today) > 0:
        for _, row in absences_today.iterrows():
            justif = "✅ Justifiée" if row["justifiee"] else "❌ Non justifiée"
            absences_rows += f"""
            <tr style="border-bottom:1px solid #eee;">
              <td style="padding:8px 12px;color:#333;">{row['nom_complet']}</td>
              <td style="padding:8px 12px;color:#666;">{row['nom_departement']}</td>
              <td style="padding:8px 12px;">{justif}</td>
            </tr>"""
    else:
        absences_rows = '<tr><td colspan="3" style="padding:12px;color:#888;text-align:center;">✅ Aucune absence aujourd\'hui</td></tr>'

    # ── HTML complet ───────────────────────────────────────
    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:24px 0;">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a237e,#283593);padding:28px 32px;">
      <h1 style="margin:0;color:white;font-size:22px;">📊 iNET RH - Rapport Quotidien</h1>
      <p style="margin:6px 0 0;color:#c5cae9;font-size:14px;">Synthèse du {rapport_date}</p>
    </td>
  </tr>

  <!-- KPIs -->
  <tr><td style="padding:24px 32px 8px;">
    <h2 style="margin:0 0 16px;font-size:16px;color:#333;border-left:4px solid #1a237e;padding-left:10px;">📈 KPIs Globaux</h2>
    {kpi_html}
  </td></tr>

  <!-- Alertes IA -->
  <tr><td style="padding:8px 32px;">
    <h2 style="margin:0 0 12px;font-size:16px;color:#333;border-left:4px solid #dc3545;padding-left:10px;">
      🤖 Alertes IA Non Lues
      <span style="background:#dc3545;color:white;border-radius:12px;padding:2px 10px;font-size:13px;margin-left:8px;">{nb_critiques} Critiques</span>
      <span style="background:#fd7e14;color:white;border-radius:12px;padding:2px 10px;font-size:13px;margin-left:4px;">{nb_moyennes} Moyennes</span>
    </h2>
    <table width="100%" style="border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Niveau</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Employé</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Département</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Message</th>
        </tr>
      </thead>
      <tbody>{alertes_rows if alertes_rows else '<tr><td colspan="4" style="padding:12px;color:#888;text-align:center;">✅ Aucune alerte non lue</td></tr>'}</tbody>
    </table>
  </td></tr>

  <!-- Congés en attente -->
  <tr><td style="padding:20px 32px 8px;">
    <h2 style="margin:0 0 12px;font-size:16px;color:#333;border-left:4px solid #fd7e14;padding-left:10px;">
      🏖️ Congés En Attente ({len(conges)})
    </h2>
    <table width="100%" style="border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Employé</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Département</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Type</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Période</th>
          <th style="padding:10px 12px;text-align:center;font-size:13px;color:#666;">Jours</th>
        </tr>
      </thead>
      <tbody>{conges_rows if conges_rows else '<tr><td colspan="5" style="padding:12px;color:#888;text-align:center;">✅ Aucun congé en attente</td></tr>'}</tbody>
    </table>
  </td></tr>

  <!-- Absences du jour -->
  <tr><td style="padding:20px 32px;">
    <h2 style="margin:0 0 12px;font-size:16px;color:#333;border-left:4px solid #ffc107;padding-left:10px;">
      📅 Absences Aujourd'hui ({len(absences_today)})
    </h2>
    <table width="100%" style="border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Employé</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Département</th>
          <th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;">Statut</th>
        </tr>
      </thead>
      <tbody>{absences_rows}</tbody>
    </table>
  </td></tr>

  <!-- Footer -->
  <tr>
    <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #eee;">
      <p style="margin:0;color:#999;font-size:12px;">
        iNET RH Intelligente - Rapport généré automatiquement le {rapport_date}<br>
        <span style="color:#1a237e;">Ne pas répondre à cet email</span>
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html


def build_and_get_subject(data: dict) -> str:
    """Générer le sujet de l'email selon la criticité"""
    nb_critiques = len(data["alertes"][data["alertes"]["niveau"] == "Critique"])
    nb_conges    = len(data["conges"])

    if nb_critiques > 0:
        return f"🔴 iNET RH - {nb_critiques} Alerte(s) Critique(s) | Rapport du {data['date']}"
    elif nb_conges > 0:
        return f"🟡 iNET RH - {nb_conges} Congé(s) en attente | Rapport du {data['date']}"
    else:
        return f"✅ iNET RH - Rapport quotidien du {data['date']}"