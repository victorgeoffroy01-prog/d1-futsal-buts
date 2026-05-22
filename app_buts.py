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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER

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
    padding-bottom:.25rem;letter-spacing:-.3px;font-size:1.55rem!important;margin-bottom:.9rem!important}}
h2,h3{{color:{D1_BLANC}!important;font-weight:600!important}}
h3{{font-size:.98rem!important;margin-top:1rem!important;margin-bottom:.25rem!important;
    border-left:3px solid {D1_ROUGE};padding-left:.5rem}}
p,label,span,div{{color:{D1_BLANC}}}
[data-testid="stSidebar"]{{background:{D1_BORDEAUX};border-right:1px solid {D1_BORDEAUX_2};
    min-width:200px!important;max-width:200px!important}}
[data-testid="stSidebar"] *{{color:{D1_BLANC}!important}}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label{{
    padding:.28rem .55rem;border-radius:5px;font-size:.86rem;font-weight:500;
    margin:.06rem 0;cursor:pointer;transition:background .1s}}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover{{background:rgba(255,255,255,.1)}}
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
        font=dict(family="Inter", color=D1_BLANC, size=12), height=h,
        margin=dict(l=8, r=8, t=38 if titre else 14, b=8),
        title=dict(text=titre or "", font=dict(size=13, color=D1_BLANC)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    return fig

def barh_equipes(noms, vals, h=320, texte=None, opacite=1.0):
    """Barres horizontales avec couleur propre à chaque équipe, chiffres droits."""
    fig = go.Figure()
    for nom, val in zip(noms, vals):
        coul = COULEUR_EQUIPE.get(nom, D1_ROUGE)
        if opacite < 1:
            coul = hex_to_rgba(coul, opacite)
        txt = str(int(val))
        fig.add_trace(go.Bar(
            x=[val], y=[nom], orientation="h",
            marker_color=coul,
            text=[txt], textposition="auto",
            textangle=0,
            showlegend=False, name=nom,
            insidetextanchor="middle",
        ))
    fig.update_yaxes(autorange="reversed")
    return style_fig(fig, h)

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
# SIDEBAR
# ============================================================================
with st.sidebar:
    if LOGO_D1.exists():
        st.image(str(LOGO_D1), width=88)
    st.markdown("---")
    page = st.radio("", [
        "🏠 Accueil","🏆 Classement","⚽ Fiche match",
        "👟 Classement buteurs","⏱ Profil temporel",
        "📊 Dynamique de score","🛡 Vue équipe",
        "🎯 Tactique / Origines","⚔ Confrontations",
        "🔭 Scouting adverse","📈 Analyse avancée",
    ], label_visibility="collapsed")
    page = page.split(" ",1)[-1].strip()
    st.markdown("---")
    st.caption(f"{len(df)} buts · {len(EQUIPES)} équipes · J{min(JOURNEES)}–J{max(JOURNEES)}")

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
    c5.metric("Meilleure attaque", f"{top_att.max()} buts", top_att.idxmax().split()[0])

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

# ============================================================================
# PAGE — CLASSEMENT
# ============================================================================
elif page == "Classement":
    st.title("Classement D1 Futsal")
    clt = construire_classement()

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

    tab_exp = clt[["equipe","J","V","N","D","Pts","BP","BC","Diff"]].copy()
    tab_exp.columns = ["Équipe","J","V","N","D","Pts","BP","BC","Diff"]
    c1,c2 = st.columns(2)
    with c1: dl_csv(tab_exp,"⬇ CSV","classement_d1.csv")
    with c2:
        st.download_button("⬇ PDF",
            pdf_tableau("Classement D1 Futsal",f"Journée {max(JOURNEES)}",tab_exp),
            file_name="classement_d1.pdf",mime="application/pdf")

    st.markdown("### Évolution des points (cumulés)")
    evo = evolution_classement()
    fig = go.Figure()
    for eq in clt["equipe"].tolist():
        sub = evo[evo["equipe"]==eq].sort_values("journee")
        coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
        fig.add_trace(go.Scatter(
            x=sub["journee"], y=sub["pts"], mode="lines+markers",
            name=eq.split()[0], line=dict(color=coul, width=2.5), marker=dict(size=4),
            hovertemplate=f"<b>{eq}</b><br>J%{{x}} → %{{y}} pts<extra></extra>"
        ))
    fig.update_xaxes(tickvals=JOURNEES, ticktext=[f"J{j}" for j in JOURNEES])
    st.plotly_chart(style_fig(fig, 440), use_container_width=True)

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
        hovertemplate=f"<b>{dom.split()[0]}</b> %{{y}}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ye, mode="lines", name=ext.split()[0],
        line=dict(color=coul_ext, width=3),
        fill="tozeroy", fillcolor=hex_to_rgba(coul_ext, 0.22),
        hovertemplate=f"<b>{ext.split()[0]}</b> %{{y}}<extra></extra>"
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

# ============================================================================
# PAGE — CLASSEMENT BUTEURS
# ============================================================================
elif page == "Classement buteurs":
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
    c1,c2=st.columns(2)
    with c1: dl_csv(aff,"⬇ CSV","buteurs.csv")
    with c2:
        st.download_button("⬇ PDF",pdf_tableau("Classement des buteurs","D1 Futsal",aff.head(40)),
                           file_name="buteurs.pdf",mime="application/pdf")
    st.markdown("### Profil d'un buteur")
    recherche = st.text_input("🔍 Rechercher un buteur", placeholder="Nom du joueur...")
    liste_joueurs = clt["joueur"].tolist()
    if recherche:
        liste_joueurs = [j for j in liste_joueurs if recherche.upper() in j.upper()]
    if not liste_joueurs:
        st.warning("Aucun joueur trouvé.")
        st.stop()
    j = st.selectbox("Résultats", liste_joueurs, label_visibility="collapsed")
    dj=df[df["joueur"]==j]
    a,b,c,d2=st.columns(4)
    a.metric("Buts",len(dj)); b.metric("1re période",int((dj["periode"]==1).sum()))
    c.metric("2e période",int((dj["periode"]==2).sum())); d2.metric("Adversaires",dj["equipe_encaisse"].nunique())
    sit=dj["situation"].value_counts()
    if not sit.empty:
        fig=go.Figure(go.Bar(x=sit.index,y=sit.values,textangle=0,
                             marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit.index],
                             text=sit.values,textposition="outside"))
        fig.update_yaxes(showticklabels=False)
        st.plotly_chart(style_fig(fig,230,"Situation au moment des buts"),use_container_width=True)

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
    c1.metric("En étant mené",int(sit["Mené"]),f"{sit['Mené']/tot*100:.0f}%")
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
            st.markdown("#### En étant mené")
            s=comp.sort_values("pct_mené",ascending=False)
            fig_m=go.Figure(go.Bar(x=s["pct_mené"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_ROUGE,text=[f"{v:.0f}%" for v in s["pct_mené"]],
                                   textposition="auto",textangle=0))
            fig_m.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_m,max(280,28*len(s))),use_container_width=True)
        with c2:
            st.markdown("#### À égalité")
            s=comp.sort_values("pct_egal",ascending=False)
            fig_e=go.Figure(go.Bar(x=s["pct_egal"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_OR,text=[f"{v:.0f}%" for v in s["pct_egal"]],
                                   textposition="auto",textangle=0))
            fig_e.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_e,max(280,28*len(s))),use_container_width=True)
        with c3:
            st.markdown("#### En menant")
            s=comp.sort_values("pct_men",ascending=False)
            fig_v=go.Figure(go.Bar(x=s["pct_men"].round(0),y=s["Équipe"],orientation="h",
                                   marker_color=D1_VERT,text=[f"{v:.0f}%" for v in s["pct_men"]],
                                   textposition="auto",textangle=0))
            fig_v.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_v,max(280,28*len(s))),use_container_width=True)

