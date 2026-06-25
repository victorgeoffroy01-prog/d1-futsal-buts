"""
================================================================================
ANALYSE DES BUTS — D1 FUTSAL   (v2.2 — correctifs visuels)
================================================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from io import BytesIO
import plotly.graph_objects as go
from PIL import Image
import base64
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF

# ============================================================================
# CONFIG & CHARTE
# ============================================================================
DB_PATH   = "futsal_d1.db"
XLSX_PATH    = "But_D1.xlsx"      # source de vérité : la base est reconstruite à partir de ce fichier
SCHEMA_PATH  = "schema_buts.sql"  # schéma SQL utilisé pour (re)construire la base
LOGO_D1   = Path("D1_Futsal_logo.png")
LOGOS_DIR = Path("logos")

D1_ROUGE       = "#0096C7"
D1_ROUGE_CLAIR = "#48CAE4"
D1_BORDEAUX    = "#1A1E2E"
D1_BORDEAUX_2  = "#252A3A"
D1_ANTHRACITE  = "#0F1117"
D1_CARTE       = "#1A1E2E"
D1_BLANC       = "#E8EDF2"
D1_GRIS        = "#8895A7"
D1_OR          = "#F4A261"
D1_VERT        = "#2DC653"
D1_BLEU        = "#0096C7"
D1_DANGER      = "#E03045"   # rouge sémantique — défaites, danger, irrégularité

# Couleurs issues des logos (extraites + ajustées pour lisibilité)
COULEUR_EQUIPE = {
    "ETOILE LAVALLOISE FC":  "#D2784B",   # orange du logo
    "SPORTING CLUB PARIS":   "#1E7A5F",   # vert foncé
    "MONTPELLIER MED. F.":   "#E10000",   # rouge vif
    "TOULON METROPOLE F.":   "#8C3A20",   # bordeaux/brun
    "GOAL FUTSAL CLUB":      "#A08C64",   # or/beige
    "NANTES METROPOLE F.":   "#1A2D5A",   # marine
    "PARIS ACASA":           "#14783C",   # vert moyen
    "AS AVION FUTSAL":       "#4A4A4A",   # gris anthracite
    "UJS TOULOUSE":          "#8C0000",   # rouge bordeaux
    "NICE FUTSAL CLUB":      "#5A5A5A",   # gris
    "FC KINGERSHEIM":        "#C814A0",   # rose/violet
}
PALETTE = list(COULEUR_EQUIPE.values())

st.set_page_config(
    page_title="D1 Futsal — Analyse des buts",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLE — injection fiable en blocs séparés
# ============================================================================
_CSS_BASE = f"""
<style>
.stApp {{background:{D1_ANTHRACITE}}}
html,body,[class*="css"],.stMarkdown,.stMetric,button,input,select,textarea{{
    font-family:'Inter',-apple-system,sans-serif!important}}
.block-container{{padding-top:1.1rem;padding-bottom:2rem;max-width:1400px}}
h1{{color:{D1_BLANC}!important;border-bottom:2px solid {D1_ROUGE};
    padding-bottom:.25rem;letter-spacing:-.3px;font-size:1.55rem!important;
    margin-bottom:1.4rem!important}}
h2,h3{{color:{D1_BLANC}!important;font-weight:600!important}}
h3{{font-size:.98rem!important;margin-top:1rem!important;margin-bottom:.25rem!important;
    border-left:3px solid {D1_ROUGE};padding-left:.5rem}}
p,label,span,div{{color:{D1_BLANC}}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,{D1_BORDEAUX} 0%,#0A0E18 100%);border-right:1px solid {D1_BORDEAUX_2};
    min-width:255px!important;max-width:255px!important}}
[data-testid="stSidebar"] *{{color:{D1_BLANC}!important}}
.nav-cat{{font-size:.64rem;font-weight:800;letter-spacing:.8px;color:{D1_OR}!important;
    text-transform:uppercase;margin:.65rem 0 .18rem .2rem;opacity:.85}}
[data-testid="stSidebar"] .stButton>button{{
    text-align:left;justify-content:flex-start;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis;width:100%;
    background:transparent;border:none;color:{D1_BLANC}!important;
    font-size:.84rem;font-weight:500;padding:.3rem .55rem;border-radius:6px;
    margin:.03rem 0;transition:background .1s;box-shadow:none!important}}
[data-testid="stSidebar"] .stButton>button:hover{{background:rgba(255,255,255,.1)!important}}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{{
    background:{D1_ROUGE}!important;color:white!important;font-weight:700}}
[data-testid="stSidebar"] .stButton>button[kind="primary"]:hover{{background:{D1_ROUGE_CLAIR}!important}}
[data-testid="stMetric"]{{background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:10px;padding:.65rem .85rem}}
[data-testid="stMetricValue"]{{font-size:1.4rem!important;font-weight:800;color:{D1_BLANC}}}
[data-testid="stMetricLabel"]{{font-size:.7rem;color:{D1_GRIS};font-weight:500;text-transform:uppercase;letter-spacing:.4px}}
.stSelectbox>div>div,.stMultiSelect>div>div{{background:{D1_CARTE}!important;border:1px solid {D1_BORDEAUX_2}!important;border-radius:7px!important}}
div[data-baseweb="select"] *{{color:{D1_BLANC}!important}}
.stDownloadButton>button{{background:{D1_ROUGE}!important;color:white!important;border:none!important;
    border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.3rem .85rem!important}}
.stDownloadButton>button:hover{{background:{D1_ROUGE_CLAIR}!important}}
.stTabs [data-baseweb="tab-list"]{{
    gap:6px;border-bottom:2px solid {D1_BORDEAUX_2}!important;padding-bottom:0}}
.stTabs [data-baseweb="tab"]{{
    font-size:.95rem!important;font-weight:600!important;
    padding:.55rem 1.2rem!important;
    border-radius:8px 8px 0 0!important;
    border:1px solid {D1_BORDEAUX_2}!important;
    border-bottom:none!important;
    background:{D1_CARTE}!important;
    color:{D1_GRIS}!important;
    cursor:pointer;transition:all .15s;
    margin-bottom:-2px}}
.stTabs [data-baseweb="tab"]:hover{{
    background:rgba(192,0,24,.12)!important;
    color:{D1_BLANC}!important;
    border-color:{D1_ROUGE}!important}}
.stTabs [aria-selected="true"]{{
    color:{D1_BLANC}!important;
    background:{D1_BORDEAUX}!important;
    border-color:{D1_ROUGE}!important;
    border-bottom:2px solid {D1_BORDEAUX}!important}}

/* ============ RESPONSIVE : tablette & téléphone ============ */
/* Tablette paysage et fenêtres réduites */
@media (max-width: 1024px) {{
    .block-container{{padding-left:1rem!important;padding-right:1rem!important;
        padding-top:.9rem!important}}
}}
/* Tablette portrait */
@media (max-width: 768px) {{
    h1{{font-size:1.3rem!important;margin-bottom:1rem!important}}
    h2{{font-size:1.05rem!important}}
    h3{{font-size:.92rem!important}}
    /* Les rangées de st.columns passent en flex-wrap : si une colonne ne
       tient pas, elle redescend à la ligne au lieu d'être écrasée */
    div[data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important;gap:.4rem!important}}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{{
        min-width:48%!important;flex:1 1 48%!important;
        margin-bottom:.25rem}}
    [data-testid="stMetricValue"]{{font-size:1.2rem!important}}
    [data-testid="stMetric"]{{padding:.55rem .7rem!important}}
    [data-testid="stSidebar"]{{min-width:240px!important;max-width:80%!important}}
    .stTabs [data-baseweb="tab"]{{
        font-size:.82rem!important;padding:.4rem .7rem!important}}
}}
/* Téléphone : tout en pleine largeur */
@media (max-width: 480px) {{
    .block-container{{padding-top:.5rem!important;padding-left:.7rem!important;
        padding-right:.7rem!important}}
    h1{{font-size:1.15rem!important;margin-bottom:.8rem!important;
        padding-bottom:.2rem!important}}
    h2,h3{{font-size:.88rem!important;margin-top:.7rem!important}}
    /* Toutes les colonnes empilées une par ligne */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{{
        min-width:100%!important;flex:1 1 100%!important}}
    [data-testid="stMetricValue"]{{font-size:1.1rem!important}}
    [data-testid="stMetricLabel"]{{font-size:.65rem!important}}
    [data-testid="stMetric"]{{padding:.45rem .6rem!important}}
    .stTabs [data-baseweb="tab"]{{
        font-size:.75rem!important;padding:.35rem .55rem!important}}
    /* Tableaux dataframe : un peu plus compacts */
    [data-testid="stDataFrame"]{{font-size:.82rem!important}}
    /* Selectbox plus petits */
    .stSelectbox>div>div,.stMultiSelect>div>div{{font-size:.85rem!important}}
}}
</style>
"""

_CSS_CLT = f"""
<style>
.clt-wrap{{border-radius:10px;overflow:hidden;border:1px solid {D1_BORDEAUX_2}}}
.clt-head{{display:flex;align-items:center;gap:8px;padding:.3rem .75rem;
    background:{D1_BORDEAUX_2};font-size:.68rem;font-weight:700;
    text-transform:uppercase;letter-spacing:.5px;color:{D1_GRIS}}}
.clt-row{{display:flex;align-items:center;gap:8px;padding:.38rem .75rem;
    border-bottom:1px solid rgba(255,255,255,.04);transition:background .1s}}
.clt-row:last-child{{border-bottom:none}}
.clt-row:hover{{background:rgba(255,255,255,.035)}}
.w-rang{{width:20px;flex-shrink:0;font-weight:700;font-size:.82rem;color:{D1_GRIS}}}
.w-rang.or{{color:{D1_OR}}}
.w-logo{{width:28px;flex-shrink:0;display:flex;align-items:center}}
.w-nom{{flex:1;font-weight:600;font-size:.85rem}}
.w-pts{{width:32px;text-align:center;font-weight:800;font-size:1rem;color:{D1_ROUGE_CLAIR};flex-shrink:0}}
.w-vnpd{{width:86px;text-align:center;font-size:.75rem;color:{D1_GRIS};flex-shrink:0}}
.w-buts{{width:66px;text-align:center;font-size:.78rem;flex-shrink:0}}
.w-diff{{width:38px;text-align:center;font-size:.78rem;font-weight:600;flex-shrink:0}}
.w-forme{{width:110px;text-align:right;flex-shrink:0}}

/* ===== Classement responsive : tout reste visible, scroll horizontal ===== */
.clt-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
.clt-head,.clt-row{{min-width:560px}}
@media (max-width: 768px) {{
    .clt-head,.clt-row{{padding:.35rem .55rem;gap:6px}}
    .w-rang{{font-size:.78rem}}
    .w-nom{{font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .w-pts{{font-size:.95rem}}
    .w-vnpd{{font-size:.7rem}}
    .w-buts{{font-size:.74rem}}
    .w-diff{{font-size:.74rem}}
}}
.fr{{display:inline-block;width:17px;height:17px;border-radius:50%;
    font-size:.62rem;font-weight:700;text-align:center;line-height:17px;margin:1px}}
.fr-V{{background:{D1_VERT};color:white}}
.fr-N{{background:{D1_OR};color:#1a1a1e}}
.fr-D{{background:{D1_DANGER};color:white}}
.note{{color:{D1_GRIS};font-size:.76rem;font-style:italic;margin:.15rem 0}}
.pod{{background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:11px;padding:.9rem;text-align:center}}
.tag{{display:inline-block;padding:.12rem .5rem;border-radius:4px;font-weight:600;font-size:.75rem}}
</style>
"""

st.markdown(_CSS_BASE, unsafe_allow_html=True)
st.markdown(_CSS_CLT,  unsafe_allow_html=True)

# ============================================================================
# HELPERS
# ============================================================================
def logo_b64(nom, size=28):
    p = LOGOS_DIR / f"{nom}.png"
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
            img.thumbnail((size*2, size*2), Image.LANCZOS)
            buf = BytesIO(); img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return (f'<img src="data:image/png;base64,{b64}" width="{size}" height="{size}" '
                    f'style="object-fit:contain;border-radius:3px;vertical-align:middle">')
        except Exception:
            pass
    coul = COULEUR_EQUIPE.get(nom, D1_ROUGE)
    ini  = "".join(w[0] for w in nom.split()[:2])
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{coul};'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'font-weight:800;font-size:{max(9,size//3)}px;color:white;vertical-align:middle">'
            f'{ini}</div>')

def forme_ronds(resultats):
    return "".join(f'<span class="fr fr-{r}">{r}</span>' for r in resultats[-5:])

def hex_to_rgba(h, a=0.28):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

def style_fig(fig, h=320, titre=None):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=D1_BLANC, size=14), height=h,
        margin=dict(l=8, r=8, t=40 if titre else 16, b=8),
        title=dict(text=titre or "", font=dict(size=15, color=D1_BLANC)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        uniformtext=dict(minsize=11, mode="show"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False,
                     tickfont=dict(size=13, color=D1_BLANC))
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False,
                     tickfont=dict(size=13, color=D1_BLANC))
    return fig

def barh_equipes(noms, vals, h=320, texte=None, opacite=1.0):
    """Barres horizontales couleur équipe, noms courts sur l'axe."""
    fig = go.Figure()
    for nom, val in zip(noms, vals):
        coul = COULEUR_EQUIPE.get(nom, D1_ROUGE)
        if opacite < 1:
            coul = hex_to_rgba(coul, opacite)
        fig.add_trace(go.Bar(
            x=[val], y=[nc(nom)], orientation="h",   # nom court sur axe
            marker_color=coul,
            text=[str(int(val))], textposition="outside",
            textangle=0, textfont=dict(size=14, color=D1_BLANC),
            cliponaxis=False,
            showlegend=False, name=nc(nom),
        ))
    fig.update_yaxes(autorange="reversed")
    fig2 = style_fig(fig, h)
    fig2.update_layout(margin=dict(l=8, r=44, t=16, b=8))
    fig2.update_xaxes(showticklabels=False)
    return fig2

def barv_simple(x, y, couleur=D1_ROUGE, h=280, titre=None):
    if isinstance(couleur, list):
        mc = dict(color=couleur)
    else:
        mc = dict(color=couleur)
    fig = go.Figure(go.Bar(x=x, y=y, marker=mc,
                           text=y, textposition="outside", textangle=0))
    fig.update_yaxes(showticklabels=False)
    return style_fig(fig, h, titre)

def dl_csv(df, label, nom):
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nom, mime="text/csv")

# ============================================================================
# DONNÉES
# ============================================================================
@st.cache_data
def charger():
    # La base SQLite est reconstruite automatiquement à partir de But_D1.xlsx
    # au démarrage (source de vérité unique). Plus besoin de pousser le .db :
    # il suffit de mettre à jour But_D1.xlsx dans le dépôt et de redéployer.
    if Path(XLSX_PATH).exists() and Path(SCHEMA_PATH).exists():
        try:
            import openpyxl
            import migration_buts as mig
            wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
            buts = mig.lire_buts_principale(wb)
            origines = mig.lire_origines(wb)
            for b in buts:
                cle = mig.cle_rattachement(
                    b["journee"], b["minute"], b["periode"], b["joueur"]
                )
                if cle in origines:
                    b["origine"] = origines[cle]
            mig.construire_base(buts).close()      # (ré)écrit futsal_d1.db
        except Exception as e:
            # Reconstruction impossible : on se rabat sur une base déjà présente.
            if not Path(DB_PATH).exists():
                st.error(f"Reconstruction de la base impossible : {e}")
                return None
    if not Path(DB_PATH).exists():
        return None
    return pd.read_sql_query("SELECT * FROM but", sqlite3.connect(DB_PATH))

df_full = charger()
if df_full is None:
    st.error("Données introuvables : `But_D1.xlsx` (+ `schema_buts.sql`) ou `futsal_d1.db` doit être présent dans le dépôt.")
    st.stop()

# Sépare saison régulière et phase finale. La journée des matchs de phase finale
# est saisie sous forme texte : PO1 (demi aller), PO2 (demi retour), POF (finale).
# Tout le code existant continue à travailler sur df = saison régulière, comme
# avant. La phase finale a ses pages dédiées (univers PHASE FINALE).
_phase_po = df_full["journee"].astype(str).str.upper().str.startswith("PO")
df_po = df_full[_phase_po].copy()
df    = df_full[~_phase_po].copy()
# Garde les journées numériques triées comme entiers
df["journee"] = pd.to_numeric(df["journee"], errors="coerce").astype("Int64")
df = df.dropna(subset=["journee"])

EQUIPES   = sorted(df["equipe_marque"].dropna().unique().tolist())
JOURNEES  = sorted([int(j) for j in df["journee"].dropna().unique().tolist()])
EQUIPES_AVEC_ORIGINE = sorted(
    df.loc[df["origine"].notna(), "equipe_marque"].dropna().unique().tolist()
)

# Noms courts pour graphes (quand la place manque)
NOM_COURT = {
    "ETOILE LAVALLOISE FC":  "LAVAL",
    "UJS TOULOUSE":          "TOULOUSE",
    "AS AVION FUTSAL":       "AVION",
    "GOAL FUTSAL CLUB":      "GOAL",
    "NANTES METROPOLE F.":   "NANTES",
    "PARIS ACASA":           "ACASA",
    "TOULON METROPOLE F.":   "TOULON",
    "MONTPELLIER MED. F.":   "MONTPELLIER",
    "SPORTING CLUB PARIS":   "PARIS",
    "FC KINGERSHEIM":        "KINGERSHEIM",
    "NICE FUTSAL CLUB":      "NICE",
}
def nc(eq):
    """Nom court pour axes de graphes."""
    return NOM_COURT.get(eq, eq.split()[0])
def ncs(liste):
    return [nc(e) for e in liste]

def _nom_famille(nom):
    parts = str(nom).strip().split()
    return parts[-1] if parts else str(nom)

def _construire_noms_affiche(noms):
    """Construit {nom_complet: label} pour les graphes.
    Si plusieurs joueurs partagent le même nom de famille (frères, homonymes),
    on préfixe l'initiale du prénom (ex: 'I. AHSSEN' / 'Y. AHSSEN').
    En cas de même initiale aussi, on garde le prénom complet."""
    from collections import defaultdict
    groupes = defaultdict(list)
    for n in noms:
        groupes[_nom_famille(n).upper()].append(n)
    mapping = {}
    for fam, membres in groupes.items():
        if len(membres) <= 1:
            mapping[membres[0]] = _nom_famille(membres[0])
            continue
        par_initiale = defaultdict(list)
        for n in membres:
            parts = n.strip().split()
            ini = parts[0][0].upper() if len(parts) > 1 and parts[0] else ""
            par_initiale[ini].append(n)
        for ini, lst in par_initiale.items():
            if len(lst) == 1:
                mapping[lst[0]] = f"{ini}. {_nom_famille(lst[0])}" if ini else _nom_famille(lst[0])
            else:
                for n in lst:  # même initiale -> prénom complet
                    prenom = n.strip().split()[0]
                    mapping[n] = f"{prenom} {_nom_famille(n)}"
    return mapping

NOM_AFFICHE = _construire_noms_affiche(df["joueur"].dropna().unique().tolist())

def nj(nom, court=False):
    """Label de buteur pour les graphes : nom de famille, avec initiale du
    prénom si un homonyme existe (frères, etc.)."""
    return NOM_AFFICHE.get(nom, _nom_famille(nom))

def njs(liste):
    return [nj(n) for n in liste]

# Buts non attribuables à un buteur : contre son camp (CSC) et buteur inconnu
# ('?', ex. match forfait). Crédités à l'équipe (score, buts pour) mais exclus
# de tous les classements/fiches de buteurs.
CSC = "CSC"
NON_BUTEURS = {"CSC", "?"}
def sans_csc(d):
    """Retire les buts non rattachables à un buteur (CSC, buteur inconnu '?')."""
    return d[~d["joueur"].astype(str).str.strip().str.upper().isin(NON_BUTEURS)]

# ============================================================================
# FONCTIONS MÉTIER
# ============================================================================
@st.cache_data
def construire_matchs():
    rows = []
    for (j, dom, ext), g in df.groupby(["journee","equipe_domicile","equipe_exterieure"]):
        bd = int((g["equipe_marque"]==dom).sum())
        be = int((g["equipe_marque"]==ext).sum())
        rows.append({"journee":j,"dom":dom,"ext":ext,"score_dom":bd,"score_ext":be,
                     "res_dom":"V" if bd>be else("N" if bd==be else "D"),
                     "res_ext":"D" if bd>be else("N" if bd==be else "V"),
                     "total_buts":bd+be})
    return pd.DataFrame(rows).sort_values(["journee","dom"]).reset_index(drop=True)

@st.cache_data
def construire_classement():
    matchs = construire_matchs()
    rows = []
    for eq in EQUIPES:
        jdom = list(matchs[matchs["dom"]==eq][["journee","res_dom"]].sort_values("journee").itertuples(index=False))
        jext = list(matchs[matchs["ext"]==eq][["journee","res_ext"]].sort_values("journee").itertuples(index=False))
        hist = sorted([(r.journee, r.res_dom) for r in jdom]+[(r.journee, r.res_ext) for r in jext])
        res  = [r for _,r in hist]
        v=res.count("V"); n=res.count("N"); d=res.count("D")
        bp=int(df[df["equipe_marque"]==eq].shape[0])
        bc=int(df[df["equipe_encaisse"]==eq].shape[0])
        rows.append({"equipe":eq,"J":len(res),"V":v,"N":n,"D":d,
                     "Pts":3*v+n,"BP":bp,"BC":bc,"Diff":bp-bc,"forme":res})
    return (pd.DataFrame(rows)
            .sort_values(["Pts","Diff","BP"], ascending=[False,False,False])
            .reset_index(drop=True))

@st.cache_data
def evolution_classement():
    matchs = construire_matchs()
    rows = []
    for eq in EQUIPES:
        pts = 0
        for j in JOURNEES:
            mj = matchs[matchs["journee"]==j]
            for _,m in mj[mj["dom"]==eq].iterrows():
                pts += 3 if m["res_dom"]=="V" else(1 if m["res_dom"]=="N" else 0)
            for _,m in mj[mj["ext"]==eq].iterrows():
                pts += 3 if m["res_ext"]=="V" else(1 if m["res_ext"]=="N" else 0)
            rows.append({"equipe":eq,"journee":j,"pts":pts})
    return pd.DataFrame(rows)

def reconstruire_score(df_match, dom, ext):
    # Les minutes sont absolues (1-40 sur tout le match)
    buts = df_match.sort_values(["periode","minute"], na_position="last")
    sd, se = 0, 0
    evts = []
    for _, b in buts.iterrows():
        if b["equipe_marque"]==dom: sd+=1
        else: se+=1
        evts.append({"minute": int(b["minute"]) if pd.notna(b["minute"]) else None,
                     "periode": int(b["periode"]) if pd.notna(b["periode"]) else None,
                     "equipe":b["equipe_marque"],"joueur":b["joueur"],
                     "score_dom":sd,"score_ext":se,
                     "origine":b["origine"] if pd.notna(b["origine"]) else "—"})
    return evts

# ============================================================================
# HELPERS — PHASE FINALE
# ============================================================================
def _matchs_phase(phase):
    """Liste des matchs d'une phase finale (PO1/PO2/POF) sous forme
    [(dom, ext, score_dom, score_ext, df_match), ...]"""
    sub = df_po[df_po["journee"].astype(str).str.upper() == phase]
    res = []
    for (dom, ext), g in sub.groupby(["equipe_domicile", "equipe_exterieure"]):
        sd = int((g["equipe_marque"] == dom).sum())
        se = int((g["equipe_marque"] == ext).sum())
        res.append((dom, ext, sd, se, g))
    return res


def _bloc_match(dom, ext, sd, se, label, joue=True):
    """Carte HTML d'un match aller/retour/finale."""
    coul_d = COULEUR_EQUIPE.get(dom, D1_ROUGE)
    coul_e = COULEUR_EQUIPE.get(ext, D1_BLEU)
    if joue:
        score_html = (f'<span style="font-size:1.4rem;font-weight:700;color:{D1_BLANC}">'
                      f'{sd} <span style="color:{D1_GRIS};font-weight:400">–</span> {se}</span>')
    else:
        score_html = f'<span style="color:{D1_GRIS};font-style:italic">à venir</span>'
    return (
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-radius:8px;padding:.7rem .9rem;margin:.4rem 0">'
        f'<div style="color:{D1_GRIS};font-size:.7rem;text-transform:uppercase;'
        f'letter-spacing:.5px;margin-bottom:.3rem">{label}</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.6rem">'
        f'<span style="border-left:3px solid {coul_d};padding-left:.5rem;'
        f'font-size:.9rem">{nc(dom)}</span>'
        f'{score_html}'
        f'<span style="border-right:3px solid {coul_e};padding-right:.5rem;'
        f'font-size:.9rem;text-align:right">{nc(ext)}</span>'
        f'</div></div>'
    )


def _qualifie(pair_matches):
    """Renvoie l'équipe qualifiée d'une double confrontation, ou None si
    incomplet / égalité parfaite (à départager en prolongation/TAB)."""
    if len(pair_matches) < 2:
        return None
    score = defaultdict(int)
    for dom, ext, sd, se, _ in pair_matches:
        score[dom] += sd
        score[ext] += se
    eqs = list(score.keys())
    if len(eqs) != 2:
        return None
    a, b = eqs
    if score[a] > score[b]: return a
    if score[b] > score[a]: return b
    return None


def _detail_match_po(dom, ext, dfm):
    """Affiche la chronologie et les origines d'un match PO."""
    g = dfm.sort_values(["periode", "minute"], na_position="last")
    sd, se = 0, 0
    for _, b in g.iterrows():
        if b["equipe_marque"] == dom: sd += 1
        else: se += 1
        coul = COULEUR_EQUIPE.get(b["equipe_marque"], D1_ROUGE)
        is_dom = (b["equipe_marque"] == dom)
        align = "flex-start" if is_dom else "flex-end"
        mi = f"{int(b['minute'])}'" if pd.notna(b["minute"]) else "?"
        per = f"P{int(b['periode'])}" if pd.notna(b["periode"]) else ""
        orig = (f" <span style='color:{D1_GRIS};font-size:.72rem'>· {b['origine']}</span>"
                if pd.notna(b["origine"]) else "")
        st.markdown(
            f'<div style="display:flex;justify-content:{align};margin:.18rem 0">'
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-left:3px solid {coul};border-radius:7px;padding:.3rem .7rem;max-width:60%">'
            f'<b style="font-size:.86rem">{b["joueur"]}</b>'
            f'<span style="color:{D1_GRIS};font-size:.76rem"> {per} {mi}</span>'
            f'<b style="color:{coul}"> {sd}–{se}</b>{orig}'
            f'</div></div>',
            unsafe_allow_html=True
        )
    # Origines du match si renseignées
    oo = g["origine"].dropna()
    if len(oo):
        rep = oo.value_counts()
        st.markdown(f"<p class='note' style='margin-top:.5rem'><b>Origines :</b> " +
                    " · ".join(f"{o} ({n})" for o, n in rep.items()) + "</p>",
                    unsafe_allow_html=True)


def _stats_po_equipe(eq):
    """Stats d'une équipe sur l'ensemble de la phase finale."""
    pour = df_po[df_po["equipe_marque"] == eq]
    contre = df_po[df_po["equipe_encaisse"] == eq]
    # matchs joués (paires uniques journee+dom+ext impliquant l'équipe)
    matchs = df_po[(df_po["equipe_domicile"] == eq) | (df_po["equipe_exterieure"] == eq)]
    n_matchs = matchs.groupby(["journee", "equipe_domicile", "equipe_exterieure"]).ngroups
    return {
        "matchs": n_matchs,
        "buts_pour": len(pour),
        "buts_contre": len(contre),
        "diff": len(pour) - len(contre),
        "pour_df": pour,
        "contre_df": contre,
    }

# ============================================================================
# SIDEBAR — navigation par catégories
# ============================================================================
NAV = {
    "CHAMPIONNAT": [("🏠", "Accueil"), ("🏆", "Classement"),
                    ("⚽", "Fiche match"), ("⏱", "Profil temporel"),
                    ("📊", "Dynamique de score"), ("📈", "Analyse avancée"),
                    ("🧤", "Power play")],
    "ÉQUIPES":     [("🛡", "Fiche équipe"), ("⚔", "Confrontations"),
                    ("📋", "Rapport équipe")],
    "JOUEURS":     [("👟", "Buteurs"), ("🆚", "Comparateur")],
    "PHASE FINALE":[("🏅", "Bracket"), ("🛡", "Stats équipes PO"),
                    ("🎯", "Buteurs PO"), ("🎬", "Origines PO")],
    "MÉTHODO":     [("📖", "Méthodo & Couverture")],
}

if "page" not in st.session_state:
    st.session_state.page = "Accueil"

with st.sidebar:
    if LOGO_D1.exists():
        st.image(str(LOGO_D1), width=84)
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    for cat, items in NAV.items():
        st.markdown(f"<div class='nav-cat'>{cat}</div>", unsafe_allow_html=True)
        for emoji, nom in items:
            actif = (st.session_state.page == nom)
            if st.button(f"{emoji}  {nom}", key=f"nav_{nom}",
                         use_container_width=True,
                         type="primary" if actif else "secondary"):
                st.session_state.page = nom
                st.rerun()
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.caption(f"{len(df)} buts · {len(EQUIPES)} équipes · J{min(JOURNEES)}–J{max(JOURNEES)}")
    if len(df_po):
        st.caption(f"Phase finale : {len(df_po)} buts")

page = st.session_state.page

# Quand l'utilisateur change de page, on remonte automatiquement en haut.
if st.session_state.get("_last_page") != page:
    st.session_state._last_page = page
    import streamlit.components.v1 as _components
    _components.html(
        "<script>window.parent.scrollTo({top:0, behavior:'instant'});</script>",
        height=0
    )

# Mémoire de l'équipe sélectionnée entre pages
if "equipe_sel" not in st.session_state:
    st.session_state.equipe_sel = EQUIPES[0]

def sel_equipe(label="Équipe", key=None):
    """Selectbox équipe avec mémoire entre pages."""
    idx = EQUIPES.index(st.session_state.equipe_sel) if st.session_state.equipe_sel in EQUIPES else 0
    k = key or f"eq_{page.replace(' ','_').replace('/','_')}"
    eq = st.selectbox(label, EQUIPES, index=idx, key=k)
    st.session_state.equipe_sel = eq
    return eq

# ============================================================================
# PDF
# ============================================================================
def pdf_tableau(titre, sous_titre, df_tab, note=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,topMargin=1.5*cm,bottomMargin=1.5*cm,leftMargin=1.5*cm,rightMargin=1.5*cm)
    styles = getSampleStyleSheet(); rouge = colors.HexColor(D1_ROUGE)
    h   = ParagraphStyle("h",parent=styles["Title"],textColor=rouge,fontSize=17,alignment=TA_CENTER,spaceAfter=4)
    sub = ParagraphStyle("sub",parent=styles["Normal"],textColor=colors.grey,fontSize=10,alignment=TA_CENTER,spaceAfter=14)
    nt  = ParagraphStyle("nt",parent=styles["Normal"],textColor=colors.grey,fontSize=8,alignment=TA_CENTER,spaceBefore=10)
    elems = []
    if LOGO_D1.exists():
        try:
            img=RLImage(str(LOGO_D1),width=2.2*cm,height=2.35*cm); img.hAlign="CENTER"; elems+=[img,Spacer(1,6)]
        except Exception: pass
    elems += [Paragraph(titre,h),Paragraph(sous_titre,sub)]
    data = [list(df_tab.columns)]+df_tab.astype(str).values.tolist()
    t = Table(data,repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),rouge),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#ECEFF4")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#2A3348")),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    elems.append(t)
    if note: elems.append(Paragraph(note,nt))
    doc.build(elems); buf.seek(0)
    return buf


# ---- Helpers PDF visuels ----
def _pdf_header(elems, styles, titre, sous_titre):
    rouge = colors.HexColor(D1_ROUGE)
    h   = ParagraphStyle("h2",parent=styles["Title"],textColor=rouge,fontSize=16,alignment=TA_CENTER,spaceAfter=3)
    sub = ParagraphStyle("s2",parent=styles["Normal"],textColor=colors.grey,fontSize=9,alignment=TA_CENTER,spaceAfter=10)
    if LOGO_D1.exists():
        try:
            img=RLImage(str(LOGO_D1),width=1.8*cm,height=1.9*cm); img.hAlign="CENTER"; elems+=[img,Spacer(1,4)]
        except Exception: pass
    elems += [Paragraph(titre,h), Paragraph(sous_titre,sub),
              HRFlowable(width="100%",thickness=1.5,color=rouge,spaceAfter=8)]

def _pdf_stat_row(label, valeur, couleur_hex=None):
    """Ligne label + valeur avec couleur optionnelle."""
    rouge = colors.HexColor(couleur_hex or D1_ROUGE)
    data  = [[label, str(valeur)]]
    t = Table(data, colWidths=[12*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,0),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),9),
        ("TEXTCOLOR",(1,0),(1,0),rouge),("FONTNAME",(1,0),(1,0),"Helvetica-Bold"),
        ("ALIGN",(1,0),(1,0),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LINEBELOW",(0,0),(-1,0),0.3,colors.HexColor("#E0D0D3")),
    ]))
    return t

