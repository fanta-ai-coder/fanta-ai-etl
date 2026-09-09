-- ======================================================================
-- AGGIUNTA COLONNE PREDIZIONE MACHINE LEARNING SU player_kpi_summary
-- ======================================================================

ALTER TABLE public.player_kpi_summary
ADD COLUMN IF NOT EXISTS stima_prezzo_1000 NUMERIC,
ADD COLUMN IF NOT EXISTS range_min_1000 NUMERIC,
ADD COLUMN IF NOT EXISTS range_max_1000 NUMERIC,
ADD COLUMN IF NOT EXISTS stima_prezzo_500 NUMERIC,
ADD COLUMN IF NOT EXISTS range_min_500 NUMERIC,
ADD COLUMN IF NOT EXISTS range_max_500 NUMERIC,
ADD COLUMN IF NOT EXISTS rmse_modello_1000 NUMERIC,
ADD COLUMN IF NOT EXISTS r2_modello NUMERIC;
