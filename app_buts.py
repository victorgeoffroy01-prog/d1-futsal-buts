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
LOGO_D1   = Path("D1_Futsal_logo.png")
LOGOS_DIR = Path("logos")

D1_ROUGE       = "#C00018"
D1_ROUGE_CLAIR = "#E11030"
D1_BORDEAUX    = "#540C18"
D1_BORDEAUX_2  = "#6C1420"
D1_ANTHRACITE  = "#1A1A1E"
D1_CARTE       = "#26181C"
D1_BLANC       = "#F5F2F3"
D1_GRIS        = "#9A8E91"
D1_OR          = "#C9A24B"
D1_VERT        = "#27AE60"
D1_BLEU        = "#3A7BD5"

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
[data-testid="stSidebar"]{{background:{D1_BORDEAUX};border-right:1px solid {D1_BORDEAUX_2};
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
.stDataFrame{{border-radius:10px;overflow:hidden}}
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
.fr{{display:inline-block;width:17px;height:17px;border-radius:50%;
    font-size:.62rem;font-weight:700;text-align:center;line-height:17px;margin:1px}}
.fr-V{{background:{D1_VERT};color:white}}
.fr-N{{background:{D1_OR};color:#1a1a1e}}
.fr-D{{background:{D1_ROUGE};color:white}}
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
    if not Path(DB_PATH).exists():
        return None
    return pd.read_sql_query("SELECT * FROM but", sqlite3.connect(DB_PATH))

df = charger()
if df is None:
    st.error("Base `futsal_d1.db` introuvable. Lance d'abord : python migration_buts.py")
    st.stop()

EQUIPES   = sorted(df["equipe_marque"].dropna().unique().tolist())
JOURNEES  = sorted(df["journee"].dropna().unique().tolist())
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

def nj(nom, court=False):
    """Nom de famille en priorité (dernier mot) pour graphes."""
    parts = nom.strip().split()
    if len(parts) <= 1:
        return nom
    return parts[-1]  # Nom de famille = dernier token

def njs(liste):
    return [nj(n) for n in liste]

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
    return pd.DataFrame(rows).sort_values("Pts",ascending=False).reset_index(drop=True)

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
    buts = df_match.sort_values(["periode","minute"])
    sd, se = 0, 0
    evts = []
    for _, b in buts.iterrows():
        if b["equipe_marque"]==dom: sd+=1
        else: se+=1
        evts.append({"minute":int(b["minute"]),"periode":int(b["periode"]),
                     "equipe":b["equipe_marque"],"joueur":b["joueur"],
                     "score_dom":sd,"score_ext":se,
                     "origine":b["origine"] if pd.notna(b["origine"]) else "—"})
    return evts

# ============================================================================
# SIDEBAR — navigation par catégories
# ============================================================================
NAV = {
    "VUE D'ENSEMBLE": [("🏠", "Accueil"), ("🏆", "Classement")],
    "ÉQUIPES":        [("🛡", "Fiche équipe"), ("⚔", "Confrontations")],
    "JOUEURS":        [("👟", "Buteurs")],
    "MATCHS":         [("⚽", "Fiche match")],
    "ANALYSE":        [("⏱", "Profil temporel"), ("📊", "Dynamique de score"),
                       ("📈", "Analyse avancée")],
    "RAPPORT":        [("📋", "Rapport équipe")],
    "AIDE":           [("📖", "Lexique")],
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

page = st.session_state.page

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
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4ECEE")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9C7CB")),
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
    d.add(Rect(0,0,w,height,fillColor=colors.HexColor("#F0E8EA"),strokeColor=None))
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
    elems.append(_pdf_section("⚽ Buteurs dangereux", stl))
    bb = dpour["joueur"].value_counts().head(8)
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
        rouge_flag = " ← TRANCHE VULNÉRABLE" if tr==best_tr else ""
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
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4ECEE")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9C7CB")),
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
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4ECEE")]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9C7CB")),
            ("ALIGN",(1,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ]))
        elems.append(t_prog)
    elems.append(Spacer(1,8))

    # Adversaires favoris
    elems.append(_pdf_section("🎯 Adversaires favoris", stl))
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
    elems.append(_pdf_stat_row(f"Buteurs {dom.split()[0]}", buts_dom_df["joueur"].nunique()))
    elems.append(_pdf_stat_row(f"Buteurs {ext.split()[0]}", buts_ext_df["joueur"].nunique()))
    elems.append(Spacer(1,8))

    # Chronologie
    elems.append(_pdf_section("⏱ Chronologie des buts", stl))
    data_chr = [["Per.", "Min", "Buteur", "Équipe", "Score"]]
    for e in events:
        data_chr.append([
            f"P{e['periode']}", f"{e['minute']}'", e["joueur"],
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
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4ECEE")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9C7CB")),
        ("ALIGN",(0,0),(1,-1),"CENTER"),("ALIGN",(4,0),(4,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]+coul_rows))
    elems.append(t_chr)

    doc.build(elems); buf.seek(0)
    return buf