def _pdf_barre(val, max_val, width_cm=14, height=10, couleur_hex=D1_ROUGE):
    w = width_cm*cm
    d = Drawing(w, height+2)
    d.add(Rect(0,0,w,height,fillColor=colors.HexColor("#1A2540"),strokeColor=None))
    if max_val>0:
        fw = val/max_val*w
        d.add(Rect(0,0,fw,height,fillColor=colors.HexColor(couleur_hex),strokeColor=None))
    return d

def _pdf_section(titre, styles):
    rouge = colors.HexColor(D1_ROUGE)
    s = ParagraphStyle("sec",parent=styles["Normal"],textColor=rouge,
                       fontSize=11,fontName="Helvetica-Bold",spaceBefore=10,spaceAfter=4)
    return Paragraph(titre, s)


def pdf_scouting(eq):
    """PDF scouting complet d'une équipe."""
    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf,pagesize=A4,topMargin=1.2*cm,bottomMargin=1.5*cm,
                              leftMargin=1.8*cm,rightMargin=1.8*cm)
    stl  = getSampleStyleSheet()
    elems= []
    clt  = construire_classement()
    matchs = construire_matchs()
    rang_row = clt[clt["equipe"]==eq].iloc[0]
    rang     = clt[clt["equipe"]==eq].index[0]+1
    dpour    = df[df["equipe_marque"]==eq]
    dcontre  = df[df["equipe_encaisse"]==eq]
    meq      = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    n_m      = len(meq) or 1
    coul_hex = COULEUR_EQUIPE.get(eq, D1_ROUGE)

    _pdf_header(elems, stl, f"Fiche Scouting — {eq}", f"D1 Futsal · Saison en cours · Journée {max(JOURNEES)}")

    # Classement
    elems.append(_pdf_section("📊 Position au classement", stl))
    elems.append(_pdf_stat_row("Rang", f"{rang}e", coul_hex))
    elems.append(_pdf_stat_row("Points", int(rang_row["Pts"]), coul_hex))
    elems.append(_pdf_stat_row("Bilan", f"{int(rang_row['V'])}V  {int(rang_row['N'])}N  {int(rang_row['D'])}D"))
    elems.append(_pdf_stat_row("Buts marqués / encaissés", f"{int(rang_row['BP'])} / {int(rang_row['BC'])}"))
    elems.append(_pdf_stat_row("Différentiel", f"{int(rang_row['Diff']):+d}"))
    elems.append(_pdf_stat_row("Buts/match (att.)", f"{len(dpour)/n_m:.1f}"))
    elems.append(_pdf_stat_row("Buts/match (déf.)", f"{len(dcontre)/n_m:.1f}"))
    elems.append(Spacer(1,8))

    # Top buteurs
    elems.append(_pdf_section("⚽ Principaux buteurs", stl))
    bb = sans_csc(dpour)["joueur"].value_counts().head(8)
    max_b = bb.max() if len(bb) else 1
    np_stl = ParagraphStyle("np",parent=stl["Normal"],fontSize=8.5,spaceBefore=1,spaceAfter=1)
    for joueur, nb in bb.items():
        elems.append(Paragraph(f"{joueur}  ({nb} buts, {nb/len(dpour)*100:.0f}%)", np_stl))
        elems.append(_pdf_barre(nb, max_b, couleur_hex=coul_hex))
    elems.append(Spacer(1,8))

    # Profil temporel offensif
    elems.append(_pdf_section("⏱ Profil temporel offensif", stl))
    mins_p = dpour["minute"].dropna().astype(int)
    tr_p   = pd.cut(mins_p,bins=range(0,41,5),
                    labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    max_tr = tr_p.max() if tr_p.max()>0 else 1
    for tr, v in tr_p.items():
        elems.append(Paragraph(f"{tr}  ({int(v)} buts)", np_stl))
        elems.append(_pdf_barre(int(v), int(max_tr), couleur_hex=coul_hex))
    elems.append(Spacer(1,8))

    # Profil défensif
    elems.append(_pdf_section("🛡 Profil défensif — tranches à risque", stl))
    mins_c = dcontre["minute"].dropna().astype(int)
    tr_c   = pd.cut(mins_c,bins=range(0,41,5),
                    labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    max_tc = tr_c.max() if tr_c.max()>0 else 1
    best_tr = tr_c.idxmax()
    for tr, v in tr_c.items():
        rouge_flag = " ← PLUS ENCAISSÉ" if tr==best_tr else ""
        elems.append(Paragraph(f"{tr}  ({int(v)} buts encaissés){rouge_flag}", np_stl))
        c_bar = D1_ROUGE if tr==best_tr else "#9A8E91"
        elems.append(_pdf_barre(int(v), int(max_tc), couleur_hex=c_bar))
    elems.append(Spacer(1,8))

    # Situation offensive / défensive
    elems.append(_pdf_section("📈 Dynamique de score", stl))
    sit_p = dpour[dpour["situation"].notna()]["situation"].value_counts()
    sit_c = dcontre[dcontre["situation"].notna()]["situation"].value_counts()
    data_sit = [["", "Offensive (buts marqués)", "Défensive (buts encaissés)"]]
    for s in ["Menant","Égalité","Mené"]:
        vo = int(sit_p.get(s,0)); vc = int(sit_c.get(s,0))
        tp = sit_p.sum() or 1; tc = sit_c.sum() or 1
        data_sit.append([s, f"{vo} ({vo/tp*100:.0f}%)", f"{vc} ({vc/tc*100:.0f}%)"])
    t_sit = Table(data_sit, colWidths=[4.5*cm,7*cm,7*cm])
    t_sit.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(D1_ROUGE)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#ECEFF4")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#2A3348")),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    elems.append(t_sit)
    doc.build(elems); buf.seek(0)
    return buf


def pdf_buteur(joueur_nom):
    """PDF fiche buteur enrichie."""
    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf,pagesize=A4,topMargin=1.2*cm,bottomMargin=1.5*cm,
                              leftMargin=1.8*cm,rightMargin=1.8*cm)
    stl  = getSampleStyleSheet()
    elems= []
    dj   = df[df["joueur"]==joueur_nom]
    if len(dj)==0:
        return buf
    eq_j     = dj["equipe_marque"].mode().iloc[0]
    coul_hex = COULEUR_EQUIPE.get(eq_j, D1_ROUGE)
    np_stl   = ParagraphStyle("np",parent=stl["Normal"],fontSize=8.5,spaceBefore=1,spaceAfter=1)

    _pdf_header(elems, stl, f"Fiche Buteur — {joueur_nom}", f"{eq_j} · D1 Futsal · {len(dj)} buts")

    # Stats générales
    elems.append(_pdf_section("📊 Statistiques", stl))
    elems.append(_pdf_stat_row("Buts total", len(dj), coul_hex))
    elems.append(_pdf_stat_row("Buts en 1re période", int((dj["periode"]==1).sum())))
    elems.append(_pdf_stat_row("Buts en 2e période", int((dj["periode"]==2).sum())))
    elems.append(_pdf_stat_row("Journées avec but", dj["journee"].nunique()))
    elems.append(_pdf_stat_row("Adversaires différents scorés", dj["equipe_encaisse"].nunique()))
    elems.append(Spacer(1,8))

    # Situation au moment des buts
    elems.append(_pdf_section("📈 Situation au moment des buts", stl))
    sit = dj["situation"].value_counts()
    tot_s = sit.sum() or 1
    for s, v in sit.items():
        elems.append(Paragraph(f"{s}  ({int(v)} buts, {v/tot_s*100:.0f}%)", np_stl))
        c_b = D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE)
        elems.append(_pdf_barre(int(v), int(sit.max()), couleur_hex=c_b))
    elems.append(Spacer(1,8))

    # Progression (tableau journée par journée)
    elems.append(_pdf_section("📅 Progression sur la saison", stl))
    prog = dj.groupby("journee").size().reindex(range(1,max(JOURNEES)+1),fill_value=0)
    cumul = prog.cumsum()
    data_prog = [["Journée","Buts","Total cumulé"]]
    for j_, (nb, tot) in enumerate(zip(prog.values, cumul.values), 1):
        if nb > 0:
            data_prog.append([f"J{j_}", int(nb), int(tot)])
    if len(data_prog)>1:
        t_prog = Table(data_prog, colWidths=[4*cm,5.5*cm,5.5*cm])
        t_prog.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor(D1_ROUGE)),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#ECEFF4")]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#2A3348")),
            ("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ]))
        elems.append(t_prog)
    elems.append(Spacer(1,8))

    # Adversaires favoris
    elems.append(_pdf_section("🎯 Buts par adversaire", stl))
    adv = dj["equipe_encaisse"].value_counts().head(6)
    for eq_, n_ in adv.items():
        elems.append(Paragraph(f"{eq_}  ({int(n_)} buts)", np_stl))
        elems.append(_pdf_barre(int(n_), int(adv.max()), couleur_hex=COULEUR_EQUIPE.get(eq_, D1_ROUGE)))

    doc.build(elems); buf.seek(0)
    return buf


def pdf_match(journee, dom, ext):
    """PDF fiche match avec chronologie."""
    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf,pagesize=A4,topMargin=1.2*cm,bottomMargin=1.5*cm,
                              leftMargin=1.8*cm,rightMargin=1.8*cm)
    stl  = getSampleStyleSheet()
    elems= []
    df_m = df[(df["journee"]==journee)&(df["equipe_domicile"]==dom)&(df["equipe_exterieure"]==ext)]
    events = reconstruire_score(df_m, dom, ext)
    bd   = int((df_m["equipe_marque"]==dom).sum())
    be   = int((df_m["equipe_marque"]==ext).sum())
    coul_dom = COULEUR_EQUIPE.get(dom, D1_ROUGE)
    coul_ext = COULEUR_EQUIPE.get(ext, D1_BLEU)
    np_stl = ParagraphStyle("np",parent=stl["Normal"],fontSize=8.5,spaceBefore=2,spaceAfter=2)

    _pdf_header(elems, stl, f"{dom}  {bd} — {be}  {ext}", f"D1 Futsal · Journée {journee}")

    # Stats
    elems.append(_pdf_section("📊 Stats du match", stl))
    elems.append(_pdf_stat_row("Buts 1re période", int((df_m["periode"]==1).sum())))
    elems.append(_pdf_stat_row("Buts 2e période", int((df_m["periode"]==2).sum())))
    buts_dom_df = df_m[df_m["equipe_marque"]==dom]
    buts_ext_df = df_m[df_m["equipe_marque"]==ext]
    elems.append(_pdf_stat_row(f"Buteurs {dom.split()[0]}", sans_csc(buts_dom_df)["joueur"].nunique()))
    elems.append(_pdf_stat_row(f"Buteurs {ext.split()[0]}", sans_csc(buts_ext_df)["joueur"].nunique()))
    elems.append(Spacer(1,8))

    # Chronologie
    elems.append(_pdf_section("⏱ Chronologie des buts", stl))
    data_chr = [["Per.", "Min", "Buteur", "Équipe", "Score"]]
    for e in events:
        data_chr.append([
            f"P{e['periode'] if e['periode'] is not None else '?'}",
            f"{e['minute']}'" if e['minute'] is not None else "?",
            e["joueur"],
            e["equipe"].split()[0], f"{e['score_dom']}—{e['score_ext']}"
        ])
    t_chr = Table(data_chr, colWidths=[1.5*cm,1.5*cm,5.5*cm,4.5*cm,2.5*cm])
    coul_rows = []
    for i, e in enumerate(events, 1):
        c = colors.HexColor(coul_dom) if e["equipe"]==dom else colors.HexColor(coul_ext)
        coul_rows.append(("TEXTCOLOR",(3,i),(3,i),c))
        coul_rows.append(("FONTNAME",(4,i),(4,i),"Helvetica-Bold"))
    t_chr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(D1_ROUGE)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#ECEFF4")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#2A3348")),
        ("ALIGN",(0,0),(1,-1),"CENTER"),("ALIGN",(4,0),(4,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]+coul_rows))
    elems.append(t_chr)

    doc.build(elems); buf.seek(0)
    return buf