# ============================================================================
# PAGE — VUE ÉQUIPE
# ============================================================================
elif page == "Vue équipe":
    st.title("Fiche équipe")
    eq=st.selectbox("Équipe",EQUIPES)
    clt=construire_classement(); rang_row=clt[clt["equipe"]==eq].iloc[0]
    rang=clt[clt["equipe"]==eq].index[0]+1
    coul=COULEUR_EQUIPE.get(eq,D1_ROUGE); lg=logo_b64(eq,48)
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul};border-radius:11px;padding:.9rem 1.1rem;'
        f'display:flex;align-items:center;gap:.9rem;margin-bottom:.9rem">'
        f'{lg}<div>'
        f'<div style="font-size:1.05rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.8rem">'
        f'Rang <b style="color:{coul}">{rang}</b> · {int(rang_row["Pts"])} pts · '
        f'{int(rang_row["V"])}V {int(rang_row["N"])}N {int(rang_row["D"])}D</div>'
        f'<div style="margin-top:.25rem">{forme_ronds(rang_row["forme"])}</div>'
        f'</div></div>', unsafe_allow_html=True
    )
    dpour=df[df["equipe_marque"]==eq]; dcontre=df[df["equipe_encaisse"]==eq]
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Buts marqués",len(dpour)); c2.metric("Buts encaissés",len(dcontre))
    c3.metric("Différence",f"{len(dpour)-len(dcontre):+d}"); c4.metric("Buteurs",dpour["joueur"].nunique())
    cg,cd=st.columns(2)
    with cg:
        st.markdown("### Buteurs")
        bb=dpour["joueur"].value_counts()
        fig=go.Figure(go.Bar(x=bb.values,y=bb.index,orientation="h",
                             marker_color=coul,text=bb.values,textposition="auto",textangle=0))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig,max(240,24*len(bb))),use_container_width=True)
    with cd:
        st.markdown("### Quand l'équipe marque")
        mins=dpour["minute"].dropna().astype(int)
        tr=pd.cut(mins,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
        fig2=go.Figure(go.Bar(x=tr.index.astype(str),y=tr.values,marker_color=coul,
                              text=tr.values,textposition="outside",textangle=0))
        fig2.update_yaxes(showticklabels=False)
        st.plotly_chart(style_fig(fig2,260),use_container_width=True)
    if eq in EQUIPES_AVEC_ORIGINE:
        st.markdown("### Origine des buts")
        oo=dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
        n_r=int(dpour["origine"].notna().sum())
        st.markdown(f'<span class="tag" style="background:{coul};color:white">{n_r}/{len(dpour)} buts analysés</span>',
                    unsafe_allow_html=True)
        fig3=go.Figure(go.Bar(x=oo.values,y=oo.index,orientation="h",
                              marker_color=coul,text=oo.values,textposition="auto",textangle=0))
        fig3.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig3,max(220,28*len(oo))),use_container_width=True)
    else:
        st.info("Origine des buts pas encore renseignée pour cette équipe.")