def bloc_export(pdf_buffer, nom_fichier, label="Exporter en PDF", csv_df=None, csv_nom=None):
    """Bloc d'export uniforme placé en bas de page."""
    st.markdown("<hr style='border:none;border-top:1px solid #6C1420;margin:1.2rem 0 .6rem 0'>",
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
if page == "Accueil":
    st.title("D1 Futsal — Vue d'ensemble")
    matchs = construire_matchs()
    nb_matchs = len(matchs)
    moy = len(df)/nb_matchs if nb_matchs else 0
    top_but = df["joueur"].value_counts()
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
        vals2 = df["equipe_encaisse"].value_counts()
        # même couleur d'équipe (pas de transparence différente)
        st.plotly_chart(barh_equipes(vals2.index.tolist(), vals2.values,
                                     h=max(300,30*len(vals2))), use_container_width=True)

    st.markdown("### Répartition 1re / 2e période")
    p1 = int((df["periode"]==1).sum()); p2 = int((df["periode"]==2).sum())
    fig2 = go.Figure(go.Bar(
        x=["1re période","2e période"], y=[p1,p2],
        marker_color=[D1_ROUGE, D1_BORDEAUX_2],
        text=[f"{p1}  ({p1/(p1+p2)*100:.0f}%)", f"{p2}  ({p2/(p1+p2)*100:.0f}%)"],
        textposition="outside", textangle=0, width=[0.4,0.4]
    ))
    fig2.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig2, 250), use_container_width=True)

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
    fig_de.update_layout(barmode="group", bargap=0.2, bargroupgap=0.08)
    fig_de.update_yaxes(showticklabels=False, range=[0,120],
                        title=dict(text="% de victoires", font=dict(size=12, color=D1_GRIS)))
    st.plotly_chart(style_fig(fig_de, 340, "% de victoires — Domicile vs Extérieur par équipe"),
                    use_container_width=True)
    st.markdown("<p class='note'>Barre pleine = domicile · Barre semi-transparente = extérieur</p>",
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
    st.plotly_chart(style_fig(fig_hm, max(360, 32*len(ordre))), use_container_width=True)
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
        return pd.DataFrame(rows).sort_values("Pts",ascending=False).reset_index(drop=True)

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
        diff_color = D1_VERT if diff>0 else(D1_ROUGE if diff<0 else D1_GRIS)
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
    # On utilise les minutes directement (déjà absolues 1-40)
    xs  = [0] + [e["minute"] for e in events] + [40]
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
            f'<span style="color:{D1_GRIS};font-size:.76rem"> {per} {e["minute"]}\' </span>'
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
    c5.metric("Buteurs dom.",buts_dom["joueur"].nunique()); c6.metric("Buteurs ext.",buts_ext["joueur"].nunique())
    cg,cd = st.columns(2)
    with cg:
        st.markdown(f"**{dom.split()[0]}**")
        for j,n in buts_dom["joueur"].value_counts().items(): st.markdown(f'{"⚽"*n} **{j}** ({n})')
    with cd:
        st.markdown(f"**{ext.split()[0]}**")
        for j,n in buts_ext["joueur"].value_counts().items(): st.markdown(f'{"⚽"*n} **{j}** ({n})')

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
        st.markdown("### Adversaires favoris")
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

    bloc_export(pdf_buteur(j), f"buteur_{j.replace(' ','_')}.pdf",
                f"Exporter la fiche de {j.split()[0]}")

# ============================================================================
# PAGE — PROFIL TEMPOREL
# ============================================================================
elif page == "Profil temporel":
    st.title("Profil temporel des buts")
    eq=st.selectbox("Périmètre",["Tout le championnat"]+EQUIPES)
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
                         marker_color=coul_b,textangle=0))
    # Mi-temps : ligne verticale entre 20' et 21' (index 19 et 20)
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
    fig2=go.Figure(go.Bar(x=tr.index.astype(str),y=tr.values,
                          marker_color=coul_q,text=tr.values,textposition="outside",textangle=0))
    fig2.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig2,260),use_container_width=True)

# ============================================================================
# PAGE — DYNAMIQUE DE SCORE
# ============================================================================
elif page == "Dynamique de score":
    st.title("Dynamique de score")
    st.markdown("<p class='note'>Situation de l'équipe qui marque, juste avant son but.</p>",unsafe_allow_html=True)
    eq=st.selectbox("Périmètre",["Tout le championnat"]+EQUIPES)
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
    fig=go.Figure(go.Bar(x=ordre,y=sit.values,
                         marker_color=[coul_sit[s] for s in ordre],
                         text=[f"{v}  ({v/tot*100:.0f}%)" for v in sit.values],
                         textposition="outside",textangle=0,width=[0.4,0.4,0.4]))
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig,260),use_container_width=True)
    if eq=="Tout le championnat":
        st.markdown("### Comparaison par équipe — buts selon situation de score")
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
            fig_m=go.Figure(go.Bar(x=s["pct_mené"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_ROUGE,text=[f"{v:.0f}%" for v in s["pct_mené"]],
                                   textposition="outside",textangle=0,
                                   textfont=dict(size=13,color="#F5F2F3"),cliponaxis=False))
            fig_m.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_m,max(280,28*len(s))),use_container_width=True)
        with c2:
            st.markdown("#### À égalité")
            s=comp.sort_values("pct_egal",ascending=False)
            fig_e=go.Figure(go.Bar(x=s["pct_egal"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_OR,text=[f"{v:.0f}%" for v in s["pct_egal"]],
                                   textposition="outside",textangle=0,
                                   textfont=dict(size=13,color="#F5F2F3"),cliponaxis=False))
            fig_e.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_e,max(280,28*len(s))),use_container_width=True)
        with c3:
            st.markdown("#### En menant")
            s=comp.sort_values("pct_men",ascending=False)
            fig_v=go.Figure(go.Bar(x=s["pct_men"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_VERT,text=[f"{v:.0f}%" for v in s["pct_men"]],
                                   textposition="outside",textangle=0,
                                   textfont=dict(size=13,color="#F5F2F3"),cliponaxis=False))
            fig_v.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_v,max(280,28*len(s))),use_container_width=True)