def pdf_rapport_complet(eq):
    """PDF complet style rapport Laval — fond blanc, couleur équipe."""
    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              topMargin=1.2*cm, bottomMargin=1.5*cm,
                              leftMargin=1.8*cm, rightMargin=1.8*cm)
    coul_hex = COULEUR_EQUIPE.get(eq, D1_ROUGE)
    COUL   = colors.HexColor(coul_hex)
    BLANC  = colors.white
    GRIS   = colors.HexColor("#ECEFF4")
    BORD   = colors.HexColor("#2A3348")
    TEXTE  = colors.HexColor("#0F1117")
    TEXTE_G= colors.HexColor("#8895A7")
    stl = getSampleStyleSheet()
    def ps(name, **kw): return ParagraphStyle(name, parent=stl["Normal"], **kw)
    titre_section = ps("ts", textColor=BLANC, fontSize=11, fontName="Helvetica-Bold",
                        backColor=COUL, borderPadding=(6,8,6,8), spaceBefore=14, spaceAfter=6)
    sous_titre    = ps("ss", textColor=COUL, fontSize=10, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
    corps         = ps("co", textColor=TEXTE, fontSize=8.5, spaceBefore=1, spaceAfter=1)
    gris_stl      = ps("gr", textColor=TEXTE_G, fontSize=8, spaceBefore=1, spaceAfter=1)
    def tbl_base():
        return [("FONTSIZE",(0,0),(-1,-1),8.5),("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),("GRID",(0,0),(-1,-1),0.4,BORD),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(-1,-1),"CENTER")]
    def hdr_row():
        return [("BACKGROUND",(0,0),(-1,0),COUL),("TEXTCOLOR",(0,0),(-1,0),BLANC),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    def zebra():
        return [("ROWBACKGROUNDS",(0,1),(-1,-1),[BLANC,GRIS])]
    def mini_b(val, mx, w=5*cm, h=9, cf=None):
        cf2=colors.HexColor(cf) if cf else COUL
        d=Drawing(w,h+2)
        d.add(Rect(0,0,w,h,fillColor=colors.HexColor("#1A2540"),strokeColor=None))
        if mx>0: d.add(Rect(0,0,val/mx*w,h,fillColor=cf2,strokeColor=None))
        return d

    matchs   = _get_matchs(); clt = construire_classement()
    rang_row = clt[clt["equipe"]==eq].iloc[0]; rang=clt[clt["equipe"]==eq].index[0]+1
    dpour=df[df["equipe_marque"]==eq]; dcontre=df[df["equipe_encaisse"]==eq]
    meq=matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]; n_m=len(meq) or 1
    pb=analyser_premier_but(eq); de_s=analyser_dom_ext(eq)
    rs_d=analyser_retours_score(eq); mo_d=analyser_momentum(eq)
    vt6,nt6,dt6=analyser_bilan_top6(eq); tot_t6=vt6+nt6+dt6
    vd,nd,dd=de_s["dom"]; ve,ne_,de_=de_s["ext"]
    td=vd+nd+dd or 1; te=ve+ne_+de_ or 1
    m_tot=pb["marque"]["total"] or 1; e_tot=pb["encaisse"]["total"] or 1
    mw=pb["marque"]["V"]/m_tot*100; ew=pb["encaisse"]["V"]/e_tot*100
    elems=[]

    # Header
    logo_p=LOGOS_DIR/f"{eq}.png"
    hdr_txt=Paragraph(f'<font size="18" color="{coul_hex}"><b>{eq}</b></font><br/>'
                      f'<font size="9" color="#6B6066">D1 Futsal · Saison 2025–2026 · J1→J{max(JOURNEES)}</font>',
                      ps("hdr",leading=20))
    if logo_p.exists():
        try:
            li=RLImage(str(logo_p),width=2*cm,height=2*cm)
            t_hdr=Table([[hdr_txt,li]],colWidths=[13.5*cm,3*cm])
        except: t_hdr=Table([[hdr_txt,""]],colWidths=[13.5*cm,3*cm])
    else: t_hdr=Table([[hdr_txt,""]],colWidths=[13.5*cm,3*cm])
    t_hdr.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"RIGHT"),
                                ("LINEBELOW",(0,0),(-1,0),2,COUL),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    elems+=[t_hdr,Spacer(1,8)]

    # Section 01
    elems.append(Paragraph("SECTION 01 — Vue d'ensemble",titre_section))
    tv=int(rang_row["V"])/n_m*100
    kd=[["Points","Buts marqués","Buts encaissés","Taux de victoire"],
        [f'{int(rang_row["Pts"])}',f'{int(rang_row["BP"])}',f'{int(rang_row["BC"])}',f'{tv:.0f}%'],
        [f'{int(rang_row["Pts"])/n_m:.1f}/match',f'{len(dpour)/n_m:.1f}/match',
         f'{len(dcontre)/n_m:.1f}/match',f'{int(rang_row["V"])}V·{int(rang_row["N"])}N·{int(rang_row["D"])}D']]
    kd_p=[[Paragraph(f'<font color="{coul_hex}"><b>{x}</b></font>',ps("k",alignment=1)) if i==1 else
           Paragraph(x,gris_stl if i==2 else ps("kh",fontName="Helvetica-Bold",fontSize=8.5)) for x in row]
          for i,row in enumerate(kd)]
    tk=Table(kd_p,colWidths=[4.1*cm]*4)
    tk.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                             ("GRID",(0,0),(-1,-1),0.5,BORD),("ROWBACKGROUNDS",(0,0),(-1,-1),[GRIS,BLANC,GRIS]),
                             ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    elems+=[tk,Spacer(1,4)]
    extra=[[f"Position au classement",Paragraph(f'<font color="{coul_hex}"><b>{rang}e</b></font>',corps)]]
    if tot_t6: extra.append(["Bilan vs Top 6",Paragraph(f'<font color="{coul_hex}"><b>{vt6}V·{nt6}N·{dt6}D ({vt6/tot_t6*100:.0f}%)</b></font>',corps)])
    te_=Table(extra,colWidths=[9*cm,7.5*cm])
    te_.setStyle(TableStyle([("FONTSIZE",(0,0),(-1,-1),8.5),("TOPPADDING",(0,0),(-1,-1),3),
                              ("BOTTOMPADDING",(0,0),(-1,-1),3),("LINEBELOW",(0,0),(-1,-1),0.3,BORD)]))
    elems+=[te_,Spacer(1,6)]

    # Fil de la saison
    elems.append(Paragraph("Fil de la saison",sous_titre))
    fd=[["J","Adversaire","Score","Rés."]]
    for _,m in meq.sort_values("journee").iterrows():
        is_dom=(m["dom"]==eq); adv=m["ext"] if is_dom else m["dom"]
        sc=f'{m["score_dom"]}–{m["score_ext"]}' if is_dom else f'{m["score_ext"]}–{m["score_dom"]}'
        r=m["res_dom"] if is_dom else m["res_ext"]; loc="Dom" if is_dom else "Ext"
        rc="#27AE60" if r=="V" else("#C9A24B" if r=="N" else D1_DANGER)
        fd.append([f'J{int(m["journee"])} ({loc})',nc(adv),sc,
                   Paragraph(f'<font color="{rc}"><b>{r}</b></font>',corps)])
    tf=Table(fd,colWidths=[2.5*cm,8.5*cm,2.5*cm,3*cm],repeatRows=1)
    tf.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()))
    elems+=[tf,Spacer(1,6)]

    # Section 02
    elems.append(Paragraph("SECTION 02 — Analyse Tactique",titre_section))
    elems.append(Paragraph("Impact du premier but",sous_titre))
    pb_d=[["","Matchs","Victoires","Nuls","Défaites","% Vic."],
          ["Marque 1er",pb["marque"]["total"],pb["marque"]["V"],pb["marque"]["N"],pb["marque"]["D"],f"{mw:.0f}%"],
          ["Encaisse 1er",pb["encaisse"]["total"],pb["encaisse"]["V"],pb["encaisse"]["N"],pb["encaisse"]["D"],f"{ew:.0f}%"]]
    tp=Table(pb_d,colWidths=[5*cm,2*cm,2*cm,2*cm,2*cm,3*cm])
    tp.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()+
                           [("TEXTCOLOR",(5,1),(5,-1),COUL),("FONTNAME",(5,1),(5,-1),"Helvetica-Bold")]))
    elems+=[tp,Spacer(1,5)]
    elems.append(Paragraph("Domicile vs Extérieur",sous_titre))
    de_d=[["","V","N","D","% Vic."],["Domicile",vd,nd,dd,f"{vd/td*100:.0f}%"],["Extérieur",ve,ne_,de_,f"{ve/te*100:.0f}%"]]
    td2=Table(de_d,colWidths=[5*cm,2.5*cm,2.5*cm,2.5*cm,3.5*cm])
    td2.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()+
                            [("TEXTCOLOR",(4,1),(4,-1),COUL),("FONTNAME",(4,1),(4,-1),"Helvetica-Bold")]))
    elems+=[td2,Spacer(1,5)]
    elems.append(Paragraph("Retours au score",sous_titre))
    rs_rows=[["Scénario","Matchs"]]
    for lab,val,cf in [("Jamais mené",rs_d["jamais"],D1_VERT),("Est mené → Victoire",rs_d["mv"],coul_hex),
                        ("Est mené → Nul",rs_d["mn"],D1_OR),("Est mené → Défaite",rs_d["md"],D1_DANGER)]:
        rs_rows.append([lab,Paragraph(f'<font color="{cf}"><b>{val}</b></font>',corps)])
    tr=Table(rs_rows,colWidths=[10*cm,6*cm])
    tr.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()))
    elems+=[tr,Spacer(1,5)]
    elems.append(Paragraph("Momentum après un but (min. moyennes)",sous_titre))
    mo_rows=[["Transition","Minutes"]]
    mo_cols={"Marque → Marque":D1_VERT,"Marque → Encaisse":D1_OR,"Encaisse → Marque":coul_hex,"Encaisse → Encaisse":D1_ROUGE}
    for lab,val in mo_d.items():
        mo_rows.append([lab,Paragraph(f'<font color="{mo_cols.get(lab,D1_GRIS)}"><b>{val} min</b></font>' if val else "—",corps)])
    tm=Table(mo_rows,colWidths=[10*cm,6*cm])
    tm.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()))
    elems+=[tm,Spacer(1,6)]

    # Section 03
    elems.append(Paragraph("SECTION 03 — Analyse Temporelle",titre_section))
    mins_p=dpour["minute"].dropna().astype(int)
    mins_c=dcontre["minute"].dropna().astype(int)
    tr_p=pd.cut(mins_p,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    tr_c=pd.cut(mins_c,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    mx_tr=max(tr_p.max(),tr_c.max(),1)
    tr_rows=[["Tranche","Marqués","","Encaissés",""]]
    for tr in tr_p.index:
        vp=int(tr_p[tr]); vc=int(tr_c[tr])
        d_p=Drawing(6*cm,10); d_p.add(Rect(0,1,6*cm,8,fillColor=colors.HexColor("#1A2540"),strokeColor=None))
        if vp>0: d_p.add(Rect(0,1,vp/mx_tr*6*cm,8,fillColor=COUL,strokeColor=None))
        d_c=Drawing(3.5*cm,10); d_c.add(Rect(0,1,3.5*cm,8,fillColor=colors.HexColor("#1A2540"),strokeColor=None))
        if vc>0: d_c.add(Rect(0,1,vc/mx_tr*3.5*cm,8,fillColor=colors.HexColor(D1_DANGER),strokeColor=None))
        tr_rows.append([str(tr),Paragraph(f'<font color="{coul_hex}"><b>{vp}</b></font>',corps),d_p,
                        Paragraph(f'<font color="{D1_DANGER}"><b>{vc}</b></font>',corps),d_c])
    tt=Table(tr_rows,colWidths=[1.8*cm,1.2*cm,6*cm,1.2*cm,4.5*cm],repeatRows=1)
    tt.setStyle(TableStyle(tbl_base()+hdr_row()+zebra()))
    elems+=[tt,Spacer(1,6)]

    # Section 04
    elems.append(Paragraph("SECTION 04 — Analyse des Buteurs",titre_section))
    bb=sans_csc(dpour)["joueur"].value_counts(); tot_b=len(dpour) or 1
    elems.append(Paragraph(f'Top 3 : {bb.head(3).sum()} buts ({bb.head(3).sum()/tot_b*100:.0f}%)',gris_stl))
    elems.append(Spacer(1,4))
    for joueur,nb in bb.head(10).items():
        row_data=[[Paragraph(nj(joueur),corps),
                   Paragraph(f'<font color="{coul_hex}"><b>{nb}</b></font>',ps("bj",alignment=1)),
                   mini_b(nb,int(bb.max()),7*cm),Paragraph(f'{nb/tot_b*100:.0f}%',gris_stl)]]
        tr2=Table(row_data,colWidths=[4.5*cm,1*cm,7*cm,1.5*cm])
        tr2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),2),
                                  ("BOTTOMPADDING",(0,0),(-1,-1),2),("LINEBELOW",(0,0),(-1,-1),0.2,BORD)]))
        elems.append(tr2)
    elems.append(Spacer(1,6))

    # Section 05
    if eq in EQUIPES_AVEC_ORIGINE:
        elems.append(Paragraph("SECTION 05 — Origines des Buts",titre_section))
        oo=dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
        n_r=int(dpour["origine"].notna().sum())
        elems.append(Paragraph(f'{n_r} buts analysés sur {tot_b}',gris_stl))
        elems.append(Spacer(1,4))
        for orig,nb in oo.items():
            row_data=[[Paragraph(orig,corps),
                       Paragraph(f'<font color="{coul_hex}"><b>{nb}</b></font>',ps("oo",alignment=1)),
                       mini_b(nb,int(oo.max()),7*cm),Paragraph(f'{nb/n_r*100:.0f}%',gris_stl)]]
            tr3=Table(row_data,colWidths=[4.5*cm,1*cm,7*cm,1.5*cm])
            tr3.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),2),
                                      ("BOTTOMPADDING",(0,0),(-1,-1),2),("LINEBELOW",(0,0),(-1,-1),0.2,BORD)]))
            elems.append(tr3)

    doc.build(elems); buf.seek(0)
    return buf


def bloc_export(pdf_buffer, nom_fichier, label="Exporter en PDF", csv_df=None, csv_nom=None):
    """Bloc d'export uniforme placé en bas de page."""
    st.markdown("<hr style='border:none;border-top:1px solid #252A3A;margin:1.2rem 0 .6rem 0'>",
                unsafe_allow_html=True)
    st.markdown("<div class='nav-cat' style='color:#9A8E91!important;margin-bottom:.3rem'>EXPORTER</div>",
                unsafe_allow_html=True)
    if csv_df is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(f"⬇ {label} (PDF)", pdf_buffer,
                               file_name=nom_fichier, mime="application/pdf",
                               use_container_width=True)
        with c2:
            st.download_button("⬇ Données (CSV)",
                               csv_df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=csv_nom or nom_fichier.replace(".pdf",".csv"),
                               mime="text/csv", use_container_width=True)
    else:
        st.download_button(f"⬇ {label} (PDF)", pdf_buffer,
                           file_name=nom_fichier, mime="application/pdf")

# ============================================================================
# PAGE — ACCUEIL
# ============================================================================
# FONCTIONS D'ANALYSE TACTIQUE
# ============================================================================

def _get_matchs():
    return construire_matchs()

def analyser_premier_but(eq):
    matchs = _get_matchs()
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    res = {"marque":{"V":0,"N":0,"D":0,"total":0},
           "encaisse":{"V":0,"N":0,"D":0,"total":0}}
    for _,m in meq.iterrows():
        dm = df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&
                (df["equipe_exterieure"]==m["ext"])]
        if len(dm)==0: continue
        first = dm.sort_values(["periode","minute"]).iloc[0]
        r = m["res_dom"] if m["dom"]==eq else m["res_ext"]
        cle = "marque" if first["equipe_marque"]==eq else "encaisse"
        res[cle][r]+=1; res[cle]["total"]+=1
    return res

def analyser_dom_ext(eq):
    matchs = _get_matchs()
    dom_m = matchs[matchs["dom"]==eq]; ext_m = matchs[matchs["ext"]==eq]
    vd=int((dom_m["res_dom"]=="V").sum()); nd=int((dom_m["res_dom"]=="N").sum()); dd=int((dom_m["res_dom"]=="D").sum())
    ve=int((ext_m["res_ext"]=="V").sum()); ne=int((ext_m["res_ext"]=="N").sum()); de=int((ext_m["res_ext"]=="D").sum())
    return {"dom":(vd,nd,dd),"ext":(ve,ne,de)}

def analyser_retours_score(eq):
    matchs = _get_matchs()
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    jamais=0; mv=0; mn=0; md=0
    for _,m in meq.iterrows():
        dm = df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&
                (df["equipe_exterieure"]==m["ext"])]
        goals = dm.sort_values(["periode","minute"]); is_dom=(m["dom"]==eq)
        was_trailing=False; sd=0; se=0
        for _,b in goals.iterrows():
            if b["equipe_marque"]==m["dom"]: sd+=1
            else: se+=1
            if (sd if is_dom else se)<(se if is_dom else sd): was_trailing=True; break
        r = m["res_dom"] if is_dom else m["res_ext"]
        if not was_trailing: jamais+=1
        elif r=="V": mv+=1
        elif r=="N": mn+=1
        else: md+=1
    return {"jamais":jamais,"mv":mv,"mn":mn,"md":md}

def analyser_momentum(eq):
    matchs = _get_matchs()
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    trans = {"MM":[],"ME":[],"EM":[],"EE":[]}
    for _,m in meq.iterrows():
        dm = df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&
                (df["equipe_exterieure"]==m["ext"])]
        if len(dm)<2: continue
        goals = dm.dropna(subset=["minute"]).sort_values(["periode","minute"])
        if len(goals)<2: continue
        mins = goals["minute"].values; teams = goals["equipe_marque"].values
        for i in range(len(goals)-1):
            delta = max(1,int(mins[i+1])-int(mins[i]))
            t1="M" if teams[i]==eq else "E"; t2="M" if teams[i+1]==eq else "E"
            trans[t1+t2].append(delta)
    labels={"MM":"Marque → Marque","ME":"Marque → Encaisse",
            "EM":"Encaisse → Marque","EE":"Encaisse → Encaisse"}
    return {labels[k]:(round(sum(v)/len(v)) if v else None) for k,v in trans.items()}

def analyser_bilan_top6(eq):
    matchs = _get_matchs()
    clt = construire_classement()
    top6 = [e for e in clt.head(6)["equipe"].tolist() if e!=eq]
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    bvt = meq[(meq["dom"].isin(top6))|(meq["ext"].isin(top6))]
    v=0; n=0; d=0
    for _,m in bvt.iterrows():
        r = m["res_dom"] if m["dom"]==eq else m["res_ext"]
        if r=="V": v+=1
        elif r=="N": n+=1
        else: d+=1
    return v,n,d

def _carte_stat(titre, valeur_principale, sous_texte=None, couleur=None):
    c = couleur or D1_ROUGE
    html = (
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-top:4px solid {c};border-radius:12px;padding:1.2rem 1.3rem;height:100%;min-height:110px">'
        f'<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.5px;color:{D1_GRIS};margin-bottom:.5rem">{titre}</div>'
        f'<div style="font-size:2.4rem;font-weight:900;color:{c};line-height:1.1">{valeur_principale}</div>'
    )
    if sous_texte:
        html += f'<div style="font-size:.85rem;color:{D1_GRIS};margin-top:.4rem;font-weight:500">{sous_texte}</div>'
    html += '</div>'
    return html

# ============================================================================
# FONCTIONS NOUVELLES STATS
# ============================================================================

def buts_clutch_eq(eq):
    """Buts marqués entre la 36e et la 40e minute."""
    dp = df[df["equipe_marque"]==eq]
    clutch = dp[dp["minute"] >= 36]
    return int(len(clutch)), int(len(dp))

def impact_but_rapide(eq):
    """Si l'équipe marque dans les 3 premières minutes, quel résultat ?"""
    matchs = _get_matchs()
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    res = {"total":0,"V":0,"N":0,"D":0}
    sans = {"total":0,"V":0,"N":0,"D":0}
    for _,m in meq.iterrows():
        dm = df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&(df["equipe_exterieure"]==m["ext"])]
        early = dm[(dm["minute"]<=3)&(dm["equipe_marque"]==eq)]
        r = m["res_dom"] if m["dom"]==eq else m["res_ext"]
        if len(early)>0:
            res[r]+=1; res["total"]+=1
        else:
            sans[r]+=1; sans["total"]+=1
    return res, sans

def retournements_eq(eq):
    """Matchs où l'équipe était menée à la mi-temps."""
    matchs = _get_matchs()
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    mene_ht=0; v_after=0; n_after=0; d_after=0
    for _,m in meq.iterrows():
        dm = df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&(df["equipe_exterieure"]==m["ext"])]
        is_dom=(m["dom"]==eq)
        p1=dm[dm["periode"]==1]
        sd_ht=int((p1["equipe_marque"]==m["dom"]).sum())
        se_ht=int((p1["equipe_marque"]==m["ext"]).sum())
        seq=sd_ht if is_dom else se_ht
        saq=se_ht if is_dom else sd_ht
        if seq<saq:
            mene_ht+=1
            r=m["res_dom"] if is_dom else m["res_ext"]
            if r=="V": v_after+=1
            elif r=="N": n_after+=1
            else: d_after+=1
    return {"mene_ht":mene_ht,"v":v_after,"n":n_after,"d":d_after}

