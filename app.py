import os
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from supabase import create_client


# ==========================================
# 1. PAGE CONFIG & DESIGN SYSTEM (M3 DARK)
# ==========================================

st.set_page_config(
    page_title="FantaAI Analytics Pro — Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* --------------------------------------------
   GLOBAL STYLE RESET
-------------------------------------------- */
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
}

section.main, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
    background-color: #0B0F19 !important;
    padding-top: 4.5rem !important;
    padding-bottom: 2rem !important;
}

/* --------------------------------------------
   SCROLLBAR CUSTOM
-------------------------------------------- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: #10B981; }

/* ─────────────────────────────────────────────────────────────
   GLOBAL & WIDGET RESET
───────────────────────────────────────────────────────────── */
.stTextInput input, .stSelectbox [data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 6px !important;
    color: #F9FAFB !important;
    font-size: 0.78rem !important;
    min-height: 32px !important;
    height: 32px !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    min-height: 32px !important;
    height: 32px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    font-size: 0.78rem !important;
}

/* TIGHTEN VERTICAL GAP IN LEFT COLUMN */
div[data-testid="column"]:first-child [data-testid="stVerticalBlock"] {
    gap: 4px !important;
}


/* ─────────────────────────────────────────────────────────────
   1. ROLE BUTTONS (Colore per ruolo + bordo attivo)
───────────────────────────────────────────────────────────── */
/* Role filter buttons only */
[class*="st-key-btn_role_"] button {
    min-height: 28px !important;
    height: 28px !important;
    padding: 2px 0px !important;
    font-size: 0.75rem !important;
    font-weight: 800 !important;
    border-radius: 6px !important;
    white-space: nowrap !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
}

/* ALL Button: Grigio */
[class*="st-key-btn_role_all"] button {
    background-color: rgba(148, 163, 184, 0.12) !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    color: #F8FAFC !important;
}
[class*="st-key-btn_role_all"] button p {
    color: #F8FAFC !important;
    font-weight: 800 !important;
}

/* P Button: Giallo / Oro */
[class*="st-key-btn_role_p"] button {
    background-color: rgba(245, 158, 11, 0.14) !important;
    border: 1px solid rgba(245, 158, 11, 0.45) !important;
    color: #F59E0B !important;
}
[class*="st-key-btn_role_p"] button p {
    color: #F59E0B !important;
    font-weight: 800 !important;
}

/* D Button: Blu */
[class*="st-key-btn_role_d"] button {
    background-color: rgba(59, 130, 246, 0.14) !important;
    border: 1px solid rgba(59, 130, 246, 0.45) !important;
    color: #3B82F6 !important;
}
[class*="st-key-btn_role_d"] button p {
    color: #3B82F6 !important;
    font-weight: 800 !important;
}

/* C Button: Verde */
[class*="st-key-btn_role_c"] button {
    background-color: rgba(16, 185, 129, 0.14) !important;
    border: 1px solid rgba(16, 185, 129, 0.45) !important;
    color: #10B981 !important;
}
[class*="st-key-btn_role_c"] button p {
    color: #10B981 !important;
    font-weight: 800 !important;
}

/* A Button: Rosso */
[class*="st-key-btn_role_a"] button {
    background-color: rgba(239, 68, 68, 0.14) !important;
    border: 1px solid rgba(239, 68, 68, 0.45) !important;
    color: #EF4444 !important;
}
[class*="st-key-btn_role_a"] button p {
    color: #EF4444 !important;
    font-weight: 800 !important;
}

/* Tasto Selezionato: solo il bordino viene evidenziato con un bagliore */
[class*="st-key-btn_role_"][class*="_act"] button {
    border: 2px solid #FFFFFF !important;
    box-shadow: 0 0 8px rgba(255, 255, 255, 0.45) !important;
}

/* ─────────────────────────────────────────────────────────────
   2. ROSTER LISTA GIOCATORI (Eliminazione Totale Pallino & Card 100%)
───────────────────────────────────────────────────────────── */

/* 2.1 Eliminazione totale di qualsiasi cerchio / pallino / indicator radio */
div[data-testid="stRadio"] input[type="radio"],
div[data-testid="stRadio"] [data-testid="stWidgetSelectionIndicator"],
div[data-testid="stRadio"] label [data-testid="stWidgetSelectionIndicator"],
div[data-testid="stRadio"] label > div:first-child:not([data-testid="stRadioOptionLabel"]):not([data-testid="stMarkdownContainer"]),
div[data-testid="stRadio"] label > span:first-child,
div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child:not([data-testid="stRadioOptionLabel"]),
div[data-testid="stRadio"] [data-baseweb="radio"] span,
div[data-testid="stRadio"] [data-baseweb="radio"] svg,
div[data-testid="stRadio"] label svg,
div[data-testid="stRadio"] label [aria-hidden="true"],
div[data-testid="stRadio"] [data-baseweb="radio"] [aria-hidden="true"] {
    display: none !important;
    width: 0px !important;
    height: 0px !important;
    max-width: 0px !important;
    max-height: 0px !important;
    min-width: 0px !important;
    min-height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
    position: absolute !important;
}

div[data-testid="stRadio"] label::before,
div[data-testid="stRadio"] label::after {
    display: none !important;
    content: none !important;
}

/* 2.2 Forzatura larghezza 100% dal container fino a ogni singola card nello scroll */
div[data-testid="column"]:first-child,
div[data-testid="column"]:first-child > div,
div[data-testid="column"]:first-child div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="column"]:first-child div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stRadio"],
div[data-testid="stRadio"] > div,
div[data-testid="stRadio"] div[role="radiogroup"] {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] {
    gap: 8px !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > div,
div[data-testid="stRadio"] [data-baseweb="radio"],
div[data-testid="stRadio"] label[data-baseweb="radio"],
div[data-testid="stRadio"] label {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    align-self: stretch !important;
    flex: 1 1 100% !important;
}

div[data-testid="stRadio"] label {
    background: #111827 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stRadio"] label:hover {
    background: #1E293B !important;
    border-color: rgba(16, 185, 129, 0.4) !important;
}

div[data-testid="stRadio"] label:has(input:checked),
div[data-testid="stRadio"] label[aria-checked="true"] {
    background: rgba(16, 185, 129, 0.14) !important;
    border: 1.5px solid #10B981 !important;
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.25) !important;
}

/* 2.3 Contenuto e testo sempre visibili e a tutta larghezza */
div[data-testid="stRadio"] [data-testid="stRadioOptionLabel"],
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

div[data-testid="stRadio"] [data-testid="stRadioOptionLabel"] *,
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] * {
    visibility: visible !important;
    opacity: 1 !important;
}

div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
    white-space: pre-line !important;
    line-height: 1.6 !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    width: 100% !important;
}

/* 2.4 Pulsante Aggiungi alla Rosa (+) Verde Smeraldo */
div[class*="st-key-btn_roster_"] button[kind="primary"],
div[class*="st-key-btn_roster_"] button[data-testid="stBaseButton-primary"],
div[class*="st-key-btn_roster_"] button.st-emotion-cache-1280hey,
div[class*="st-key-btn_roster_"] button:not([kind="secondary"]):not([disabled]) {
    background: #10B981 !important;
    background-color: #10B981 !important;
    border: 1px solid #059669 !important;
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.25rem !important;
    line-height: 1 !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25) !important;
}

div[class*="st-key-btn_roster_"] button[kind="primary"]:hover,
div[class*="st-key-btn_roster_"] button[data-testid="stBaseButton-primary"]:hover,
div[class*="st-key-btn_roster_"] button:not([kind="secondary"]):not([disabled]):hover {
    background: #059669 !important;
    background-color: #059669 !important;
    border-color: #34D399 !important;
    box-shadow: 0 0 16px rgba(16, 185, 129, 0.45) !important;
    transform: translateY(-1px) !important;
}

div[class*="st-key-btn_roster_"] button[kind="primary"] p,
div[class*="st-key-btn_roster_"] button[data-testid="stBaseButton-primary"] p,
div[class*="st-key-btn_roster_"] button:not([kind="secondary"]):not([disabled]) p {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.25rem !important;
    margin: 0 !important;
}

/* ─────────────────────────────────────────────────────────────
   3. TUTTE LE LABEL IN BIANCO PURO
───────────────────────────────────────────────────────────── */
div[data-testid="stSelectbox"] label p,
div[data-testid="stSelectbox"] label,
div[data-testid="stCheckbox"] label p,
div[data-testid="stCheckbox"] label,
div[data-testid="stSlider"] label p,
div[data-testid="stSlider"] label,
.stTextInput label p,
.stTextInput label {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    margin-bottom: 2px !important;
}

/* --------------------------------------------
   CLASSI DI UTILITÀ (per eventuali contenitori)
-------------------------------------------- */
.glass-panel {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
}

.kpi-card {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
}

.kpi-card .kpi-label {
    color: #94A3B8;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.kpi-card .kpi-value {
    color: #F8FAFC;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 4px 0;
    font-family: 'Inter', sans-serif;
}

.kpi-card .kpi-sub {
    color: #64748B;
    font-size: 0.75rem;
}

.sub-card {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
}

.sub-card .sub-label {
    color: #94A3B8;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.sub-card .sub-value {
    color: #F8FAFC;
    font-size: 1.2rem;
    font-weight: 800;
    margin: 3px 0 2px 0;
    font-family: 'Inter', sans-serif;
}

.sub-card .sub-desc {
    color: #64748B;
    font-size: 0.7rem;
}


/* Badges di ruolo */
.badge-tier {
    background: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
}