# ============================================================================
# PAGE — VUE ÉQUIPE
# ============================================================================
# PAGE Vue équipe → fusionnée dans Fiche équipe
# PAGE Tactique/Origines → fusionnée dans Fiche équipe
elif page == "Confrontations":
    st.title("Confrontations directes")
    c1,c2=st.columns(2)
    e1=c1.selectbox("Équipe A",EQUIPES,index=0)
    e2=c2.selectbox("Équipe B",EQUIPES,index=1 if len(EQUIPES)>1 else 0)
    if e1==e2: st.warning("Choisis deux équipes différentes."); st.stop()
    masque=(((df["equipe_marque"]==e1)&(df["equipe_encaisse"]==e2))|
            ((df["equipe_marque"]==e2)&(df["equipe_encaisse"]==e1)))
    d=df[masque]
    if d.empty: st.info("Aucun but recensé entre ces deux équipes."); st.stop()
    matchs=construire_matchs()
    mh2h=matchs[((matchs["dom"]==e1)&(matchs["ext"]==e2))|
                ((matchs["dom"]==e2)&(matchs["ext"]==e1))]
    b1=int((d["equipe_marque"]==e1).sum()); b2=int((d["equipe_marque"]==e2).sum())
    v1=(int(((mh2h["dom"]==e1)&(mh2h["res_dom"]=="V")).sum())+
        int(((mh2h["ext"]==e1)&(mh2h["res_ext"]=="V")).sum()))
    v2=(int(((mh2h["dom"]==e2)&(mh2h["res_dom"]=="V")).sum())+
        int(((mh2h["ext"]==e2)&(mh2h["res_ext"]=="V")).sum()))
    nb_nuls=len(mh2h)-v1-v2
    coul1=COULEUR_EQUIPE.get(e1,D1_ROUGE); coul2=COULEUR_EQUIPE.get(e2,D1_BLEU)
    lg1=logo_b64(e1,44); lg2=logo_b64(e2,44)
    tot_b=b1+b2 or 1
    pct1=b1/tot_b*100; pct2=b2/tot_b*100
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:13px;padding:1.1rem;margin-bottom:.8rem">'
        f'<div style="display:flex;align-items:center;justify-content:space-between">'
        f'<div style="flex:1;text-align:center">{lg1}<br><b style="font-size:.88rem">{e1.split()[0]}</b>'
        f'<div style="color:{coul1};font-size:1.9rem;font-weight:900;margin:.2rem 0">{b1}</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem">{v1} victoire{"s" if v1!=1 else ""}</div>'
        f'</div>'
        f'<div style="text-align:center;padding:0 1.2rem">'
        f'<div style="color:{D1_GRIS};font-size:.75rem;margin-bottom:.25rem">{len(mh2h)} rencontre{"s" if len(mh2h)!=1 else ""}</div>'
        f'<div style="font-size:1.2rem;font-weight:700;color:{D1_GRIS}">VS</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem;margin-top:.25rem">{nb_nuls} nul{"s" if nb_nuls!=1 else ""}</div>'
        f'</div>'
        f'<div style="flex:1;text-align:center">{lg2}<br><b style="font-size:.88rem">{e2.split()[0]}</b>'
        f'<div style="color:{coul2};font-size:1.9rem;font-weight:900;margin:.2rem 0">{b2}</div>'
        f'<div style="color:{D1_GRIS};font-size:.75rem">{v2} victoire{"s" if v2!=1 else ""}</div>'
        f'</div></div>'
        f'<div style="margin-top:.8rem">'
        f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden">'
        f'<div style="width:{pct1:.1f}%;background:{coul1}"></div>'
        f'<div style="width:{pct2:.1f}%;background:{coul2}"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.74rem;color:{D1_GRIS};margin-top:.15rem">'
        f'<span>{pct1:.0f}% des buts</span><span>{pct2:.0f}% des buts</span></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    if len(mh2h):
        st.markdown("### Résultats")
        for _,m in mh2h.sort_values("journee").iterrows():
            bc_dom=D1_VERT if m["res_dom"]=="V" else(D1_OR if m["res_dom"]=="N" else D1_ROUGE)
            bc_ext=D1_VERT if m["res_dom"]=="D" else(D1_OR if m["res_dom"]=="N" else D1_ROUGE)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:1rem;padding:.28rem .6rem;'
                f'background:{D1_CARTE};border-radius:7px;margin:.15rem 0;font-size:.86rem">'
                f'<span style="color:{D1_GRIS};width:45px">J{int(m["journee"])}</span>'
                f'<span style="flex:1;text-align:right;font-weight:600">{m["dom"]}</span>'
                f'<span style="font-weight:800;padding:0 .7rem">'
                f'<span style="color:{bc_dom}">{m["score_dom"]}</span>'
                f'<span style="color:{D1_GRIS}"> — </span>'
                f'<span style="color:{bc_ext}">{m["score_ext"]}</span>'
                f'</span>'
                f'<span style="flex:1;font-weight:600">{m["ext"]}</span>'
                f'</div>', unsafe_allow_html=True)
    st.markdown("### Détail des buts")
    det=(d.sort_values(["journee","periode","minute"])
         [["journee","equipe_marque","joueur","periode","minute","situation","origine"]]
         .rename(columns={"journee":"J","equipe_marque":"Marque","joueur":"Buteur",
                          "periode":"Pér.","minute":"Min","situation":"Situation","origine":"Origine"}))
    det["Origine"]=det["Origine"].fillna("—")
    st.dataframe(det,use_container_width=True,height=320)
    dl_csv(det,"⬇ CSV",f"h2h_{e1[:6]}_{e2[:6]}.csv")