def buteurs_clutch_eq(eq):
    """Buteurs avec le plus de buts entre 36' et 40'."""
    return sans_csc(df[(df["equipe_marque"]==eq)&(df["minute"]>=36)])["joueur"].value_counts()

# ============================================================================
# FONCTION — POWER PLAY (gardien volant)
# ============================================================================
@st.cache_data
def analyser_power_play():
    """Buts d'origine 'Power play' tels qu'enregistrés, sans interprétation."""
    pp = df[df["origine"] == "Power play"].copy()
    if not pp.empty:
        pp["ecart_avant"] = pp["score_marque_avant"] - pp["score_encaisse_avant"]
    return pp

# ============================================================================
# PAGE — FICHE ÉQUIPE (fusion Vue équipe + Analyse Tactique + Scouting + Origines)
# ============================================================================


if page == "Accueil":
    st.title("D1 Futsal — Vue d'ensemble")
    matchs = construire_matchs()
    nb_matchs = len(matchs)
    moy = len(df)/nb_matchs if nb_matchs else 0
    top_but = sans_csc(df)["joueur"].value_counts()
    top_att = df["equipe_marque"].value_counts()

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Buts", len(df)); c2.metric("Matchs", nb_matchs)
    c3.metric("Moy. buts/match", f"{moy:.1f}")
    c4.metric("Top buteur", f"{top_but.max()} buts", top_but.idxmax())
    c5.metric("Meilleure attaque", f"{top_att.max()} buts", nc(top_att.idxmax()))

    st.markdown("### Buts par journée")
    parj = df.groupby("journee").size().reindex(JOURNEES, fill_value=0)
    fig = go.Figure(go.Bar(x=[f"J{j}" for j in parj.index], y=parj.values,
                           marker_color=D1_ROUGE, text=parj.values,
                           textposition="outside", textangle=0))
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig, 250), use_container_width=True)

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buts marqués par équipe")
        vals = df["equipe_marque"].value_counts()
        st.plotly_chart(barh_equipes(vals.index.tolist(), vals.values,
                                     h=max(300,30*len(vals))), use_container_width=True)
    with cd:
        st.markdown("### Buts encaissés par équipe")
        vals2 = df["equipe_encaisse"].value_counts().sort_values()  # moins encaissé en haut
        # même couleur d'équipe (pas de transparence différente)
        st.plotly_chart(barh_equipes(vals2.index.tolist(), vals2.values,
                                     h=max(300,30*len(vals2))), use_container_width=True)

    st.markdown("### Répartition 1re / 2e période")
    p1 = int((df["periode"]==1).sum()); p2 = int((df["periode"]==2).sum())
    cp1, cp2 = st.columns(2)
    cp1.metric("1re période", p1, f"{p1/(p1+p2)*100:.0f}% des buts")
    cp2.metric("2e période", p2, f"{p2/(p1+p2)*100:.0f}% des buts")

    st.markdown("### Domicile vs Extérieur — vue championnat")
    matchs_acc = construire_matchs()
    rows_de = []
    for eq in EQUIPES:
        dom_m = matchs_acc[matchs_acc["dom"]==eq]
        ext_m = matchs_acc[matchs_acc["ext"]==eq]
        vd=int((dom_m["res_dom"]=="V").sum()); td=len(dom_m) or 1
        ve=int((ext_m["res_ext"]=="V").sum()); te=len(ext_m) or 1
        rows_de.append({"eq":eq,"pct_dom":vd/td*100,"pct_ext":ve/te*100})
    de_df = pd.DataFrame(rows_de).sort_values("pct_dom",ascending=False)

    # 2 traces (dom + ext) avec noms courts sur l'axe X
    fig_de = go.Figure()
    fig_de.add_trace(go.Bar(
        name="% Victoires Domicile",
        x=ncs(de_df["eq"].tolist()),
        y=de_df["pct_dom"].values,
        marker_color=[COULEUR_EQUIPE.get(e, D1_ROUGE) for e in de_df["eq"]],
        text=[f'{v:.0f}%' for v in de_df["pct_dom"]],
        textposition="outside", textangle=0,
        textfont=dict(size=14, color=D1_BLANC),
    ))
    fig_de.add_trace(go.Bar(
        name="% Victoires Extérieur",
        x=ncs(de_df["eq"].tolist()),
        y=de_df["pct_ext"].values,
        marker_color=[hex_to_rgba(COULEUR_EQUIPE.get(e, D1_ROUGE), 0.5) for e in de_df["eq"]],
        text=[f'{v:.0f}%' for v in de_df["pct_ext"]],
        textposition="outside", textangle=0,
        textfont=dict(size=14, color=D1_BLANC),
    ))
    fig_de.update_layout(barmode="group", bargap=0.2, bargroupgap=0.08, width=780)
    fig_de.update_yaxes(showticklabels=False, range=[0,120],
                        title=dict(text="% de victoires", font=dict(size=12, color=D1_GRIS)))
    st.plotly_chart(style_fig(fig_de, 340, "% de victoires — Domicile vs Extérieur par équipe"),
                    use_container_width=False)
    st.markdown("<p class='note'>Barre pleine = domicile · Barre semi-transparente = extérieur · "
                "Glisse horizontalement sur mobile pour tout voir.</p>",
                unsafe_allow_html=True)

    st.markdown("### Heatmap — buts par équipe et par journée")
    pivot_hm = df.groupby(["equipe_marque","journee"]).size().reset_index(name="buts")
    pivot_hm = pivot_hm.pivot(index="equipe_marque",columns="journee",values="buts").fillna(0)
    # Ordonner par classement
    clt_acc = construire_classement()
    ordre = clt_acc["equipe"].tolist()
    pivot_hm = pivot_hm.reindex(ordre)
    fig_hm = go.Figure(go.Heatmap(
        z=pivot_hm.values,
        x=[f"J{j}" for j in pivot_hm.columns],
        y=[nc(e) for e in pivot_hm.index],
        colorscale=[[0,"rgba(38,24,28,1)"],[0.3,f"rgba(140,10,24,0.6)"],[1,D1_ROUGE]],
        text=pivot_hm.values.astype(int),
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        hovertemplate="<b>%{y}</b> · J%{x}<br>%{z} buts<extra></extra>",
        showscale=False,
    ))
    fig_hm.update_xaxes(tickfont=dict(size=11))
    fig_hm.update_yaxes(tickfont=dict(size=11))
    fig_hm.update_layout(width=max(780, 38*len(pivot_hm.columns)+220))
    st.plotly_chart(style_fig(fig_hm, max(360, 32*len(ordre))), use_container_width=False)
    st.markdown("<p class='note'>Couleur = nombre de buts marqués ce match-là. "
                "Plus rouge = plus de buts.</p>", unsafe_allow_html=True)

# ============================================================================
# PAGE — CLASSEMENT
# ============================================================================
elif page == "Classement":
    st.title("Classement D1 Futsal")

    # Filtre journée
    j_max = max(JOURNEES)
    j_filtre = st.selectbox(
        "Classement après la journée",
        options=JOURNEES,
        index=len(JOURNEES)-1,
        format_func=lambda x: f"Journée {x}"
    )
    df_filtre = df[df["journee"] <= j_filtre]

    @st.cache_data
    def construire_classement_filtre(j_max_filtre):
        matchs_f = construire_matchs()
        matchs_f = matchs_f[matchs_f["journee"] <= j_max_filtre]
        rows = []
        for eq in EQUIPES:
            jdom = list(matchs_f[matchs_f["dom"]==eq][["journee","res_dom"]].sort_values("journee").itertuples(index=False))
            jext = list(matchs_f[matchs_f["ext"]==eq][["journee","res_ext"]].sort_values("journee").itertuples(index=False))
            hist = sorted([(r.journee, r.res_dom) for r in jdom]+[(r.journee, r.res_ext) for r in jext])
            res  = [r for _,r in hist]
            v=res.count("V"); n=res.count("N"); d=res.count("D")
            df_eq = df.loc[df["journee"] <= j_max_filtre]
            bp=int(df_eq.loc[df_eq["equipe_marque"]==eq].shape[0])
            bc=int(df_eq.loc[df_eq["equipe_encaisse"]==eq].shape[0])
            rows.append({"equipe":eq,"J":len(res),"V":v,"N":n,"D":d,
                         "Pts":3*v+n,"BP":bp,"BC":bc,"Diff":bp-bc,"forme":res})
        return (pd.DataFrame(rows)
                .sort_values(["Pts","Diff","BP"], ascending=[False,False,False])
                .reset_index(drop=True))

    clt = construire_classement_filtre(j_filtre)
    if j_filtre < j_max:
        st.markdown(f'<div style="display:inline-block;background:{D1_ROUGE};color:white;'
                    f'padding:.2rem .7rem;border-radius:5px;font-size:.8rem;font-weight:700;margin-bottom:.6rem">'
                    f'Affichage après J{j_filtre} — {len(df_filtre)} buts comptabilisés</div>',
                    unsafe_allow_html=True)

    # Ligne d'en-tête
    head_html = (
        '<div class="clt-wrap">'
        '<div class="clt-head">'
        '<span class="w-rang">#</span>'
        '<span class="w-logo"></span>'
        '<span style="flex:1">Équipe</span>'
        '<span class="w-pts">Pts</span>'
        '<span class="w-vnpd">V / N / D</span>'
        '<span class="w-buts">BP — BC</span>'
        '<span class="w-diff">Diff</span>'
        '<span class="w-forme">Forme</span>'
        '</div>'
    )
    rows_html = ""
    for i, row in clt.iterrows():
        rang = i+1
        is_top3 = rang <= 3
        coul = COULEUR_EQUIPE.get(row["equipe"], D1_ROUGE)
        lg   = logo_b64(row["equipe"], 26)
        forme= forme_ronds(row["forme"])
        diff = row["Diff"]
        diff_color = D1_VERT if diff>0 else(D1_DANGER if diff<0 else D1_GRIS)
        diff_txt = f"+{diff}" if diff>0 else str(diff)
        bg = hex_to_rgba(coul, 0.08) if is_top3 else "transparent"
        border_left = f"border-left:3px solid {coul}" if is_top3 else "border-left:3px solid transparent"
        rang_class = "w-rang or" if is_top3 else "w-rang"
        rows_html += (
            f'<div class="clt-row" style="background:{bg};{border_left}">'
            f'<span class="{rang_class}">{rang}</span>'
            f'<span class="w-logo">{lg}</span>'
            f'<span class="w-nom">{row["equipe"]}</span>'
            f'<span class="w-pts">{int(row["Pts"])}</span>'
            f'<span class="w-vnpd">{int(row["V"])}V {int(row["N"])}N {int(row["D"])}D</span>'
            f'<span class="w-buts">{int(row["BP"])} — {int(row["BC"])}</span>'
            f'<span class="w-diff" style="color:{diff_color}">{diff_txt}</span>'
            f'<span class="w-forme">{forme}</span>'
            f'</div>'
        )
    st.markdown(head_html + rows_html + '</div>', unsafe_allow_html=True)
    st.markdown("<p class='note' style='margin-top:.5rem'>Forme sur les 5 derniers matchs</p>",
                unsafe_allow_html=True)

    # Séries en cours
    st.markdown("### Séries en cours")
    rows_ser = []
    for eq in EQUIPES:
        row = clt[clt["equipe"]==eq].iloc[0]
        forme = row["forme"]
        # Série actuelle (compter depuis la fin sans interruption)
        serie_v=0; serie_inv=0; serie_d=0
        for r in reversed(forme):
            if r=="V": serie_v+=1
            else: break
        for r in reversed(forme):
            if r in ("V","N"): serie_inv+=1
            else: break
        for r in reversed(forme):
            if r=="D": serie_d+=1
            else: break
        rows_ser.append({"eq":eq,"serie_v":serie_v,"serie_inv":serie_inv,"serie_d":serie_d})
    ser_df = pd.DataFrame(rows_ser)

    cg_s, cd_s = st.columns(2)
    with cg_s:
        st.markdown("#### Sans défaite (matchs consécutifs)")
        ser_inv = ser_df.sort_values("serie_inv",ascending=False)
        fig_ser = go.Figure()
        for _,r in ser_inv.iterrows():
            if r["serie_inv"]==0: continue
            coul_s = D1_VERT if r["serie_inv"]>=5 else(D1_OR if r["serie_inv"]>=3 else D1_BLANC)
            fig_ser.add_trace(go.Bar(x=[r["serie_inv"]],y=[nc(r["eq"])],orientation="h",
                                     marker_color=COULEUR_EQUIPE.get(r["eq"],D1_ROUGE),
                                     text=[f'{int(r["serie_inv"])} matchs'],
                                     textposition="outside",textangle=0,showlegend=False,
                                     textfont=dict(size=14,color="#F5F2F3")))
        fig_ser.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_ser, max(220,28*len(ser_inv[ser_inv["serie_inv"]>0]))),
                        use_container_width=True)
    with cd_s:
        st.markdown("#### Victoires consécutives")
        ser_v = ser_df[ser_df["serie_v"]>0].sort_values("serie_v",ascending=False)
        if len(ser_v):
            fig_v = go.Figure()
            for _,r in ser_v.iterrows():
                fig_v.add_trace(go.Bar(x=[r["serie_v"]],y=[nc(r["eq"])],orientation="h",
                                       marker_color=COULEUR_EQUIPE.get(r["eq"],D1_ROUGE),
                                       text=[f'{int(r["serie_v"])} victoires'],
                                       textposition="auto",textangle=0,showlegend=False))
            fig_v.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_v, max(220,28*len(ser_v))), use_container_width=True)
        else:
            st.info("Aucune équipe en série de victoires actuellement.")

    st.markdown("### Évolution des points (cumulés)")
    evo = evolution_classement()
    # Ne montrer que jusqu'à la journée filtrée
    evo_f = evo[evo["journee"] <= j_filtre]
    journees_affichees = [j for j in JOURNEES if j <= j_filtre]
    fig = go.Figure()
    for eq in clt["equipe"].tolist():
        sub = evo_f[evo_f["equipe"]==eq].sort_values("journee")
        coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
        fig.add_trace(go.Scatter(
            x=sub["journee"], y=sub["pts"], mode="lines+markers",
            name=nc(eq), line=dict(color=coul, width=2.5), marker=dict(size=4),
            hovertemplate=f"<b>{eq}</b><br>J%{{x}} → %{{y}} pts<extra></extra>"
        ))
    fig.update_xaxes(tickvals=journees_affichees, ticktext=[f"J{j}" for j in journees_affichees])
    st.plotly_chart(style_fig(fig, 440), use_container_width=True)

    tab_exp = clt[["equipe","J","V","N","D","Pts","BP","BC","Diff"]].copy()
    tab_exp.columns = ["Équipe","J","V","N","D","Pts","BP","BC","Diff"]
    bloc_export(pdf_tableau("Classement D1 Futsal", f"Journée {j_filtre}", tab_exp),
                f"classement_D1_J{j_filtre}.pdf", "Exporter le classement",
                csv_df=tab_exp, csv_nom=f"classement_d1_J{j_filtre}.csv")

