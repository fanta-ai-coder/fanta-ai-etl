-- ============================================================
-- TABELLA PRECALCOLATA KPI GIOCATORI: player_kpi_summary
-- ============================================================
-- Esegui questo script nel SQL Editor di Supabase:
-- https://supabase.com/dashboard/project/yzwgntdmcravpzaybcrp/sql

CREATE TABLE IF NOT EXISTS public.player_kpi_summary (
    player_id INTEGER NOT NULL,
    stagione TEXT NOT NULL DEFAULT '2026-27',
    nome TEXT NOT NULL,
    ruolo TEXT NOT NULL,
    ruolo_mantra TEXT,
    squadra TEXT NOT NULL,
    quotazione_attuale INTEGER DEFAULT 0,
    quotazione_iniziale INTEGER DEFAULT 0,
    diff_quotazione INTEGER DEFAULT 0,
    fvm INTEGER DEFAULT 0,
    ceduto BOOLEAN DEFAULT FALSE,
    
    -- Indici Algoritmici & Ranking
    indice_finale NUMERIC(5,2),
    rank_ruolo INTEGER,
    totale_ruolo INTEGER,
    rank_generale INTEGER,
    totale_generale INTEGER,
    performance_score NUMERIC(5,2),
    reliability_score NUMERIC(5,2),
    forma_attuale_score NUMERIC(5,2),
    titolarita_score NUMERIC(5,2),
    presenze_pesate NUMERIC(5,2),
    
    -- Statistiche aggregate storiche
    fantamedia NUMERIC(4,2),
    media_voto NUMERIC(4,2),
    presenze_totali INTEGER DEFAULT 0,
    presenza_pct NUMERIC(5,2) DEFAULT 0,
    presenze_medie NUMERIC(4,1) DEFAULT 0,
    gol_stagione NUMERIC(4,1) DEFAULT 0,
    assist_stagione NUMERIC(4,1) DEFAULT 0,
    gs_stagione NUMERIC(4,1) DEFAULT 0,
    rigori_parati NUMERIC(4,1) DEFAULT 0,
    varianza_voto NUMERIC(5,3),
    varianza_gol NUMERIC(5,3),
    ammonizioni NUMERIC(4,1) DEFAULT 0,
    espulsioni NUMERIC(4,1) DEFAULT 0,
    
    -- Status & Probabili Formazioni (da scraping)
    titolarita TEXT,
    is_titolare BOOLEAN DEFAULT FALSE,
    infortunato BOOLEAN DEFAULT FALSE,
    desc_infortunio TEXT,
    squalificato BOOLEAN DEFAULT FALSE,
    rigorista_pos INTEGER,
    punizioni_pos INTEGER,
    
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, stagione)
);

-- Indici per velocizzare ricerche e ordinamenti della dashboard
CREATE INDEX IF NOT EXISTS idx_kpi_ruolo ON public.player_kpi_summary(ruolo);
CREATE INDEX IF NOT EXISTS idx_kpi_squadra ON public.player_kpi_summary(squadra);
CREATE INDEX IF NOT EXISTS idx_kpi_indice ON public.player_kpi_summary(indice_finale DESC);

-- Abilita accesso in lettura se RLS è attivo
ALTER TABLE public.player_kpi_summary ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON public.player_kpi_summary;
CREATE POLICY "Allow public read access" ON public.player_kpi_summary FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow service role full access" ON public.player_kpi_summary;
CREATE POLICY "Allow service role full access" ON public.player_kpi_summary FOR ALL USING (true);