# ============================================================================
# PAGE — SCOUTING ADVERSE
# ============================================================================
# PAGE Scouting → fusionnée dans Fiche équipe
elif page == "Analyse avancée":
    st.title("Analyse avancée")

    matchs = construire_matchs()

    # ---- RÉGULARITÉ OFFENSIVE ----
    st.markdown("### Régularité offensive")
    st.markdown("<p class='note'>Moyenne de buts par match, et indice de régularité "
                "(plus l'écart-type est bas, plus l'équipe est constante d'un match à l'autre).</p>",
                unsafe_allow_html=True)
    rows_reg = []
    for eq in EQUIPES:
        meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
        bpm = []
        for _,m in meq.iterrows():
            dm = df[(df["journee"]==m["journee"])&
                    (df["equipe_domicile"]==m["dom"])&
                    (df["equipe_exterieure"]==m["ext"])]
            bpm.append(int((dm["equipe_marque"]==eq).sum()))
        if bpm:
            rows_reg.append({"equipe":eq,"moy":pd.Series(bpm).mean(),
                             "std":pd.Series(bpm).std(ddof=0),"min":min(bpm),"max":max(bpm)})
    reg = pd.DataFrame(rows_reg).sort_values("moy",ascending=False)

    cg_r, cd_r = st.columns(2)
    with cg_r:
        st.markdown("#### Moyenne de buts par match")
        fig_moy = go.Figure()
        for _,r in reg.iterrows():
            coul = COULEUR_EQUIPE.get(r["equipe"], D1_ROUGE)
            fig_moy.add_trace(go.Bar(
                x=[round(r["moy"],1)], y=[r["equipe"]], orientation="h",
                marker_color=coul, text=[f'{r["moy"]:.1f}'],
                textposition="auto", textangle=0, showlegend=False,
                hovertemplate=f'{r["equipe"]}<br>Moyenne : {r["moy"]:.1f} buts/match<br>'
                              f'Mini : {r["min"]} · Maxi : {r["max"]}<extra></extra>'
            ))
        fig_moy.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_moy, max(320,30*len(reg))), use_container_width=True)
    with cd_r:
        st.markdown("#### Régularité (écart-type, plus bas = plus constant)")
        reg_s = reg.sort_values("std")
        fig_std = go.Figure()
        for _,r in reg_s.iterrows():
            # vert si régulier (std bas), rouge si irrégulier (std haut)
            ratio = (r["std"]-reg_s["std"].min())/((reg_s["std"].max()-reg_s["std"].min()) or 1)
            coul = D1_VERT if ratio<0.4 else(D1_OR if ratio<0.7 else D1_ROUGE)
            fig_std.add_trace(go.Bar(
                x=[round(r["std"],1)], y=[r["equipe"]], orientation="h",
                marker_color=coul, text=[f'± {r["std"]:.1f}'],
                textposition="auto", textangle=0, showlegend=False,
                hovertemplate=f'{r["equipe"]}<br>Écart-type : {r["std"]:.1f}<extra></extra>'
            ))
        fig_std.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_std, max(320,30*len(reg_s))), use_container_width=True)
    st.markdown("<p class='note'>🟢 régulier · 🟡 moyen · 🔴 irrégulier — survole une barre pour le détail mini/maxi.</p>",
                unsafe_allow_html=True)

    st.markdown("---")

    # ---- MOMENTUM DÉBUT / FIN DE PÉRIODE ----
    st.markdown("### Momentum : buts selon le moment de la période")
    eq_sel = st.selectbox("Équipe (ou tout le championnat)", ["Tout le championnat"]+EQUIPES,
                          key="momentum_sel")
    d_mom = df if eq_sel=="Tout le championnat" else df[df["equipe_marque"]==eq_sel]

    # Tranches : début P1 (1-5), milieu P1 (6-15), fin P1 (16-20)
    #            début P2 (21-25), milieu P2 (26-35), fin P2 (36-40)
    def tranche_moment(row):
        m = row["minute"]; p = row["periode"]
        if p==1:
            if m<=5:  return "Début P1 (1-5')"
            elif m<=15: return "Milieu P1 (6-15')"
            else:       return "Fin P1 (16-20')"
        else:
            if m<=25: return "Début P2 (21-25')"
            elif m<=35: return "Milieu P2 (26-35')"
            else:       return "Fin P2 (36-40')"

    d_mom2 = d_mom.copy()
    d_mom2["moment"] = d_mom2.apply(tranche_moment, axis=1)
    ordre_mom = ["Début P1 (1-5')","Milieu P1 (6-15')","Fin P1 (16-20')",
                 "Début P2 (21-25')","Milieu P2 (26-35')","Fin P2 (36-40')"]
    mom_cnt = d_mom2["moment"].value_counts().reindex(ordre_mom, fill_value=0)
    coul_mom = [D1_ROUGE]*3 + [D1_BORDEAUX_2]*3
    fig_mom = go.Figure(go.Bar(
        x=ordre_mom, y=mom_cnt.values,
        marker_color=coul_mom, text=mom_cnt.values,
        textposition="outside", textangle=0
    ))
    fig_mom.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig_mom, 280), use_container_width=True)
    # Identifier le moment le plus productif
    best = mom_cnt.idxmax()
    st.markdown(f"<p class='note'>Moment le plus productif : <b>{best}</b> ({int(mom_cnt.max())} buts)</p>",
                unsafe_allow_html=True)

    st.markdown("---")

    # ---- CONCENTRATION OFFENSIVE ----
    st.markdown("### Concentration offensive — dépendance aux buteurs clés")
    rows_conc = []
    for eq in EQUIPES:
        dp = df[df["equipe_marque"]==eq]
        if len(dp)==0: continue
        bb = dp["joueur"].value_counts()
        rows_conc.append({
            "equipe":eq,
            "top1_pct": bb.iloc[0]/len(dp)*100,
            "top3_pct": bb.head(3).sum()/len(dp)*100,
            "nb_buteurs": len(bb),
        })
    conc = pd.DataFrame(rows_conc).sort_values("top3_pct", ascending=False)

    cg, cd = st.columns(2)
    with cg:
        st.markdown("#### Part du top buteur dans les buts de l'équipe")
        fig_c1 = go.Figure()
        for _,r in conc.sort_values("top1_pct",ascending=False).iterrows():
            c = COULEUR_EQUIPE.get(r["equipe"], D1_ROUGE)
            fig_c1.add_trace(go.Bar(x=[r["top1_pct"]], y=[nc(r["equipe"])], orientation="h",
                                    marker_color=c, text=[f'{r["top1_pct"]:.0f}%'],
                                    textposition="outside", textangle=0, showlegend=False,
                                    textfont=dict(size=13,color="#F5F2F3"),cliponaxis=False))
        fig_c1.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_c1, max(280,28*len(conc))), use_container_width=True)
    with cd:
        st.markdown("#### Nombre de buteurs différents utilisés")
        fig_c2 = go.Figure()
        for _,r in conc.sort_values("nb_buteurs",ascending=False).iterrows():
            c = COULEUR_EQUIPE.get(r["equipe"], D1_ROUGE)
            fig_c2.add_trace(go.Bar(x=[r["nb_buteurs"]], y=[nc(r["equipe"])], orientation="h",
                                    marker_color=c, text=[int(r["nb_buteurs"])],
                                    textposition="outside", textangle=0, showlegend=False,
                                    textfont=dict(size=13,color="#F5F2F3"),cliponaxis=False))
        fig_c2.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_c2, max(280,28*len(conc))), use_container_width=True)

    st.markdown("---")

    # ---- RADAR COMPARATIF ----
    st.markdown("### Radar comparatif — profil d'équipe")
    st.markdown("<p class='note'>Sélectionne 2 à 4 équipes à comparer.</p>", unsafe_allow_html=True)
    eq_radar = st.multiselect("Équipes", EQUIPES, default=EQUIPES[:3], max_selections=4)

    if len(eq_radar) >= 2:
        indicateurs = ["Buts/match","Efficacité P2 (%)","Buts en menant (%)","Collectif (nb buteurs)","Solidité déf."]

        def radar_vals(eq):
            dp = df[df["equipe_marque"]==eq]
            dc = df[df["equipe_encaisse"]==eq]
            meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
            nm = len(meq) or 1
            bpm = len(dp)/nm
            p2_eff = (dp["periode"]==2).mean()*100 if len(dp) else 0
            men_pct = ((dp["situation"]=="Menant").sum()/len(dp)*100) if len(dp) else 0
            nb_but = float(dp["joueur"].nunique())
            solidite = max(0, 10 - len(dc)/nm)  # plus on encaisse peu, plus c'est élevé
            return [bpm, p2_eff, men_pct, nb_but, solidite]

        # Normaliser 0-100 pour le radar
        all_vals = {eq: radar_vals(eq) for eq in eq_radar}
        all_matrix = pd.DataFrame(all_vals, index=indicateurs)
        norm = all_matrix.copy()
        for idx in indicateurs:
            mn = all_matrix.loc[idx].min(); mx = all_matrix.loc[idx].max()
            if mx != mn:
                norm.loc[idx] = (all_matrix.loc[idx] - mn) / (mx - mn) * 100
            else:
                norm.loc[idx] = 50

        fig_radar = go.Figure()
        for eq in eq_radar:
            vals = norm[eq].tolist()
            vals += [vals[0]]  # fermer le polygone
            cats = indicateurs + [indicateurs[0]]
            coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=cats, name=eq.split()[0],
                line=dict(color=coul, width=2.5),
                fill="toself", fillcolor=hex_to_rgba(coul, 0.12),
            ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0,100],
                                gridcolor="rgba(255,255,255,.1)", tickfont=dict(size=9)),
                angularaxis=dict(gridcolor="rgba(255,255,255,.1)")
            )
        )
        st.plotly_chart(style_fig(fig_radar, 460), use_container_width=True)
        st.markdown("<p class='note'>Valeurs normalisées 0-100 entre les équipes sélectionnées. "
                    "Solidité déf. = inversement proportionnelle aux buts encaissés/match.</p>",
                    unsafe_allow_html=True)

    st.markdown("---")

    # ---- HEATMAP MINUTE × ÉQUIPE ----
    st.markdown("### Heatmap — quand chaque équipe marque (minutes)")
    st.markdown("<p class='note'>Intensité = nombre de buts marqués à cette minute sur toute la saison. "
                "Repère les équipes qui marquent tôt, tard, ou de façon régulière.</p>",
                unsafe_allow_html=True)

    eq_hm = st.multiselect("Équipes (laisser vide = toutes)", EQUIPES,
                            default=[], key="hm_eq")
    equipes_hm = eq_hm if eq_hm else EQUIPES

    clt_hm = construire_classement()
    ordre_hm = [e for e in clt_hm["equipe"].tolist() if e in equipes_hm]

    pivot_hm2 = (df[df["equipe_marque"].isin(equipes_hm)]
                 .groupby(["equipe_marque","minute"]).size()
                 .reset_index(name="buts")
                 .pivot(index="equipe_marque",columns="minute",values="buts")
                 .reindex(ordre_hm)
                 .reindex(columns=range(1,41), fill_value=0)
                 .fillna(0))

    fig_hm2 = go.Figure(go.Heatmap(
        z=pivot_hm2.values,
        x=[f"{m}'" for m in range(1,41)],
        y=[nc(e) for e in pivot_hm2.index],
        colorscale=[[0,"rgba(38,24,28,1)"],[0.4,"rgba(140,10,24,0.7)"],[1,D1_ROUGE]],
        text=[[str(int(v)) if v>0 else "" for v in row] for row in pivot_hm2.values],
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z} buts<extra></extra>",
        showscale=True,
        colorbar=dict(len=0.8, thickness=12, tickfont=dict(size=10))
    ))
    # Ligne mi-temps
    fig_hm2.add_vline(x="20'", line_dash="dot", line_color=D1_GRIS, line_width=1.5,
                      annotation_text="Mi-temps", annotation_font_color=D1_GRIS,
                      annotation_position="top")
    fig_hm2.update_xaxes(tickfont=dict(size=10),
                          tickvals=[f"{m}'" for m in [1,5,10,15,20,25,30,35,40]])
    fig_hm2.update_yaxes(tickfont=dict(size=11))
    st.plotly_chart(style_fig(fig_hm2, max(300, 38*len(ordre_hm))),
                    use_container_width=True)
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
        res[cle][r] += 1; res[cle]["total"] += 1
    return res