# ============================================================================
# PAGE — FICHE MATCH
# ============================================================================
elif page == "Fiche match":
    st.title("Fiche match")
    matchs = construire_matchs()
    j_sel = st.selectbox("Journée", sorted(matchs["journee"].unique()),
                         format_func=lambda x: f"Journée {x}")
    matchs_j = matchs[matchs["journee"]==j_sel]
    opts = [f"{r.dom}  {r.score_dom} — {r.score_ext}  {r.ext}" for r in matchs_j.itertuples()]
    m_sel = st.selectbox("Match", opts)
    idx = opts.index(m_sel)
    m_row = matchs_j.iloc[idx]
    dom, ext = m_row["dom"], m_row["ext"]
    score_dom, score_ext = m_row["score_dom"], m_row["score_ext"]
    coul_dom = COULEUR_EQUIPE.get(dom, D1_ROUGE)
    coul_ext = COULEUR_EQUIPE.get(ext, D1_BLEU)

    r_dom = m_row["res_dom"]; r_ext = m_row["res_ext"]
    c_r_dom = D1_VERT if r_dom=="V" else(D1_OR if r_dom=="N" else D1_ROUGE)
    c_r_ext = D1_VERT if r_ext=="V" else(D1_OR if r_ext=="N" else D1_ROUGE)
    lg_dom = logo_b64(dom, 52); lg_ext = logo_b64(ext, 52)

    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:13px;'
        f'padding:1.1rem;text-align:center;margin-bottom:.9rem">'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:2.5rem">'
        f'<div style="flex:1;text-align:right">'
        f'<div style="font-weight:700;font-size:.92rem;margin-bottom:.35rem">{dom}</div>{lg_dom}'
        f'</div>'
        f'<div style="padding:0 .8rem">'
        f'<div style="font-size:2.4rem;font-weight:900;letter-spacing:.12rem">'
        f'<span style="color:{c_r_dom}">{score_dom}</span>'
        f'<span style="color:{D1_GRIS}"> — </span>'
        f'<span style="color:{c_r_ext}">{score_ext}</span>'
        f'</div>'
        f'<div style="color:{D1_GRIS};font-size:.78rem">Journée {j_sel}</div>'
        f'</div>'
        f'<div style="flex:1;text-align:left">'
        f'{lg_ext}<div style="font-weight:700;font-size:.92rem;margin-top:.35rem">{ext}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    df_match = df[
        (df["journee"]==j_sel) &
        (df["equipe_domicile"]==dom) &
        (df["equipe_exterieure"]==ext)
    ]
    events = reconstruire_score(df_match, dom, ext)

    # ---- Momentum : minutes absolues 1-40, mi-temps à x=20 ----
    st.markdown("### Momentum du match")
    # On utilise les minutes directement (déjà absolues 1-40) ; minute None -> fin du match
    xs  = [0] + [(e["minute"] if e["minute"] is not None else 40) for e in events] + [40]
    yd  = [0] + [e["score_dom"] for e in events] + [(events[-1]["score_dom"] if events else 0)]
    ye  = [0] + [e["score_ext"] for e in events] + [(events[-1]["score_ext"] if events else 0)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=yd, mode="lines", name=dom.split()[0],
        line=dict(color=coul_dom, width=3),
        fill="tozeroy", fillcolor=hex_to_rgba(coul_dom, 0.22),
        hovertemplate=f"<b>{nc(dom)}</b> %{{y}}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ye, mode="lines", name=ext.split()[0],
        line=dict(color=coul_ext, width=3),
        fill="tozeroy", fillcolor=hex_to_rgba(coul_ext, 0.22),
        hovertemplate=f"<b>{nc(ext)}</b> %{{y}}<extra></extra>"
    ))
    # Mi-temps à la minute 20 (numérique)
    fig.add_shape(type="line", x0=20, x1=20, y0=0, y1=1, yref="paper",
                  line=dict(color=D1_GRIS, width=1, dash="dot"))
    fig.add_annotation(x=20, y=1, yref="paper", text="Mi-temps",
                       showarrow=False, font=dict(color=D1_GRIS, size=11),
                       yanchor="bottom", xanchor="center")
    fig.update_xaxes(title="Minute", range=[0,40],
                     tickvals=[0,5,10,15,20,25,30,35,40],
                     ticktext=["0'","5'","10'","15'","20'","25'","30'","35'","40'"])
    fig.update_yaxes(title="Score", dtick=1)
    st.plotly_chart(style_fig(fig, 290), use_container_width=True)

    # Chronologie
    st.markdown("### Chronologie des buts")
    for e in events:
        is_dom = e["equipe"]==dom
        coul   = coul_dom if is_dom else coul_ext
        per    = "1P" if e["periode"]==1 else "2P"
        score_txt = f'{e["score_dom"]} — {e["score_ext"]}'
        orig   = f' <span style="color:{D1_GRIS};font-size:.74rem">· {e["origine"]}</span>' if e["origine"]!="—" else ""
        lg     = logo_b64(e["equipe"], 19)
        align  = "flex-start" if is_dom else "flex-end"
        st.markdown(
            f'<div style="display:flex;justify-content:{align};margin:.18rem 0">'
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-left:3px solid {coul};border-radius:7px;padding:.3rem .7rem;max-width:54%">'
            f'{lg} <b style="font-size:.86rem">{e["joueur"]}</b>'
            f'<span style="color:{D1_GRIS};font-size:.76rem"> {per} {e["minute"] if e["minute"] is not None else "?"}\' </span>'
            f'<b style="color:{coul}">{score_txt}</b>{orig}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # Stats rapides
    st.markdown("### Stats")
    buts_dom = df_match[df_match["equipe_marque"]==dom]
    buts_ext = df_match[df_match["equipe_marque"]==ext]
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Buts dom.",len(buts_dom)); c2.metric("Buts ext.",len(buts_ext))
    c3.metric("Buts P1",int((df_match["periode"]==1).sum())); c4.metric("Buts P2",int((df_match["periode"]==2).sum()))
    c5.metric("Buteurs dom.",sans_csc(buts_dom)["joueur"].nunique()); c6.metric("Buteurs ext.",sans_csc(buts_ext)["joueur"].nunique())
    cg,cd = st.columns(2)
    with cg:
        st.markdown(f"**{dom.split()[0]}**")
        for j,n in sans_csc(buts_dom)["joueur"].value_counts().items(): st.markdown(f'{"⚽"*n} **{j}** ({n})')
    with cd:
        st.markdown(f"**{ext.split()[0]}**")
        for j,n in sans_csc(buts_ext)["joueur"].value_counts().items(): st.markdown(f'{"⚽"*n} **{j}** ({n})')

    bloc_export(pdf_match(j_sel, dom, ext),
                f"match_J{j_sel}_{dom[:8].replace(' ','_')}_{ext[:8].replace(' ','_')}.pdf",
                "Exporter la fiche match")

# ============================================================================
# PAGE — CLASSEMENT BUTEURS
# ============================================================================
elif page == "Buteurs":
    st.title("Classement des buteurs")
    eq = st.selectbox("Filtrer par équipe", ["Toutes"]+EQUIPES)
    d  = df if eq=="Toutes" else df[df["equipe_marque"]==eq]
    d  = sans_csc(d)
    clt = (d.groupby("joueur")
             .agg(buts=("but_id","count"), equipe=("equipe_marque",lambda s:s.mode().iloc[0]))
             .reset_index().sort_values("buts",ascending=False).reset_index(drop=True))
    clt.index += 1
    if len(clt)>=3:
        p=clt.head(3); cols=st.columns(3); medals=["🥇","🥈","🥉"]
        for i,(col,(_,row)) in enumerate(zip(cols,p.iterrows())):
            coul=COULEUR_EQUIPE.get(row["equipe"],D1_ROUGE)
            col.markdown(
                f'<div class="pod"><div style="font-size:1.5rem">{medals[i]}</div>'
                f'{logo_b64(row["equipe"],36)}<br>'
                f'<div style="font-weight:700;margin-top:.3rem;font-size:.9rem">{row["joueur"]}</div>'
                f'<div class="note">{row["equipe"]}</div>'
                f'<div style="color:{coul};font-size:1.25rem;font-weight:800;margin-top:.25rem">{row["buts"]} buts</div>'
                f'</div>', unsafe_allow_html=True)
        st.markdown("")
    aff = clt.rename(columns={"joueur":"Joueur","buts":"Buts","equipe":"Équipe"})[["Joueur","Équipe","Buts"]]
    st.dataframe(aff,use_container_width=True,height=420)
    st.markdown("### Profil d'un buteur")
    recherche = st.text_input("🔍 Rechercher un buteur", placeholder="Nom du joueur...")
    liste_joueurs = clt["joueur"].tolist()
    if recherche:
        liste_joueurs = [j for j in liste_joueurs if recherche.upper() in j.upper()]
    if not liste_joueurs:
        st.warning("Aucun joueur trouvé.")
        st.stop()
    j = st.selectbox("Résultats", liste_joueurs, label_visibility="collapsed")

    dj = df[df["joueur"]==j]
    eq_j = dj["equipe_marque"].mode().iloc[0]
    coul_j = COULEUR_EQUIPE.get(eq_j, D1_ROUGE)
    lg_j = logo_b64(eq_j, 32)

    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul_j};border-radius:11px;padding:.8rem 1rem;'
        f'display:flex;align-items:center;gap:.8rem;margin:.4rem 0 .8rem 0">'
        f'{lg_j}'
        f'<div><div style="font-size:1rem;font-weight:800">{j}</div>'
        f'<div style="color:{D1_GRIS};font-size:.78rem">{eq_j}</div></div>'
        f'<div style="margin-left:auto;font-size:1.6rem;font-weight:900;color:{coul_j}">{len(dj)} buts</div>'
        f'</div>', unsafe_allow_html=True
    )

    a,b,c,d2 = st.columns(4)
    a.metric("Buts", len(dj))
    b.metric("1re période", int((dj["periode"]==1).sum()))
    c.metric("2e période", int((dj["periode"]==2).sum()))
    d2.metric("Adversaires différents", dj["equipe_encaisse"].nunique())

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Progression sur la saison")
        prog = dj.groupby("journee").size().reindex(JOURNEES, fill_value=0).cumsum()
        fig_prog = go.Figure(go.Scatter(
            x=[f"J{j_}" for j_ in prog.index], y=prog.values,
            mode="lines+markers", name=j,
            line=dict(color=coul_j, width=3),
            fill="tozeroy", fillcolor=hex_to_rgba(coul_j, 0.18),
            marker=dict(size=5),
        ))
        fig_prog.update_yaxes(dtick=5)
        st.plotly_chart(style_fig(fig_prog, 250), use_container_width=True)
    with cd:
        st.markdown("### Buts par adversaire")
        adv = dj["equipe_encaisse"].value_counts().head(6)
        fig_adv = go.Figure()
        for eq_, n_ in adv.items():
            c_ = COULEUR_EQUIPE.get(eq_, D1_ROUGE)
            fig_adv.add_trace(go.Bar(x=[n_], y=[nc(eq_)], orientation="h",
                                     marker_color=c_, text=[n_],
                                     textposition="outside", textangle=0, showlegend=False,
                                     textfont=dict(size=14,color="#F5F2F3"),cliponaxis=False))
        fig_adv.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_adv, 250), use_container_width=True)

    axes_radar = ["Buts P1","Buts P2","En menant","À égalité","Est mené"]
    cg2, cd2 = st.columns(2)
    with cg2:
        st.markdown("### Radar — profil de buteur")
        vals_raw = [
            int((dj["periode"]==1).sum()), int((dj["periode"]==2).sum()),
            int((dj["situation"]=="Menant").sum()),
            int((dj["situation"]=="Égalité").sum()),
            int((dj["situation"]=="Mené").sum()),
        ]
        total_vals = sum(vals_raw) or 1
        # Normaliser en % du total (pas sur le max) pour mieux voir les proportions
        vals_pct = [v/total_vals*100 for v in vals_raw]
        fig_radar = go.Figure(go.Scatterpolar(
            r=vals_pct+[vals_pct[0]],
            theta=axes_radar+[axes_radar[0]],
            fill="toself",
            fillcolor=hex_to_rgba(coul_j, 0.35),
            line=dict(color=coul_j, width=3),
            name=j,
            mode="lines+markers+text",
            marker=dict(size=8, color=coul_j),
            customdata=vals_raw+[vals_raw[0]],
            hovertemplate="<b>%{theta}</b><br>%{customdata} buts (%{r:.0f}%)<extra></extra>",
            texttemplate="%{customdata}",
            textposition="top center",
            textfont=dict(size=13, color=D1_BLANC),
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0,60],
                                gridcolor="rgba(255,255,255,.15)",
                                tickfont=dict(size=10, color=D1_GRIS),
                                ticksuffix="%"),
                angularaxis=dict(gridcolor="rgba(255,255,255,.15)",
                                 tickfont=dict(size=13, color=D1_BLANC))
            )
        )
        st.plotly_chart(style_fig(fig_radar, 320), use_container_width=True)
        st.markdown("<p class='note'>Valeurs en % du total de buts du joueur. "
                    "Les chiffres = nombre de buts.</p>", unsafe_allow_html=True)
    with cd2:
        st.markdown("### Comparateur multi-buteurs")
        top_list = clt["joueur"].head(20).tolist()
        comp_sel = st.multiselect("Comparer avec",
                                  [x for x in top_list if x != j],
                                  default=top_list[1:3] if len(top_list)>2 else [],
                                  max_selections=3)
        fig_comp = go.Figure()
        for bu in [j]+comp_sel:
            dbu = df[df["joueur"]==bu]; eq_bu = dbu["equipe_marque"].mode().iloc[0] if len(dbu) else EQUIPES[0]
            coul_bu = COULEUR_EQUIPE.get(eq_bu, D1_ROUGE); tot_bu = len(dbu) or 1
            vr = [int((dbu["periode"]==1).sum())/tot_bu*100, int((dbu["periode"]==2).sum())/tot_bu*100,
                  int((dbu["situation"]=="Menant").sum())/tot_bu*100,
                  int((dbu["situation"]=="Égalité").sum())/tot_bu*100,
                  int((dbu["situation"]=="Mené").sum())/tot_bu*100]
            fig_comp.add_trace(go.Scatterpolar(
                r=vr+[vr[0]], theta=axes_radar+[axes_radar[0]],
                fill="toself", fillcolor=hex_to_rgba(coul_bu, 0.12),
                line=dict(color=coul_bu, width=2), name=bu.split()[0]
            ))
        fig_comp.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,100],
                            gridcolor="rgba(255,255,255,.1)", tickfont=dict(size=8)),
            angularaxis=dict(gridcolor="rgba(255,255,255,.1)")
        ))
        st.plotly_chart(style_fig(fig_comp, 300), use_container_width=True)
        st.markdown("<p class='note'>Valeurs en % du total de buts du joueur.</p>", unsafe_allow_html=True)

    # ---- PROFIL D'ORIGINE DU BUTEUR ----
    st.markdown("### Profil de but — type de buts marqués")
    dj_orig = dj[dj["origine"].notna()]
    if len(dj_orig) == 0:
        st.markdown(
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-radius:10px;padding:.9rem 1.1rem;color:{D1_GRIS};font-size:.88rem">'
            f'Origine des buts non disponible pour <b style="color:{D1_BLANC}">{j}</b> — '
            f'son équipe n\'a pas encore saisi les origines.</div>',
            unsafe_allow_html=True
        )
    else:
        n_tot_j = len(dj); n_orig_j = len(dj_orig)
        st.markdown(
            f'<span style="background:{coul_j};color:white;padding:.15rem .6rem;'
            f'border-radius:5px;font-weight:600;font-size:.78rem">'
            f'{n_orig_j}/{n_tot_j} buts analysés</span>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        oo_j = dj_orig["origine"].value_counts()
        cg_orig, cd_orig = st.columns(2)
        with cg_orig:
            fig_oj = go.Figure(go.Bar(
                x=oo_j.values, y=oo_j.index, orientation="h",
                marker_color=coul_j,
                text=[f"{v} ({v/n_orig_j*100:.0f}%)" for v in oo_j.values],
                textposition="outside", textangle=0,
                textfont=dict(size=14, color=D1_BLANC), cliponaxis=False
            ))
            fig_oj.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_oj, max(220, 32*len(oo_j))), use_container_width=True)
        with cd_orig:
            # Signature : origine principale + situation principale
            orig_principale = oo_j.index[0]
            sit_j = dj["situation"].value_counts()
            sit_principale = sit_j.index[0] if len(sit_j) else "—"
            clutch_j = int((dj["minute"] >= 36).sum())
            minute_fetiche = int(dj["minute"].mode().iloc[0]) if len(dj) else 0
            st.markdown(
                f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
                f'border-radius:12px;padding:1rem 1.2rem">'
                f'<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:.5px;color:{D1_GRIS};margin-bottom:.8rem">Signature de buteur</div>'
                f'<div style="margin-bottom:.6rem">'
                f'<span style="color:{D1_GRIS};font-size:.8rem">Type de but principal</span><br>'
                f'<b style="color:{coul_j};font-size:1.1rem">{orig_principale}</b>'
                f'<span style="color:{D1_GRIS};font-size:.8rem"> ({oo_j.iloc[0]} buts, {oo_j.iloc[0]/n_orig_j*100:.0f}%)</span>'
                f'</div>'
                f'<div style="margin-bottom:.6rem">'
                f'<span style="color:{D1_GRIS};font-size:.8rem">Situation la plus fréquente</span><br>'
                f'<b style="color:{D1_BLANC};font-size:1rem">{sit_principale}</b>'
                f'</div>'
                f'<div style="margin-bottom:.6rem">'
                f'<span style="color:{D1_GRIS};font-size:.8rem">Buts clutch (36\'-40\')</span><br>'
                f'<b style="color:{D1_DANGER if clutch_j==0 else D1_VERT};font-size:1rem">{clutch_j} buts</b>'
                f'</div>'
                f'<div>'
                f'<span style="color:{D1_GRIS};font-size:.8rem">Minute la plus fréquente</span><br>'
                f'<b style="color:{D1_BLANC};font-size:1rem">{minute_fetiche}\'</b>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown("<p class='note'>Profil basé sur les buts dont l'origine est renseignée. "
                    "Les données d'origine sont disponibles pour les équipes qui ont saisi "
                    "leurs données dans le fichier Excel.</p>", unsafe_allow_html=True)

    bloc_export(pdf_buteur(j), f"buteur_{j.replace(' ','_')}.pdf",
                f"Exporter la fiche de {j.split()[0]}")

# ============================================================================
# PAGE — COMPARATEUR DE BUTEURS
# ============================================================================
elif page == "Comparateur":
    st.title("Comparateur de buteurs")

    ordre_buteurs = sans_csc(df)["joueur"].value_counts().index.tolist()
    c_sel1, c_sel2 = st.columns(2)
    jA = c_sel1.selectbox("Joueur A", ordre_buteurs, index=0, key="cmp_a")
    jB = c_sel2.selectbox("Joueur B", ordre_buteurs,
                          index=1 if len(ordre_buteurs) > 1 else 0, key="cmp_b")

    if jA == jB:
        st.info("Choisis deux joueurs différents pour comparer.")
    else:
        dA = df[df["joueur"] == jA]
        dB = df[df["joueur"] == jB]
        COUL_A, COUL_B = D1_ROUGE, D1_OR

        def _eq_joueur(d):
            m = d["equipe_marque"].mode()
            return m.iloc[0] if len(m) else "—"
        eqA, eqB = _eq_joueur(dA), _eq_joueur(dB)

        def grp_bar(cats, va, vb, h=280):
            fig = go.Figure()
            fig.add_trace(go.Bar(name=nj(jA), x=cats, y=va, marker_color=COUL_A,
                text=[str(x) if x else "" for x in va], textposition="outside",
                textangle=0, textfont=dict(size=12, color=D1_BLANC), cliponaxis=False))
            fig.add_trace(go.Bar(name=nj(jB), x=cats, y=vb, marker_color=COUL_B,
                text=[str(x) if x else "" for x in vb], textposition="outside",
                textangle=0, textfont=dict(size=12, color=D1_BLANC), cliponaxis=False))
            fig.update_layout(barmode="group")
            fig.update_yaxes(showticklabels=False)
            return style_fig(fig, h)

        # En-tête
        h1, h2 = st.columns(2)
        h1.markdown(_carte_stat(jA, len(dA), nc(eqA), COUL_A), unsafe_allow_html=True)
        h2.markdown(_carte_stat(jB, len(dB), nc(eqB), COUL_B), unsafe_allow_html=True)

        # Repères chiffrés
        st.markdown("### Repères")
        rA, rB = st.columns(2)
        for col_, d, nom, coul_ in [(rA, dA, jA, COUL_A), (rB, dB, jB, COUL_B)]:
            tot = len(d)
            mm = d["minute"].dropna().mean()
            cl = int((d["minute"] >= 36).sum())
            p2 = (d["periode"] == 2).sum() / (tot or 1) * 100
            with col_:
                st.markdown(f"<b style='color:{coul_}'>{nj(nom)}</b>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Minute moy", f"{mm:.0f}'" if tot else "—")
                m2.metric("Clutch 36-40'", cl)
                m3.metric("2e période", f"{p2:.0f}%")

        # Par période
        st.markdown("### Buts par période")
        vA = [int((dA["periode"] == 1).sum()), int((dA["periode"] == 2).sum())]
        vB = [int((dB["periode"] == 1).sum()), int((dB["periode"] == 2).sum())]
        st.plotly_chart(grp_bar(["1re période", "2e période"], vA, vB, 260),
                        use_container_width=True)

        # Situation au moment du but
        st.markdown("### Situation au moment du but")
        AFF = {"Mené": "Est mené", "Égalité": "À égalité", "Menant": "En tête"}
        base_sit = ["Mené", "Égalité", "Menant"]
        sA = dA["situation"].value_counts(); sB = dB["situation"].value_counts()
        st.plotly_chart(grp_bar([AFF[s] for s in base_sit],
                                [int(sA.get(s, 0)) for s in base_sit],
                                [int(sB.get(s, 0)) for s in base_sit], 260),
                        use_container_width=True)

        # Tranches de 5 minutes
        st.markdown("### Buts par tranche de 5 minutes")
        tr_cats = [f"{i+1}-{i+5}'" for i in range(0, 40, 5)]
        def _tr(d):
            t = pd.cut(d["minute"].dropna(), bins=range(0, 41, 5),
                       labels=tr_cats).value_counts().reindex(tr_cats, fill_value=0)
            return [int(x) for x in t]
        st.plotly_chart(grp_bar(tr_cats, _tr(dA), _tr(dB), 280), use_container_width=True)

        # Profil par type d'action (si origine dispo pour les deux)
        dA_o = dA[dA["origine"].notna()]; dB_o = dB[dB["origine"].notna()]
        if len(dA_o) and len(dB_o):
            st.markdown("### Profil par type d'action")
            oA = dA_o["origine"].value_counts(); oB = dB_o["origine"].value_counts()
            cats = sorted(set(oA.index) | set(oB.index))
            st.plotly_chart(grp_bar(cats,
                                    [int(oA.get(c, 0)) for c in cats],
                                    [int(oB.get(c, 0)) for c in cats], 320),
                            use_container_width=True)
        else:
            st.markdown("<p class='note'>Profil par type d'action indisponible : l'origine "
                        "des buts n'est saisie que pour certaines équipes.</p>",
                        unsafe_allow_html=True)


# ============================================================================
# PAGE — PROFIL TEMPOREL
# ============================================================================
elif page == "Profil temporel":
    st.title("Profil temporel des buts")
    eq=st.selectbox("Périmètre",["Tout le championnat"]+EQUIPES, key="pt_eq")
    d=df if eq=="Tout le championnat" else df[df["equipe_marque"]==eq]
    p1=int((d["periode"]==1).sum()); p2=int((d["periode"]==2).sum())
    c1,c2,c3=st.columns(3)
    c1.metric("Buts",len(d))
    c2.metric("1re période",p1,f"{p1/len(d)*100:.0f}%" if len(d) else "")
    c3.metric("2e période",p2,f"{p2/len(d)*100:.0f}%" if len(d) else "")
    st.markdown("### Buts par minute")
    mins=d["minute"].dropna().astype(int)
    serie=mins.value_counts().reindex(range(1,41),fill_value=0).sort_index()
    coul_b=[D1_ROUGE if m<=20 else D1_BORDEAUX_2 for m in serie.index]
    fig=go.Figure(go.Bar(x=[f"{m}'" for m in serie.index],y=serie.values,
                         marker_color=coul_b,text=serie.values,
                         textposition="outside",textangle=0,
                         textfont=dict(size=12,color=D1_BLANC)))
    fig.update_yaxes(showticklabels=False)
    fig.add_shape(type="line",x0="20'",x1="20'",y0=0,y1=1,yref="paper",
                  line=dict(color=D1_GRIS,width=1,dash="dot"))
    fig.add_annotation(x="20'",y=1,yref="paper",text="Mi-temps",
                       showarrow=False,font=dict(color=D1_GRIS,size=10),
                       yanchor="bottom",xanchor="right")
    st.plotly_chart(style_fig(fig,300),use_container_width=True)
    st.markdown("<p class='note'>Rouge = 1re période · Bordeaux = 2e période</p>",unsafe_allow_html=True)
    st.markdown("### Buts par tranche de 5 minutes")
    tr=pd.cut(mins,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    coul_q=[D1_ROUGE if i<4 else D1_BORDEAUX_2 for i in range(8)]
    fig2=go.Figure(go.Bar(x=tr.index.astype(str),y=tr.values,marker_color=coul_q,
                          text=tr.values,textposition="outside",textangle=0,
                          textfont=dict(size=13,color=D1_BLANC)))
    fig2.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig2,270),use_container_width=True)

elif page == "Dynamique de score":
    st.title("Dynamique de score")
    st.markdown("<p class='note'>Situation de l'équipe qui marque, juste avant son but.</p>",unsafe_allow_html=True)
    eq=st.selectbox("Périmètre",["Tout le championnat"]+EQUIPES,key="ds_eq")
    d=df if eq=="Tout le championnat" else df[df["equipe_marque"]==eq]
    d=d[d["situation"].notna()]
    ordre=["Mené","Égalité","Menant"]
    coul_sit={"Mené":D1_ROUGE,"Égalité":D1_OR,"Menant":D1_VERT}
    sit=d["situation"].value_counts().reindex(ordre,fill_value=0)
    tot=sit.sum() or 1
    c1,c2,c3=st.columns(3)
    c1.metric("Est mené",int(sit["Mené"]),f"{sit['Mené']/tot*100:.0f}%")
    c2.metric("À égalité",int(sit["Égalité"]),f"{sit['Égalité']/tot*100:.0f}%")
    c3.metric("En menant",int(sit["Menant"]),f"{sit['Menant']/tot*100:.0f}%")
    fig=go.Figure(go.Bar(x=["Est mené","Égalité","Menant"],y=sit.values,
                         marker_color=[coul_sit[s] for s in ordre],
                         text=[f"{v}  ({v/tot*100:.0f}%)" for v in sit.values],
                         textposition="outside",textangle=0,
                         textfont=dict(size=13,color=D1_BLANC),width=[0.4,0.4,0.4]))
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig,260),use_container_width=True)
    if eq=="Tout le championnat":
        st.markdown("### Comparaison par équipe")
        rows=[]
        for e in EQUIPES:
            de=df[(df["equipe_marque"]==e)&(df["situation"].notna())]
            if len(de):
                rows.append({"Équipe":e,
                    "pct_mené":(de["situation"]=="Mené").mean()*100,
                    "pct_egal":(de["situation"]=="Égalité").mean()*100,
                    "pct_men": (de["situation"]=="Menant").mean()*100})
        comp=pd.DataFrame(rows)
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("#### Est mené")
            s=comp.sort_values("pct_mené",ascending=False)
            fig_m=go.Figure(go.Bar(x=s["pct_mené"].round(0),y=[nc(e) for e in s["Équipe"]],
                orientation="h",marker_color=D1_ROUGE,
                text=[f"{v:.0f}%" for v in s["pct_mené"]],
                textposition="outside",textangle=0,
                textfont=dict(size=13,color=D1_BLANC),cliponaxis=False))
            fig_m.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_m,max(280,28*len(s))),use_container_width=True)
        with c2:
            st.markdown("#### À égalité")
            s=comp.sort_values("pct_egal",ascending=False)
            fig_e=go.Figure(go.Bar(x=s["pct_egal"].round(0),y=[nc(e) for e in s["Équipe"]],
                orientation="h",marker_color=D1_OR,
                text=[f"{v:.0f}%" for v in s["pct_egal"]],
                textposition="outside",textangle=0,
                textfont=dict(size=13,color=D1_BLANC),cliponaxis=False))
            fig_e.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_e,max(280,28*len(s))),use_container_width=True)
        with c3:
            st.markdown("#### En menant")
            s=comp.sort_values("pct_men",ascending=False)
            fig_v=go.Figure(go.Bar(x=s["pct_men"].round(0),y=[nc(e) for e in s["Équipe"]],
                orientation="h",marker_color=D1_VERT,
                text=[f"{v:.0f}%" for v in s["pct_men"]],
                textposition="outside",textangle=0,
                textfont=dict(size=13,color=D1_BLANC),cliponaxis=False))
            fig_v.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_v,max(280,28*len(s))),use_container_width=True)

