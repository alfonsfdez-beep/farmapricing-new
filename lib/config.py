"""
Configuración de la app. Lee desde st.secrets en cloud, o env vars en local.
"""
from __future__ import annotations

import os
import streamlit as st


def _get(key: str, default: str = "") -> str:
    # Streamlit secrets en producción, env vars en local
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


GOOGLE_SHEET_ID = _get("GOOGLE_SHEET_ID", "1_rn_2CTc8yEcnZUUei-ytKAEW0lph3QeUKojCS3WRd8")

# Pestañas que alimenta el pipeline 01-06
TAB_MERCADO = _get("SHEET_TAB_MERCADO", "mercado")
TAB_RECOMENDACIONES = _get("SHEET_TAB_RECOMENDACIONES", "Recomendaciones")
TAB_RECOMENDACIONES_RESUMEN = _get("SHEET_TAB_RECOMENDACIONES_RESUMEN", "Recomendaciones_Resumen")
TAB_HUECOS_FAMILIA = _get("SHEET_TAB_HUECOS_FAMILIA", "Huecos_Familia")
TAB_HUECOS_SUBFAMILIA = _get("SHEET_TAB_HUECOS_SUBFAMILIA", "Huecos_Subfamilia")
TAB_HUECOS_PRODUCTOS = _get("SHEET_TAB_HUECOS_PRODUCTOS", "Huecos_Productos")

# Pestañas que escribe esta app (log de decisiones)
TAB_DECISIONES_PRICING = _get("SHEET_TAB_DECISIONES_PRICING", "Decisiones_Pricing")
TAB_DECISIONES_SURTIDO = _get("SHEET_TAB_DECISIONES_SURTIDO", "Decisiones_Surtido")

APP_TITLE = "Farmapricing - Centro de Decisiones"
APP_ICON = ":pill:"  # se usa la versión por defecto si el cliente no soporta emojis
