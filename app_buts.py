"""
================================================================================
ANALYSE DES BUTS — D1 FUTSAL   (v2 — Livraison 1)
================================================================================
Blocs :
  1 - Logos + ergonomie générale
  2 - Classement reconstitué + évolution journée par journée
  3 - Fiche match (momentum, chronologie, buts par buteur)
  + pages existantes améliorées
================================================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px
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
# CONFIG
# ============================================================================
DB_PATH    = "futsal_d1.db"
LOGO_D1    = Path("D1_Futsal_logo.png")
LOGOS_DIR  = Path("logos")

D1_ROUGE       = "#C00018"
D1_ROUGE_CLAIR = "#E11030"
D1_BORDEAUX    = "#540C18"
D1_BORDEAUX_2  = "#6C1420"
D1_ANTHRACITE  = "#1A1A1E"
D1_CARTE       = "#26181C"
D1_BLANC       = "#F5F2F3"
D1_GRIS        = "#9A8E91"
D1_OR          = "#C9A24B"
D1_VERT        = "#2E8B57"
D1_BLEU        = "#3A7BD5"

PALETTE = [D1_ROUGE, "#E0762A", D1_OR, D1_BLEU, "#7BA05B",
           "#8E6FB0", "#C8607A", D1_GRIS, "#4B9E8E", "#B5563C", "#5A8FB5"]

COULEUR_EQUIPE = {
    "ETOILE LAVALLOISE FC":  "#FFA500",
    "SPORTING CLUB PARIS":   "#003399",
    "MONTPELLIER MED. F.":   "#0066CC",
    "TOULON METROPOLE F.":   "#CC0000",
    "GOAL FUTSAL CLUB":      "#006400",
    "NANTES METROPOLE F.":   "#FFCC00",
    "PARIS ACASA":           "#8B0000",
    "AS AVION FUTSAL":       "#4169E1",
    "UJS TOULOUSE":          "#9932CC",
    "NICE FUTSAL CLUB":      "#CC0033",
    "FC KINGERSHEIM":        "#FF6600",
}

st.set_page_config(
    page_title="D1 Futsal — Analyse des buts",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLE
# ============================================================================
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
.stApp {{ background:{D1_ANTHRACITE}; }}
html,body,[class*="css"],.stMarkdown,.stMetric,button,input,select,textarea{{
    font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;
}}
.block-container{{padding-top:1.2rem;padding-bottom:2rem;max-width:1400px}}
h1{{color:{D1_BLANC}!important;border-bottom:3px solid {D1_ROUGE};
    padding-bottom:.3rem;letter-spacing:-.5px;font-size:1.85rem!important;margin-bottom:1.2rem!important}}
h2,h3{{color:{D1_ROUGE_CLAIR}!important;letter-spacing:-.3px}}
h3{{font-size:1.05rem!important;margin-top:1.2rem!important;margin-bottom:.4rem!important}}
p,label,span,div{{color:{D1_BLANC}}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,{D1_BORDEAUX} 0%,#3A0C14 100%);border-right:1px solid {D1_BORDEAUX_2}}}
[data-testid="stSidebar"] *{{color:{D1_BLANC}!important}}
[data-testid="stSidebar"] .stRadio label{{
    background:rgba(255,255,255,.06);border-radius:8px;padding:.4rem .8rem;
    margin:.15rem 0;display:block;transition:background .15s;font-weight:500
}}
[data-testid="stSidebar"] .stRadio label:hover{{background:rgba(192,0,24,.25)}}
[data-testid="stMetric"]{{
    background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};
    border-radius:14px;padding:.9rem 1.1rem;transition:transform .15s
}}
[data-testid="stMetric"]:hover{{transform:translateY(-2px)}}
[data-testid="stMetricValue"]{{font-size:1.75rem;font-weight:800;color:{D1_BLANC}}}
[data-testid="stMetricLabel"]{{font-size:.78rem;color:{D1_GRIS};font-weight:500;text-transform:uppercase;letter-spacing:.5px}}
[data-testid="stMetricDelta"]{{font-size:.9rem}}
.stDataFrame{{border-radius:12px;overflow:hidden}}
.stSelectbox>div>div,.stMultiSelect>div>div{{
    background:{D1_CARTE}!important;border:1px solid {D1_BORDEAUX_2}!important;border-radius:8px!important
}}
div[data-baseweb="select"] *{{color:{D1_BLANC}!important}}
.stDownloadButton>button{{
    background:{D1_ROUGE}!important;color:white!important;border:none!important;
    border-radius:8px!important;font-weight:600!important;padding:.4rem 1rem!important
}}
.stDownloadButton>button:hover{{background:{D1_ROUGE_CLAIR}!important}}

/* Cartes custom */
.card{{background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:14px;padding:1rem 1.2rem;margin-bottom:.8rem}}
.card-titre{{font-size:.75rem;font-weight:600;color:{D1_GRIS};text-transform:uppercase;letter-spacing:.6px;margin-bottom:.3rem}}
.card-val{{font-size:1.6rem;font-weight:800;color:{D1_BLANC}}}
.card-sub{{font-size:.82rem;color:{D1_GRIS};margin-top:.15rem}}

/* Badge forme */
.badge-V{{display:inline-flex;align-items:center;justify-content:center;
    width:22px;height:22px;border-radius:50%;background:{D1_VERT};
    color:white;font-weight:700;font-size:.72rem;margin:1px}}
.badge-N{{display:inline-flex;align-items:center;justify-content:center;
    width:22px;height:22px;border-radius:50%;background:{D1_OR};
    color:#1A1A1E;font-weight:700;font-size:.72rem;margin:1px}}
.badge-D{{display:inline-flex;align-items:center;justify-content:center;
    width:22px;height:22px;border-radius:50%;background:{D1_ROUGE};
    color:white;font-weight:700;font-size:.72rem;margin:1px}}

/* Séparateur */
.sep{{border:none;border-top:1px solid {D1_BORDEAUX_2};margin:1rem 0}}

/* Note */
.note{{color:{D1_GRIS};font-size:.8rem;font-style:italic}}

/* Podium */
.podium{{background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:14px;
    padding:1.1rem;text-align:center;transition:transform .15s}}
.podium:hover{{transform:translateY(-3px)}}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPERS
# ============================================================================
def logo_eq(nom, width=36):
    """Affiche le logo d'une équipe (ou initiales si absent)."""
    p = LOGOS_DIR / f"{nom}.png"
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
            buf = BytesIO(); img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f'<img src="data:image/png;base64,{b64}" width="{width}" height="{width}" style="border-radius:4px;object-fit:contain;vertical-align:middle">'
        except Exception:
            pass
    coul = COULEUR_EQUIPE.get(nom, D1_ROUGE)
    initiales = "".join(w[0] for w in nom.split()[:2])
    return (f'<div style="width:{width}px;height:{width}px;border-radius:50%;'
            f'background:{coul};display:inline-flex;align-items:center;justify-content:center;'
            f'font-weight:800;font-size:{max(10,width//3)}px;color:white;vertical-align:middle">'
            f'{initiales}</div>')