elif page == "Analyse avancée":
    st.title("Analyse avancée")
    matchs = construire_matchs()

    st.markdown("### Régularité offensive")
    rows_reg=[]
    for eq in EQUIPES:
        meq=matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
        bpm=[]
        for _,m in meq.iterrows():
            dm=df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&(df["equipe_exterieure"]==m["ext"])]
            bpm.append(int((dm["equipe_marque"]==eq).sum()))
        if bpm:
            rows_reg.append({"equipe":eq,"moy":pd.Series(bpm).mean(),"std":pd.Series(bpm).std(ddof=0),"min":min(bpm),"max":max(bpm)})
    reg=pd.DataFrame(rows_reg).sort_values("moy",ascending=False)
    cg_r,cd_r=st.columns(2)
    with cg_r:
        st.markdown("#### Moyenne de buts/match")
        fig_moy=go.Figure()
        for _,r in reg.iterrows():
            c_eq=COULEUR_EQUIPE.get(r["equipe"],D1_ROUGE)
            fig_moy.add_trace(go.Bar(x=[round(r["moy"],1)],y=[nc(r["equipe"])],
                orientation="h",marker_color=c_eq,text=[f'{r["moy"]:.1f}'],
                textposition="outside",textangle=0,showlegend=False,
                textfont=dict(size=13,color=D1_BLANC),cliponaxis=False,
                hovertemplate=f'{r["equipe"]}<br>Moy:{r["moy"]:.1f} Min:{r["min"]} Max:{r["max"]}<extra></extra>'))
        fig_moy.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_moy,max(320,30*len(reg))),use_container_width=True)
    with cd_r:
        st.markdown("#### Régularité (écart-type)")
        reg_s=reg.sort_values("std")
        fig_std=go.Figure()
        for _,r in reg_s.iterrows():
            ratio=(r["std"]-reg_s["std"].min())/((reg_s["std"].max()-reg_s["std"].min()) or 1)
            c_eq=D1_VERT if ratio<0.4 else(D1_OR if ratio<0.7 else D1_DANGER)
            fig_std.add_trace(go.Bar(x=[round(r["std"],1)],y=[nc(r["equipe"])],
                orientation="h",marker_color=c_eq,text=[f'± {r["std"]:.1f}'],
                textposition="outside",textangle=0,showlegend=False,
                textfont=dict(size=13,color=D1_BLANC),cliponaxis=False))
        fig_std.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_std,max(320,30*len(reg_s))),use_container_width=True)
    st.markdown("<p class='note'>🟢 régulier · 🟡 moyen · 🔴 irrégulier</p>",unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### Radar comparatif")
    eq_radar=st.multiselect("Équipes",EQUIPES,default=EQUIPES[:3],max_selections=4)
    if len(eq_radar)>=2:
        indicateurs=["Volume offensif","Solidité défensive","Résistance","Régularité","Collectif"]
        def radar_vals(eq):
            dp=df[df["equipe_marque"]==eq]; dc=df[df["equipe_encaisse"]==eq]
            meq_r=matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]; nm=len(meq_r) or 1
            vol_off=len(dp)/nm; enc_pm=len(dc)/nm
            rs_r=analyser_retours_score(eq); menes=rs_r["mv"]+rs_r["mn"]+rs_r["md"]
            resistance=(rs_r["mv"]+rs_r["mn"])/menes*100 if menes>0 else 50
            bpm_l=[]
            for _,m in meq_r.iterrows():
                dm2=df[(df["journee"]==m["journee"])&(df["equipe_domicile"]==m["dom"])&(df["equipe_exterieure"]==m["ext"])]
                bpm_l.append(int((dm2["equipe_marque"]==eq).sum()))
            std=pd.Series(bpm_l).std(ddof=0) if len(bpm_l)>1 else 0
            collectif=float(sans_csc(dp)["joueur"].nunique())
            return [vol_off,enc_pm,resistance,std,collectif]
        all_vals={eq:radar_vals(eq) for eq in eq_radar}
        all_matrix=pd.DataFrame(all_vals,index=indicateurs)
        axes_inv={"Solidité défensive","Régularité"}
        norm=all_matrix.copy()
        for idx in indicateurs:
            mn=all_matrix.loc[idx].min(); mx=all_matrix.loc[idx].max()
            if mx!=mn:
                vn=(all_matrix.loc[idx]-mn)/(mx-mn)*100
                norm.loc[idx]=100-vn if idx in axes_inv else vn
            else:
                norm.loc[idx]=50
        fig_radar=go.Figure()
        for eq in eq_radar:
            vals=norm[eq].tolist(); raw=all_matrix[eq].tolist()
            raw_labels=[f"{raw[0]:.1f} buts/match",f"{raw[1]:.1f} encaissés/match",
                f"{raw[2]:.0f}% résultat positif quand mené",f"écart-type {raw[3]:.1f}",f"{int(raw[4])} buteurs"]
            coul=COULEUR_EQUIPE.get(eq,D1_ROUGE)
            fig_radar.add_trace(go.Scatterpolar(
                r=vals+[vals[0]],theta=indicateurs+[indicateurs[0]],name=nc(eq),
                line=dict(color=coul,width=2.5),fill="toself",fillcolor=hex_to_rgba(coul,0.15),
                customdata=raw_labels+[raw_labels[0]],
                hovertemplate="<b>%{theta}</b><br>%{customdata}<extra></extra>"))
        fig_radar.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True,range=[0,100],gridcolor="rgba(255,255,255,.1)",tickfont=dict(size=9)),
            angularaxis=dict(gridcolor="rgba(255,255,255,.1)",tickfont=dict(size=13,color=D1_BLANC))))
        st.plotly_chart(style_fig(fig_radar,460),use_container_width=True)
        st.markdown(
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:10px;padding:.8rem 1rem;font-size:.8rem;color:{D1_GRIS}">'+
            f'<b style="color:{D1_BLANC}">Lecture</b> — tous les axes "plus = mieux", normalisés 0-100.<br>'+
            f'<b>Volume offensif</b> = buts/match · <b>Solidité défensive</b> = inverse buts encaissés/match · '+
            f'<b>Résistance</b> = % résultats positifs quand mené · <b>Régularité</b> = inverse écart-type · <b>Collectif</b> = nb buteurs différents'+
            f'</div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Heatmap — quand chaque équipe marque")
    eq_hm=st.multiselect("Équipes",EQUIPES,default=[],key="hm_eq")
    equipes_hm=eq_hm if eq_hm else EQUIPES
    clt_hm=construire_classement(); ordre_hm=[e for e in clt_hm["equipe"].tolist() if e in equipes_hm]
    pivot_hm2=(df[df["equipe_marque"].isin(equipes_hm)]
        .groupby(["equipe_marque","minute"]).size().reset_index(name="buts")
        .pivot(index="equipe_marque",columns="minute",values="buts")
        .reindex(ordre_hm).reindex(columns=range(1,41),fill_value=0).fillna(0))
    fig_hm2=go.Figure(go.Heatmap(
        z=pivot_hm2.values,x=[f"{m}'" for m in range(1,41)],
        y=[nc(e) for e in pivot_hm2.index],
        colorscale=[[0,"rgba(15,17,23,1)"],[0.4,"rgba(0,80,120,0.7)"],[1,D1_ROUGE]],
        text=[[str(int(v)) if v>0 else "" for v in row] for row in pivot_hm2.values],
        texttemplate="%{text}",textfont=dict(size=10,color="white"),
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z} buts<extra></extra>",showscale=True,
        colorbar=dict(len=0.8,thickness=12,tickfont=dict(size=10))))
    # Mi-temps : add_shape car axe catégoriel (add_vline ne marche pas)
    fig_hm2.add_shape(type="line", x0=19.5, x1=19.5, y0=-0.5, y1=len(ordre_hm)-0.5,
                      line=dict(color=D1_GRIS, width=1.5, dash="dot"))
    fig_hm2.add_annotation(x=19.5, y=-0.8, text="Mi-temps", showarrow=False,
                            font=dict(color=D1_GRIS, size=10), yanchor="top", xanchor="center")
    fig_hm2.update_xaxes(tickfont=dict(size=10),
        tickvals=[f"{m}'" for m in [1,5,10,15,20,25,30,35,40]])
    fig_hm2.update_yaxes(tickfont=dict(size=11))
    fig_hm2.update_layout(width=780)
    st.plotly_chart(style_fig(fig_hm2,max(300,38*len(ordre_hm))),use_container_width=False)


elif page == "Power play":
    st.title("Power play")
    st.markdown(
        "<p class='note'>Buts dont l'origine saisie est « Power play ». "
        "Données limitées aux équipes ayant renseigné l'origine de leurs buts.</p>",
        unsafe_allow_html=True,
    )

    pp = analyser_power_play()

    if pp.empty:
        st.info("Aucun but power play enregistré pour l'instant.")
    else:
        mins = pp["minute"].dropna().astype(int)

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(_carte_stat("Buts power play", len(pp),
                    f"sur {len(df)} buts au total"), unsafe_allow_html=True)
        c2.markdown(_carte_stat("Équipes", pp["equipe_marque"].nunique(),
                    "ont marqué en power play", D1_ROUGE), unsafe_allow_html=True)
        c3.markdown(_carte_stat("Buteurs", sans_csc(pp)["joueur"].nunique(),
                    "différents", D1_VERT), unsafe_allow_html=True)
        c4.markdown(_carte_stat("Minute moyenne",
                    f"{mins.mean():.0f}'" if len(mins) else "—",
                    "du but", D1_OR), unsafe_allow_html=True)

        # --- Par équipe ---
        st.markdown("### Buts power play par équipe")
        parq = pp["equipe_marque"].value_counts()
        if len(parq):
            st.plotly_chart(barh_equipes(parq.index.tolist(), parq.values.tolist(),
                            h=max(220, 42*len(parq))), use_container_width=True)

        # --- Par minute ---
        st.markdown("### À quelles minutes ?")
        if len(mins):
            serie = mins.value_counts().reindex(range(1, 41), fill_value=0).sort_index()
            coul = [D1_ROUGE if m >= 36 else D1_BORDEAUX_2 for m in serie.index]
            fig = go.Figure(go.Bar(
                x=[f"{m}'" for m in serie.index], y=serie.values,
                marker_color=coul, text=[v if v else "" for v in serie.values],
                textposition="outside", textangle=0, textfont=dict(size=12, color=D1_BLANC)))
            fig.update_yaxes(showticklabels=False)
            fig.add_shape(type="line", x0="35'", x1="35'", y0=0, y1=1, yref="paper",
                          line=dict(color=D1_GRIS, width=1, dash="dot"))
            fig.add_annotation(x="35'", y=1, yref="paper", text="36'–40'", showarrow=False,
                               font=dict(color=D1_GRIS, size=10), yanchor="bottom", xanchor="left")
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)

        # --- Situation au moment du but (donnée enregistrée) ---
        st.markdown("### Situation au moment du but")
        AFF = {"Menant": "En tête", "Égalité": "À égalité", "Mené": "Est mené"}
        sit = pp["situation"].value_counts()
        ordre = [s for s in ["Mené", "Égalité", "Menant"] if s in sit.index]
        cS = {"Mené": D1_DANGER, "Égalité": D1_OR, "Menant": D1_VERT}
        fig3 = go.Figure(go.Bar(
            x=[AFF[s] for s in ordre], y=[int(sit[s]) for s in ordre],
            marker_color=[cS[s] for s in ordre],
            text=[int(sit[s]) for s in ordre], textposition="outside",
            textangle=0, textfont=dict(size=14, color=D1_BLANC)))
        fig3.update_yaxes(showticklabels=False)
        st.plotly_chart(style_fig(fig3, 260), use_container_width=True)

        # --- En étant mené de combien (donnée enregistrée) ---
        menes = pp[pp["situation"] == "Mené"].copy()
        if len(menes):
            st.markdown("### En étant mené de combien ?")
            menes["deficit"] = (-menes["ecart_avant"]).astype(int)
            dd = menes["deficit"].value_counts().sort_index()
            labels = [f"−{d} but" + ("s" if d > 1 else "") for d in dd.index]
            fig2 = go.Figure(go.Bar(x=labels, y=dd.values, marker_color=D1_DANGER,
                            text=dd.values, textposition="outside", textangle=0,
                            textfont=dict(size=14, color=D1_BLANC)))
            fig2.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig2, 260), use_container_width=True)

        # --- Buteurs ---
        st.markdown("### Buteurs en power play")
        bz = sans_csc(pp)["joueur"].value_counts().head(10)
        if len(bz):
            noms = [nj(n) for n in bz.index][::-1]
            vals = bz.values.tolist()[::-1]
            figb = go.Figure(go.Bar(x=vals, y=noms, orientation="h",
                            marker_color=D1_ROUGE, text=vals, textposition="outside",
                            textangle=0, textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
            figb.update_xaxes(showticklabels=False)
            st.plotly_chart(style_fig(figb, max(220, 34*len(bz))), use_container_width=True)

        # --- Export ---
        exp = pp[["journee", "equipe_marque", "equipe_encaisse", "minute", "periode",
                  "situation", "score_marque_avant", "score_encaisse_avant", "joueur"]] \
            .sort_values(["journee", "minute"])
        dl_csv(exp, "Exporter les buts power play (CSV)", "power_play_d1.csv")

        st.markdown(
            f"<p class='note' style='margin-top:1rem'>Origine saisie pour "
            f"{len(EQUIPES_AVEC_ORIGINE)} équipes sur {len(EQUIPES)}.</p>",
            unsafe_allow_html=True,
        )


elif page == "Confrontations":
    st.title("Confrontations directes")
    c1,c2=st.columns(2)
    e1=c1.selectbox("Équipe A",EQUIPES,index=0)
    e2=c2.selectbox("Équipe B",EQUIPES,index=1 if len(EQUIPES)>1 else 0)
    if e1==e2:
        st.warning("Choisis deux équipes différentes."); st.stop()
    masque=(((df["equipe_marque"]==e1)&(df["equipe_encaisse"]==e2))|
            ((df["equipe_marque"]==e2)&(df["equipe_encaisse"]==e1)))
    d=df[masque]
    if d.empty:
        st.info("Aucun but recensé entre ces deux équipes."); st.stop()
    matchs_h2h=construire_matchs()
    mh2h=matchs_h2h[((matchs_h2h["dom"]==e1)&(matchs_h2h["ext"]==e2))|
                    ((matchs_h2h["dom"]==e2)&(matchs_h2h["ext"]==e1))]
    b1=int((d["equipe_marque"]==e1).sum()); b2=int((d["equipe_marque"]==e2).sum())
    v1=(int(((mh2h["dom"]==e1)&(mh2h["res_dom"]=="V")).sum())+
        int(((mh2h["ext"]==e1)&(mh2h["res_ext"]=="V")).sum()))
    v2=(int(((mh2h["dom"]==e2)&(mh2h["res_dom"]=="V")).sum())+
        int(((mh2h["ext"]==e2)&(mh2h["res_ext"]=="V")).sum()))
    nb_nuls=len(mh2h)-v1-v2
    coul1=COULEUR_EQUIPE.get(e1,D1_ROUGE); coul2=COULEUR_EQUIPE.get(e2,D1_BLEU)
    lg1=logo_b64(e1,44); lg2=logo_b64(e2,44)
    tot_b=b1+b2 or 1; pct1=b1/tot_b*100; pct2=b2/tot_b*100
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:13px;padding:1.1rem;margin-bottom:.8rem">'
        f'<div style="display:flex;align-items:center;justify-content:space-between">'
        f'<div style="flex:1;text-align:center">{lg1}<br><b style="font-size:.88rem">{nc(e1)}</b>'
        f'<div style="color:{coul1};font-size:1.9rem;font-weight:900;margin:.2rem 0">{b1}</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem">{v1} victoire{"s" if v1!=1 else ""}</div></div>'
        f'<div style="text-align:center;padding:0 1.2rem">'
        f'<div style="color:{D1_GRIS};font-size:.75rem;margin-bottom:.25rem">{len(mh2h)} rencontre{"s" if len(mh2h)!=1 else ""}</div>'
        f'<div style="font-size:1.2rem;font-weight:700;color:{D1_GRIS}">VS</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem;margin-top:.25rem">{nb_nuls} nul{"s" if nb_nuls!=1 else ""}</div></div>'
        f'<div style="flex:1;text-align:center">{lg2}<br><b style="font-size:.88rem">{nc(e2)}</b>'
        f'<div style="color:{coul2};font-size:1.9rem;font-weight:900;margin:.2rem 0">{b2}</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem">{v2} victoire{"s" if v2!=1 else ""}</div></div></div>'
        f'<div style="margin-top:.8rem">'
        f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden">'
        f'<div style="width:{pct1:.1f}%;background:{coul1}"></div>'
        f'<div style="width:{pct2:.1f}%;background:{coul2}"></div></div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.74rem;color:{D1_GRIS};margin-top:.15rem">'
        f'<span>{pct1:.0f}% des buts</span><span>{pct2:.0f}% des buts</span></div></div></div>',
        unsafe_allow_html=True)
    if len(mh2h):
        st.markdown("### Résultats")
        for _,m in mh2h.sort_values("journee").iterrows():
            bc_dom=D1_VERT if m["res_dom"]=="V" else(D1_OR if m["res_dom"]=="N" else D1_DANGER)
            bc_ext=D1_VERT if m["res_dom"]=="D" else(D1_OR if m["res_dom"]=="N" else D1_DANGER)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:1rem;padding:.28rem .6rem;'
                f'background:{D1_CARTE};border-radius:7px;margin:.15rem 0;font-size:.86rem">'
                f'<span style="color:{D1_GRIS};width:45px">J{int(m["journee"])}</span>'
                f'<span style="flex:1;text-align:right;font-weight:600">{m["dom"]}</span>'
                f'<span style="font-weight:800;padding:0 .7rem">'
                f'<span style="color:{bc_dom}">{m["score_dom"]}</span>'
                f'<span style="color:{D1_GRIS}"> — </span>'
                f'<span style="color:{bc_ext}">{m["score_ext"]}</span></span>'
                f'<span style="flex:1;font-weight:600">{m["ext"]}</span></div>',
                unsafe_allow_html=True)
    st.markdown("### Détail des buts")
    det=(d.sort_values(["journee","periode","minute"])
         [["journee","equipe_marque","joueur","periode","minute","situation","origine"]]
         .rename(columns={"journee":"J","equipe_marque":"Marque","joueur":"Buteur",
                          "periode":"Pér.","minute":"Min","situation":"Situation","origine":"Origine"}))
    det["Origine"]=det["Origine"].fillna("—")
    st.dataframe(det,use_container_width=True,height=320)
    dl_csv(det,"⬇ CSV",f"h2h_{nc(e1)}_{nc(e2)}.csv")


if page == "Rapport équipe":
    st.title("Rapport équipe complet")
    st.markdown("<p class='note'>Génère un rapport PDF complet pour chaque équipe — "
                "5 sections : vue d'ensemble, analyse tactique, profil temporel, "
                "buteurs, origines.</p>", unsafe_allow_html=True)

    eq = sel_equipe(key="eq_rapport")
    coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
    lg   = logo_b64(eq, 52)
    clt  = construire_classement()
    rang_row = clt[clt["equipe"]==eq].iloc[0]
    rang = clt[clt["equipe"]==eq].index[0]+1
    dpour = df[df["equipe_marque"]==eq]
    dcontre = df[df["equipe_encaisse"]==eq]

    # Aperçu rapide
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul};border-radius:12px;padding:1rem 1.2rem;'
        f'display:flex;align-items:center;gap:1rem;margin-bottom:1rem">'
        f'{lg}<div style="flex:1">'
        f'<div style="font-size:1.1rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.82rem;margin-top:.2rem">'
        f'Rang <b style="color:{coul}">{rang}</b> · {int(rang_row["Pts"])} pts · '
        f'{int(rang_row["BP"])} buts marqués · {int(rang_row["BC"])} encaissés</div>'
        f'<div style="margin-top:.3rem">{forme_ronds(rang_row["forme"])}</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:.72rem;color:{D1_GRIS};text-transform:uppercase;letter-spacing:.5px">Contenu du rapport</div>'
        f'<div style="font-size:.82rem;color:{D1_BLANC};margin-top:.3rem">'
        f'01 Vue d\'ensemble &nbsp;·&nbsp; 02 Analyse Tactique<br>'
        f'03 Analyse Temporelle &nbsp;·&nbsp; 04 Buteurs'
        f'{"&nbsp;·&nbsp; 05 Origines" if eq in EQUIPES_AVEC_ORIGINE else ""}'
        f'</div></div>'
        f'</div>', unsafe_allow_html=True
    )

    # Aperçu des chiffres clés
    c1,c2,c3,c4 = st.columns(4)
    pb  = analyser_premier_but(eq)
    de2 = analyser_dom_ext(eq)
    vd2,nd2,dd2 = de2["dom"]; ve2,ne2,de2_ = de2["ext"]
    td2 = vd2+nd2+dd2 or 1; te2 = ve2+ne2+de2_ or 1
    m_tot2 = pb["marque"]["total"] or 1

    c1.metric("Taux de victoire", f'{int(rang_row["V"])/len(construire_matchs()[(construire_matchs()["dom"]==eq)|(construire_matchs()["ext"]==eq)])*100:.0f}%')
    c2.metric("Buts/match", f"{len(dpour)/len(construire_matchs()[(construire_matchs()['dom']==eq)|(construire_matchs()['ext']==eq)]):.1f}")
    c3.metric("% victoire si 1er but", f"{pb['marque']['V']/m_tot2*100:.0f}%")
    c4.metric("% victoire dom.", f"{vd2/td2*100:.0f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="background:rgba(192,0,24,.08);border:1px solid {D1_ROUGE};'
        f'border-radius:10px;padding:.8rem 1rem;margin-bottom:.8rem;font-size:.88rem">'
        f'📋 Le rapport PDF contient toutes les sections avec tableaux et barres visuelles, '
        f'optimisé pour être envoyé à un staff technique ou présenté en réunion.</div>',
        unsafe_allow_html=True
    )

    bloc_export(pdf_rapport_complet(eq),
                f"rapport_D1_{eq[:20].replace(' ','_')}_J{max(JOURNEES)}.pdf",
                f"Générer le rapport — {eq}")