# ============================================================================
# PAGE — TACTIQUE / ORIGINES
# ============================================================================
elif page == "Tactique / Origines":
    st.title("Tactique — Origine des buts")
    if not EQUIPES_AVEC_ORIGINE: st.info("Aucune origine renseignée."); st.stop()
    st.markdown(f"<p class='note'>Données : {', '.join(EQUIPES_AVEC_ORIGINE)}</p>",unsafe_allow_html=True)
    do=df[df["origine"].notna()]
    st.markdown("### Répartition globale")
    glob=do["origine"].value_counts()
    fig=go.Figure(go.Bar(x=glob.values,y=glob.index,orientation="h",
                         marker_color=D1_ROUGE,text=glob.values,textposition="auto",textangle=0))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig,max(260,30*len(glob))),use_container_width=True)
    st.markdown("### Comparaison par équipe")
    sel=st.multiselect("Équipes",EQUIPES_AVEC_ORIGINE,default=EQUIPES_AVEC_ORIGINE[:3])
    if sel:
        sous=do[do["equipe_marque"].isin(sel)]
        pivot=sous.groupby(["equipe_marque","origine"]).size().reset_index(name="n")
        fig2=go.Figure()
        for i,og in enumerate(sorted(sous["origine"].unique())):
            sub=pivot[pivot["origine"]==og]
            fig2.add_trace(go.Bar(name=og,x=sub["equipe_marque"],y=sub["n"],
                                  marker_color=PALETTE[i%len(PALETTE)]))
        fig2.update_layout(barmode="stack")
        st.plotly_chart(style_fig(fig2,380),use_container_width=True)
        tab=pivot.pivot(index="equipe_marque",columns="origine",values="n").fillna(0).astype(int)
        st.dataframe(tab,use_container_width=True)