def analyser_dom_ext(eq):
    matchs = _get_matchs()
    dom_m = matchs[matchs["dom"]==eq]
    ext_m = matchs[matchs["ext"]==eq]
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
        goals = dm.sort_values(["periode","minute"])
        is_dom = (m["dom"]==eq)
        was_trailing = False; sd=0; se=0
        for _,b in goals.iterrows():
            if b["equipe_marque"]==m["dom"]: sd+=1
            else: se+=1
            seq = sd if is_dom else se
            saq = se if is_dom else sd
            if seq < saq: was_trailing=True; break
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
        goals = dm.sort_values(["periode","minute"])
        mins = goals["minute"].values; teams = goals["equipe_marque"].values
        for i in range(len(goals)-1):
            delta = max(1, int(mins[i+1])-int(mins[i]))
            t1="M" if teams[i]==eq else "E"
            t2="M" if teams[i+1]==eq else "E"
            trans[t1+t2].append(delta)
    labels={"MM":"Marque → Marque","ME":"Marque → Encaisse",
            "EM":"Encaisse → Marque","EE":"Encaisse → Encaisse"}
    return {labels[k]: (round(sum(v)/len(v)) if v else None) for k,v in trans.items()}

def analyser_bilan_top6(eq):
    matchs = _get_matchs()
    clt = construire_classement()
    top6 = [e for e in clt.head(6)["equipe"].tolist() if e != eq]
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
    """Carte métrique stylisée pour l'analyse tactique."""
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
# PDF RAPPORT COMPLET — style Laval (fond blanc, couleur équipe)
# ============================================================================
def pdf_rapport_complet(eq):
    """PDF complet avec fond blanc, structure identique au rapport Laval."""
    from reportlab.platypus import KeepTogether

    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              topMargin=1.5*cm, bottomMargin=1.5*cm,
                              leftMargin=1.8*cm, rightMargin=1.8*cm)

    # Couleurs
    coul_hex = COULEUR_EQUIPE.get(eq, D1_ROUGE)
    COUL     = colors.HexColor(coul_hex)
    BLANC    = colors.white
    GRIS     = colors.HexColor("#F7F4F5")
    BORD     = colors.HexColor("#E0D8DA")
    TEXTE    = colors.HexColor("#1A1A1E")
    TEXTE_G  = colors.HexColor("#6B6066")
    VERT_RL  = colors.HexColor(D1_VERT)
    OR_RL    = colors.HexColor(D1_OR)
    ROUGE_RL = colors.HexColor(D1_ROUGE)

    stl = getSampleStyleSheet()
    def ps(name, **kw):
        return ParagraphStyle(name, parent=stl["Normal"], **kw)

    titre_section = ps("tit_sec", textColor=BLANC, fontSize=11, fontName="Helvetica-Bold",
                        backColor=COUL, borderPadding=(6, 8, 6, 8), spaceBefore=14, spaceAfter=6)
    sous_titre    = ps("sous", textColor=COUL, fontSize=10, fontName="Helvetica-Bold",
                        spaceBefore=8, spaceAfter=3)
    corps         = ps("corps", textColor=TEXTE, fontSize=8.5, spaceBefore=1, spaceAfter=1)
    gris_stl      = ps("gr", textColor=TEXTE_G, fontSize=8, spaceBefore=1, spaceAfter=1)

    def sep():
        return HRFlowable(width="100%", thickness=0.6, color=BORD, spaceAfter=4, spaceBefore=2)

    def tbl_style_base():
        return [
            ("FONTSIZE", (0,0), (-1,-1), 8.5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("GRID", (0,0), (-1,-1), 0.4, BORD),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ]

    def header_row():
        return [
            ("BACKGROUND", (0,0), (-1,0), COUL),
            ("TEXTCOLOR", (0,0), (-1,0), BLANC),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]

    def zebra():
        return [("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, GRIS])]

    def mini_barre_h(val, max_val, w=5*cm, h=9, coul_fill=None):
        """Mini barre horizontale ReportLab."""
        cf = colors.HexColor(coul_fill) if coul_fill else COUL
        d = Drawing(w, h+2)
        d.add(Rect(0, 0, w, h, fillColor=colors.HexColor("#F0EDED"), strokeColor=None))
        if max_val > 0:
            d.add(Rect(0, 0, val/max_val*w, h, fillColor=cf, strokeColor=None))
        return d

    # ---- DONNÉES ----
    matchs   = _get_matchs()
    clt      = construire_classement()
    rang_row = clt[clt["equipe"]==eq].iloc[0]
    rang     = clt[clt["equipe"]==eq].index[0]+1
    dpour    = df[df["equipe_marque"]==eq]
    dcontre  = df[df["equipe_encaisse"]==eq]
    meq      = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    n_m      = len(meq) or 1
    j_max    = max(JOURNEES)
    pb       = analyser_premier_but(eq)
    de_stats = analyser_dom_ext(eq)
    rs_data  = analyser_retours_score(eq)
    mo_data  = analyser_momentum(eq)
    vt6, nt6, dt6 = analyser_bilan_top6(eq)
    tot_t6   = vt6+nt6+dt6
    vd, nd, dd = de_stats["dom"]; ve, ne_, de_ = de_stats["ext"]
    td = vd+nd+dd or 1; te = ve+ne_+de_ or 1

    elems = []

    # ---- HEADER ----
    logo_p = LOGOS_DIR / f"{eq}.png"
    header_data = [[
        Paragraph(f'<font size="20" color="{coul_hex}"><b>{eq}</b></font><br/>'
                  f'<font size="9" color="#6B6066">D1 Futsal · Saison 2025–2026 · J1→J{j_max}</font>',
                  ps("hdr", leading=22)),
        ""
    ]]
    if logo_p.exists():
        try:
            logo_img = RLImage(str(logo_p), width=2*cm, height=2*cm)
            header_data = [[
                Paragraph(f'<font size="20" color="{coul_hex}"><b>{eq}</b></font><br/>'
                          f'<font size="9" color="#6B6066">D1 Futsal · Saison 2025–2026 · J1→J{j_max}</font>',
                          ps("hdr", leading=22)),
                logo_img
            ]]
        except Exception:
            pass

    t_hdr = Table(header_data, colWidths=[13.5*cm, 3*cm])
    t_hdr.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("LINEBELOW", (0,0), (-1,0), 2, COUL),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elems += [t_hdr, Spacer(1, 8)]

    # ---- SECTION 01 : VUE D'ENSEMBLE ----
    elems.append(Paragraph("SECTION 01 — Vue d'ensemble", titre_section))

    # 4 KPIs
    tv = int(rang_row["V"])/n_m*100
    kpi_data = [
        [Paragraph(f'<font color="{coul_hex}"><b>POINTS</b></font>', corps),
         Paragraph(f'<font color="{coul_hex}"><b>BUTS MARQUÉS</b></font>', corps),
         Paragraph(f'<font color="{coul_hex}"><b>BUTS ENCAISSÉS</b></font>', corps),
         Paragraph(f'<font color="{coul_hex}"><b>TAUX DE VICTOIRE</b></font>', corps)],
        [Paragraph(f'<font size="22" color="{coul_hex}"><b>{int(rang_row["Pts"])}</b></font>', ps("kv",alignment=1)),
         Paragraph(f'<font size="22" color="{coul_hex}"><b>{int(rang_row["BP"])}</b></font>', ps("kv2",alignment=1)),
         Paragraph(f'<font size="22" color="{coul_hex}"><b>{int(rang_row["BC"])}</b></font>', ps("kv3",alignment=1)),
         Paragraph(f'<font size="22" color="{coul_hex}"><b>{tv:.0f}%</b></font>', ps("kv4",alignment=1))],
        [Paragraph(f'{int(rang_row["Pts"])/n_m:.1f} pts/match', gris_stl),
         Paragraph(f'{len(dpour)/n_m:.1f} buts/match', gris_stl),
         Paragraph(f'{len(dcontre)/n_m:.1f} buts/match', gris_stl),
         Paragraph(f'{int(rang_row["V"])}V · {int(rang_row["N"])}N · {int(rang_row["D"])}D', gris_stl)],
    ]
    t_kpi = Table(kpi_data, colWidths=[4.1*cm]*4)
    t_kpi.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,0), GRIS),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, BORD),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [GRIS, BLANC, GRIS]),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    elems += [t_kpi, Spacer(1, 4)]

    # Rang + bilan top 6
    extra_data = [
        ["Position au classement", Paragraph(f'<font color="{coul_hex}"><b>{rang}e</b></font>', corps)],
    ]
    if tot_t6:
        extra_data.append(["Bilan vs Top 6",
            Paragraph(f'<font color="{coul_hex}"><b>{vt6}V · {nt6}N · {dt6}D  ({vt6/tot_t6*100:.0f}% victoires)</b></font>', corps)])
    t_extra = Table(extra_data, colWidths=[9*cm, 7.5*cm])
    t_extra.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8.5), ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, BORD),
    ]))
    elems += [t_extra, Spacer(1, 6)]

    # Fil de la saison
    elems.append(Paragraph("Fil de la saison", sous_titre))
    fil_data = [[
        Paragraph("<b>J</b>", corps), Paragraph("<b>Adversaire</b>", corps),
        Paragraph("<b>Score</b>", corps), Paragraph("<b>Rés.</b>", corps)
    ]]
    for _, m in meq.sort_values("journee").iterrows():
        is_dom = (m["dom"]==eq)
        adv = m["ext"] if is_dom else m["dom"]
        sc = f'{m["score_dom"]}–{m["score_ext"]}' if is_dom else f'{m["score_ext"]}–{m["score_dom"]}'
        r = m["res_dom"] if is_dom else m["res_ext"]
        loc = "Dom" if is_dom else "Ext"
        rc = (VERT_RL if r=="V" else (OR_RL if r=="N" else ROUGE_RL))
        fil_data.append([
            Paragraph(f'J{int(m["journee"])} ({loc})', corps),
            Paragraph(nc(adv), corps),
            Paragraph(sc, corps),
            Paragraph(f'<font color="{"#27AE60" if r=="V" else ("#C9A24B" if r=="N" else "#C00018")}"><b>{r}</b></font>', corps)
        ])
    t_fil = Table(fil_data, colWidths=[2.5*cm, 8.5*cm, 2.5*cm, 3*cm], repeatRows=1)
    t_fil.setStyle(TableStyle(tbl_style_base() + header_row() + zebra()))
    elems += [t_fil, Spacer(1, 6)]

    # ---- SECTION 02 : ANALYSE TACTIQUE ----
    elems.append(Paragraph("SECTION 02 — Analyse Tactique", titre_section))

    # Impact 1er but + Dom/Ext (2 colonnes)
    m_tot = pb["marque"]["total"] or 1; e_tot = pb["encaisse"]["total"] or 1
    mw = pb["marque"]["V"]/m_tot*100; ew = pb["encaisse"]["V"]/e_tot*100

    pb_data = [[Paragraph("Impact du premier but", sous_titre), Paragraph("Domicile vs Extérieur", sous_titre)]]
    pb_inner = [
        [Paragraph(f'Marque 1er ({pb["marque"]["total"]} matchs)', corps),
         Paragraph(f'<font color="{coul_hex}" size="16"><b>{mw:.0f}%</b></font>', ps("v1",alignment=1))],
        [Paragraph(f'{pb["marque"]["V"]}V · {pb["marque"]["N"]}N · {pb["marque"]["D"]}D', gris_stl), ""],
        [Paragraph(f'Encaisse 1er ({pb["encaisse"]["total"]} matchs)', corps),
         Paragraph(f'<font color="#C00018" size="16"><b>{ew:.0f}%</b></font>', ps("v2",alignment=1))],
        [Paragraph(f'{pb["encaisse"]["V"]}V · {pb["encaisse"]["N"]}N · {pb["encaisse"]["D"]}D', gris_stl), ""],
    ]
    t_pb_inner = Table(pb_inner, colWidths=[4.5*cm, 2.5*cm])
    t_pb_inner.setStyle(TableStyle([
        ("GRID", (0,0),(-1,-1), 0.3, BORD), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("SPAN",(1,1),(1,1)), ("SPAN",(1,3),(1,3)),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#F0FFF4")),
        ("BACKGROUND",(0,2),(-1,2),colors.HexColor("#FFF5F5")),
    ]))

    de_inner = [
        [Paragraph(f'Domicile ({td} matchs)', corps),
         Paragraph(f'<font color="{coul_hex}" size="16"><b>{vd/td*100:.0f}%</b></font>', ps("v3",alignment=1))],
        [Paragraph(f'{vd}V · {nd}N · {dd}D', gris_stl), ""],
        [Paragraph(f'Extérieur ({te} matchs)', corps),
         Paragraph(f'<font color="{coul_hex}" size="16"><b>{ve/te*100:.0f}%</b></font>', ps("v4",alignment=1))],
        [Paragraph(f'{ve}V · {ne_}N · {de_}D', gris_stl), ""],
    ]
    t_de_inner = Table(de_inner, colWidths=[4.5*cm, 2.5*cm])
    t_de_inner.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,BORD), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BLANC,GRIS,BLANC,GRIS]),
    ]))

    t_row1 = Table([[t_pb_inner, t_de_inner]], colWidths=[8.2*cm, 8.2*cm])
    t_row1.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),4),
    ]))
    elems += [t_row1, Spacer(1,6)]

    # Retours au score + Momentum (2 colonnes)
    rs_inner_data = [
        [Paragraph("Jamais mené", corps),
         Paragraph(f'<font color="#27AE60"><b>{rs_data["jamais"]}</b></font>', ps("rs",alignment=2)),
         mini_barre_h(rs_data["jamais"], n_m, 4*cm, coul_fill=D1_VERT)],
        [Paragraph("Est mené → Victoire", corps),
         Paragraph(f'<font color="{coul_hex}"><b>{rs_data["mv"]}</b></font>', ps("rs2",alignment=2)),
         mini_barre_h(rs_data["mv"], n_m, 4*cm, coul_fill=coul_hex)],
        [Paragraph("Est mené → Nul", corps),
         Paragraph(f'<font color="#C9A24B"><b>{rs_data["mn"]}</b></font>', ps("rs3",alignment=2)),
         mini_barre_h(rs_data["mn"], n_m, 4*cm, coul_fill=D1_OR)],
        [Paragraph("Est mené → Défaite", corps),
         Paragraph(f'<font color="#C00018"><b>{rs_data["md"]}</b></font>', ps("rs4",alignment=2)),
         mini_barre_h(rs_data["md"], n_m, 4*cm, coul_fill=D1_ROUGE)],
    ]
    t_rs = Table(rs_inner_data, colWidths=[3.5*cm, 1.2*cm, 4*cm])
    t_rs.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,BORD), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BLANC,GRIS,BLANC,GRIS]),
    ]))

    mo_labels = {"Marque → Marque":"#27AE60","Marque → Encaisse":"#C9A24B",
                 "Encaisse → Marque":coul_hex,"Encaisse → Encaisse":"#C00018"}
    mo_inner_data = []
    for label, val in mo_data.items():
        badge_color = mo_labels.get(label, D1_GRIS)
        txt = f"{val} min" if val else "—"
        mo_inner_data.append([
            Paragraph(label, corps),
            Paragraph(f'<font color="{badge_color}" size="12"><b>{txt}</b></font>',
                      ps(f"mo_{label[:3]}", alignment=2))
        ])
    t_mo = Table(mo_inner_data, colWidths=[5*cm, 2.7*cm])
    t_mo.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,BORD), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BLANC,GRIS,BLANC,GRIS]),
    ]))

    rs_header = Paragraph("Retours au score", sous_titre)
    mo_header = Paragraph("Momentum après un but", sous_titre)
    t_row2 = Table([[rs_header, mo_header],[t_rs, t_mo]], colWidths=[8.2*cm, 8.2*cm])
    t_row2.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),4),
    ]))
    elems += [t_row2, Spacer(1,6)]

    # ---- SECTION 03 : ANALYSE TEMPORELLE ----
    elems.append(Paragraph("SECTION 03 — Analyse Temporelle", titre_section))
    mins_p = dpour["minute"].dropna().astype(int)
    mins_c = dcontre["minute"].dropna().astype(int)
    tr_p = pd.cut(mins_p, bins=range(0,41,5), labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    tr_c = pd.cut(mins_c, bins=range(0,41,5), labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    max_tr = max(tr_p.max(), tr_c.max(), 1)

    tr_data = [[Paragraph("<b>Tranche</b>", corps),
                Paragraph("<b>Buts marqués</b>", corps), Paragraph("", corps),
                Paragraph("<b>Buts encaissés</b>", corps), Paragraph("", corps)]]
    for tr in tr_p.index:
        vp = int(tr_p[tr]); vc = int(tr_c[tr])
        is_p1 = tr in list(tr_p.index)[:4]
        cf = coul_hex if is_p1 else D1_ROUGE
        tr_data.append([
            Paragraph(str(tr), corps),
            Paragraph(f'<font color="{coul_hex}"><b>{vp}</b></font>', corps),
            mini_barre_h(vp, int(max_tr), 6*cm, coul_fill=coul_hex),
            Paragraph(f'<font color="#C00018"><b>{vc}</b></font>', corps),
            mini_barre_h(vc, int(max_tr), 3.5*cm, coul_fill=D1_ROUGE),
        ])
    t_tr = Table(tr_data, colWidths=[1.8*cm, 1.2*cm, 6*cm, 1.2*cm, 3.5*cm], repeatRows=1)
    t_tr.setStyle(TableStyle(tbl_style_base() + header_row() + zebra()))
    elems += [t_tr, Spacer(1,6)]

    # ---- SECTION 04 : BUTEURS ----
    elems.append(Paragraph("SECTION 04 — Analyse des Buteurs", titre_section))
    bb = dpour["joueur"].value_counts()
    total_b = len(dpour) or 1
    top3_pct = bb.head(3).sum()/total_b*100
    elems.append(Paragraph(f'Top 3 : {bb.head(3).sum()} buts sur {total_b} ({top3_pct:.0f}%)', gris_stl))
    elems.append(Spacer(1,4))
    for joueur, nb in bb.head(10).items():
        pct = nb/total_b*100
        row_data = [[
            Paragraph(nj(joueur), corps),
            Paragraph(f'<font color="{coul_hex}"><b>{nb}</b></font>', ps(f"bj",alignment=1)),
            mini_barre_h(nb, int(bb.max()), 7*cm, coul_fill=coul_hex),
            Paragraph(f'{pct:.0f}%', gris_stl),
        ]]
        t_row = Table(row_data, colWidths=[4.5*cm, 1*cm, 7*cm, 1.5*cm])
        t_row.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),2), ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LINEBELOW",(0,0),(-1,-1),0.2,BORD),
        ]))
        elems.append(t_row)
    elems.append(Spacer(1,6))

    # ---- SECTION 05 : ORIGINES ----
    if eq in EQUIPES_AVEC_ORIGINE:
        elems.append(Paragraph("SECTION 05 — Origines des Buts", titre_section))
        oo = dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
        n_r = int(dpour["origine"].notna().sum())
        elems.append(Paragraph(f'{n_r} buts analysés sur {total_b}', gris_stl))
        elems.append(Spacer(1,4))
        for orig, nb in oo.items():
            pct = nb/n_r*100
            row_data = [[
                Paragraph(orig, corps),
                Paragraph(f'<font color="{coul_hex}"><b>{nb}</b></font>', ps(f"oo",alignment=1)),
                mini_barre_h(nb, int(oo.max()), 7*cm, coul_fill=coul_hex),
                Paragraph(f'{pct:.0f}%', gris_stl),
            ]]
            t_row = Table(row_data, colWidths=[4.5*cm, 1*cm, 7*cm, 1.5*cm])
            t_row.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("TOPPADDING",(0,0),(-1,-1),2), ("BOTTOMPADDING",(0,0),(-1,-1),2),
                ("LINEBELOW",(0,0),(-1,-1),0.2,BORD),
            ]))
            elems.append(t_row)

    doc.build(elems)
    buf.seek(0)
    return buf


