"""
================================================================================
ANALYSE DES BUTS — D1 FUTSAL   (v1)
================================================================================
Tableau de bord d'analyse de tous les buts de la saison de D1 Futsal.
Source : futsal_d1.db (générée par migration_buts.py).

Pages :
  - Accueil            : chiffres clés du championnat + buts par journée
  - Classement buteurs : podium + tableau, mini-profil du buteur
  - Profil temporel    : buts par minute / période (championnat ou équipe)
  - Dynamique de score : buts marqués en menant / égalité / mené
  - Vue équipe         : fiche complète d'une équipe (+ origines si dispo)
  - Tactique / Origines: d'où viennent les buts (équipes renseignées)
  - Confrontations     : head-to-head entre deux équipes

Lancer :  streamlit run app_buts.py
================================================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from io import BytesIO

import plotly.graph_objects as go

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
DB_PATH   = "futsal_d1.db"
LOGO_PATH = Path("D1_Futsal_logo.png")

# --- Charte D1 Futsal (extraite du logo) ---
D1_ROUGE       = "#C00018"   # rouge vif principal
D1_ROUGE_CLAIR = "#E11030"
D1_BORDEAUX    = "#540C18"   # bordeaux foncé (fonds de cartes)
D1_BORDEAUX_2  = "#6C1420"
D1_ANTHRACITE  = "#1A1A1E"   # fond général
D1_CARTE       = "#26181C"   # fond carte (bordeaux très sombre)
D1_BLANC       = "#F5F2F3"
D1_GRIS        = "#9A8E91"
D1_OR          = "#C9A24B"   # accent discret (podium)

# palette ordonnée pour les graphes catégoriels
PALETTE = [D1_ROUGE, "#E0762A", D1_OR, "#5A8FB5", "#7BA05B",
           "#8E6FB0", "#C8607A", D1_GRIS, "#4B9E8E", "#B5563C"]

st.set_page_config(
    page_title="D1 Futsal — Analyse des buts", page_icon="⚽",
    layout="wide", initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# STYLE
# ---------------------------------------------------------------------------
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    .stApp {{ background: {D1_ANTHRACITE}; }}
    html, body, [class*="css"], .stMarkdown, .stMetric, button, input, select, textarea {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}
    .block-container {{ padding-top: 1.4rem; padding-bottom: 2rem; }}
    h1 {{
        color: {D1_BLANC} !important;
        border-bottom: 3px solid {D1_ROUGE};
        padding-bottom: .3rem; letter-spacing: -.5px; font-size: 1.9rem !important;
    }}
    h2, h3 {{ color: {D1_ROUGE_CLAIR} !important; letter-spacing: -.3px; }}
    p, label, span, div {{ color: {D1_BLANC}; }}
    /* sidebar */
    [data-testid="stSidebar"] {{ background: {D1_BORDEAUX}; }}
    [data-testid="stSidebar"] * {{ color: {D1_BLANC} !important; }}
    /* metrics en cartes */
    [data-testid="stMetric"] {{
        background: {D1_CARTE}; border: 1px solid {D1_BORDEAUX_2};
        border-radius: 12px; padding: .8rem 1rem;
    }}
    [data-testid="stMetricValue"] {{ font-size: 1.7rem; color: {D1_BLANC}; }}
    [data-testid="stMetricLabel"] {{ font-size: .82rem; color: {D1_GRIS}; }}
    /* radios actifs en rouge */
    [data-baseweb="radio"] [aria-checked="true"] div:first-child {{
        background-color: {D1_ROUGE} !important; border-color: {D1_ROUGE} !important;
    }}
    .stDataFrame {{ border-radius: 10px; overflow: hidden; }}
    .d1-badge {{
        display:inline-block; background:{D1_ROUGE}; color:#fff;
        padding:.15rem .6rem; border-radius:6px; font-weight:600; font-size:.8rem;
    }}
    .d1-note {{ color:{D1_GRIS}; font-size:.82rem; font-style:italic; }}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DONNÉES
# ============================================================================
@st.cache_data
def charger():
    if not Path(DB_PATH).exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM but", conn)
    conn.close()
    return df


df = charger()
if df is None:
    st.error("Base `futsal_d1.db` introuvable. Lance d'abord :  python migration_buts.py")
    st.stop()

EQUIPES = sorted(df["equipe_marque"].dropna().unique().tolist())
JOURNEES = sorted(df["journee"].dropna().unique().tolist())
EQUIPES_AVEC_ORIGINE = sorted(
    df.loc[df["origine"].notna(), "equipe_marque"].dropna().unique().tolist()
)


# ---------------------------------------------------------------------------
# HELPERS GRAPHIQUES
# ---------------------------------------------------------------------------
def style_fig(fig, hauteur=360, titre=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=D1_BLANC, size=13),
        height=hauteur,
        margin=dict(l=10, r=10, t=40 if titre else 15, b=10),
        title=dict(text=titre or "", font=dict(size=15, color=D1_BLANC)),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    return fig


def barres(x, y, couleur=D1_ROUGE, horizontal=False, hauteur=360, titre=None, texte=None):
    if horizontal:
        fig = go.Figure(go.Bar(x=y, y=x, orientation="h",
                               marker_color=couleur, text=texte, textposition="auto"))
        fig.update_yaxes(autorange="reversed")
    else:
        fig = go.Figure(go.Bar(x=x, y=y, marker_color=couleur,
                               text=texte, textposition="auto"))
    return style_fig(fig, hauteur, titre)


def telecharger_csv(dframe, label, nom):
    st.download_button(label, dframe.to_csv(index=False).encode("utf-8-sig"),
                       file_name=nom, mime="text/csv")


# ---------------------------------------------------------------------------
# EXPORT PDF
# ---------------------------------------------------------------------------
def pdf_tableau(titre, sous_titre, df_tab, note=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    rouge = colors.HexColor(D1_ROUGE)
    bordeaux = colors.HexColor(D1_BORDEAUX)

    h = ParagraphStyle("h", parent=styles["Title"], textColor=rouge,
                       fontSize=18, alignment=TA_CENTER, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey,
                         fontSize=10, alignment=TA_CENTER, spaceAfter=14)
    notest = ParagraphStyle("note", parent=styles["Normal"], textColor=colors.grey,
                            fontSize=8, alignment=TA_CENTER, spaceBefore=10)

    elems = []
    if LOGO_PATH.exists():
        try:
            img = RLImage(str(LOGO_PATH), width=2.2*cm, height=2.35*cm)
            img.hAlign = "CENTER"
            elems += [img, Spacer(1, 6)]
        except Exception:
            pass
    elems += [Paragraph(titre, h), Paragraph(sous_titre, sub)]

    data = [list(df_tab.columns)] + df_tab.astype(str).values.tolist()
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rouge),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4ECEE")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9C7CB")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(t)
    if note:
        elems.append(Paragraph(note, notest))
    doc.build(elems)
    buf.seek(0)
    return buf


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=120)
    st.markdown("### D1 FUTSAL")
    st.caption("Analyse des buts de la saison")
    st.markdown("---")
    page = st.radio("Navigation", [
        "Accueil",
        "Classement buteurs",
        "Profil temporel",
        "Dynamique de score",
        "Vue équipe",
        "Tactique / Origines",
        "Confrontations",
    ])
    st.markdown("---")
    st.caption(f"{len(df)} buts · {len(EQUIPES)} équipes · "
               f"J{min(JOURNEES)}–J{max(JOURNEES)}")


# ============================================================================
# PAGE — ACCUEIL
# ============================================================================
if page == "Accueil":
    st.title("D1 Futsal — Vue d'ensemble")

    nb_buts = len(df)
    nb_matchs = df.groupby(["journee", "equipe_domicile", "equipe_exterieure"]).ngroups
    moy = nb_buts / nb_matchs if nb_matchs else 0

    pour = df["equipe_marque"].value_counts()
    contre = df["equipe_encaisse"].value_counts()
    top_buteur = df["joueur"].value_counts().idxmax()
    top_buteur_n = df["joueur"].value_counts().max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Buts marqués", nb_buts)
    c2.metric("Matchs couverts", nb_matchs)
    c3.metric("Moyenne buts/match", f"{moy:.1f}")
    c4.metric("Meilleur buteur", f"{top_buteur_n}", top_buteur)

    c1, c2, c3 = st.columns(3)
    c1.metric("Attaque la + prolifique", pour.idxmax(), f"{pour.max()} buts")
    c2.metric("Défense la + solide", contre.idxmin(), f"{contre.min()} encaissés")
    part_origine = df["origine"].notna().mean() * 100
    c3.metric("Buts avec origine analysée", f"{part_origine:.0f}%")

    st.markdown("### Buts par journée")
    parj = df.groupby("journee").size().reindex(JOURNEES, fill_value=0)
    st.plotly_chart(barres(
        [f"J{j}" for j in parj.index], parj.values,
        texte=parj.values, hauteur=320), use_container_width=True)

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buts marqués par équipe")
        st.plotly_chart(barres(pour.index.tolist(), pour.values, horizontal=True,
                               hauteur=420, texte=pour.values), use_container_width=True)
    with cd:
        st.markdown("### Buts encaissés par équipe")
        st.plotly_chart(barres(contre.index.tolist(), contre.values, horizontal=True,
                               couleur=D1_GRIS, hauteur=420, texte=contre.values),
                        use_container_width=True)


# ============================================================================
# PAGE — CLASSEMENT BUTEURS
# ============================================================================
elif page == "Classement buteurs":
    st.title("Classement des buteurs")

    eq = st.selectbox("Filtrer par équipe", ["Toutes"] + EQUIPES)
    d = df if eq == "Toutes" else df[df["equipe_marque"] == eq]

    clt = (d.groupby("joueur")
             .agg(buts=("but_id", "count"),
                  equipe=("equipe_marque", lambda s: s.mode().iloc[0]))
             .reset_index()
             .sort_values("buts", ascending=False)
             .reset_index(drop=True))
    clt.index += 1

    # podium
    if len(clt) >= 3:
        p = clt.head(3)
        cols = st.columns(3)
        medailles = ["🥇", "🥈", "🥉"]
        for i, (col, (_, row)) in enumerate(zip(cols, p.iterrows())):
            col.markdown(
                f"<div style='background:{D1_CARTE};border:1px solid {D1_BORDEAUX_2};"
                f"border-radius:12px;padding:1rem;text-align:center'>"
                f"<div style='font-size:1.6rem'>{medailles[i]}</div>"
                f"<div style='font-weight:700;font-size:1.05rem'>{row['joueur']}</div>"
                f"<div class='d1-note'>{row['equipe']}</div>"
                f"<div style='color:{D1_ROUGE_CLAIR};font-size:1.5rem;font-weight:800'>"
                f"{row['buts']} buts</div></div>",
                unsafe_allow_html=True)
        st.markdown("")

    aff = clt.rename(columns={"joueur": "Joueur", "buts": "Buts", "equipe": "Équipe"})
    aff = aff[["Joueur", "Équipe", "Buts"]]
    st.dataframe(aff, use_container_width=True, height=460)

    c1, c2 = st.columns(2)
    with c1:
        telecharger_csv(aff, "⬇ CSV", f"buteurs_{eq.replace(' ','_')}.csv")
    with c2:
        st.download_button(
            "⬇ PDF", pdf_tableau("Classement des buteurs",
                                 f"D1 Futsal — {eq}", aff.head(40)),
            file_name=f"buteurs_{eq.replace(' ','_')}.pdf", mime="application/pdf")

    # mini-profil
    st.markdown("### Profil d'un buteur")
    j = st.selectbox("Buteur", clt["joueur"].tolist())
    dj = df[df["joueur"] == j]
    a, b, c = st.columns(3)
    a.metric("Buts", len(dj))
    b.metric("1re période", int((dj["periode"] == 1).sum()))
    c.metric("2e période", int((dj["periode"] == 2).sum()))
    sit = dj["situation"].value_counts()
    if not sit.empty:
        st.plotly_chart(barres(sit.index.tolist(), sit.values, couleur=D1_OR,
                               hauteur=240, texte=sit.values,
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
    c1.metric("Buts", len(d))
    p1 = int((d["periode"] == 1).sum()); p2 = int((d["periode"] == 2).sum())
    c2.metric("1re période", p1)
    c3.metric("2e période", p2)

    st.markdown("### Répartition par minute")
    mins = d["minute"].dropna().astype(int)
    serie = mins.value_counts().reindex(range(1, 41), fill_value=0).sort_index()
    coul = [D1_ROUGE if m <= 20 else D1_BORDEAUX_2 for m in serie.index]
    fig = go.Figure(go.Bar(x=[f"{m}'" for m in serie.index], y=serie.values,
                           marker_color=coul))
    st.plotly_chart(style_fig(fig, 340), use_container_width=True)
    st.markdown("<span class='d1-note'>Rouge = 1re période · "
                "Bordeaux = 2e période</span>", unsafe_allow_html=True)

    st.markdown("### Buts par tranche de 5 minutes")
    tranches = pd.cut(mins, bins=range(0, 41, 5),
                      labels=[f"{i+1}-{i+5}'" for i in range(0, 40, 5)])
    tr = tranches.value_counts().sort_index()
    st.plotly_chart(barres(tr.index.astype(str).tolist(), tr.values,
                           texte=tr.values, hauteur=300), use_container_width=True)


# ============================================================================
# PAGE — DYNAMIQUE DE SCORE
# ============================================================================
elif page == "Dynamique de score":
    st.title("Dynamique de score")
    st.markdown("<span class='d1-note'>Situation de l'équipe qui marque, "
                "juste avant son but.</span>", unsafe_allow_html=True)

    eq = st.selectbox("Périmètre", ["Tout le championnat"] + EQUIPES)
    d = df if eq == "Tout le championnat" else df[df["equipe_marque"] == eq]
    d = d[d["situation"].notna()]

    ordre = ["Mené", "Égalité", "Menant"]
    coul = {"Mené": D1_ROUGE, "Égalité": D1_OR, "Menant": "#5A8FB5"}
    sit = d["situation"].value_counts().reindex(ordre, fill_value=0)

    c1, c2, c3 = st.columns(3)
    tot = sit.sum() or 1
    c1.metric("En étant mené", int(sit["Mené"]), f"{sit['Mené']/tot*100:.0f}%")
    c2.metric("À égalité", int(sit["Égalité"]), f"{sit['Égalité']/tot*100:.0f}%")
    c3.metric("En menant", int(sit["Menant"]), f"{sit['Menant']/tot*100:.0f}%")

    fig = go.Figure(go.Bar(x=ordre, y=sit.values,
                           marker_color=[coul[s] for s in ordre],
                           text=sit.values, textposition="auto"))
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    if eq == "Tout le championnat":
        st.markdown("### Part des buts marqués en étant mené, par équipe")
        rows = []
        for e in EQUIPES:
            de = df[(df["equipe_marque"] == e) & (df["situation"].notna())]
            if len(de):
                rows.append((e, (de["situation"] == "Mené").mean() * 100, len(de)))
        comp = pd.DataFrame(rows, columns=["Équipe", "pct", "n"]).sort_values("pct", ascending=False)
        st.plotly_chart(barres(comp["Équipe"].tolist(), comp["pct"].round(0),
                               horizontal=True, hauteur=420,
                               texte=[f"{v:.0f}%" for v in comp["pct"]]),
                        use_container_width=True)


# ============================================================================
# PAGE — VUE ÉQUIPE
# ============================================================================
elif page == "Vue équipe":
    st.title("Fiche équipe")
    eq = st.selectbox("Équipe", EQUIPES)
    dpour = df[df["equipe_marque"] == eq]
    dcontre = df[df["equipe_encaisse"] == eq]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Buts marqués", len(dpour))
    c2.metric("Buts encaissés", len(dcontre))
    c3.metric("Différence", f"{len(dpour) - len(dcontre):+d}")
    c4.metric("Buteurs utilisés", dpour["joueur"].nunique())

    cg, cd = st.columns(2)
    with cg:
        st.markdown("### Buteurs de l'équipe")
        bb = dpour["joueur"].value_counts()
        st.plotly_chart(barres(bb.index.tolist(), bb.values, horizontal=True,
                               hauteur=max(260, 28*len(bb)), texte=bb.values),
                        use_container_width=True)
    with cd:
        st.markdown("### Quand l'équipe marque")
        mins = dpour["minute"].dropna().astype(int)
        tr = pd.cut(mins, bins=range(0, 41, 5),
                    labels=[f"{i+1}-{i+5}'" for i in range(0, 40, 5)]).value_counts().sort_index()
        st.plotly_chart(barres(tr.index.astype(str).tolist(), tr.values,
                               couleur=D1_OR, texte=tr.values, hauteur=300),
                        use_container_width=True)

    st.markdown("### Origine des buts")
    if eq in EQUIPES_AVEC_ORIGINE:
        oo = dpour.loc[dpour["origine"].notna(), "origine"].value_counts()
        n_rens = int(dpour["origine"].notna().sum())
        st.markdown(f"<span class='d1-badge'>{n_rens}/{len(dpour)} buts analysés</span>",
                    unsafe_allow_html=True)
        st.plotly_chart(barres(oo.index.tolist(), oo.values, horizontal=True,
                               couleur=D1_ROUGE, hauteur=max(260, 32*len(oo)),
                               texte=oo.values), use_container_width=True)
    else:
        st.info("Origine des buts pas encore renseignée pour cette équipe.")


# ============================================================================
# PAGE — TACTIQUE / ORIGINES
# ============================================================================
elif page == "Tactique / Origines":
    st.title("Tactique — origine des buts")
    if not EQUIPES_AVEC_ORIGINE:
        st.info("Aucune origine renseignée pour le moment.")
        st.stop()

    st.markdown(f"<span class='d1-note'>Données disponibles pour : "
                f"{', '.join(EQUIPES_AVEC_ORIGINE)}.</span>", unsafe_allow_html=True)

    do = df[df["origine"].notna()]

    st.markdown("### Répartition globale des origines")
    glob = do["origine"].value_counts()
    st.plotly_chart(barres(glob.index.tolist(), glob.values, horizontal=True,
                           hauteur=max(300, 34*len(glob)), texte=glob.values),
                    use_container_width=True)

    st.markdown("### Comparaison par équipe")
    sel = st.multiselect("Équipes", EQUIPES_AVEC_ORIGINE,
                         default=EQUIPES_AVEC_ORIGINE[:3])
    if sel:
        sous = do[do["equipe_marque"].isin(sel)]
        pivot = (sous.groupby(["equipe_marque", "origine"]).size()
                 .reset_index(name="n"))
        fig = go.Figure()
        origines_uniques = sorted(sous["origine"].unique())
        for i, og in enumerate(origines_uniques):
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
    e2 = c2.selectbox("Équipe B", EQUIPES, index=1 if len(EQUIPES) > 1 else 0)

    if e1 == e2:
        st.warning("Choisis deux équipes différentes.")
        st.stop()

    # buts entre les deux équipes (dans les matchs qui les opposent)
    masque = (
        ((df["equipe_marque"] == e1) & (df["equipe_encaisse"] == e2)) |
        ((df["equipe_marque"] == e2) & (df["equipe_encaisse"] == e1))
    )
    d = df[masque]
    if d.empty:
        st.info("Aucun but recensé entre ces deux équipes.")
        st.stop()

    b1 = int((d["equipe_marque"] == e1).sum())
    b2 = int((d["equipe_marque"] == e2).sum())
    nb_conf = d.groupby(["journee"]).ngroups

    c1, c2, c3 = st.columns(3)
    c1.metric(e1, b1)
    c2.metric("Rencontres", nb_conf)
    c3.metric(e2, b2)

    fig = go.Figure(go.Bar(x=[e1, e2], y=[b1, b2],
                           marker_color=[D1_ROUGE, "#5A8FB5"],
                           text=[b1, b2], textposition="auto"))
    st.plotly_chart(style_fig(fig, 300, "Buts marqués dans les confrontations"),
                    use_container_width=True)

    st.markdown("### Détail des buts")
    det = (d.sort_values(["journee", "periode", "minute"])
             [["journee", "equipe_marque", "joueur", "periode", "minute", "situation", "origine"]]
             .rename(columns={"journee": "J", "equipe_marque": "Marque", "joueur": "Buteur",
                              "periode": "Pér.", "minute": "Min", "situation": "Situation",
                              "origine": "Origine"}))
    det["Origine"] = det["Origine"].fillna("—")
    st.dataframe(det, use_container_width=True, height=380)
    telecharger_csv(det, "⬇ CSV", f"confrontation_{e1[:6]}_{e2[:6]}.csv")
