-- ====================================================================
-- TABELLA CALENDARIO SERIE A (2026-27) SU SUPABASE
-- Esegui questo script nel SQL Editor del tuo progetto Supabase.
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.serie_a_calendar (
    id BIGSERIAL PRIMARY KEY,
    giornata INT NOT NULL,
    squadra_casa TEXT NOT NULL,
    squadra_trasferta TEXT NOT NULL,
    stagione TEXT DEFAULT '2026-27',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indici per query ad altissima velocita
CREATE INDEX IF NOT EXISTS idx_calendar_giornata ON public.serie_a_calendar(giornata);
CREATE INDEX IF NOT EXISTS idx_calendar_casa ON public.serie_a_calendar(squadra_casa);
CREATE INDEX IF NOT EXISTS idx_calendar_trasferta ON public.serie_a_calendar(squadra_trasferta);

-- Abilita Row Level Security con policy di sola lettura pubblica
ALTER TABLE public.serie_a_calendar ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read-only access to calendar"
ON public.serie_a_calendar
FOR SELECT
TO anon, authenticated
USING (true);