# ============================================================================
# PAGE — CONFRONTATIONS
# ============================================================================
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
elif page == "Scouting adverse":
    st.title("Scouting adverse")
    st.markdown("<p class='note'>Fiche de préparation match — analyse offensive et défensive d'une équipe.</p>",
                unsafe_allow_html=True)

    eq = st.selectbox("Équipe à analyser", EQUIPES)
    coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
    clt  = construire_classement()
    matchs = construire_matchs()
    rang_row = clt[clt["equipe"]==eq].iloc[0]
    rang = clt[clt["equipe"]==eq].index[0]+1
    lg   = logo_b64(eq, 48)

    # Header équipe
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul};border-radius:11px;padding:.9rem 1.1rem;'
        f'display:flex;align-items:center;gap:.9rem;margin-bottom:1rem">'
        f'{lg}<div>'
        f'<div style="font-size:1.05rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.8rem">'
        f'Rang <b style="color:{coul}">{rang}</b> · {int(rang_row["Pts"])} pts · '
        f'{int(rang_row["V"])}V {int(rang_row["N"])}N {int(rang_row["D"])}D · '
        f'{int(rang_row["BP"])} buts marqués · {int(rang_row["BC"])} encaissés</div>'
        f'<div style="margin-top:.25rem">{forme_ronds(rang_row["forme"])}</div>'
        f'</div></div>', unsafe_allow_html=True
    )

    # Calcul buts/match
    meq = matchs[(matchs["dom"]==eq)|(matchs["ext"]==eq)]
    n_matchs = len(meq) or 1
    dpour   = df[df["equipe_marque"]==eq]
    dcontre = df[df["equipe_encaisse"]==eq]

    buts_pm  = len(dpour)/n_matchs
    enc_pm   = len(dcontre)/n_matchs
    clean_sh = int((meq.apply(lambda m:
        (m["score_ext"]==0 and m["dom"]==eq) or
        (m["score_dom"]==0 and m["ext"]==eq), axis=1)).sum())

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Buts/match (att.)", f"{buts_pm:.1f}")
    c2.metric("Buts/match (déf.)", f"{enc_pm:.1f}")
    c3.metric("Clean sheets", clean_sh)
    c4.metric("Matchs analysés", n_matchs)

    st.markdown("---")
    ong1, ong2 = st.tabs(["⚔ Profil offensif", "🛡 Profil défensif"])

    # ---- OFFENSIF ----
    with ong1:
        st.markdown("### Buteurs dangereux")
        bb = dpour["joueur"].value_counts().head(10)
        total_buts = len(dpour) or 1
        fig = go.Figure()
        for j, n in bb.items():
            pct = n/total_buts*100
            fig.add_trace(go.Bar(
                x=[n], y=[j], orientation="h",
                marker_color=coul,
                text=[f"{n} ({pct:.0f}%)"],
                textposition="auto", textangle=0,
                showlegend=False, name=j
            ))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig, max(240,26*len(bb))), use_container_width=True)

        # Concentration
        top1_pct = bb.iloc[0]/total_buts*100 if len(bb) else 0
        top3_pct = bb.head(3).sum()/total_buts*100 if len(bb) else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Part du top buteur", f"{top1_pct:.0f}%", bb.index[0] if len(bb) else "")
        c2.metric("Part du top 3", f"{top3_pct:.0f}%", "des buts de l'équipe")
        c3.metric("Buteurs différents utilisés", dpour["joueur"].nunique())

        cg, cd = st.columns(2)
        with cg:
            st.markdown("### Quand ils marquent (tranches 5 min)")
            mins_p = dpour["minute"].dropna().astype(int)
            tr_p = pd.cut(mins_p, bins=range(0,41,5),
                          labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
            fig2 = go.Figure(go.Bar(x=tr_p.index.astype(str), y=tr_p.values,
                                    marker_color=coul, text=tr_p.values,
                                    textposition="outside", textangle=0))
            fig2.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig2, 260), use_container_width=True)
        with cd:
            st.markdown("### Dans quelle situation ils marquent")
            sit_p = dpour[dpour["situation"].notna()]["situation"].value_counts()
            fig3 = go.Figure(go.Bar(
                x=sit_p.index, y=sit_p.values,
                marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit_p.index],
                text=[f"{v} ({v/sit_p.sum()*100:.0f}%)" for v in sit_p.values],
                textposition="outside", textangle=0
            ))
            fig3.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig3, 260), use_container_width=True)

        if eq in EQUIPES_AVEC_ORIGINE:
            st.markdown("### Origine des buts offensifs")
            oo = dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
            fig4 = go.Figure(go.Bar(x=oo.values, y=oo.index, orientation="h",
                                    marker_color=coul, text=oo.values,
                                    textposition="auto", textangle=0))
            fig4.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig4, max(220,28*len(oo))), use_container_width=True)

    # ---- DÉFENSIF ----
    with ong2:
        st.markdown("### Quand ils encaissent (minutes à risque)")
        mins_c = dcontre["minute"].dropna().astype(int)
        tr_c = pd.cut(mins_c, bins=range(0,41,5),
                      labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
        # Mettre en rouge la tranche la plus dangereuse
        max_tr = tr_c.max()
        coul_tr = [D1_ROUGE if v==max_tr else D1_BORDEAUX_2 for v in tr_c.values]
        fig5 = go.Figure(go.Bar(x=tr_c.index.astype(str), y=tr_c.values,
                                marker_color=coul_tr, text=tr_c.values,
                                textposition="outside", textangle=0))
        fig5.update_yaxes(showticklabels=False)
        st.plotly_chart(style_fig(fig5, 260), use_container_width=True)
        tranche_max = tr_c.idxmax()
        st.markdown(f"<p class='note'>⚠ Tranche la plus vulnérable : <b>{tranche_max}</b> "
                    f"({int(tr_c.max())} buts encaissés)</p>", unsafe_allow_html=True)

        cg, cd = st.columns(2)
        with cg:
            st.markdown("### Situation de l'adversaire quand il marque contre eux")
            sit_c = dcontre[dcontre["situation"].notna()]["situation"].value_counts()
            fig6 = go.Figure(go.Bar(
                x=sit_c.index, y=sit_c.values,
                marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit_c.index],
                text=[f"{v} ({v/sit_c.sum()*100:.0f}%)" for v in sit_c.values],
                textposition="outside", textangle=0
            ))
            fig6.update_yaxes(showticklabels=False)
            st.plotly_chart(style_fig(fig6, 260), use_container_width=True)
        with cd:
            st.markdown("### Buteurs qui leur ont le plus scoré")
            scoreurs = dcontre["joueur"].value_counts().head(8)
            fig7 = go.Figure(go.Bar(x=scoreurs.values, y=scoreurs.index, orientation="h",
                                    marker_color=D1_ROUGE, text=scoreurs.values,
                                    textposition="auto", textangle=0))
            fig7.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig7, max(220,28*len(scoreurs))), use_container_width=True)

        st.markdown("### Par quelle équipe ils ont le plus encaissé")
        enc_par_eq = dcontre["equipe_marque"].value_counts()
        fig8 = go.Figure()
        for e, v in enc_par_eq.items():
            c = COULEUR_EQUIPE.get(e, D1_ROUGE)
            fig8.add_trace(go.Bar(x=[v], y=[e], orientation="h",
                                  marker_color=c, text=[v], textposition="auto", textangle=0,
                                  showlegend=False, name=e))
        fig8.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig8, max(240,28*len(enc_par_eq))), use_container_width=True)

        # Vulnérabilité P1 vs P2
        vul_p1 = int((dcontre["periode"]==1).sum())
        vul_p2 = int((dcontre["periode"]==2).sum())
        tot_enc = vul_p1+vul_p2 or 1
        c1,c2,c3 = st.columns(3)
        c1.metric("Buts encaissés P1", vul_p1, f"{vul_p1/tot_enc*100:.0f}%")
        c2.metric("Buts encaissés P2", vul_p2, f"{vul_p2/tot_enc*100:.0f}%")
        c3.metric("Plus vulnérable en", "1re période" if vul_p1>vul_p2 else "2e période")