def logo_path(nom):
    p = LOGOS_DIR / f"{nom}.png"
    return str(p) if p.exists() else None


def style_fig(fig, h=360, titre=None):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=D1_BLANC, size=13),
        height=h, margin=dict(l=10, r=10, t=44 if titre else 18, b=10),
        title=dict(text=titre or "", font=dict(size=14, color=D1_BLANC)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.07)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.07)", zeroline=False)
    return fig


def barre(x, y, couleur=D1_ROUGE, horizontal=False, h=360, titre=None, texte=None):
    if horizontal:
        fig = go.Figure(go.Bar(x=y, y=x, orientation="h",
                               marker_color=couleur, text=texte, textposition="auto"))
        fig.update_yaxes(autorange="reversed")
    else:
        fig = go.Figure(go.Bar(x=x, y=y, marker_color=couleur,
                               text=texte, textposition="outside"))
    return style_fig(fig, h, titre)


def dl_csv(dframe, label, nom):
    st.download_button(label, dframe.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nom, mime="text/csv")


def forme_html(resultats):
    """Liste de 'V','N','D' -> badges HTML."""
    mapping = {"V": "badge-V", "N": "badge-N", "D": "badge-D"}
    return "".join(f'<span class="{mapping.get(r,"badge-D")}">{r}</span>'
                   for r in resultats[-5:])


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
    """Un DataFrame avec un match par ligne + score final."""
    rows = []
    for (j, dom, ext), g in df.groupby(["journee", "equipe_domicile", "equipe_exterieure"]):
        bd = int((g["equipe_marque"] == dom).sum())
        be = int((g["equipe_marque"] == ext).sum())
        rows.append({"journee": j, "dom": dom, "ext": ext,
                     "score_dom": bd, "score_ext": be,
                     "res_dom": "V" if bd > be else ("N" if bd == be else "D"),
                     "res_ext": "D" if bd > be else ("N" if bd == be else "V"),
                     "total_buts": bd + be})
    return pd.DataFrame(rows).sort_values(["journee", "dom"]).reset_index(drop=True)


@st.cache_data
def construire_classement():
    matchs = construire_matchs()
    rows = []
    for eq in EQUIPES:
        m_dom = matchs[matchs["dom"] == eq]
        m_ext = matchs[matchs["ext"] == eq]
        all_res = (list(m_dom["res_dom"]) + list(m_ext["res_ext"]))
        # trier par journée pour la forme
        jdom = list(m_dom[["journee","res_dom"]].sort_values("journee").itertuples(index=False))
        jext = list(m_ext[["journee","res_ext"]].sort_values("journee").itertuples(index=False))
        hist = sorted(
            [(r.journee, r.res_dom) for r in jdom] +
            [(r.journee, r.res_ext) for r in jext]
        )
        resultats_tries = [r for _, r in hist]
        v = all_res.count("V"); n = all_res.count("N"); d = all_res.count("D")
        bp = int(df[df["equipe_marque"] == eq].shape[0])
        bc = int(df[df["equipe_encaisse"] == eq].shape[0])
        rows.append({
            "equipe": eq, "J": len(all_res), "V": v, "N": n, "D": d,
            "Pts": 3*v + n, "BP": bp, "BC": bc, "Diff": bp - bc,
            "forme": resultats_tries,
        })
    return pd.DataFrame(rows).sort_values("Pts", ascending=False).reset_index(drop=True)


