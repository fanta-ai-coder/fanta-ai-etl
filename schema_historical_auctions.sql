-- ======================================================================
-- TABELLA STORICO ACQUISTI ASTA: historical_auction_purchases
-- Salva tutti gli acquisti d'asta passati (2021-2024) con costi normalizzati
-- ======================================================================

CREATE TABLE IF NOT EXISTS public.historical_auction_purchases (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    calciatore TEXT NOT NULL,
    ruolo TEXT NOT NULL,
    squadra TEXT,
    fantasquadra TEXT,
    costo NUMERIC NOT NULL,
    budget_lega NUMERIC NOT NULL,
    costo_pct NUMERIC NOT NULL,
    costo_normalizzato_1000 NUMERIC NOT NULL,
    anno_asta INTEGER NOT NULL,
    stagione_asta TEXT NOT NULL,
    prev_season TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indici per query e join veloci
CREATE INDEX IF NOT EXISTS idx_hist_auction_calciatore ON public.historical_auction_purchases(calciatore);
CREATE INDEX IF NOT EXISTS idx_hist_auction_ruolo ON public.historical_auction_purchases(ruolo);
CREATE INDEX IF NOT EXISTS idx_hist_auction_anno ON public.historical_auction_purchases(anno_asta);
CREATE INDEX IF NOT EXISTS idx_hist_auction_stagione ON public.historical_auction_purchases(stagione_asta);
CREATE INDEX IF NOT EXISTS idx_hist_auction_prev_season ON public.historical_auction_purchases(prev_season);

-- Sicurezza RLS
ALTER TABLE public.historical_auction_purchases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read access" ON public.historical_auction_purchases;
CREATE POLICY "Allow public read access" ON public.historical_auction_purchases FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow service role full access" ON public.historical_auction_purchases;
CREATE POLICY "Allow service role full access" ON public.historical_auction_purchases FOR ALL USING (true);
