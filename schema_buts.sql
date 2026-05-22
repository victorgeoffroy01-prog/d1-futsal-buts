-- ============================================================================
-- SCHÉMA SQLITE — Analyse des buts D1 Futsal
-- ============================================================================
-- Principe : une seule table de faits "but", chaque ligne = un but marqué.
--   - les stats (buteurs, profil temporel, dynamique de score, origines)
--     sont calculées à la volée dans le code Python / les vues SQL
--   - l'origine du but n'existe que pour certaines équipes (saisie partielle) :
--     elle est stockée telle quelle, NULL ou "Non identifié" si inconnue
-- ============================================================================

DROP VIEW  IF EXISTS v_but;
DROP TABLE IF EXISTS but;

-- ----------------------------------------------------------------------------
-- TABLE DE FAITS : un but
-- ----------------------------------------------------------------------------
CREATE TABLE but (
    but_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    journee           INTEGER NOT NULL,
    equipe_domicile   TEXT,
    equipe_exterieure TEXT,
    equipe_marque     TEXT NOT NULL,       -- équipe qui a marqué
    equipe_encaisse   TEXT NOT NULL,       -- équipe qui a encaissé
    periode           INTEGER,             -- 1 ou 2
    minute            INTEGER,             -- 1 à 40
    score_marque_avant   INTEGER,          -- score de l'équipe qui marque, AVANT le but
    score_encaisse_avant INTEGER,          -- score de l'équipe qui encaisse, AVANT le but
    situation         TEXT,                -- "Menant" / "Égalité" / "Mené" (au moment du but)
    joueur            TEXT NOT NULL,       -- buteur
    origine           TEXT                 -- attaque placée, transition... / "Non identifié" / NULL
);

CREATE INDEX idx_but_marque   ON but(equipe_marque);
CREATE INDEX idx_but_encaisse ON but(equipe_encaisse);
CREATE INDEX idx_but_joueur   ON but(joueur);
CREATE INDEX idx_but_journee  ON but(journee);

-- ----------------------------------------------------------------------------
-- VUE pratique (alias lisibles)
-- ----------------------------------------------------------------------------
CREATE VIEW v_but AS
SELECT
    but_id, journee, equipe_marque, equipe_encaisse,
    periode, minute, situation, joueur,
    COALESCE(origine, 'Non renseigné') AS origine
FROM but;