@st.cache_data
def evolution_classement():
    """Points cumulés journée par journée, par équipe."""
    matchs = construire_matchs()
    rows = []
    for eq in EQUIPES:
        pts = 0
        for j in JOURNEES:
            mj = matchs[matchs["journee"] == j]
            m_dom = mj[mj["dom"] == eq]
            m_ext = mj[mj["ext"] == eq]
            for _, m in m_dom.iterrows():
                pts += 3 if m["res_dom"] == "V" else (1 if m["res_dom"] == "N" else 0)
            for _, m in m_ext.iterrows():
                pts += 3 if m["res_ext"] == "V" else (1 if m["res_ext"] == "N" else 0)
            rows.append({"equipe": eq, "journee": j, "pts_cumules": pts})
    return pd.DataFrame(rows)


@st.cache_data
def buts_equipe_par_journee():
    """Buts marqués et encaissés par équipe par journée."""
    rows = []
    for j in JOURNEES:
        dj = df[df["journee"] == j]
        for eq in EQUIPES:
            rows.append({
                "journee": j, "equipe": eq,
                "pour": int((dj["equipe_marque"] == eq).sum()),
                "contre": int((dj["equipe_encaisse"] == eq).sum()),
            })
    return pd.DataFrame(rows)


def reconstruire_score(df_match, dom, ext):
    """
    Renvoie une liste d'événements triés avec le score courant :
    [(minute, periode, equipe, joueur, score_dom, score_ext), ...]
    """
    buts_tries = df_match.sort_values(["periode", "minute"])
    score_dom, score_ext = 0, 0
    events = []
    for _, b in buts_tries.iterrows():
        if b["equipe_marque"] == dom:
            score_dom += 1
        else:
            score_ext += 1
        events.append({
            "minute": b["minute"], "periode": b["periode"],
            "equipe": b["equipe_marque"], "joueur": b["joueur"],
            "score_dom": score_dom, "score_ext": score_ext,
            "origine": b["origine"] if pd.notna(b["origine"]) else "—",
        })
    return events


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    if LOGO_D1.exists():
        st.image(str(LOGO_D1), width=110)
    else:
        st.markdown(f"## D1 FUTSAL")
    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠  Accueil",
        "🏆  Classement",
        "⚽  Fiche match",
        "👟  Classement buteurs",
        "⏱️  Profil temporel",
        "📊  Dynamique de score",
        "🛡️  Vue équipe",
        "🎯  Tactique / Origines",
        "⚔️  Confrontations",
    ])
    page = page.split("  ", 1)[-1].strip()
    st.markdown("---")
    st.caption(f"{len(df)} buts · {len(EQUIPES)} équipes · J{min(JOURNEES)}–J{max(JOURNEES)}")


# ============================================================================
# PDF HELPER
# ============================================================================
def pdf_tableau(titre, sous_titre, df_tab, note=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    rouge = colors.HexColor(D1_ROUGE)
    h   = ParagraphStyle("h", parent=styles["Title"], textColor=rouge,
                         fontSize=17, alignment=TA_CENTER, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey,
                         fontSize=10, alignment=TA_CENTER, spaceAfter=14)
    nt  = ParagraphStyle("nt", parent=styles["Normal"], textColor=colors.grey,
                         fontSize=8, alignment=TA_CENTER, spaceBefore=10)
    elems = []
    if LOGO_D1.exists():
        try:
            img = RLImage(str(LOGO_D1), width=2.2*cm, height=2.35*cm)
            img.hAlign = "CENTER"; elems += [img, Spacer(1, 6)]
        except Exception:
            pass
    elems += [Paragraph(titre, h), Paragraph(sous_titre, sub)]
    data = [list(df_tab.columns)] + df_tab.astype(str).values.tolist()
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), rouge),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4ECEE")]),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#D9C7CB")),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems.append(t)
    if note:
        elems.append(Paragraph(note, nt))
    doc.build(elems)
    buf.seek(0)
    return buf


