"""
Farmapricing - Centro de Decisiones.

Punto de entrada. Streamlit detecta automáticamente las páginas en /pages.
"""
from __future__ import annotations

import streamlit as st

from lib import config as cfg
from lib import data as d
from lib import ui

ui.setup_page("Inicio")
ui.page_header("Farmapricing", "Centro de decisiones de pricing y surtido")

# Health check rápido: ¿hay datos en el sheet?
with st.spinner("Conectando con Google Sheets..."):
    rec = d.get_recomendaciones()
    huecos = d.get_huecos_familia()

if rec.empty and huecos.empty:
    st.error(
        "No se han encontrado datos en el Google Sheet. Asegúrate de haber ejecutado "
        "`python run_all.py` en el PC para alimentar las pestañas Recomendaciones y "
        "Huecos_*."
    )
    st.stop()

# Resumen breve
n_pendientes = 0
if not rec.empty and "TipoCambio" in rec.columns:
    n_pendientes = (rec["TipoCambio"].isin(["PVP", "PROMO"])).sum()

cobertura = None
if not huecos.empty and "Cobertura_Pct" in huecos.columns:
    # Cobertura ponderada por venta de mercado
    if "Venta_Mercado_Total" in huecos.columns:
        tot = huecos["Venta_Mercado_Total"].sum()
        if tot > 0:
            cobertura = (huecos["Cobertura_Pct"] * huecos["Venta_Mercado_Total"]).sum() / tot

c1, c2, c3 = st.columns(3)
c1.metric("Recomendaciones pendientes", n_pendientes)
c2.metric("Cobertura del mercado (ponderada)", f"{cobertura:.1f}%" if cobertura else "-")
c3.metric("Pestañas leídas", "Sheets OK")

st.divider()

st.markdown("### Páginas")
st.markdown(
    """
    Usa el menú lateral para navegar:

    - **Dashboard**: KPIs ejecutivos y top oportunidades.
    - **Pricing**: revisar y aprobar/rechazar las recomendaciones de precio.
    - **Surtido**: huecos del catálogo vs mercado, decisiones de compra.
    - **Producto**: drill-down por artículo individual con histórico.
    """
)

with st.sidebar:
    st.subheader("Configuración activa")
    st.code(
        f"Sheet ID: {cfg.GOOGLE_SHEET_ID[:20]}...\n"
        f"Pestaña recomendaciones: {cfg.TAB_RECOMENDACIONES}\n"
        f"Pestaña decisiones pricing: {cfg.TAB_DECISIONES_PRICING}\n"
        f"Pestaña decisiones surtido: {cfg.TAB_DECISIONES_SURTIDO}",
        language="text",
    )
ui.sidebar_refresh_button()
