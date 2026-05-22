"""
================================================================================
ANALYSE DES BUTS — D1 FUTSAL   (v2.1 — retours visuels)
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

# Couleur identitaire par équipe — utilisée sur TOUS les graphes
COULEUR_EQUIPE = {
    "ETOILE LAVALLOISE FC":  "#FFA500",
    "SPORTING CLUB PARIS":   "#2ECC71",
    "MONTPELLIER MED. F.":   "#3A7BD5",
    "TOULON METROPOLE F.":   "#E74C3C",
    "GOAL FUTSAL CLUB":      "#27AE60",
    "NANTES METROPOLE F.":   "#F1C40F",
    "PARIS ACASA":           "#8E44AD",
    "AS AVION FUTSAL":       "#1ABC9C",
    "UJS TOULOUSE":          "#E67E22",
    "NICE FUTSAL CLUB":      "#C0392B",
    "FC KINGERSHEIM":        "#95A5A6",
}

PALETTE = list(COULEUR_EQUIPE.values())

st.set_page_config(
    page_title="D1 Futsal — Analyse des buts",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLE — sobre, inspiré EDF
# ============================================================================
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
.stApp {{ background:{D1_ANTHRACITE}; }}
html,body,[class*="css"],.stMarkdown,.stMetric,button,input,select,textarea{{
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important;
}}
.block-container{{padding-top:1.2rem;padding-bottom:2rem;max-width:1400px}}

/* Titres */
h1{{color:{D1_BLANC}!important;border-bottom:2px solid {D1_ROUGE};
    padding-bottom:.25rem;letter-spacing:-.4px;font-size:1.6rem!important;margin-bottom:1rem!important}}
h2,h3{{color:{D1_BLANC}!important;font-weight:600!important;letter-spacing:-.2px}}
h3{{font-size:1rem!important;margin-top:1.1rem!important;margin-bottom:.3rem!important;
    border-left:3px solid {D1_ROUGE};padding-left:.6rem}}
p,label,span,div{{color:{D1_BLANC}}}

/* Sidebar sobre */
[data-testid="stSidebar"]{{
    background:{D1_BORDEAUX};
    border-right:1px solid {D1_BORDEAUX_2};
    min-width:210px!important;max-width:210px!important
}}
[data-testid="stSidebar"] *{{color:{D1_BLANC}!important}}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label{{
    padding:.3rem .6rem;border-radius:6px;font-size:.88rem;font-weight:500;
    margin:.08rem 0;display:flex;align-items:center;gap:.4rem;
    cursor:pointer;transition:background .12s
}}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover{{
    background:rgba(255,255,255,.1)
}}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] [aria-checked="true"] + label,
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"]{{
    background:rgba(192,0,24,.35)!important;font-weight:600
}}

/* Métriques compactes */
[data-testid="stMetric"]{{
    background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};
    border-radius:10px;padding:.7rem .9rem
}}
[data-testid="stMetricValue"]{{font-size:1.45rem!important;font-weight:800;color:{D1_BLANC}}}
[data-testid="stMetricLabel"]{{font-size:.72rem;color:{D1_GRIS};font-weight:500;
    text-transform:uppercase;letter-spacing:.4px}}
[data-testid="stMetricDelta"]{{font-size:.82rem}}

/* Selects */
.stSelectbox>div>div,.stMultiSelect>div>div{{
    background:{D1_CARTE}!important;border:1px solid {D1_BORDEAUX_2}!important;border-radius:8px!important
}}
div[data-baseweb="select"] *{{color:{D1_BLANC}!important}}

/* Bouton téléchargement */
.stDownloadButton>button{{
    background:{D1_ROUGE}!important;color:white!important;border:none!important;
    border-radius:7px!important;font-weight:600!important;font-size:.82rem!important;padding:.35rem .9rem!important
}}
.stDownloadButton>button:hover{{background:{D1_ROUGE_CLAIR}!important}}

/* Tables */
.stDataFrame{{border-radius:10px;overflow:hidden}}

/* Classement */
.clt-header{{display:flex;align-items:center;padding:.3rem .8rem;
    color:{D1_GRIS};font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px;
    border-bottom:1px solid {D1_BORDEAUX_2};margin-bottom:.15rem}}
.clt-row{{display:flex;align-items:center;gap:10px;padding:.4rem .8rem;
    border-radius:8px;margin:.1rem 0;border:1px solid rgba(255,255,255,.05);transition:background .1s}}
.clt-row:hover{{background:rgba(255,255,255,.04)}}
.clt-row.top3{{border-left:3px solid {D1_OR}}}
.clt-rang{{width:22px;font-weight:700;font-size:.88rem;color:{D1_GRIS};flex-shrink:0}}
.clt-rang.or{{color:{D1_OR}}}
.clt-nom{{flex:1;font-weight:600;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.clt-pts{{width:36px;text-align:center;font-weight:800;font-size:1.05rem;color:{D1_ROUGE_CLAIR};flex-shrink:0}}
.clt-vnpd{{width:90px;text-align:center;font-size:.78rem;color:{D1_GRIS};flex-shrink:0}}
.clt-buts{{width:70px;text-align:center;font-size:.8rem;flex-shrink:0}}
.clt-diff{{width:42px;text-align:center;font-size:.82rem;font-weight:600;flex-shrink:0}}
.clt-forme{{width:115px;text-align:right;flex-shrink:0}}

/* Badges forme ronds */
.fr{{display:inline-block;width:18px;height:18px;border-radius:50%;
    font-size:.66rem;font-weight:700;text-align:center;line-height:18px;margin:1px}}
.fr-V{{background:{D1_VERT};color:white}}
.fr-N{{background:{D1_OR};color:#1a1a1e}}
.fr-D{{background:{D1_ROUGE};color:white}}

/* Note */
.note{{color:{D1_GRIS};font-size:.78rem;font-style:italic;margin:.2rem 0}}

/* Podium */
.pod{{background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:12px;
    padding:1rem;text-align:center}}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPERS
# ============================================================================
def logo_b64(nom, size=32):
    p = LOGOS_DIR / f"{nom}.png"
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
            img.thumbnail((size*2, size*2), Image.LANCZOS)
            buf = BytesIO(); img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return (f'<img src="data:image/png;base64,{b64}" '
                    f'width="{size}" height="{size}" '
                    f'style="object-fit:contain;border-radius:3px;vertical-align:middle">')
        except Exception:
            pass
    coul = COULEUR_EQUIPE.get(nom, D1_ROUGE)
    ini = "".join(w[0] for w in nom.split()[:2])
    s = size
    return (f'<div style="width:{s}px;height:{s}px;border-radius:50%;background:{coul};'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'font-weight:800;font-size:{max(9,s//3)}px;color:white;vertical-align:middle;flex-shrink:0">'
            f'{ini}</div>')


def forme_ronds(resultats):
    return "".join(f'<span class="fr fr-{r}">{r}</span>' for r in resultats[-5:])


def hex_to_rgba(h, a=0.3):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"


def style_fig(fig, h=340, titre=None):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=D1_BLANC, size=12),
        height=h, margin=dict(l=8, r=8, t=38 if titre else 14, b=8),
        title=dict(text=titre or "", font=dict(size=13, color=D1_BLANC)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    return fig


def barh(noms, vals, couleurs=None, h=340, titre=None, texte=None):
    if couleurs is None:
        couleurs = [COULEUR_EQUIPE.get(n, D1_ROUGE) for n in noms]
    fig = go.Figure()
    for nom, val, coul in zip(noms, vals, couleurs):
        fig.add_trace(go.Bar(x=[val], y=[nom], orientation="h",
                             marker_color=coul, text=[texte[noms.index(nom)] if texte else val],
                             textposition="auto", showlegend=False, name=nom))
    fig.update_yaxes(autorange="reversed")
    return style_fig(fig, h, titre)


def barv(x, y, couleur=D1_ROUGE, h=300, titre=None, texte=None):
    if isinstance(couleur, list):
        marker = dict(color=couleur)
    else:
        marker = dict(color=couleur)
    fig = go.Figure(go.Bar(x=x, y=y, marker=marker,
                           text=texte if texte else y,
                           textposition="outside"))
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

EQUIPES  = sorted(df["equipe_marque"].dropna().unique().tolist())
JOURNEES = sorted(df["journee"].dropna().unique().tolist())
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
        hist = sorted([(r.journee, r.res_dom) for r in jdom] + [(r.journee, r.res_ext) for r in jext])
        res = [r for _,r in hist]
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
    buts = df_match.sort_values(["periode","minute"])
    sd, se = 0, 0
    evts = []
    for _, b in buts.iterrows():
        if b["equipe_marque"]==dom: sd+=1
        else: se+=1
        evts.append({"minute":b["minute"],"periode":b["periode"],
                     "equipe":b["equipe_marque"],"joueur":b["joueur"],
                     "score_dom":sd,"score_ext":se,
                     "origine":b["origine"] if pd.notna(b["origine"]) else "—"})
    return evts


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    if LOGO_D1.exists():
        st.image(str(LOGO_D1), width=90)
    st.markdown("---")
    page = st.radio("", [
        "🏠 Accueil",
        "🏆 Classement",
        "⚽ Fiche match",
        "👟 Classement buteurs",
        "⏱ Profil temporel",
        "📊 Dynamique de score",
        "🛡 Vue équipe",
        "🎯 Tactique / Origines",
        "⚔ Confrontations",
    ], label_visibility="collapsed")
    page = page.split(" ",1)[-1].strip()
    st.markdown("---")
    st.caption(f"{len(df)} buts · {len(EQUIPES)} équipes · J{min(JOURNEES)}–J{max(JOURNEES)}")


# ============================================================================
# PDF
# ============================================================================
def pdf_tableau(titre, sous_titre, df_tab, note=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    rouge = colors.HexColor(D1_ROUGE)
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
    t = Table(data, repeatRows=1)
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
    c1.metric("Buts", len(df))
    c2.metric("Matchs", nb_matchs)
    c3.metric("Moy. buts/match", f"{moy:.1f}")
    c4.metric("Top buteur", f"{top_but.max()} buts", top_but.idxmax())
    c5.metric("Meilleure attaque", f"{top_att.max()} buts", top_att.idxmax().split()[0])

    st.markdown("### Buts par journée")
    parj = df.groupby("journee").size().reindex(JOURNEES, fill_value=0)
    fig = go.Figure(go.Bar(x=[f"J{j}" for j in parj.index], y=parj.values,
                           marker_color=D1_ROUGE, text=parj.values, textposition="outside"))
    st.plotly_chart(style_fig(fig, 260), use_container_width=True)

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buts marqués par équipe")
        vals = df["equipe_marque"].value_counts()
        noms = vals.index.tolist()
        st.plotly_chart(barh(noms, vals.values,
                             couleurs=[COULEUR_EQUIPE.get(n,D1_ROUGE) for n in noms],
                             h=max(300,30*len(noms)), texte=list(vals.values)),
                        use_container_width=True)
    with cd:
        st.markdown("### Buts encaissés par équipe")
        vals2 = df["equipe_encaisse"].value_counts()
        noms2 = vals2.index.tolist()
        st.plotly_chart(barh(noms2, vals2.values,
                             couleurs=[hex_to_rgba(COULEUR_EQUIPE.get(n,D1_ROUGE),0.7) for n in noms2],
                             h=max(300,30*len(noms2)), texte=list(vals2.values)),
                        use_container_width=True)

    st.markdown("### Répartition 1re / 2e période")
    p1 = int((df["periode"]==1).sum()); p2 = int((df["periode"]==2).sum())
    fig2 = go.Figure(go.Bar(
        x=["1re période","2e période"], y=[p1,p2],
        marker_color=[D1_ROUGE, D1_BORDEAUX_2],
        text=[f"{p1} ({p1/(p1+p2)*100:.0f}%)", f"{p2} ({p2/(p1+p2)*100:.0f}%)"],
        textposition="outside", width=[0.4,0.4]
    ))
    fig2.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig2, 260), use_container_width=True)


# ============================================================================
# PAGE — CLASSEMENT
# ============================================================================
elif page == "Classement":
    st.title("Classement D1 Futsal")
    clt = construire_classement()

    # Header colonnes
    st.markdown(
        f'<div class="clt-header">'
        f'<span style="width:22px;flex-shrink:0">#</span>'
        f'<span style="width:32px;flex-shrink:0"></span>'
        f'<span style="flex:1">Équipe</span>'
        f'<span style="width:36px;text-align:center;flex-shrink:0">Pts</span>'
        f'<span style="width:90px;text-align:center;flex-shrink:0">V / N / D</span>'
        f'<span style="width:70px;text-align:center;flex-shrink:0">BP — BC</span>'
        f'<span style="width:42px;text-align:center;flex-shrink:0">Diff</span>'
        f'<span style="width:115px;text-align:right;flex-shrink:0">Forme</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    for i, row in clt.iterrows():
        rang = i+1
        is_top3 = rang <= 3
        coul_eq = COULEUR_EQUIPE.get(row["equipe"], D1_ROUGE)
        lg = logo_b64(row["equipe"], 28)
        forme = forme_ronds(row["forme"])
        diff_color = D1_VERT if row["Diff"]>0 else(D1_ROUGE if row["Diff"]<0 else D1_GRIS)
        diff_txt = f'+{row["Diff"]}' if row["Diff"]>0 else str(row["Diff"])
        bg = f"rgba({','.join(str(int(c,16)) for c in [coul_eq.lstrip('#')[i:i+2] for i in (0,2,4)])},0.07)" if is_top3 else "rgba(255,255,255,.02)"
        border_left = f"border-left:3px solid {coul_eq}" if is_top3 else "border-left:3px solid transparent"

        st.markdown(
            f'<div class="clt-row" style="background:{bg};{border_left}">'
            f'<span class="clt-rang {"or" if is_top3 else ""}">{rang}</span>'
            f'<span style="width:28px;flex-shrink:0">{lg}</span>'
            f'<span class="clt-nom" title="{row["equipe"]}">{row["equipe"]}</span>'
            f'<span class="clt-pts">{int(row["Pts"])}</span>'
            f'<span class="clt-vnpd">{int(row["V"])}V {int(row["N"])}N {int(row["D"])}D</span>'
            f'<span class="clt-buts">{int(row["BP"])} — {int(row["BC"])}</span>'
            f'<span class="clt-diff" style="color:{diff_color}">{diff_txt}</span>'
            f'<span class="clt-forme">{forme}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<p class='note' style='margin-top:.6rem'>Forme 5 derniers matchs</p>",
                unsafe_allow_html=True)

    # Export
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
    clt_order = clt["equipe"].tolist()
    fig = go.Figure()
    for eq in clt_order:
        sub = evo[evo["equipe"]==eq].sort_values("journee")
        coul = COULEUR_EQUIPE.get(eq, D1_ROUGE)
        fig.add_trace(go.Scatter(
            x=sub["journee"], y=sub["pts"],
            mode="lines+markers", name=eq.split()[0],
            line=dict(color=coul, width=2.5), marker=dict(size=4),
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

    # Header match
    r_dom = m_row["res_dom"]; r_ext = m_row["res_ext"]
    c_r_dom = D1_VERT if r_dom=="V" else(D1_OR if r_dom=="N" else D1_ROUGE)
    c_r_ext = D1_VERT if r_ext=="V" else(D1_OR if r_ext=="N" else D1_ROUGE)
    lg_dom = logo_b64(dom, 52); lg_ext = logo_b64(ext, 52)

    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:14px;'
        f'padding:1.2rem;text-align:center;margin-bottom:1rem">'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:2.5rem">'
        f'<div style="flex:1;text-align:right">'
        f'<div style="font-weight:700;font-size:.95rem;margin-bottom:.4rem">{dom}</div>{lg_dom}'
        f'</div>'
        f'<div style="padding:0 1rem">'
        f'<div style="font-size:2.6rem;font-weight:900;letter-spacing:.15rem">'
        f'<span style="color:{c_r_dom}">{score_dom}</span>'
        f'<span style="color:{D1_GRIS}"> — </span>'
        f'<span style="color:{c_r_ext}">{score_ext}</span>'
        f'</div>'
        f'<div style="color:{D1_GRIS};font-size:.8rem">Journée {j_sel}</div>'
        f'</div>'
        f'<div style="flex:1;text-align:left">'
        f'{lg_ext}<div style="font-weight:700;font-size:.95rem;margin-top:.4rem">{ext}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    df_match = df[
        (df["journee"]==j_sel) &
        (df["equipe_domicile"]==dom) &
        (df["equipe_exterieure"]==ext)
    ]
    events = reconstruire_score(df_match, dom, ext)

    # Courbe momentum
    st.markdown("### Momentum du match")
    # axe X = minute ajustée (P2 : +20)
    xs = [0]+[e["minute"]+(20 if e["periode"]==2 else 0) for e in events]+[40]
    yd = [0]+[e["score_dom"] for e in events]+[events[-1]["score_dom"] if events else 0]
    ye = [0]+[e["score_ext"] for e in events]+[events[-1]["score_ext"] if events else 0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=yd, mode="lines", name=dom.split()[0],
        line=dict(color=coul_dom, width=3),
        fill="tozeroy", fillcolor=hex_to_rgba(coul_dom, 0.25),
        hovertemplate=f"<b>{dom.split()[0]}</b> %{{y}}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=ye, mode="lines", name=ext.split()[0],
        line=dict(color=coul_ext, width=3),
        fill="tozeroy", fillcolor=hex_to_rgba(coul_ext, 0.25),
        hovertemplate=f"<b>{ext.split()[0]}</b> %{{y}}<extra></extra>"
    ))
    fig.add_vline(x=20, line_dash="dot", line_color=D1_GRIS, line_width=1.2,
                  annotation_text="Mi-temps", annotation_font_color=D1_GRIS,
                  annotation_position="top")
    fig.update_xaxes(title="Minute", tickvals=[0,5,10,15,20,25,30,35,40],
                     ticktext=["0'","5'","10'","15'","20'","25'","30'","35'","40'"])
    fig.update_yaxes(title="Score", dtick=1)
    st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    # Chronologie
    st.markdown("### Chronologie des buts")
    for e in events:
        is_dom = e["equipe"]==dom
        coul = coul_dom if is_dom else coul_ext
        per = "1P" if e["periode"]==1 else "2P"
        score_txt = f'{e["score_dom"]} — {e["score_ext"]}'
        orig = f' <span style="color:{D1_GRIS};font-size:.76rem">· {e["origine"]}</span>' if e["origine"]!="—" else ""
        lg = logo_b64(e["equipe"], 20)
        align = "flex-start" if is_dom else "flex-end"
        st.markdown(
            f'<div style="display:flex;justify-content:{align};margin:.2rem 0">'
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-left:3px solid {coul};border-radius:8px;padding:.35rem .75rem;max-width:54%">'
            f'{lg} <b style="font-size:.88rem">{e["joueur"]}</b>'
            f'<span style="color:{D1_GRIS};font-size:.78rem"> {per} {e["minute"]}\' </span>'
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
        for j,n in buts_dom["joueur"].value_counts().items():
            st.markdown(f'{"⚽"*n} **{j}** ({n})')
    with cd:
        st.markdown(f"**{ext.split()[0]}**")
        for j,n in buts_ext["joueur"].value_counts().items():
            st.markdown(f'{"⚽"*n} **{j}** ({n})')


# ============================================================================
# PAGE — CLASSEMENT BUTEURS
# ============================================================================
elif page == "Classement buteurs":
    st.title("Classement des buteurs")
    eq = st.selectbox("Filtrer par équipe", ["Toutes"]+EQUIPES)
    d = df if eq=="Toutes" else df[df["equipe_marque"]==eq]
    clt = (d.groupby("joueur")
             .agg(buts=("but_id","count"),
                  equipe=("equipe_marque",lambda s: s.mode().iloc[0]))
             .reset_index().sort_values("buts",ascending=False).reset_index(drop=True))
    clt.index += 1

    if len(clt)>=3:
        p = clt.head(3); cols=st.columns(3); medals=["🥇","🥈","🥉"]
        for i,(col,(_,row)) in enumerate(zip(cols,p.iterrows())):
            lg=logo_b64(row["equipe"],38)
            col.markdown(
                f'<div class="pod">'
                f'<div style="font-size:1.6rem">{medals[i]}</div>{lg}<br>'
                f'<div style="font-weight:700;margin-top:.4rem;font-size:.92rem">{row["joueur"]}</div>'
                f'<div class="note">{row["equipe"]}</div>'
                f'<div style="color:{COULEUR_EQUIPE.get(row["equipe"],D1_ROUGE)};font-size:1.3rem;font-weight:800;margin-top:.3rem">{row["buts"]} buts</div>'
                f'</div>',unsafe_allow_html=True)
        st.markdown("")

    aff = clt.rename(columns={"joueur":"Joueur","buts":"Buts","equipe":"Équipe"})[["Joueur","Équipe","Buts"]]
    st.dataframe(aff,use_container_width=True,height=420)
    c1,c2=st.columns(2)
    with c1: dl_csv(aff,"⬇ CSV",f"buteurs.csv")
    with c2:
        st.download_button("⬇ PDF",pdf_tableau("Classement des buteurs",f"D1 Futsal",aff.head(40)),
                           file_name="buteurs.pdf",mime="application/pdf")

    st.markdown("### Profil d'un buteur")
    j=st.selectbox("Buteur",clt["joueur"].tolist())
    dj=df[df["joueur"]==j]
    a,b,c,d2=st.columns(4)
    a.metric("Buts",len(dj)); b.metric("1re période",int((dj["periode"]==1).sum()))
    c.metric("2e période",int((dj["periode"]==2).sum()))
    d2.metric("Adversaires différents",dj["equipe_encaisse"].nunique())
    sit=dj["situation"].value_counts()
    if not sit.empty:
        fig=go.Figure(go.Bar(x=sit.index,y=sit.values,
                             marker_color=[D1_VERT if s=="Menant" else(D1_OR if s=="Égalité" else D1_ROUGE) for s in sit.index],
                             text=sit.values,textposition="outside"))
        st.plotly_chart(style_fig(fig,240,"Situation au moment des buts"),use_container_width=True)


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
    fig=go.Figure(go.Bar(x=[f"{m}'" for m in serie.index],y=serie.values,marker_color=coul_b))
    fig.add_vline(x="20'→21'",line_dash="dot",line_color=D1_GRIS,line_width=1,
                  annotation_text="Mi-temps",annotation_font_color=D1_GRIS)
    st.plotly_chart(style_fig(fig,300),use_container_width=True)
    st.markdown("<p class='note'>Rouge = 1re période · Bordeaux = 2e période</p>",unsafe_allow_html=True)

    st.markdown("### Buts par tranche de 5 minutes")
    tr=pd.cut(mins,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    coul_q=[D1_ROUGE if i<4 else D1_BORDEAUX_2 for i in range(8)]
    fig2=go.Figure(go.Bar(x=tr.index.astype(str),y=tr.values,marker_color=coul_q,
                          text=tr.values,textposition="outside"))
    st.plotly_chart(style_fig(fig2,280),use_container_width=True)


# ============================================================================
# PAGE — DYNAMIQUE DE SCORE
# ============================================================================
elif page == "Dynamique de score":
    st.title("Dynamique de score")
    st.markdown("<p class='note'>Situation de l'équipe qui marque, juste avant son but.</p>",
                unsafe_allow_html=True)
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
                         text=[f"{v} ({v/tot*100:.0f}%)" for v in sit.values],
                         textposition="outside",width=[0.4,0.4,0.4]))
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(style_fig(fig,280),use_container_width=True)

    if eq=="Tout le championnat":
        st.markdown("### Comparaison par équipe — buts selon situation de score")
        rows=[]
        for e in EQUIPES:
            de=df[(df["equipe_marque"]==e)&(df["situation"].notna())]
            if len(de):
                rows.append({
                    "Équipe":e,
                    "Menant":int((de["situation"]=="Menant").sum()),
                    "Égalité":int((de["situation"]=="Égalité").sum()),
                    "Mené":int((de["situation"]=="Mené").sum()),
                    "pct_mené":(de["situation"]=="Mené").mean()*100,
                    "pct_egal":(de["situation"]=="Égalité").mean()*100,
                    "pct_men":(de["situation"]=="Menant").mean()*100,
                })
        comp=pd.DataFrame(rows).sort_values("pct_mené",ascending=False)

        # 3 graphes côte à côte
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("#### En étant mené")
            fig_m=go.Figure(go.Bar(
                x=comp["pct_mené"].round(0),y=comp["Équipe"],orientation="h",
                marker_color=D1_ROUGE,text=[f"{v:.0f}%" for v in comp["pct_mené"]],
                textposition="auto"))
            fig_m.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_m,max(300,30*len(comp))),use_container_width=True)
        with c2:
            st.markdown("#### À égalité")
            comp2=comp.sort_values("pct_egal",ascending=False)
            fig_e=go.Figure(go.Bar(
                x=comp2["pct_egal"].round(0),y=comp2["Équipe"],orientation="h",
                marker_color=D1_OR,text=[f"{v:.0f}%" for v in comp2["pct_egal"]],
                textposition="auto"))
            fig_e.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_e,max(300,30*len(comp2))),use_container_width=True)
        with c3:
            st.markdown("#### En menant")
            comp3=comp.sort_values("pct_men",ascending=False)
            fig_v=go.Figure(go.Bar(
                x=comp3["pct_men"].round(0),y=comp3["Équipe"],orientation="h",
                marker_color=D1_VERT,text=[f"{v:.0f}%" for v in comp3["pct_men"]],
                textposition="auto"))
            fig_v.update_yaxes(autorange="reversed")
            st.plotly_chart(style_fig(fig_v,max(300,30*len(comp3))),use_container_width=True)


# ============================================================================
# PAGE — VUE ÉQUIPE
# ============================================================================
elif page == "Vue équipe":
    st.title("Fiche équipe")
    eq=st.selectbox("Équipe",EQUIPES)
    clt=construire_classement()
    rang_row=clt[clt["equipe"]==eq].iloc[0]
    rang=clt[clt["equipe"]==eq].index[0]+1
    coul=COULEUR_EQUIPE.get(eq,D1_ROUGE)
    lg=logo_b64(eq,50)

    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
        f'border-left:4px solid {coul};border-radius:12px;padding:1rem 1.2rem;'
        f'display:flex;align-items:center;gap:1rem;margin-bottom:1rem">'
        f'{lg}'
        f'<div><div style="font-size:1.1rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.82rem">'
        f'Rang <b style="color:{coul}">{rang}</b> · {int(rang_row["Pts"])} pts · '
        f'{int(rang_row["V"])}V {int(rang_row["N"])}N {int(rang_row["D"])}D</div>'
        f'<div style="margin-top:.3rem">{forme_ronds(rang_row["forme"])}</div>'
        f'</div></div>',
        unsafe_allow_html=True
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
                             marker_color=coul,text=bb.values,textposition="auto"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig,max(260,26*len(bb))),use_container_width=True)
    with cd:
        st.markdown("### Quand l'équipe marque")
        mins=dpour["minute"].dropna().astype(int)
        tr=pd.cut(mins,bins=range(0,41,5),labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
        fig2=go.Figure(go.Bar(x=tr.index.astype(str),y=tr.values,
                              marker_color=coul,text=tr.values,textposition="outside"))
        st.plotly_chart(style_fig(fig2,280),use_container_width=True)

    if eq in EQUIPES_AVEC_ORIGINE:
        st.markdown("### Origine des buts")
        oo=dpour.loc[dpour["origine"].notna(),"origine"].value_counts()
        n_r=int(dpour["origine"].notna().sum())
        st.markdown(f'<span style="background:{coul};color:white;padding:.15rem .6rem;'
                    f'border-radius:5px;font-weight:600;font-size:.78rem">'
                    f'{n_r}/{len(dpour)} buts analysés</span>',unsafe_allow_html=True)
        fig3=go.Figure(go.Bar(x=oo.values,y=oo.index,orientation="h",
                              marker_color=coul,text=oo.values,textposition="auto"))
        fig3.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig3,max(240,30*len(oo))),use_container_width=True)
    else:
        st.info("Origine des buts pas encore renseignée pour cette équipe.")


# ============================================================================
# PAGE — TACTIQUE / ORIGINES
# ============================================================================
elif page == "Tactique / Origines":
    st.title("Tactique — Origine des buts")
    if not EQUIPES_AVEC_ORIGINE:
        st.info("Aucune origine renseignée pour le moment."); st.stop()
    st.markdown(f"<p class='note'>Données : {', '.join(EQUIPES_AVEC_ORIGINE)}</p>",unsafe_allow_html=True)
    do=df[df["origine"].notna()]

    st.markdown("### Répartition globale")
    glob=do["origine"].value_counts()
    fig=go.Figure(go.Bar(x=glob.values,y=glob.index,orientation="h",
                         marker_color=D1_ROUGE,text=glob.values,textposition="auto"))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig,max(280,32*len(glob))),use_container_width=True)

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
        st.plotly_chart(style_fig(fig2,400),use_container_width=True)
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
    if e1==e2:
        st.warning("Choisis deux équipes différentes."); st.stop()

    masque=(
        ((df["equipe_marque"]==e1)&(df["equipe_encaisse"]==e2))|
        ((df["equipe_marque"]==e2)&(df["equipe_encaisse"]==e1))
    )
    d=df[masque]
    if d.empty:
        st.info("Aucun but recensé entre ces deux équipes."); st.stop()

    matchs_h2h = construire_matchs()
    matchs_h2h = matchs_h2h[
        ((matchs_h2h["dom"]==e1)&(matchs_h2h["ext"]==e2))|
        ((matchs_h2h["dom"]==e2)&(matchs_h2h["ext"]==e1))
    ]

    b1=int((d["equipe_marque"]==e1).sum()); b2=int((d["equipe_marque"]==e2).sum())
    v1=int(((matchs_h2h["dom"]==e1)&(matchs_h2h["res_dom"]=="V")).sum())+\
       int(((matchs_h2h["ext"]==e1)&(matchs_h2h["res_ext"]=="V")).sum())
    v2=int(((matchs_h2h["dom"]==e2)&(matchs_h2h["res_dom"]=="V")).sum())+\
       int(((matchs_h2h["ext"]==e2)&(matchs_h2h["res_ext"]=="V")).sum())
    nb_nuls=int(len(matchs_h2h))-v1-v2
    coul1=COULEUR_EQUIPE.get(e1,D1_ROUGE); coul2=COULEUR_EQUIPE.get(e2,D1_BLEU)
    lg1=logo_b64(e1,44); lg2=logo_b64(e2,44)

    # Fiche h2h visuelle
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:14px;'
        f'padding:1.2rem;margin-bottom:1rem">'
        f'<div style="display:flex;align-items:center;justify-content:space-between">'
        f'<div style="flex:1;text-align:center">'
        f'{lg1}<br><b style="font-size:.9rem">{e1.split()[0]}</b>'
        f'<div style="color:{coul1};font-size:2rem;font-weight:900;margin-top:.3rem">{b1}</div>'
        f'<div style="color:{D1_GRIS};font-size:.78rem">{v1} victoire{"s" if v1>1 else ""}</div>'
        f'</div>'
        f'<div style="text-align:center;padding:0 1.5rem">'
        f'<div style="color:{D1_GRIS};font-size:.78rem;margin-bottom:.3rem">{len(matchs_h2h)} rencontre{"s" if len(matchs_h2h)>1 else ""}</div>'
        f'<div style="font-size:1.3rem;font-weight:700;color:{D1_GRIS}">VS</div>'
        f'<div style="color:{D1_GRIS};font-size:.78rem;margin-top:.3rem">{nb_nuls} nul{"s" if nb_nuls>1 else ""}</div>'
        f'</div>'
        f'<div style="flex:1;text-align:center">'
        f'{lg2}<br><b style="font-size:.9rem">{e2.split()[0]}</b>'
        f'<div style="color:{coul2};font-size:2rem;font-weight:900;margin-top:.3rem">{b2}</div>'
        f'<div style="color:{D1_GRIS};font-size:.78rem">{v2} victoire{"s" if v2>1 else ""}</div>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Barre comparaison buts
    tot_b=b1+b2 or 1
    pct1=b1/tot_b*100; pct2=b2/tot_b*100
    st.markdown(
        f'<div style="margin:.5rem 0">'
        f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden">'
        f'<div style="width:{pct1:.1f}%;background:{coul1}"></div>'
        f'<div style="width:{pct2:.1f}%;background:{coul2}"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.78rem;color:{D1_GRIS};margin-top:.2rem">'
        f'<span>{pct1:.0f}% des buts</span><span>{pct2:.0f}% des buts</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Résultats des rencontres
    if len(matchs_h2h):
        st.markdown("### Résultats des rencontres")
        for _,m in matchs_h2h.sort_values("journee").iterrows():
            res_dom=m["res_dom"]
            bc_dom=D1_VERT if res_dom=="V" else(D1_OR if res_dom=="N" else D1_ROUGE)
            bc_ext=D1_VERT if res_dom=="D" else(D1_OR if res_dom=="N" else D1_ROUGE)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:1rem;padding:.3rem .6rem;'
                f'background:{D1_CARTE};border-radius:8px;margin:.2rem 0;font-size:.88rem">'
                f'<span style="color:{D1_GRIS};width:50px">J{int(m["journee"])}</span>'
                f'<span style="flex:1;text-align:right;font-weight:600">{m["dom"]}</span>'
                f'<span style="font-weight:800;padding:0 .8rem;font-size:1rem">'
                f'<span style="color:{bc_dom}">{m["score_dom"]}</span>'
                f'<span style="color:{D1_GRIS}"> — </span>'
                f'<span style="color:{bc_ext}">{m["score_ext"]}</span>'
                f'</span>'
                f'<span style="flex:1;font-weight:600">{m["ext"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("### Détail des buts")
    det=(d.sort_values(["journee","periode","minute"])
         [["journee","equipe_marque","joueur","periode","minute","situation","origine"]]
         .rename(columns={"journee":"J","equipe_marque":"Marque","joueur":"Buteur",
                          "periode":"Pér.","minute":"Min","situation":"Situation","origine":"Origine"}))
    det["Origine"]=det["Origine"].fillna("—")
    st.dataframe(det,use_container_width=True,height=340)
    dl_csv(det,"⬇ CSV",f"h2h_{e1[:6]}_{e2[:6]}.csv")