# ============================================================================
# PAGE — ACCUEIL
# ============================================================================
if page == "Accueil":
    st.title("D1 Futsal — Vue d'ensemble")

    matchs = construire_matchs()
    nb_matchs = len(matchs)
    moy = len(df) / nb_matchs if nb_matchs else 0
    top_but = df["joueur"].value_counts()
    top_eq_att = df["equipe_marque"].value_counts()
    top_eq_def = df["equipe_encaisse"].value_counts()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Buts totaux", len(df))
    c2.metric("Matchs", nb_matchs)
    c3.metric("Moy. buts/match", f"{moy:.1f}")
    c4.metric("Top buteur", f"{top_but.max()} buts", top_but.idxmax())
    c5.metric("Meilleure attaque", f"{top_eq_att.max()} buts", top_eq_att.idxmax().split()[0])

    st.markdown("### Buts par journée")
    parj = df.groupby("journee").size().reindex(JOURNEES, fill_value=0)
    coul = [COULEUR_EQUIPE.get(e, D1_ROUGE) for e in [None]*len(parj)]
    fig = go.Figure(go.Bar(x=[f"J{j}" for j in parj.index], y=parj.values,
                           marker_color=D1_ROUGE, text=parj.values, textposition="outside"))
    st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buts marqués")
        vals = df["equipe_marque"].value_counts()
        fig2 = go.Figure()
        for i, (eq, v) in enumerate(vals.items()):
            fig2.add_trace(go.Bar(
                x=[v], y=[eq], orientation="h",
                marker_color=COULEUR_EQUIPE.get(eq, PALETTE[i % len(PALETTE)]),
                text=[v], textposition="auto", showlegend=False,
                name=eq
            ))
        fig2.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig2, max(340, 34*len(vals))), use_container_width=True)
    with cd:
        st.markdown("### Buts encaissés")
        vals2 = df["equipe_encaisse"].value_counts()
        fig3 = go.Figure()
        for i, (eq, v) in enumerate(vals2.items()):
            fig3.add_trace(go.Bar(
                x=[v], y=[eq], orientation="h",
                marker_color=COULEUR_EQUIPE.get(eq, PALETTE[i % len(PALETTE)]),
                text=[v], textposition="auto", showlegend=False,
                opacity=0.6, name=eq
            ))
        fig3.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig3, max(340, 34*len(vals2))), use_container_width=True)

    st.markdown("### Répartition 1re / 2e période")
    p1 = int((df["periode"]==1).sum()); p2 = int((df["periode"]==2).sum())
    fig4 = go.Figure(go.Pie(labels=["1re période","2e période"], values=[p1,p2],
                            marker_colors=[D1_ROUGE, D1_BORDEAUX_2],
                            hole=.45, textinfo="label+percent"))
    st.plotly_chart(style_fig(fig4, 300), use_container_width=True)


# ============================================================================
# PAGE — CLASSEMENT
# ============================================================================
elif page == "Classement":
    st.title("Classement D1 Futsal")
    clt = construire_classement()

    # Tableau avec logos et forme
    st.markdown("### Classement général")
    for i, row in clt.iterrows():
        rang = i + 1
        logo = logo_eq(row["equipe"], 30)
        forme = forme_html(row["forme"])
        trend = row["forme"][-1] if row["forme"] else "—"
        bg = "rgba(192,0,24,.12)" if rang <= 3 else ("rgba(255,255,255,.03)" if rang % 2 == 0 else "rgba(0,0,0,0)")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:.5rem .8rem;'
            f'background:{bg};border-radius:10px;margin:.2rem 0;border:1px solid rgba(255,255,255,.06)">'
            f'<span style="font-size:1rem;font-weight:700;color:{"#C9A24B" if rang<=3 else D1_GRIS};width:24px">{rang}</span>'
            f'{logo}'
            f'<span style="flex:1;font-weight:600;font-size:.9rem">{row["equipe"]}</span>'
            f'<span style="width:40px;text-align:center;font-weight:800;font-size:1.1rem;color:{D1_ROUGE_CLAIR}">{row["Pts"]}</span>'
            f'<span style="width:80px;text-align:center;font-size:.82rem;color:{D1_GRIS}">{row["V"]}V {row["N"]}N {row["D"]}D</span>'
            f'<span style="width:70px;text-align:center;font-size:.82rem">{row["BP"]} — {row["BC"]}</span>'
            f'<span style="width:45px;text-align:center;font-size:.82rem;'
            f'color:{"#2E8B57" if row["Diff"]>0 else (D1_ROUGE if row["Diff"]<0 else D1_GRIS)}">'
            f'{"+" if row["Diff"]>0 else ""}{row["Diff"]}</span>'
            f'<span style="width:120px;text-align:right">{forme}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<p class='note' style='margin-top:.5rem'>Forme sur les 5 derniers matchs. "
                "🟢 V  🟡 N  🔴 D</p>", unsafe_allow_html=True)

    st.markdown("### Évolution du classement (points cumulés)")
    evo = evolution_classement()
    fig = go.Figure()
    for i, eq in enumerate(clt["equipe"].tolist()):
        sub = evo[evo["equipe"] == eq].sort_values("journee")
        coul = COULEUR_EQUIPE.get(eq, PALETTE[i % len(PALETTE)])
        fig.add_trace(go.Scatter(
            x=sub["journee"], y=sub["pts_cumules"],
            mode="lines+markers", name=eq.split()[0],
            line=dict(color=coul, width=2.5),
            marker=dict(size=5),
            hovertemplate=f"<b>{eq}</b><br>J%{{x}} → %{{y}} pts<extra></extra>"
        ))
    fig.update_xaxes(tickvals=JOURNEES, ticktext=[f"J{j}" for j in JOURNEES])
    st.plotly_chart(style_fig(fig, 480, "Points cumulés par journée"), use_container_width=True)

    # Export
    tab_export = clt[["equipe","J","V","N","D","Pts","BP","BC","Diff"]].copy()
    tab_export.columns = ["Équipe","J","V","N","D","Pts","BP","BC","Diff"]
    c1, c2 = st.columns(2)
    with c1:
        dl_csv(tab_export, "⬇ CSV", "classement_d1.csv")
    with c2:
        st.download_button("⬇ PDF",
            pdf_tableau("Classement D1 Futsal", f"Journée {max(JOURNEES)}", tab_export),
            file_name="classement_d1.pdf", mime="application/pdf")