.badge-role-A { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-role-C { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-role-D { background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-role-P { background: rgba(180, 83, 9, 0.15); color: #F59E0B; border: 1px solid rgba(180, 83, 9, 0.3); }


/* --------------------------------------------
   V2: TABS & PITCH / FORMATION SYSTEM (COMPACT)
-------------------------------------------- */
div[data-testid="stTabs"] button {
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 8px 18px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    color: #94A3B8 !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    background-color: rgba(16, 185, 129, 0.15) !important;
    color: #34D399 !important;
    border-bottom: 2px solid #10B981 !important;
}

.pitch-container {
    background: radial-gradient(circle at 50% 50%, #113f2b 0%, #0a2419 75%, #05140d 100%);
    border: 1.5px solid rgba(16, 185, 129, 0.35);
    border-radius: 14px;
    padding: 22px 16px;
    max-width: 620px;
    width: 100%;
    min-height: 540px;
    margin: 0 auto 12px auto;
    position: relative;
    box-shadow: inset 0 0 45px rgba(0, 0, 0, 0.65), 0 4px 16px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.pitch-row-title {
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #34D399;
    margin-bottom: 6px;
    text-align: center;
    opacity: 0.9;
}

.pitch-row-cards {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 6px;
}

.player-pitch-card {
    background: rgba(17, 24, 39, 0.95);
    border: 1.5px solid rgba(255, 255, 255, 0.16);
    backdrop-filter: blur(8px);
    border-radius: 9px;
    padding: 6px 10px;
    text-align: center;
    width: 122px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    transition: all 0.15s ease;
}

.player-pitch-card:hover {
    border-color: #10B981;
    transform: translateY(-2px);
}

.player-pitch-card-empty {
    background: rgba(17, 24, 39, 0.4);
    border: 1.5px dashed rgba(255, 255, 255, 0.22);
    border-radius: 9px;
    padding: 8px 6px;
    text-align: center;
    width: 112px;
    color: #64748B;
    font-size: 0.76rem;
}

.kpi-card-compact {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 12px;
    display: flex;
    flex-direction: column;
}

.kpi-card-compact .kpi-label {
    color: #94A3B8;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.kpi-card-compact .kpi-value {
    color: #F8FAFC;
    font-size: 1.35rem;
    font-weight: 800;
    margin: 2px 0;
    font-family: 'Inter', sans-serif;
}

.kpi-card-compact .kpi-sub {
    color: #64748B;
    font-size: 0.68rem;
}

.roster-role-header-compact {
    font-size: 0.98rem;
    font-weight: 800;
    color: #F8FAFC;
    margin-top: 24px !important;
    margin-bottom: 16px !important;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255, 255, 255, 0.04);
    padding: 7px 12px;
    border-radius: 6px;
    border-left: 4px solid #10B981;
}

/* La prima intestazione ruolo parte compatta senza gap eccessivo sopra */
div[data-testid="column"] .roster-role-header-compact:first-of-type {
    margin-top: 4px !important;
}

/* Assicura che i blocchi verticali mantengano sempre flex-direction column per evitare sovrapposizioni */
div[data-testid="stVerticalBlock"] {
    flex-direction: column !important;
}

/* =========================================================
   V2: FIX OUTER SCOUT LAYOUT (ELIMINATE EMPTY GAP & FULL-WINDOW BORDER)
   ========================================================= */
div[data-testid="stHorizontalBlock"]:has(> div [data-testid="column"]:first-child:has(input[placeholder*="Cerca"])) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    align-items: flex-start !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(> div [data-testid="column"]:first-child:has(input[placeholder*="Cerca"])) > div[data-testid="column"] {
    align-self: flex-start !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* =========================================================
   V2: TABELLA ROSA SUPER COMPATTA + ALLINEAMENTO PERFETTO
   ========================================================= */
/* Forza l'allineamento in alto delle colonne della Tab 2 (Rosa & Formazione Consigliata) */
div[data-testid="stHorizontalBlock"]:has(.pitch-container) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    align-items: flex-start !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(.pitch-container) > div[data-testid="column"] {
    align-self: flex-start !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* Stile applicato ESCLUSIVAMENTE alla singola riga giocatore nella lista della rosa.
   Usa :not(:has(div[data-testid="stHorizontalBlock"])) per NON matchare mai il container principale */
div[data-testid="stHorizontalBlock"]:has([class*="st-key-del_r_"]):not(:has(div[data-testid="stHorizontalBlock"])) {
    display: flex !important;
    align-items: center !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    padding: 3px 0 !important;
    min-height: 28px !important;
}

div[data-testid="stHorizontalBlock"]:has([class*="st-key-del_r_"]):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"] {
    display: flex !important;
    align-items: center !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has([class*="st-key-del_r_"]):not(:has(div[data-testid="stHorizontalBlock"])) [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: stretch !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    gap: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has([class*="st-key-del_r_"]):not(:has(div[data-testid="stHorizontalBlock"])) [data-testid="element-container"] {
    display: flex !important;
    align-items: center !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    gap: 0 !important;
}

.roster-row-nom {
    font-size: 0.98rem;
    font-weight: 800;
    color: #F8FAFC;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    margin: 0;
    padding: 0;
    width: 100%;
}
.roster-row-fm {
    font-size: 0.90rem;
    color: #34D399;
    font-weight: 700;
    text-align: right;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin: 0;
    padding: 0;
    width: 100%;
}
.roster-row-prz {
    font-size: 0.94rem;
    color: #F59E0B;
    font-weight: 800;
    text-align: right;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin: 0;
    padding: 0;
    width: 100%;
}

div[class*="st-key-del_r_"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}

div[class*="st-key-del_r_"] div[data-testid="stButton"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    margin: 0 !important;
    padding: 0 !important;
    width: auto !important;
    height: auto !important;
}

div[class*="st-key-del_r_"] button {
    width: 17px !important;
    height: 17px !important;
    min-width: 17px !important;
    min-height: 17px !important;
    max-width: 17px !important;
    max-height: 17px !important;
    padding: 0 !important;
    margin: 0 !important;
    background: #DC2626 !important;
    background-color: #DC2626 !important;
    border: 1px solid #B91C1C !important;
    border-radius: 3px !important;
    box-shadow: 0 1px 3px rgba(220, 38, 38, 0.35) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    line-height: 1 !important;
}

div[class*="st-key-del_r_"] button:hover {
    background: #EF4444 !important;
    background-color: #EF4444 !important;
    border-color: #F87171 !important;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.6) !important;
    transform: scale(1.1) !important;
}

div[class*="st-key-del_r_"] button p {
    color: #FFFFFF !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.top-header {
    background: #111827;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 20px;
    border-radius: 12px;
    margin-bottom: 16px;
}
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# 2. SUPABASE & DATA FETCHING
# ==========================================

import env_loader

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ SUPABASE_URL e/o SUPABASE_KEY non configurate.")
    st.stop()


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


@st.cache_data(ttl=300)
def load_kpi_summary():
    """Carica la tabella precalcolata player_kpi_summary (o fallback locale) e integra le previsioni ML d'asta."""
    df = pd.DataFrame()
    try:
        if supabase:
            res = supabase.table("player_kpi_summary").select("*").execute()
            if res.data and len(res.data) > 0:
                df = pd.DataFrame(res.data)
    except Exception:
        pass

    # Fallback locale
    if df.empty:
        local_csv = Path(__file__).resolve().parent / "player_kpi_summary.csv"
        if local_csv.exists():
            df = pd.read_csv(local_csv)
        else:
            url = "https://raw.githubusercontent.com/fanta-ai-coder/fanta-ai-etl/refs/heads/main/player_kpi_summary.csv"
            try:
                df = pd.read_csv(url)
            except Exception:
                df = pd.DataFrame()

    # Integrazione delle predizioni ML d'asta (da file locale o se non presenti in Supabase)
    pred_csv = Path(__file__).resolve().parent / "auction_predictions.csv"
    if not df.empty and pred_csv.exists():
        try:
            preds = pd.read_csv(pred_csv)
            ml_cols = [
                "player_id", "stima_prezzo_1000", "range_min_1000", "range_max_1000",
                "stima_prezzo_500", "range_min_500", "range_max_500", "rmse_modello_1000", "r2_modello"
            ]
            avail_ml = [c for c in ml_cols if c in preds.columns]
            if "player_id" in avail_ml:
                cols_to_drop = [c for c in avail_ml if c in df.columns and c != "player_id"]
                if cols_to_drop:
                    df = df.drop(columns=cols_to_drop)
                df = pd.merge(df, preds[avail_ml], on="player_id", how="left")
        except Exception:
            pass

    return df


@st.cache_data(ttl=600)
def fetch_player_matches(player_id):
    """Carica lo storico partite on-demand solo per il singolo giocatore selezionato."""
    try:
        if supabase:
            res = (
                supabase.table("player_stats_history")
                .select("*")
                .eq("player_id", int(player_id))
                .execute()
            )
            if res.data:
                return pd.DataFrame(res.data)
    except Exception:
        pass
    return pd.DataFrame()


# ==========================================
# 3. STATISTICAL UTILITIES
# ==========================================

def normalize_player_id_series(series):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.round().astype("Int64")


def normalize_dataframe(df):
    if df.empty:
        return df.copy()
    result = df.copy()
    if "player_id" in result.columns:
        result["player_id"] = normalize_player_id_series(result["player_id"])
    return result


def numeric_series(df, column):
    if column not in df.columns:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def safe_sum(df, column):
    if column not in df.columns:
        return 0.0
    return float(numeric_series(df, column).fillna(0).sum())


def safe_mean(df, column):
    if column not in df.columns:
        return 0.0
    values = numeric_series(df, column).dropna()
    return float(values.mean()) if not values.empty else 0.0


def safe_variance(df, column):
    if column not in df.columns:
        return None
    values = numeric_series(df, column).dropna()
    if len(values) < 2:
        return None
    val = values.var(ddof=1)
    return None if pd.isna(val) else float(val)


def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/D"
    return f"{value:.{decimals}f}"


def remove_starred_vote_rows(df):
    if df.empty or "voto" not in df.columns:
        return df.copy()
    raw_vote = df["voto"].astype(str).str.strip()
    starred = raw_vote.str.contains(r"\*", regex=True, na=False)
    return df.loc[~starred].copy() if starred.any() else df.copy()


def calculate_fantavoto(df):
    result = df.copy()
    if "voto" not in result.columns:
        result["fanta_voto_calcolato"] = float("nan")
        return result

    voto = numeric_series(result, "voto").fillna(0)
    gf = numeric_series(result, "gf").fillna(0)
    ass = numeric_series(result, "ass").fillna(0)
    rf = numeric_series(result, "rf").fillna(0)
    au = numeric_series(result, "au").fillna(0)
    esp = numeric_series(result, "esp").fillna(0)
    amm = numeric_series(result, "amm").fillna(0)

    clean_sheet = pd.Series(0.0, index=result.index)
    penalty_saved = pd.Series(0.0, index=result.index)
    gol_subiti = pd.Series(0.0, index=result.index)

    for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
        if c in result.columns:
            clean_sheet = numeric_series(result, c).fillna(0)
            break

    for c in ["rp", "rigori_parati", "rigore_parato"]:
        if c in result.columns:
            penalty_saved = numeric_series(result, c).fillna(0)
            break

    for c in ["gs", "gol_subiti"]:
        if c in result.columns:
            gol_subiti = numeric_series(result, c).fillna(0)
            break

    if "ruolo" in result.columns:
        is_p = result["ruolo"].astype(str).str.strip().str.upper().eq("P")
        clean_sheet = clean_sheet.where(is_p, 0)
        gol_subiti = gol_subiti.where(is_p, 0)

    result["fanta_voto_calcolato"] = (
        voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (penalty_saved * 3) - gol_subiti
    )
    result.loc[numeric_series(result, "voto").isna(), "fanta_voto_calcolato"] = float("nan")
    return result


def calculate_bonus_malus(df):
    res = calculate_fantavoto(df)
    res["bonus_malus"] = res["fanta_voto_calcolato"] - numeric_series(res, "voto")
    return res


def calculate_relative_metrics(p_stats, is_goalkeeper=False):
    seasons = p_stats["stagione"].dropna().astype(str).str.strip().nunique() if "stagione" in p_stats.columns else 0
    if seasons <= 0:
        return {
            "stagioni": 0, "presenze_medie": 0.0, "presenza_pct": 0.0,
            "gol_stagione": 0.0, "assist_stagione": 0.0, "rigori_segnati": 0.0,
            "rigori_sbagliati": 0.0, "ammonizioni": 0.0, "espulsioni": 0.0,
            "gs_stagione": 0.0, "rigori_parati": 0.0
        }

    presenze_totali = numeric_series(p_stats, "voto").count()
    presenze_medie = presenze_totali / seasons
    presenza_pct = min(100.0, (presenze_medie / 38) * 100)

    if is_goalkeeper:
        gs_tot = safe_sum(p_stats, "gs")
        rp_tot = safe_sum(p_stats, "rp")
        gf_tot = 0
        rf_tot = 0
    else:
        gf_tot = safe_sum(p_stats, "gf") + safe_sum(p_stats, "rf")
        rf_tot = safe_sum(p_stats, "rf")
        gs_tot = 0
        rp_tot = 0

    return {
        "stagioni": seasons,
        "presenze_medie": presenze_medie,
        "presenza_pct": presenza_pct,
        "assist_stagione": safe_sum(p_stats, "ass") / seasons,
        "rigori_sbagliati": safe_sum(p_stats, "rs") / seasons,
        "ammonizioni": safe_sum(p_stats, "amm") / seasons,
        "espulsioni": safe_sum(p_stats, "esp") / seasons,
        "gol_stagione": gf_tot / seasons,
        "rigori_segnati": rf_tot / seasons,
        "gs_stagione": gs_tot / seasons,
        "rigori_parati": rp_tot / seasons,
    }


def varianza_gol_binaria(p_stats):
    if p_stats.empty or "giornata" not in p_stats.columns:
        return 0.0
    gol_g = p_stats.groupby("giornata").apply(
        lambda df: 1 if (safe_sum(df, "gf") + safe_sum(df, "rf")) > 0 else 0
    )
    return 0.0 if len(gol_g) <= 1 else float(gol_g.var(ddof=1))


def get_slot_asta(ruolo, rank_ruolo):
    r = str(ruolo).upper().strip()
    rk = int(rank_ruolo) if pd.notna(rank_ruolo) and rank_ruolo is not None else 99
    
    if r == "A":
        if rk <= 6:
            return "👑 1° SLOT TOP", "#10B981", "rgba(16, 185, 129, 0.15)"
        elif rk <= 14:
            return "⭐ 2° SLOT TITOLARE", "#38BDF8", "rgba(56, 189, 248, 0.15)"
        elif rk <= 24:
            return "🔷 3° SLOT ROTAZIONE", "#F59E0B", "rgba(245, 158, 11, 0.15)"
        else:
            return "🟢 SCOMMESSA / LOW-COST", "#94A3B8", "rgba(148, 163, 184, 0.15)"
    elif r == "C":
        if rk <= 8:
            return "👑 1° SLOT TOP", "#10B981", "rgba(16, 185, 129, 0.15)"
        elif rk <= 18:
            return "⭐ 2° SLOT TITOLARE", "#38BDF8", "rgba(56, 189, 248, 0.15)"
        elif rk <= 30:
            return "🔷 3° SLOT ROTAZIONE", "#F59E0B", "rgba(245, 158, 11, 0.15)"
        else:
            return "🟢 SCOMMESSA / LOW-COST", "#94A3B8", "rgba(148, 163, 184, 0.15)"
    elif r == "D":
        if rk <= 8:
            return "👑 1° SLOT TOP", "#10B981", "rgba(16, 185, 129, 0.15)"
        elif rk <= 20:
            return "⭐ 2° SLOT TITOLARE", "#38BDF8", "rgba(56, 189, 248, 0.15)"
        elif rk <= 35:
            return "🔷 3° SLOT ROTAZIONE", "#F59E0B", "rgba(245, 158, 11, 0.15)"
        else:
            return "🟢 SCOMMESSA / LOW-COST", "#94A3B8", "rgba(148, 163, 184, 0.15)"
    else: # P
        if rk <= 4:
            return "👑 1° SLOT TOP (BIG)", "#10B981", "rgba(16, 185, 129, 0.15)"
        elif rk <= 10:
            return "⭐ 2° SLOT TITOLARE", "#38BDF8", "rgba(56, 189, 248, 0.15)"
        else:
            return "🔷 3° SLOT LOW-COST", "#94A3B8", "rgba(148, 163, 184, 0.15)"


def format_bonus_frequency(player_row):
    ruolo = str(player_row.get("ruolo", "")).upper().strip()
    presenze = float(player_row.get("presenze_medie", 0.0)) if pd.notna(player_row.get("presenze_medie")) else 0.0
    
    if ruolo == "P":
        gs = float(player_row.get("gs_stagione", 0.0)) if pd.notna(player_row.get("gs_stagione")) else 0.0
        if gs > 0 and presenze > 0:
            ratio = presenze / gs
            if abs(ratio - 1.0) <= 0.1:
                return "1 gol subito a partita", f"{gs/presenze:.2f} GS/partita", "Frequenza GS"
            elif abs(ratio - 1.5) <= 0.15:
                return "1 gol ogni partita e mezza", f"{gs/presenze:.2f} GS/partita", "Frequenza GS"
            elif ratio < 1.0:
                return f"{1.0/ratio:.1f} gol a partita", f"{gs/presenze:.2f} GS/partita", "Frequenza GS"
            else:
                return f"1 gol ogni {ratio:.1f} partite", f"{gs/presenze:.2f} GS/partita", "Frequenza GS"
        else:
            return "Porta inviolata frequente", "Zero o minimi gol subiti", "Frequenza GS"

    gol = float(player_row.get("gol_stagione", 0.0)) if pd.notna(player_row.get("gol_stagione")) else 0.0
    ass = float(player_row.get("assist_stagione", 0.0)) if pd.notna(player_row.get("assist_stagione")) else 0.0

    if gol > 0 and presenze > 0:
        ratio = presenze / gol
        if abs(ratio - 1.0) <= 0.1:
            val = "1 gol a partita"
        elif abs(ratio - 1.5) <= 0.15:
            val = "1 gol ogni partita e mezza"
        elif ratio < 1.0:
            val = f"{1.0/ratio:.1f} gol a partita"
        else:
            val = f"1 gol ogni {ratio:.1f} partite"
        return val, f"{gol/presenze:.2f} gol/partita", "Frequenza Gol"
    elif ass > 0 and presenze > 0:
        ratio = presenze / ass
        if abs(ratio - 1.0) <= 0.1:
            val = "1 assist a partita"
        elif abs(ratio - 1.5) <= 0.15:
            val = "1 assist ogni partita e mezza"
        elif ratio < 1.0:
            val = f"{1.0/ratio:.1f} assist a partita"
        else:
            val = f"1 assist ogni {ratio:.1f} partite"
        return val, f"{ass/presenze:.2f} assist/partita", "Frequenza Assist"
    else:
        return "Nessun bonus atteso", "Bonus rari o difensivi", "Frequenza Bonus"


def build_radar_dna_chart(categories, values):
    vals = values + [values[0]]
    cats = categories + [categories[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals,
        theta=cats,
        fill='toself',
        fillcolor='rgba(16, 185, 129, 0.22)',
        line=dict(color='#10B981', width=2.5),
        marker=dict(size=6, color='#34D399'),
        hoverinfo='text',
        hovertext=[f"<b>{c}</b>: {v:.0f}/100" for c, v in zip(cats, vals)]
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(17, 24, 39, 0.5)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                linecolor="rgba(255, 255, 255, 0.08)",
                gridcolor="rgba(255, 255, 255, 0.08)",
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color="#CBD5E1", family="Plus Jakarta Sans"),
                linecolor="rgba(255, 255, 255, 0.08)",
                gridcolor="rgba(255, 255, 255, 0.08)",
            )
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=260,
        margin=dict(l=35, r=35, t=25, b=25)
    )
    return fig


def season_sort_key(value):
    try:
        return int(str(value).strip().split("/")[0])
    except Exception:
        return -1


def build_rolling_data(player_stats, window=5):
    if player_stats.empty or any(c not in player_stats.columns for c in ["stagione", "giornata"]):
        return pd.DataFrame()

    res = player_stats.copy()
    res["giornata"] = pd.to_numeric(res["giornata"], errors="coerce")
    res = res[res["giornata"].notna()].copy()
    if res.empty:
        return pd.DataFrame()

    res["giornata"] = res["giornata"].astype(int)
    res["stagione"] = res["stagione"].astype(str).str.strip()
    res["_season_sort"] = res["stagione"].apply(season_sort_key)
    res = res.sort_values(["_season_sort", "giornata"]).reset_index(drop=True)
    res = calculate_fantavoto(res)

    if "voto" in res.columns:
        res["voto"] = pd.to_numeric(res["voto"], errors="coerce")
        res["media_mobile_voto"] = res.groupby("stagione", sort=False)["voto"].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )

    res["media_mobile_fanta"] = res.groupby("stagione", sort=False)["fanta_voto_calcolato"].transform(
        lambda x: x.rolling(window=window, min_periods=1).mean()
    )
    res["periodo"] = res["stagione"] + " G" + res["giornata"].astype(str)
    return res


def get_latest_season(df):
    if df.empty or "stagione" not in df.columns:
        return None
    seasons = df["stagione"].dropna().astype(str).str.strip()
    seasons = seasons[seasons != ""]
    return max(seasons.unique(), key=season_sort_key) if not seasons.empty else None


def get_latest_quote_row(player_quotes):
    if player_quotes.empty:
        return None
    res = player_quotes.copy()
    if "stagione" in res.columns:
        res["_season_sort"] = res["stagione"].apply(season_sort_key)
        res = res.sort_values("_season_sort")
    return res.iloc[-1]


def get_player_ranking(ranking_df, player_id, stagione=None):
    if ranking_df.empty or "player_id" not in ranking_df.columns:
        return None
    ranking = ranking_df.copy()
    ranking["player_id"] = normalize_player_id_series(ranking["player_id"])
    try:
        pid = int(float(player_id))
    except Exception:
        return None

    ranking = ranking[ranking["player_id"] == pid].copy()
    if ranking.empty:
        return None

    if stagione is not None and "stagione" in ranking.columns:
        current = ranking[ranking["stagione"].astype(str).str.strip() == str(stagione).strip()].copy()
        if not current.empty:
            ranking = current

    if len(ranking) > 1:
        if "calculated_at" in ranking.columns:
            ranking["calculated_at"] = pd.to_datetime(ranking["calculated_at"], errors="coerce")
            ranking = ranking.sort_values("calculated_at")
        elif "stagione" in ranking.columns:
            ranking["_season_sort"] = ranking["stagione"].apply(season_sort_key)
            ranking = ranking.sort_values("_season_sort")

    return ranking.iloc[-1]


@st.cache_data(ttl=600)
def compute_player_summaries(stats_df, quot_df, ranking_df, titolari_df):
    if quot_df.empty:
        return quot_df.copy()

    base = quot_df.copy()
    base["player_id"] = normalize_player_id_series(base["player_id"])

    if not ranking_df.empty and "player_id" in ranking_df.columns:
        rdf = ranking_df.copy()
        rdf["player_id"] = normalize_player_id_series(rdf["player_id"])
        rank_cols = [
            "player_id", "indice_finale", "rank_ruolo", "totale_ruolo",
            "rank_generale", "totale_generale", "titolarita_score",
            "presenze_pesate", "forma_attuale_score", "performance_score"
        ]
        avail_rank_cols = [c for c in rank_cols if c in rdf.columns]
        rdf_unique = rdf.drop_duplicates(subset=["player_id"])[avail_rank_cols]
        base = pd.merge(base, rdf_unique, on="player_id", how="left")
    else:
        for c in ["indice_finale", "rank_ruolo", "totale_ruolo", "rank_generale", "totale_generale", "titolarita_score", "presenze_pesate"]:
            base[c] = None

    if not titolari_df.empty:
        tdf = titolari_df.copy()
        tdf["nome_norm"] = tdf["nome_giocatore"].astype(str).str.upper().str.strip()
        tdf["squadra_norm"] = tdf["squadra"].astype(str).str.upper().str.strip()

        base["nome_norm"] = base["nome"].astype(str).str.upper().str.strip()
        base["squadra_norm"] = base["squadra"].astype(str).str.upper().str.strip()

        tdf_unique = tdf.drop_duplicates(subset=["nome_norm", "squadra_norm"])
        base = pd.merge(
            base,
            tdf_unique[["nome_norm", "squadra_norm", "titolarita", "squalificato", "infortunato"]],
            on=["nome_norm", "squadra_norm"],
            how="left"
        )
        base["is_titolare"] = base["titolarita"].astype(str).str.lower().str.strip() == "titolare"
    else:
        base["is_titolare"] = False

    if not stats_df.empty and "player_id" in stats_df.columns:
        sdf = stats_df.copy()
        sdf["player_id"] = normalize_player_id_series(sdf["player_id"])

        if "stagione" in sdf.columns:
            sdf_hist = sdf[sdf["stagione"].astype(str).str.strip() != "2026-27"].copy()
            if sdf_hist.empty:
                sdf_hist = sdf.copy()
        else:
            sdf_hist = sdf.copy()

        voto = numeric_series(sdf_hist, "voto")
        gf = numeric_series(sdf_hist, "gf").fillna(0)
        rf = numeric_series(sdf_hist, "rf").fillna(0)
        ass = numeric_series(sdf_hist, "ass").fillna(0)
        au = numeric_series(sdf_hist, "au").fillna(0)
        esp = numeric_series(sdf_hist, "esp").fillna(0)
        amm = numeric_series(sdf_hist, "amm").fillna(0)
        gs = numeric_series(sdf_hist, "gs").fillna(0)
        rp = numeric_series(sdf_hist, "rp").fillna(0)

        clean_sheet = pd.Series(0.0, index=sdf_hist.index)
        for c in ["pi", "porta_inviolata", "clean_sheet", "imbattuto"]:
            if c in sdf_hist.columns:
                clean_sheet = numeric_series(sdf_hist, c).fillna(0)
                break

        if "ruolo" in sdf_hist.columns:
            is_p = sdf_hist["ruolo"].astype(str).str.strip().str.upper().eq("P")
            clean_sheet = clean_sheet.where(is_p, 0)
            gs = gs.where(is_p, 0)

        fv = voto + (gf * 3) + ass + (rf * 3) - (au * 2) - esp - (amm * 0.5) + clean_sheet + (rp * 3) - gs
        sdf_hist["_fanta_calc"] = fv
        sdf_hist["_voto_num"] = voto

        valid = sdf_hist[voto.notna()]
        agg = valid.groupby("player_id").agg(
            presenze_totali=("_voto_num", "count"),
            fantamedia=("_fanta_calc", "mean"),
            media_voto=("_voto_num", "mean")
        ).reset_index()

        base = pd.merge(base, agg, on="player_id", how="left")
    else:
        base["presenze_totali"] = 0
        base["fantamedia"] = None
        base["media_voto"] = None

    base["presenze_totali"] = base["presenze_totali"].fillna(0).astype(int)
    return base


# ==========================================

# ==========================================
# 3.5 ROSTER STATE & BEST 11 OPTIMIZER
# ==========================================

ROSTER_SAVE_FILE = Path(__file__).parent / "data" / "mia_rosa_session.json"

def load_saved_roster():
    if ROSTER_SAVE_FILE.exists():
        try:
            with open(ROSTER_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("roster", []), data.get("budget_totale", 1000)
        except Exception:
            pass
    return [], 1000

def save_roster_to_disk():
    try:
        ROSTER_SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ROSTER_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "roster": st.session_state.get("roster", []),
                "budget_totale": st.session_state.get("budget_totale", 1000)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Errore nel salvataggio rosa: {e}")

def optimize_best_lineup(roster, forced_module="Auto"):
    modules = {
        "3-4-3": {"P": 1, "D": 3, "C": 4, "A": 3},
        "4-3-3": {"P": 1, "D": 4, "C": 3, "A": 3},
        "3-5-2": {"P": 1, "D": 3, "C": 5, "A": 2},
        "4-4-2": {"P": 1, "D": 4, "C": 4, "A": 2},
        "4-5-1": {"P": 1, "D": 4, "C": 5, "A": 1},
        "5-3-2": {"P": 1, "D": 5, "C": 3, "A": 2},
        "5-4-1": {"P": 1, "D": 5, "C": 4, "A": 1},
    }
    
    by_role = {"P": [], "D": [], "C": [], "A": []}
    for p in roster:
        r = str(p.get("ruolo", "C")).upper().strip()
        if r in by_role:
            by_role[r].append(p)
            
    for r in by_role:
        by_role[r].sort(
            key=lambda x: (
                float(x.get("fantamedia") or 0.0),
                float(x.get("media_voto") or 0.0),
                float(x.get("fvm") or 0.0)
            ),
            reverse=True
        )
        
    candidate_modules = [forced_module] if forced_module in modules else list(modules.keys())
    
    best_score = -1e9
    best_mod_name = candidate_modules[0]
    best_starters = {"P": [], "D": [], "C": [], "A": []}
    best_bench = {"P": [], "D": [], "C": [], "A": []}
    
    for mod_name in candidate_modules:
        req = modules[mod_name]
        starters = {"P": [], "D": [], "C": [], "A": []}
        bench = {"P": [], "D": [], "C": [], "A": []}
        score = 0.0
        
        for r, needed in req.items():
            avail = by_role[r]
            starters[r] = avail[:needed]
            bench[r] = avail[needed:]
            for p in starters[r]:
                score += float(p.get("fantamedia") or p.get("media_voto") or 5.5)
                
        tot_starters = sum(len(s) for s in starters.values())
        weighted_score = score + (tot_starters * 0.1)
        
        if weighted_score > best_score:
            best_score = weighted_score
            best_mod_name = mod_name
            best_starters = starters
            best_bench = bench
            
    raw_score = sum(float(p.get("fantamedia") or p.get("media_voto") or 5.5) for s in best_starters.values() for p in s)
    return {
        "module": best_mod_name,
        "score": raw_score,
        "starters": best_starters,
        "bench": best_bench,
        "requirements": modules[best_mod_name]
    }

@st.dialog("➕ Gestione Calciatore in Rosa")
def modal_aggiungi_giocatore(p_row, stima_ml_val, crediti_disp):
    nome = p_row.get("nome", "Giocatore")
    ruolo = str(p_row.get("ruolo", "-")).upper().strip()
    squadra = p_row.get("squadra", "-")
    fm = float(p_row.get("fantamedia", 0.0)) if pd.notna(p_row.get("fantamedia")) else 0.0
    mv = float(p_row.get("media_voto", 0.0)) if pd.notna(p_row.get("media_voto")) else 0.0
    fvm = int(p_row.get("fvm", 0)) if pd.notna(p_row.get("fvm")) else 0
    quota = int(p_row.get("quotazione_attuale", 0)) if pd.notna(p_row.get("quotazione_attuale")) else 0
    pid = int(p_row.get("player_id"))

    existing = [p for p in st.session_state.roster if p["player_id"] == pid]
    current_count_role = sum(1 for p in st.session_state.roster if p["ruolo"] == ruolo)
    max_slots = {"P": 3, "D": 8, "C": 8, "A": 6}.get(ruolo, 8)
    is_role_full = (current_count_role >= max_slots and not existing)

    crediti_altri = sum(int(p.get("prezzo", 0)) for p in st.session_state.roster if p["player_id"] != pid)
    crediti_disponibili = max(0, st.session_state.budget_totale - crediti_altri)
    
    st.markdown(f"""
    <div style="background: #1E293B; padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 14px;">
        <div style="font-size: 1.2rem; font-weight: 800; color: #F8FAFC;">
            <span class="badge-role-{ruolo}" style="padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; margin-right: 6px;">{ruolo}</span>
            {nome} <span style="font-size: 0.9rem; color: #94A3B8; font-weight: 500;">({squadra})</span>
        </div>
        <div style="display: flex; gap: 14px; margin-top: 8px; font-size: 0.82rem; color: #CBD5E1;">
            <span>⭐ Fantamedia: <b>{fm:.2f}</b></span>
            <span>🎯 Stima Asta ML: <b style="color: #34D399;">{stima_ml_val:.0f} FMV</b></span>
            <span>💰 Listino: <b>{quota}</b></span>
        </div>
        <div style="margin-top: 6px; font-size: 0.78rem; color: {'#F87171' if is_role_full else '#38BDF8'};">
            Slot {ruolo} occupati: <b>{current_count_role} / {max_slots}</b> {'⛔ (Reparto al completo!)' if is_role_full else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_role_full:
        st.error(f"⛔ **Reparto {ruolo} al completo ({current_count_role}/{max_slots})!** Non è consentito aggiungere altri calciatori in questo reparto a meno di non rimuoverne uno.")

    default_price = existing[0]["prezzo"] if existing else max(1, int(round(stima_ml_val)) if stima_ml_val > 0 else 1)
    if crediti_disponibili > 0 and default_price > crediti_disponibili:
        default_price = crediti_disponibili
    elif crediti_disponibili <= 0:
        default_price = 1

    prezzo_acq = st.number_input(
        "Prezzo di Acquisto (FMV / Crediti):",
        min_value=1,
        max_value=max(1, crediti_disponibili),
        value=max(1, min(default_price, max(1, crediti_disponibili))),
        step=1,
        help="Crediti spesi per acquistare questo calciatore all'asta",
        disabled=is_role_full
    )

    is_over_budget = (prezzo_acq > crediti_disponibili) or (crediti_disponibili <= 0)
    if is_over_budget and not is_role_full:
        st.error(f"⛔ **Prezzo superiore ai crediti residui!** Hai a disposizione al massimo **{crediti_disponibili} FMV** per questo acquisto.")
    elif not is_role_full:
        st.caption(f"Crediti residui dopo l'operazione: **{crediti_disponibili - prezzo_acq} FMV**")

    c1, c2 = st.columns(2)
    with c1:
        can_save = (not is_role_full) and (not is_over_budget) and (crediti_disponibili > 0)
        btn_label = "💾 Aggiorna Prezzo" if existing else "➕ Aggiungi alla Rosa"
        if st.button(btn_label, type="primary", use_container_width=True, disabled=(not can_save)):
            if existing:
                existing[0]["prezzo"] = int(prezzo_acq)
            else:
                st.session_state.roster.append({
                    "player_id": pid,
                    "nome": nome,
                    "ruolo": ruolo,
                    "squadra": squadra,
                    "prezzo": int(prezzo_acq),
                    "fantamedia": fm if fm > 0 else mv,
                    "media_voto": mv,
                    "fvm": fvm,
                    "quotazione_attuale": quota,
                    "stima_prezzo": float(stima_ml_val),
                    "is_titolare": bool(p_row.get("is_titolare", False)),
                    "titolarita": str(p_row.get("titolarita", "")),
                    "infortunato": str(p_row.get("infortunato", "")),
                    "gol_stagione": float(p_row.get("gol_stagione", 0.0)) if pd.notna(p_row.get("gol_stagione")) else 0.0,
                    "assist_stagione": float(p_row.get("assist_stagione", 0.0)) if pd.notna(p_row.get("assist_stagione")) else 0.0,
                })
            save_roster_to_disk()
            st.toast(f"✅ {nome} salvato in rosa a {prezzo_acq} FMV!", icon="🎉")
            st.rerun()
    with c2:
        if existing:
            if st.button("🗑️ Rimuovi dalla Rosa", use_container_width=True):
                st.session_state.roster = [p for p in st.session_state.roster if p["player_id"] != pid]
                save_roster_to_disk()
                st.toast(f"🗑️ {nome} rimosso dalla rosa!", icon="ℹ️")
                st.rerun()
        else:
            if st.button("Annulla", use_container_width=True):
                st.rerun()

@st.dialog("⚠️ Azzera Rosa")
def modal_reset_roster():
    st.warning("Sei sicuro di voler azzerare l'intera rosa? Questa azione cancellerà tutti i calciatori acquistati e ripristinerà il budget iniziale.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Sì, Azzera Tutto", type="primary", use_container_width=True):
            st.session_state.roster = []
            save_roster_to_disk()
            st.toast("Rosa azzerata con successo!", icon="🔄")
            st.rerun()
    with c2:
        if st.button("Annulla", use_container_width=True):
            st.rerun()



# ==========================================
# 4. APP TOP BARS & SESSION STATE
# ==========================================

# Inizializzazione Stato Rosa
if "roster" not in st.session_state:
    saved_r, saved_b = load_saved_roster()
    st.session_state.roster = saved_r
    st.session_state.budget_totale = saved_b

if "budget_totale" not in st.session_state:
    st.session_state.budget_totale = 1000

# Calcolo Crediti e Metriche Rosa
crediti_spesi = sum(int(p.get("prezzo", 0)) for p in st.session_state.roster)
crediti_residui = max(0, st.session_state.budget_totale - crediti_spesi)
num_rosa = len(st.session_state.roster)
role_counts = {r: sum(1 for p in st.session_state.roster if p.get("ruolo") == r) for r in ["P", "D", "C", "A"]}
roster_pids = set(int(p.get("player_id")) for p in st.session_state.roster if "player_id" in p)

# Top Application Header con contatori live
st.markdown(f"""
<div class="top-header" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="background: #10B981; color: #0B0F19; border-radius: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.2rem;">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.15rem; color: #F8FAFC; letter-spacing: -0.02em;">
                FantaAI <span style="color: #34D399;">Analytics Pro</span> <span style="font-size: 0.72rem; background: rgba(52, 211, 153, 0.2); color: #34D399; padding: 2px 8px; border-radius: 6px; font-weight: 700; margin-left: 6px;">V2</span>
            </div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
        <div style="background: rgba(16, 185, 129, 0.12); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.8rem; font-weight: 700; color: #F8FAFC;">
            💰 Crediti Residui: <span style="color: #34D399; font-size: 0.95rem;">{crediti_residui}</span> <span style="color: #94A3B8; font-size: 0.75rem;">/ {st.session_state.budget_totale} FMV</span>
        </div>
        <div style="background: rgba(56, 189, 248, 0.12); padding: 5px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 0.8rem; font-weight: 700; color: #F8FAFC;">
            📋 Rosa: <span style="color: #38BDF8; font-size: 0.95rem;">{num_rosa} / 25</span> <span style="color: #94A3B8; font-size: 0.75rem;">(P:{role_counts['P']}/3 D:{role_counts['D']}/8 C:{role_counts['C']}/8 A:{role_counts['A']}/6)</span>
        </div>
        <div style="background: rgba(16, 185, 129, 0.08); padding: 5px 10px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2); color: #34D399; font-size: 0.72rem; font-weight: 600;">
            ● Supabase Live
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 5. DATA LOADING
# ==========================================

summary_df = load_kpi_summary()

if summary_df.empty:
    st.warning("⚠️ Dati KPI non disponibili. Esegui 'python main.py' per precalcolare la tabella.")
    st.stop()

summary_df = normalize_dataframe(summary_df)


# ==========================================
# 6. TABS NAVIGATION (V2)
# ==========================================

tab_scout, tab_rosa = st.tabs([
    "📊 1. Esplora & Analytics",
    "📋 2. La Mia Rosa & Asta Live"
])

with tab_scout:
    col_roster, col_dossier = st.columns([0.43, 0.57], gap="medium")
    
    
    # ------------------------------------------
    # COLONNA SINISTRA: ROSTER & FILTRI COMPATTI
    # ------------------------------------------
    with col_roster:
    
        # 1. Barra di ricerca
        search_query = st.text_input("Ricerca", placeholder="Cerca giocatore o squadra...", label_visibility="collapsed")
    
        # 2. Pulsanti Ruolo Compatti (5 pulsanti con colori specifici)
        if "role_filter" not in st.session_state:
            st.session_state["role_filter"] = "ALL"
    
        cur_role = st.session_state["role_filter"]
    
        b_all, b_p, b_d, b_c, b_a = st.columns(5, gap="small")
        with b_all:
            if st.button("ALL", key="btn_role_all" + ("_act" if cur_role == "ALL" else ""), use_container_width=True):
                st.session_state["role_filter"] = "ALL"
                st.rerun()
        with b_p:
            if st.button("P", key="btn_role_p" + ("_act" if cur_role == "P" else ""), use_container_width=True):
                st.session_state["role_filter"] = "P"
                st.rerun()
        with b_d:
            if st.button("D", key="btn_role_d" + ("_act" if cur_role == "D" else ""), use_container_width=True):
                st.session_state["role_filter"] = "D"
                st.rerun()
        with b_c:
            if st.button("C", key="btn_role_c" + ("_act" if cur_role == "C" else ""), use_container_width=True):
                st.session_state["role_filter"] = "C"
                st.rerun()
        with b_a:
            if st.button("A", key="btn_role_a" + ("_act" if cur_role == "A" else ""), use_container_width=True):
                st.session_state["role_filter"] = "A"
                st.rerun()
    
        selected_role = "Tutti" if cur_role == "ALL" else cur_role
    
        # 3. Club + Ordinamento
        squadre_raw = summary_df["squadra"].dropna().astype(str).str.strip().unique() if "squadra" in summary_df.columns else []
        squadre_list = ["Tutte"] + sorted(list(squadre_raw))
    
        c1, c2 = st.columns(2, gap="small")
        with c1: selected_team = st.selectbox("Club Serie A", squadre_list, index=0)
        with c2: selected_sort = st.selectbox(
            "Ordinamento",
            ["🤖 Stima Prezzo ML", "👑 Indice Ranking", "⭐ Fantamedia", "💰 Quotazione Listino", "🔤 Nome (A-Z)"],
            index=0
        )
    
        # 4. Budget Asta & Solo titolari
        b1, b2 = st.columns([1.1, 1.9], gap="small")
        with b1:
            budget_mode = st.selectbox("Budget Lega", ["1000 FMV", "500 FMV"], index=0)
            is_1000 = (budget_mode == "1000 FMV")
            if is_1000 and st.session_state.budget_totale != 1000 and num_rosa == 0:
                st.session_state.budget_totale = 1000
            elif not is_1000 and st.session_state.budget_totale != 500 and num_rosa == 0:
                st.session_state.budget_totale = 500
        with b2:
            only_titolari = st.checkbox("Solo titolari", value=False)
            min_partite = st.slider("Partite minime", 0, 38, 0, step=1)
    
        # ── APPLICA FILTRI ──────────────────────────────
        quot_view = summary_df.copy()
        stima_col = "stima_prezzo_1000" if is_1000 else "stima_prezzo_500"
    
        if selected_role != "Tutti" and "ruolo" in quot_view.columns:
            quot_view = quot_view[quot_view["ruolo"].astype(str).str.upper().str.strip() == selected_role]
        if selected_team != "Tutte" and "squadra" in quot_view.columns:
            quot_view = quot_view[quot_view["squadra"].astype(str).str.upper().str.strip() == selected_team.upper().strip()]
        if search_query.strip():
            _q = search_query.upper().strip()
            match_nome = quot_view["nome"].astype(str).str.upper().str.contains(_q, na=False) if "nome" in quot_view.columns else False
            match_squadra = quot_view["squadra"].astype(str).str.upper().str.contains(_q, na=False) if "squadra" in quot_view.columns else False
            quot_view = quot_view[match_nome | match_squadra]
        if only_titolari and "is_titolare" in quot_view.columns:
            quot_view = quot_view[quot_view["is_titolare"] == True]
        if min_partite > 0 and "presenze_totali" in quot_view.columns:
            quot_view = quot_view[quot_view["presenze_totali"] >= min_partite]
    
        if selected_sort == "🤖 Stima Prezzo ML" and stima_col in quot_view.columns:
            quot_view = quot_view.sort_values([stima_col, "fvm", "nome"], ascending=[False, False, True], na_position="last")
        elif selected_sort == "👑 Indice Ranking":
            quot_view = quot_view.sort_values(["indice_finale", "quotazione_attuale", "nome"], ascending=[False, False, True], na_position="last")
        elif selected_sort == "⭐ Fantamedia":
            quot_view = quot_view.sort_values(["fantamedia", "presenze_totali", "nome"], ascending=[False, False, True], na_position="last")
        elif selected_sort == "💰 Quotazione Listino":
            quot_view = quot_view.sort_values(["quotazione_attuale", "fvm", "nome"], ascending=[False, False, True], na_position="last")
        elif selected_sort == "🔤 Nome (A-Z)":
            quot_view = quot_view.sort_values(["nome"], ascending=True, na_position="last")
    
        if quot_view.empty:
            st.info("Nessun giocatore trovato con questi filtri.")
            selected_id = None
        else:
            options_df = quot_view.drop_duplicates(subset="player_id").copy()
    
            _ROLE_BADGES = {
                "A": ":red[[A]]",
                "C": ":green[[C]]",
                "D": ":blue[[D]]",
                "P": ":orange[[P]]"
            }
    
            labels, ids = [], []
            for _row in options_df.itertuples():
                _n     = getattr(_row, "nome", "Giocatore")
                _s     = getattr(_row, "squadra", "-")
                _pid   = getattr(_row, "player_id")
                _r     = str(getattr(_row, "ruolo", "")).upper().strip()
                _ind   = getattr(_row, "indice_finale", None)
                _fm    = getattr(_row, "fantamedia", None)
                _fvm   = getattr(_row, "fvm", None)
                _pres  = int(getattr(_row, "presenze_totali", 0) or 0)
                _q_att = getattr(_row, "quotazione_attuale", None)
                _mv    = getattr(_row, "media_voto", None)
                _stima = getattr(_row, stima_col, None)
    
                # FM (FantaMedia con bonus): prioritizza fantamedia, fallback media voto
                _fm_val = f"{float(_fm):.2f}" if pd.notna(_fm) else (f"{float(_mv):.2f}" if pd.notna(_mv) else "—")
                _pg = str(_pres)
                _q = str(int(_q_att)) if pd.notna(_q_att) else "—"
                # FMV (Valore FantaMilioni): stima ML per l'asta
                _fmv_num = str(int(_stima)) if pd.notna(_stima) else (str(int(_fvm)) if pd.notna(_fvm) else "—")
    
                _badge = _ROLE_BADGES.get(_r, f"[{_r}]")
    
                # Riga 1: Solo ruolo, nome e squadra (rimosse stelle e corone)
                _line1 = f"{_badge}  {_n} - {_s}"
                # Riga 2: Distinzione chiara FM (FantaMedia) e FMV (Fantamilioni Asta) con spazi preservati
                _line2 = f"FM: {_fm_val}\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0PG: {_pg}\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0Q: {_q}\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0FMV: {_fmv_num}"
    
                _lbl = f"{_line1}\n{_line2}"
    
                if _lbl in labels:
                    _lbl = f"{_lbl} #{int(_pid)}"
                labels.append(_lbl)
                ids.append(int(_pid))
    
            label_to_id = dict(zip(labels, ids))
            radio_key = "roster_radio"
            prev_label = st.session_state.get(radio_key)
            if prev_label not in labels:
                default_idx = 0
                if "active_player_id" in st.session_state and st.session_state["active_player_id"] in ids:
                    default_idx = ids.index(st.session_state["active_player_id"])
                st.session_state[radio_key] = labels[default_idx]
    
            with st.container(height=720, border=False):
                selected_label = st.radio(
                    "Roster",
                    options=labels,
                    key=radio_key,
                    label_visibility="collapsed"
                )
    
            selected_id = label_to_id.get(selected_label)
            st.session_state["active_player_id"] = selected_id
    
    
    # ------------------------------------------
    # COLONNA DESTRA: DOSSIER ANALITICO
    # ------------------------------------------
    with col_dossier:
        if selected_id is None:
            st.info("👈 Seleziona un giocatore dalla lista a sinistra per aprire la scheda analitica.")
        else:
            player_id = int(float(selected_id))
            p_match = summary_df[summary_df["player_id"] == player_id]
            if p_match.empty:
                st.info("Dati non disponibili per questo calciatore.")
                st.stop()
            player_row = p_match.iloc[0]
    
            nome = player_row.get("nome", "Giocatore")
            ruolo = str(player_row.get("ruolo", "-")).upper().strip()
            squadra = player_row.get("squadra", "-")
    
            titolarita_val = str(player_row.get("titolarita", "")).lower().strip()
            infortunato_val = str(player_row.get("infortunato", "")).lower().strip()
            desc_infortunio = str(player_row.get("desc_infortunio", "")).strip()
    
            tags_html = ""
            if "titolare" in titolarita_val or bool(player_row.get("is_titolare", False)):
                tags_html += '<span style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟢 Titolare</span> '
            elif "panchina" in titolarita_val or "riserva" in titolarita_val:
                tags_html += '<span style="background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🟠 Panchina</span> '
            
            if infortunato_val in ["sì", "si", "true", "1", "yes"] or bool(player_row.get("infortunato", False)):
                tags_html += '<span style="background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🚑 Infortunato</span> '
    
            desc_html = ""
            if desc_infortunio and desc_infortunio.lower() not in ["nan", "none", ""]:
                desc_html = f'<div style="font-size: 0.8rem; color: #FCA5A5; margin-top: 8px; font-weight: 600; background: rgba(239, 68, 68, 0.1); padding: 6px 12px; border-radius: 6px; display: inline-block;">⚠️ {desc_infortunio}</div>'
    
            # --- METRICHE E ASTA (INTEGRAZIONE MODELLO ML) ---
            rk_ruolo = int(player_row.get("rank_ruolo")) if pd.notna(player_row.get("rank_ruolo")) else 1
            tot_ruolo = int(player_row.get("totale_ruolo")) if pd.notna(player_row.get("totale_ruolo")) else 68
            quota_val = int(player_row.get("quotazione_attuale", 38)) if pd.notna(player_row.get("quotazione_attuale")) else 38
            fvm_val = int(player_row.get("fvm", 320)) if pd.notna(player_row.get("fvm")) else 320
    
            # Valori Stima ML e Range basato su RMSE
            stima_ml_raw = player_row.get("stima_prezzo_1000" if is_1000 else "stima_prezzo_500")
            if pd.notna(stima_ml_raw):
                stima_val = float(stima_ml_raw)
                range_min = float(player_row.get("range_min_1000" if is_1000 else "range_min_500", max(1, stima_val - 20)))
                range_max = float(player_row.get("range_max_1000" if is_1000 else "range_max_500", stima_val + 20))
            else:
                scale_f = 1.0 if is_1000 else 0.5
                stima_val = float(fvm_val * scale_f)
                range_min = max(1.0, round(stima_val * 0.85))
                range_max = round(stima_val * 1.15)
    
            rmse_val = float(player_row.get("rmse_modello_1000", 46.5)) / (1.0 if is_1000 else 2.0)
            r2_val = float(player_row.get("r2_modello", 0.47))
    
            slot_badge, slot_color, slot_bg = get_slot_asta(ruolo, rk_ruolo)
    
            rigor_pos = player_row.get("rigorista_pos")
            rigor_str = f"Sì (#{int(rigor_pos)})" if pd.notna(rigor_pos) and int(rigor_pos) > 0 else "No"
    
            st.markdown(f"""
            <div class="glass-panel" style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div style="display: flex; gap: 16px; align-items: center;">
                        <div style="width: 72px; height: 72px; border-radius: 50%; background: #1E293B; border: 2px solid #10B981; display: flex; align-items: center; justify-content: center; font-size: 2rem;">
                            👤
                        </div>
                        <div>
                            <div style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; display: flex; align-items: center; flex-wrap: wrap; gap: 10px;">
                                <span>{nome}</span>
                                <div style="display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                                    <span class="badge-tier badge-role-{ruolo}">{ruolo}</span>
                                    <span style="background: rgba(255,255,255,0.08); color: #F1F5F9; border: 1px solid rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">🛡️ {squadra}</span>
                                    {tags_html}
                                </div>
                            </div>{desc_html}
                            <div style="font-size: 0.8rem; color: #94A3B8; display: flex; gap: 14px; margin-top: 8px; align-items: center; flex-wrap: wrap;">
                                <span>🏆 Rank Ruolo: <b>#{rk_ruolo} / {tot_ruolo}</b></span>
                                <span>🎯 Rigorista: <b>{rigor_str}</b></span>
                                <span>Slot Asta: <b style="color: {slot_color}; background: {slot_bg}; padding: 3px 8px; border-radius: 6px; border: 1px solid {slot_color}55;">{slot_badge}</b></span>
                            </div>
                        </div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 12px; padding: 12px 18px; text-align: right; min-width: 255px;">
                        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 6px; font-size: 0.68rem; color: #34D399; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">
                            <span>🤖 Stima Modello ML</span>
                            <span style="background: rgba(16, 185, 129, 0.2); padding: 1px 6px; border-radius: 4px; font-size: 0.62rem; color: #6EE7B7;">R² {r2_val:.2f}</span>
                        </div>
                        <div style="font-size: 1.75rem; font-weight: 800; color: #F8FAFC; margin: 2px 0;">
                            {stima_val:.0f} <span style="font-size: 0.85rem; color: #94A3B8;">FMV</span>
                        </div>
                        <div style="font-size: 0.74rem; color: #38BDF8; font-weight: 700; margin-bottom: 4px;">
                            🎯 Range Asta (±{rmse_val:.0f}): <b>{range_min:.0f} - {range_max:.0f} FMV</b>
                        </div>
                        <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center; font-size: 0.68rem; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 4px; margin-top: 3px;">
                            <span>FVM: <b style="color: #F8FAFC;">{fvm_val} FMV</b></span>
                            <span style="color: #64748B;">•</span>
                            <span>Listino: <b style="color: #F8FAFC;">{quota_val} FMV</b></span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
            # --- TASTO RAPIDO AGGIUNGI ALLA ROSA / STATO IN ROSA (V2) ---
            act_col1, act_col2 = st.columns([0.68, 0.32], gap="small")
            with act_col1:
                existing_entry = next((p for p in st.session_state.roster if p["player_id"] == player_id), None)
                role_c = sum(1 for p in st.session_state.roster if p["ruolo"] == ruolo)
                role_m = {"P": 3, "D": 8, "C": 8, "A": 6}.get(ruolo, 8)
                role_is_full = (role_c >= role_m and not existing_entry)
    
                if existing_entry:
                    if st.button(f"✅ In Rosa ({existing_entry['prezzo']} FMV) — Modifica / Rimuovi", key=f"btn_roster_{player_id}", type="secondary", use_container_width=True):
                        modal_aggiungi_giocatore(player_row, stima_val, crediti_residui)
                elif role_is_full:
                    st.button(f"⛔ Reparto {ruolo} al Completo ({role_c}/{role_m})", key=f"btn_roster_{player_id}", disabled=True, use_container_width=True)
                elif crediti_residui <= 0:
                    st.button("⛔ Crediti Esauriti (0 FMV)", key=f"btn_roster_{player_id}", disabled=True, use_container_width=True)
                else:
                    if st.button("➕", key=f"btn_roster_{player_id}", type="primary", use_container_width=True, help=f"Aggiungi {nome} alla rosa"):
                        modal_aggiungi_giocatore(player_row, stima_val, crediti_residui)
            with act_col2:
                st.markdown(f"<div style='text-align: right; padding-top: 6px; font-size: 0.8rem; color: #94A3B8;'>Crediti residui: <b style='color: #34D399;'>{crediti_residui} FMV</b></div>", unsafe_allow_html=True)
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            is_goalkeeper = (ruolo == "P")
            fantamedia = float(player_row.get("fantamedia", 0.0)) if pd.notna(player_row.get("fantamedia")) else 0.0
            media_voto = float(player_row.get("media_voto", 0.0)) if pd.notna(player_row.get("media_voto")) else 0.0
            presenza_pct = float(player_row.get("presenza_pct", 0.0)) if pd.notna(player_row.get("presenza_pct")) else 0.0
            presenze_medie = float(player_row.get("presenze_medie", 0.0)) if pd.notna(player_row.get("presenze_medie")) else 0.0
    
            gs_stagione = float(player_row.get("gs_stagione", 0.0)) if pd.notna(player_row.get("gs_stagione")) else 0.0
            rigori_parati = float(player_row.get("rigori_parati", 0.0)) if pd.notna(player_row.get("rigori_parati")) else 0.0
            gol_stagione = float(player_row.get("gol_stagione", 0.0)) if pd.notna(player_row.get("gol_stagione")) else 0.0
            assist_stagione = float(player_row.get("assist_stagione", 0.0)) if pd.notna(player_row.get("assist_stagione")) else 0.0
    
            varianza_v = player_row.get("varianza_voto")
            varianza_bin = player_row.get("varianza_gol")
            ammonizioni = float(player_row.get("ammonizioni", 0.0)) if pd.notna(player_row.get("ammonizioni")) else 0.0
            espulsioni = float(player_row.get("espulsioni", 0.0)) if pd.notna(player_row.get("espulsioni")) else 0.0
    
            # Calcolo frequenza bonus basata su partite
            freq_val, freq_sub, freq_label = format_bonus_frequency(player_row)
    
            # --- MATRICE 4 KPI PRINCIPALI ---
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                diff_suff = fantamedia - 6.0
                suff_sign = f"+{diff_suff:.2f}" if diff_suff >= 0 else f"{diff_suff:.2f}"
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Fantamedia Pesata</div>
                    <div class="kpi-value" style="color: #34D399;">{fantamedia:.2f}</div>
                    <div class="kpi-sub">Sufficienza {suff_sign}</div>
                </div>
                """, unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Media Voto Pura</div>
                    <div class="kpi-value">{media_voto:.2f}</div>
                    <div class="kpi-sub">Stabilità Redazionale</div>
                </div>
                """, unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{freq_label}</div>
                    <div class="kpi-value" style="color: #38BDF8; font-size: 1.22rem; line-height: 1.25; white-space: normal;">{freq_val}</div>
                    <div class="kpi-sub">{freq_sub}</div>
                </div>
                """, unsafe_allow_html=True)
            with k4:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">% Presenze Titolare</div>
                    <div class="kpi-value" style="color: #A78BFA;">{presenza_pct:.1f}%</div>
                    <div class="kpi-sub">{presenze_medie:.1f} Partite/Stagione</div>
                </div>
                """, unsafe_allow_html=True)
    
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
            # --- CALCOLO SCORE DNA RADAR ---
            if is_goalkeeper:
                score_bonus = min(100.0, max(20.0, (fantamedia - 4.0) / 2.5 * 100.0))
            else:
                score_bonus = min(100.0, max(20.0, (fantamedia - 5.5) / 3.0 * 100.0))
    
            score_titolare = min(100.0, max(15.0, presenza_pct))
    
            if varianza_v is not None and pd.notna(varianza_v):
                score_regolarita = min(100.0, max(20.0, 100.0 - (float(varianza_v) * 60.0)))
            else:
                score_regolarita = 70.0
    
            score_affidabilita = 92.0
            if infortunato_val in ["sì", "si", "true", "1", "yes"] or bool(player_row.get("infortunato", False)):
                score_affidabilita -= 35.0
            if presenze_medie < 20:
                score_affidabilita -= 20.0
            score_affidabilita = min(100.0, max(25.0, score_affidabilita))
    
            score_disciplina = min(100.0, max(25.0, 100.0 - (ammonizioni * 6.0 + espulsioni * 20.0)))
    
            dna_categories = ["Bonus/FM", "Titolarità", "Regolarità", "Affidabilità", "Disciplina"]
            dna_values = [score_bonus, score_titolare, score_regolarita, score_affidabilita, score_disciplina]
    
            # Classificazioni metriche secondarie
    
            if varianza_v is not None and pd.notna(varianza_v):
                v_num = float(varianza_v)
                if v_num < 0.4:
                    var_desc = "Altissima regolarità"
                elif v_num < 0.7:
                    var_desc = "Buona regolarità"
                else:
                    var_desc = "Rendimento altalenante"
            else:
                var_desc = "Dati storici limitati"
    
            if score_affidabilita >= 80:
                aff_desc = "Alta certezza titolare"
            elif score_affidabilita >= 60:
                aff_desc = "Buona affidabilità"
            else:
                aff_desc = "Profilo a rischio"
    
            # --- SEZIONE SECONDARIA: METRICHE + DNA RADAR CHART ---
            sec_col_left, sec_col_right = st.columns([0.56, 0.44], gap="medium")
            with sec_col_left:
                st.markdown("""
                <div style="font-weight: 700; font-size: 0.92rem; color: #F8FAFC; margin-bottom: 8px;">
                    🎯 Indicatori Strategici Asta
                </div>
                """, unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                with m1:
                    st.markdown(f"""
                    <div class="sub-card" style="margin-bottom: 10px;">
                        <div class="sub-label">Varianza Voto</div>
                        <div class="sub-value">{format_number(varianza_v)}</div>
                        <div class="sub-desc">{var_desc}</div>
                    </div>
                    <div class="sub-card">
                        <div class="sub-label">Disciplina & Malus</div>
                        <div class="sub-value" style="color: #FBBF24;">{ammonizioni:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">Amm</span> | {espulsioni:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">Esp</span></div>
                        <div class="sub-desc">Malus medio annuo</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m2:
                    if is_goalkeeper:
                        st.markdown(f"""
                        <div class="sub-card" style="margin-bottom: 10px;">
                            <div class="sub-label">Rendimento Portiere</div>
                            <div class="sub-value" style="color: #38BDF8;">{gs_stagione:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">GS</span> | {rigori_parati:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">RP</span></div>
                            <div class="sub-desc">Gol subiti e rigori parati medi</div>
                        </div>
                        <div class="sub-card">
                            <div class="sub-label">Affidabilità Asta</div>
                            <div class="sub-value" style="color: #38BDF8;">{score_affidabilita:.0f}%</div>
                            <div class="sub-desc">{aff_desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="sub-card" style="margin-bottom: 10px;">
                            <div class="sub-label">Gol & Assist Medi</div>
                            <div class="sub-value" style="color: #34D399;">{gol_stagione:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">Gol</span> | {assist_stagione:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">Assist</span></div>
                            <div class="sub-desc">Bonus medi a stagione</div>
                        </div>
                        <div class="sub-card">
                            <div class="sub-label">Affidabilità Asta</div>
                            <div class="sub-value" style="color: #38BDF8;">{score_affidabilita:.0f}%</div>
                            <div class="sub-desc">{aff_desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
            with sec_col_right:
                st.markdown("""
                <div style="font-weight: 700; font-size: 0.92rem; color: #F8FAFC; margin-bottom: 8px;">
                    🧬 DNA del Calciatore (Scala 0-100)
                </div>
                """, unsafe_allow_html=True)
                fig_radar = build_radar_dna_chart(dna_categories, dna_values)
                st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})
    
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
            # --- GRAFICO TREND (ALTEZZA AUMENTATA E RANGE DINAMICO) ---
            st.markdown("""
            <div style="font-weight: 700; font-size: 1rem; color: #F8FAFC; margin-bottom: 8px;">
                📈 Trend di Forma (Rolling 5 Giornate)
            </div>
            """, unsafe_allow_html=True)
    
            # Carica partite on-demand solo per grafico e tabella storico
            p_stats = fetch_player_matches(player_id)
            if not p_stats.empty:
                if "stagione" in p_stats.columns: p_stats["stagione"] = p_stats["stagione"].astype(str).str.strip()
                if "giornata" in p_stats.columns: p_stats["giornata"] = pd.to_numeric(p_stats["giornata"], errors="coerce")
                p_stats = remove_starred_vote_rows(p_stats)
                p_stats = calculate_bonus_malus(p_stats)
                rolling_df = build_rolling_data(p_stats, window=5)
                if not rolling_df.empty:
                    fig = go.Figure()
                    
                    # Calcola dinamicamente il limite Y (Scala Minima 12.0)
                    upper_y = 12.0
                    if "media_mobile_fanta" in rolling_df.columns:
                        max_fanta = rolling_df["media_mobile_fanta"].max()
                        if pd.notna(max_fanta) and max_fanta > 11.0:
                            upper_y = max_fanta + 1.0
    
                    if "media_mobile_fanta" in rolling_df.columns:
                        fig.add_trace(go.Scatter(x=rolling_df["periodo"], y=rolling_df["media_mobile_fanta"], mode="lines", name="Fantamedia (5G)", line=dict(color="#10B981", width=3, shape="spline"), fill="tozeroy", fillcolor="rgba(16, 185, 129, 0.08)", hovertemplate="<b>%{x}</b><br>Fantamedia: <b>%{y:.2f}</b><extra></extra>"))
                    if "media_mobile_voto" in rolling_df.columns:
                        fig.add_trace(go.Scatter(x=rolling_df["periodo"], y=rolling_df["media_mobile_voto"], mode="lines", name="Media Voto (5G)", line=dict(color="#60A5FA", width=2, dash="dot", shape="spline"), hovertemplate="<b>%{x}</b><br>Media Voto: <b>%{y:.2f}</b><extra></extra>"))
    
                    fig.add_hline(y=6.0, line_dash="dash", line_color="rgba(255,255,255,0.2)", annotation_text="Sufficienza", annotation_position="bottom right")
    
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(17, 24, 39, 0.6)",
                        font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
                        hovermode="x unified",
                        height=400,
                        margin=dict(l=10, r=10, t=30, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
                        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True, range=[4.0, upper_y]),
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
                # --- TABELLA STORICO ---
                st.markdown("""
                <div style="font-weight: 700; font-size: 1rem; color: #F8FAFC; margin-top: 12px; margin-bottom: 8px;">
                    📅 Storico Prestazioni per Stagione
                </div>
                """, unsafe_allow_html=True)
    
                if "stagione" in p_stats.columns:
                    rows = []
                    for s, g in p_stats.groupby("stagione"):
                        gfanta = calculate_fantavoto(g)
                        if is_goalkeeper:
                            rows.append({"Stagione": s, "Presenze": int(numeric_series(g, "voto").count()), "Media Voto": round(safe_mean(g, "voto"), 2), "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2), "Gol Subiti": int(safe_sum(g, "gs")), "Clean Sheet": (numeric_series(g, "gs") == 0).sum(), "Amm": int(safe_sum(g, "amm")), "Esp": int(safe_sum(g, "esp"))})
                        else:
                            rows.append({"Stagione": s, "Presenze": int(numeric_series(g, "voto").count()), "Media Voto": round(safe_mean(g, "voto"), 2), "Fantamedia": round(safe_mean(gfanta, "fanta_voto_calcolato"), 2), "Gol": int(safe_sum(g, "gf") + safe_sum(g, "rf")), "Assist": int(safe_sum(g, "ass")), "Amm": int(safe_sum(g, "amm")), "Esp": int(safe_sum(g, "esp"))})
    
                    season_df = pd.DataFrame(rows)
                    if not season_df.empty:
                        season_df["_sort"] = season_df["Stagione"].apply(season_sort_key)
                        season_df = season_df.sort_values("_sort", ascending=False).drop(columns="_sort")
                        st.dataframe(season_df, use_container_width=True, hide_index=True, column_config={"Fantamedia": st.column_config.NumberColumn(format="%.2f ⭐"), "Media Voto": st.column_config.NumberColumn(format="%.2f"), "Presenze": st.column_config.ProgressColumn(min_value=0, max_value=38, format="%d / 38")})
            else:
                st.info("Nessuna statistica storica disponibile per questo calciatore.")


# ==========================================
# 7. TAB 2: LA MIA ROSA & ASTA LIVE (COMPACT)
# ==========================================

with tab_rosa:
    # 1. RIEPILOGO METRICHE COMPATTO IN ALTO
    pct_spesi = (crediti_spesi / st.session_state.budget_totale * 100) if st.session_state.budget_totale > 0 else 0
    slot_mancanti = max(0, 25 - num_rosa)
    costo_medio_slot = (crediti_residui / slot_mancanti) if slot_mancanti > 0 else 0
    
    fms = [float(p.get("fantamedia") or 0.0) for p in st.session_state.roster if float(p.get("fantamedia") or 0.0) > 0]
    avg_fm_rosa = (sum(fms) / len(fms)) if fms else 0.0
    
    valore_tot_ml = sum(float(p.get("stima_prezzo") or 0.0) for p in st.session_state.roster)
    delta_ml = valore_tot_ml - crediti_spesi
    delta_sign = f"+{delta_ml:.0f}" if delta_ml >= 0 else f"{delta_ml:.0f}"
    delta_color = "#34D399" if delta_ml >= 0 else "#F87171"

    best_res = optimize_best_lineup(st.session_state.roster, forced_module="Auto")

    k1, k2, k3, k4, k5 = st.columns(5, gap="small")
    with k1:
        st.markdown(f'''
        <div class="kpi-card-compact">
            <div class="kpi-label">Crediti Residui</div>
            <div class="kpi-value" style="color: #34D399;">{crediti_residui} <span style="font-size:0.75rem; color:#94A3B8;">FMV</span></div>
            <div class="kpi-sub">Spesi {crediti_spesi} ({pct_spesi:.0f}%)</div>
        </div>
        ''', unsafe_allow_html=True)
    with k2:
        val_s = f"{costo_medio_slot:.0f} FMV" if slot_mancanti > 0 else "Completa! 🎉"
        st.markdown(f'''
        <div class="kpi-card-compact">
            <div class="kpi-label">Media / Slot Libero</div>
            <div class="kpi-value" style="color: #38BDF8;">{val_s}</div>
            <div class="kpi-sub">{slot_mancanti} slot mancanti</div>
        </div>
        ''', unsafe_allow_html=True)
    with k3:
        st.markdown(f'''
        <div class="kpi-card-compact">
            <div class="kpi-label">Fantamedia Rosa</div>
            <div class="kpi-value" style="color: #FBBF24;">{avg_fm_rosa:.2f} ⭐</div>
            <div class="kpi-sub">Media complessiva</div>
        </div>
        ''', unsafe_allow_html=True)
    with k4:
        st.markdown(f'''
        <div class="kpi-card-compact">
            <div class="kpi-label">Potenziale 11 Titolare</div>
            <div class="kpi-value" style="color: #A78BFA;">{best_res['score']:.2f}</div>
            <div class="kpi-sub">Modulo: {best_res['module']}</div>
        </div>
        ''', unsafe_allow_html=True)
    with k5:
        st.markdown(f'''
        <div class="kpi-card-compact">
            <div class="kpi-label">Bilancio Modello ML</div>
            <div class="kpi-value" style="color: {delta_color};">{delta_sign} <span style="font-size:0.75rem; color:#94A3B8;">FMV</span></div>
            <div class="kpi-sub">{"Risparmio asta" if delta_ml >= 0 else "Spesa sopra stima"}</div>
        </div>
        ''', unsafe_allow_html=True)

    # Barra di avanzamento slot orizzontale compatta
    st.markdown(f'''
    <div style="background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 6px 14px; display: flex; justify-content: space-between; align-items: center; margin: 8px 0 16px 0; font-size: 0.78rem;">
        <div><span class="badge-role-P" style="padding:1px 5px; border-radius:3px; font-weight:800;">P</span> Portieri: <b style="color:#F8FAFC;">{role_counts['P']}/3</b></div>
        <div><span class="badge-role-D" style="padding:1px 5px; border-radius:3px; font-weight:800;">D</span> Difensori: <b style="color:#F8FAFC;">{role_counts['D']}/8</b></div>
        <div><span class="badge-role-C" style="padding:1px 5px; border-radius:3px; font-weight:800;">C</span> Centrocampisti: <b style="color:#F8FAFC;">{role_counts['C']}/8</b></div>
        <div><span class="badge-role-A" style="padding:1px 5px; border-radius:3px; font-weight:800;">A</span> Attaccanti: <b style="color:#F8FAFC;">{role_counts['A']}/6</b></div>
        <div style="color:#34D399; font-weight:700;">Totale Rosa: {num_rosa} / 25</div>
    </div>
    ''', unsafe_allow_html=True)

    # 2. LAYOUT DUE COLONNE AFFIANCATE: TABELLA A SINISTRA (STRETTA), FORMAZIONE A DESTRA (ALLARGATA)
    col_tabella, col_campo = st.columns([0.45, 0.55], gap="large")

    # -------------------------------------------------------------
    # COLONNA SINISTRA: TABELLA STRETTA E COMPATTA
    # -------------------------------------------------------------
    with col_tabella:
        st.markdown('''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; min-height: 28px;">
            <div style="font-weight: 800; font-size: 1.08rem; color: #F8FAFC;">
                📋 La Mia Rosa ({num_rosa}/25)
            </div>
            <div style="font-size: 0.82rem; color: #94A3B8;">
                Spesi: <b style="color:#F59E0B; font-size: 0.95rem;">{crediti_spesi} FMV</b>
            </div>
        </div>
        '''.format(num_rosa=num_rosa, crediti_spesi=crediti_spesi), unsafe_allow_html=True)

        if not st.session_state.roster:
            st.info("💡 La rosa è vuota. Aggiungi giocatori dalla schermata **'Esplora & Analytics'** cliccando su **'➕ Aggiungi alla Rosa'**!")
        else:
            for r_code, r_name, r_badge, r_max in [("P", "Portieri", "badge-role-P", 3), ("D", "Difensori", "badge-role-D", 8), ("C", "Centrocampisti", "badge-role-C", 8), ("A", "Attaccanti", "badge-role-A", 6)]:
                players_in_role = [p for p in st.session_state.roster if p.get("ruolo") == r_code]
                spesa_rep = sum(p.get('prezzo', 0) for p in players_in_role)
                
                st.markdown(f'''
                <div class="roster-role-header-compact">
                    <div>
                        <span class="{r_badge}" style="padding: 2px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 800; margin-right: 8px;">{r_code}</span>
                        <span style="font-size: 0.98rem; font-weight: 800;">{r_name}</span> <span style="font-size: 0.82rem; color: #94A3B8; font-weight: 600;">({len(players_in_role)}/{r_max})</span>
                    </div>
                    <div style="font-size: 0.80rem; color: #94A3B8; font-weight: 600;">
                        Tot: <b style="color: #F59E0B; font-size: 0.90rem;">{spesa_rep} FMV</b>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

                if not players_in_role:
                    st.markdown(f"<div style='color: #64748B; font-size: 0.78rem; padding: 4px 10px; margin-bottom: 8px;'>Nessun {r_name.lower()} acquistato</div>", unsafe_allow_html=True)
                else:
                    for p in players_in_role:
                        pid = p["player_id"]
                        fm_val = float(p.get("fantamedia") or p.get("media_voto") or 0.0)
                        prezzo_m = int(p.get("prezzo", 0))
                        stima_m = float(p.get("stima_prezzo") or 0.0)
                        delta_p = stima_m - prezzo_m
                        d_col = "#34D399" if delta_p >= 0 else "#F87171"
                        d_str = f"+{delta_p:.0f}" if delta_p >= 0 else f"{delta_p:.0f}"
                        
                        is_tit = p.get("is_titolare", False)
                        tit_dot = "🟢" if is_tit else "🟠"

                        c_nom, c_fm, c_prz, c_del = st.columns([0.50, 0.20, 0.22, 0.08], gap="small")
                        with c_nom:
                            st.markdown(f"<div class='roster-row-nom'><span style='margin-right:8px; font-size:0.90rem;'>{tit_dot}</span>{p['nome']} <span style='font-size:0.80rem; color:#94A3B8; font-weight:500; margin-left:4px;'>({p['squadra']})</span></div>", unsafe_allow_html=True)
                        with c_fm:
                            st.markdown(f"<div class='roster-row-fm'>{fm_val:.2f} FM</div>", unsafe_allow_html=True)
                        with c_prz:
                            st.markdown(f"<div class='roster-row-prz'>{prezzo_m} FMV</div>", unsafe_allow_html=True)
                        with c_del:
                            if st.button("✕", key=f"del_r_{pid}", help=f"Rimuovi {p['nome']} e rimborsa {prezzo_m} crediti"):
                                st.session_state.roster = [x for x in st.session_state.roster if x["player_id"] != pid]
                                save_roster_to_disk()
                                st.toast(f"🗑️ {p['nome']} rimosso!", icon="ℹ️")
                                st.rerun()

        # Azioni Esportazione compatte
        st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
        act_b1, act_b2 = st.columns(2, gap="small")
        with act_b1:
            if st.session_state.roster:
                export_df = pd.DataFrame(st.session_state.roster)[[
                    "ruolo", "nome", "squadra", "prezzo", "fantamedia", "media_voto", "stima_prezzo", "fvm", "quotazione_attuale"
                ]].rename(columns={
                    "ruolo": "Ruolo", "nome": "Nome", "squadra": "Squadra", "prezzo": "Prezzo Pagato",
                    "fantamedia": "Fantamedia", "media_voto": "Media Voto", "stima_prezzo": "Stima ML",
                    "fvm": "FVM", "quotazione_attuale": "Listino"
                })
                csv_data = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Scarica Rosa (CSV)",
                    data=csv_data,
                    file_name="mia_rosa_fantacalcio.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.button("📥 Scarica Rosa", disabled=True, use_container_width=True)
        with act_b2:
            if st.button("🔄 Azzera Rosa", type="secondary", use_container_width=True):
                modal_reset_roster()

    # -------------------------------------------------------------
    # COLONNA DESTRA: FORMAZIONE TITOLARE SULLA DESTRA (BEST 11)
    # -------------------------------------------------------------
    with col_campo:
        st.markdown('''
        <div style="display: flex; align-items: center; font-weight: 800; font-size: 1.08rem; color: #F8FAFC; margin-bottom: 8px; min-height: 28px;">
            🏆 Formazione Titolare Consigliata
        </div>
        ''', unsafe_allow_html=True)

        opt_c1, opt_c2 = st.columns([0.42, 0.58], gap="small")
        with opt_c1:
            sel_mod = st.selectbox(
                "Modulo Tattico",
                ["🤖 Automatico", "3-4-3", "4-3-3", "3-5-2", "4-4-2", "4-5-1", "5-3-2", "5-4-1"],
                index=0,
                label_visibility="collapsed"
            )
            chosen_module = "Auto" if "Automatico" in sel_mod else sel_mod
            active_lineup = optimize_best_lineup(st.session_state.roster, forced_module=chosen_module)
        with opt_c2:
            st.markdown(f'''
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 5px 10px; display: flex; justify-content: space-between; align-items: center; min-height: 32px; height: 32px; box-sizing: border-box;">
                <span style="font-size: 0.76rem; color: #94A3B8;">Modulo: <b style="color: #34D399;">{active_lineup['module']}</b></span>
                <span style="font-size: 0.76rem; color: #F8FAFC;">Potenziale: <b style="color: #34D399;">{active_lineup['score']:.2f} FM</b></span>
            </div>
            ''', unsafe_allow_html=True)

        req = active_lineup["requirements"]
        starters = active_lineup["starters"]
        bench = active_lineup["bench"]

        # FUNZIONE RENDERING RIGA SENZA INDENTAZIONI MARKDOWN (RISOLVE IL BUG DEL CODICE GREZZO)
        def render_pitch_row_clean(role_letter, title, needed_count, player_list, badge_class):
            cards = []
            for p in player_list:
                nome_p = p.get("nome", "Calciatore")
                sq_p = p.get("squadra", "-")
                fm_p = float(p.get("fantamedia") or p.get("media_voto") or 0.0)
                pr_p = int(p.get("prezzo", 0))
                c_html = (
                    f'<div class="player-pitch-card">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">'
                    f'<span class="{badge_class}" style="font-size:0.70rem; padding:1px 5px; border-radius:3px; font-weight:800;">{role_letter}</span>'
                    f'<span style="font-size:0.74rem; color:#F59E0B; font-weight:800;">{pr_p} FMV</span>'
                    f'</div>'
                    f'<div style="font-weight:800; font-size:0.86rem; color:#F8FAFC; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{nome_p}">{nome_p}</div>'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.72rem; margin-top:3px; border-top:1px solid rgba(255,255,255,0.1); padding-top:3px;">'
                    f'<span style="color:#CBD5E1; font-size:0.70rem; font-weight:500;">{sq_p}</span>'
                    f'<b style="color:#34D399; font-size:0.80rem; font-weight:800;">{fm_p:.2f} FM</b>'
                    f'</div>'
                    f'</div>'
                )
                cards.append(c_html)

            missing = needed_count - len(player_list)
            for _ in range(missing):
                e_html = (
                    f'<div class="player-pitch-card-empty">'
                    f'<div style="font-weight:700; font-size:0.78rem; color:#94A3B8;">➕ {role_letter}</div>'
                    f'<div style="font-size:0.65rem; color:#64748B;">Slot mancante</div>'
                    f'</div>'
                )
                cards.append(e_html)

            all_cards = "".join(cards)
            return f'<div class="pitch-row-title">{title}</div><div class="pitch-row-cards">{all_cards}</div>'

        # Campo Tattico
        p_html = '<div class="pitch-container">'
        p_html += render_pitch_row_clean("A", "⚡ ATTACCO", req["A"], starters["A"], "badge-role-A")
        p_html += '<div style="border-top: 1px dashed rgba(255,255,255,0.12); margin: 12px 0;"></div>'
        p_html += render_pitch_row_clean("C", "⚙️ CENTROCAMPO", req["C"], starters["C"], "badge-role-C")
        p_html += '<div style="border-top: 1px dashed rgba(255,255,255,0.12); margin: 12px 0;"></div>'
        p_html += render_pitch_row_clean("D", "🛡️ DIFESA", req["D"], starters["D"], "badge-role-D")
        p_html += '<div style="border-top: 1px dashed rgba(255,255,255,0.12); margin: 12px 0;"></div>'
        p_html += render_pitch_row_clean("P", "🧤 PORTA", req["P"], starters["P"], "badge-role-P")
        p_html += '</div>'

        st.markdown(p_html, unsafe_allow_html=True)

        # Riserve / Panchina orizzontale compatta sotto al campo
        tot_bench = sum(len(b) for b in bench.values())
        if tot_bench == 0:
            st.caption("🪑 Panchina vuota: tutti i giocatori acquistati sono titolari nell'11.")
        else:
            st.markdown(f"<div style='font-size:0.78rem; font-weight:700; color:#94A3B8; margin-bottom:4px;'>🪑 Riserve in Panchina ({tot_bench}):</div>", unsafe_allow_html=True)
            bench_pills = []
            for r_c, r_cl in [("P", "badge-role-P"), ("D", "badge-role-D"), ("C", "badge-role-C"), ("A", "badge-role-A")]:
                for bp in bench.get(r_c, []):
                    fm_b = float(bp.get("fantamedia") or bp.get("media_voto") or 0.0)
                    prz_b = int(bp.get("prezzo", 0))
                    pill = (
                        f'<span style="background:#111827; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:2px 7px; margin-right:5px; margin-bottom:4px; display:inline-block; font-size:0.72rem;">'
                        f'<span class="{r_cl}" style="font-size:0.6rem; padding:1px 3px; border-radius:3px;">{r_c}</span> '
                        f'<b>{bp["nome"]}</b> <span style="color:#34D399;">{fm_b:.2f} FM</span> <span style="color:#F59E0B;">({prz_b} FMV)</span>'
                        f'</span>'
                    )
                    bench_pills.append(pill)
            st.markdown("".join(bench_pills), unsafe_allow_html=True)