# ============================================================================
if page == "Fiche équipe":
    st.title("Fiche équipe")
    eq = sel_equipe(key="eq_fiche")
    coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
    clt  = construire_classement()
    rang_row = clt[clt["equipe"]==eq].iloc[0]
    rang = clt[clt["equipe"]==eq].index[0]+1
    lg   = logo_b64(eq, 48)
    dpour   = df[df["equipe_marque"]==eq]
    dcontre = df[df["equipe_encaisse"]==eq]

    # Header commun
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul};border-radius:11px;padding:.9rem 1.1rem;'
        f'display:flex;align-items:center;gap:.9rem;margin-bottom:1rem">'
        f'{lg}<div style="flex:1">'
        f'<div style="font-size:1.1rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.82rem">'
        f'Rang <b style="color:{coul}">{rang}</b> · {int(rang_row["Pts"])} pts · '
        f'{int(rang_row["V"])}V {int(rang_row["N"])}N {int(rang_row["D"])}D</div>'
        f'<div style="margin-top:.25rem">{forme_ronds(rang_row["forme"])}</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:1.5rem;font-weight:900;color:{coul}">{len(dpour)}</div>'
        f'<div style="font-size:.72rem;color:{D1_GRIS};text-transform:uppercase">buts marqués</div>'
        f'<div style="font-size:.82rem;color:{D1_GRIS};margin-top:.2rem">{len(dcontre)} encaissés · '
        f'{len(dpour)-len(dcontre):+d} diff</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊  Vue générale",
        "🎯  Analyse Tactique",
        "🔭  Scouting",
        "⚽  Origines des buts",
    ])

    # ---- TAB 1 : VUE GÉNÉRALE ----
    with tab1:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Buteurs utilisés", sans_csc(dpour)["joueur"].nunique())
        c2.metric("Buts P1", int((dpour["periode"]==1).sum()))
        c3.metric("Buts P2", int((dpour["periode"]==2).sum()))
        clutch_n, total_dp = buts_clutch_eq(eq)
        c4.metric("Buts clutch (36-40')", clutch_n,
                  f"{clutch_n/total_dp*100:.0f}% des buts" if total_dp else "")

        cg, cd = st.columns(2)
        with cg:
            st.markdown("### Top buteurs")
            bb = sans_csc(dpour)["joueur"].value_counts()
            fig = go.Figure(go.Bar(x=bb.values, y=[nj(j) for j in bb.index], orientation="h",
                                   marker_color=coul, text=bb.values, textposition="outside",
                                   textangle=0, textfont=dict(size=14,color=D1_BLANC),
                                   cliponaxis=False))
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig, max(260,26*len(bb))), use_container_width=True)

        with cd:
            st.markdown("### Quand l'équipe marque")
            mins = dpour["minute"].dropna().astype(int)
            tr = pd.cut(mins, bins=range(0,41,5),
                        labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
            coul_tr = [coul if i<7 else D1_ROUGE for i in range(8)]
            fig2 = go.Figure(go.Bar(x=tr.index.astype(str), y=tr.values,
                                    marker_color=coul_tr, text=tr.values,
                                    textposition="outside", textangle=0,
                                    textfont=dict(size=14,color=D1_BLANC)))
            fig2.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig2, 260), use_container_width=True)
            st.markdown("<p class='note'>Les barres en rouge = buts entre 36'-40' (clutch)</p>",
                        unsafe_allow_html=True)

        # Buteurs clutch
        bc = buteurs_clutch_eq(eq)
        if len(bc):
            st.markdown("### Buteurs clutch (36'-40')")
            fig3 = go.Figure(go.Bar(
                x=bc.values, y=[nj(j) for j in bc.index], orientation="h",
                marker_color=D1_ROUGE, text=bc.values, textposition="outside",
                textangle=0, textfont=dict(size=14,color=D1_BLANC), cliponaxis=False
            ))
            fig3.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig3, max(200,26*len(bc))), use_container_width=True)

    # ---- TAB 2 : ANALYSE TACTIQUE ----
    with tab2:
        pb       = analyser_premier_but(eq)
        de_stats = analyser_dom_ext(eq)
        rs       = analyser_retours_score(eq)
        mo       = analyser_momentum(eq)
        m_tot = pb["marque"]["total"] or 1; e_tot = pb["encaisse"]["total"] or 1
        m_win = pb["marque"]["V"]/m_tot*100; e_win = pb["encaisse"]["V"]/e_tot*100
        vd, nd, dd = de_stats["dom"]; ve, ne, de_ = de_stats["ext"]
        td = vd+nd+dd or 1; te = ve+ne+de_ or 1

        # Titres + message
        ct1, ct2 = st.columns(2)
        with ct1:
            st.markdown("### Impact du premier but")
            msg = (f"{m_win:.0f}% de victoires en marquant le premier but, "
                   f"{e_win:.0f}% en l'encaissant.")
            st.markdown(f'<div style="background:{D1_CARTE};border-left:3px solid {coul};'
                        f'border-radius:8px;padding:.45rem .75rem;margin-bottom:.5rem;'
                        f'font-size:.82rem;color:{D1_GRIS}">{msg}</div>', unsafe_allow_html=True)
        with ct2:
            st.markdown("### Domicile vs Extérieur")

        ca,cb,cc,cd_col = st.columns(4)
        ca.markdown(_carte_stat(f"Marque 1er ({pb['marque']['total']} matchs)", f"{m_win:.0f}%",
            f"{pb['marque']['V']}V · {pb['marque']['N']}N · {pb['marque']['D']}D",
            D1_VERT if m_win>=70 else D1_OR), unsafe_allow_html=True)
        cb.markdown(_carte_stat(f"Encaisse 1er ({pb['encaisse']['total']} matchs)", f"{e_win:.0f}%",
            f"{pb['encaisse']['V']}V · {pb['encaisse']['N']}N · {pb['encaisse']['D']}D",
            D1_OR if e_win>=50 else D1_ROUGE), unsafe_allow_html=True)
        cc.markdown(_carte_stat(f"Domicile ({td} matchs)", f"{vd/td*100:.0f}%",
            f"{vd}V · {nd}N · {dd}D", coul), unsafe_allow_html=True)
        cd_col.markdown(_carte_stat(f"Extérieur ({te} matchs)", f"{ve/te*100:.0f}%",
            f"{ve}V · {ne}N · {de_}D", coul), unsafe_allow_html=True)

        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
        st.markdown("---")

        c3_t, c4_t = st.columns(2)
        with c3_t:
            st.markdown("### Retours au score")
            tot_m = rs["jamais"]+rs["mv"]+rs["mn"]+rs["md"]
            txt_ret = (f'N\'a jamais été menée sur les {tot_m} matchs.' if rs["mv"]+rs["mn"]+rs["md"]==0
                       else f'Sur {rs["mv"]+rs["mn"]+rs["md"]} matchs où l\'équipe a été menée, elle a réussi à revenir {rs["mv"]+rs["mn"]} fois.')
            st.markdown(f'<p style="color:{D1_GRIS};font-size:.82rem">{txt_ret}</p>', unsafe_allow_html=True)
            for label, val, c_ in [("Jamais menée",rs["jamais"],D1_VERT),("Menée → Victoire",rs["mv"],coul),("Menée → Nul",rs["mn"],D1_OR),("Menée → Défaite",rs["md"],D1_DANGER)]:
                pct = val/tot_m*100 if tot_m else 0
                st.markdown(
                    f'<div style="margin:.35rem 0">'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:.2rem">'
                    f'<span>{label}</span><b style="color:{c_}">{val} matchs</b></div>'
                    f'<div style="background:rgba(255,255,255,.06);border-radius:4px;height:8px;overflow:hidden">'
                    f'<div style="width:{pct:.0f}%;background:{c_};height:8px;border-radius:4px"></div>'
                    f'</div></div>', unsafe_allow_html=True)

            # Retournements mi-temps
            st.markdown("### Retournements (menés à la mi-temps)")
            ret = retournements_eq(eq)
            if ret["mene_ht"]:
                r_pct = (ret["v"]+ret["n"])/ret["mene_ht"]*100
                st.markdown(f'<p style="color:{D1_GRIS};font-size:.82rem">'
                            f'Menée à la mi-temps {ret["mene_ht"]} fois — résultat positif '
                            f'{ret["v"]+ret["n"]} fois ({r_pct:.0f}%)</p>', unsafe_allow_html=True)
                cr1,cr2,cr3 = st.columns(3)
                cr1.metric("→ Victoire", ret["v"]); cr2.metric("→ Nul", ret["n"]); cr3.metric("→ Défaite", ret["d"])
            else:
                st.info("Jamais menée à la mi-temps.")

        with c4_t:
            st.markdown("### Momentum après un but")
            st.markdown(f'<p style="color:{D1_GRIS};font-size:.82rem;margin-bottom:.6rem">'
                        f'Temps moyen entre deux buts consécutifs selon le contexte.</p>', unsafe_allow_html=True)
            couleurs_mo = {"Marque → Marque":D1_VERT,"Marque → Encaisse":D1_OR,"Encaisse → Marque":coul,"Encaisse → Encaisse":D1_ROUGE}
            for label, val in mo.items():
                c_ = couleurs_mo.get(label, D1_GRIS)
                txt = f"{val} min" if val else "—"
                st.markdown(
                    f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
                    f'border-left:3px solid {c_};border-radius:8px;padding:.45rem .8rem;margin:.25rem 0;'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="font-size:.85rem">{label}</span>'
                    f'<b style="color:{c_};font-size:1.1rem">{txt}</b>'
                    f'</div>', unsafe_allow_html=True)

            # Impact but rapide
            st.markdown("### Impact du but rapide (1-3')")
            ibr, ibr_sans = impact_but_rapide(eq)
            if ibr["total"]:
                win_ibr = ibr["V"]/ibr["total"]*100
                win_sans = ibr_sans["V"]/ibr_sans["total"]*100 if ibr_sans["total"] else 0
                st.markdown(f'<p style="color:{D1_GRIS};font-size:.82rem">'
                            f'But marqué dans les 3 premières minutes : {ibr["total"]} fois.</p>',
                            unsafe_allow_html=True)
                ci1,ci2 = st.columns(2)
                ci1.metric("Taux victoire avec but rapide", f"{win_ibr:.0f}%",
                           f"{ibr['V']}V · {ibr['N']}N · {ibr['D']}D")
                ci2.metric("Taux victoire sans but rapide", f"{win_sans:.0f}%")
            else:
                st.info("Aucun but marqué dans les 3 premières minutes.")

        st.markdown("---")
        st.markdown("### Bilan vs Top 6")
        vt6, nt6, dt6 = analyser_bilan_top6(eq)
        tot_t6 = vt6+nt6+dt6
        if tot_t6:
            cv,cn,cd2,ce = st.columns([1,1,1,5])
            cv.metric("Victoires",vt6); cn.metric("Nuls",nt6); cd2.metric("Défaites",dt6)
            ce.markdown(
                f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:10px;'
                f'padding:.7rem 1rem;display:flex;flex-direction:column;justify-content:center">'
                f'<div style="font-size:1.2rem;font-weight:800;color:{coul}">{vt6/tot_t6*100:.0f}%</div>'
                f'<div style="font-size:.8rem;color:{D1_GRIS}">de victoires sur {tot_t6} matchs contre le Top 6</div>'
                f'<div style="background:rgba(255,255,255,.06);border-radius:4px;height:6px;margin-top:.4rem;overflow:hidden">'
                f'<div style="width:{vt6/tot_t6*100:.0f}%;background:{coul};height:6px;border-radius:4px"></div>'
                f'</div></div>', unsafe_allow_html=True)
        else:
            st.info("Pas encore de matchs contre le Top 6.")

    # ---- TAB 3 : SCOUTING ----
    with tab3:
        matchs_sc = construire_matchs()
        meq_sc = matchs_sc[(matchs_sc["dom"]==eq)|(matchs_sc["ext"]==eq)]
        n_m_sc = len(meq_sc) or 1
        clean_sh = int((meq_sc.apply(lambda m:(m["score_ext"]==0 and m["dom"]==eq) or
                                     (m["score_dom"]==0 and m["ext"]==eq), axis=1)).sum())
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Buts/match (att.)", f"{len(dpour)/n_m_sc:.1f}")
        c2.metric("Buts/match (déf.)", f"{len(dcontre)/n_m_sc:.1f}")
        c3.metric("Clean sheets", clean_sh)
        c4.metric("Matchs analysés", n_m_sc)

        ong1, ong2 = st.tabs(["⚔ Profil offensif","🛡 Profil défensif"])
        with ong1:
            st.markdown("### Top buteurs")
            bb_sc = sans_csc(dpour)["joueur"].value_counts().head(10)
            total_sc = len(dpour) or 1
            fig_off = go.Figure()
            for j, n in bb_sc.items():
                fig_off.add_trace(go.Bar(x=[n], y=[nj(j)], orientation="h", marker_color=coul,
                    text=[f"{n} ({n/total_sc*100:.0f}%)"], textposition="outside", textangle=0,
                    showlegend=False, textfont=dict(size=13,color=D1_BLANC), cliponaxis=False))
            fig_off.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_off, max(240,26*len(bb_sc))), use_container_width=True)

            c_off1, c_off2 = st.columns(2)
            with c_off1:
                st.markdown("### Quand ils marquent")
                mins_p = dpour["minute"].dropna().astype(int)
                tr_p = pd.cut(mins_p, bins=range(0,41,5), labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
                fig_tp = go.Figure(go.Bar(x=tr_p.index.astype(str), y=tr_p.values, marker_color=coul,
                    text=tr_p.values, textposition="outside", textangle=0, textfont=dict(size=13,color=D1_BLANC)))
                fig_tp.update_yaxes(showticklabels=False)
                st.plotly_chart(style_fig(fig_tp, 260), use_container_width=True)
            with c_off2:
                st.markdown("### Situation offensive")
                sit_p = dpour[dpour["situation"].notna()]["situation"].value_counts()
                fig_sp = go.Figure(go.Bar(x=sit_p.index, y=sit_p.values,
                    marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit_p.index],
                    text=[f"{v} ({v/sit_p.sum()*100:.0f}%)" for v in sit_p.values],
                    textposition="outside", textangle=0, textfont=dict(size=13,color=D1_BLANC)))
                fig_sp.update_yaxes(showticklabels=False)
                st.plotly_chart(style_fig(fig_sp, 260), use_container_width=True)

            if eq in EQUIPES_AVEC_ORIGINE:
                st.markdown("### Origines des buts offensifs")
                oo_sc = dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
                fig_oo = go.Figure(go.Bar(x=oo_sc.values, y=oo_sc.index, orientation="h",
                    marker_color=coul, text=oo_sc.values, textposition="outside", textangle=0,
                    textfont=dict(size=13,color=D1_BLANC), cliponaxis=False))
                fig_oo.update_yaxes(autorange="reversed")
                st.plotly_chart(style_fig(fig_oo, max(220,28*len(oo_sc))), use_container_width=True)

        with ong2:
            st.markdown("### Tranche à risque")
            mins_c = dcontre["minute"].dropna().astype(int)
            tr_c = pd.cut(mins_c, bins=range(0,41,5), labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
            max_tc = tr_c.max(); best_tr = tr_c.idxmax()
            coul_tc = [D1_DANGER if t==best_tr else D1_BORDEAUX_2 for t in tr_c.index]
            fig_tc = go.Figure(go.Bar(x=tr_c.index.astype(str), y=tr_c.values, marker_color=coul_tc,
                text=tr_c.values, textposition="outside", textangle=0, textfont=dict(size=13,color=D1_BLANC)))
            fig_tc.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig_tc, 260), use_container_width=True)
            st.markdown(f"<p class='note'>Tranche la plus encaissée : <b>{best_tr}</b> ({int(tr_c.max())} buts encaissés)</p>",
                        unsafe_allow_html=True)

            c_def1, c_def2 = st.columns(2)
            with c_def1:
                st.markdown("### Situation adverse quand ils marquent")
                sit_c = dcontre[dcontre["situation"].notna()]["situation"].value_counts()
                fig_sc2 = go.Figure(go.Bar(x=sit_c.index, y=sit_c.values,
                    marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit_c.index],
                    text=[f"{v} ({v/sit_c.sum()*100:.0f}%)" for v in sit_c.values],
                    textposition="outside", textangle=0, textfont=dict(size=13,color=D1_BLANC)))
                fig_sc2.update_yaxes(showticklabels=False)
                st.plotly_chart(style_fig(fig_sc2, 260), use_container_width=True)
            with c_def2:
                st.markdown("### Principaux buteurs adverses")
                sc_adv = sans_csc(dcontre)["joueur"].value_counts().head(8)
                fig_sa = go.Figure(go.Bar(x=sc_adv.values, y=[nj(j) for j in sc_adv.index], orientation="h",
                    marker_color=D1_ROUGE, text=sc_adv.values, textposition="outside", textangle=0,
                    textfont=dict(size=13,color=D1_BLANC), cliponaxis=False))
                fig_sa.update_yaxes(autorange="reversed")
                st.plotly_chart(style_fig(fig_sa, max(220,28*len(sc_adv))), use_container_width=True)

            vul_p1=int((dcontre["periode"]==1).sum()); vul_p2=int((dcontre["periode"]==2).sum())
            tot_enc=vul_p1+vul_p2 or 1
            cd1,cd2,cd3=st.columns(3)
            cd1.metric("Encaissés P1",vul_p1,f"{vul_p1/tot_enc*100:.0f}%")
            cd2.metric("Encaissés P2",vul_p2,f"{vul_p2/tot_enc*100:.0f}%")
            cd3.metric("Encaisse le plus","1re période" if vul_p1>vul_p2 else "2e période")

            # ---- ORIGINES DES BUTS ENCAISSÉS ----
            st.markdown("### Par quel type d'action encaissent-ils ?")
            dc_orig = dcontre[dcontre["origine"].notna()]
            n_enc_tot = len(dcontre); n_enc_orig = len(dc_orig)
            if n_enc_orig == 0:
                st.markdown(
                    f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
                    f'border-radius:10px;padding:.8rem 1rem;color:{D1_GRIS};font-size:.85rem">'
                    f'Origines des buts encaissés non disponibles — les équipes qui ont '
                    f'marqué contre <b style="color:{D1_BLANC}">{nc(eq)}</b> n\'ont pas encore '
                    f'toutes saisi leurs données d\'origine.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<span style="background:{D1_ROUGE};color:white;padding:.15rem .6rem;'
                    f'border-radius:5px;font-weight:600;font-size:.78rem">'
                    f'{n_enc_orig}/{n_enc_tot} buts encaissés analysés</span>',
                    unsafe_allow_html=True
                )
                st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
                oo_enc = dc_orig["origine"].value_counts()
                cg_enc, cd_enc = st.columns(2)
                with cg_enc:
                    fig_enc = go.Figure(go.Bar(
                        x=oo_enc.values, y=oo_enc.index, orientation="h",
                        marker_color=D1_DANGER,
                        text=[f"{v} ({v/n_enc_orig*100:.0f}%)" for v in oo_enc.values],
                        textposition="outside", textangle=0,
                        textfont=dict(size=13, color=D1_BLANC), cliponaxis=False
                    ))
                    fig_enc.update_yaxes(autorange="reversed")
                    st.plotly_chart(style_fig(fig_enc, max(240, 32*len(oo_enc))),
                                    use_container_width=True)
                with cd_enc:
                    # Point faible principal
                    orig_faible = oo_enc.index[0]
                    pct_faible = oo_enc.iloc[0]/n_enc_orig*100
                    st.markdown(
                        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
                        f'border-left:4px solid {D1_DANGER};border-radius:12px;padding:1rem 1.2rem">'
                        f'<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;'
                        f'letter-spacing:.5px;color:{D1_GRIS};margin-bottom:.8rem">Origine la plus encaissée</div>'
                        f'<div style="color:{D1_ROUGE};font-size:1.2rem;font-weight:800">{orig_faible}</div>'
                        f'<div style="color:{D1_GRIS};font-size:.85rem;margin-top:.3rem">'
                        f'{oo_enc.iloc[0]} buts encaissés sur ce type ({pct_faible:.0f}%)</div>'
                        f'<hr style="border:none;border-top:1px solid {D1_BORDEAUX_2};margin:.7rem 0">'
                        f'<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;'
                        f'letter-spacing:.5px;color:{D1_GRIS};margin-bottom:.5rem">Répartition</div>',
                        unsafe_allow_html=True
                    )
                    for orig, n_o in oo_enc.items():
                        pct = n_o/n_enc_orig*100
                        st.markdown(
                            f'<div style="margin:.2rem 0;font-size:.82rem">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:.15rem">'
                            f'<span>{orig}</span><b style="color:{D1_ROUGE}">{n_o}</b></div>'
                            f'<div style="background:rgba(255,255,255,.06);border-radius:3px;height:5px">'
                            f'<div style="width:{pct:.0f}%;background:{D1_ROUGE};height:5px;border-radius:3px"></div>'
                            f'</div></div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"<p class='note'>Basé sur les buts marqués contre {nc(eq)} "
                            f"dont l'origine a été renseignée par l'équipe marquante.</p>",
                            unsafe_allow_html=True)

    # ---- TAB 4 : ORIGINES ----
    with tab4:
        if eq in EQUIPES_AVEC_ORIGINE:
            oo_t4 = dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
            n_r_t4 = int(dpour["origine"].notna().sum())
            st.markdown(f'<span style="background:{coul};color:white;padding:.15rem .6rem;'
                        f'border-radius:5px;font-weight:600;font-size:.78rem">'
                        f'{n_r_t4}/{len(dpour)} buts analysés</span>', unsafe_allow_html=True)
            fig_t4 = go.Figure(go.Bar(x=oo_t4.values, y=oo_t4.index, orientation="h",
                marker_color=coul, text=[f"{v} ({v/n_r_t4*100:.0f}%)" for v in oo_t4.values],
                textposition="outside", textangle=0, textfont=dict(size=14,color=D1_BLANC), cliponaxis=False))
            fig_t4.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_t4, max(280,30*len(oo_t4))), use_container_width=True)

            st.markdown("### Buteurs par type d'action")
            st.markdown("<p class='note'>Pour un type d'action donné, les joueurs de l'équipe qui marquent le plus dessus.</p>",
                        unsafe_allow_html=True)
            og_sel = st.selectbox("Type d'action", oo_t4.index.tolist(), key="conc_orig_fiche")
            sous_og = dpour[dpour["origine"] == og_sel]
            bb_og = sans_csc(sous_og)["joueur"].value_counts().head(10)
            if len(bb_og):
                noms_og = [nj(n) for n in bb_og.index][::-1]
                vals_og = bb_og.values.tolist()[::-1]
                fig_cog = go.Figure(go.Bar(x=vals_og, y=noms_og, orientation="h",
                    marker_color=coul, text=vals_og, textposition="outside", textangle=0,
                    textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
                fig_cog.update_xaxes(showticklabels=False)
                st.plotly_chart(style_fig(fig_cog, max(220, 30*len(bb_og))), use_container_width=True)
                st.markdown(f"<p class='note'>{int(len(sous_og))} buts de {nc(eq)} sur {og_sel.lower()}.</p>",
                            unsafe_allow_html=True)
        else:
            st.info("Origine des buts pas encore renseignée pour cette équipe.")

        if len(EQUIPES_AVEC_ORIGINE) > 1:
            st.markdown("### Comparaison multi-équipes")
            do_t4 = df[df["origine"].notna()]
            sel_t4 = st.multiselect("Équipes à comparer", EQUIPES_AVEC_ORIGINE,
                                    default=EQUIPES_AVEC_ORIGINE[:3], key="orig_sel_fiche")
            if sel_t4:
                sous_t4 = do_t4[do_t4["equipe_marque"].isin(sel_t4)]
                pivot_t4 = sous_t4.groupby(["equipe_marque","origine"]).size().reset_index(name="n")
                fig_pt = go.Figure()
                for i, og in enumerate(sorted(sous_t4["origine"].unique())):
                    sub = pivot_t4[pivot_t4["origine"]==og]
                    fig_pt.add_trace(go.Bar(name=og, x=[nc(e) for e in sub["equipe_marque"]],
                                            y=sub["n"], marker_color=PALETTE[i%len(PALETTE)]))
                fig_pt.update_layout(barmode="stack")
                st.plotly_chart(style_fig(fig_pt, 380), use_container_width=True)

    # Export PDF en bas
    bloc_export(pdf_rapport_complet(eq),
                f"rapport_{eq[:20].replace(' ','_')}.pdf",
                f"Exporter le rapport — {eq.split()[0]}")


# ============================================================================
# PAGE — LEXIQUE
# ============================================================================

elif page == "Bracket":
    st.title("Phase finale")

    if df_po.empty:
        st.info("Aucun match de phase finale enregistré pour l'instant.")
    else:
        from collections import defaultdict
        m_po1 = _matchs_phase("PO1")
        m_po2 = _matchs_phase("PO2")
        m_pof = _matchs_phase("POF")

        # Regroupe les matchs PO1+PO2 par paire d'équipes (demi-finales)
        demis = defaultdict(list)
        for m in m_po1 + m_po2:
            dom, ext = m[0], m[1]
            cle = frozenset((dom, ext))
            demis[cle].append(m)

        if not demis:
            st.info("Demi-finales pas encore commencées.")
        else:
            st.markdown("### Demi-finales")
            cols = st.columns(2)
            qualifies = []
            for idx, (cle, matches) in enumerate(demis.items()):
                with cols[idx % 2]:
                    eqs = list(cle)
                    # ordre : match aller (PO1) en premier
                    matches_tries = sorted(matches, key=lambda m: 0 if m[4]["journee"].astype(str).str.upper().iloc[0]=="PO1" else 1)
                    # cumul
                    cum = defaultdict(int)
                    for dom, ext, sd, se, _ in matches_tries:
                        cum[dom] += sd; cum[ext] += se
                    eq_a, eq_b = sorted(eqs, key=lambda e: -cum[e])
                    titre = f"{nc(eq_a)} – {nc(eq_b)}"
                    st.markdown(f"<div style='color:{D1_BLANC};font-weight:600;"
                                f"margin:.5rem 0 .2rem 0'>{titre}</div>",
                                unsafe_allow_html=True)
                    # affichage aller / retour + drill-down
                    for dom, ext, sd, se, dfm in matches_tries:
                        ph = str(dfm["journee"].iloc[0]).upper()
                        lib = "Aller" if ph == "PO1" else ("Retour" if ph == "PO2" else "Finale")
                        st.markdown(_bloc_match(dom, ext, sd, se, lib),
                                    unsafe_allow_html=True)
                        with st.expander(f"Détail — {nc(dom)} {sd}–{se} {nc(ext)}"):
                            _detail_match_po(dom, ext, dfm)
                    if len(matches_tries) < 2:
                        st.markdown(_bloc_match(eq_a, eq_b, 0, 0, "Retour", joue=False),
                                    unsafe_allow_html=True)
                    # cumul + qualifié
                    qual = _qualifie(matches_tries)
                    cumul_txt = (f"Cumul : <b>{nc(eq_a)} {cum[eq_a]}</b> – "
                                 f"<b>{cum[eq_b]} {nc(eq_b)}</b>")
                    if qual:
                        qualifies.append(qual)
                        cumul_txt += f"<br><span style='color:{D1_VERT};font-weight:600'>" \
                                     f"{nc(qual)} qualifié</span>"
                    elif len(matches_tries) >= 2:
                        cumul_txt += f"<br><span style='color:{D1_OR}'>" \
                                     f"Égalité — à départager (prolongation / TAB)</span>"
                    st.markdown(f"<p class='note' style='margin-top:.3rem'>{cumul_txt}</p>",
                                unsafe_allow_html=True)

            # Finale
            st.markdown("### Finale")
            if m_pof:
                for dom, ext, sd, se, dfm in m_pof:
                    st.markdown(_bloc_match(dom, ext, sd, se, "Finale"),
                                unsafe_allow_html=True)
                    with st.expander(f"Détail — {nc(dom)} {sd}–{se} {nc(ext)}"):
                        _detail_match_po(dom, ext, dfm)
                    if sd != se:
                        champion = dom if sd > se else ext
                        coul = COULEUR_EQUIPE.get(champion, D1_ROUGE)
                        st.markdown(
                            f'<div style="background:{D1_CARTE};border:2px solid {coul};'
                            f'border-radius:10px;padding:1rem;text-align:center;margin-top:.5rem">'
                            f'<div style="color:{D1_GRIS};font-size:.8rem;letter-spacing:1px;'
                            f'text-transform:uppercase">Champion de France</div>'
                            f'<div style="color:{coul};font-size:1.5rem;font-weight:700;'
                            f'margin-top:.3rem">🏆 {champion}</div></div>',
                            unsafe_allow_html=True)
            elif len(qualifies) == 2:
                st.markdown(_bloc_match(qualifies[0], qualifies[1], 0, 0, "Finale", joue=False),
                            unsafe_allow_html=True)
            else:
                st.markdown(f"<p class='note'>Finale à venir — opposera les deux "
                            f"qualifiés des demi-finales.</p>", unsafe_allow_html=True)


elif page == "Stats équipes PO":
    st.title("Stats des équipes — Phase finale")
    if df_po.empty:
        st.info("Aucune équipe encore impliquée en phase finale.")
    else:
        eqs_po = sorted(set(df_po["equipe_domicile"].dropna()) | set(df_po["equipe_exterieure"].dropna()))
        eq = st.selectbox("Équipe", eqs_po, key="po_eq_sel")
        coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
        s = _stats_po_equipe(eq)

        # Header carte
        st.markdown(
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-left:4px solid {coul};border-radius:8px;padding:.8rem 1rem;margin:.6rem 0">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div><b style="color:{coul};font-size:1.1rem">{eq}</b>'
            f'<div style="color:{D1_GRIS};font-size:.8rem">{s["matchs"]} match(s) de phase finale</div></div>'
            f'<div style="text-align:right">'
            f'<b style="color:{D1_BLANC};font-size:1.6rem">{s["buts_pour"]}</b>'
            f'<span style="color:{D1_GRIS}"> – </span>'
            f'<b style="color:{D1_GRIS};font-size:1.2rem">{s["buts_contre"]}</b>'
            f'<div style="color:{D1_GRIS};font-size:.75rem">{s["diff"]:+d} diff</div>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

        # KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(_carte_stat("Buts marqués", s["buts_pour"],
                    f"{s['buts_pour']/s['matchs']:.1f}/match" if s["matchs"] else "—"),
                    unsafe_allow_html=True)
        c2.markdown(_carte_stat("Buts encaissés", s["buts_contre"],
                    f"{s['buts_contre']/s['matchs']:.1f}/match" if s["matchs"] else "—",
                    D1_DANGER), unsafe_allow_html=True)
        nb_buteurs = sans_csc(s["pour_df"])["joueur"].nunique()
        c3.markdown(_carte_stat("Buteurs", nb_buteurs, "différents", D1_ROUGE),
                    unsafe_allow_html=True)
        mins_pour = s["pour_df"]["minute"].dropna()
        c4.markdown(_carte_stat("Minute moyenne",
                    f"{mins_pour.mean():.0f}'" if len(mins_pour) else "—",
                    "de ses buts", D1_OR), unsafe_allow_html=True)

        # Top buteurs PO de l'équipe
        st.markdown("### Buteurs de l'équipe en phase finale")
        bb = sans_csc(s["pour_df"])["joueur"].value_counts()
        if len(bb):
            noms = [nj(n) for n in bb.index][::-1]
            vals = bb.values.tolist()[::-1]
            fig = go.Figure(go.Bar(x=vals, y=noms, orientation="h",
                marker_color=coul, text=vals, textposition="outside", textangle=0,
                textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
            fig.update_xaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig, max(220, 32*len(bb))), use_container_width=True)
        else:
            st.info("L'équipe n'a pas encore marqué en phase finale.")

        # Origines
        st.markdown("### Origines des buts en phase finale")
        oo = s["pour_df"]["origine"].dropna()
        if len(oo):
            rep = oo.value_counts()
            fig_o = go.Figure(go.Bar(x=rep.values, y=rep.index, orientation="h",
                marker_color=coul, text=rep.values, textposition="outside", textangle=0,
                textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
            fig_o.update_xaxes(showticklabels=False); fig_o.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_o, max(220, 34*len(rep))), use_container_width=True)
        else:
            st.markdown("<p class='note'>Origines pas encore renseignées pour cette équipe en phase finale.</p>",
                        unsafe_allow_html=True)

        # Comparaison saison régulière
        st.markdown("### Comparaison avec la saison régulière")
        reg = df[df["equipe_marque"] == eq]
        reg_contre = df[df["equipe_encaisse"] == eq]
        n_match_reg = df[(df["equipe_domicile"]==eq)|(df["equipe_exterieure"]==eq)].groupby(
            ["journee","equipe_domicile","equipe_exterieure"]).ngroups
        comp = pd.DataFrame([
            {"Indicateur": "Buts marqués / match",
             "Saison régulière": f"{len(reg)/n_match_reg:.2f}" if n_match_reg else "—",
             "Phase finale": f"{s['buts_pour']/s['matchs']:.2f}" if s["matchs"] else "—"},
            {"Indicateur": "Buts encaissés / match",
             "Saison régulière": f"{len(reg_contre)/n_match_reg:.2f}" if n_match_reg else "—",
             "Phase finale": f"{s['buts_contre']/s['matchs']:.2f}" if s["matchs"] else "—"},
            {"Indicateur": "Total buts marqués",
             "Saison régulière": len(reg),
             "Phase finale": s["buts_pour"]},
            {"Indicateur": "Total buts encaissés",
             "Saison régulière": len(reg_contre),
             "Phase finale": s["buts_contre"]},
        ])
        st.dataframe(comp, use_container_width=True, hide_index=True)


elif page == "Buteurs PO":
    st.title("Buteurs en phase finale")

    if df_po.empty:
        st.info("Aucun but de phase finale enregistré.")
    else:
        d_po = sans_csc(df_po)
        st.markdown(f"<p class='note'>{len(df_po)} buts en phase finale · "
                    f"{d_po['joueur'].nunique()} buteurs différents.</p>",
                    unsafe_allow_html=True)

        clt_po = (d_po.groupby("joueur")
                  .agg(buts=("but_id", "count"),
                       equipe=("equipe_marque", lambda s: s.mode().iloc[0]))
                  .sort_values("buts", ascending=False)
                  .reset_index())

        # KPI
        c1, c2, c3 = st.columns(3)
        c1.markdown(_carte_stat("Buts PO", len(d_po), "(hors CSC)"), unsafe_allow_html=True)
        c2.markdown(_carte_stat("Buteurs différents", d_po["joueur"].nunique(),
                    "joueurs", D1_VERT), unsafe_allow_html=True)
        mins_po = d_po["minute"].dropna()
        c3.markdown(_carte_stat("Minute moyenne",
                    f"{mins_po.mean():.0f}'" if len(mins_po) else "—",
                    "des buts PO", D1_OR), unsafe_allow_html=True)

        # Top buteurs graphique
        st.markdown("### Top buteurs PO")
        top = clt_po.head(12)
        noms = [nj(n) for n in top["joueur"]][::-1]
        vals = top["buts"].tolist()[::-1]
        couls = [COULEUR_EQUIPE.get(e, D1_ROUGE) for e in top["equipe"]][::-1]
        fig = go.Figure(go.Bar(x=vals, y=noms, orientation="h",
            marker_color=couls, text=vals, textposition="outside", textangle=0,
            textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
        fig.update_xaxes(showticklabels=False)
        st.plotly_chart(style_fig(fig, max(240, 32*len(top))), use_container_width=True)

        # Répartition par équipe
        st.markdown("### Répartition des buts par équipe")
        parq = d_po["equipe_marque"].value_counts()
        st.plotly_chart(barh_equipes(parq.index.tolist(), parq.values.tolist(),
                        h=max(180, 38*len(parq))), use_container_width=True)

        # Classement détaillé
        st.markdown("### Classement détaillé")
        for i, row in clt_po.head(20).iterrows():
            coul = COULEUR_EQUIPE.get(row["equipe"], D1_ROUGE)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:.7rem;'
                f'background:{D1_CARTE};border-left:3px solid {coul};'
                f'border-radius:6px;padding:.5rem .8rem;margin:.25rem 0">'
                f'<span style="color:{D1_GRIS};width:1.5rem">{i+1}.</span>'
                f'<span style="flex:1;color:{D1_BLANC};font-weight:500">{row["joueur"]}</span>'
                f'<span style="color:{D1_GRIS};font-size:.85rem">{nc(row["equipe"])}</span>'
                f'<span style="color:{coul};font-weight:700;font-size:1.1rem;min-width:2rem;'
                f'text-align:right">{row["buts"]}</span>'
                f'</div>',
                unsafe_allow_html=True)

        # Comparaison saison régulière / PO
        st.markdown("### Saison régulière vs Phase finale")
        cmp = []
        for j in clt_po["joueur"]:
            reg = int((df["joueur"] == j).sum())
            po = int((d_po["joueur"] == j).sum())
            cmp.append({"Buteur": j, "Saison régulière": reg, "Phase finale": po,
                        "Total": reg + po})
        cmp_df = pd.DataFrame(cmp).sort_values("Phase finale", ascending=False)
        st.dataframe(cmp_df, use_container_width=True, hide_index=True)


elif page == "Origines PO":
    st.title("Origines des buts — Phase finale")
    if df_po.empty:
        st.info("Aucun but de phase finale enregistré.")
    else:
        ren = df_po["origine"].notna().sum()
        total = len(df_po)
        st.markdown(f"<p class='note'>{ren}/{total} buts avec origine renseignée "
                    f"({ren/total*100:.0f}%).</p>", unsafe_allow_html=True)

        if ren == 0:
            st.info("Aucune origine encore renseignée pour la phase finale.")
        else:
            # Répartition globale
            st.markdown("### Répartition globale en phase finale")
            rep_po = df_po["origine"].dropna().value_counts()
            fig = go.Figure(go.Bar(x=rep_po.values, y=rep_po.index, orientation="h",
                marker_color=D1_ROUGE,
                text=[f"{v} ({v/ren*100:.0f}%)" for v in rep_po.values],
                textposition="outside", textangle=0,
                textfont=dict(size=13, color=D1_BLANC), cliponaxis=False))
            fig.update_xaxes(showticklabels=False); fig.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig, max(280, 36*len(rep_po))), use_container_width=True)

            # Comparaison avec saison régulière
            st.markdown("### Comparaison avec la saison régulière")
            rep_reg = df["origine"].dropna().value_counts()
            ren_reg = rep_reg.sum()
            all_o = sorted(set(rep_po.index) | set(rep_reg.index))
            cmp = pd.DataFrame([
                {"Origine": o,
                 "Saison régulière": int(rep_reg.get(o, 0)),
                 "Saison %": f"{rep_reg.get(o,0)/ren_reg*100:.1f}%" if ren_reg else "—",
                 "Phase finale": int(rep_po.get(o, 0)),
                 "PO %": f"{rep_po.get(o,0)/ren*100:.1f}%" if ren else "—"}
                for o in all_o
            ]).sort_values("Phase finale", ascending=False)
            st.dataframe(cmp, use_container_width=True, hide_index=True)

            # Origines par équipe (en PO)
            st.markdown("### Origines par équipe (phase finale)")
            with_orig = df_po[df_po["origine"].notna()]
            eqs_po = sorted(with_orig["equipe_marque"].unique())
            for eq in eqs_po:
                sub = with_orig[with_orig["equipe_marque"] == eq]
                rep_eq = sub["origine"].value_counts()
                coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
                with st.expander(f"{nc(eq)} — {len(sub)} buts avec origine"):
                    fig_eq = go.Figure(go.Bar(x=rep_eq.values, y=rep_eq.index,
                        orientation="h", marker_color=coul,
                        text=rep_eq.values, textposition="outside", textangle=0,
                        textfont=dict(size=12, color=D1_BLANC), cliponaxis=False))
                    fig_eq.update_xaxes(showticklabels=False)
                    fig_eq.update_yaxes(autorange="reversed")
                    st.plotly_chart(style_fig(fig_eq, max(180, 34*len(rep_eq))),
                                    use_container_width=True)