# ============================================================================
# PAGE — ANALYSE AVANCÉE
# ============================================================================
elif page == "Analyse avancée":
    st.title("Analyse avancée")

    matchs = construire_matchs()

    # ---- RÉGULARITÉ OFFENSIVE ----
    st.markdown("### Régularité offensive (buts/match)")
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

    fig_reg = go.Figure()
    for _,r in reg.iterrows():
        coul = COULEUR_EQUIPE.get(r["equipe"], D1_ROUGE)
        # Barre principale
        fig_reg.add_trace(go.Bar(
            x=[r["moy"]], y=[r["equipe"]], orientation="h",
            marker_color=coul, name=r["equipe"],
            text=[f'{r["moy"]:.1f} ± {r["std"]:.1f}'],
            textposition="auto", textangle=0, showlegend=False,
            error_x=dict(type="data", array=[r["std"]], color="rgba(255,255,255,.5)", thickness=2)
        ))
    fig_reg.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig_reg, max(320,30*len(reg))), use_container_width=True)
    st.markdown("<p class='note'>Barre d'erreur = écart-type. Plus la barre est large, plus l'équipe est irrégulière.</p>",
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
            fig_c1.add_trace(go.Bar(x=[r["top1_pct"]], y=[r["equipe"]], orientation="h",
                                    marker_color=c, text=[f'{r["top1_pct"]:.0f}%'],
                                    textposition="auto", textangle=0, showlegend=False))
        fig_c1.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig_c1, max(280,28*len(conc))), use_container_width=True)
    with cd:
        st.markdown("#### Nombre de buteurs différents utilisés")
        fig_c2 = go.Figure()
        for _,r in conc.sort_values("nb_buteurs",ascending=False).iterrows():
            c = COULEUR_EQUIPE.get(r["equipe"], D1_ROUGE)
            fig_c2.add_trace(go.Bar(x=[r["nb_buteurs"]], y=[r["equipe"]], orientation="h",
                                    marker_color=c, text=[int(r["nb_buteurs"])],
                                    textposition="auto", textangle=0, showlegend=False))
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