# PAGE Analyse Tactique → fusionnée dans Fiche équipe

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
    return df[(df["equipe_marque"]==eq)&(df["minute"]>=36)]["joueur"].value_counts()

# ============================================================================
# PAGE — FICHE ÉQUIPE (fusion Vue équipe + Analyse Tactique + Scouting + Origines)
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
        c1.metric("Buteurs utilisés", dpour["joueur"].nunique())
        c2.metric("Buts P1", int((dpour["periode"]==1).sum()))
        c3.metric("Buts P2", int((dpour["periode"]==2).sum()))
        clutch_n, total_dp = buts_clutch_eq(eq)
        c4.metric("Buts clutch (36-40')", clutch_n,
                  f"{clutch_n/total_dp*100:.0f}% des buts" if total_dp else "")

        cg, cd = st.columns(2)
        with cg:
            st.markdown("### Top buteurs")
            bb = dpour["joueur"].value_counts()
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
            diff_pct = m_win - e_win
            msg = (f"<b style='color:{D1_BLANC}'>{diff_pct:.0f}%</b> de plus en marquant le premier but"
                   if diff_pct > 0 else "Reste performante même en encaissant le premier but")
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
            for label, val, c_ in [("Jamais menée",rs["jamais"],D1_VERT),("Menée → Victoire",rs["mv"],coul),("Menée → Nul",rs["mn"],D1_OR),("Menée → Défaite",rs["md"],D1_ROUGE)]:
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
            bb_sc = dpour["joueur"].value_counts().head(10)
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
            coul_tc = [D1_ROUGE if t==best_tr else D1_BORDEAUX_2 for t in tr_c.index]
            fig_tc = go.Figure(go.Bar(x=tr_c.index.astype(str), y=tr_c.values, marker_color=coul_tc,
                text=tr_c.values, textposition="outside", textangle=0, textfont=dict(size=13,color=D1_BLANC)))
            fig_tc.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig_tc, 260), use_container_width=True)
            st.markdown(f"<p class='note'>⚠ Tranche la plus vulnérable : <b>{best_tr}</b> ({int(tr_c.max())} buts encaissés)</p>",
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
                st.markdown("### Scoreurs adverses les plus prolifiques")
                sc_adv = dcontre["joueur"].value_counts().head(8)
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
            cd3.metric("Plus vulnérable","1re période" if vul_p1>vul_p2 else "2e période")

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
elif page == "Lexique":
    st.title("Lexique — Indicateurs & Calculs")

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

    st.markdown("---")
    st.markdown("### Source des données & mise à jour")
    st.markdown(
        f'<div style="background:{D1_CARTE};border-radius:10px;padding:1rem 1.2rem">'
        f'<p style="margin:0 0 .5rem 0"><b>Source :</b> fichier Excel <code>But_D1.xlsx</code> — '
        f'mis à jour manuellement après chaque journée.</p>'
        f'<p style="margin:0 0 .5rem 0"><b>Migration :</b> le script <code>python migration_buts.py</code> '
        f'lit le fichier Excel et génère la base SQLite <code>futsal_d1.db</code>.</p>'
        f'<p style="margin:0 0 .5rem 0"><b>Données actuelles :</b> {len(df)} buts · '
        f'{len(EQUIPES)} équipes · J{min(JOURNEES)}–J{max(JOURNEES)}</p>'
        f'<p style="margin:0"><b>Origines des buts :</b> saisie en cours pour {len(EQUIPES_AVEC_ORIGINE)} équipes — '
        f'{df["origine"].notna().sum()} buts sur {len(df)} analysés '
        f'({df["origine"].notna().mean()*100:.0f}%)</p>'
        f'</div>',
        unsafe_allow_html=True
    )