# ============================================================================
# PAGE — FICHE MATCH
# ============================================================================
elif page == "Fiche match":
    st.title("Fiche match")

    matchs = construire_matchs()
    j_sel = st.selectbox("Journée", sorted(matchs["journee"].unique()),
                         format_func=lambda x: f"Journée {x}")
    matchs_j = matchs[matchs["journee"] == j_sel]

    opts = [f"{r.dom}  {r.score_dom} — {r.score_ext}  {r.ext}"
            for r in matchs_j.itertuples()]
    m_sel = st.selectbox("Match", opts)
    idx = opts.index(m_sel)
    m_row = matchs_j.iloc[idx]
    dom, ext = m_row["dom"], m_row["ext"]
    score_dom, score_ext = m_row["score_dom"], m_row["score_ext"]

    # Header match
    l_dom = logo_eq(dom, 56); l_ext = logo_eq(ext, 56)
    coul_res_dom = D1_VERT if m_row["res_dom"]=="V" else (D1_OR if m_row["res_dom"]=="N" else D1_ROUGE)
    coul_res_ext = D1_VERT if m_row["res_ext"]=="V" else (D1_OR if m_row["res_ext"]=="N" else D1_ROUGE)
    st.markdown(
        f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};border-radius:16px;'
        f'padding:1.4rem;text-align:center;margin-bottom:1.2rem">'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:2rem">'
        f'<div style="flex:1;text-align:right">'
        f'<div style="font-weight:700;font-size:1rem;margin-bottom:.4rem">{dom}</div>'
        f'{l_dom}'
        f'</div>'
        f'<div style="text-align:center;padding:0 1rem">'
        f'<div style="font-size:2.8rem;font-weight:900;letter-spacing:.1rem">'
        f'<span style="color:{coul_res_dom}">{score_dom}</span>'
        f'<span style="color:{D1_GRIS}"> — </span>'
        f'<span style="color:{coul_res_ext}">{score_ext}</span>'
        f'</div>'
        f'<div style="color:{D1_GRIS};font-size:.82rem;margin-top:.3rem">Journée {j_sel}</div>'
        f'</div>'
        f'<div style="flex:1;text-align:left">'
        f'{l_ext}'
        f'<div style="font-weight:700;font-size:1rem;margin-top:.4rem">{ext}</div>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    df_match = df[
        (df["journee"] == j_sel) &
        (df["equipe_domicile"] == dom) &
        (df["equipe_exterieure"] == ext)
    ]
    events = reconstruire_score(df_match, dom, ext)

    # Courbe momentum
    st.markdown("### Momentum du match")
    minutes_x = [0] + [e["minute"] + (20 if e["periode"] == 2 else 0) for e in events] + [40]
    dom_y = [0]; ext_y = [0]
    for e in events:
        dom_y.append(e["score_dom"]); ext_y.append(e["score_ext"])
    dom_y.append(dom_y[-1]); ext_y.append(ext_y[-1])

    fig = go.Figure()
    coul_dom = COULEUR_EQUIPE.get(dom, D1_ROUGE)
    coul_ext = COULEUR_EQUIPE.get(ext, D1_BLEU)
    fig.add_trace(go.Scatter(x=minutes_x, y=dom_y, mode="lines",
                             name=dom.split()[0], line=dict(color=coul_dom, width=3),
                             fill="tozeroy", fillcolor=f"rgba{tuple(list(bytes.fromhex(coul_dom.lstrip('#'))) + [40])}"))
    fig.add_trace(go.Scatter(x=minutes_x, y=ext_y, mode="lines",
                             name=ext.split()[0], line=dict(color=coul_ext, width=3),
                             fill="tozeroy", fillcolor=f"rgba{tuple(list(bytes.fromhex(coul_ext.lstrip('#'))) + [40])}"))
    fig.add_vline(x=20, line_dash="dot", line_color=D1_GRIS, line_width=1,
                  annotation_text="Mi-temps", annotation_font_color=D1_GRIS)
    fig.update_xaxes(title="Minute", tickvals=[0,5,10,15,20,25,30,35,40],
                     ticktext=["0'","5'","10'","15'","20'→MT","25'","30'","35'","40'"])
    fig.update_yaxes(title="Score", dtick=1)
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    # Chronologie
    st.markdown("### Chronologie des buts")
    for e in events:
        min_aff = e["minute"]
        per = "1P" if e["periode"] == 1 else "2P"
        is_dom = e["equipe"] == dom
        coul = COULEUR_EQUIPE.get(e["equipe"], D1_ROUGE)
        score_txt = f'{e["score_dom"]} — {e["score_ext"]}'
        orig = f' · <span style="color:{D1_GRIS};font-size:.78rem">{e["origine"]}</span>' if e["origine"] != "—" else ""
        logo = logo_eq(e["equipe"], 22)
        align = "flex-start" if is_dom else "flex-end"
        st.markdown(
            f'<div style="display:flex;justify-content:{align};margin:.25rem 0">'
            f'<div style="background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};'
            f'border-left:3px solid {coul};border-radius:8px;padding:.4rem .8rem;max-width:55%">'
            f'<span style="font-weight:700;font-size:.92rem">{logo} {e["joueur"]}</span>'
            f'<span style="color:{D1_GRIS};font-size:.82rem"> {per} {min_aff}\' </span>'
            f'<span style="font-weight:800;color:{coul};font-size:.95rem"> {score_txt}</span>'
            f'{orig}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # Stats du match
    st.markdown("### Stats du match")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    buts_dom = df_match[df_match["equipe_marque"] == dom]
    buts_ext = df_match[df_match["equipe_marque"] == ext]
    c1.metric("Buts dom.", len(buts_dom))
    c2.metric("Buts ext.", len(buts_ext))
    c3.metric("Buts P1", int((df_match["periode"]==1).sum()))
    c4.metric("Buts P2", int((df_match["periode"]==2).sum()))
    c5.metric("Buteurs dom.", buts_dom["joueur"].nunique())
    c6.metric("Buteurs ext.", buts_ext["joueur"].nunique())

    # Buteurs de chaque équipe
    cg, cd = st.columns(2)
    with cg:
        st.markdown(f"**Buteurs {dom.split()[0]}**")
        bd = buts_dom["joueur"].value_counts()
        for j, n in bd.items():
            st.markdown(f'⚽ {"⚽"*(n-1)} **{j}** ({n})')
    with cd:
        st.markdown(f"**Buteurs {ext.split()[0]}**")
        be = buts_ext["joueur"].value_counts()
        for j, n in be.items():
            st.markdown(f'⚽ {"⚽"*(n-1)} **{j}** ({n})')


# ============================================================================
# PAGE — CLASSEMENT BUTEURS
# ============================================================================
elif page == "Classement buteurs":
    st.title("Classement des buteurs")

    eq = st.selectbox("Filtrer par équipe", ["Toutes"] + EQUIPES)
    d = df if eq == "Toutes" else df[df["equipe_marque"] == eq]

    clt = (d.groupby("joueur")
             .agg(buts=("but_id","count"),
                  equipe=("equipe_marque", lambda s: s.mode().iloc[0]))
             .reset_index()
             .sort_values("buts", ascending=False)
             .reset_index(drop=True))
    clt.index += 1

    # Podium
    if len(clt) >= 3:
        p = clt.head(3)
        cols = st.columns(3)
        medals = ["🥇","🥈","🥉"]
        for i, (col, (_, row)) in enumerate(zip(cols, p.iterrows())):
            lg = logo_eq(row["equipe"], 40)
            col.markdown(
                f'<div class="podium">'
                f'<div style="font-size:1.8rem">{medals[i]}</div>'
                f'{lg}<br>'
                f'<div style="font-weight:700;margin-top:.4rem">{row["joueur"]}</div>'
                f'<div class="note">{row["equipe"]}</div>'
                f'<div style="color:{D1_ROUGE_CLAIR};font-size:1.4rem;font-weight:800;margin-top:.3rem">{row["buts"]} buts</div>'
                f'</div>', unsafe_allow_html=True)
        st.markdown("")

    aff = clt.rename(columns={"joueur":"Joueur","buts":"Buts","equipe":"Équipe"})[["Joueur","Équipe","Buts"]]
    st.dataframe(aff, use_container_width=True, height=440)
    c1, c2 = st.columns(2)
    with c1: dl_csv(aff, "⬇ CSV", f"buteurs_{eq.replace(' ','_')}.csv")
    with c2:
        st.download_button("⬇ PDF",
            pdf_tableau("Classement des buteurs", f"D1 Futsal — {eq}", aff.head(40)),
            file_name=f"buteurs.pdf", mime="application/pdf")

    st.markdown("### Profil d'un buteur")
    j = st.selectbox("Buteur", clt["joueur"].tolist())
    dj = df[df["joueur"] == j]
    a, b, c, d2 = st.columns(4)
    a.metric("Buts", len(dj))
    b.metric("1re période", int((dj["periode"]==1).sum()))
    c.metric("2e période", int((dj["periode"]==2).sum()))
    d2.metric("Équipes adverses", dj["equipe_encaisse"].nunique())
    sit = dj["situation"].value_counts()
    if not sit.empty:
        st.plotly_chart(barre(sit.index.tolist(), sit.values, couleur=D1_OR,
                              h=240, texte=sit.values,
                              titre="Situation au moment des buts"),
                        use_container_width=True)


# ============================================================================
# PAGE — PROFIL TEMPOREL
# ============================================================================
elif page == "Profil temporel":
    st.title("Profil temporel des buts")
    eq = st.selectbox("Périmètre", ["Tout le championnat"] + EQUIPES)
    d = df if eq == "Tout le championnat" else df[df["equipe_marque"] == eq]

    c1, c2, c3 = st.columns(3)
    p1 = int((d["periode"]==1).sum()); p2 = int((d["periode"]==2).sum())
    c1.metric("Buts", len(d))
    c2.metric("1re période", p1, f"{p1/len(d)*100:.0f}%" if len(d) else "")
    c3.metric("2e période", p2, f"{p2/len(d)*100:.0f}%" if len(d) else "")

    st.markdown("### Buts par minute")
    mins = d["minute"].dropna().astype(int)
    serie = mins.value_counts().reindex(range(1, 41), fill_value=0).sort_index()
    coul_bars = [D1_ROUGE if m <= 20 else D1_BORDEAUX_2 for m in serie.index]
    fig = go.Figure(go.Bar(x=[f"{m}'" for m in serie.index], y=serie.values,
                           marker_color=coul_bars))
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)
    st.markdown("<p class='note'>Rouge = 1re période · Bordeaux = 2e période</p>",
                unsafe_allow_html=True)

    st.markdown("### Buts par tranche de 5 minutes")
    tr = pd.cut(mins, bins=range(0,41,5),
                labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
    st.plotly_chart(barre(tr.index.astype(str).tolist(), tr.values,
                          texte=tr.values, h=300), use_container_width=True)


# ============================================================================
# PAGE — DYNAMIQUE DE SCORE
# ============================================================================
elif page == "Dynamique de score":
    st.title("Dynamique de score")
    st.markdown("<p class='note'>Situation de l'équipe qui marque, juste avant son but.</p>",
                unsafe_allow_html=True)

    eq = st.selectbox("Périmètre", ["Tout le championnat"] + EQUIPES)
    d = df if eq == "Tout le championnat" else df[df["equipe_marque"] == eq]
    d = d[d["situation"].notna()]

    ordre = ["Mené","Égalité","Menant"]
    coul_sit = {"Mené": D1_ROUGE, "Égalité": D1_OR, "Menant": D1_BLEU}
    sit = d["situation"].value_counts().reindex(ordre, fill_value=0)
    tot = sit.sum() or 1

    c1, c2, c3 = st.columns(3)
    c1.metric("En étant mené", int(sit["Mené"]), f"{sit['Mené']/tot*100:.0f}%")
    c2.metric("À égalité",     int(sit["Égalité"]), f"{sit['Égalité']/tot*100:.0f}%")
    c3.metric("En menant",     int(sit["Menant"]), f"{sit['Menant']/tot*100:.0f}%")

    fig = go.Figure(go.Bar(x=ordre, y=sit.values,
                           marker_color=[coul_sit[s] for s in ordre],
                           text=sit.values, textposition="auto"))
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    if eq == "Tout le championnat":
        st.markdown("### Part des buts marqués en étant mené, par équipe")
        rows = []
        for e in EQUIPES:
            de = df[(df["equipe_marque"]==e) & (df["situation"].notna())]
            if len(de):
                rows.append((e, (de["situation"]=="Mené").mean()*100, len(de)))
        comp = pd.DataFrame(rows, columns=["Équipe","pct","n"]).sort_values("pct", ascending=False)
        st.plotly_chart(barre(comp["Équipe"].tolist(), comp["pct"].round(0),
                              horizontal=True, h=max(340,34*len(comp)),
                              texte=[f"{v:.0f}%" for v in comp["pct"]]),
                        use_container_width=True)


# ============================================================================
# PAGE — VUE ÉQUIPE
# ============================================================================
elif page == "Vue équipe":
    st.title("Fiche équipe")
    eq = st.selectbox("Équipe", EQUIPES,
                      format_func=lambda e: e)
    lg = logo_eq(eq, 52)
    clt = construire_classement()
    rang_row = clt[clt["equipe"]==eq].iloc[0]

    st.markdown(
        f'<div class="card" style="display:flex;align-items:center;gap:1.2rem">'
        f'{lg}'
        f'<div><div style="font-size:1.2rem;font-weight:800">{eq}</div>'
        f'<div style="color:{D1_GRIS};font-size:.85rem">'
        f'Rang : <b style="color:{D1_ROUGE_CLAIR}">{clt[clt["equipe"]==eq].index[0]+1}</b> · '
        f'{int(rang_row["Pts"])} pts · {int(rang_row["V"])}V {int(rang_row["N"])}N {int(rang_row["D"])}D'
        f'</div>'
        f'<div style="margin-top:.4rem">{forme_html(rang_row["forme"])}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    dpour   = df[df["equipe_marque"]  == eq]
    dcontre = df[df["equipe_encaisse"] == eq]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Buts marqués", len(dpour))
    c2.metric("Buts encaissés", len(dcontre))
    c3.metric("Différence", f"{len(dpour)-len(dcontre):+d}")
    c4.metric("Buteurs utilisés", dpour["joueur"].nunique())

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buteurs")
        bb = dpour["joueur"].value_counts()
        st.plotly_chart(barre(bb.index.tolist(), bb.values, horizontal=True,
                              h=max(260, 28*len(bb)), texte=bb.values),
                        use_container_width=True)
    with cd:
        st.markdown("### Quand l'équipe marque (tranches 5 min)")
        mins = dpour["minute"].dropna().astype(int)
        tr = pd.cut(mins, bins=range(0,41,5),
                    labels=[f"{i+1}-{i+5}'" for i in range(0,40,5)]).value_counts().sort_index()
        st.plotly_chart(barre(tr.index.astype(str).tolist(), tr.values,
                              couleur=COULEUR_EQUIPE.get(eq, D1_OR),
                              texte=tr.values, h=300), use_container_width=True)

    st.markdown("### Origine des buts")
    if eq in EQUIPES_AVEC_ORIGINE:
        oo = dpour.loc[dpour["origine"].notna(), "origine"].value_counts()
        n_rens = int(dpour["origine"].notna().sum())
        st.markdown(f'<span style="background:{D1_ROUGE};color:white;padding:.15rem .6rem;'
                    f'border-radius:6px;font-weight:600;font-size:.8rem">'
                    f'{n_rens}/{len(dpour)} buts analysés</span>', unsafe_allow_html=True)
        st.plotly_chart(barre(oo.index.tolist(), oo.values, horizontal=True,
                              h=max(260, 32*len(oo)), texte=oo.values),
                        use_container_width=True)
    else:
        st.info("Origine des buts pas encore renseignée pour cette équipe.")


# ============================================================================
# PAGE — TACTIQUE / ORIGINES
# ============================================================================
elif page == "Tactique / Origines":
    st.title("Tactique — Origine des buts")
    if not EQUIPES_AVEC_ORIGINE:
        st.info("Aucune origine renseignée pour le moment.")
        st.stop()

    st.markdown(f"<p class='note'>Données disponibles : {', '.join(EQUIPES_AVEC_ORIGINE)}</p>",
                unsafe_allow_html=True)
    do = df[df["origine"].notna()]

    st.markdown("### Répartition globale")
    glob = do["origine"].value_counts()
    st.plotly_chart(barre(glob.index.tolist(), glob.values, horizontal=True,
                          h=max(300, 34*len(glob)), texte=glob.values),
                    use_container_width=True)

    st.markdown("### Comparaison par équipe")
    sel = st.multiselect("Équipes", EQUIPES_AVEC_ORIGINE, default=EQUIPES_AVEC_ORIGINE[:3])
    if sel:
        sous = do[do["equipe_marque"].isin(sel)]
        pivot = sous.groupby(["equipe_marque","origine"]).size().reset_index(name="n")
        fig = go.Figure()
        for i, og in enumerate(sorted(sous["origine"].unique())):
            sub = pivot[pivot["origine"] == og]
            fig.add_trace(go.Bar(name=og, x=sub["equipe_marque"], y=sub["n"],
                                 marker_color=PALETTE[i % len(PALETTE)]))
        fig.update_layout(barmode="stack")
        st.plotly_chart(style_fig(fig, 420), use_container_width=True)
        tab = pivot.pivot(index="equipe_marque", columns="origine", values="n").fillna(0).astype(int)
        st.dataframe(tab, use_container_width=True)


# ============================================================================
# PAGE — CONFRONTATIONS
# ============================================================================
elif page == "Confrontations":
    st.title("Confrontations directes")
    c1, c2 = st.columns(2)
    e1 = c1.selectbox("Équipe A", EQUIPES, index=0)
    e2 = c2.selectbox("Équipe B", EQUIPES, index=1 if len(EQUIPES)>1 else 0)

    if e1 == e2:
        st.warning("Choisis deux équipes différentes.")
        st.stop()

    masque = (
        ((df["equipe_marque"]==e1) & (df["equipe_encaisse"]==e2)) |
        ((df["equipe_marque"]==e2) & (df["equipe_encaisse"]==e1))
    )
    d = df[masque]
    if d.empty:
        st.info("Aucun but recensé entre ces deux équipes."); st.stop()

    b1 = int((d["equipe_marque"]==e1).sum())
    b2 = int((d["equipe_marque"]==e2).sum())
    nb_conf = d["journee"].nunique()

    l1 = logo_eq(e1, 44); l2 = logo_eq(e2, 44)
    c1, c2, c3 = st.columns([2,1,2])
    c1.markdown(f'<div style="text-align:center">{l1}<br><b>{e1.split()[0]}</b></div>',
                unsafe_allow_html=True)
    c2.metric("Rencontres", nb_conf)
    c3.markdown(f'<div style="text-align:center">{l2}<br><b>{e2.split()[0]}</b></div>',
                unsafe_allow_html=True)

    fig = go.Figure(go.Bar(
        x=[e1.split()[0], e2.split()[0]], y=[b1, b2],
        marker_color=[COULEUR_EQUIPE.get(e1, D1_ROUGE), COULEUR_EQUIPE.get(e2, D1_BLEU)],
        text=[b1, b2], textposition="auto"))
    st.plotly_chart(style_fig(fig, 300, "Buts marqués dans les confrontations"),
                    use_container_width=True)

    st.markdown("### Détail des buts")
    det = (d.sort_values(["journee","periode","minute"])
            [["journee","equipe_marque","joueur","periode","minute","situation","origine"]]
            .rename(columns={"journee":"J","equipe_marque":"Marque","joueur":"Buteur",
                             "periode":"Pér.","minute":"Min",
                             "situation":"Situation","origine":"Origine"}))
    det["Origine"] = det["Origine"].fillna("—")
    st.dataframe(det, use_container_width=True, height=380)
    dl_csv(det, "⬇ CSV", f"confrontation_{e1[:6]}_{e2[:6]}.csv")
