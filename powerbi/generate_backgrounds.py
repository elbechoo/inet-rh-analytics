"""
iNET RH - Power BI Background Generator
Generates 4 PNG background images (1280x720) for the 4 dashboard pages.

Run from the powerbi/ folder:
    python generate_backgrounds.py

Output: powerbi/backgrounds/page1_executive_overview.png  ... page4_...png

In Power BI Desktop:
    1. Select the page
    2. Format pane -> Canvas background -> Image -> Browse -> pick the PNG
    3. Image fit: Fit   Transparency: 0%
    4. Then drag your visuals on top of the white boxes.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 1280, 720

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = (240, 244, 250)
WHITE    = (255, 255, 255)
DARK     = (15,  23,  42)
MUTED    = (100, 116, 139)
BORDER   = (220, 228, 240)
SURFACE  = (248, 250, 252)

INDIGO   = (99,  102, 241)
INDIGO_D = (67,  56,  202)
GREEN    = (16,  185, 129)
YELLOW   = (245, 158, 11)
RED      = (220, 38,  38)
PURPLE   = (167, 139, 250)
CYAN     = (34,  211, 238)

HDR_L    = (55,  48,  163)   # header gradient left
HDR_R    = (99,  102, 241)   # header gradient right
HDR_H    = 66               # header height


# ── Fonts ─────────────────────────────────────────────────────────────────────
def load_fonts():
    wins = "C:/Windows/Fonts/"
    candidates = {
        "title":   [(wins + "seguisb.ttf", 20), (wins + "arialbd.ttf", 20)],
        "bold":    [(wins + "seguisb.ttf", 13), (wins + "arialbd.ttf", 13)],
        "regular": [(wins + "segoeui.ttf", 12), (wins + "arial.ttf",   12)],
        "small":   [(wins + "segoeui.ttf", 10), (wins + "arial.ttf",   10)],
        "logo":    [(wins + "seguisb.ttf", 22), (wins + "arialbd.ttf", 22)],
        "kpi_val": [(wins + "seguisb.ttf", 28), (wins + "arialbd.ttf", 28)],
    }
    fonts = {}
    for key, opts in candidates.items():
        for path, size in opts:
            if os.path.exists(path):
                try:
                    fonts[key] = ImageFont.truetype(path, size)
                    break
                except Exception:
                    pass
        if key not in fonts:
            fonts[key] = ImageFont.load_default()
    return fonts


# ── Drawing primitives ────────────────────────────────────────────────────────
def rounded_rect(draw, x1, y1, x2, y2, r, fill=None, outline=None, width=1):
    """Draw a rounded rectangle (compatible with PIL < 8.2 fallback)."""
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=r,
                               fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)


def shadow_rect(draw, x1, y1, x2, y2, r=12):
    """Draw a subtle drop-shadow rectangle."""
    for offset, alpha in [(4, 20), (3, 30), (2, 40)]:
        color = tuple([int(c * (1 - alpha/255)) for c in BG])
        rounded_rect(draw, x1 + offset, y1 + offset,
                     x2 + offset, y2 + offset, r, fill=(190, 200, 215))


def header(draw, fonts, page_title: str):
    """Draw the gradient header bar."""
    r1, g1, b1 = HDR_L
    r2, g2, b2 = HDR_R
    for x in range(W):
        t = x / max(W - 1, 1)
        c = (int(r1 + (r2 - r1) * t),
             int(g1 + (g2 - g1) * t),
             int(b1 + (b2 - b1) * t))
        draw.line([(x, 0), (x, HDR_H)], fill=c)

    # iNET RH logo
    draw.text((24, HDR_H // 2 - 1), "iNET RH",
              font=fonts["logo"], fill=(255, 255, 255), anchor="lm")

    # Separator dot
    draw.ellipse([148, HDR_H // 2 - 4, 156, HDR_H // 2 + 4],
                 fill=(200, 205, 255))

    # Page title (centered)
    draw.text((W // 2, HDR_H // 2), page_title,
              font=fonts["bold"], fill=(210, 214, 255), anchor="mm")

    # Right badge
    badge_text = "HR Intelligence Platform"
    bx1, by1, bx2, by2 = W - 260, HDR_H // 2 - 14, W - 20, HDR_H // 2 + 14
    rounded_rect(draw, bx1, by1, bx2, by2, 10,
                 fill=(255, 255, 255, 0), outline=(180, 185, 255), width=1)
    draw.text(((bx1 + bx2) // 2, HDR_H // 2), badge_text,
              font=fonts["small"], fill=(200, 205, 255), anchor="mm")


def kpi_card(draw, fonts, x, y, w, h, label: str, color: tuple):
    """Draw a KPI card placeholder."""
    shadow_rect(draw, x, y, x + w, y + h, r=10)
    rounded_rect(draw, x, y, x + w, y + h, 10, fill=WHITE, outline=BORDER, width=1)

    # Left accent strip
    rounded_rect(draw, x, y, x + 4, y + h, 3, fill=color)

    # Label (small uppercase)
    draw.text((x + 16, y + 14), label.upper(),
              font=fonts["small"], fill=MUTED)

    # Placeholder value bar
    r, g, b = color
    bar_fill = (r, g, b, 40)
    rounded_rect(draw, x + 16, y + 36, x + 90, y + 58, 5,
                 fill=(min(r + 180, 255), min(g + 180, 255), min(b + 180, 255)))

    # Hint text
    draw.text((x + 16, y + h - 18), "<- drag measure here",
              font=fonts["small"], fill=(190, 200, 215))

    # Icon circle (top right)
    cx, cy = x + w - 22, y + 24
    rounded_rect(draw, cx - 15, cy - 15, cx + 15, cy + 15, 8,
                 fill=(min(r + 180, 255), min(g + 180, 255), min(b + 180, 255)))


def chart_area(draw, fonts, x, y, w, h, title: str, hint: str = "",
               accent: tuple = INDIGO):
    """Draw a chart placeholder area."""
    shadow_rect(draw, x, y, x + w, y + h, r=12)
    rounded_rect(draw, x, y, x + w, y + h, 12, fill=WHITE, outline=BORDER, width=1)

    # Top accent bar
    rounded_rect(draw, x, y, x + w, y + 4, 3, fill=accent)

    # Title
    draw.text((x + 14, y + 14), title,
              font=fonts["bold"], fill=DARK)

    # Hint / chart type
    if hint:
        draw.text((x + 14, y + 32), hint,
                  font=fonts["small"], fill=MUTED)

    # Subtle grid lines inside the white area
    gy_start = y + (50 if hint else 38)
    gy_end   = y + h - 8
    gx_start = x + 10
    gx_end   = x + w - 10
    for gy in range(gy_start, gy_end, 28):
        draw.line([(gx_start, gy), (gx_end, gy)], fill=(235, 240, 248), width=1)
    for gx in range(gx_start, gx_end, 55):
        draw.line([(gx, gy_start), (gx, gy_end)], fill=(235, 240, 248), width=1)

    # "Place visual here" watermark in center
    cx, cy = x + w // 2, y + (h + 50) // 2
    draw.text((cx, cy), "[ place visual here ]",
              font=fonts["small"], fill=(210, 218, 230), anchor="mm")


def slicer_area(draw, fonts, x, y, w, h, field_name: str):
    """Draw a slicer/filter placeholder."""
    shadow_rect(draw, x, y, x + w, y + h, r=10)
    rounded_rect(draw, x, y, x + w, y + h, 10, fill=WHITE, outline=BORDER, width=1)

    draw.text((x + 14, y + 14), "FILTER",
              font=fonts["small"], fill=MUTED)
    draw.text((x + 14, y + 30), field_name,
              font=fonts["bold"], fill=DARK)

    # Fake dropdown box
    rounded_rect(draw, x + 14, y + 50, x + w - 14, y + 72, 6,
                 fill=SURFACE, outline=BORDER, width=1)
    draw.text((x + 22, y + 56), "Select...",
              font=fonts["small"], fill=(180, 190, 205))
    # Arrow
    draw.polygon([(x + w - 32, y + 62), (x + w - 24, y + 62),
                  (x + w - 28, y + 68)], fill=MUTED)

    draw.text((x + w // 2, y + h - 12), "[ slicer visual ]",
              font=fonts["small"], fill=(210, 218, 230), anchor="mm")


def new_page() -> tuple:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


# ── Pages ─────────────────────────────────────────────────────────────────────

def page1(fonts) -> Image.Image:
    """Executive Overview"""
    img, draw = new_page()
    header(draw, fonts, "Executive Overview")

    # KPI row ─ y=80, h=108
    ky, kh, kw, gap = 80, 108, 295, 14
    kpis = [("Total Employees", INDIGO), ("Absenteeism Rate", RED),
            ("Late Rate", YELLOW), ("Critical Alerts", RED)]
    for i, (label, color) in enumerate(kpis):
        kpi_card(draw, fonts, 20 + i * (kw + gap), ky, kw, kh, label, color)

    # Row 2 ─ y=206, h=240
    r2y, r2h = 206, 240
    chart_area(draw, fonts, 20,  r2y, 630, r2h,
               "Monthly KPI Trends",
               "Line chart · X-axis: annee_mois  · Y-axis: Taux Absentéisme %, Taux Retard %",
               INDIGO)
    chart_area(draw, fonts, 665, r2y, 300, r2h,
               "Employee Status",
               "Donut · Legend: statut · Values: count(employe_id)",
               GREEN)
    chart_area(draw, fonts, 980, r2y, 280, r2h,
               "Absences by Dept",
               "Bar · Y: nom_departement · X: count(absence_id)",
               RED)

    # Row 3 ─ y=460, h=245
    r3y, r3h = 460, 245
    chart_area(draw, fonts, 20,  r3y, 490, r3h,
               "Absences by Department",
               "Horizontal bar · sorted descending",
               RED)
    chart_area(draw, fonts, 525, r3y, 215, r3h,
               "YoY Variation",
               "Card · measure: Variation Absences YoY",
               YELLOW)
    slicer_area(draw, fonts, 755, r3y, 180, r3h, "Year")
    chart_area(draw, fonts, 950, r3y, 310, r3h,
               "Summary Stats",
               "Multi-row card · Absentéisme %, Retard %, Alertes Actives",
               INDIGO)

    return img


def page2(fonts) -> Image.Image:
    """Attendance & Absences"""
    img, draw = new_page()
    header(draw, fonts, "Attendance & Absences")

    # KPI row
    ky, kh, kw, gap = 80, 108, 295, 14
    kpis = [("Present Today", GREEN), ("Late Arrivals", YELLOW),
            ("Justification Rate", INDIGO), ("Missing Clock-Out", RED)]
    for i, (label, color) in enumerate(kpis):
        kpi_card(draw, fonts, 20 + i * (kw + gap), ky, kw, kh, label, color)

    # Area chart (wide)
    chart_area(draw, fonts, 20, 206, 960, 180,
               "Daily Attendance Rate (%)",
               "Area chart · X: date_pointage · Y: Taux Présence %  · filtered by year slicer",
               GREEN)
    slicer_area(draw, fonts, 995, 206, 265, 180, "Year")

    # Heatmap + bar
    chart_area(draw, fonts, 20,  400, 455, 245,
               "Absenteeism Heatmap",
               "Matrix · Rows: nom_mois · Cols: annee · Values: Taux Absentéisme % (gradient red)",
               RED)
    chart_area(draw, fonts, 490, 400, 470, 245,
               "Late Arrivals by Department",
               "Clustered bar · Y: nom_departement · X: Nb Retards · sorted desc",
               YELLOW)
    slicer_area(draw, fonts, 975, 400, 285, 115, "Department")
    chart_area(draw, fonts, 975, 528, 285, 117,
               "Justified vs Unjustified",
               "Stacked bar · nom_mois · Absences Justifiées + Non Justifiées",
               INDIGO)

    # Employee table
    chart_area(draw, fonts, 20, 660, 1240, 50,
               "Employee Attendance Detail - Table: nom_complet · nom_departement · Nb Présents · Nb Retards · Moy Minutes Retard · Taux Présence %",
               "", INDIGO)

    return img


def page3(fonts) -> Image.Image:
    """Leave & Training"""
    img, draw = new_page()
    header(draw, fonts, "Leave & Training")

    # KPI row
    ky, kh, kw, gap = 80, 108, 295, 14
    kpis = [("Total Leave Days", INDIGO), ("Pending Requests", YELLOW),
            ("Training Attendance", GREEN), ("Avg Training Score", PURPLE)]
    for i, (label, color) in enumerate(kpis):
        kpi_card(draw, fonts, 20 + i * (kw + gap), ky, kw, kh, label, color)

    # Row 2: leave visuals
    chart_area(draw, fonts, 20,  206, 355, 245,
               "Leave Type Distribution",
               "Donut · Legend: type_conge · Values: SUM(nb_jours)",
               INDIGO)
    chart_area(draw, fonts, 390, 206, 355, 245,
               "Leave Days by Department",
               "Clustered bar · Y: nom_departement · X: Total Jours Congé",
               INDIGO)
    chart_area(draw, fonts, 760, 206, 500, 245,
               "Training Sessions by Type",
               "Column chart · X: type_formation · Y: DISTINCTCOUNT(formation_id)",
               GREEN)

    # Row 3: leave trend + training table
    chart_area(draw, fonts, 20,  465, 430, 240,
               "Leave Requests Over Time",
               "Line chart · X: annee · Y: count(conge_id) · Legend: statut",
               YELLOW)
    chart_area(draw, fonts, 465, 465, 795, 240,
               "Training Sessions Detail - Table: titre · type_formation · annee · Taux Participation Formation % · Score Moy Formation",
               "Table visual", GREEN)

    return img


def page4(fonts) -> Image.Image:
    """AI Alerts & Missions"""
    img, draw = new_page()
    header(draw, fonts, "AI Alerts & Missions")

    # KPI row - 5 cards
    ky, kh, kw, gap = 80, 108, 232, 11
    kpis = [("Critical Alerts", RED), ("At-Risk Employees", YELLOW),
            ("Total Missions", INDIGO), ("Intl Missions", PURPLE),
            ("Alerts Read Rate", GREEN)]
    for i, (label, color) in enumerate(kpis):
        kpi_card(draw, fonts, 20 + i * (kw + gap), ky, kw, kh, label, color)

    # Row 2: donut + bar + line
    chart_area(draw, fonts, 20,  206, 305, 258,
               "Alert Levels",
               "Donut · Legend: niveau · Values: count(alerte_id)",
               RED)
    chart_area(draw, fonts, 340, 206, 440, 258,
               "Critical Alerts by Department",
               "Clustered bar · Y: nom_departement · X: Alertes Critiques (total)",
               RED)
    chart_area(draw, fonts, 795, 206, 465, 258,
               "Alert Trend Over Time",
               "Line chart · X: annee_mois · Y: Total Alertes · Legend: niveau",
               INDIGO)

    # Row 3: table + mission charts
    chart_area(draw, fonts, 20,  478, 545, 230,
               "At-Risk Employees",
               "Table: nom_complet · nom_departement · Total Alertes · Alertes Critiques (total)",
               RED)
    chart_area(draw, fonts, 580, 478, 325, 230,
               "Missions by Type",
               "Column chart · X: type_mission · Y: count(mission_id)",
               INDIGO)
    chart_area(draw, fonts, 920, 478, 340, 230,
               "Missions by Status",
               "Column chart · X: statut · Y: count(mission_id) · custom colors",
               GREEN)

    # Slicers panel
    slicer_area(draw, fonts, 1275 - 180, 206, 165, 120, "Alert Level")
    slicer_area(draw, fonts, 1275 - 180, 340, 165, 120, "Year")

    return img


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    out_dir = os.path.join(os.path.dirname(__file__), "backgrounds")
    os.makedirs(out_dir, exist_ok=True)

    fonts = load_fonts()

    pages = [
        ("page1_executive_overview.png",  page1),
        ("page2_attendance_absences.png", page2),
        ("page3_leave_training.png",      page3),
        ("page4_ai_alerts_missions.png",  page4),
    ]

    for filename, gen in pages:
        print(f"  Generating {filename} ...", end=" ")
        img = gen(fonts)
        path = os.path.join(out_dir, filename)
        img.save(path, "PNG")
        print("done")

    print(f"\nAll 4 backgrounds saved to:  {out_dir}")
    print()
    print("HOW TO USE IN POWER BI DESKTOP:")
    print("  1. Open the page (e.g. 'Executive Overview')")
    print("  2. Format pane > Canvas background > Image > Browse")
    print("  3. Select the matching PNG")
    print("  4. Image fit: Fit   |   Transparency: 0%")
    print("  5. Drag your visuals on top of the white boxes")
    print("  6. Match the measure/field exactly as shown in the hint text on each box")


if __name__ == "__main__":
    main()