elif page == "Méthodo & Couverture":
    st.title("Méthodo & Couverture des données")

    st.markdown("### Origines des buts")
    origines_expl = {
        "Attaque placée":       "Possession organisée, l'équipe contrôle le ballon face à une défense en place. But sur phase offensive construite.",
        "Transition offensive":  "Récupération du ballon et attaque rapide avant que la défense adverse se replace.",
        "Attaque rapide":        "Accélération du jeu sans prise de risque excessive, entre l'attaque placée et la transition.",
        "Touche offensive":      "Remise en jeu côté offensif (dans la moitié de terrain adverse) transformée en but.",
        "Touche défensive":      "Remise en jeu côté défensif récupérée et convertie rapidement.",
        "Corner":                "Coup de pied de coin direct ou phase combinée suite à un corner.",
        "Coup franc":            "Coup franc direct ou indirect transformé en but.",
        "Jet franc (10m)":       "Situation de pénalité à 10 mètres accordée après 5 fautes cumulées.",
        "Penalty":               "Faute dans la surface, tir direct au but.",
        "Power play":            "Avantage numérique — l'équipe joue avec un joueur de champ de plus (gardien sorti par l'adversaire).",
        "Non identifié (?)":     "Vidéo de la séquence indisponible au moment de l'analyse. Origine non identifiable.",
    }
    for orig, expl in origines_expl.items():
        st.markdown(
            f'<div style="background:{D1_CARTE};border-left:3px solid {D1_ROUGE};'
            f'border-radius:8px;padding:.5rem .9rem;margin:.3rem 0">'
            f'<b style="color:{D1_BLANC}">{orig}</b><br>'
            f'<span style="color:{D1_GRIS};font-size:.85rem">{expl}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### Situations de score")
    situations = {
        "Menant":   ("vert", D1_VERT,  "L'équipe qui marque ce but était déjà en tête au moment du tir."),
        "Égalité":  ("or",   D1_OR,    "Le score était à égalité juste avant ce but."),
        "Est mené": ("rouge",D1_ROUGE, "L'équipe qui marque ce but était en retard au tableau d'affichage."),
    }
    for sit, (_, coul_s, expl) in situations.items():
        st.markdown(
            f'<div style="background:{D1_CARTE};border-left:3px solid {coul_s};'
            f'border-radius:8px;padding:.5rem .9rem;margin:.3rem 0">'
            f'<b style="color:{coul_s}">{sit}</b><br>'
            f'<span style="color:{D1_GRIS};font-size:.85rem">{expl}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### Indicateurs tactiques")
    indicateurs = {
        "Impact du 1er but":
            "Pour chaque match, on identifie l'équipe qui a marqué en premier. On calcule ensuite le taux de victoire de l'équipe analysée selon qu'elle ait marqué ou encaissé le premier but.",
        "Momentum (Marque → Marque, etc.)":
            "Pour chaque match, on calcule le temps en minutes entre deux buts consécutifs. On classe chaque paire selon le contexte (Marque→Marque = l'équipe marque deux fois d'affilée). La valeur affichée est la moyenne sur tous les matchs.",
        "Retours au score":
            "Pour chaque match, on parcourt la chronologie but par but. Si le score de l'équipe passe en dessous de celui de l'adversaire, le match est classé 'menée'. Le résultat final détermine si l'équipe a retourné la situation (Victoire ou Nul) ou non (Défaite).",
        "Retournements (menés à la mi-temps)":
            "On calcule le score à l'issue de la 1re période uniquement. Si l'équipe était derrière à la mi-temps, on regarde si elle a obtenu un résultat positif (Victoire ou Nul) sur l'ensemble du match.",
        "Impact du but rapide (1-3')":
            "On identifie les matchs où l'équipe a marqué dans les 3 premières minutes. On compare le taux de victoire dans ces matchs vs les matchs sans but rapide.",
        "Buts clutch (36'-40')":
            "Tout but marqué entre la 36e et la 40e minute (fin de match). Indicateur de la résistance physique et mentale en fin de rencontre.",
        "Régularité offensive (écart-type)":
            "On calcule le nombre de buts marqués par match pour chaque journée. L'écart-type mesure la dispersion : un écart-type de 0 = même nombre de buts à chaque match ; un écart-type élevé = grande variabilité.",
        "Concentration offensive":
            "Part des buts de l'équipe marqués par le(s) meilleur(s) buteur(s). Une concentration élevée indique une dépendance forte à un ou deux joueurs.",
        "Bilan vs Top 6":
            "Résultats contre les 6 équipes ayant le plus de points au classement général (l'équipe analysée exclue).",
    }
    for ind, expl in indicateurs.items():
        st.markdown(
            f'<div style="background:{D1_CARTE};border-left:3px solid {D1_OR};'
            f'border-radius:8px;padding:.5rem .9rem;margin:.3rem 0">'
            f'<b style="color:{D1_BLANC}">{ind}</b><br>'
            f'<span style="color:{D1_GRIS};font-size:.85rem">{expl}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
